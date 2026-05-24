import pygame
import math
import config
from pygame.sprite import Sprite

_font: pygame.font.Font | None = None


def _label_font() -> pygame.font.Font:
    """Lazily create the label font (pygame must be initialised first)."""
    global _font
    if _font is None:
        _font = pygame.font.Font(None, 20)
    return _font


def _build_orb(color: tuple, label: str) -> pygame.Surface:
    """Render a glowing orb with a text label centred inside."""
    SIZE = 32
    cx = cy = SIZE // 2
    r  = SIZE // 2 - 1

    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)

    # Outer soft glow
    pygame.draw.circle(surf, (*color[:3], 60), (cx, cy), r)
    # Main filled circle
    pygame.draw.circle(surf, (*color[:3], 210), (cx, cy), r - 3)
    # Bright inner highlight
    pygame.draw.circle(surf, (255, 255, 255, 130), (cx - 5, cy - 5), 6)
    # Crisp border
    pygame.draw.circle(surf, (255, 255, 255, 190), (cx, cy), r - 3, 2)

    # Label
    lbl = _label_font().render(label, True, (10, 10, 10))
    surf.blit(lbl, lbl.get_rect(center=(cx, cy + 1)))
    return surf


class PowerUp(Sprite):
    """Base class for collectible power-ups that fall from destroyed aliens."""

    DURATION:   float = 0.0          # 0 = one-shot (shield)
    COLOR:      tuple = (200, 200, 200)
    LABEL:      str   = '?'
    FALL_SPEED: float = 62.0         # px/s downward

    def __init__(self, cx: int, cy: int):
        super().__init__()
        self.image = _build_orb(self.COLOR, self.LABEL)
        self.rect  = self.image.get_rect(centerx=cx, top=cy)
        self.y     = float(self.rect.y)
        self._t    = 0.0   # time counter for bobbing

    def update(self, dt: float):
        self._t += dt
        self.y  += self.FALL_SPEED * dt
        # Gentle horizontal bob (±4 px)
        self.rect.x = int(self.rect.centerx - self.image.get_width() // 2
                          + math.sin(self._t * 4.0) * 4)
        self.rect.y = int(self.y)

    def is_off_screen(self) -> bool:
        return self.rect.top > config.SCREEN_HEIGHT


# ---------------------------------------------------------------------------
# Concrete types
# ---------------------------------------------------------------------------

class TripleShotPowerUp(PowerUp):
    """Fire three bullets per shot for DURATION seconds."""
    DURATION = 8.0
    COLOR    = (255, 210, 0)
    LABEL    = '3x'


class ShieldPowerUp(PowerUp):
    """Absorb the next hit (one-shot, no duration timer)."""
    DURATION = 0.0
    COLOR    = (70, 150, 255)
    LABEL    = 'S'


class SlowTimePowerUp(PowerUp):
    """All enemies move at 30 % speed for DURATION seconds."""
    DURATION = 6.0
    COLOR    = (165, 75, 255)
    LABEL    = 'T'
