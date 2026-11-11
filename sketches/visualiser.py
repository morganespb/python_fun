import os
import sys
import wave

import numpy as np
import pygame

from core.app import TEST_FRAMES
from core.audio import SR, Track
from core.draw import Canvas, text
from core.noise import noise3
from core.palette import BROWN, GREY, SILVER

# a ring of smoke that breathes with a track.
# space plays the built in loop. python main.py 11 song.wav plays your own (16 bit wav).


def read_wav(path):
    with wave.open(path) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels())
        rate = w.getframerate()
    mono = data.mean(1) / 32768
    return np.interp(np.arange(0, mono.size, rate / SR), np.arange(mono.size), mono)


class Visualiser:
    title = "Music Visualiser"
    hint = "space or click to play · add a .wav path to use your own"
    glow = 0.4
    BINS = 96

    def __init__(self, size):
        self.w, self.h = size
        self.track = Track(118)
        wav = next((a for a in sys.argv[2:] if a.endswith(".wav") and os.path.exists(a)), None)
        if wav:
            self.track.data = read_wav(wav)
            self.track.length = self.track.data.size / SR
        self.cv = Canvas(*size)
        self.bands = np.zeros(self.BINS)
        self.puffs, self.age = np.zeros((0, 4)), np.zeros(0)
        self.beat, self.t = -1, 0
        self.rng = np.random.default_rng(11)
        if TEST_FRAMES:
            self.track.toggle()

    def event(self, e):
        if (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE) or e.type == pygame.MOUSEBUTTONDOWN:
            self.track.toggle()

    def update(self, dt, mouse):
        self.t += dt
        on = self.track.playing
        target = self.track.spectrum(self.BINS) if on else 0.15 + 0.1 * noise3(np.arange(self.BINS) * 0.15, self.t * 0.5, 0)
        self.bands += (target - self.bands) * 0.35
        self.kick = self.track.kick if on else 0.0
        r0 = self.h * 0.2
        if on and int(self.track.beat) != self.beat:      # every beat sends a puff of smoke out
            self.beat = int(self.track.beat)
            a = self.rng.uniform(0, 2 * np.pi, 600)
            sp = self.rng.uniform(40, 160, 600) * (1 + self.bands[:8].mean())
            new = np.stack([self.w / 2 + np.cos(a) * r0, self.h / 2 + np.sin(a) * r0, np.cos(a) * sp, np.sin(a) * sp], 1)
            self.puffs = np.concatenate([self.puffs, new])[-7000:]
            self.age = np.concatenate([self.age, np.zeros(600)])[-7000:]
        if len(self.puffs):
            p = self.puffs
            curl = noise3(p[:, 0] * 0.006, p[:, 1] * 0.006, self.t * 0.3) * 4
            p[:, 2:] = (p[:, 2:] + np.stack([np.cos(curl), np.sin(curl)], 1) * 50 * dt) * 0.97
            p[:, :2] += p[:, 2:] * dt
            self.age += dt

    def draw(self, screen):
        cx, cy, r0 = self.w / 2, self.h / 2, self.h * 0.2
        self.cv.fade(0.12)
        if len(self.puffs):
            self.cv.splat(self.puffs[:, 0], self.puffs[:, 1], SILVER, np.clip(0.5 - self.age * 0.16, 0, 1))
        # the spectrum mirrored around the ring, 20 points along each spoke
        ang = np.concatenate([np.linspace(-np.pi / 2, np.pi / 2, self.BINS), np.linspace(np.pi / 2, 1.5 * np.pi, self.BINS)])
        mag = np.concatenate([self.bands, self.bands[::-1]])
        r = r0 * (1 + 0.12 * self.kick) + mag[:, None] * r0 * 1.4 * np.linspace(0, 1, 20)
        self.cv.splat(cx + np.cos(ang)[:, None] * r, cy + np.sin(ang)[:, None] * r, SILVER, 0.18)
        self.cv.blit(screen)
        pygame.draw.circle(screen, BROWN, (cx, cy), r0 * (0.9 + 0.08 * self.kick), 1)
        if not self.track.playing:
            text(screen, "space", (cx, cy), 26, GREY, italic=True, anchor="center")
