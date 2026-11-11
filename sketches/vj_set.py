import math

import numpy as np
import pygame

from core.audio import Track
from core.draw import font, text
from core.noise import noise3
from core.palette import BLACK, BROWN, GREY, SILVER

# four scenes you switch live. they follow the beat clock even with the sound off,
# so you can rehearse in silence. it changes scene by itself every 8 beats.

SCENES = ["tunnel", "grid", "echo", "type"]


def dim(col, k):
    return tuple(int(c * max(0, min(1, k))) for c in col)


class VJSet:
    title = "VJ Set"
    hint = "space for sound · 1 2 3 4 to switch scene"
    glow = 0.45

    def __init__(self, size):
        self.w, self.h = size
        self.track = Track(124)
        self.scene, self.hold = 0, -1
        self.canvas = pygame.Surface(size)
        self.word = font(300, italic=True).render("brume", True, SILVER)
        self.t = 0

    def event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                self.track.toggle()
            elif pygame.K_1 <= e.key <= pygame.K_4:
                self.scene, self.hold = e.key - pygame.K_1, self.t + 8

    def update(self, dt, mouse):
        self.t += dt
        self.beat, self.kick = self.track.beat, self.track.kick
        if self.t > self.hold:
            self.scene = int(self.beat // 8) % 4

    def tunnel(self, s):
        s.fill(BLACK)
        for i in range(1, 18):
            z = (i - self.beat % 1) / 18
            r = pygame.Rect(0, 0, 64 / z ** 1.2, 40 / z ** 1.2)
            r.center = (self.w / 2 + math.sin(self.beat * 0.25 + i * 0.3) * 40 * z, self.h / 2)
            col = BROWN if (int(self.beat) - i) % 4 == 0 else SILVER
            pygame.draw.rect(s, dim(col, z * 1.6 * (0.4 + 0.6 * self.kick)), r, 1)

    def grid(self, s):
        s.fill(BLACK)
        cw, ch = self.w / 8, self.h / 6
        lit = np.random.default_rng(int(self.beat * 4)).random((8, 6)) < 0.15 + 0.3 * self.kick
        for i, j in zip(*np.nonzero(lit)):
            s.fill(dim(BROWN if (i + j) % 7 == 0 else SILVER, 0.3 + 0.7 * self.kick), (i * cw + 4, j * ch + 4, cw - 8, ch - 8))

    def echo(self, s):
        # the last frame, zoomed and turned a little, under the new one
        old = pygame.transform.rotozoom(s, 0.5 + self.kick, 1.025 + 0.02 * self.kick)
        old.set_alpha(232)
        s.fill(BLACK)
        s.blit(old, old.get_rect(center=(self.w / 2, self.h / 2)))
        for k in range(3):
            a = self.beat * 0.9 + k * 2.09
            x = self.w / 2 + math.cos(a) * 180 * (0.6 + noise3(k, self.beat * 0.2, 0))
            pygame.draw.circle(s, BROWN if k == 0 else SILVER, (x, self.h / 2 + math.sin(a) * 140), 5 + 18 * self.kick)

    def type(self, s):
        s.fill(BLACK)
        r = self.word.get_rect(center=(self.w / 2, self.h / 2))
        for y in range(0, r.h, 6):                 # horizontal slices, pushed on the beat
            s.blit(self.word, (r.x + noise3(y * 0.05, self.beat * 0.8, 0) * 140 * self.kick, r.y + y), (0, y, r.w, 4))

    def draw(self, screen):
        getattr(self, SCENES[self.scene])(self.canvas)
        screen.blit(self.canvas, (0, 0))
        for i, name in enumerate(SCENES):
            text(screen, name, (self.w - 40, 36 + i * 26), 18, SILVER if i == self.scene else GREY, italic=i == self.scene,
                 anchor="topright", alpha=255 if i == self.scene else 120)
