import whisper

MODELS: dict[str, whisper.Whisper] = {}
MODEL_NAMES = {"large-v3", "turbo"}


def get_model(name: str = "turbo") -> whisper.Whisper:
    if name not in MODELS:
        MODELS[name] = whisper.load_model(name)
    return MODELS[name]


def transcribe(audio_path: str, language: str = "auto", model_name: str = "turbo") -> dict:
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

    result = model.transcribe(audio_path, **opts)
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
