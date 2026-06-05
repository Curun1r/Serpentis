import pygame
import config
import math
import random
from pygame.sprite import Sprite
from settings_manager import Settings


# ---------------------------------------------------------------------------
# Sprite generation — one builder per boss tier
# ---------------------------------------------------------------------------

def _build_boss1() -> pygame.Surface:
    """Tier-1 boss: purple hexagon — Phantom.
    Classic design, hexagonal hull, twin eye sensors, triple engine nozzles."""
    SIZE = 120
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    cx = cy = SIZE // 2

    # Main hull (dark hexagon)
    hull = [(cx + round(54 * math.cos(math.radians(i * 60 - 90))),
             cy + round(54 * math.sin(math.radians(i * 60 - 90))))
            for i in range(6)]
    pygame.draw.polygon(surf, (50, 8, 75),    hull)
    pygame.draw.polygon(surf, (150, 30, 200), hull, 2)

    # Side wing cannons
    for sx in (4, SIZE - 34):
        pygame.draw.rect(surf, (38, 5, 62), (sx, cy - 9, 30, 18), border_radius=4)
    pygame.draw.circle(surf, (255, 70, 70),  (2,        cy), 6)
    pygame.draw.circle(surf, (255, 70, 70),  (SIZE - 2, cy), 6)
    pygame.draw.circle(surf, (255, 180, 80), (2,        cy), 3)
    pygame.draw.circle(surf, (255, 180, 80), (SIZE - 2, cy), 3)

    # Energy core
    pygame.draw.circle(surf, (75,  0, 120),  (cx, cy), 22)
    pygame.draw.circle(surf, (185, 45, 240), (cx, cy), 16)
    pygame.draw.circle(surf, (235, 170, 255),(cx, cy),  8)
    pygame.draw.circle(surf, (255, 245, 255),(cx, cy),  3)

    # Sensor eyes
    for ex in (cx - 18, cx + 18):
        pygame.draw.circle(surf, (0, 0, 0),       (ex, cy - 15), 9)
        pygame.draw.circle(surf, (255, 30, 30),   (ex, cy - 15), 6)
        pygame.draw.circle(surf, (255, 210, 210), (ex, cy - 15), 2)

    # Top gun barrel
    pygame.draw.rect(surf, (78, 0, 128), (cx - 12, 5, 24, 16), border_radius=3)
    pygame.draw.circle(surf, (255, 55, 55), (cx, 5), 6)

    # Bottom engine nozzles (3)
    for bx in (cx - 22, cx, cx + 22):
        pygame.draw.rect(surf, (105, 0, 162), (bx - 6, 98, 12, 16), border_radius=3)
        pygame.draw.circle(surf, (205, 105, 255), (bx, 114), 5)
        pygame.draw.circle(surf, (255, 230, 255), (bx, 114), 2)

    return surf


