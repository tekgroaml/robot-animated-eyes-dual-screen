#!/usr/bin/env python3
"""Animate independent eyes in the left/right halves of one HDMI canvas."""
import argparse
from dataclasses import dataclass
import math
import os
from pathlib import Path
import random
import sys
import config


@dataclass(frozen=True)
class Pose:
    openness: float = 1.0
    width: float = 1.0
    brow: float = 0.0
    dilation: float = 1.0


POSES = {
    "neutral": Pose(), "happy": Pose(0.68, 1.04, -0.25, 1.15),
    "angry": Pose(0.60, 1.02, 0.90, 0.70), "curious": Pose(1.08, 0.94, -0.20, 1.25),
}
LOOKS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1), "center": (0, 0)}


class EyeMotion:
    """Time-based expression interpolation, autonomous blinks and small saccades."""
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.expression = "neutral"
        self.pose = list(Pose().__dict__.values())
        self.gaze = [0.0, 0.0]
        self.target = [0.0, 0.0]
        self.micro = [0.0, 0.0]
        self.time = 0.0
        self.blink_started = -10.0
        self.next_blink = self.rng.uniform(*config.AUTO_BLINK_SECONDS)
        self.next_saccade = 0.0

    def blink(self):
        self.blink_started = self.time
        self.next_blink = self.time + self.rng.uniform(*config.AUTO_BLINK_SECONDS)

    def update(self, dt):
        self.time += dt
        if self.time >= self.next_blink:
            self.blink()
        if self.time >= self.next_saccade:
            self.micro = [self.rng.uniform(-0.12, 0.12), self.rng.uniform(-0.08, 0.08)]
            self.next_saccade = self.time + self.rng.uniform(*config.SACCADE_SECONDS)
        factor = 1 - math.exp(-config.TRANSITION_SPEED * dt)
        desired = list(POSES[self.expression].__dict__.values())
        for i, value in enumerate(desired):
            self.pose[i] += (value - self.pose[i]) * factor
        for i in range(2):
            goal = max(-1, min(1, self.target[i] + self.micro[i]))
            self.gaze[i] += (goal - self.gaze[i]) * factor

    def blink_amount(self, delay=0):
        elapsed = self.time - self.blink_started - delay
        if not 0 <= elapsed <= 0.24:
            return 0.0
        return math.sin(math.pi * elapsed / 0.24) ** 2


def validate_config(size, fps):
    if not 128 <= size <= 2160 or not 10 <= fps <= 240:
        raise ValueError("Screen size must be 128..2160 and FPS must be 10..240.")
    for name in ("BACKGROUND", "SCLERA_COLOR", "IRIS_COLOR", "PUPIL_COLOR"):
        color = getattr(config, name)
        if len(color) != 3 or any(not isinstance(v, int) or not 0 <= v <= 255 for v in color):
            raise ValueError(f"{name} must contain three integer RGB channels.")
    for name, low, high in (("EYE_WIDTH", .2, .9), ("EYE_HEIGHT", .1, .65),
                            ("IRIS_RADIUS", .03, .25), ("PUPIL_DILATION", .1, .8)):
        if not low <= getattr(config, name) <= high:
            raise ValueError(f"{name} must be between {low} and {high}.")
    if config.TRANSITION_SPEED <= 0:
        raise ValueError("TRANSITION_SPEED must be positive.")
    for interval in (config.AUTO_BLINK_SECONDS, config.SACCADE_SECONDS):
        if len(interval) != 2 or not 0 < interval[0] <= interval[1]:
            raise ValueError("Animation intervals must be positive ordered pairs.")


