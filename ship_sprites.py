"""Procedural ship sprite builder.

Each ship has a unique silhouette that reflects its stats:
  serpent — balanced / classic fighter    (symmetric, medium)
  viper   — speed & agility              (slim, needle fuselage, swept wings)
  hydra   — heavy firepower              (wide, triple cannon barrels, armoured hull)

All sprites face UP (nose at the top), matching the original fighter.png orientation.
"""
import pygame
import math


# ---------------------------------------------------------------------------
# Serpent — balanced blue fighter
# ---------------------------------------------------------------------------
def _build_serpent() -> pygame.Surface:
    W, H = 52, 64
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2

    # Main fuselage (rounded teardrop)
    body_pts = [
        (cx,      4),          # nose tip
        (cx + 14, 26),         # mid-right
        (cx + 10, 52),         # rear-right
        (cx,      56),         # tail centre
        (cx - 10, 52),         # rear-left
        (cx - 14, 26),         # mid-left
    ]
    pygame.draw.polygon(surf, (20, 60, 100), body_pts)
    pygame.draw.polygon(surf, (80, 200, 255), body_pts, 2)

    # Swept wings
    for sign in (-1, 1):
        wing = [
            (cx + sign * 10, 30),
            (cx + sign * 26,  46),
            (cx + sign * 18,  52),
            (cx + sign * 6,   40),
        ]
        pygame.draw.polygon(surf, (15, 50, 85), wing)
        pygame.draw.polygon(surf, (60, 170, 230), wing, 1)

    # Cockpit window
    pygame.draw.ellipse(surf, (0, 30, 70),    (cx - 6, 12, 12, 14))
    pygame.draw.ellipse(surf, (100, 220, 255),(cx - 5, 13, 10, 12))
    pygame.draw.ellipse(surf, (200, 240, 255),(cx - 3, 14,  6,  6))

    # Centre cannon
    pygame.draw.rect(surf, (50, 140, 200), (cx - 3, 0, 6, 10), border_radius=2)
    pygame.draw.circle(surf, (140, 230, 255), (cx, 1), 3)

    # Twin engine nozzles
    for ex in (cx - 8, cx + 8):
        pygame.draw.rect(surf, (30, 80, 140), (ex - 5, 52, 10, 10), border_radius=3)
        pygame.draw.ellipse(surf, (80, 180, 255), (ex - 4, 59, 8, 6))
        pygame.draw.ellipse(surf, (200, 235, 255),(ex - 2, 60, 4, 4))

    # Hull detail line
    pygame.draw.line(surf, (70, 160, 220), (cx, 10), (cx, 50), 1)

    return surf


# ---------------------------------------------------------------------------
# Viper — speed / agility green fighter
# ---------------------------------------------------------------------------
def _build_viper() -> pygame.Surface:
    W, H = 44, 68
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2

    # Slim needle fuselage
    body_pts = [
        (cx,      2),          # sharp nose
        (cx + 6,  20),
        (cx + 8,  48),
        (cx,      62),
        (cx - 8,  48),
        (cx - 6,  20),
    ]
    pygame.draw.polygon(surf, (10, 70, 25), body_pts)
    pygame.draw.polygon(surf, (80, 255, 110), body_pts, 2)

    # Delta swept-back wings (very angular)
    for sign in (-1, 1):
        wing = [
            (cx + sign * 6,  28),
            (cx + sign * 22, 58),
            (cx + sign * 14, 60),
            (cx + sign * 4,  42),
        ]
        pygame.draw.polygon(surf, (8, 55, 20), wing)
        pygame.draw.polygon(surf, (60, 210, 85), wing, 1)

        # Thin winglet tip
        tip = [
            (cx + sign * 20, 54),
            (cx + sign * 26, 50),
            (cx + sign * 22, 60),
        ]
        pygame.draw.polygon(surf, (50, 180, 70), tip)

    # Cockpit (narrow slit)
    pygame.draw.ellipse(surf, (0, 40, 15),    (cx - 4, 10, 8, 16))
    pygame.draw.ellipse(surf, (80, 255, 120), (cx - 3, 11, 6, 14))
    pygame.draw.ellipse(surf, (190, 255, 200),(cx - 2, 12, 4,  8))

    # Single slim cannon (long and thin)
    pygame.draw.rect(surf, (40, 160, 60), (cx - 2, 0, 4, 12), border_radius=1)
    pygame.draw.circle(surf, (150, 255, 160), (cx, 1), 2)

    # Single compact engine
    pygame.draw.rect(surf, (15, 80, 30), (cx - 6, 58, 12, 9), border_radius=3)
    pygame.draw.ellipse(surf, (80, 255, 110), (cx - 5, 64, 10, 6))
    pygame.draw.ellipse(surf, (200, 255, 210),(cx - 3, 65,  6, 4))

    # Speed stripes on fuselage
    for sy in (24, 32, 40):
        pygame.draw.line(surf, (50, 200, 80), (cx - 4, sy), (cx + 4, sy), 1)

    return surf


