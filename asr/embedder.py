"""Speaker embeddings (ECAPA-TDNN) for diarizing live sessions client-side.

Returns a normalized voice vector per audio chunk; callers cluster the vectors
themselves, which keeps speaker identity stable across an ongoing call without
the service holding any session state.
"""
import torch
import torchaudio

_MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
_CACHE_DIR = "/models/ecapa"
_TARGET_RATE = 16000

# Below this, ECAPA vectors are too unstable to identify a speaker.
MIN_RELIABLE_SECONDS = 1.0

_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        from speechbrain.inference.speaker import EncoderClassifier

        _classifier = EncoderClassifier.from_hparams(
            source=_MODEL_SOURCE,
            savedir=_CACHE_DIR,
            run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"},
        )
    return _classifier


def embed(audio_path: str) -> dict:
    """Compute an L2-normalized speaker embedding for a single-speaker chunk."""
    waveform, rate = torchaudio.load(audio_path)

    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    if rate != _TARGET_RATE:
        waveform = torchaudio.functional.resample(waveform, rate, _TARGET_RATE)

    seconds = waveform.shape[1] / _TARGET_RATE

    classifier = _get_classifier()
    with torch.no_grad():
        vector = classifier.encode_batch(waveform).squeeze()
    vector = torch.nn.functional.normalize(vector, dim=0)

    return {
        "embedding": [round(v, 6) for v in vector.cpu().tolist()],
        "seconds": round(seconds, 3),
        "reliable": seconds >= MIN_RELIABLE_SECONDS,
    }
