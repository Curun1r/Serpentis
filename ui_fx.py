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
