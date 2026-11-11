import os

import numpy as np
import pygame

from core.app import ROOT
from core.draw import Canvas, text
from core.noise import fbm, smoothstep
from core.palette import BLACK, DEEP, GREY, SILVER, TAN

# a 24 second film in three acts:
#   i breath    a cloud breathes alone
#   ii beings   it gathers into two figures, close enough to kiss
#   iii release they rise apart and scatter
# r renders it frame by frame into output/film/, then:
#   ffmpeg -framerate 30 -i output/film/%04d.png -pix_fmt yuv420p film.mp4

LENGTH = 24.0
ACTS = [(0, "i  breath"), (8, "ii  beings"), (16, "iii  release")]


def two_figures(n, rng):
    """points inside a simple drawing of two people facing each other, heads touching"""
    s = pygame.Surface((200, 200))
    white = (255, 255, 255)
    for x, facing in ((80, 1), (122, -1)):
        pygame.draw.circle(s, white, (x + facing * 7, 44), 13)                       # head
        pygame.draw.rect(s, white, (x - 4, 54, 8, 14))                                # neck
        pygame.draw.polygon(s, white, [(x - 21, 68), (x + 21, 68), (x + 14, 128), (x - 14, 128)])   # body
        pygame.draw.ellipse(s, white, (x - 13, 122, 12, 72))                          # legs
        pygame.draw.ellipse(s, white, (x + 1, 122, 12, 72))
        pygame.draw.line(s, white, (x + facing * 16, 74), (x + facing * 40, 98), 7)   # arm reaching over
    xs, ys = np.nonzero(pygame.surfarray.array3d(s)[:, :, 0])
    pick = rng.integers(0, xs.size, n)
    return (np.stack([xs[pick], ys[pick]], 1) + rng.random((n, 2)) - 100) / 100


class ShortFilm:
    title = "Short Film"
    hint = "click below the film to jump · r renders it"
    glow = 0.4

    def __init__(self, size):
        self.w, self.h = size
        rng = np.random.default_rng(17)
        n = 11000
        self.seed = rng.random((n, 3))
        self.cloud = rng.normal(0, 0.35, (n, 2))
        self.people = two_figures(n, rng)
        self.heart = np.hypot(self.people[:, 0], self.people[:, 1] + 0.56) < 0.1     # where the faces meet
        self.film_h = int(self.w / 2.39)                 # cinema shape
        self.top = (self.h - self.film_h) // 2
        self.cv = Canvas(*size)
        self.t = float(os.environ.get("FILM_T", 0))
        self.frame = None

    def event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.pos[1] > self.top + self.film_h:
            self.t = e.pos[0] / self.w * LENGTH
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_r:
            self.t, self.frame = 0.0, 0
            os.makedirs(os.path.join(ROOT, "output", "film"), exist_ok=True)
            self.cv.clear()

    def update(self, dt, mouse):
        if self.frame is not None:
            dt = 1 / 30                                 # fixed steps: the same film every time
        self.t = (self.t + dt) % LENGTH

    def draw(self, screen):
        t = self.t
        drift = np.stack([fbm(self.seed[:, 0] * 4, t * 0.15, 1, 2), fbm(self.seed[:, 1] * 4, t * 0.15, 2, 2)], 1)
        meet = smoothstep(8, 11.5, t)
        part = smoothstep(16, 22, t)
        pos = (self.cloud * (1 + 0.08 * np.sin(t * 1.3)) + drift * 0.25) * (1 - meet) + (self.people + drift * 0.03) * meet
        pos += drift * part * 0.9 + np.stack([np.sign(self.people[:, 0]) * part * 0.4, -part ** 2 * (0.6 + self.seed[:, 2])], 1)
        x = self.w / 2 + pos[:, 0] * self.film_h * 0.42
        y = self.top + self.film_h * 0.52 + pos[:, 1] * self.film_h * 0.42
        light = 1 - smoothstep(19, 22, t)
        warm = self.heart & (meet > 0.5)
        self.cv.fade(0.3)
        self.cv.splat(x[~warm], y[~warm], SILVER, (0.4 + 0.15 * self.seed[~warm, 2]) * light)
        self.cv.splat(x[warm], y[warm], TAN, meet * (1 - part) * light * 1.4)
        self.cv.blit(screen)
        screen.fill(BLACK, (0, 0, self.w, self.top))
        screen.fill(BLACK, (0, self.top + self.film_h, self.w, self.h))
        for start, name in ACTS:
            if start <= t < start + 3:
                text(screen, name, (60, self.top + self.film_h - 50), 24, SILVER, italic=True, alpha=255 * min(1, (t - start) * 2, start + 3 - t))
        if t > 21.5:
            text(screen, "resonant", (self.w / 2, self.top + self.film_h / 2), 64, SILVER, italic=True, anchor="center",
                 alpha=255 * min(1, (t - 21.5) * 2, (LENGTH - t) * 2))
        if self.frame is not None:
            pygame.image.save(screen.subsurface((0, self.top, self.w, self.film_h)), os.path.join(ROOT, "output", "film", f"{self.frame:04d}.png"))
            self.frame += 1
            text(screen, f"rendering {self.frame} / {int(LENGTH * 30)}", (self.w - 40, 30), 18, GREY, anchor="topright")
            if self.frame >= LENGTH * 30:
                self.frame = None
        # the timeline
        y = self.top + self.film_h + 40
        for start, _ in ACTS:
            pygame.draw.line(screen, DEEP, (start / LENGTH * self.w + 3, y), ((start + 8) / LENGTH * self.w - 3, y), 2)
        pygame.draw.line(screen, SILVER, (0, y), (t / LENGTH * self.w, y), 2)
