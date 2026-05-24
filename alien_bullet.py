import pygame
import config
from pygame.sprite import Sprite


class AlienBullet(Sprite):
    """A projectile fired downward (optionally at an angle) by aliens or the boss.

    *vx* and *vy* are pixel-per-second velocity components.  Defaults produce
    a straight downward shot at 200 px/s, matching the original ShooterAlien
    behaviour.  The boss passes angled velocities for spread / fan patterns.
    """

    def __init__(self, cx: int, cy: int,
                 vx: float = 0.0, vy: float = 200.0):
        super().__init__()

        surf = pygame.Surface((6, 18), pygame.SRCALPHA)
        pygame.draw.rect(surf, (220,  50,  50), (1, 0, 4, 18), border_radius=2)
        pygame.draw.rect(surf, (255, 190, 100), (2, 3, 2, 10), border_radius=1)
        self.image = surf
        self.rect  = self.image.get_rect(centerx=cx, top=cy)
        self.x     = float(self.rect.x)
        self.y     = float(self.rect.y)
        self.vx    = vx
        self.vy    = vy

    def update(self, dt: float):
        self.x     += self.vx * dt
        self.y     += self.vy * dt
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def is_off_screen(self) -> bool:
        return (self.rect.top  >  config.SCREEN_HEIGHT or
                self.rect.right < 0 or
                self.rect.left  > config.SCREEN_WIDTH)
