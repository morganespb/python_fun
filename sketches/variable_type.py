import math

import numpy as np
import pygame

from core.draw import font
from core.palette import BLACK, BROWN, SILVER

# letters get heavier near the mouse and wider the faster you move.
# a real variable font has these as axes (weight, width). pygame can't read
# font axes, so here weight = thickening the letter, width = stretching it.

WORD = "souffle"


class VariableType:
    title = "Variable Type"
    hint = "move near the letters · move fast to stretch them"
    glow = 0.2

    def __init__(self, size):
        self.w, self.h = size
        self.size = 200
        self.letters = [font(self.size, italic=True).render(c, True, SILVER) for c in WORD]
        self.px, self.py, self.speed, self.t = self.w / 2, self.h / 2, 0.0, 0
        self.weight, self.width = np.zeros(len(WORD)), np.ones(len(WORD))

    def update(self, dt, mouse):
        self.t += dt
        if mouse.inside and mouse.idle < 2.5:
            aim, fast = mouse.pos, mouse.speed
        else:                                      # nobody there: a ghost cursor sweeps across
            aim, fast = (self.w * (0.5 + 0.42 * math.sin(self.t * 0.9)), self.h / 2), 14 * abs(math.cos(self.t * 0.9))
        self.px += (aim[0] - self.px) * 0.3
        self.py += (aim[1] - self.py) * 0.3
        self.speed += (min(fast, 40) - self.speed) * 0.1

    def draw(self, screen):
        screen.fill(BLACK)
        base = [g.get_width() for g in self.letters]
        x = self.w / 2 - sum(base) / 2
        centres = np.array([x + sum(base[:i]) + b / 2 for i, b in enumerate(base)])
        near = np.exp(-((centres - self.px) ** 2 + (self.h / 2 - self.py) ** 2 * 0.3) / 160 ** 2)
        self.weight += (near * 6 - self.weight) * 0.25
        self.width += (1 + near * (0.15 + self.speed / 40 * 0.9) - self.width) * 0.25
        widths = [int(b * k) for b, k in zip(base, self.width)]
        x = self.w / 2 - sum(widths) / 2
        y = self.h / 2 - self.size * 0.62
        for g, gw, heavy in zip(self.letters, widths, self.weight):
            g = pygame.transform.smoothscale(g, (gw, g.get_height()))
            r = round(heavy)
            for a in np.linspace(0, 2 * math.pi, 12, endpoint=False) if r else []:
                screen.blit(g, (x + r * 0.5 * math.cos(a), y + r * 0.5 * math.sin(a)))   # thicker
            screen.blit(g, (x, y))
            if heavy > 4:
                pygame.draw.line(screen, BROWN, (x + 10, y + self.size * 1.2), (x + gw - 10, y + self.size * 1.2), 2)
            x += gw
