"""Procedural ship sprite builder — high-detail versions.

  serpent — balanced fighter    (cobalt interceptor, swept wings, twin engines)
  viper   — speed & agility     (emerald interceptor, swept wings, twin thrusters)
  hydra   — heavy firepower     (amber gunship, layered armour, weapon pods)

All sprites face UP (nose at top).
"""
import pygame


# ---------------------------------------------------------------------------
# Serpent — balanced blue fighter  (52×68)
# ---------------------------------------------------------------------------
def _build_serpent() -> pygame.Surface:
    # Original canvas and gameplay footprint; only the drawn hull changes.
    W, H = 52, 68
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    edge, light, seam = (76, 173, 227), (168, 232, 255), (10, 31, 54)

    # Broad swept wings and pale leading edges define the balanced fighter.
    for sign in (-1, 1):
        def point(x, y):
            return cx + sign * x, y

        wing = [point(7, 22), point(24, 36), point(24, 46),
                point(18, 44), point(12, 56), point(6, 48)]
        pygame.draw.polygon(surf, (24, 61, 100), wing)
        pygame.draw.polygon(surf, edge, wing, 1)
        pygame.draw.polygon(surf, (43, 104, 151),
                            [point(8, 25), point(21, 37), point(15, 40), point(9, 47)])
        pygame.draw.line(surf, light, point(9, 26), point(22, 37), 1)
        pygame.draw.line(surf, seam, point(10, 38), point(19, 43), 2)
        pygame.draw.line(surf, (120, 219, 255), point(24, 38), point(24, 42), 2)

        # Armoured engine shoulders flank the narrow tail.
        pod = [point(7, 43), point(14, 46), point(15, 57),
               point(12, 63), point(7, 63), point(5, 55)]
        pygame.draw.polygon(surf, seam, pod)
        pygame.draw.polygon(surf, (54, 113, 158), pod, 1)
        pygame.draw.line(surf, (101, 172, 214), point(10, 47), point(11, 55), 2)
        ex = cx + sign * 10
        pygame.draw.rect(surf, (27, 68, 108), (ex - 4, 57, 8, 7), border_radius=2)
        pygame.draw.rect(surf, (84, 195, 255), (ex - 3, 61, 6, 4), border_radius=2)
        pygame.draw.rect(surf, (207, 246, 255), (ex - 1, 62, 2, 3))

    body = [(cx, 2), (cx + 7, 13), (cx + 10, 29), (cx + 8, 46),
            (cx + 4, 57), (cx - 4, 57), (cx - 8, 46), (cx - 10, 29), (cx - 7, 13)]
    pygame.draw.polygon(surf, (29, 74, 116), body)
    pygame.draw.polygon(surf, edge, body, 1)
    pygame.draw.polygon(surf, (58, 122, 168),
                        [(cx, 5), (cx, 51), (cx - 5, 46), (cx - 7, 28), (cx - 4, 14)])
    pygame.draw.line(surf, light, (cx, 4), (cx, 12), 1)
    pygame.draw.line(surf, (113, 197, 238), (cx, 35), (cx, 51), 1)

    # A hexagonal canopy replaces the old flat glowing oval.
    canopy = [(cx, 13), (cx + 6, 20), (cx + 5, 28),
              (cx, 32), (cx - 5, 28), (cx - 6, 20)]
    pygame.draw.polygon(surf, seam, canopy)
    pygame.draw.polygon(surf, (94, 191, 227),
                        [(cx, 15), (cx + 4, 20), (cx + 3, 27), (cx, 29), (cx - 3, 27), (cx - 4, 20)])
    pygame.draw.polygon(surf, (207, 247, 255),
                        [(cx, 16), (cx + 2, 20), (cx, 26), (cx - 2, 23), (cx - 2, 20)])
    for sign in (-1, 1):
        for y in (36, 40, 44):
            pygame.draw.line(surf, seam, (cx + sign * 4, y), (cx + sign * 7, y + 1), 1)
    pygame.draw.polygon(surf, (16, 44, 73), [(cx - 3, 50), (cx + 3, 50), (cx + 2, 60), (cx - 2, 60)])
    pygame.draw.line(surf, edge, (cx, 52), (cx, 60), 1)
    return surf


