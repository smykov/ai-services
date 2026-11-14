import pytest
from app.core.tts import KOKORO_QUEUE, XTTS_QUEUE, tts_queue


@pytest.mark.parametrize("model", ["xtts-v2", "tts-1", "", None])
def test_xtts_queue(model):
    assert tts_queue(model, "ru") == XTTS_QUEUE


@pytest.mark.parametrize("model,lang", [("kokoro", "en"), ("Kokoro-82M", "en-GB"), ("kokoro", "pt_BR"), ("kokoro", None)])
def test_kokoro_queue(model, lang):
    assert tts_queue(model, lang) == KOKORO_QUEUE


def test_kokoro_without_russian():
    with pytest.raises(ValueError):
        tts_queue("kokoro", "ru")
