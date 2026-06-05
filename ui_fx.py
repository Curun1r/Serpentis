"""UI visual-effects helpers for Serpentis.

All functions draw onto existing pygame.Surface objects and return nothing,
unless noted otherwise.
"""
import pygame
import math


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def render_shadowed(font: pygame.font.Font, text: str,
                    color, shadow_color=(0, 0, 0),
                    offset: int = 2) -> pygame.Surface:
    """Render text with a drop-shadow underneath."""
    base   = font.render(text, True, color)
    shadow = font.render(text, True, shadow_color)
    w = base.get_width()  + offset
    h = base.get_height() + offset
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.blit(shadow, (offset, offset))
    surf.blit(base,   (0, 0))
    return surf


def render_outlined(font: pygame.font.Font, text: str,
                    color, outline_color=(0, 0, 0),
                    thickness: int = 2) -> pygame.Surface:
    """Render text with a solid outline (8-directional)."""
    base = font.render(text, True, color)
    w = base.get_width()  + thickness * 2
    h = base.get_height() + thickness * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    outline = font.render(text, True, outline_color)
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx == 0 and dy == 0:
                continue
            surf.blit(outline, (dx + thickness, dy + thickness))
    surf.blit(base, (thickness, thickness))
    return surf


def render_glowing(font: pygame.font.Font, text: str,
                   color, glow_color,
                   glow_radius: int = 6) -> pygame.Surface:
    """Render text with a soft glow halo around it."""
    base = font.render(text, True, color)
    bw, bh = base.get_size()
    pad  = glow_radius + 4
    surf = pygame.Surface((bw + pad * 2, bh + pad * 2), pygame.SRCALPHA)

    # Soft glow: series of increasingly transparent/large blits
    glow_surf = font.render(text, True, glow_color)
    steps = max(1, glow_radius)
    for i in range(steps, 0, -1):
        alpha = int(90 * (i / steps) ** 2)
        gs    = glow_surf.copy()
        gs.set_alpha(alpha)
        # Scale up slightly for bloom
        scale = 1.0 + (steps - i + 1) * 0.08
        sw2 = int(bw * scale)
        sh2 = int(bh * scale)
        scaled = pygame.transform.smoothscale(gs, (sw2, sh2))
        ox = pad + (bw - sw2) // 2
        oy = pad + (bh - sh2) // 2
        surf.blit(scaled, (ox, oy))

    surf.blit(base, (pad, pad))
    return surf


# ---------------------------------------------------------------------------
# Shape helpers
# ---------------------------------------------------------------------------

def draw_glow_circle(surface: pygame.Surface, center: tuple,
                     radius: int, color: tuple, steps: int = 8):
    """Draw a subtle soft radial glow."""
    r, g, b = color[:3]
    for i in range(steps, 0, -1):
        alpha = int(18 * (i / steps) ** 2)   # very subtle — won't blow out
        rad   = int(radius * (i / steps) * 1.6)
        glow  = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (r, g, b, alpha), (rad, rad), rad)
        surface.blit(glow, (center[0] - rad, center[1] - rad))


