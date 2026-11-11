import os
import sys

import numpy as np
import pygame

from core.draw import Canvas
from core.noise import fbm
from core.palette import BROWN, DEEP, SILVER, TAN

S = 170     # the image is sampled at S x S points


def eclipse():
    """a made up picture so no file is needed: an eclipse over still water"""
    s = pygame.Surface((S, S))
    c = S // 2
    for r in range(52, 34, -1):                      # the glow around the moon
        k = (52 - r) / 18
        pygame.draw.circle(s, tuple(int(v * k) for v in TAN), (c, c - 14), r)
    pygame.draw.circle(s, DEEP, (c, c - 14), 35)
    for x, y, r in ((c - 11, c - 22, 6), (c + 10, c - 4, 4), (c + 2, c - 30, 3)):
        pygame.draw.circle(s, BROWN, (x, y), r)
    for y in range(c + 40, S):                       # water, with the reflection in silver lines
        k = (y - c - 40) / (S - c - 40)
        pygame.draw.line(s, (int(30 + 30 * k),) * 3, (0, y), (S, y))
        if y % 3 == 0:
            half = int(18 * (1 - k * 0.5))
            pygame.draw.line(s, SILVER, (c - half, y), (c + half, y))
    return s


class ImageDissolve:
    title = "Image Dissolve"
    hint = "hover to push · click to turn it to smoke · python main.py 6 photo.jpg uses your photo"
    glow = 0.35

    def __init__(self, size):
        self.w, self.h = size
        path = next((a for a in sys.argv[2:] if os.path.exists(a)), None)
        img = pygame.transform.smoothscale(pygame.image.load(path), (S, S)) if path else eclipse()
        rgb = pygame.surfarray.array3d(img).astype(np.float32)
        ix, iy = np.nonzero(rgb.sum(2) > 25)        # skip the black
        self.col = rgb[ix, iy]
        cell = self.h * 0.82 / S
        self.home = np.stack([self.w / 2 + (ix - S / 2) * cell, self.h / 2 + (iy - S / 2) * cell], 1)
        self.p, self.v = self.home.copy(), np.zeros_like(self.home)
        self.rise = np.random.default_rng(8).random(len(self.p))
        self.smoke, self.t = 0.0, 0
        self.cv = Canvas(*size)

    def event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            self.smoke = 2.2

    def update(self, dt, mouse):
        self.t += dt
        p, v = self.p, self.v
        if self.smoke > 0:
            self.smoke -= dt
            angle = fbm(p[:, 0] * 0.006, p[:, 1] * 0.006, self.t * 0.3, 2) * 6
            v += np.stack([np.cos(angle) * 60, np.sin(angle) * 60 - 90 * (0.5 + self.rise)], 1) * dt
            v *= 0.985
        else:
            v += (self.home - p) * 9 * dt            # spring back home
            v *= 0.9
        if mouse.inside:
            d = p - mouse.pos
            dist = np.hypot(*d.T) + 1e-3
            v += d / dist[:, None] * (np.clip(1 - dist / 90, 0, 1) ** 2 * 1800 * dt)[:, None]
        p += v * dt

    def draw(self, screen):
        self.cv.fade(0.5)
        away = np.hypot(*(self.p - self.home).T)
        self.cv.splat(self.p[:, 0], self.p[:, 1], self.col, np.clip(1.6 - away / 300, 0.25, 1.6))
        self.cv.blit(screen)