# ---------------------------------------------------------------------------
# Viper — speed / agility green fighter  (46×72)
# ---------------------------------------------------------------------------
def _build_viper() -> pygame.Surface:
    # Keep the original footprint so the visual refresh does not change collisions.
    W, H = 46, 72
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    edge = (66, 207, 119)
    light = (153, 255, 191)
    seam = (12, 43, 34)

    # Swept, faceted wings: a broad silhouette without the old needle-like tail.
    for sign in (-1, 1):
        def point(x, y):
            return cx + sign * x, y

        wing = [point(6, 23), point(21, 39), point(21, 49),
                point(14, 44), point(10, 58), point(4, 52)]
        pygame.draw.polygon(surf, (16, 73, 49), wing)
        pygame.draw.polygon(surf, edge, wing, 1)
        pygame.draw.polygon(surf, (31, 112, 69),
                            [point(7, 28), point(18, 40), point(12, 42), point(7, 49)])
        pygame.draw.line(surf, light, point(8, 28), point(19, 40), 1)
        pygame.draw.line(surf, seam, point(8, 39), point(15, 45), 2)
        # Small navigation lights at the outer edge.
        pygame.draw.line(surf, (109, 255, 156), point(21, 41), point(21, 45), 2)

        # Engine pods sit inside the outline, with dark separation from the hull.
        pod = [point(7, 46), point(13, 48), point(14, 60),
               point(12, 65), point(7, 65), point(5, 59)]
        pygame.draw.polygon(surf, seam, pod)
        pygame.draw.polygon(surf, (44, 128, 87), pod, 1)
        pygame.draw.line(surf, (72, 163, 113), point(10, 50), point(11, 58), 2)
        ex = cx + sign * 10
        pygame.draw.rect(surf, (36, 110, 77), (ex - 4, 60, 8, 6), border_radius=2)
        pygame.draw.rect(surf, (75, 242, 159), (ex - 3, 64, 6, 4), border_radius=2)
        pygame.draw.rect(surf, (208, 255, 226), (ex - 1, 65, 2, 3))

    # Tapered fuselage with a raised spine and two distinct armour facets.
    body = [(cx, 2), (cx + 5, 14), (cx + 8, 34), (cx + 6, 52),
            (cx + 3, 61), (cx - 3, 61), (cx - 6, 52), (cx - 8, 34), (cx - 5, 14)]
    pygame.draw.polygon(surf, (22, 82, 56), body)
    pygame.draw.polygon(surf, edge, body, 1)
    pygame.draw.polygon(surf, (43, 132, 81),
                        [(cx, 5), (cx, 55), (cx - 4, 49), (cx - 6, 31), (cx - 3, 14)])
    pygame.draw.line(surf, light, (cx, 4), (cx, 15), 1)
    pygame.draw.line(surf, (94, 210, 134), (cx, 36), (cx, 56), 1)

    # A substantial mint-glass canopy stays readable in the 48 px menu preview.
    canopy = [(cx, 15), (cx + 4, 21), (cx + 4, 31),
              (cx, 35), (cx - 4, 31), (cx - 4, 21)]
    pygame.draw.polygon(surf, (7, 35, 33), canopy)
    pygame.draw.polygon(surf, (115, 230, 172),
                        [(cx, 17), (cx + 3, 22), (cx + 3, 30), (cx, 32), (cx - 3, 30), (cx - 3, 22)])
    pygame.draw.polygon(surf, (213, 255, 226),
                        [(cx, 18), (cx + 1, 22), (cx, 29), (cx - 2, 26), (cx - 2, 22)])

    # Rear air intakes and a short centre keel finish the mechanical silhouette.
    for sign in (-1, 1):
        for y in (39, 43, 47):
            pygame.draw.line(surf, seam, (cx + sign * 3, y), (cx + sign * 5, y + 1), 1)
    pygame.draw.polygon(surf, (10, 49, 38), [(cx - 3, 54), (cx + 3, 54), (cx + 2, 64), (cx - 2, 64)])
    pygame.draw.line(surf, edge, (cx, 56), (cx, 63), 1)
    return surf


