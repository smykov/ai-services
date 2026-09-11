import os
import tempfile
import urllib.request

os.environ["COQUI_TOS_AGREED"] = "1"

_MODEL = None
_MODEL_NAME = None
_DEFAULT_VOICE_PATH = None


def _download_default_voice():
    global _DEFAULT_VOICE_PATH
    if _DEFAULT_VOICE_PATH is not None:
        return _DEFAULT_VOICE_PATH
    url = "https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/en_sample.wav"
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    urllib.request.urlretrieve(url, tmp.name)
    _DEFAULT_VOICE_PATH = tmp.name
    return _DEFAULT_VOICE_PATH


MODEL_ALIASES = {
    "": "xtts-v2",
    "default": "xtts-v2",
    "tts-1": "xtts-v2",
    "tts-1-hd": "xtts-v2",
    "xtts": "xtts-v2",
    "xtts-v2": "xtts-v2",
    "xtts_v2": "xtts-v2",
}


def resolve_model(name: str) -> str:
    """Map client-supplied model names (incl. OpenAI's tts-1) onto a real backend."""
    resolved = MODEL_ALIASES.get((name or "").strip().lower())
    if resolved is None:
        raise ValueError(
            f"Unknown TTS model {name!r}; supported: {sorted(set(MODEL_ALIASES) - {''})}"
        )
    return resolved


def _load_model(name: str = "xtts-v2"):
    global _MODEL, _MODEL_NAME
    if _MODEL is None or _MODEL_NAME != name:
        if name == "xtts-v2":
            from TTS.api import TTS
            _MODEL = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
        _MODEL_NAME = name


def synthesize(text: str, voice: str = "default", model_name: str = "xtts-v2", language: str = "ru") -> str:
    model_name = resolve_model(model_name)
    _load_model(model_name)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output_path = f.name

    # OpenAI-style voice names (alloy, nova, ...) are not speaker samples - only an
    # existing wav path is used as a reference voice, anything else falls back.
    speaker_wav = voice if voice and os.path.isfile(voice) else _download_default_voice()
    _MODEL.tts_to_file(text=text, speaker_wav=speaker_wav, language=language, file_path=output_path)

    if os.path.getsize(output_path) == 0:
        os.unlink(output_path)
        raise RuntimeError("TTS produced an empty audio file")

    return output_path
