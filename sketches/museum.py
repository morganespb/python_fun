import math

import numpy as np
import pygame

from core.draw import Canvas, project, text
from core.palette import GREY, SILVER, TAN

GROWTH, TURNS = 0.19, 5.5 * math.pi


def shell(u, v):
    # a cone shell: u runs along the spiral, v around the tube
    a = 0.05 * np.exp(GROWTH * u)
    r = a * 0.75
    return np.stack([(a + r * np.cos(v)) * np.cos(u), -a * 1.9 + r * np.sin(v), (a + r * np.cos(v)) * np.sin(u)], -1)


NOTES = [(TURNS * 0.985, 0.0, "aperture", "where the animal lived"),
         (TURNS * 0.6, 1.6, "body whorl", "each turn 1.8× wider than the last"),
         (0.6, 0.0, "apex", "the oldest part")]


class Museum:
    title = "Museum of One Object"
    hint = "drag to turn · hover the rings"
    glow = 0.3

    def __init__(self, size):
        self.w, self.h = size
        rng = np.random.default_rng(4)
        n = 16000
        # more points on the big late turns, so the density looks even
        u = np.log1p(rng.random(n) * (np.exp(2 * GROWTH * TURNS) - 1)) / (2 * GROWTH)
        pts = shell(u, rng.random(n) * 2 * np.pi)
        notes = np.array([shell(np.array(a), np.array(b)) for a, b, *_ in NOTES])
        lo, hi = pts.min(0), pts.max(0)
        mid, s = (lo + hi) / 2, 2.2 / (hi - lo).max()
        self.pts, self.notes = (pts - mid) * s, (notes - mid) * s
        self.ry, self.rx, self.spin, self.t = 0.6, 0.35, 0.0, 0
        self.cv = Canvas(*size)

    def update(self, dt, mouse):
        self.t += dt
        if mouse.down:
            self.spin = mouse.vx * 0.01
            self.rx = float(np.clip(self.rx + mouse.vy * 0.01, -1.2, 1.2))
        else:
            self.spin += (0.004 - self.spin) * 0.03      # drift back to a slow turn
        self.ry += self.spin
        self.mouse = mouse

    def draw(self, screen):
        view = dict(ry=self.ry, rx=self.rx, scale=self.h * 0.32, cx=self.w / 2, cy=self.h / 2)
        x, y, z = project(self.pts, **view)
        self.cv.fade(0.5)
        self.cv.splat(x, y, SILVER, 0.18 + 0.45 * (z + 1.1) / 2.2)
        self.cv.blit(screen)
        nx, ny, nz = project(self.notes, **view)
        d = np.hypot(nx - self.mouse.x, ny - self.mouse.y)
        pick = int(d.argmin()) if d.min() < 26 else (int(self.t / 3) % 3 if self.mouse.idle > 3 else -1)
        for i in range(3):
            pygame.draw.circle(screen, TAN, (nx[i], ny[i]), 9 if i == pick else 5, 1)
        if pick >= 0:
            name, line = NOTES[pick][2:]
            r = text(screen, name, (nx[pick] + 20, ny[pick] - 22), 26, SILVER, italic=True)
            text(screen, line, (r.x, r.bottom), 17, GREY)
        text(screen, "no. 017 — cone shell", (self.w - 40, 36), 18, GREY, anchor="topright")
