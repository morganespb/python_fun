import numpy as np
import pygame

from core.app import TEST_FRAMES
from core.draw import Canvas, blur, text
from core.noise import fbm, noise3, smoothstep
from core.palette import BLACK, GREY, SILVER, TAN

TIPS = [4, 8, 12, 16, 20]       # thumb to little finger
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
         (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]


class Hands:
    """up to two hands from the hidden camera, smoothed. the mouse if there is no camera"""

    def __init__(self, size):
        self.w, self.h = size
        self.tracker = None
        if not TEST_FRAMES:
            from core.camera import Tracker
            self.tracker = Tracker("hand")
        self.pts, self.vel, self.raw = [], [], []

    def update(self, mouse):
        found = self.tracker.hands if self.tracker and self.tracker.fresh else []
        self.raw = found
        if found:
            # use the middle 80% of the camera so the screen edges are easy to reach
            targets = [np.stack([(h[:, 0] - 0.1) / 0.8 * self.w, (h[:, 1] - 0.1) / 0.8 * self.h], 1) for h in found]
        elif mouse.inside:
            targets = [np.tile(mouse.pos, (21, 1)).astype(float)]
        else:
            targets = []
        if len(targets) != len(self.pts):
            self.pts = [t.copy() for t in targets]
        old = [p.copy() for p in self.pts]
        for p, t in zip(self.pts, targets):
            p += (t - p) * 0.6                      # smooth the jitter
        self.vel = [p - o for p, o in zip(self.pts, old)]
        self.camera = bool(found)
        # pinch (thumb meets index) lifts the hand, so does holding the mouse
        if found:
            self.lifted = [np.linalg.norm(h[4, :2] - h[8, :2]) / (np.linalg.norm(h[9, :2] - h[0, :2]) + 1e-6) < 0.35 for h in found]
        else:
            self.lifted = [mouse.down] * len(targets)

    def tips(self):
        """(points, velocities) of every fingertip touching the surface"""
        pts, vel = [], []
        for p, v, up in zip(self.pts, self.vel, self.lifted):
            if not up:
                idx = TIPS if self.camera else [8]
                pts.append(p[idx])
                vel.append(v[idx])
        return (np.concatenate(pts), np.concatenate(vel)) if pts else (np.zeros((0, 2)), np.zeros((0, 2)))

    def status(self):
        if not self.tracker:
            return "mouse"
        if self.camera:
            return f"{len(self.pts)} hand{'s' if len(self.pts) > 1 else ''}"
        return self.tracker.status

    def preview(self, screen):
        """small camera view with the points it found, to check the tracking"""
        if not self.tracker or self.tracker.image is None:
            return
        img = self.tracker.image
        w = 240
        h = w * img.shape[0] // img.shape[1]
        surf = pygame.transform.smoothscale(pygame.surfarray.make_surface(img.swapaxes(0, 1)), (w, h))
        x0, y0 = self.w - w - 24, 24
        screen.blit(surf, (x0, y0))
        for hand in self.raw:
            p = [(x0 + float(x) * w, y0 + float(y) * h) for x, y, _ in hand]
            for a, b in BONES:
                pygame.draw.line(screen, SILVER, p[a], p[b], 1)
            for i in TIPS:
                pygame.draw.circle(screen, TAN, p[i], 4)


class Ghost:
    """a soft light on your index fingertip"""

    def __init__(self, size):
        self.cv = Canvas(*size, 2)

    def step(self, hands, t, dt):
        self.cv.fade(0.04)
        for i, (p, v) in enumerate(zip(hands.pts, hands.vel)):
            a, b = p[8] - v[8], p[8]
            line = a + (b - a) * np.linspace(0, 1, 24)[:, None]
            dust = np.repeat(line, 10, 0) + np.random.normal(0, 2.5, (240, 2))
            self.cv.splat(dust[:, 0], dust[:, 1], SILVER, 0.12)
            core = b + np.random.normal(0, 1.5, (80, 2))
            self.cv.splat(core[:, 0], core[:, 1], TAN, 0.25)

    def draw(self, screen):
        self.cv.blit(screen)


