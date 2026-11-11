import numpy as np
import pygame

from core.app import TEST_FRAMES
from core.draw import blur, text
from core.noise import noise3
from core.palette import BLACK, GREY, SILVER, TAN

# walk past the screen and leave smoke. the hidden camera finds your body (mediapipe
# selfie segmentation), the outline of it breathes smoke into a field that rises.
# fast movement warms the smoke to brown. no camera: the mouse moves a stand-in figure.

GW, GH = 320, 200


class SmokeMirror:
    title = "Smoke Mirror"
    hint = "walk in front of the camera, or move the mouse"
    glow = 0.25

    def __init__(self, size):
        self.w, self.h = size
        self.tracker = None
        if not TEST_FRAMES:
            from core.camera import Tracker
            self.tracker = Tracker("segment")
        self.smoke, self.heat, self.before = (np.zeros((GW, GH), np.float32) for _ in range(3))
        self.gx, self.gy = np.meshgrid(np.arange(GW), np.arange(GH), indexing="ij")
        self.fx, self.t = GW / 2, 0

    def body(self, mouse):
        tr = self.tracker
        if tr and tr.fresh and tr.mask is not None:
            m = tr.mask.T
            return (m[np.linspace(0, m.shape[0] - 1, GW).astype(int)][:, np.linspace(0, m.shape[1] - 1, GH).astype(int)] > 0.5).astype(np.float32)
        # stand-in: a head and a body that follow the mouse sideways
        aim = mouse.x / self.w * GW if mouse.inside else GW / 2 + np.sin(self.t * 0.5) * GW * 0.3
        self.fx += (aim - self.fx) * 0.15
        bob = np.sin(self.t * 6) * 2
        head = np.hypot(self.gx - self.fx, self.gy - GH * 0.3 - bob) < GH * 0.08
        torso = ((self.gx - self.fx) / (GH * 0.14)) ** 2 + ((self.gy - GH * 0.7 - bob) / (GH * 0.32)) ** 2 < 1
        return (head | torso).astype(np.float32)

    def update(self, dt, mouse):
        self.t += dt
        m = self.body(mouse)
        outline = np.clip(m - blur(m, 2), 0, 1) * 4
        moved = np.abs(m - self.before)
        self.before = m
        # move everything up one pixel and a little sideways with noise
        sway = np.round(noise3(self.gx * 0.02, self.gy * 0.02 - self.t * 0.3, self.t * 0.2) * 2).astype(int)
        sx, sy = np.clip(self.gx + sway, 0, GW - 1), np.clip(self.gy + 1, 0, GH - 1)
        self.smoke = blur(self.smoke[sx, sy], 1) * 0.975 + outline * 0.35
        self.heat = blur(self.heat[sx, sy], 1) * 0.92 + blur(moved, 2) * 0.35

    def draw(self, screen):
        d = blur(np.clip(self.smoke, 0, 1.2) / 1.2, 1) ** 0.8          # soften the pixel steps
        warm = (np.clip(self.heat, 0, 1) * d)[..., None]
        col = np.float32(BLACK) + (np.float32(SILVER) - BLACK) * d[..., None]
        col = col * (1 - warm * 0.6) + np.float32(TAN) * warm
        img = pygame.surfarray.make_surface(np.clip(col, 0, 255).astype(np.uint8))
        pygame.transform.smoothscale(img, (self.w, self.h), screen)
        if self.tracker and not self.tracker.fresh:
            text(screen, self.tracker.status, (self.w - 28, 24), 16, GREY, anchor="topright")

    def close(self):
        if self.tracker:
            self.tracker.stop()
