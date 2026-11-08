"""Animated parallax starfield background for Serpentis.

Usage:
    bg = StarBackground(width, height)
    # each frame:
    bg.update(dt)
    bg.draw(canvas)
"""
import pygame
import random
import math


class StarBackground:
    """Three-layer parallax starfield with scrolling nebula blobs."""

    # (speed_px_per_sec, count, size_range, brightness_range)
    _LAYERS = [
        (18,  80, (1, 1), (40,  90)),   # far  — tiny, dim
        (38,  50, (1, 2), (70, 140)),   # mid
        (70,  30, (2, 3), (140, 220)),  # near — larger, bright
    ]

    # Nebula clouds: (r, g, b, alpha, radius)
    _NEBULA_PALETTE = [
        (80,  30, 140, 14),   # purple
        (20,  60, 120, 12),   # deep blue
        (10,  90,  80, 10),   # teal
        (120, 20,  60, 11),   # magenta
    ]

    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self._stars: list[list] = []   # [x, y, layer_idx, size, brightness]
        self._nebulae: list[list] = [] # [x, y, color, radius, dy]
        self._t = 0.0
        self._cloud_images = {}
        self._cloud_scale = None

        # Initialise stars spread across full height so they don't all
        # appear at the top at startup.
        for li, (speed, count, size_r, br_r) in enumerate(self._LAYERS):
            for _ in range(count):
                self._stars.append([
                    random.uniform(0, width),
                    random.uniform(0, height),
                    li,
                    random.randint(*size_r),
                    random.randint(*br_r),
                ])

        # A handful of large nebula blobs
        for _ in range(8):
            col = random.choice(self._NEBULA_PALETTE)
            self._nebulae.append([
                random.uniform(0, width),
                random.uniform(0, height),
                col,
                random.randint(120, 280),
                random.uniform(4, 12),   # drift speed px/s downward
            ])

    # ------------------------------------------------------------------

    def update(self, dt: float):
        self._t += dt

        for star in self._stars:
            li    = star[2]
            speed = self._LAYERS[li][0]
            star[1] += speed * dt
            if star[1] > self.h:
                star[1] = -star[3]
                star[0] = random.uniform(0, self.w)

        for neb in self._nebulae:
            neb[1] += neb[4] * dt
            if neb[1] - neb[3] > self.h:
                neb[1] = -neb[3]
                neb[0] = random.uniform(0, self.w)

    # ------------------------------------------------------------------

    def draw(self, canvas: pygame.Surface):
        canvas.fill((5, 5, 16))

        self._draw_clouds(canvas, 1.0)

        # Stars
        for star in self._stars:
            x, y, li, size, br = star
            # Twinkle: slight brightness oscillation per star
            twinkle = int(br + 20 * math.sin(self._t * 3.0 + x * 0.05))
            twinkle = max(0, min(255, twinkle))
            col     = (twinkle, twinkle, min(255, twinkle + 25))
            ix, iy  = int(x), int(y)
            if size == 1:
                canvas.set_at((ix, iy), col)
            else:
                pygame.draw.circle(canvas, col, (ix, iy), size)
                # Small cross-hair glint on the brightest near-stars
                if li == 2 and twinkle > 180:
                    dim = (twinkle // 3, twinkle // 3, twinkle // 3)
                    canvas.set_at((ix - 2, iy), dim)
                    canvas.set_at((ix + 2, iy), dim)
                    canvas.set_at((ix, iy - 2), dim)
                    canvas.set_at((ix, iy + 2), dim)

    def draw_scaled(self, painter) -> None:
        """Draw stars and nebula geometry in the HD framebuffer."""
        painter.surface.fill((5, 5, 16))
        self._draw_clouds(painter.surface, painter.scale)
        for x, y, layer, size, brightness in self._stars:
            twinkle = max(0, min(255, int(brightness + 20 * math.sin(self._t * 3 + x * .05))))
            color = (twinkle, twinkle, min(255, twinkle + 25))
            if size == 1:
                painter.pixel((x, y), color)
            else:
                painter.circle(color, (x, y), size)
                if layer == 2 and twinkle > 180:
                    dim = (twinkle // 3,) * 3
                    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                        painter.pixel((x + dx, y + dy), dim)

    def _draw_clouds(self, surface, scale):
        # One precomposed image per cloud replaces four large alpha blits.
        # Keep only the current resolution so monitor changes cannot grow memory.
        if self._cloud_scale != scale:
            self._cloud_images.clear()
            self._cloud_scale = scale
        for x, y, color, radius, _ in self._nebulae:
            key = color, radius
            image = self._cloud_images.get(key)
            physical_radius = max(1, round(radius * scale))
            if image is None:
                size = physical_radius * 2 + 2
                image = pygame.Surface((size, size), pygame.SRCALPHA)
                center = physical_radius + 1
                for step in range(4, 0, -1):
                    fraction = step / 4
                    ring_radius = max(1, round(int(radius * fraction) * scale))
                    layer = pygame.Surface((ring_radius * 2 + 2,) * 2, pygame.SRCALPHA)
                    pygame.draw.circle(layer, (*color[:3], int(color[3] * fraction * fraction)),
                                       (ring_radius + 1,) * 2, ring_radius)
                    image.blit(layer, (center - ring_radius - 1,) * 2)
                image.set_alpha(255, pygame.RLEACCEL)
                self._cloud_images[key] = image
            surface.blit(image, (round(x * scale) - physical_radius - 1,
                                 round(y * scale) - physical_radius - 1))