class Sand:
    """a tray of brown sand seen from above. under it, a silver plate shows through"""

    def __init__(self, size):
        self.w, self.h = size
        self.gw, self.gh = 400, 250
        gx, gy = np.meshgrid(np.arange(self.gw), np.arange(self.gh), indexing="ij")
        self.gx, self.gy = gx.astype(np.float32), gy.astype(np.float32)
        self.reset()
        # fine grain texture, multiplied over the shading
        g = np.random.default_rng(3).uniform(205, 255, (self.w, self.h)).astype(np.uint8)
        self.grain = pygame.surfarray.make_surface(np.repeat(g[..., None], 3, 2))

    def reset(self):
        ridges = 0.05 * np.sin(self.gy * 0.33 + noise3(self.gx * 0.02, self.gy * 0.02, 1))  # raked lines
        self.height = (1 + ridges + 0.05 * fbm(self.gx * 0.03, self.gy * 0.03, 4)).astype(np.float32)

    def plough(self, x, y, vx, vy, r=9):
        near = np.clip(1 - np.hypot(self.gx - x, self.gy - y) / r, 0, 1) ** 1.5
        take = self.height * near * 0.35
        self.height -= take
        speed = np.hypot(vx, vy)
        if speed > 0.3:
            # most of it goes in front of the finger, the rest to the sides
            ahead = np.roll(take, (int(vx / speed * r * 1.1), int(vy / speed * r * 1.1)), (0, 1))
            self.height += ahead * 0.55 + blur(take, r) * 0.45
        else:
            self.height += blur(take, int(r * 1.5))

    def settle(self, slope=0.05, rate=0.22):
        # sand slides only where it is steeper than its natural angle
        h = self.height
        for axis in (0, 1):
            d = np.diff(h, axis=axis)
            flow = np.sign(d) * np.maximum(np.abs(d) - slope, 0) * rate
            lo, hi = (slice(None, -1), slice(1, None))
            if axis == 0:
                h[lo, :] += flow
                h[hi, :] -= flow
            else:
                h[:, lo] += flow
                h[:, hi] -= flow

    def step(self, hands, t, dt):
        sx, sy = self.gw / self.w, self.gh / self.h
        for (x, y), (vx, vy) in zip(*hands.tips()):
            self.plough(x * sx, y * sy, vx * sx, vy * sy)
        self.settle()
        self.settle()

    def draw(self, screen):
        h = self.height
        gx, gy = np.gradient(h * 9)
        # low light from the top left, so grooves cast soft shadows
        light = np.array([-0.62, -0.48, 0.62]) / np.linalg.norm([-0.62, -0.48, 0.62])
        shade = np.clip((-gx * light[0] - gy * light[1] + light[2]) / np.sqrt(gx * gx + gy * gy + 1), 0, 1) ** 2.2
        col = np.float32(BLACK) + (np.float32(TAN) - BLACK) * shade[..., None]
        plate = smoothstep(0.6, 0.15, h)[..., None]          # thin sand shows the plate
        col = col * (1 - plate) + np.float32(SILVER) * plate * (0.45 + 0.55 * shade[..., None])
        img = pygame.surfarray.make_surface(np.clip(col, 0, 255).astype(np.uint8))
        pygame.transform.smoothscale(img, (self.w, self.h), screen)
        screen.blit(self.grain, (0, 0), special_flags=pygame.BLEND_MULT)


class Smoke:
    """rising smoke. your palm pushes it, fast moves warm it to brown"""

    def __init__(self, size):
        self.w, self.h = size
        self.rng = np.random.default_rng(1)
        n = 36000
        self.p = self.rng.uniform((0, 0), size, (n, 2))
        self.v = np.zeros((n, 2))
        self.life = self.rng.uniform(0, 1, n)
        self.heat = np.zeros(n)
        self.cv = Canvas(*size, 2)

    def step(self, hands, t, dt):
        p, v = self.p, self.v
        angle = fbm(p[:, 0] * 0.003, p[:, 1] * 0.003, t * 0.12, 2) * 5
        flow = np.stack([np.cos(angle) * 22, np.sin(angle) * 22 - 38], 1)   # drift + rise
        for pts, vel, up in zip(hands.pts, hands.vel, hands.lifted):
            if up:
                continue
            palm, push = pts[[0, 5, 9, 13, 17]].mean(0), vel[9]
            d = p - palm
            dist = np.hypot(*d.T) + 1e-3
            near = np.exp(-(dist / 120) ** 2)
            v += push * near[:, None] * 1.8 + d / dist[:, None] * near[:, None] * 1.2
            self.heat = np.maximum(self.heat, near * min(1, np.hypot(*push) / 18))
        v += (flow - v) * min(1, 2.2 * dt)
        p += v * dt
        self.heat *= 0.97
        self.life -= dt * 0.12
        dead = (self.life <= 0) | (p[:, 1] < -20)
        k = dead.sum()
        p[dead] = np.stack([self.rng.uniform(0, self.w, k), self.h + self.rng.uniform(0, 60, k)], 1)
        v[dead], self.heat[dead] = 0, 0
        self.life[dead] = self.rng.uniform(0.6, 1, k)

    def draw(self, screen):
        self.cv.fade(0.12)
        a = np.clip(self.life, 0, 1) * 0.1
        self.cv.splat(self.p[:, 0], self.p[:, 1], SILVER, a * (1 - self.heat))
        self.cv.splat(self.p[:, 0], self.p[:, 1], TAN, a * self.heat * 2)
        self.cv.blit(screen)


class UnseenHand:
    title = "Unseen Hand"
    hint = "1 light   2 sand   3 smoke   ·   pinch to lift   ·   r rake   ·   c camera check"
    glow = 0.12

    def __init__(self, size):
        self.hands = Hands(size)
        self.modes = {1: Ghost(size), 2: Sand(size), 3: Smoke(size)}
        self.mode, self.check, self.t = 2, False, 0

    def event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.mode = e.key - pygame.K_0
            elif e.key == pygame.K_r:
                self.modes[2].reset()
            elif e.key == pygame.K_c:
                self.check = not self.check

    def update(self, dt, mouse):
        self.t += dt
        self.hands.update(mouse)
        self.modes[self.mode].step(self.hands, self.t, dt)

    def draw(self, screen):
        self.modes[self.mode].draw(screen)
        if self.check:
            self.hands.preview(screen)
            text(screen, self.hands.status(), (screen.get_width() - 24, 24 + 190), 16, GREY, anchor="topright")

    def close(self):
        if self.hands.tracker:
            self.hands.tracker.stop()
