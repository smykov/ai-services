"""Which TTS worker gets a request.

xtts-v2 (tts-gpu) clones a voice and speaks Russian; kokoro (tts-kokoro) is ~15x faster with
preset voices and no Russian. The language list mirrors tts-kokoro/synthesizer.py.
"""
XTTS_QUEUE = "tts:queue"
KOKORO_QUEUE = "tts:kokoro:queue"

KOKORO_MODELS = {"kokoro", "kokoro-82m", "kokoro_82m"}
KOKORO_LANGUAGES = {"en", "es", "fr", "hi", "it", "pt"}


def is_kokoro(model: str | None) -> bool:
    return (model or "").strip().lower() in KOKORO_MODELS


def tts_queue(model: str | None, language: str | None, has_speaker_sample: bool = False) -> str:
    """Queue for the model; rejects requests Kokoro cannot serve before they reach a worker."""
    if not is_kokoro(model):
        return XTTS_QUEUE
    lang = (language or "en").strip().lower().replace("_", "-").split("-")[0]
    if lang not in KOKORO_LANGUAGES:
        raise ValueError(f"Model kokoro does not support language {language!r} (supported: {sorted(KOKORO_LANGUAGES)}); use xtts-v2")
    if has_speaker_sample:
        raise ValueError("Model kokoro has preset voices only; use xtts-v2 to clone a voice from speaker_wav")
    return KOKORO_QUEUE
