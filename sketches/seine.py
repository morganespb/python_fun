import numpy as np
import pygame

from core.draw import text
from core.noise import noise3
from core.palette import BLACK, BROWN, GREY, SILVER

# the seine's water level as one living ring. each day is a ring, old days fade like tree rings.
# these numbers are SAMPLE data shaped like a winter flood. real data: hub'eau api
# (hubeau.eaufrance.fr, "hydrometrie"), station paris-austerlitz.

DAYS = 90


def sample_levels():
    d = np.arange(DAYS)
    flood = 3.0 * np.exp(-((d - 48) / 7) ** 2) + 0.6 * np.exp(-((d - 70) / 4) ** 2)
    return 1.3 + 0.25 * np.sin(d / 9) + flood + np.random.default_rng(13).normal(0, 0.05, DAYS)


class Seine:
    title = "The Seine Breathing"
    hint = "move the mouse left and right to go through the days"
    glow = 0.3

    def __init__(self, size):
        self.w, self.h = size
        self.level = sample_levels()
        self.day, self.t = 0.0, 0

    def update(self, dt, mouse):
        self.t += dt
        if mouse.inside and mouse.idle < 3:
            self.day += (mouse.x / self.w * (DAYS - 1) - self.day) * 0.15
        else:
            self.day = (self.day + dt * 5) % DAYS

    def ring(self, level, seed):
        a = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        r = self.h * (0.06 + level * 0.06) * (1 + 0.09 * noise3(np.cos(a) * 1.4 + seed, np.sin(a) * 1.4, self.t * 0.25 + seed))
        return np.stack([self.w / 2 + np.cos(a) * r, self.h * 0.45 + np.sin(a) * r * 0.82], 1)

    def draw(self, screen):
        screen.fill(BLACK)
        d = int(self.day)
        for back in range(24, 0, -1):
            if d - back >= 0:
                c = int(18 + 70 * (1 - back / 24))
                pygame.draw.aalines(screen, (c, c - 4, c - 8), True, self.ring(self.level[d - back], (d - back) * 0.37))
        high = self.level[d] > 3.5
        now = self.ring(self.level[d], d * 0.37)
        for k in (0, 1):                           # a slightly thicker line for today
            pygame.draw.aalines(screen, BROWN if high else SILVER, True, now + k * 0.6)
        text(screen, f"{self.level[d]:.2f} m", (self.w / 2, self.h * 0.45), 44, BROWN if high else SILVER, italic=True, anchor="center")
        # the whole season as one thin line at the bottom
        x0, x1, base = 120, self.w - 120, self.h * 0.86
        pts = [(x0 + i / (DAYS - 1) * (x1 - x0), base - v / 5 * 70) for i, v in enumerate(self.level)]
        pygame.draw.aalines(screen, GREY, False, pts)
        pygame.draw.circle(screen, SILVER, pts[d], 3)
        text(screen, f"day {d + 1}", (x1, base + 14), 17, GREY, anchor="topright")
        text(screen, "sample data", (x0, base + 14), 17, GREY, italic=True)
