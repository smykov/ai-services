import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from synthesizer import resolve_lang, resolve_voice


@pytest.mark.parametrize("lang,code", [
    ("en", "a"), ("EN-US", "a"), ("en-GB", "b"), ("en_gb", "b"), ("pt-BR", "p"), ("fr-CA", "f"), ("", "a"),
])
def test_resolve_lang(lang, code):
    assert resolve_lang(lang) == code


@pytest.mark.parametrize("lang", ["ru", "ru-RU", "ja", "zh", "de"])
def test_unsupported_language(lang):
    with pytest.raises(ValueError, match="does not support"):
        resolve_lang(lang)


def test_resolve_voice():
    assert resolve_voice("am_michael", "a") == "am_michael"
    assert resolve_voice("default", "a") == "af_heart"
    assert resolve_voice("alloy", "b") == "bf_emma"
    # A voice of another language falls back instead of mispronouncing the text.
    assert resolve_voice("af_heart", "e") == "ef_dora"
