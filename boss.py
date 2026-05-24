import pygame
import config
import math
import random
from pygame.sprite import Sprite


# ---------------------------------------------------------------------------
# Sprite generation
# ---------------------------------------------------------------------------

def _build_boss_image() -> pygame.Surface:
    """Draw a menacing boss ship entirely with pygame.draw primitives."""
    SIZE = 120
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    cx = cy = SIZE // 2

    # ── Main hull (dark hexagon) ──────────────────────────────────────────
    hull = [(cx + round(54 * math.cos(math.radians(i * 60 - 90))),
             cy + round(54 * math.sin(math.radians(i * 60 - 90))))
            for i in range(6)]
    pygame.draw.polygon(surf, (50, 8, 75),   hull)
    pygame.draw.polygon(surf, (150, 30, 200), hull, 2)

    # ── Side wing cannons ─────────────────────────────────────────────────
    for side, sx in ((-1, 4), (1, SIZE - 34)):
        pygame.draw.rect(surf, (38, 5, 62), (sx, cy - 9, 30, 18), border_radius=4)
    pygame.draw.circle(surf, (255, 70, 70),  (2,        cy), 6)   # left tip
    pygame.draw.circle(surf, (255, 70, 70),  (SIZE - 2, cy), 6)   # right tip
    pygame.draw.circle(surf, (255, 180, 80), (2,        cy), 3)
    pygame.draw.circle(surf, (255, 180, 80), (SIZE - 2, cy), 3)

    # ── Energy core ───────────────────────────────────────────────────────
    pygame.draw.circle(surf, (75,  0,  120), (cx, cy), 22)
    pygame.draw.circle(surf, (185, 45, 240), (cx, cy), 16)
    pygame.draw.circle(surf, (235, 170, 255),(cx, cy),  8)
    pygame.draw.circle(surf, (255, 245, 255),(cx, cy),  3)

    # ── Sensor eyes ───────────────────────────────────────────────────────
    for ex in (cx - 18, cx + 18):
        pygame.draw.circle(surf, (0, 0, 0),       (ex, cy - 15), 9)
        pygame.draw.circle(surf, (255, 30, 30),   (ex, cy - 15), 6)
        pygame.draw.circle(surf, (255, 210, 210), (ex, cy - 15), 2)

    # ── Top gun barrel ────────────────────────────────────────────────────
    pygame.draw.rect(surf, (78, 0, 128), (cx - 12, 5, 24, 16), border_radius=3)
    pygame.draw.circle(surf, (255, 55, 55), (cx, 5), 6)

    # ── Bottom engine nozzles ─────────────────────────────────────────────
    for bx in (cx - 22, cx, cx + 22):
        pygame.draw.rect(surf, (105, 0, 162), (bx - 6, 98, 12, 16), border_radius=3)
        pygame.draw.circle(surf, (205, 105, 255), (bx, 114), 5)
        pygame.draw.circle(surf, (255, 230, 255), (bx, 114), 2)

    return surf


# ---------------------------------------------------------------------------
# Boss class
# ---------------------------------------------------------------------------

class Boss(Sprite):
    """Large boss enemy that appears on waves 5, 10, 15 …

    Three combat phases driven by remaining HP fraction:
      Phase 1 (> 66 %) — 1 centre bullet
      Phase 2 (33–66 %) — 3-bullet spread
      Phase 3 (< 33 %)  — 5-bullet fan
    """

    def __init__(self, wave: int):
        super().__init__()

        self.max_hp = 15 + wave * 3     # wave 5 → 30 HP, wave 10 → 45 HP …
        self.hp     = self.max_hp
        self.SCORE  = 10 + wave * 2     # scales with wave

        # Scale sprite slightly on later appearances (max +60 %)
        scale = 1.0 + min((wave // 5 - 1) * 0.15, 0.60)
        base  = _build_boss_image()
        if scale > 1.01:
            w, h = base.get_size()
            base = pygame.transform.smoothscale(base, (int(w * scale), int(h * scale)))

        self._img_normal = base
        self._img_flash  = base.copy()
        self._img_flash.fill((130, 130, 130), special_flags=pygame.BLEND_RGB_ADD)
        self.image  = self._img_normal
        self.width, self.height = self.image.get_size()

        self._hit_flash = 0.0
        self._HIT_FLASH_DURATION = 0.10

        # Position — centred near top
        self.x = float(config.SCREEN_WIDTH // 2 - self.width // 2)
        self.y = float(18)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        # Horizontal movement (faster on higher wave encounters)
        self.speed_x = 75.0 + wave * 3.5

        # Shooting state
        self._shoot_timer  = 2.0                # delay before first shot
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

        # Side-to-side movement
        self.x += self.speed_x * dt
        if self.x <= 0:
            self.x = 0.0
            self.speed_x = abs(self.speed_x)
        elif self.x >= config.SCREEN_WIDTH - self.width:
            self.x = float(config.SCREEN_WIDTH - self.width)
            self.speed_x = -abs(self.speed_x)
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)   # Y stays fixed near top

        # Shooting — interval shrinks each phase
        interval = {1: 2.4, 2: 1.7, 3: 1.0}[self._phase]
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = interval + random.uniform(-0.2, 0.2)
            self._queue_shots()

    def _queue_shots(self):
        cx = self.rect.centerx
        cy = self.rect.bottom - 4
        p  = self._phase
        if p == 1:
            self._pending.append((cx, cy, 0.0, 205.0))
        elif p == 2:
            for ox in (-26, 0, 26):
                self._pending.append((cx + ox, cy, 0.0, 215.0))
        else:
            # 5-bullet fan — edge bullets get outward horizontal velocity
            for i, ox in enumerate((-44, -22, 0, 22, 44)):
                vx = ox * 1.8         # outward drift
                self._pending.append((cx + ox, cy, vx, 225.0))

    def drain_shots(self) -> list[tuple]:
        """Return (cx, cy, vx, vy) tuples and clear the queue."""
        shots = self._pending[:]
        self._pending.clear()
        return shots