def render_eye(pygame, canvas, layer, mask, motion, index, size):
    layer.fill((0, 0, 0, 0))
    mask.fill((0, 0, 0, 0))
    openness, width_scale, brow, dilation = motion.pose
    if motion.expression == "curious":
        openness *= 1.12 if index == 0 else 0.72
    openness *= 1 - motion.blink_amount(index * 0.012)
    cx, cy = size // 2, size // 2
    width = round(size * config.EYE_WIDTH * width_scale)
    height = max(3, round(size * config.EYE_HEIGHT * openness))
    rect = pygame.Rect(cx-width//2, cy-height//2, width, height)
    pygame.draw.ellipse(layer, config.SCLERA_COLOR, rect)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), rect)
    gx, gy = motion.gaze
    iris_x = round(cx + gx*size*.16)
    iris_y = round(cy + gy*size*.10)
    radius = max(4, round(size*config.IRIS_RADIUS*dilation))
    pygame.draw.circle(layer, config.IRIS_COLOR, (iris_x, iris_y), radius)
    pygame.draw.circle(layer, (14, 104, 139), (iris_x, iris_y), radius, max(1, size//150))
    pygame.draw.circle(layer, config.PUPIL_COLOR, (iris_x, iris_y), max(2, round(radius*config.PUPIL_DILATION)))
    pygame.draw.circle(layer, (245, 255, 255), (iris_x-radius//3, iris_y-radius//3), max(2, radius//7))
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    canvas.blit(layer, (index*size, 0))
    # Opaque upper lids angle toward the bridge for an angry expression.
    if brow > .01:
        x0 = index*size
        inner = round(size*.17*brow)
        points = [(x0+rect.left-2, rect.top-2), (x0+rect.right+2, rect.top-2),
                  (x0+rect.right+2, rect.top+(inner if index == 0 else 0)),
                  (x0+rect.left-2, rect.top+(inner if index == 1 else 0))]
        pygame.draw.polygon(canvas, config.BACKGROUND, points)
    if motion.expression == "happy":
        cut = pygame.Rect(index*size+cx-width//2, cy+height//4, width, height)
        pygame.draw.ellipse(canvas, config.BACKGROUND, cut)
    accent = (12, 61, 78)
    arc = pygame.Rect(index*size+size*.10, size*.10, size*.80, size*.80)
    pygame.draw.arc(canvas, accent, arc, math.radians(30), math.radians(150), max(1, size//160))
    pygame.draw.arc(canvas, accent, arc, math.radians(210), math.radians(330), max(1, size//160))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=config.SCREEN_SIZE, help="Width of one square panel")
    parser.add_argument("--fps", type=int, default=config.FPS)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--display", type=int, default=0, help="SDL desktop index, not an SBS half")
    parser.add_argument("--mouse", action="store_true", default=config.MOUSE_TRACKING)
    parser.add_argument("--expression", choices=POSES, default="neutral")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--headless", action="store_true", help="Use the SDL dummy video driver")
    parser.add_argument("--frames", type=int, default=0, help="Exit after N frames; zero runs continuously")
    parser.add_argument("--screenshot", type=Path, help="Save the final frame as PNG")
    args = parser.parse_args(argv)
    try:
        validate_config(args.size, args.fps)
        if args.frames < 0 or (args.headless and args.frames == 0):
            raise ValueError("Headless mode requires a positive --frames limit.")
    except ValueError as exc:
        parser.error(str(exc))
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame
    except ImportError:
        parser.exit(1, "Pygame is missing. Run ./setup.sh --install-only first.\n")
    pygame.display.init()
    size = args.size
    try:
        desktops = pygame.display.get_desktop_sizes()
        if not 0 <= args.display < len(desktops):
            raise ValueError("The selected SDL display does not exist.")
        if not args.windowed and not args.headless and desktops[args.display] != (2*size, size):
            raise ValueError(f"Configure the HDMI desktop to {2*size}x{size} at 100% scale first, or use --windowed.")
        flags = 0 if args.windowed or args.headless else pygame.FULLSCREEN
        canvas = pygame.display.set_mode((2*size, size), flags, display=args.display)
        pygame.display.set_caption("SBS Robot Eyes | N H A C B | Arrows | M | Esc")
        pygame.mouse.set_visible(args.windowed)
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        clock = pygame.time.Clock()
        motion = EyeMotion(args.seed)
        motion.expression = args.expression
        tracking = args.mouse
        running, frame = True, 0
        keys = {pygame.K_n: "neutral", pygame.K_h: "happy", pygame.K_a: "angry", pygame.K_c: "curious"}
        looks = {pygame.K_LEFT: "left", pygame.K_RIGHT: "right", pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_SPACE: "center"}
        print(f"Rendering one {2*size}x{size} canvas: Screen A=left, Screen B=right. Press Esc to exit.")
        while running:
            dt = 1/args.fps if args.headless else min(clock.tick(args.fps)/1000, .1)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q): running = False
                    elif event.key in keys: motion.expression = keys[event.key]
                    elif event.key == pygame.K_b: motion.blink()
                    elif event.key == pygame.K_m: tracking = not tracking
                    elif event.key in looks:
                        tracking = False
                        motion.target = list(LOOKS[looks[event.key]])
                elif event.type == pygame.MOUSEMOTION and tracking:
                    mx, my = event.pos
                    motion.target = [((mx % size)/size-.5)*2, (my/size-.5)*2]
            motion.update(dt)
            canvas.fill(config.BACKGROUND)
            for index in range(2):
                render_eye(pygame, canvas, layer, mask, motion, index, size)
            pygame.display.flip()
            frame += 1
            if args.frames and frame >= args.frames: break
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(canvas, str(args.screenshot))
        return 0
    except (ValueError, pygame.error, OSError) as exc:
        print(f"Display error: {exc}", file=sys.stderr)
        return 1
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
