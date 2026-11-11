import os

import numpy as np

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from .palette import BLACK, SILVER  # noqa: E402

_fonts = {}
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")


def font(size, italic=False):
    # one typeface for everything: instrument serif (open font licence, in fonts/)
    key = (size, italic)
    if key not in _fonts:
        name = "InstrumentSerif-Italic.ttf" if italic else "InstrumentSerif-Regular.ttf"
        _fonts[key] = pygame.font.Font(os.path.join(FONT_DIR, name), size)
    return _fonts[key]


def text(surf, s, pos, size=18, color=SILVER, italic=False, anchor="topleft", alpha=255):
    img = font(size, italic).render(s, True, color)
    img.set_alpha(int(alpha))
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


class Canvas:
    """a float image for drawing lots of soft points fast"""

    def __init__(self, w, h, scale=1):
        self.s = scale
        self.w, self.h = int(w // scale), int(h // scale)
        self.buf = np.zeros((self.w, self.h, 3), np.float32)
        self.clear()

    def clear(self, color=BLACK):
        self.buf[:] = color

    def fade(self, k, color=BLACK):
        # pull every pixel a bit back to the background, leaves trails
        self.buf *= 1 - k
        self.buf += np.float32(color) * k

    def splat(self, x, y, color=SILVER, alpha=1.0):
        # each point is shared between 4 pixels, so slow motion stays smooth
        x = np.asarray(x, np.float32).ravel() / self.s
        y = np.asarray(y, np.float32).ravel() / self.s
        if x.size == 0:
            return
        a = np.broadcast_to(np.asarray(alpha, np.float32).ravel(), x.shape)
        col = np.asarray(color, np.float32)
        x0, y0 = np.floor(x), np.floor(y)
        fx, fy = x - x0, y - y0
        x0, y0 = x0.astype(np.int64), y0.astype(np.int64)
        xs = np.concatenate([x0, x0 + 1, x0, x0 + 1])
        ys = np.concatenate([y0, y0, y0 + 1, y0 + 1])
        wt = np.concatenate([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy]) * np.tile(a, 4)
        ok = (xs >= 0) & (xs < self.w) & (ys >= 0) & (ys < self.h)
        idx, wt = xs[ok] * self.h + ys[ok], wt[ok]
        n = self.w * self.h
        flat = self.buf.reshape(-1, 3)
        hit = np.unique(idx)                      # only touch pixels that got points
        if col.ndim == 1:
            flat[hit] += (np.bincount(idx, wt, n)[hit, None] * col).astype(np.float32)
        else:
            c4 = np.tile(col, (4, 1))[ok]
            for c in range(3):
                flat[hit, c] += np.bincount(idx, wt * c4[:, c], n)[hit].astype(np.float32)

    def blit(self, surf):
        img = pygame.surfarray.make_surface(np.clip(self.buf, 0, 255).astype(np.uint8))
        if self.s == 1:
            surf.blit(img, (0, 0))
        else:
            pygame.transform.smoothscale(img, surf.get_size(), surf)


def project(p, ry, rx, scale, cx, cy, cam=3.2):
    """turn 3d points (n, 3) and put them on screen. returns x, y, depth"""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    x, z = x * np.cos(ry) + z * np.sin(ry), -x * np.sin(ry) + z * np.cos(ry)
    y, z = y * np.cos(rx) - z * np.sin(rx), y * np.sin(rx) + z * np.cos(rx)
    k = cam / (cam - z)
    return cx + x * k * scale, cy + y * k * scale, z


def blur(a, k):
    """box blur a 2d array, k pixels each side"""
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (k + 1, k)
        c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
        n = a.shape[axis]
        a = (np.take(c, np.arange(2 * k + 1, 2 * k + 1 + n), axis) - np.take(c, np.arange(n), axis)) / (2 * k + 1)
    return a


class Finish:
    """the last pass on every frame: soft glow, vignette, film grain"""

    def __init__(self, size):
        w, h = size
        self.size = size
        gx, gy = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h), indexing="ij")
        v = 1 - 0.38 * np.clip(gx * gx * 0.8 + gy * gy, 0, 1.4) ** 1.4
        v = (np.clip(v, 0, 1) * 255).astype(np.uint8)
        self.vignette = pygame.surfarray.make_surface(np.repeat(v[..., None], 3, 2))
        rng = np.random.default_rng(1)
        self.grain = []
        for _ in range(4):
            g = rng.integers(0, 9, (w // 2, h // 2), dtype=np.uint8)
            s = pygame.surfarray.make_surface(np.repeat(g[..., None], 3, 2))
            self.grain.append(pygame.transform.scale(s, size))
        self.frame = 0

    def __call__(self, screen, glow=0.3):
        w, h = self.size
        if glow > 0:
            small = pygame.transform.smoothscale(screen, (w // 5, h // 5))
            small = pygame.transform.gaussian_blur(small, 4)
            k = int(255 * glow)
            small.fill((k, k, k), special_flags=pygame.BLEND_MULT)
            screen.blit(pygame.transform.smoothscale(small, (w, h)), (0, 0), special_flags=pygame.BLEND_ADD)
        screen.blit(self.vignette, (0, 0), special_flags=pygame.BLEND_MULT)
        self.frame += 1
        screen.blit(self.grain[self.frame % 4], (0, 0), special_flags=pygame.BLEND_ADD)
        screen.fill((4, 4, 4), special_flags=pygame.BLEND_SUB)
