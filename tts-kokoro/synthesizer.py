"""Kokoro-82M text-to-speech: fast preset voices, no voice cloning, no Russian.

Model card: https://huggingface.co/hexgrad/Kokoro-82M (Apache-2.0). Weights are downloaded
from the Hugging Face hub on first use into HF_HOME.
"""
import os
import tempfile

# Language code from the request (ISO 639-1, optionally with region) -> Kokoro lang_code.
# Japanese and Chinese need extra G2P packages (misaki[ja], misaki[zh]) not installed here.
LANG_CODES = {
    "en": "a",
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr": "f",
    "hi": "h",
    "it": "i",
    "pt": "p",
    "pt-br": "p",
}

# Voices whose name starts with the lang_code letter belong to that language (af_heart -> "a").
DEFAULT_VOICES = {
    "a": "af_heart",
    "b": "bf_emma",
    "e": "ef_dora",
    "f": "ff_siwis",
    "h": "hf_alpha",
    "i": "if_sara",
    "p": "pf_dora",
}

SAMPLE_RATE = 24000

REPO_ID = "hexgrad/Kokoro-82M"

_MODEL = None
_PIPELINES: dict = {}


def resolve_lang(language: str) -> str:
    key = (language or "en").strip().lower().replace("_", "-")
    code = LANG_CODES.get(key) or LANG_CODES.get(key.split("-")[0])
    if code is None:
        raise ValueError(f"Kokoro does not support language {language!r}; supported: {sorted(LANG_CODES)}. Use xtts-v2 for Russian.")
    return code


def resolve_voice(voice: str, lang_code: str) -> str:
    """A Kokoro voice name of the right language is used as is; anything else (default, alloy, ...)
    falls back to the language's default voice."""
    v = (voice or "").strip().lower()
    if len(v) > 3 and v[2] == "_" and v[0] == lang_code and v[1] in "fm":
        return v
    return DEFAULT_VOICES[lang_code]


def _device() -> str:
    wanted = os.environ.get("KOKORO_DEVICE", "auto")
    if wanted != "auto":
        return wanted
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _pipeline(lang_code: str):
    """One model on the device shared by per-language pipelines (each holds only its G2P)."""
    global _MODEL
    if lang_code not in _PIPELINES:
        from kokoro import KModel, KPipeline
        if _MODEL is None:
            _MODEL = KModel(repo_id=REPO_ID).to(_device()).eval()
        _PIPELINES[lang_code] = KPipeline(lang_code=lang_code, repo_id=REPO_ID, model=_MODEL)
    return _PIPELINES[lang_code]


def synthesize(text: str, voice: str = "default", language: str = "en", speed: float = 1.0) -> str:
    import numpy as np
    import soundfile as sf

    lang_code = resolve_lang(language)
    voice_name = resolve_voice(voice, lang_code)
    chunks = [r.audio.cpu().numpy() for r in _pipeline(lang_code)(text, voice=voice_name, speed=speed) if r.audio is not None]
    if not chunks:
        raise RuntimeError("TTS produced no audio")

    fd, output_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    sf.write(output_path, np.concatenate(chunks), SAMPLE_RATE)
    return output_path
