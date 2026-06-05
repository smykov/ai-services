import tempfile

_MODEL = None
_MODEL_NAME = None


def _load_model(name: str = "xtts-v2"):
    global _MODEL, _MODEL_NAME
    if _MODEL is None or _MODEL_NAME != name:
        if name == "xtts-v2":
            from TTS.api import TTS
            _MODEL = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
        _MODEL_NAME = name


def synthesize(text: str, voice: str = "default", model_name: str = "xtts-v2", language: str = "ru") -> str:
    _load_model(model_name)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output_path = f.name

    if model_name == "xtts-v2":
        _MODEL.tts_to_file(text=text, speaker_wav=voice, language=language, file_path=output_path)

    return output_path
