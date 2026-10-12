"""Which video frames carry speech.

Frames inside long silences do not need lip-sync: the worker shows prepared idle
frames there, which roughly halves the GPU time for training videos where every
phrase is followed by a pause.
"""
import numpy as np


def speech_frames(samples: np.ndarray, rate: int, fps: int, n_frames: int, threshold_db: float = -42.0,
                  window_s: float = 0.08, min_silence_frames: int = 8, pad_frames: int = 3) -> np.ndarray:
    """Return a bool array, True where frame i should be lip-synced.

    A frame is silent when the RMS of the audio around it is below `threshold_db` (dBFS).
    Silences shorter than `min_silence_frames` are treated as speech (pauses between words),
    and every speech run is widened by `pad_frames` so the mouth can open and close.
    """
    if n_frames <= 0:
        return np.zeros(0, dtype=bool)
    samples = samples.astype(np.float32)
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak > 1.0:
        samples = samples / 32768.0
    half = max(1, int(window_s * rate / 2))
    speech = np.zeros(n_frames, dtype=bool)
    for i in range(n_frames):
        c = int(i * rate / fps)
        seg = samples[max(0, c - half): c + half]
        if seg.size:
            rms = float(np.sqrt(np.mean(seg * seg)))
            speech[i] = rms > 0 and 20 * np.log10(rms) > threshold_db

    # Fill short silences (between words) so the mouth does not snap shut mid-phrase.
    i = 0
    while i < n_frames:
        if not speech[i]:
            j = i
            while j < n_frames and not speech[j]:
                j += 1
            bounded = i > 0 and j < n_frames
            if bounded and j - i < min_silence_frames:
                speech[i:j] = True
            i = j
        else:
            i += 1

    if pad_frames:
        padded = speech.copy()
        for i in np.flatnonzero(speech):
            padded[max(0, i - pad_frames): i + pad_frames + 1] = True
        speech = padded
    return speech


def cycle_index(i: int, n_source: int) -> int:
    """Index into the source frames played forward then backward (ping-pong), as MuseTalk does."""
    if n_source <= 1:
        return 0
    period = 2 * n_source
    k = i % period
    return k if k < n_source else period - 1 - k
