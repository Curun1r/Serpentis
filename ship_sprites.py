"""Procedural ship sprite builder — high-detail versions.

  serpent — balanced fighter    (blue,  symmetric, twin engines, central cannon)
  viper   — speed & agility     (green, slim delta, swept fins, single thruster)
  hydra   — heavy firepower     (orange, wide armoured hull, triple cannon array)

All sprites face UP (nose at top).
"""
import pygame
import math


# ---------------------------------------------------------------------------
# Serpent — balanced blue fighter  (52×68)
# ---------------------------------------------------------------------------
def _build_serpent() -> pygame.Surface:
    W, H = 52, 68
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2

    # ── Main fuselage ────────────────────────────────────────────────
    body = [
        (cx,      2),           # nose tip
        (cx + 9,  14),
        (cx + 13, 34),
        (cx + 10, 54),
        (cx,      60),
        (cx - 10, 54),
        (cx - 13, 34),
        (cx - 9,  14),
    ]
    pygame.draw.polygon(surf, (14, 45, 80), body)
    pygame.draw.polygon(surf, (80, 200, 255), body, 2)

    # Fuselage centre ridge
    pygame.draw.line(surf, (50, 130, 200), (cx, 4), (cx, 56), 2)

    # ── Swept wings ───────────────────────────────────────────────────
    for sign in (-1, 1):
        wing = [
            (cx + sign * 10, 28),
            (cx + sign * 26, 48),
            (cx + sign * 20, 56),
            (cx + sign * 8,  44),
        ]
        pygame.draw.polygon(surf, (10, 35, 68), wing)
        pygame.draw.polygon(surf, (60, 160, 230), wing, 1)
        # Wing trailing edge detail
        pygame.draw.line(surf, (40, 110, 180),
                         (cx + sign * 12, 32), (cx + sign * 22, 50), 1)

    # ── Cockpit ───────────────────────────────────────────────────────
    pygame.draw.ellipse(surf, (0, 25, 60),      (cx - 7, 8,  14, 18))
    pygame.draw.ellipse(surf, (90, 200, 255),   (cx - 6, 9,  12, 16))
    pygame.draw.ellipse(surf, (180, 235, 255),  (cx - 4, 10,  8, 10))
    # Cockpit highlight
    pygame.draw.ellipse(surf, (230, 248, 255),  (cx - 3, 11,  4,  5))

    # ── Nose cannon ───────────────────────────────────────────────────
    pygame.draw.rect(surf, (40, 110, 180), (cx - 3, 0, 6, 10), border_radius=2)
    pygame.draw.circle(surf, (130, 220, 255), (cx, 1), 3)

    # ── Armour plates on fuselage ─────────────────────────────────────
    for py in (20, 30, 40):
        pygame.draw.line(surf, (30, 85, 145),
                         (cx - 9 + (py - 20) // 2, py),
                         (cx + 9 - (py - 20) // 2, py), 1)

    # ── Twin engine nozzles ───────────────────────────────────────────
    for ex in (cx - 8, cx + 8):
        pygame.draw.rect(surf, (25, 65, 120), (ex - 5, 54, 10, 12), border_radius=3)
        pygame.draw.rect(surf, (60, 150, 220), (ex - 5, 54, 10, 12), 1, border_radius=3)
        # Engine glow ring
        pygame.draw.ellipse(surf, (70, 170, 255), (ex - 5, 62, 10, 8))
        pygame.draw.ellipse(surf, (180, 225, 255),(ex - 3, 63,  6, 5))

    return surf


# ---------------------------------------------------------------------------
# Viper — speed / agility green fighter  (46×72)
# ---------------------------------------------------------------------------
def _build_viper() -> pygame.Surface:
    W, H = 46, 72
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2

    # ── Slim needle fuselage ──────────────────────────────────────────
    body = [
        (cx,      1),           # sharp nose
        (cx + 5,  16),
        (cx + 7,  44),
        (cx + 4,  62),
        (cx,      68),
        (cx - 4,  62),
        (cx - 7,  44),
        (cx - 5,  16),
    ]
    pygame.draw.polygon(surf, (8, 55, 20), body)
    pygame.draw.polygon(surf, (80, 255, 110), body, 2)

    # Centre spine highlight
    pygame.draw.line(surf, (50, 200, 80), (cx, 3), (cx, 64), 1)

    # ── Delta swept wings (very angular) ─────────────────────────────
    for sign in (-1, 1):
        wing = [
            (cx + sign * 6,  26),
            (cx + sign * 22, 58),
            (cx + sign * 15, 64),
            (cx + sign * 4,  46),
        ]
        pygame.draw.polygon(surf, (6, 42, 16), wing)
        pygame.draw.polygon(surf, (55, 210, 80), wing, 1)
        # Wing leading edge glow line
        pygame.draw.line(surf, (40, 180, 65),
                         (cx + sign * 6, 26), (cx + sign * 22, 58), 1)

        # Winglet tip fin
        tip = [
            (cx + sign * 20, 54),
            (cx + sign * 28, 48),
            (cx + sign * 22, 64),
        ]
        pygame.draw.polygon(surf, (5, 32, 14), tip)
        pygame.draw.polygon(surf, (50, 185, 65), tip, 1)

    # ── Cockpit (narrow, tall) ────────────────────────────────────────
    pygame.draw.ellipse(surf, (0, 35, 15),      (cx - 4, 8,  8, 20))
    pygame.draw.ellipse(surf, (75, 240, 110),   (cx - 3, 9,  6, 18))
    pygame.draw.ellipse(surf, (170, 255, 190),  (cx - 2, 10,  4, 12))
    pygame.draw.ellipse(surf, (220, 255, 225),  (cx - 1, 11,  2,  6))

    # ── Speed stripes ─────────────────────────────────────────────────
    for sy in (28, 35, 42):
        w = 3 + (sy - 28) // 3
        pygame.draw.line(surf, (45, 185, 70),
                         (cx - w, sy), (cx + w, sy), 1)

    # ── Slim nose cannon ──────────────────────────────────────────────
    pygame.draw.rect(surf, (35, 145, 55), (cx - 2, 0, 4, 12), border_radius=1)
    pygame.draw.circle(surf, (140, 255, 155), (cx, 1), 2)

    # ── Single compact engine ─────────────────────────────────────────
    pygame.draw.rect(surf, (12, 65, 28), (cx - 6, 62, 12, 9), border_radius=3)
    pygame.draw.rect(surf, (55, 195, 75), (cx - 6, 62, 12, 9), 1, border_radius=3)
    pygame.draw.ellipse(surf, (80, 250, 110),  (cx - 5, 68, 10, 7))
    pygame.draw.ellipse(surf, (190, 255, 205), (cx - 3, 69,  6, 5))

    return surf


# ---------------------------------------------------------------------------
# Hydra — heavy firepower orange fighter  (68×60)
# ---------------------------------------------------------------------------
def _build_hydra() -> pygame.Surface:
    W, H = 68, 60
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    cy = H // 2

    # ── Wide armoured hull ────────────────────────────────────────────
    hull = [
        (cx,      3),           # nose
        (cx + 10, 12),
        (cx + 26, 18),
        (cx + 28, 42),
        (cx + 16, 52),
        (cx,      55),
        (cx - 16, 52),
        (cx - 28, 42),
        (cx - 26, 18),
        (cx - 10, 12),
    ]
    pygame.draw.polygon(surf, (82, 28, 6), hull)
    pygame.draw.polygon(surf, (255, 120, 50), hull, 2)

    # Armour plating bands
    for py, w in ((20, 40), (30, 46), (40, 40)):
        pygame.draw.line(surf, (150, 55, 15),
                         (cx - w // 2, py), (cx + w // 2, py), 1)
        # Rivet dots
        for rx in (-w // 2, 0, w // 2):
            pygame.draw.circle(surf, (180, 70, 20), (cx + rx, py), 1)

    # ── Short stubby wings with weapon pods ───────────────────────────
    for sign in (-1, 1):
        wing = [
            (cx + sign * 24, 20),
            (cx + sign * 34, 36),
            (cx + sign * 28, 46),
            (cx + sign * 16, 34),
        ]
        pygame.draw.polygon(surf, (65, 20, 4), wing)
        pygame.draw.polygon(surf, (215, 88, 28), wing, 1)
        # Wing cannon pod
        pod_x = cx + sign * 32
        pod_y = 30
        pygame.draw.rect(surf, (48, 14, 3),
                         (pod_x - 4, pod_y - 6, 8, 14), border_radius=2)
        pygame.draw.rect(surf, (200, 80, 20),
                         (pod_x - 4, pod_y - 6, 8, 14), 1, border_radius=2)
        pygame.draw.circle(surf, (255, 85, 5), (pod_x, pod_y - 6), 4)
        pygame.draw.circle(surf, (255, 195, 80),(pod_x, pod_y - 6), 2)

    # ── Wide cockpit (battle visor) ───────────────────────────────────
    pygame.draw.ellipse(surf, (55, 16, 3),      (cx - 10, 14, 20, 12))
    pygame.draw.ellipse(surf, (255, 125, 55),   (cx - 9,  15, 18, 10))
    pygame.draw.ellipse(surf, (255, 215, 170),  (cx - 6,  16, 12,  7))
    pygame.draw.ellipse(surf, (255, 240, 210),  (cx - 3,  17,  6,  4))

    # ── Triple cannon array ───────────────────────────────────────────
    for bx, blen in ((cx, 14), (cx - 12, 10), (cx + 12, 10)):
        pygame.draw.rect(surf, (105, 35, 5), (bx - 3, 0, 6, blen), border_radius=1)
        pygame.draw.rect(surf, (200, 75, 20), (bx - 3, 0, 6, blen), 1, border_radius=1)
        pygame.draw.circle(surf, (255, 95, 15), (bx, 1), 3)
        pygame.draw.circle(surf, (255, 195, 80),(bx, 1), 1)

    # ── Twin wide engine nozzles ──────────────────────────────────────
    for ex in (cx - 13, cx + 13):
        pygame.draw.rect(surf, (95, 32, 5), (ex - 7, 50, 14, 10), border_radius=3)
        pygame.draw.rect(surf, (210, 90, 25),(ex - 7, 50, 14, 10), 1, border_radius=3)
        pygame.draw.ellipse(surf, (255, 135, 40),  (ex - 6, 56, 12,  7))
        pygame.draw.ellipse(surf, (255, 225, 140), (ex - 3, 57,  6,  5))

    return surf


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_BUILDERS = {
    'serpent': _build_serpent,
    'viper':   _build_viper,
    'hydra':   _build_hydra,
}


_SHIP_SCALE = 0.88   # shrink all ships by ~12 %


def build_ship(ship_id: str) -> pygame.Surface:
    fn = _BUILDERS.get(ship_id)
    if fn is None:
        raise ValueError(f"Unknown ship id: {ship_id!r}")
    surf = fn()
    if _SHIP_SCALE != 1.0:
        w, h = surf.get_size()
        surf = pygame.transform.smoothscale(
            surf, (max(1, int(w * _SHIP_SCALE)), max(1, int(h * _SHIP_SCALE))))
    return surf
