import numpy as np
import pygame

from core.draw import Canvas, font, text
from core.palette import DEEP, GREY, SILVER, TAN


class KineticType:
    title = "Kinetic Type"
    hint = "brush the letters with the mouse · enter to type a new word"
    glow = 0.3

    def __init__(self, size):
        self.w, self.h = size
        self.floor = self.h - 90
        self.rng = np.random.default_rng(9)
        self.cv = Canvas(*size)
        self.typing, self.draft = False, ""
        self.build("brume")

    def build(self, word):
        img = font(int(min(300, self.w * 1.6 / max(3, len(word)))), italic=True).render(word, True, (255, 255, 255))
        a = pygame.surfarray.array_alpha(img)[::3, ::3]
        ix, iy = np.nonzero(a > 128)
        x0, y0 = (self.w - img.get_width()) / 2, self.h * 0.4 - img.get_height() / 2
        self.home = np.stack([x0 + ix * 3, y0 + iy * 3], 1) + self.rng.normal(0, 0.6, (ix.size, 2))
        n = len(self.home)
        self.p, self.v = self.home.copy(), np.zeros((n, 2))
        self.loose, self.landed, self.timer = np.zeros(n, bool), np.zeros(n, bool), np.zeros(n)
        self.pile = np.zeros(self.w // 3 + 1)            # how many grains sit in each 3px column
        self.light = self.rng.random(n) < 0.05

    def event(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_RETURN:
            if self.typing and self.draft:
                self.build(self.draft.lower())
            self.typing, self.draft = not self.typing, ""
        elif self.typing and e.key == pygame.K_BACKSPACE:
            self.draft = self.draft[:-1]
        elif self.typing and e.unicode.isalpha():
            self.draft += e.unicode

    def update(self, dt, mouse):
        p, v = self.p, self.v
        # grains near the mouse come loose
        if mouse.inside:
            hit = (np.hypot(p[:, 0] - mouse.x, p[:, 1] - mouse.y) < 70) & ~self.loose
            k = hit.sum()
            self.loose[hit] = True
            v[hit] = np.stack([mouse.vx * 25 + self.rng.normal(0, 60, k), mouse.vy * 25 + self.rng.normal(-80, 60, k)], 1)
        self.timer[self.loose] += dt
        guarded = (np.hypot(*(self.home - mouse.pos).T) < 140) & mouse.inside   # don't rebuild under the mouse
        back = self.loose & (self.timer > 2.2) & ~guarded
        fall = self.loose & ~back & ~self.landed

        # falling: gravity, then land on the pile
        v[fall, 1] += 1400 * dt
        p[fall] += v[fall] * dt
        col = np.clip((p[:, 0] / 3).astype(int), 0, self.pile.size - 1)
        lands = np.flatnonzero(fall & (p[:, 1] >= self.floor - self.pile[col] * 1.2))
        for i in lands:
            c = col[i]
            for _ in range(8):                           # roll off while a neighbour is lower
                left, right = self.pile[max(c - 1, 0)], self.pile[min(c + 1, self.pile.size - 1)]
                if min(left, right) >= self.pile[c] - 1:
                    break
                c = c - 1 if left <= right else c + 1
            p[i] = (c * 3 + 1.5, self.floor - self.pile[c] * 1.2)
            self.pile[c] += 1
            v[i] = 0
            self.landed[i] = True

        # going home: leave the pile, spring back into the letter
        leave = back & self.landed
        np.subtract.at(self.pile, col[leave], 1)
        self.landed[leave] = False
        v[back] = (v[back] + (self.home[back] - p[back]) * 30 * dt) * 0.86
        p[back] += v[back] * dt
        done = back & (np.hypot(*(p - self.home).T) < 1.5)
        p[done], v[done] = self.home[done], 0
        self.loose[done], self.timer[done] = False, 0

    def draw(self, screen):
        self.cv.fade(0.6)
        self.cv.splat(self.p[~self.light, 0], self.p[~self.light, 1], SILVER, 1.2)
        self.cv.splat(self.p[self.light, 0], self.p[self.light, 1], TAN, 1.4)
        self.cv.blit(screen)
        pygame.draw.line(screen, DEEP, (0, self.floor + 2), (self.w, self.floor + 2))
        if self.typing:
            text(screen, (self.draft or "type a word") + ", then enter", (self.w - 40, 40), 24, GREY, italic=True, anchor="topright")
