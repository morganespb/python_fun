import math

import numpy as np
import pygame

from core.draw import text
from core.noise import fbm
from core.palette import BLACK, BROWN, DEEP, GREY, SILVER


class WeatherGlass:
    title = "Weather in a Glass"
    hint = "move the mouse left and right to blow"
    glow = 0.25

    def __init__(self, size):
        self.w, self.h = size
        self.R = int(self.h * 0.32)
        self.cx, self.cy = self.w // 2, int(self.h * 0.45)
        self.rng = np.random.default_rng(6)
        self.drops = self.rng.uniform(-1, 1, (700, 2)) * self.R
        self.speed = self.rng.uniform(0.8, 1.2, 700)
        self.wind, self.flash, self.t = 0.0, 0.0, 0
        n = self.R // 2                             # fog is computed at quarter size
        self.fx, self.fy = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        self.round = pygame.Surface((2 * self.R, 2 * self.R), pygame.SRCALPHA)
        pygame.draw.circle(self.round, (255, 255, 255, 255), (self.R, self.R), self.R)

    def update(self, dt, mouse):
        self.t += dt
        aim = (mouse.x - self.cx) / (self.w / 2) if mouse.inside and mouse.idle < 3 else math.sin(self.t * 0.4) * 0.8
        self.wind += (np.clip(aim, -1, 1) - self.wind) * min(1, dt * 2)
        d = self.drops
        d += np.stack([np.full(700, self.wind * 420), np.full(700, 560.0)], 1) * dt * self.speed[:, None]
        d[d[:, 1] > self.R * 0.55, 1] -= self.R * 1.6                  # back to the top
        d[:, 0] = (d[:, 0] + self.R) % (2 * self.R) - self.R
        if abs(self.wind) > 0.75 and self.rng.random() < dt * 0.6:
            self.flash = 1.0                                          # lightning
        self.flash *= 0.85

    def draw(self, screen):
        screen.fill(BLACK)
        R = self.R
        fog = (fbm(self.fx * 0.05 - self.t * self.wind * 0.6, self.fy * 0.06, self.t * 0.1) + 1) / 2
        v = 12 + 80 * fog ** 2 + self.flash * 120
        img = np.stack([v * 1.05, v * 0.95, v * 0.85], -1).clip(0, 255).astype(np.uint8)   # warm grey
        layer = pygame.Surface((2 * R, 2 * R), pygame.SRCALPHA)
        layer.blit(pygame.transform.smoothscale(pygame.surfarray.make_surface(img), (2 * R, 2 * R)), (0, 0))
        # water with a wave
        sea = [(x, R * 1.55 + math.sin(x * 0.04 + self.t * 3) * 4 * (1 + abs(self.wind))) for x in range(0, 2 * R + 8, 8)]
        pygame.draw.polygon(layer, DEEP, sea + [(2 * R, 2 * R), (0, 2 * R)])
        pygame.draw.lines(layer, GREY, False, sea, 1)
        tilt = self.wind * 14
        for (x, y), s in zip(self.drops, self.speed):
            pygame.draw.aaline(layer, (190, 190, 194, 140), (x + R, y + R), (x + R - tilt * s, y + R - 16 * s))
        layer.blit(self.round, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)      # keep the inside of the sphere
        screen.blit(layer, (self.cx - R, self.cy - R))
        pygame.draw.circle(screen, GREY, (self.cx, self.cy), R, 1)
        pygame.draw.arc(screen, SILVER, (self.cx - R + 16, self.cy - R + 16, 2 * R - 32, 2 * R - 32), 1.9, 2.6, 2)
        base = pygame.Rect(0, 0, R * 1.1, R * 0.22)
        base.midtop = (self.cx, self.cy + R - 6)
        pygame.draw.rect(screen, BROWN, base, border_radius=4)
        text(screen, f"{abs(self.wind) * 60:.0f} km/h", (self.cx, base.bottom + 18), 20, GREY, italic=True, anchor="midtop")
