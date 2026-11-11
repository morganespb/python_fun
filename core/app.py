import math
import os
import time

# test mode: BENCH_FRAMES=200 runs without a window and a fake mouse
TEST_FRAMES = int(os.environ.get("BENCH_FRAMES", "0"))
if TEST_FRAMES:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from .draw import Finish, pygame, text  # noqa: E402
from .palette import GREY, SILVER  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = (1280, 800)


class Mouse:
    """where the mouse is, how fast it moves, how long it has been still"""

    def __init__(self, size):
        self.w, self.h = size
        self.x, self.y = self.w / 2, self.h / 2
        self.vx = self.vy = 0.0
        self.down, self.inside, self.idle = False, False, 0.0
        self.frame = 0

    def update(self, dt):
        self.frame += 1
        if TEST_FRAMES:
            # a scripted loop with a click now and then
            t = self.frame / 60
            x, y = self.w * (0.5 + 0.35 * math.sin(t * 1.3)), self.h * (0.5 + 0.3 * math.sin(t * 2.1 + 0.5))
            self.down, self.inside = self.frame % 90 > 75, True
        else:
            x, y = pygame.mouse.get_pos()
            self.down, self.inside = pygame.mouse.get_pressed()[0], pygame.mouse.get_focused()
        self.vx, self.vy = x - self.x, y - self.y
        still = abs(self.vx) + abs(self.vy) < 0.5 and not self.down
        self.idle = self.idle + dt if still else 0.0
        self.x, self.y = x, y

    @property
    def pos(self):
        return (self.x, self.y)

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)


def run(sketches, start=0):
    """one window for every sketch. sketches = list of functions that return a sketch class.
    keys: left / right switch · esc quit · h hide label · p save png · f fullscreen"""
    pygame.init()
    screen = pygame.display.set_mode(SIZE)
    clock = pygame.time.Clock()
    mouse, finish = Mouse(SIZE), Finish(SIZE)
    label, frame = True, 0
    index = start % len(sketches)
    sketch, t = sketches[index]()(SIZE), 0.0
    old, slide, direction = None, 1.0, 1
    switch_at = int(os.environ.get("BENCH_SWITCH", "0"))   # test mode: press right at this frame

    def switch(step):
        nonlocal sketch, index, t, old, slide, direction
        old, slide, direction = screen.copy(), 0.0, step     # keep the last frame for the slide
        close(sketch)
        index = (index + step) % len(sketches)
        sketch, t = sketches[index]()(SIZE), 0.0

    while True:
        dt = 1 / 60 if TEST_FRAMES else min(clock.tick(60) / 1000, 0.05)
        t += dt
        pygame.display.set_caption(f"{index}  {sketch.title.lower()}")
        was_down = mouse.down
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                return close(sketch, quit=True)
            if e.type == pygame.KEYDOWN and not getattr(sketch, "typing", False):
                if e.key in (pygame.K_RIGHT, pygame.K_LEFT):
                    switch(1 if e.key == pygame.K_RIGHT else -1)
                    continue
                if e.key == pygame.K_h:
                    label = not label
                elif e.key == pygame.K_p:
                    save(screen, sketch.title)
                elif e.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
            if hasattr(sketch, "event"):
                sketch.event(e)
        if TEST_FRAMES and frame == switch_at > 0:
            switch(1)

        mouse.update(dt)
        if TEST_FRAMES and hasattr(sketch, "event") and mouse.down != was_down:
            kind = pygame.MOUSEBUTTONDOWN if mouse.down else pygame.MOUSEBUTTONUP
            sketch.event(pygame.event.Event(kind, button=1, pos=mouse.pos))

        sketch.update(dt, mouse)
        sketch.draw(screen)
        finish(screen, getattr(sketch, "glow", 0.3))

        # a quiet label: number and title, and the hint for the first few seconds
        if label:
            text(screen, f"{index}   {sketch.title.lower()}", (28, SIZE[1] - 30), 20, SILVER, italic=True, anchor="bottomleft", alpha=200)
            text(screen, "‹   ›", (SIZE[0] - 28, SIZE[1] - 30), 20, GREY, anchor="bottomright", alpha=160)
            fade = 200 * max(0, min(1, 6 - t))
            if fade > 0:
                text(screen, sketch.hint, (28, SIZE[1] - 12), 16, GREY, anchor="bottomleft", alpha=fade)

        # the old sketch slides out, the new one slides in
        if slide < 1:
            slide = min(1, slide + dt / 0.6)
            k = 1 - (1 - slide) ** 3
            new = screen.copy()
            screen.blit(old, (-k * SIZE[0] * direction, 0))
            screen.blit(new, ((1 - k) * SIZE[0] * direction, 0))
        pygame.display.flip()

        frame += 1
        if TEST_FRAMES and frame >= TEST_FRAMES:
            if os.environ.get("BENCH_SHOT"):
                pygame.image.save(screen, os.environ["BENCH_SHOT"])
            return close(sketch, quit=True)


def close(sketch, quit=False):
    if hasattr(sketch, "close"):
        sketch.close()          # stops the camera, frees the gpu
    if quit:
        pygame.quit()


def save(screen, title):
    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    name = "-".join(title.lower().split())
    path = os.path.join(ROOT, "output", f"{name}-{time.strftime('%H%M%S')}.png")
    pygame.image.save(screen, path)
    print("saved", path)
