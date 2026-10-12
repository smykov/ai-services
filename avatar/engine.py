"""Talking-head rendering: MuseTalk 1.5 lip-sync plus optional GFPGAN face restoration.

The face (a short video of a person looking at the camera, or a photo) is prepared once
and cached on disk by content hash: frames, face boxes, VAE latents, blending masks and the
"idle" frames shown during silences. Rendering then only runs the lip-sync network on frames
that carry speech, so long training videos with pauses cost roughly their speaking time.

MuseTalk's code is imported from its checkout (MUSETALK_DIR) and expects `./models` relative
to the working directory; the Dockerfile links that to the persistent /models volume.
"""
import gc
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

import cv2
import numpy as np
import torch
from speech_mask import cycle_index, speech_frames

FPS = 25
AUDIO_RATE = 16000
MUSETALK_DIR = os.environ.get("MUSETALK_DIR", "/opt/MuseTalk")
MAX_SOURCE_SECONDS = 30
CACHE_VERSION = "1"


@dataclass
class FaceOptions:
    max_side: int = 720
    extra_margin: int = 10
    parsing_mode: str = "jaw"
    left_cheek_width: int = 90
    right_cheek_width: int = 90

    def key(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True)


@dataclass
class Face:
    face_id: str
    path: str
    frames: np.ndarray  # N x H x W x 3, BGR
    coords: list[list[int]]
    latents: torch.Tensor  # N x 8 x 32 x 32
    masks: list[np.ndarray]
    mask_boxes: list[list[int]]


def face_id_for(data: bytes, opts: FaceOptions) -> str:
    h = hashlib.sha256(data)
    h.update(opts.key().encode())
    h.update(CACHE_VERSION.encode())
    return h.hexdigest()[:32]


def _run(cmd: list[str]):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _load_audio(path: str) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(AUDIO_RATE), "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


