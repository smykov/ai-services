"""Which Whisper checkpoint a request gets.

Only a small set of checkpoints is served. Every other name, including the
OpenAI-style "whisper-1" sent by many clients, falls back to the default, so an
arbitrary request can never load yet another multi-gigabyte model onto the GPU.
"""

DEFAULT_MODEL = "turbo"
ALLOWED_MODELS = {"turbo", "large-v3"}
ALIASES = {
    "whisper-1": "turbo",
    "large-v3-turbo": "turbo",
    "large": "large-v3",
}


def resolve_model_name(name: str | None) -> str:
    key = (name or "").strip().lower()
    key = ALIASES.get(key, key)
    return key if key in ALLOWED_MODELS else DEFAULT_MODEL
