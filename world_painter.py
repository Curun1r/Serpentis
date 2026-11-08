"""Draw logical gameplay coordinates directly into an HD framebuffer.

Physics keep the original 720-unit height. Only this boundary converts positions,
geometry, fonts and sprites to framebuffer pixels; actors and hitboxes stay intact.
"""

from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache
from weakref import WeakKeyDictionary

import pygame

from ui_fx import draw_glass_panel, render_shadowed


class WorldPainter:
    def __init__(self, surface: pygame.Surface, logical_size: tuple[int, int], fonts: dict):
        self.surface = surface
        self.width, self.height = logical_size
        self.scale = surface.get_height() / self.height
        self._fonts = {font: pygame.font.Font(None, max(1, round(size * self.scale))) for font, size in fonts.items()}
        self._images = WeakKeyDictionary()
        self._labels = OrderedDict()

    def point(self, point):
        return round(point[0] * self.scale), round(point[1] * self.scale)

    def rect_pixels(self, rect):
        x, y, width, height = rect
        left, top = self.point((x, y))
        right, bottom = self.point((x + width, y + height))
        return pygame.Rect(left, top, right - left, bottom - top)

    def blit(self, image: pygame.Surface, position, alpha=255) -> pygame.Rect:
        size = tuple(max(1, round(dimension * self.scale)) for dimension in image.get_size())
        if size == image.get_size():
            scaled = image
        else:
            scaled = self._images.get(image)
            if scaled is None:
                scaled = pygame.transform.smoothscale(image, size)
                self._images[image] = scaled
        if alpha != 255:
            scaled = scaled.copy()
            scaled.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        return self.surface.blit(scaled, self.point(position))

    def sprite(self, sprite) -> None:
        self.blit(sprite.image, sprite.rect.topleft)

    def group(self, sprites) -> None:
        for sprite in sprites:
            self.sprite(sprite)

    def rect(self, color, rect, width=0, border_radius=0) -> None:
        pygame.draw.rect(
            self.surface,
            color,
            self.rect_pixels(rect),
            max(1, round(width * self.scale)) if width else 0,
            border_radius=round(border_radius * self.scale),
        )

    @staticmethod
    @lru_cache(maxsize=48)
    def _circle_image(color, radius, width):
        image = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(image, color, (radius + 1, radius + 1), radius, width)
        return image

    def circle(self, color, center, radius, width=0) -> None:
        physical_radius = max(1, round(radius * self.scale))
        physical_width = max(1, round(width * self.scale)) if width else 0
        if len(color) == 4:
            image = self._circle_image(tuple(color), physical_radius, physical_width)
            self.surface.blit(image, image.get_rect(center=self.point(center)))
        else:
            pygame.draw.circle(self.surface, color, self.point(center), physical_radius, physical_width)

    def pixel(self, point, color) -> None:
        self.rect(color, (*point, 1, 1))

    def panel(self, rect, **kwargs) -> None:
        kwargs["radius"] = round(kwargs.get("radius", 12) * self.scale)
        draw_glass_panel(self.surface, self.rect_pixels(rect), **kwargs)

    def text(self, font, value, color, position, anchor="topleft", shadow=None, alpha=255) -> pygame.Rect:
        key = (font, value, tuple(color), tuple(shadow) if shadow is not None else None)
        label = self._labels.get(key)
        if label is None:
            native_font = self._fonts[font]
            label = (
                native_font.render(value, True, color)
                if shadow is None
                else render_shadowed(native_font, value, color, shadow, offset=max(1, round(2 * self.scale)))
            )
            self._labels[key] = label
            if len(self._labels) > 128:
                self._labels.popitem(last=False)
        else:
            self._labels.move_to_end(key)
        if alpha != 255:
            label = label.copy()
            label.set_alpha(alpha)
        rect = label.get_rect(**{anchor: self.point(position)})
        self.surface.blit(label, rect)
        # Return logical bounds for optional layout of neighboring labels.
        return pygame.Rect(*(round(value / self.scale) for value in rect))

    def tint(self, color) -> None:
        overlay = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        overlay.fill(color)
        self.surface.blit(overlay, (0, 0))
