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
        speaker_wav = _download_default_voice() if voice == "default" else voice
        _MODEL.tts_to_file(text=text, speaker_wav=speaker_wav, language=language, file_path=output_path)

    return output_path

