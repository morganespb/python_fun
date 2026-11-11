import numpy as np

from core.draw import Canvas, project, text
from core.noise import fbm, smoothstep
from core.palette import BROWN, GREY, SILVER
from core.scroll import Scroll

# cendre no.3 is a made up perfume
CHAPTERS = [(0.0, "cendre no. 3"), (0.3, "smoke, iris, cold air"), (0.6, "burnt cedar"), (0.85, "spring 2027")]


def box(n, sx, sy, sz, rng):
    """random points on the outside of a box"""
    p = (rng.random((n, 3)) - 0.5) * [sx, sy, sz]
    sides = np.array([sy * sz, sx * sz, sx * sy])
    axis = rng.choice(3, n, p=sides / sides.sum())
    p[np.arange(n), axis] = np.where(rng.random(n) < 0.5, -0.5, 0.5) * np.array([sx, sy, sz])[axis]
    return p


class ProductLaunch:
    title = "Product Launch"
    hint = "scroll to turn and open the bottle"
    glow = 0.35

    def __init__(self, size):
        self.w, self.h = size
        rng = np.random.default_rng(2)
        self.body = box(5000, 0.62, 0.86, 0.34, rng) + [0, 0.12, 0]
        a = rng.random(600) * 2 * np.pi
        self.neck = np.stack([0.09 * np.cos(a), -0.32 - rng.random(600) * 0.1, 0.09 * np.sin(a)], 1)
        self.cap = box(1000, 0.3, 0.24, 0.3, rng) + [0, -0.55, 0]
        self.liquid = (rng.random((1200, 3)) - 0.5) * [0.56, 0.5, 0.28] + [0, 0.3, 0]
        self.seed = rng.random((1800, 3))
        self.cv = Canvas(*size)
        self.scroll, self.t = Scroll(0.045), 0

    def event(self, e):
        self.scroll.event(e)

    def update(self, dt, mouse):
        self.t += dt
        self.p = self.scroll.update(dt)

    def draw(self, screen):
        p, t = self.p, self.t
        turn = 0.4 + p * np.pi * 1.6
        view = dict(ry=turn, rx=0.18, scale=self.h * 0.5, cx=self.w / 2, cy=self.h * 0.5)
        cap = self.cap - [0, smoothstep(0.3, 0.6, p) * 0.5, 0]   # the cap lifts
        self.cv.fade(0.4)
        for pts, a in ((self.body, 0.7), (self.neck, 0.8), (cap, 0.9)):
            x, y, z = project(pts, **view)
            self.cv.splat(x, y, SILVER, a * (0.4 + 0.6 * (z + 0.5)))
        x, y, z = project(self.liquid, **view)
        self.cv.splat(x, y, BROWN, 0.9)
        # smoke leaves the open neck
        s = smoothstep(0.45, 0.8, p)
        if s > 0:
            life = (t * 0.22 + self.seed[:, 0]) % 1
            drift = fbm(self.seed[:, 1] * 3, life * 2, t * 0.2, 2) * life
            smoke = np.stack([drift * 0.9, -0.42 - life * 1.4 * s, drift * 0.5], 1)
            x, y, z = project(smoke, **view)
            self.cv.splat(x, y, SILVER, s * (1 - life) * 0.4)
        self.cv.blit(screen)
        words = [c[1] for c in CHAPTERS if p >= c[0] - 0.02][-1]
        text(screen, words, (60, self.h * 0.5), 34, SILVER, italic=True, anchor="midleft")
        text(screen, f"{int(p * 100)}", (self.w - 60, self.h * 0.5), 18, GREY, anchor="midright")
