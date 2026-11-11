import numpy as np
import pygame

from core.audio import hz, pluck, sound
from core.palette import BLACK, DEEP, GREY, SILVER, TAN

# every line you draw is a melody. height = pitch, left/right = stereo.
# let go and the line loops at the speed you drew it. c clears.

SCALE = [0, 3, 5, 7, 10]       # a minor pentatonic, never sounds wrong


class Instrument:
    title = "Drawing Instrument"
    hint = "draw with the mouse · c clears"
    glow = 0.35

    def __init__(self, size):
        self.w, self.h = size
        self.lines, self.drawing, self.rings = [], None, []
        self.sounds, self.t = {}, 0
        # one example line so the screen isn't empty (it plays silently)
        xs = np.linspace(160, self.w - 160, 26)
        self.lines.append(self.finish([(x, self.h / 2 + np.sin(i * 0.6) * 160, i * 0.12) for i, x in enumerate(xs)], quiet=True))

    def note(self, y):
        step = int((1 - y / self.h) * 13)
        return 45 + 12 * (step // 5) + SCALE[step % 5]

    def play(self, x, y, quiet=False):
        self.rings.append([x, y, 0.0])
        if quiet:
            return
        key = (self.note(y), round(x / self.w * 8) / 4 - 1)
        if key not in self.sounds:
            self.sounds[key] = sound(pluck(hz(key[0])), key[1], 0.8)
        if self.sounds[key]:
            self.sounds[key].play()

    def finish(self, pts, quiet=False):
        t0 = pts[0][2]
        pts = [(x, y, t - t0) for x, y, t in pts]
        return dict(pts=pts, length=pts[-1][2] + 0.6, start=self.t, last=0.0, quiet=quiet)

    def event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            self.lines = [ln for ln in self.lines if not ln["quiet"]]
            self.drawing = [(*e.pos, self.t)]
            self.play(*e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and self.drawing:
            if len(self.drawing) > 1:
                self.lines = (self.lines + [self.finish(self.drawing)])[-5:]
            self.drawing = None
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_c:
            self.lines = []

    def update(self, dt, mouse):
        self.t += dt
        if self.drawing and mouse.down:
            x, y, _ = self.drawing[-1]
            if np.hypot(mouse.x - x, mouse.y - y) > 14:
                self.drawing.append((mouse.x, mouse.y, self.t))
                self.play(mouse.x, mouse.y)
        for ln in self.lines:                      # replay notes whose time has come round
            now, before = (self.t - ln["start"]) % ln["length"], ln["last"]
            for x, y, t in ln["pts"]:
                if before < t <= now or (now < before and (t > before or t <= now)):
                    self.play(x, y, ln["quiet"])
            ln["last"] = now
        self.rings = [[x, y, a + dt] for x, y, a in self.rings if a < 0.7]

    def draw(self, screen):
        screen.fill(BLACK)
        for i in range(14):
            y = self.h - (i + 0.5) / 13 * self.h
            pygame.draw.line(screen, DEEP, (0, y), (self.w, y))
        shapes = [ln["pts"] for ln in self.lines] + ([self.drawing] if self.drawing else [])
        for pts in shapes:
            if len(pts) > 1:
                pygame.draw.aalines(screen, SILVER, False, [(x, y) for x, y, _ in pts])
            for x, y, _ in pts:
                pygame.draw.circle(screen, GREY, (x, y), 2)
        for x, y, a in self.rings:
            k = a / 0.7
            pygame.draw.circle(screen, TAN, (x, y), 4 + 30 * k, 1)
            pygame.draw.circle(screen, TAN, (x, y), 4 * (1 - k) + 1)
