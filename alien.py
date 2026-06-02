import pygame
import config
import math
import random
from pygame.sprite import Sprite
from config import ALIEN_SPEED, ALIEN_SCALE, ALIEN_STAGGER
from assets import Assets
from settings_manager import Settings


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _scaled_base_image() -> pygame.Surface:
    """Return a freshly scaled alien sprite (never mutate the cached original)."""
    raw = Assets.get_image('image/alien.png')
    w, h = raw.get_size()
    return pygame.transform.scale(raw, (int(w * ALIEN_SCALE), int(h * ALIEN_SCALE)))


def _flash_img(surf: pygame.Surface) -> pygame.Surface:
    s = surf.copy()
    s.fill((160, 160, 160), special_flags=pygame.BLEND_RGB_ADD)
    return s


# ---------------------------------------------------------------------------
# Procedural sprite builders — all sprites face DOWN (nose toward player)
# ---------------------------------------------------------------------------

def _build_armored(size: int = 42) -> tuple[pygame.Surface, pygame.Surface]:
    """Blue hexagonal armored tank. Returns (normal, damaged)."""
    S  = size
    cx = cy = S // 2
    surf = pygame.Surface((S, S), pygame.SRCALPHA)

    # Outer hex hull
    pts = [(cx + round((S//2 - 2) * math.cos(math.radians(i * 60 + 30))),
            cy + round((S//2 - 2) * math.sin(math.radians(i * 60 + 30))))
           for i in range(6)]
    pygame.draw.polygon(surf, (10, 25, 70),   pts)
    pygame.draw.polygon(surf, (50, 120, 220), pts, 2)

    # Armor plates — three horizontal bands
    for py, ph in ((cy - 14, 5), (cy - 4, 5), (cy + 6, 5)):
        pygame.draw.rect(surf, (20, 50, 110), (cx - 14, py, 28, ph), border_radius=2)
        pygame.draw.rect(surf, (60, 140, 230), (cx - 14, py, 28, ph), 1, border_radius=2)

    # Core reactor
    pygame.draw.circle(surf, (0,  40, 120), (cx, cy), 10)
    pygame.draw.circle(surf, (40, 130, 255), (cx, cy),  7)
    pygame.draw.circle(surf, (160, 210, 255),(cx, cy),  3)

    # Side nubs
    for sx in (cx - S//2 + 2, cx + S//2 - 8):
        pygame.draw.rect(surf, (15, 40, 95), (sx, cy - 4, 6, 8), border_radius=2)

    normal  = surf
    damaged = surf.copy()
    # Crack tint: dim blue → dark orange
    damaged = surf.copy()
    damaged.fill((80, 20, 0), special_flags=pygame.BLEND_RGB_ADD)
    # Draw crack lines
    pygame.draw.line(damaged, (180, 80, 0), (cx - 5, cy - 10), (cx + 3, cy + 10), 1)
    pygame.draw.line(damaged, (180, 80, 0), (cx + 3, cy + 2),  (cx + 9, cy + 8),  1)

    return normal, damaged


def _build_zigzag(size: int = 40) -> pygame.Surface:
    """Green crescent/swept-wing agile craft."""
    W, H = size + 4, size
    surf  = pygame.Surface((W, H), pygame.SRCALPHA)
    cx    = W // 2
    cy    = H // 2

    # Crescent body — two overlapping ellipses subtracted
    # Outer crescent shape using polygon
    body = [
        (cx,      H - 4),    # bottom tip (nose pointing down)
        (cx + 16, cy - 4),   # right shoulder
        (cx + 8,  4),        # right top
        (cx,      8),        # top centre
        (cx - 8,  4),        # left top
        (cx - 16, cy - 4),   # left shoulder
    ]
    pygame.draw.polygon(surf, (8, 55, 18),   body)
    pygame.draw.polygon(surf, (60, 220, 90), body, 2)

    # Swept wing tips
    for sign in (-1, 1):
        tip = [
            (cx + sign * 14, cy - 6),
            (cx + sign * 22, cy - 16),
            (cx + sign * 18, cy - 2),
        ]
        pygame.draw.polygon(surf, (5, 40, 12), tip)
        pygame.draw.polygon(surf, (50, 190, 70), tip, 1)

    # Central eye sensor
    pygame.draw.ellipse(surf, (0, 0, 0),      (cx - 5, cy - 8, 10, 8))
    pygame.draw.ellipse(surf, (80, 255, 100), (cx - 4, cy - 7,  8, 6))
    pygame.draw.ellipse(surf, (200, 255, 200),(cx - 2, cy - 6,  4, 3))

    # Engine glow at nose (bottom)
    pygame.draw.circle(surf, (30, 160, 50), (cx, H - 5), 4)
    pygame.draw.circle(surf, (140, 255, 150),(cx, H - 5), 2)

    return surf


def _build_shooter(size: int = 42) -> pygame.Surface:
    """Red angular craft with visible downward cannon."""
    S  = size
    cx = S // 2
    cy = S // 2
    surf = pygame.Surface((S, S), pygame.SRCALPHA)

    # Diamond hull
    hull = [
        (cx,      4),         # top
        (S - 4,   cy - 4),    # right
        (cx + 6,  S - 8),     # bottom-right
        (cx,      S - 4),     # nose tip (bottom)
        (cx - 6,  S - 8),     # bottom-left
        (4,       cy - 4),    # left
    ]
    pygame.draw.polygon(surf, (75, 10, 10), hull)
    pygame.draw.polygon(surf, (220, 50, 50), hull, 2)

    # Cross brace lines
    pygame.draw.line(surf, (160, 30, 30), (4, cy - 4), (S - 4, cy - 4), 1)

    # Side weapon pods
    for sx in (4, S - 12):
        pygame.draw.rect(surf, (55, 8, 8), (sx, cy - 6, 8, 12), border_radius=2)
        pygame.draw.circle(surf, (255, 60, 0), (sx + (0 if sx < cx else 8), cy - 6), 3)

    # Core
    pygame.draw.circle(surf, (100, 15, 15), (cx, cy - 4), 10)
    pygame.draw.circle(surf, (255, 80, 80), (cx, cy - 4),  6)
    pygame.draw.circle(surf, (255, 200, 200),(cx, cy - 4), 2)

    # Sensor eye slit
    pygame.draw.rect(surf, (0, 0, 0),      (cx - 9, cy - 12, 18, 5), border_radius=2)
    pygame.draw.rect(surf, (255, 50, 50),  (cx - 8, cy - 11, 16, 3), border_radius=1)

    # Downward cannon barrel (prominent)
    pygame.draw.rect(surf, (80, 12, 12), (cx - 3, S - 14, 6, 14), border_radius=2)
    pygame.draw.circle(surf, (255, 70, 0), (cx, S - 1), 4)
    pygame.draw.circle(surf, (255, 200, 100),(cx, S - 1), 2)

    return surf


# ---------------------------------------------------------------------------
# Base alien  (1 HP, straight fall, horizontal bounce)
# ---------------------------------------------------------------------------

class Alien(Sprite):
    """Standard alien — falls downward and bounces off screen edges."""

    MAX_HP = 1
    SCORE  = 1

    _FLASH_DURATION = 0.10

    def __init__(self, index: int = 0, speed_mult: float = 1.0):
        super().__init__()

        base = _scaled_base_image()
        self._img_normal = base
        self._img_flash  = _flash_img(base)
        self.image  = self._img_normal
        self.width, self.height = self.image.get_size()

        self.x = float(random.randint(0, max(0, config.SCREEN_WIDTH - self.width)))
        self.y = float(-index * ALIEN_STAGGER)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        self.hp  = self.MAX_HP
        self._hit_flash = 0.0

        self.base_speed = float(ALIEN_SPEED) * speed_mult
        self.speed_y    = self.base_speed
        self.speed_x    = self.base_speed * 0.8 * (1 if index % 2 == 0 else -1)

    def take_hit(self) -> bool:
        self.hp -= 1
        self._hit_flash = self._FLASH_DURATION
        return self.hp <= 0

    def _current_image(self) -> pygame.Surface:
        return self._img_flash if self._hit_flash > 0 else self._img_normal

    def update(self, dt: float):
        if self._hit_flash > 0:
            self._hit_flash = max(0.0, self._hit_flash - dt)
        self.image = self._current_image()

        self.y += self.speed_y * dt
        self.x += self.speed_x * dt

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
# Armored alien  (2 HP, hexagonal blue tank)
# ---------------------------------------------------------------------------

class ArmoredAlien(Alien):
    """Takes two hits to kill. Blue armored hex hull; cracks after first hit."""

    MAX_HP = 2
    SCORE  = 2

    def __init__(self, index: int = 0, speed_mult: float = 1.0):
        super().__init__(index, speed_mult * 0.80)
        normal, damaged = _build_armored(42)
        self._img_normal  = normal
        self._img_damaged = damaged
        self._img_flash   = _flash_img(normal)
        self.image  = self._img_normal
        self.width, self.height = self.image.get_size()
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))
        self.hp = self.MAX_HP

    def _current_image(self) -> pygame.Surface:
        if self._hit_flash > 0:
            return self._img_flash
        return self._img_normal if self.hp == self.MAX_HP else self._img_damaged


# ---------------------------------------------------------------------------
# Zigzag alien  (1 HP, green crescent, sinusoidal drift)
# ---------------------------------------------------------------------------

class ZigzagAlien(Alien):
    """Moves in a smooth wide sine-wave pattern horizontally."""

    SCORE = 2

    def __init__(self, index: int = 0, speed_mult: float = 1.0):
        super().__init__(index, speed_mult)
        sprite = _build_zigzag(40)
        self._img_normal = sprite
        self._img_flash  = _flash_img(sprite)
        self.image  = self._img_normal
        self.width, self.height = self.image.get_size()
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        self._amp   = random.uniform(160, 260)
        self._freq  = random.uniform(0.28, 0.45)
        self._phase = random.uniform(0, math.tau)
        self._time  = 0.0
        self._base_x = config.SCREEN_WIDTH / 2 - self.width / 2

    def update(self, dt: float):
        if self._hit_flash > 0:
            self._hit_flash = max(0.0, self._hit_flash - dt)
        self.image = self._current_image()

        self._time += dt
        self.y += self.speed_y * dt
        raw_x = self._base_x + self._amp * math.sin(
            self._time * self._freq * math.tau + self._phase
        )
        self.x = max(0.0, min(float(config.SCREEN_WIDTH - self.width), raw_x))
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)


# ---------------------------------------------------------------------------
# Shooter alien  (1 HP, red angular craft, fires downward)
# ---------------------------------------------------------------------------

class ShooterAlien(Alien):
    """Fires a bullet downward at random intervals."""

    SCORE = 2

    def __init__(self, index: int = 0, speed_mult: float = 1.0):
        super().__init__(index, speed_mult * 0.85)
        sprite = _build_shooter(42)
        self._img_normal = sprite
        self._img_flash  = _flash_img(sprite)
        self.image  = self._img_normal
        self.width, self.height = self.image.get_size()
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        _m = Settings.get().shooter_interval_mult
        self._shoot_timer: float = random.uniform(2.0, 4.5) * _m
        self._pending: list[tuple[int, int]] = []

    def update(self, dt: float):
        super().update(dt)
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = random.uniform(2.5, 5.5) * Settings.get().shooter_interval_mult
            self._pending.append((self.rect.centerx, self.rect.bottom))

    def drain_shots(self) -> list[tuple[int, int]]:
        shots = self._pending[:]
        self._pending.clear()
        return shots