def draw_rounded_gradient_rect(surface: pygame.Surface,
                                rect: pygame.Rect,
                                color_top: tuple,
                                color_bottom: tuple,
                                radius: int = 8):
    """Draw a vertically-gradient rounded rectangle."""
    # Clip to a rounded mask
    mask = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.w, rect.h),
                     border_radius=radius)

    grad = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    for y in range(rect.h):
        t = y / max(rect.h - 1, 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
        a = int(color_top[3] + (color_bottom[3] - color_top[3]) * t) if len(color_top) > 3 else 255
        pygame.draw.line(grad, (r, g, b, a), (0, y), (rect.w, y))

    # Mask gradient to rounded shape
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(grad, rect.topleft)


def draw_fancy_button(surface: pygame.Surface,
                      rect: pygame.Rect,
                      label: str,
                      font: pygame.font.Font,
                      base_color: tuple,
                      hover_color: tuple,
                      is_hover: bool,
                      border_color: tuple | None = None,
                      text_color: tuple = (255, 255, 255)):
    """Draw a gradient button with optional glow on hover."""
    col = hover_color if is_hover else base_color

    # Darken for bottom gradient
    bot = tuple(max(0, c - 35) for c in col[:3])

    draw_rounded_gradient_rect(surface, rect,
                               (*col, 255),
                               (*bot, 255),
                               radius=9)

    # Border
    bc = border_color if border_color else tuple(min(255, c + 60) for c in col)
    pygame.draw.rect(surface, bc, rect, 2, border_radius=9)

    # Inner top highlight line
    hi_rect = pygame.Rect(rect.x + 3, rect.y + 2, rect.w - 6, 1)
    pygame.draw.rect(surface, tuple(min(255, c + 80) for c in col), hi_rect)

    # Label
    txt = render_shadowed(font, label, text_color, (0, 0, 0), offset=2)
    surface.blit(txt, txt.get_rect(center=rect.center))


# ---------------------------------------------------------------------------
# Floating damage numbers
# ---------------------------------------------------------------------------

class DamageNumber:
    """A floating text label that rises and fades out over its lifetime.

    Usage::
        nums: list[DamageNumber] = []
        # spawn
        nums.append(DamageNumber(cx, cy, "+50", (255, 215, 0), font))
        # each frame
        DamageNumber.update_all(nums, dt)
        DamageNumber.draw_all(nums, surface)
    """

    # Presets so callers don't need to hardcode colours
    COLOR_SCORE   = (255, 215,  50)   # gold  — alien kill score
    COLOR_HIT     = (255, 255, 255)   # white — armored-alien chip damage
    COLOR_BOSS    = (255, 100, 255)   # pink  — boss hit
    COLOR_PLAYER  = (255,  60,  60)   # red   — player takes damage

    def __init__(self, x: float, y: float, text: str,
                 color: tuple, font: pygame.font.Font,
                 lifetime: float = 0.9,
                 rise_speed: float = 55.0,
                 scale: float = 1.0):
        self.x          = float(x)
        self.y          = float(y)
        self.lifetime   = lifetime
        self.max_life   = lifetime
        self.rise_speed = rise_speed

        # Pre-render with outline for readability over any background
        base    = font.render(text, True, color)
        outline = font.render(text, True, (0, 0, 0))
        bw, bh  = base.get_size()
        thick   = 1
        raw     = pygame.Surface((bw + thick * 2, bh + thick * 2), pygame.SRCALPHA)
        for dx in (-thick, 0, thick):
            for dy in (-thick, 0, thick):
                if dx == 0 and dy == 0:
                    continue
                raw.blit(outline, (dx + thick, dy + thick))
        raw.blit(base, (thick, thick))

        if scale != 1.0:
            sw = max(1, int(raw.get_width()  * scale))
            sh = max(1, int(raw.get_height() * scale))
            raw = pygame.transform.smoothscale(raw, (sw, sh))

        self._surf = raw

    # ------------------------------------------------------------------

    def update(self, dt: float):
        self.y        -= self.rise_speed * dt
        self.lifetime -= dt

    def draw(self, surface: pygame.Surface):
        ratio = max(0.0, self.lifetime / self.max_life)
        alpha = int(255 * ratio)
        if alpha <= 0:
            return
        # set_alpha() is ignored on SRCALPHA surfaces in pygame — use
        # BLEND_RGBA_MULT to multiply every pixel's alpha channel instead.
        surf = self._surf.copy()
        surf.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        cx = int(self.x) - surf.get_width()  // 2
        cy = int(self.y) - surf.get_height() // 2
        surface.blit(surf, (cx, cy))

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    # ------------------------------------------------------------------
    # Batch helpers

    @staticmethod
    def update_all(nums: list, dt: float):
        for n in nums:
            n.update(dt)
        nums[:] = [n for n in nums if n.alive]

    @staticmethod
    def draw_all(nums: list, surface: pygame.Surface):
        for n in nums:
            n.draw(surface)


def draw_glass_panel(surface: pygame.Surface,
                     rect: pygame.Rect,
                     bg_color: tuple = (12, 12, 28),
                     bg_alpha: int = 220,
                     border_color: tuple = (70, 70, 110),
                     radius: int = 12):
    """Draw a semi-transparent 'glass' panel with a top highlight."""
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*bg_color, bg_alpha), (0, 0, rect.w, rect.h),
                     border_radius=radius)
    # Top highlight stripe
    hi = pygame.Surface((rect.w - 4, 2), pygame.SRCALPHA)
    hi.fill((255, 255, 255, 28))
    panel.blit(hi, (2, 2))
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, border_color, rect, 1, border_radius=radius)
