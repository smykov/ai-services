import gc

import torch
import whisper
from models import resolve_model_name

# One checkpoint stays on the GPU at a time: switching models unloads the previous one,
# otherwise every checkpoint ever requested would stay resident (large-v3 alone is ~6 GB).
_loaded: tuple[str, whisper.Whisper] | None = None


def get_model(name: str | None = None) -> whisper.Whisper:
    global _loaded
    name = resolve_model_name(name)
    if _loaded and _loaded[0] == name:
        return _loaded[1]
    if _loaded:
        _loaded = None
        gc.collect()
        _release_cache()
    _loaded = (name, whisper.load_model(name))
    return _loaded[1]


def _release_cache():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def transcribe(audio_path: str, language: str = "auto", model_name: str | None = None) -> dict:
    model = get_model(model_name)
    opts = {
        "condition_on_previous_text": False,
        "temperature": 0.0,
        "no_speech_threshold": 0.6,
        "logprob_threshold": -1.0,
        "compression_ratio_threshold": 2.4,
    }
    if language != "auto":
        opts["language"] = language

    try:
        result = model.transcribe(audio_path, **opts)
    finally:
        # Long recordings leave gigabytes in PyTorch's cache; hand them back to other GPU workers.
        _release_cache()
    return {
        "text": result.get("text", "").strip(),
        "segments": [
            {
                "start": s.get("start"),
                "end": s.get("end"),
                "text": s.get("text", "").strip(),
            }
            for s in result.get("segments", [])
        ],
        "language": result.get("language", language),
    }
