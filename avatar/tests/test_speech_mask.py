import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speech_mask import cycle_index, speech_frames

RATE, FPS = 16000, 25


def tone(seconds):
    t = np.arange(int(seconds * RATE)) / RATE
    return 0.3 * np.sin(2 * np.pi * 220 * t)


def silence(seconds):
    return np.zeros(int(seconds * RATE))


def frames(seconds):
    return int(round(seconds * FPS))


def test_long_silence_is_idle_and_speech_is_synced():
    audio = np.concatenate([tone(1), silence(2), tone(1)])
    mask = speech_frames(audio, RATE, FPS, frames(4), pad_frames=0)
    assert mask[:frames(1) - 2].all()
    assert not mask[frames(1) + 2: frames(3) - 2].any()
    assert mask[frames(3) + 2:].all()


def test_short_pause_between_words_stays_synced():
    audio = np.concatenate([tone(1), silence(0.12), tone(1)])
    mask = speech_frames(audio, RATE, FPS, frames(2.12), pad_frames=0)
    assert mask.all()


def test_padding_widens_speech():
    audio = np.concatenate([silence(1), tone(0.4), silence(1)])
    plain = speech_frames(audio, RATE, FPS, frames(2.4), pad_frames=0)
    padded = speech_frames(audio, RATE, FPS, frames(2.4), pad_frames=3)
    assert padded.sum() == plain.sum() + 6


def test_int16_samples_are_normalized():
    audio = (np.concatenate([tone(1), silence(1)]) * 32767).astype(np.int16)
    mask = speech_frames(audio, RATE, FPS, frames(2), pad_frames=0)
    assert mask[:frames(1) - 2].all() and not mask[frames(1) + 2:].any()


def test_empty():
    assert speech_frames(np.zeros(0), RATE, FPS, 0).size == 0


def test_cycle_index_ping_pong():
    assert [cycle_index(i, 3) for i in range(8)] == [0, 1, 2, 2, 1, 0, 0, 1]
    assert cycle_index(5, 1) == 0