# ---------------------------------------------------------------------------
# Hydra — heavy firepower orange fighter  (68×60)
# ---------------------------------------------------------------------------
def _build_hydra() -> pygame.Surface:
    W, H = 68, 60
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    edge, light, seam = (221, 128, 57), (255, 217, 151), (49, 28, 23)

    # A wide chassis connects two substantial weapon and engine outriggers.
    chassis = [(cx - 14, 18), (cx + 14, 18), (cx + 30, 29),
               (cx + 28, 44), (cx + 16, 53), (cx - 16, 53), (cx - 28, 44), (cx - 30, 29)]
    pygame.draw.polygon(surf, (78, 44, 30), chassis)
    pygame.draw.polygon(surf, (149, 86, 43), chassis, 1)
    for sign in (-1, 1):
        def point(x, y):
            return cx + sign * x, y

        shoulder = [point(15, 15), point(25, 17), point(32, 29),
                    point(30, 43), point(22, 48), point(13, 39)]
        pygame.draw.polygon(surf, (113, 61, 32), shoulder)
        pygame.draw.polygon(surf, edge, shoulder, 1)
        pygame.draw.polygon(surf, (170, 96, 43),
                            [point(17, 18), point(23, 20), point(29, 29), point(20, 32), point(15, 27)])
        pygame.draw.line(surf, light, point(18, 18), point(25, 22), 1)
        pygame.draw.line(surf, seam, point(18, 33), point(28, 35), 2)
        pygame.draw.line(surf, (255, 161, 80), point(31, 30), point(30, 37), 2)

        # Forward-facing gun pods reinforce Hydra's heavy-firepower identity.
        gx = cx + sign * 23
        pygame.draw.rect(surf, seam, (gx - 4, 8, 8, 22), border_radius=2)
        pygame.draw.rect(surf, (187, 110, 55), (gx - 3, 9, 6, 19), 1, border_radius=1)
        pygame.draw.rect(surf, (239, 174, 96), (gx - 1, 8, 2, 15))
        pygame.draw.rect(surf, (255, 224, 165), (gx - 2, 8, 4, 3))
        pygame.draw.rect(surf, (63, 38, 28), (gx - 4, 24, 8, 7), border_radius=2)

        # The broad exhausts are recessed into separate armoured engine pods.
        ex = cx + sign * 19
        pod = [point(14, 39), point(25, 41), point(26, 51),
               point(23, 57), point(15, 57), point(12, 49)]
        pygame.draw.polygon(surf, seam, pod)
        pygame.draw.polygon(surf, (157, 91, 47), pod, 1)
        for y in (44, 47):
            pygame.draw.line(surf, (108, 66, 39), (ex - 3, y), (ex + 3, y), 1)
        pygame.draw.rect(surf, (123, 66, 34), (ex - 5, 50, 10, 7), border_radius=2)
        pygame.draw.rect(surf, (255, 155, 66), (ex - 4, 54, 8, 4), border_radius=2)
        pygame.draw.rect(surf, (255, 235, 181), (ex - 2, 55, 4, 3))

    # Raised central citadel, layered rather than the old round outline.
    hull = [(cx, 5), (cx + 11, 13), (cx + 15, 28), (cx + 12, 44),
            (cx + 6, 52), (cx - 6, 52), (cx - 12, 44), (cx - 15, 28), (cx - 11, 13)]
    pygame.draw.polygon(surf, (132, 72, 34), hull)
    pygame.draw.polygon(surf, edge, hull, 1)
    pygame.draw.polygon(surf, (185, 108, 49),
                        [(cx, 7), (cx, 45), (cx - 8, 40), (cx - 12, 28), (cx - 8, 15)])
    pygame.draw.line(surf, light, (cx, 7), (cx, 13), 1)
    pygame.draw.line(surf, (230, 153, 78), (cx, 31), (cx, 45), 1)

    # Wide angular battle visor, set behind the centre cannon.
    visor = [(cx - 8, 17), (cx + 8, 17), (cx + 10, 24),
             (cx + 5, 29), (cx - 5, 29), (cx - 10, 24)]
    pygame.draw.polygon(surf, seam, visor)
    pygame.draw.polygon(surf, (255, 183, 91),
                        [(cx - 6, 19), (cx + 6, 19), (cx + 7, 23), (cx + 3, 26), (cx - 3, 26), (cx - 7, 23)])
    pygame.draw.polygon(surf, (255, 240, 199),
                        [(cx - 4, 19), (cx + 4, 19), (cx + 2, 23), (cx - 3, 23)])
    pygame.draw.rect(surf, seam, (cx - 3, 1, 6, 14), border_radius=1)
    pygame.draw.rect(surf, (242, 171, 91), (cx - 1, 2, 2, 10))
    pygame.draw.rect(surf, light, (cx - 2, 1, 4, 3))
    for sign in (-1, 1):
        for y in (33, 37, 41):
            pygame.draw.line(surf, seam, (cx + sign * 5, y), (cx + sign * 9, y + 1), 1)
    pygame.draw.polygon(surf, (81, 45, 29), [(cx - 5, 45), (cx + 5, 45), (cx + 3, 53), (cx - 3, 53)])
    pygame.draw.line(surf, edge, (cx, 47), (cx, 52), 1)
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
