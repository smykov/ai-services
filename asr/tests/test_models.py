import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import DEFAULT_MODEL, resolve_model_name


def test_allowed_models_pass_through():
    assert resolve_model_name("turbo") == "turbo"
    assert resolve_model_name("large-v3") == "large-v3"


def test_aliases():
    assert resolve_model_name("whisper-1") == "turbo"
    assert resolve_model_name("large-v3-turbo") == "turbo"
    assert resolve_model_name("Large") == "large-v3"


def test_unknown_or_empty_falls_back_to_default():
    for name in (None, "", "medium", "small", "tiny.en", "nonsense"):
        assert resolve_model_name(name) == DEFAULT_MODEL
