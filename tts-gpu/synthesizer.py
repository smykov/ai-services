import tempfile

MODEL = None
MODEL_NAME = None


def load_model(name: str = "xtts-v2"):
    global MODEL, MODEL_NAME
    if MODEL is None or MODEL_NAME != name:
        if name == "xtts-v2":
            from TTS.api import TTS
            MODEL = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
        MODEL_NAME = name


def synthesize(text: str, voice: str = "default", model_name: str = "xtts-v2") -> str:
    load_model(model_name)

    output_path = tempfile.mktemp(suffix=".wav")

    if model_name == "xtts-v2":
        MODEL.tts_to_file(text=text, speaker_wav=voice, language="ru", file_path=output_path)

    return output_path
