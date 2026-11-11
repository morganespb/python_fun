import math

import numpy as np
import pygame

from core.draw import Canvas, text
from core.palette import BLACK, GREY, SILVER, TAN

# a little creature made of fuzz. the head chases the mouse, every body part
# follows the one in front. leave the mouse still and it curls up to sleep.

PARTS, GAP = 14, 11


class ParticlePet:
    title = "Particle Pet"
    hint = "move the mouse · click to make it jump · stay still and it sleeps"
    glow = 0.35

    def __init__(self, size):
        self.w, self.h = size
        self.body = np.array([[self.w / 2 - i * GAP, self.h / 2] for i in range(PARTS)], float)
        self.size = np.array([18 * (1 - i / (PARTS + 2)) + 3 for i in range(PARTS)])
        self.look = np.array([1.0, 0.0])
        self.rng = np.random.default_rng(19)
        self.sparks = np.zeros((0, 5))
        self.t, self.joy, self.sleep, self.blink = 0, 0.0, 0.0, 0.0
        self.cv = Canvas(*size)

    def event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            self.joy = 1.0
            a, sp = self.rng.uniform(0, 2 * np.pi, 60), self.rng.uniform(60, 220, 60)
            burst = np.stack([*np.tile(self.body[0], (60, 1)).T, np.cos(a) * sp, np.sin(a) * sp, np.zeros(60)], 1)
            self.sparks = np.concatenate([self.sparks, burst])

    def update(self, dt, mouse):
        self.t += dt
        tired = (mouse.idle > 4 or not mouse.inside) and self.t > 6
        self.sleep += (tired - self.sleep) * min(1, dt * 1.5)
        if self.sleep > 0.5:                       # curl up in a small slow circle
            aim, speed = np.array([self.w / 2 + math.cos(self.t * 0.5) * 30, self.h * 0.62 + math.sin(self.t * 0.5) * 30]), 0.03
        elif mouse.inside and mouse.idle < 4:
            aim, speed = np.array(mouse.pos), 0.12
        else:
            aim, speed = np.array([self.w / 2 + math.sin(self.t * 0.7) * self.w * 0.3, self.h / 2 + math.sin(self.t * 1.3) * self.h * 0.2]), 0.06
        aim[1] -= abs(math.sin(self.t * 14)) * 30 * self.joy        # hopping when happy
        step = aim - self.body[0]
        self.body[0] += step * speed
        if np.linalg.norm(step) > 1:
            self.look += (step / np.linalg.norm(step) - self.look) * 0.2
        for i in range(1, PARTS):                  # follow the leader at a fixed distance
            d = self.body[i] - self.body[i - 1]
            self.body[i] = self.body[i - 1] + d / (np.linalg.norm(d) + 1e-6) * GAP
        self.joy *= 0.97
        self.blink = 0.15 if self.rng.random() < dt * 0.4 else max(0, self.blink - dt)
        s = self.sparks
        s[:, 3] += 300 * dt
        s[:, :2] += s[:, 2:4] * dt
        s[:, 4] += dt
        self.sparks = s[s[:, 4] < 0.9]

    def draw(self, screen):
        self.cv.fade(0.5)
        breathe = 1 + 0.08 * math.sin(self.t * (1.5 if self.sleep > 0.5 else 3))
        a = self.rng.uniform(0, 2 * np.pi, (PARTS, 40))
        r = self.size[:, None] * breathe * np.sqrt(self.rng.random((PARTS, 40)))
        self.cv.splat(self.body[:, :1] + np.cos(a) * r, self.body[:, 1:] + np.sin(a) * r, SILVER, 0.5)
        self.cv.splat(self.sparks[:, 0], self.sparks[:, 1], TAN, 1.4 - self.sparks[:, 4])
        self.cv.blit(screen)
        head, side = self.body[0], np.array([-self.look[1], self.look[0]])
        for sign in (-1, 1):
            eye = head + self.look * 7 + side * 7 * sign
            if self.sleep > 0.5 or self.blink > 0:
                pygame.draw.line(screen, BLACK, eye - (4, 0), eye + (4, 0), 2)
            else:
                pygame.draw.circle(screen, BLACK, eye, 5)
                pygame.draw.circle(screen, TAN if self.joy > 0.3 else SILVER, eye + self.look * 2, 2)
        if self.sleep > 0.5:
            for i in range(3):
                k = (self.t * 0.5 + i / 3) % 1
                text(screen, "z", (head[0] + 18 + k * 20, head[1] - 20 - k * 50), 16 + i * 4, GREY, italic=True, alpha=255 * (1 - k))
