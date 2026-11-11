import math

import numpy as np
import pygame


class Scroll:
    """mouse wheel or up/down keys as a 0..1 scroll bar. plays itself when left alone"""

    def __init__(self, speed=0.05):
        self.target = self.value = 0.0
        self.idle, self.t, self.speed = 99.0, 0.0, speed

    def event(self, e):
        step = 0
        if e.type == pygame.MOUSEWHEEL:
            step = -e.y * 0.04
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_UP, pygame.K_DOWN):
            step = 0.08 if e.key == pygame.K_DOWN else -0.08
        if step:
            self.target = float(np.clip(self.target + step, 0, 1))
            self.idle = 0

    def update(self, dt):
        self.t += dt
        self.idle += dt
        if self.idle > 4:
            self.target = 0.5 - 0.5 * math.cos(self.t * self.speed * 2 * math.pi)
        self.value += (self.target - self.value) * min(1, dt * 4)   # ease towards it
        return self.value
