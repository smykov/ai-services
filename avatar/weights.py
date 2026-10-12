"""Download model weights into the /models volume on first start (they are not baked into the image)."""
import os
import urllib.request

from huggingface_hub import hf_hub_download

MODELS_DIR = os.environ.get("AVATAR_MODELS_DIR", "/models")

HF_FILES = [
    ("TMElyralab/MuseTalk", "musetalkV15/musetalk.json", ""),
    ("TMElyralab/MuseTalk", "musetalkV15/unet.pth", ""),
    ("stabilityai/sd-vae-ft-mse", "config.json", "sd-vae"),
    ("stabilityai/sd-vae-ft-mse", "diffusion_pytorch_model.bin", "sd-vae"),
    ("openai/whisper-tiny", "config.json", "whisper"),
    ("openai/whisper-tiny", "pytorch_model.bin", "whisper"),
    ("openai/whisper-tiny", "preprocessor_config.json", "whisper"),
    ("yzd-v/DWPose", "dw-ll_ucoco_384.pth", "dwpose"),
    # Mirror of the face-parsing BiSeNet weights MuseTalk publishes on Google Drive.
    ("ManyOtherFunctions/face-parse-bisent", "79999_iter.pth", "face-parse-bisent"),
]

URL_FILES = [
    ("https://download.pytorch.org/models/resnet18-5c106cde.pth", "face-parse-bisent/resnet18-5c106cde.pth"),
    ("https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth", "gfpgan/GFPGANv1.4.pth"),
]


def ensure_weights(models_dir: str = MODELS_DIR):
    for repo, filename, subdir in HF_FILES:
        target_dir = os.path.join(models_dir, subdir)
        if not os.path.exists(os.path.join(target_dir, filename)):
            print(f"downloading {repo}/{filename}", flush=True)
            hf_hub_download(repo, filename, local_dir=target_dir)
    for url, rel in URL_FILES:
        target = os.path.join(models_dir, rel)
        if not os.path.exists(target):
            print(f"downloading {url}", flush=True)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            urllib.request.urlretrieve(url, target + ".part")
            os.replace(target + ".part", target)
    os.makedirs(os.path.join(models_dir, "gfpgan", "weights"), exist_ok=True)


if __name__ == "__main__":
    ensure_weights()
