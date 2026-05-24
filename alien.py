import pygame
import config
import math
import random
from pygame.sprite import Sprite
from config import ALIEN_SPEED, ALIEN_SCALE, ALIEN_STAGGER
from assets import Assets


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _scaled_base_image() -> pygame.Surface:
    """Return a freshly scaled alien sprite (never mutate the cached original)."""
    raw = Assets.get_image('image/alien.png')
    w, h = raw.get_size()
    return pygame.transform.scale(raw, (int(w * ALIEN_SCALE), int(h * ALIEN_SCALE)))


def _tint(surf: pygame.Surface, rgb: tuple) -> pygame.Surface:
    """Return a copy of *surf* with an additive RGB tint applied.

    pygame.BLEND_RGB_ADD clamps at 255, so it only brightens/tints,
    never darkens.  Alpha channel is untouched.
    """
    s = surf.copy()
    s.fill(rgb, special_flags=pygame.BLEND_RGB_ADD)
    return s


# ---------------------------------------------------------------------------
# Base alien  (1 HP, straight fall, horizontal bounce)
# ---------------------------------------------------------------------------

class Alien(Sprite):
    """Standard alien — falls downward and bounces off screen edges."""

    MAX_HP = 1
    SCORE  = 1   # points awarded on kill

    _FLASH_DURATION = 0.10   # seconds the hit-flash lasts

    def __init__(self, index: int = 0, speed_mult: float = 1.0):
        super().__init__()

        base = _scaled_base_image()
        self._img_normal = base
        self._img_flash  = _tint(base, (170, 170, 170))   # bright white-ish flash
        self.image  = self._img_normal
        self.width, self.height = self.image.get_size()

        # Stagger starting positions so aliens don't all enter at once
        self.x = float(random.randint(0, max(0, config.SCREEN_WIDTH - self.width)))
        self.y = float(-index * ALIEN_STAGGER)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        self.hp  = self.MAX_HP
        self._hit_flash = 0.0   # seconds remaining for flash

        self.base_speed = float(ALIEN_SPEED) * speed_mult
        self.speed_y    = self.base_speed
        # Alternate horizontal direction so aliens don't all overlap
        self.speed_x    = self.base_speed * 0.8 * (1 if index % 2 == 0 else -1)

    # ------------------------------------------------------------------

    def take_hit(self) -> bool:
        """Reduce HP by 1. Returns True when the alien is killed."""
        self.hp -= 1
        self._hit_flash = self._FLASH_DURATION
        return self.hp <= 0

    def _current_image(self) -> pygame.Surface:
        return self._img_flash if self._hit_flash > 0 else self._img_normal

    def update(self, dt: float):
        # Flash timer
        if self._hit_flash > 0:
            self._hit_flash = max(0.0, self._hit_flash - dt)
        self.image = self._current_image()

        # Movement
        self.y += self.speed_y * dt
        self.x += self.speed_x * dt

        # Horizontal bounce
        if self.x <= 0:
            self.x = 0.0
            self.speed_x = abs(self.speed_x)
        elif self.x >= config.SCREEN_WIDTH - self.width:
            self.x = float(config.SCREEN_WIDTH - self.width)
            self.speed_x = -abs(self.speed_x)

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def has_reached_fighter(self, fighter) -> bool:
        return self.rect.colliderect(fighter.rect)

    def is_off_screen(self) -> bool:
        return self.rect.top > config.SCREEN_HEIGHT


# ---------------------------------------------------------------------------
# Armored alien  (2 HP, blue tint, looks damaged after first hit)
# ---------------------------------------------------------------------------

class ArmoredAlien(Alien):
    """Takes two hits to kill. Glows blue; shows a reddish-brown crack after first hit."""

    MAX_HP = 2
    SCORE  = 2

    def __init__(self, index: int = 0, speed_mult: float = 1.0):
        # Armored aliens are 20 % slower to compensate for extra HP
        super().__init__(index, speed_mult * 0.80)

        base = _scaled_base_image()
        self._img_normal  = _tint(base, (0,  0, 130))    # blue
        self._img_damaged = _tint(base, (70, 25,  0))    # cracked / reddish
        self._img_flash   = _tint(base, (170, 170, 170))
        self.image = self._img_normal
        self.hp = self.MAX_HP

    def _current_image(self) -> pygame.Surface:
        if self._hit_flash > 0:
            return self._img_flash
        return self._img_normal if self.hp == self.MAX_HP else self._img_damaged


# ---------------------------------------------------------------------------
# Zigzag alien  (1 HP, green tint, sinusoidal horizontal drift)
# ---------------------------------------------------------------------------

class ZigzagAlien(Alien):
    """Moves in a sine-wave pattern horizontally instead of bouncing."""

    SCORE = 2

    def __init__(self, index: int = 0, speed_mult: float = 1.0):
        super().__init__(index, speed_mult)

        base = _scaled_base_image()
        self._img_normal = _tint(base, (0, 110, 40))   # green
        self._img_flash  = _tint(base, (170, 170, 170))
        self.image = self._img_normal

        self._amp   = random.uniform(75, 130)             # pixel amplitude
        self._freq  = random.uniform(1.1, 2.0)            # Hz
        self._phase = random.uniform(0, math.tau)
        self._time  = 0.0
        self._base_x = self.x   # sine oscillates around this X

    def update(self, dt: float):
        if self._hit_flash > 0:
            self._hit_flash = max(0.0, self._hit_flash - dt)
        self.image = self._current_image()

        self._time += dt
        self.y += self.speed_y * dt
        # Sinusoidal X — ignores the normal horizontal-bounce logic
        raw_x = self._base_x + self._amp * math.sin(
            self._time * self._freq * math.tau + self._phase
        )
        self.x = max(0.0, min(float(config.SCREEN_WIDTH - self.width), raw_x))

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)


# ---------------------------------------------------------------------------
# Shooter alien  (1 HP, red tint, periodically fires back)
# ---------------------------------------------------------------------------

class ShooterAlien(Alien):
    """Fires a bullet downward at random intervals."""

    SCORE = 3

    def __init__(self, index: int = 0, speed_mult: float = 1.0):
        # Slightly slower than normal aliens
        super().__init__(index, speed_mult * 0.85)

        base = _scaled_base_image()
        self._img_normal = _tint(base, (140, 0, 0))    # red
        self._img_flash  = _tint(base, (170, 170, 170))
        self.image = self._img_normal

        # First shot fires after a random delay so not all shooters fire at once
        self._shoot_timer: float = random.uniform(2.0, 4.5)
        self._pending: list[tuple[int, int]] = []   # (cx, cy) spawn points

    def update(self, dt: float):
        super().update(dt)
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = random.uniform(2.5, 5.5)
            self._pending.append((self.rect.centerx, self.rect.bottom))

    def drain_shots(self) -> list[tuple[int, int]]:
        """Return pending bullet spawn positions and clear the queue."""
        shots = self._pending[:]
        self._pending.clear()
        return shots
