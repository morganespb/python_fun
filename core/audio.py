import time

import numpy as np
import pygame

# a tiny synth: everything is drawn into numpy arrays, then played by pygame

SR = 44100


def secs(d):
    return np.arange(int(SR * d)) / SR


def lowpass(x, cutoff):
    n = max(1, int(SR / cutoff))
    c = np.cumsum(np.concatenate([np.zeros(n), x]))
    return (c[n:] - c[:-n]) / n


def hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def kick():
    t = secs(0.45)
    pitch = 42 + 110 * np.exp(-t * 32)          # fast drop = punch
    return np.sin(2 * np.pi * np.cumsum(pitch) / SR) * np.exp(-t * 7)


def hat(d=0.07, seed=0):
    n = np.random.default_rng(seed).uniform(-1, 1, int(SR * d))
    return np.diff(n, prepend=0) * np.exp(-secs(d) * 70) * 0.35


def bass(f, d=0.32):
    t = secs(d)
    saw = 2 * ((t * f) % 1) - 1
    return lowpass(saw, 380) * np.minimum(1, t * 200) * np.exp(-t * 6) * 0.55


def pluck(f, d=0.8):
    t = secs(d)
    tone = 0.7 * np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 9)
    return tone * np.minimum(1, t * 400) * np.exp(-t * 5) * 0.4


def pad(freqs, d):
    t = secs(d)
    s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.01 * t) for f in freqs)
    return s * np.minimum(1, t / 0.8) * np.minimum(1, (d - t) / 0.8) * 0.05


def sound(mono, pan=0.0, gain=1.0):
    """numpy array -> pygame sound. none if there is no audio device"""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(SR, -16, 2, 512)
    except pygame.error:
        return None
    m = np.clip(mono * gain, -1, 1)
    st = np.stack([m * np.sqrt(0.5 - pan / 2), m * np.sqrt(0.5 + pan / 2)], 1)
    return pygame.sndarray.make_sound(np.ascontiguousarray((st * 32000).astype(np.int16)))


def groove(bpm=120, bars=8):
    """an 8 bar loop in a minor: kick, hats, bass, soft pad"""
    step = 60 / bpm / 4
    out = np.zeros(int(SR * step * 16 * bars) + SR)
    chords = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62])]

    def add(sig, at):
        i = int(at * SR)
        out[i:i + sig.size] += sig[:max(0, out.size - i)]

    k = kick()
    for b in range(bars):
        root, chord = chords[b % 4]
        add(pad([hz(n) for n in chord], step * 16), b * 16 * step)
        for s in range(16):
            at = (b * 16 + s) * step
            if s % 4 == 0:
                add(k, at)
            if s % 4 == 2:
                add(hat(seed=s + b), at)
            elif s % 2:
                add(hat(0.03, s * 7 + b) * 0.5, at)
            if s in (0, 3, 6, 10, 11, 14):
                add(bass(hz(root + (12 if s == 14 else 0))), at)
    out = out[:int(SR * step * 16 * bars)]
    return out / np.abs(out).max() * 0.9


class Track:
    """a looping track with a clock, so visuals stay on the beat even when muted"""

    def __init__(self, bpm=120):
        self.bpm, self.data = bpm, groove(bpm)
        self.length = self.data.size / SR
        self.snd, self.playing, self.t0 = None, False, time.perf_counter()

    def toggle(self):
        if self.playing:
            self.snd and self.snd.stop()
        else:
            self.snd = self.snd or sound(self.data)
            self.snd and self.snd.play(loops=-1)
            self.t0 = time.perf_counter()
        self.playing = not self.playing

    @property
    def pos(self):
        return (time.perf_counter() - self.t0) % self.length

    @property
    def beat(self):
        return self.pos * self.bpm / 60

    @property
    def kick(self):
        return float(np.exp(-(self.beat % 1) * 6))   # 1 on the beat, then fades

    def spectrum(self, bins=64, size=2048):
        i = int(self.pos * SR)
        seg = np.resize(np.roll(self.data, -i)[:size], size)
        mag = np.abs(np.fft.rfft(seg * np.hanning(size)))[1:]
        edges = np.unique(np.geomspace(1, mag.size, bins + 1).astype(int))  # like the ear: log spaced
        bands = np.log1p([mag[a:b].mean() for a, b in zip(edges[:-1], edges[1:])]) / 5
        return np.clip(np.pad(bands, (0, bins - len(bands))), 0, 1)
