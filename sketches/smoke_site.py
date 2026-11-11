import numpy as np

from core.draw import Canvas, project, text
from core.noise import noise3, smoothstep
from core.palette import GREY, SILVER, TAN
from core.scroll import Scroll

PROJECTS = ["resonant dust", "flow fields", "ink drift", "say hello"]


def shapes(r):
    # four shapes for the same points: sphere, ring, spiral, disc
    a, b, c = r[:, 0], r[:, 1], r[:, 2]
    th, ph = a * 2 * np.pi, np.arccos(2 * b - 1)
    sphere = np.stack([np.sin(ph) * np.cos(th), np.cos(ph), np.sin(ph) * np.sin(th)], 1) * (1 + 0.1 * (c - 0.5))[:, None]
    u, v = a * 2 * np.pi, b * 2 * np.pi
    ring = np.stack([(0.85 + 0.3 * np.cos(v)) * np.cos(u), 0.3 * np.sin(v), (0.85 + 0.3 * np.cos(v)) * np.sin(u)], 1)
    r_ = 0.6 + (b - 0.5) * 0.3
    spiral = np.stack([r_ * np.cos(u * 3), (a - 0.5) * 2.3, r_ * np.sin(u * 3)], 1)
    d = np.sqrt(a) * 1.25
    disc = np.stack([d * np.cos(v + d * 3.5), (c - 0.5) * 0.08, d * np.sin(v + d * 3.5)], 1)
    return [sphere, ring, spiral, disc]


class SmokeSite:
    title = "Smoke Site"
    hint = "scroll with the wheel or arrows, or leave it to play"
    glow = 0.35

    def __init__(self, size):
        self.w, self.h = size
        r = np.random.default_rng(1).random((12000, 4))
        self.shapes = shapes(r)
        self.accent = r[:, 3] < 0.04
        self.cv = Canvas(*size)
        self.scroll, self.t = Scroll(), 0

    def event(self, e):
        self.scroll.event(e)

    def update(self, dt, mouse):
        self.t += dt
        self.p = self.scroll.update(dt)

    def draw(self, screen):
        k = self.p * 3
        i = min(int(k), 2)
        f = smoothstep(0.15, 0.85, k - i)              # morph between two shapes
        pts = self.shapes[i] * (1 - f) + self.shapes[i + 1] * f
        pts *= 1 + 0.05 * noise3(pts[:, 0] * 2, pts[:, 1] * 2, self.t * 0.3)[:, None]
        x, y, z = project(pts, self.t * 0.15 + self.p * 2.2, 0.35, self.h * 0.3, self.w / 2, self.h * 0.46)
        self.cv.fade(0.35)
        a = 0.25 + 0.5 * (z + 1.2) / 2.4
        self.cv.splat(x[~self.accent], y[~self.accent], SILVER, a[~self.accent])
        self.cv.splat(x[self.accent], y[self.accent], TAN, 0.9)
        self.cv.blit(screen)
        # the page: just the project name under the form, and an index on the right
        now = min(int(self.p * 3 + 0.5), 3)
        text(screen, PROJECTS[now], (self.w / 2, self.h * 0.86), 30, SILVER, italic=True, anchor="center")
        for j, name in enumerate(PROJECTS):
            text(screen, f"0{j + 1}", (self.w - 40, self.h / 2 - 60 + j * 34), 18, SILVER if j == now else GREY,
                 anchor="midright", alpha=255 if j == now else 120)
