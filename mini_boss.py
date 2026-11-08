"""Three small boss encounters with distinct movement and readable attacks."""

import math
import random
from dataclasses import dataclass

import pygame
from pygame.sprite import Sprite

import config
from settings_manager import Settings


@dataclass(frozen=True)
class MiniBossStyle:
    name: str
    color: tuple[int, int, int]
    speed: float
    shot_speed: float
    cooldown: float
    windup: float


_STYLES = (
    MiniBossStyle('RAIDER', (0, 220, 170), 185, 205, 2.1, 0.65),
    MiniBossStyle('HUNTER', (255, 175, 65), 145, 265, 1.8, 0.60),
    MiniBossStyle('WARDEN', (110, 155, 255), 105, 185, 2.6, 0.75),
)


def _build_miniboss(style: MiniBossStyle) -> pygame.Surface:
    """Keep the compact hull size, with a silhouette and accent for each role."""
    surf = pygame.Surface((72, 72), pygame.SRCALPHA)
    color = style.color
    dark = tuple(c // 4 for c in color)
    if style.name == 'RAIDER':
        body = [(36, 6), (64, 62), (36, 52), (8, 62)]
        for sign in (-1, 1):
            blade = [(36 + sign * 10, 54), (36 + sign * 30, 66),
                     (36 + sign * 22, 70), (36 + sign * 6, 60)]
            pygame.draw.polygon(surf, dark, blade)
            pygame.draw.polygon(surf, color, blade, 1)
    elif style.name == 'HUNTER':
        body = [(36, 3), (49, 35), (58, 65), (36, 55), (14, 65), (23, 35)]
        for x in (14, 52):
            pygame.draw.rect(surf, dark, (x, 35, 6, 34), border_radius=2)
            pygame.draw.rect(surf, color, (x + 1, 52, 4, 18), border_radius=2)
    else:
        body = [(23, 8), (49, 8), (62, 24), (62, 50),
                (49, 64), (23, 64), (10, 50), (10, 24)]
        for x in (2, 60):
            pygame.draw.rect(surf, dark, (x, 20, 10, 38), border_radius=4)
            pygame.draw.rect(surf, color, (x, 20, 10, 38), 2, border_radius=4)
    pygame.draw.polygon(surf, dark, body)
    pygame.draw.polygon(surf, color, body, 2)
    pygame.draw.circle(surf, tuple(c // 2 for c in color), (36, 34), 16)
    pygame.draw.circle(surf, color, (36, 34), 10)
    pygame.draw.circle(surf, (235, 255, 250), (36, 34), 4)
    pygame.draw.rect(surf, dark, (31, 52, 10, 20), border_radius=3)
    pygame.draw.circle(surf, color, (36, 70), 4)
    pygame.draw.ellipse(surf, (0, 0, 0), (28, 20, 16, 8))
    pygame.draw.ellipse(surf, color, (29, 21, 14, 6))
    return surf


class MiniBoss(Sprite):
    """Cycle Raider → Hunter → Warden on waves 3, 8, 13, then repeat.

    Raider dives at a marked position and retreats to a new lane. Hunter tracks
    the player, then commits to a three-round aimed burst. Warden patrols an
    ellipse and alternates gaps in a broad fan. A windup locks each target;
    moving after the warning dodges the attack. Projectiles never home.
    """

    @staticmethod
    def style_for_wave(wave: int) -> MiniBossStyle:
        return _STYLES[max(0, (wave - 3) // 5) % len(_STYLES)]

    def __init__(self, wave: int):
        super().__init__()
        self.style = self.style_for_wave(wave)
        self.name, self.color = self.style.name, self.style.color
        self.max_hp = 4 + wave
        self.hp = self.max_hp
        self.SCORE = 5

        base = _build_miniboss(self.style)
        scale = 1.0 + min((wave // 5) * 0.10, 0.40)
        if scale > 1.01:
            base = pygame.transform.smoothscale(base, tuple(int(s * scale) for s in base.get_size()))
        self._img_normal = base
        self._img_flash = base.copy()
        self._img_flash.fill((130, 130, 130), special_flags=pygame.BLEND_RGB_ADD)
        self.image = base
        self.width, self.height = base.get_size()
        self._hit_flash = 0.0

        self.x = (config.SCREEN_WIDTH - self.width) / 2
        self._rest_y = 22.0
        self.y = float(-self.height - 8)
        self._entering = True
        self.rect = base.get_rect(x=round(self.x), y=round(self.y))
        self.hit_rect = pygame.Rect(0, 0, int(self.width * 0.70), int(self.height * 0.70))
        self._sync_rect()

        self._elapsed = 0.0
        self._orbit_angle = 0.0
        self._direction = random.choice((-1, 1))
        self._speed = self.style.speed * (1 + min(wave, 30) * 0.01)
        self._waypoint = self._new_waypoint()
        self._hunter_offset = self._direction * 80
        self._locked_target = pygame.Vector2(config.SCREEN_WIDTH / 2, config.SCREEN_HEIGHT * 0.9)
        self._dash_start = pygame.Vector2(self.x, self.y)
        self._dash_end = self._dash_start.copy()
        self._volley = random.randrange(2)
        self._burst_index = 0
        self._phase = 'cruise'
        self._phase_left = random.uniform(1.3, 1.9)
        self._pending: list[tuple] = []

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp

    @property
    def attack_warning(self) -> float:
        """Windup progress for the renderer; zero outside a charge."""
        return 1 - self._phase_left / self.style.windup if self._phase == 'windup' else 0.0

    @property
    def attack_target(self) -> tuple[float, float] | None:
        if self._phase != 'windup' or self.name == 'WARDEN':
            return None
        if self.name == 'RAIDER':
            return self._dash_end.x + self.width / 2, self._dash_end.y + self.height / 2
        return tuple(self._locked_target)

    def take_hit(self, damage: int = 1) -> bool:
        self.hp = max(0, self.hp - damage)
        self._hit_flash = 0.10
        return self.hp <= 0

    def update(self, dt: float, target: tuple[float, float] | None = None) -> None:
        self._hit_flash = max(0.0, self._hit_flash - dt)
        self.image = self._img_flash if self._hit_flash > 0 else self._img_normal
        if self._entering:
            self.y = min(self._rest_y, self.y + 260 * dt)
            self._entering = self.y < self._rest_y
            self._sync_rect()
            return  # The entrance never attacks or uses up the first cooldown.

        target = target if target is not None else (config.SCREEN_WIDTH / 2, config.SCREEN_HEIGHT * 0.9)
        # Consume time at phase boundaries so burst/dash timing does not depend
        # on the FPS cap; each new phase always has a positive duration.
        remaining = dt
        while remaining > 1e-9:
            step = min(remaining, self._phase_left)
            self._elapsed += step
            self._move(step, target)
            self._phase_left -= step
            remaining -= step
            self._sync_rect()
            if self._phase_left <= 1e-9:
                self._next_phase(target)

    def _new_waypoint(self) -> pygame.Vector2:
        return pygame.Vector2(random.uniform(0.12, 0.88) * (config.SCREEN_WIDTH - self.width),
                              random.uniform(self._rest_y, self._rest_y + 55))

    def _move(self, dt: float, target: tuple[float, float]) -> None:
        if self._phase == 'dash':
            progress = min(1.0, 1 - (self._phase_left - dt) / 0.48)
            self.x, self.y = self._dash_start.lerp(self._dash_end, progress)
        elif self._phase == 'cruise':
            if self.name == 'RAIDER':
                destination = self._waypoint
                if pygame.Vector2(self.x, self.y).distance_to(destination) < 1:
                    self._waypoint = destination = self._new_waypoint()
            elif self.name == 'HUNTER':
                destination = pygame.Vector2(target[0] - self.width / 2 + self._hunter_offset,
                                             self._rest_y + 30 + 22 * math.sin(self._elapsed * 1.2))
            else:
                self._orbit_angle += self._direction * dt * 0.55
                destination = pygame.Vector2(
                    (config.SCREEN_WIDTH - self.width) / 2
                    + math.sin(self._orbit_angle) * config.SCREEN_WIDTH * 0.32,
                    self._rest_y + 38 * (1 - math.cos(self._orbit_angle * 2)),
                )
            delta = destination - pygame.Vector2(self.x, self.y)
            distance = delta.length()
            if distance > 0:
                position = pygame.Vector2(self.x, self.y) + delta * min(1, self._speed * dt / distance)
                self.x, self.y = position
        self.x = max(0.0, min(config.SCREEN_WIDTH - self.width, self.x))
        self.y = max(self._rest_y, min(config.SCREEN_HEIGHT - self.height, self.y))

    def _next_phase(self, target: tuple[float, float]) -> None:
        if self._phase == 'cruise':
            self._locked_target = pygame.Vector2(target)
            self._dash_start = pygame.Vector2(self.x, self.y)
            self._dash_end = pygame.Vector2(
                max(0, min(config.SCREEN_WIDTH - self.width, target[0] - self.width / 2)),
                max(self._rest_y + 90, min(config.SCREEN_HEIGHT * 0.52 - self.height,
                                          target[1] - self.height / 2)),
            )
            self._phase, self._phase_left = 'windup', self.style.windup
        elif self._phase == 'windup':
            if self.name == 'RAIDER':
                self._queue_fan((-0.25, 0.0, 0.25), self._aim_angle())
                self._phase, self._phase_left = 'dash', 0.48
            elif self.name == 'HUNTER':
                self._burst_index = 0
                self._queue_hunter_shot()
                self._phase, self._phase_left = 'burst', 0.18
            else:
                # Leave a different escape lane on successive volleys.
                gap = 2 + self._volley % 2
                sweep = (-0.16, 0.0, 0.16)[self._volley % 3]
                angles = [angle for i, angle in enumerate((-0.95, -0.57, -0.19, 0.19, 0.57, 0.95))
                          if i != gap]
                self._queue_fan(angles, sweep)
                self._volley += 1
                self._start_cruise()
        elif self._phase == 'burst':
            self._burst_index += 1
            self._queue_hunter_shot()
            if self._burst_index == 2:
                self._start_cruise()
            else:
                self._phase_left = 0.18
        else:  # End of Raider's committed dive.
            self._start_cruise()

    def _start_cruise(self) -> None:
        self._phase = 'cruise'
        pressure = 0.8 if self.hp_ratio <= 0.4 else 1.0
        interval = self.style.cooldown * Settings.get().shooter_interval_mult * pressure
        self._phase_left = max(0.6, interval + random.uniform(-0.2, 0.2))
        self._waypoint = self._new_waypoint()
        self._hunter_offset = random.choice((-80, 80))

    def _aim_angle(self) -> float:
        origin = pygame.Vector2(self.rect.centerx, self.rect.bottom - 2)
        delta = self._locked_target - origin
        return max(-0.85, min(0.85, math.atan2(delta.x, max(90, delta.y))))

    def _queue_hunter_shot(self) -> None:
        self._queue_fan(((0.0, -0.055, 0.055)[self._burst_index],), self._aim_angle())

    def _queue_fan(self, angles, heading=0.0) -> None:
        for angle in angles:
            direction = max(-1.15, min(1.15, heading + angle))
            self._pending.append((self.rect.centerx, self.rect.bottom - 2,
                                  math.sin(direction) * self.style.shot_speed,
                                  math.cos(direction) * self.style.shot_speed))

    def _sync_rect(self) -> None:
        self.rect.topleft = round(self.x), round(self.y)
        self.hit_rect.center = self.rect.center

    def drain_shots(self) -> list[tuple]:
        shots = self._pending[:]
        self._pending.clear()
        return shots
