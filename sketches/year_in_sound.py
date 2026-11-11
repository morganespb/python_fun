import datetime
import math

import numpy as np
import pygame

from core.draw import text
from core.noise import noise3
from core.palette import BLACK, BROWN, GREY, SILVER, TAN

# a year of listening as one spiral. each tick is a day: length = minutes, tone = genre.
# EXAMPLE data. for yours: spotify > account > privacy > download your data.

GENRES = ["ambient", "jazz", "rap", "classical", "techno"]
TONE = {"ambient": (70, 64, 60), "jazz": (120, 114, 110), "rap": (160, 156, 154), "classical": SILVER, "techno": TAN}


def example_year():
    rng = np.random.default_rng(14)
    d = np.arange(365)
    summer = np.cos((d - 200) / 365 * 2 * np.pi)
    minutes = np.clip(50 + 60 * (noise3(d * 0.08, 0.5, 0.5) + 1) + 40 * (d % 7 >= 5) + 30 * summer + rng.normal(0, 15, 365), 5, 260)
    weights = np.clip(np.stack([1.4 - summer * 0.6, np.ones(365), np.ones(365), 1.2 - summer * 0.5, 0.7 + summer * 0.9], 1), 0.05, None)
    genres = [rng.choice(GENRES, p=w / w.sum()) for w in weights]
    return minutes, genres


class YearInSound:
    title = "Year in Sound"
    hint = "hover a day · p saves it as a picture"
    glow = 0.25

    def __init__(self, size):
        self.w, self.h = size
        self.minutes, self.genres = example_year()
        d = np.arange(365)
        self.angle = -np.pi / 2 + d / 365 * 2 * np.pi * 3          # three turns
        self.radius = self.h * (0.1 + 0.3 * d / 365)
        self.cx, self.cy = self.w * 0.56, self.h * 0.48
        self.base = np.stack([self.cx + np.cos(self.angle) * self.radius, self.cy + np.sin(self.angle) * self.radius], 1)
        self.pick = -1

    def update(self, dt, mouse):
        d = np.hypot(*(self.base - mouse.pos).T)
        self.pick = int(d.argmin()) if mouse.inside and d.min() < 14 else -1

    def draw(self, screen):
        screen.fill(BLACK)
        for i in range(365):
            a, r, n = self.angle[i], self.radius[i], 6 + self.minutes[i] * 0.16
            col = SILVER if i == self.pick else TONE[self.genres[i]]
            pygame.draw.line(screen, col, (self.cx + math.cos(a) * r, self.cy + math.sin(a) * r),
                             (self.cx + math.cos(a) * (r + n), self.cy + math.sin(a) * (r + n)), 2)
        text(screen, "2026", (80, 80), 64, SILVER, italic=True)
        text(screen, f"{int(self.minutes.sum() / 60)} hours", (82, 156), 20, GREY)
        for k, g in enumerate(GENRES):
            pygame.draw.line(screen, TONE[g], (82, 222 + k * 26), (104, 222 + k * 26), 2)
            text(screen, g, (114, 222 + k * 26), 18, GREY, anchor="midleft")
        text(screen, "example data", (82, 360), 16, BROWN, italic=True)
        if self.pick >= 0:
            day = datetime.date(2026, 1, 1) + datetime.timedelta(days=self.pick)
            m = int(self.minutes[self.pick])
            text(screen, f"{day:%d %B}, {m // 60}h{m % 60:02d}, {self.genres[self.pick]}", (82, 420), 22, SILVER, italic=True)