def _build_boss2() -> pygame.Surface:
    """Tier-2 boss: orange angular destroyer — Ravager.
    Aggressive arrowhead silhouette, four plasma cannons, dual exhaust."""
    SIZE = 120
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    cx = cy = SIZE // 2

    # Main diamond / arrowhead hull
    hull = [(cx, 6), (SIZE - 8, cy - 10), (cx, cy + 28), (8, cy - 10)]
    pygame.draw.polygon(surf, (110, 35, 5),   hull)
    pygame.draw.polygon(surf, (255, 110, 20), hull, 2)

    # Cross brace lines
    pygame.draw.line(surf, (200, 80, 10), (8, cy - 10), (SIZE - 8, cy - 10), 2)
    pygame.draw.line(surf, (200, 80, 10), (cx, 6), (cx, cy + 28), 2)

    # Four wing stubs
    for pts in [
        [(8,  cy - 10), (0,  cy - 30), (28, cy - 10)],   # top-left
        [(SIZE - 8, cy - 10), (SIZE, cy - 30), (SIZE - 28, cy - 10)],  # top-right
    ]:
        pygame.draw.polygon(surf, (85, 22, 0), pts)
        pygame.draw.polygon(surf, (255, 90, 10), pts, 1)

    # Plasma core
    pygame.draw.circle(surf, (130, 45, 0),   (cx, cy - 4), 20)
    pygame.draw.circle(surf, (255, 130, 20), (cx, cy - 4), 13)
    pygame.draw.circle(surf, (255, 220, 80), (cx, cy - 4),  6)
    pygame.draw.circle(surf, (255, 255, 220),(cx, cy - 4),  2)

    # Four plasma cannon tips (two on each side)
    for px, py in [(0, cy - 30), (SIZE, cy - 30), (0, cy + 10), (SIZE, cy + 10)]:
        pygame.draw.circle(surf, (255, 60, 0),  (px, py), 5)
        pygame.draw.circle(surf, (255, 200, 50),(px, py), 2)

    # Sensor slit (single horizontal eye)
    pygame.draw.rect(surf, (0, 0, 0),       (cx - 22, cy - 22, 44, 8), border_radius=3)
    pygame.draw.rect(surf, (255, 100, 0),   (cx - 20, cy - 21, 40, 6), border_radius=2)
    # Pupils
    for px in (cx - 8, cx + 8):
        pygame.draw.circle(surf, (255, 255, 80), (px, cy - 18), 3)

    # Top gun
    pygame.draw.rect(surf, (100, 30, 0), (cx - 8, 0, 16, 12), border_radius=2)
    pygame.draw.circle(surf, (255, 70, 0), (cx, 0), 5)

    # Dual rear exhaust
    for bx in (cx - 14, cx + 14):
        pygame.draw.rect(surf, (140, 50, 0), (bx - 7, 96, 14, 18), border_radius=3)
        pygame.draw.circle(surf, (255, 150, 30), (bx, 114), 6)
        pygame.draw.circle(surf, (255, 240, 130), (bx, 114), 2)

    return surf


def _build_boss3() -> pygame.Surface:
    """Tier-3 boss: teal/cyan overlord — Leviathan.
    Imposing octagonal fortress, six weapon ports, four exhaust clusters."""
    SIZE = 130
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    cx = cy = SIZE // 2

    # Outer octagon ring
    oct_pts = [(cx + round(58 * math.cos(math.radians(i * 45 - 22.5))),
                cy + round(58 * math.sin(math.radians(i * 45 - 22.5))))
               for i in range(8)]
    pygame.draw.polygon(surf, (5, 55, 70),    oct_pts)
    pygame.draw.polygon(surf, (0, 200, 230),  oct_pts, 2)

    # Inner octagon
    inn_pts = [(cx + round(38 * math.cos(math.radians(i * 45 - 22.5))),
                cy + round(38 * math.sin(math.radians(i * 45 - 22.5))))
               for i in range(8)]
    pygame.draw.polygon(surf, (0, 75, 95), inn_pts)
    pygame.draw.polygon(surf, (0, 180, 210), inn_pts, 1)

    # Eight radial struts
    for i in range(8):
        ang = math.radians(i * 45 - 22.5)
        x1  = cx + round(38 * math.cos(ang))
        y1  = cy + round(38 * math.sin(ang))
        x2  = cx + round(56 * math.cos(ang))
        y2  = cy + round(56 * math.sin(ang))
        pygame.draw.line(surf, (0, 160, 190), (x1, y1), (x2, y2), 2)

    # Core reactor
    pygame.draw.circle(surf, (0,  60, 80),   (cx, cy), 26)
    pygame.draw.circle(surf, (0, 190, 220),  (cx, cy), 18)
    pygame.draw.circle(surf, (80, 240, 255), (cx, cy),  9)
    pygame.draw.circle(surf, (220, 255, 255),(cx, cy),  4)

    # Six weapon emitters (cardinal + diagonal top)
    emitters = [
        (cx,           8),            # top centre
        (cx - 40,      cy - 40),      # top-left
        (cx + 40,      cy - 40),      # top-right
        (0,            cy),           # left
        (SIZE,         cy),           # right
        (cx,           cy + 38),      # bottom
    ]
    for ex, ey in emitters:
        pygame.draw.circle(surf, (0, 0, 0),         (ex, ey), 6)
        pygame.draw.circle(surf, (0, 210, 240),     (ex, ey), 4)
        pygame.draw.circle(surf, (180, 255, 255),   (ex, ey), 2)

    # Triple sensor eyes
    for ex in (cx - 14, cx, cx + 14):
        pygame.draw.circle(surf, (0, 0, 0),       (ex, cy - 12), 5)
        pygame.draw.circle(surf, (0, 230, 255),   (ex, cy - 12), 3)
        pygame.draw.circle(surf, (200, 255, 255), (ex, cy - 12), 1)

    # Quad exhaust nozzles
    for bx in (cx - 26, cx - 9, cx + 9, cx + 26):
        pygame.draw.rect(surf, (0, 80, 100), (bx - 5, SIZE - 20, 10, 16), border_radius=3)
        pygame.draw.circle(surf, (0, 210, 240),   (bx, SIZE - 4), 5)
        pygame.draw.circle(surf, (180, 255, 255), (bx, SIZE - 4), 2)

    return surf