# ---------------------------------------------------------------------------
# Hydra — heavy firepower orange fighter
# ---------------------------------------------------------------------------
def _build_hydra() -> pygame.Surface:
    W, H = 66, 58
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2

    # Wide armoured hull
    body_pts = [
        (cx,      4),           # nose
        (cx + 22, 20),          # shoulder-right
        (cx + 24, 46),          # rear-right
        (cx,      50),
        (cx - 24, 46),          # rear-left
        (cx - 22, 20),          # shoulder-left
    ]
    pygame.draw.polygon(surf, (90, 30, 5), body_pts)
    pygame.draw.polygon(surf, (255, 120, 50), body_pts, 2)

    # Armour plates (horizontal lines)
    for py in (20, 30, 40):
        pygame.draw.line(surf, (170, 65, 20),
                         (cx - 18 + (py - 20), py),
                         (cx + 18 - (py - 20), py), 1)

    # Short stubby wings with weapon pods
    for sign in (-1, 1):
        wing = [
            (cx + sign * 20, 22),
            (cx + sign * 32, 36),
            (cx + sign * 26, 44),
            (cx + sign * 14, 34),
        ]
        pygame.draw.polygon(surf, (70, 22, 4), wing)
        pygame.draw.polygon(surf, (220, 90, 30), wing, 1)
        # Wing cannon pod
        px = cx + sign * 30
        pygame.draw.rect(surf, (50, 15, 0),
                         (px - 3 if sign > 0 else px - 3, 32, 6, 12), border_radius=2)
        pygame.draw.circle(surf, (255, 80, 0), (px, 32), 4)
        pygame.draw.circle(surf, (255, 200, 80),(px, 32), 2)

    # Cockpit (wide & low)
    pygame.draw.ellipse(surf, (60, 18, 0),    (cx - 8, 12, 16, 12))
    pygame.draw.ellipse(surf, (255, 130, 60), (cx - 7, 13, 14, 10))
    pygame.draw.ellipse(surf, (255, 220, 180),(cx - 4, 14,  8,  6))

    # Triple cannon barrels (centre + two flanking)
    for bx, bh in ((cx, 12), (cx - 10, 9), (cx + 10, 9)):
        pygame.draw.rect(surf, (120, 40, 5), (bx - 3, 0, 6, bh), border_radius=1)
        pygame.draw.circle(surf, (255, 90, 20), (bx, 1), 3)
        pygame.draw.circle(surf, (255, 200, 100),(bx, 1), 1)

    # Twin wide engine nozzles
    for ex in (cx - 12, cx + 12):
        pygame.draw.rect(surf, (100, 35, 5), (ex - 7, 48, 14, 9), border_radius=3)
        pygame.draw.ellipse(surf, (255, 130, 40), (ex - 6, 54, 12, 6))
        pygame.draw.ellipse(surf, (255, 230, 150),(ex - 3, 55,  6, 4))

    return surf


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_BUILDERS = {
    'serpent': _build_serpent,
    'viper':   _build_viper,
    'hydra':   _build_hydra,
}


def build_ship(ship_id: str) -> pygame.Surface:
    """Return a freshly drawn surface for the given ship id."""
    fn = _BUILDERS.get(ship_id)
    if fn is None:
        raise ValueError(f"Unknown ship id: {ship_id!r}")
    return fn()