class Engine:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(os.path.join(cache_dir, "faces"), exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self._core = None
        self._restorer = None
        self._faces: dict[str, Face] = {}
        if MUSETALK_DIR not in sys.path:
            sys.path.insert(0, MUSETALK_DIR)

    # ---------- model lifecycle ----------

    @property
    def loaded(self) -> bool:
        return self._core is not None or self._restorer is not None

    def _ensure_core(self):
        if self._core is not None:
            return self._core
        os.chdir(MUSETALK_DIR)
        from musetalk.utils.audio_processor import AudioProcessor
        from musetalk.utils.utils import load_all_model
        from transformers import WhisperModel

        vae, unet, pe = load_all_model(device=self.device)
        pe = pe.to(self.device, dtype=self.dtype)
        vae.vae = vae.vae.to(self.device, dtype=self.dtype)
        unet.model = unet.model.to(self.device, dtype=self.dtype)
        whisper = WhisperModel.from_pretrained("./models/whisper").to(self.device, dtype=self.dtype).eval()
        whisper.requires_grad_(False)
        self._core = {
            "vae": vae, "unet": unet, "pe": pe, "whisper": whisper,
            "audio": AudioProcessor(feature_extractor_path="./models/whisper"),
            "timesteps": torch.tensor([0], device=self.device),
        }
        return self._core

    def _ensure_restorer(self):
        if self._restorer is None:
            os.chdir(MUSETALK_DIR)
            from gfpgan import GFPGANer

            self._restorer = GFPGANer(model_path="./models/gfpgan/GFPGANv1.4.pth", upscale=1, arch="clean",
                                      channel_multiplier=2, bg_upsampler=None)
        return self._restorer

    def unload(self):
        """Free the GPU; prepared faces stay on disk."""
        self._core = None
        self._restorer = None
        self._faces.clear()
        self._drop_preprocessing()

    @staticmethod
    def _drop_preprocessing():
        # Importing MuseTalk's preprocessing puts the pose and face detectors on the GPU;
        # they are needed only while preparing a face.
        for name in [m for m in sys.modules if m.startswith("musetalk.utils.preprocessing")]:
            del sys.modules[name]
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # ---------- face preparation ----------

    def face_dir(self, face_id: str) -> str:
        return os.path.join(self.cache_dir, "faces", face_id)

    def has_face(self, face_id: str) -> bool:
        return os.path.exists(os.path.join(self.face_dir(face_id), "meta.json"))

    def prepare(self, face_path: str, opts: FaceOptions) -> Face:
        with open(face_path, "rb") as f:
            face_id = face_id_for(f.read(), opts)
        if face_id in self._faces:
            return self._faces[face_id]
        d = self.face_dir(face_id)
        if not self.has_face(face_id):
            self._prepare_to_disk(face_path, opts, d)
        return self.load_face(face_id)

    def load_face(self, face_id: str) -> Face:
        if face_id in self._faces:
            return self._faces[face_id]
        d = self.face_dir(face_id)
        if not self.has_face(face_id):
            raise KeyError(f"unknown face_id {face_id}")
        meta = json.load(open(os.path.join(d, "meta.json")))
        masks = np.load(os.path.join(d, "masks.npz"))
        face = Face(
            face_id=face_id, path=d,
            frames=np.load(os.path.join(d, "frames.npy"), mmap_mode="r"),
            coords=meta["coords"],
            latents=torch.load(os.path.join(d, "latents.pt"), map_location="cpu"),
            masks=[masks[f"m{i}"] for i in range(len(meta["coords"]))],
            mask_boxes=meta["mask_boxes"],
        )
        self._faces[face_id] = face
        return face

    def _prepare_to_disk(self, face_path: str, opts: FaceOptions, d: str):
        core = self._ensure_core()
        os.chdir(MUSETALK_DIR)
        from musetalk.utils.blending import get_image_prepare_material
        from musetalk.utils.face_parsing import FaceParsing
        from musetalk.utils.preprocessing import coord_placeholder, get_landmark_and_bbox

        tmp = tempfile.mkdtemp(prefix="face-", dir=self.cache_dir)
        scale = f"scale='if(gt(iw,ih),min({opts.max_side},iw),-2)':'if(gt(iw,ih),-2,min({opts.max_side},ih))'"
        _run(["ffmpeg", "-v", "error", "-y", "-i", face_path, "-t", str(MAX_SOURCE_SECONDS),
              "-vf", f"fps={FPS},{scale}", "-start_number", "0", os.path.join(tmp, "%08d.png")])
        paths = sorted(os.path.join(tmp, p) for p in os.listdir(tmp) if p.endswith(".png"))
        if not paths:
            raise ValueError("no frames could be read from the face file")

        coords, frames = get_landmark_and_bbox(paths, 0)
        keep = [i for i, c in enumerate(coords) if c != coord_placeholder]
        if not keep:
            raise ValueError("no face found in the face file")
        fp = FaceParsing(left_cheek_width=opts.left_cheek_width, right_cheek_width=opts.right_cheek_width)

        out_frames, out_coords, latents, masks, mask_boxes = [], [], [], [], []
        for i in keep:
            frame = frames[i]
            x1, y1, x2, y2 = (int(v) for v in coords[i])
            y2 = min(y2 + opts.extra_margin, frame.shape[0])
            crop = cv2.resize(frame[y1:y2, x1:x2], (256, 256), interpolation=cv2.INTER_LANCZOS4)
            latents.append(core["vae"].get_latents_for_unet(crop).cpu())
            mask, box = get_image_prepare_material(frame, [x1, y1, x2, y2], fp=fp, mode=opts.parsing_mode)
            out_frames.append(frame)
            out_coords.append([x1, y1, x2, y2])
            masks.append(mask)
            mask_boxes.append([int(v) for v in box])
        del fp
        self._drop_preprocessing()

        os.makedirs(d, exist_ok=True)
        np.save(os.path.join(d, "frames.npy"), np.stack(out_frames))
        torch.save(torch.cat(latents, dim=0), os.path.join(d, "latents.pt"))
        np.savez(os.path.join(d, "masks.npz"), **{f"m{i}": m for i, m in enumerate(masks)})
        meta = {"coords": out_coords, "mask_boxes": mask_boxes, "options": opts.__dict__,
                "frames": len(out_frames), "dropped": len(paths) - len(keep), "created": time.time()}
        with open(os.path.join(d, "meta.json.tmp"), "w") as f:
            json.dump(meta, f)
        os.replace(os.path.join(d, "meta.json.tmp"), os.path.join(d, "meta.json"))
        subprocess.run(["rm", "-rf", tmp], check=False)

    # ---------- rendering ----------

    def _lipsync(self, face: Face, chunks: torch.Tensor, frame_idx: list[int]) -> list[np.ndarray]:
        core = self._core
        n = len(face.frames)
        latent = torch.cat([face.latents[cycle_index(i, n)].unsqueeze(0) for i in frame_idx]).to(self.device, self.dtype)
        audio = torch.stack([chunks[i] for i in frame_idx]).to(self.device, self.dtype)
        with torch.no_grad():
            feats = core["pe"](audio)
            pred = core["unet"].model(latent, core["timesteps"], encoder_hidden_states=feats).sample
            return list(core["vae"].decode_latents(pred))

    def _blend(self, face: Face, k: int, mouth: np.ndarray) -> np.ndarray:
        from musetalk.utils.blending import get_image_blending

        x1, y1, x2, y2 = face.coords[k]
        mouth = cv2.resize(mouth.astype(np.uint8), (x2 - x1, y2 - y1))
        return get_image_blending(np.array(face.frames[k]), mouth, [x1, y1, x2, y2], face.masks[k], face.mask_boxes[k])

    def _restore(self, face: Face, k: int, frame: np.ndarray, weight: float) -> np.ndarray:
        # Restore only a square around the face: detection and paste-back on the whole frame
        # cost several times more than the restoration network itself.
        x1, y1, x2, y2 = face.coords[k]
        cx, cy, s = (x1 + x2) // 2, (y1 + y2) // 2, int(max(x2 - x1, y2 - y1) * 1.1)
        h, w = frame.shape[:2]
        a, b, c, e = max(0, cx - s), max(0, cy - s), min(w, cx + s), min(h, cy + s)
        crop = np.ascontiguousarray(frame[b:e, a:c])
        _, _, restored = self._ensure_restorer().enhance(crop, has_aligned=False, only_center_face=True,
                                                         paste_back=True, weight=weight)
        if restored is not None and restored.shape == crop.shape:
            frame = frame.copy()
            frame[b:e, a:c] = restored
        return frame

    def _idle_frames(self, face: Face, restore: bool, weight: float) -> np.ndarray | None:
        """Source frames with a closed mouth, run through the same pipeline as speech frames.

        Silence is lip-synced once per source frame and cached, so switching between speech
        and pauses never changes how the face looks.
        """
        name = f"idle_r{weight:.2f}.npy" if restore else "idle.npy"
        path = os.path.join(face.path, name)
        if os.path.exists(path):
            return np.load(path, mmap_mode="r")
        n = len(face.frames)
        chunks = self._chunks(np.zeros(int(math.ceil(n / FPS * AUDIO_RATE)) + AUDIO_RATE, dtype=np.float32))
        out = []
        for start in range(0, n, 16):
            idx = list(range(start, min(n, start + 16)))
            for k, mouth in zip(idx, self._lipsync(face, chunks, idx)):
                frame = self._blend(face, k, mouth)
                out.append(self._restore(face, k, frame, weight) if restore else frame)
        arr = np.stack(out)
        np.save(path + ".tmp.npy", arr)
        os.replace(path + ".tmp.npy", path)
        return arr

    def _chunks(self, samples: np.ndarray) -> torch.Tensor:
        core = self._ensure_core()
        with tempfile.NamedTemporaryFile(suffix=".wav", dir=self.cache_dir) as f:
            import soundfile as sf

            sf.write(f.name, samples, AUDIO_RATE)
            feats, length = core["audio"].get_audio_feature(f.name, weight_dtype=self.dtype)
            with torch.no_grad():
                return core["audio"].get_whisper_chunk(feats, self.device, self.dtype, core["whisper"], length, fps=FPS,
                                                       audio_padding_length_left=2, audio_padding_length_right=2).cpu()

    def render(self, face: Face, audio_path: str, out_path: str, restore: bool = True, restore_weight: float = 0.5,
               batch_size: int = 16, progress=None) -> dict:
        self._ensure_core()
        samples = _load_audio(audio_path)
        chunks = self._chunks(samples)
        total = len(chunks)
        speech = speech_frames(samples, AUDIO_RATE, FPS, total)
        idle = self._idle_frames(face, restore, restore_weight)
        n = len(face.frames)
        h, w = face.frames.shape[1:3]

        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(FPS),
             "-i", "-", "-i", audio_path, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path],
            stdin=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        started, last_report = time.monotonic(), 0.0
        try:
            block = 256
            for start in range(0, total, block):
                frames_idx = list(range(start, min(total, start + block)))
                talk = [i for i in frames_idx if speech[i]]
                mouths = {}
                for b in range(0, len(talk), batch_size):
                    idx = talk[b:b + batch_size]
                    mouths.update(zip(idx, self._lipsync(face, chunks, idx)))
                for i in frames_idx:
                    k = cycle_index(i, n)
                    if i in mouths:
                        frame = self._blend(face, k, mouths[i])
                        if restore:
                            frame = self._restore(face, k, frame, restore_weight)
                    else:
                        frame = idle[k]
                    enc.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())
                now = time.monotonic()
                if progress and now - last_report > 5:
                    last_report = now
                    progress({"frames_done": frames_idx[-1] + 1, "frames_total": total,
                              "elapsed_s": round(now - started, 1)})
        finally:
            enc.stdin.close()
            err = enc.stderr.read().decode(errors="replace")
            enc.wait()
        if enc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {err[-500:]}")
        return {"frames": total, "speech_frames": int(speech.sum()), "seconds": round(total / FPS, 2),
                "width": w, "height": h, "render_s": round(time.monotonic() - started, 1)}