# Map tier → builder
_TIER_BUILDERS = {
    1: _build_boss1,
    2: _build_boss2,
    3: _build_boss3,
}

# Hit-box shrink factor — the visible hull is smaller than the full bounding rect
# (wings/nozzles stick out but shouldn't register hits)
_HIT_SHRINK = 0.60


# ---------------------------------------------------------------------------
# Boss class
# ---------------------------------------------------------------------------

class Boss(Sprite):
    """Large boss enemy that appears on waves 5, 10, 15 …

    Visual tier (and therefore sprite model) is determined by which boss
    encounter this is:
        tier 1 — wave  5, 20, 35 … → purple Phantom
        tier 2 — wave 10, 25, 40 … → orange Ravager
        tier 3 — wave 15, 30, 45 … → teal Leviathan

    Three combat phases driven by remaining HP fraction:
        Phase 1 (> 66 %) — 1 centre bullet
        Phase 2 (33–66 %) — 3-bullet spread
        Phase 3 (< 33 %)  — 5-bullet fan
    """

    def __init__(self, wave: int):
        super().__init__()

        base_hp     = 15 + wave * 3     # wave 5 → 30 HP, wave 10 → 45 HP …
        self.max_hp = max(1, int(base_hp * Settings.get().boss_hp_mult))
        self.hp     = self.max_hp
        self.SCORE  = 10

        # Which visual to use (cycles 1→2→3→1→2→3…)
        encounter = wave // 5            # 1, 2, 3, 4, 5 …
        tier      = ((encounter - 1) % 3) + 1   # 1, 2, 3, 1, 2, 3 …
        self._tier = tier

        # Scale sprite slightly on later appearances (max +60 %)
        scale = 1.0 + min((encounter - 1) * 0.15, 0.60)
        base  = _TIER_BUILDERS[tier]()
        if scale > 1.01:
            w, h = base.get_size()
            base = pygame.transform.smoothscale(base, (int(w * scale), int(h * scale)))

        self._img_normal = base
        self._img_flash  = base.copy()
        self._img_flash.fill((130, 130, 130), special_flags=pygame.BLEND_RGB_ADD)
        self.image  = self._img_normal
        self.width, self.height = self.image.get_size()

        self._hit_flash          = 0.0
        self._HIT_FLASH_DURATION = 0.10

        # Full bounding rect (used for rendering and movement clamping)
        self.x = float(config.SCREEN_WIDTH // 2 - self.width // 2)
        self.y = float(18)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        # Smaller hit-rect centred on the sprite — reduces false-positive hits
        # from bullets passing through wing-tips / nozzle protrusions
        hw = int(self.width  * _HIT_SHRINK)
        hh = int(self.height * _HIT_SHRINK)
        self.hit_rect = pygame.Rect(0, 0, hw, hh)
        self.hit_rect.center = self.rect.center

        # Horizontal movement
        self.speed_x = 75.0 + wave * 3.5

        # Shooting state
        self._shoot_timer  = 2.0
        self._pending: list[tuple] = []

    # ------------------------------------------------------------------

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp

    @property
    def _phase(self) -> int:
        r = self.hp_ratio
        if r > 0.66: return 1
        if r > 0.33: return 2
        return 3

    def take_hit(self, damage: int = 1) -> bool:
        """Reduce HP. Returns True when the boss is killed."""
        self.hp = max(0, self.hp - damage)
        self._hit_flash = self._HIT_FLASH_DURATION
        return self.hp <= 0

    def update(self, dt: float):
        # Hit flash
        if self._hit_flash > 0:
            self._hit_flash = max(0.0, self._hit_flash - dt)
        self.image = self._img_flash if self._hit_flash > 0 else self._img_normal

        # Tier-specific movement speed scaling
        move_scale = {1: 1.0, 2: 1.3, 3: 0.75}[self._tier]
        self.x += self.speed_x * move_scale * dt
        if self.x <= 0:
            self.x = 0.0
            self.speed_x = abs(self.speed_x)
        elif self.x >= config.SCREEN_WIDTH - self.width:
            self.x = float(config.SCREEN_WIDTH - self.width)
            self.speed_x = -abs(self.speed_x)
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.hit_rect.center = self.rect.center

        # Shooting interval varies by tier and phase
        intervals = {
            1: {1: 3.2, 2: 2.2, 3: 1.8},   # Phantom — spread shots, standard tempo
            2: {1: 2.8, 2: 1.6, 3: 1.0},   # Ravager — fast side-burst, aggressive
            3: {1: 4.0, 2: 3.0, 3: 2.2},   # Leviathan — slow but wide star-burst
        }
        interval = intervals[self._tier][self._phase]
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = interval + random.uniform(-0.15, 0.15)
            self._queue_shots()

    def _queue_shots(self):
        """Tier-specific attack patterns:
        Tier 1 Phantom  — classic spread, 3-phase fan
        Tier 2 Ravager  — diagonal side-bursts + aimed centre shot
        Tier 3 Leviathan— 360° star-burst (more bullets in later phases)
        """
        cx = self.rect.centerx
        cy = self.rect.bottom - 4
        p  = self._phase

        if self._tier == 1:
            # Phantom: downward spread fan (classic)
            if p == 1:
                self._pending.append((cx, cy, 0.0, 205.0))
            elif p == 2:
                for ox in (-28, 0, 28):
                    self._pending.append((cx + ox, cy, 0.0, 215.0))
            else:
                for ox in (-48, -24, 0, 24, 48):
                    self._pending.append((cx + ox, cy, ox * 1.6, 225.0))

        elif self._tier == 2:
            # Ravager: diagonal side-shots + centre aimed burst
            if p == 1:
                # Two diagonal shots outward
                for vx in (-120.0, 120.0):
                    self._pending.append((cx, cy, vx, 180.0))
            elif p == 2:
                # Diagonal + centre
                for vx in (-140.0, 0.0, 140.0):
                    self._pending.append((cx, cy, vx, 200.0))
            else:
                # Full diagonal X-pattern: 4 diagonals + centre
                for vx, vy in [(-160, 200), (-80, 210), (0, 220), (80, 210), (160, 200)]:
                    self._pending.append((cx, cy, vx, vy))

        elif self._tier == 3:
            # Leviathan: star-burst in all directions
            if p == 1:
                count = 6
            elif p == 2:
                count = 8
            else:
                count = 12
            speed = 190.0
            for i in range(count):
                angle = math.radians(i * 360 / count - 90)   # start pointing down
                vx = math.sin(angle) * speed
                vy = math.cos(angle) * speed * -1
                # Only fire downward hemisphere (vy > 0 or close to horizontal)
                if vy >= -30:
                    self._pending.append((cx, cy, vx, max(vy, 80.0)))

    def drain_shots(self) -> list[tuple]:
        """Return (cx, cy, vx, vy) tuples and clear the queue."""
        shots = self._pending[:]
        self._pending.clear()
        return shots


# ---------------------------------------------------------------------------
# MiniBoss — appears on waves 3, 8, 13 …  (wave % 5 == 3)
# ---------------------------------------------------------------------------

def _build_miniboss() -> pygame.Surface:
    """Compact triangular raider — teal/yellow, single cannon, fast."""
    SIZE = 72
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    cx   = SIZE // 2
    cy   = SIZE // 2

    # Main arrowhead body
    body = [(cx, 6), (SIZE - 8, SIZE - 10), (cx, SIZE - 20), (8, SIZE - 10)]
    pygame.draw.polygon(surf, (20, 60, 50),   body)
    pygame.draw.polygon(surf, (0, 200, 160),  body, 2)

    # Side wing blades
    for sign in (-1, 1):
        blade = [
            (cx + sign * 10, SIZE - 18),
            (cx + sign * 30, SIZE - 6),
            (cx + sign * 22, SIZE - 2),
            (cx + sign * 6,  SIZE - 12),
        ]
        pygame.draw.polygon(surf, (12, 45, 38), blade)
        pygame.draw.polygon(surf, (0, 170, 130), blade, 1)

    # Core
    pygame.draw.circle(surf, (0,  80, 65),   (cx, cy - 4), 16)
    pygame.draw.circle(surf, (0, 210, 165),  (cx, cy - 4), 10)
    pygame.draw.circle(surf, (180, 255, 230),(cx, cy - 4),  4)

    # Single centre cannon (bottom)
    pygame.draw.rect(surf, (0, 50, 40), (cx - 5, SIZE - 20, 10, 20), border_radius=3)
    pygame.draw.circle(surf, (0, 220, 170), (cx, SIZE - 1), 5)
    pygame.draw.circle(surf, (200, 255, 240),(cx, SIZE - 1), 2)

    # Sensor eye
    pygame.draw.ellipse(surf, (0, 0, 0),       (cx - 8, cy - 16, 16, 8))
    pygame.draw.ellipse(surf, (0, 230, 180),   (cx - 7, cy - 15, 14, 6))
    pygame.draw.ellipse(surf, (200, 255, 240), (cx - 3, cy - 14,  6, 4))

    return surf


class MiniBoss(Sprite):
    """Mini-boss — waves 3, 8, 13 …

    Less HP and smaller than a full boss, single-phase shooting,
    faster lateral movement. Drops a power-up on death.
    """

    def __init__(self, wave: int):
        super().__init__()

        self.max_hp = 4 + wave
        self.hp     = self.max_hp
        self.SCORE  = 5

        base  = _build_miniboss()
        scale = 1.0 + min((wave // 5) * 0.10, 0.40)
        if scale > 1.01:
            w, h = base.get_size()
            base = pygame.transform.smoothscale(
                base, (int(w * scale), int(h * scale)))

        self._img_normal = base
        self._img_flash  = base.copy()
        self._img_flash.fill((130, 130, 130), special_flags=pygame.BLEND_RGB_ADD)
        self.image  = self._img_normal
        self.width, self.height = self.image.get_size()

        self._hit_flash          = 0.0
        self._HIT_FLASH_DURATION = 0.10

        self.x = float(config.SCREEN_WIDTH // 2 - self.width // 2)
        # Spawn above screen and slide in — no visible teleport on appearance
        self._rest_y      = 22.0
        self.y            = float(-self.height - 8)
        self._entering    = True
        self._enter_speed = 260.0
        self.rect     = self.image.get_rect(x=int(self.x), y=int(self.y))
        self.speed_x  = 110.0 + wave * 4.0   # faster than full boss

        # Smaller hit rect (70%) — only active after entrance
        hw = int(self.width  * 0.70)
        hh = int(self.height * 0.70)
        self.hit_rect = pygame.Rect(0, 0, hw, hh)
        self.hit_rect.center = self.rect.center

        self._shoot_timer = 2.5
        self._pending: list[tuple] = []

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp

    def take_hit(self, damage: int = 1) -> bool:
        self.hp = max(0, self.hp - damage)
        self._hit_flash = self._HIT_FLASH_DURATION
        return self.hp <= 0

    def update(self, dt: float):
        if self._hit_flash > 0:
            self._hit_flash = max(0.0, self._hit_flash - dt)
        self.image = self._img_flash if self._hit_flash > 0 else self._img_normal

        # Slide-in entrance: descend from above the screen
        if self._entering:
            self.y += self._enter_speed * dt
            if self.y >= self._rest_y:
                self.y = self._rest_y
                self._entering = False
            self.rect.x = int(self.x)
            self.rect.y = int(self.y)
            self.hit_rect.center = self.rect.center
            return   # no lateral movement or shooting while entering

        self.x += self.speed_x * dt
        if self.x <= 0:
            self.x = 0.0;  self.speed_x = abs(self.speed_x)
        elif self.x >= config.SCREEN_WIDTH - self.width:
            self.x = float(config.SCREEN_WIDTH - self.width)
            self.speed_x = -abs(self.speed_x)
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.hit_rect.center = self.rect.center

        # Shoot: slower single bullet
        interval = Settings.get().shooter_interval_mult * 2.8
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = interval + random.uniform(-0.3, 0.3)
            cx = self.rect.centerx
            cy = self.rect.bottom - 2
            # Two-spread shot
            for ox in (-18, 0, 18):
                self._pending.append((cx + ox, cy, ox * 1.2, 195.0))

    def drain_shots(self) -> list[tuple]:
        shots = self._pending[:]
        self._pending.clear()
        return shots
