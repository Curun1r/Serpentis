"""Transient particles, engine trails, floating labels and camera shake."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from ui_fx import DamageNumber

if TYPE_CHECKING:
    from fighter import Fighter
    from ship import ShipConfig


class VisualEffects:
    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.reset()

    def reset(self) -> None:
        self.particles: list[dict] = []
        self.engine_particles: list[dict] = []
        self.damage_numbers: list[DamageNumber] = []
        self.shake_frames = 0

    def advance_shake(self) -> tuple[int, int]:
        if self.shake_frames > 0:
            offset = random.randint(-8, 8), random.randint(-5, 5)
            self.shake_frames -= 1
            return offset
        return 0, 0

    def spawn_particles(
        self, cx: int, cy: int, count: int = 12, colors: list[tuple[int, int, int]] | None = None
    ) -> None:
        if colors is None:
            colors = [(255, 220, 0), (255, 140, 0), (255, 70, 0), (255, 255, 100)]
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(60, 190)
            life = random.uniform(0.35, 0.65)
            self.particles.append(
                {
                    "x": float(cx),
                    "y": float(cy),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": life,
                    "max_life": life,
                    "color": random.choice(colors),
                    "size": random.randint(2, 5),
                }
            )

    def spawn_damage_number(
        self, x: float, y: float, text: str, color: tuple[int, int, int], scale: float = 1.0, lifetime: float = 0.9
    ) -> None:
        """Spawn a floating damage/score label at world position (x, y)."""
        # Add a small random horizontal scatter so overlapping numbers separate
        x += random.randint(-14, 14)
        self.damage_numbers.append(DamageNumber(x, y, text, color, self.font, lifetime=lifetime, scale=scale))

    def update_particles(self, dt: float) -> None:
        alive = []
        for particle in self.particles:
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += 90.0 * dt
            particle["life"] -= dt
            if particle["life"] > 0:
                alive.append(particle)
        self.particles = alive

    def draw_particles(self, surface: pygame.Surface) -> None:
        for particle in self.particles:
            ratio = particle["life"] / particle["max_life"]
            r = int(particle["color"][0] * ratio)
            g = int(particle["color"][1] * ratio)
            b = int(particle["color"][2] * ratio)
            s = particle["size"]
            pygame.draw.rect(surface, (r, g, b), (int(particle["x"]) - s // 2, int(particle["y"]) - s // 2, s, s))

    def spawn_engine_trail(self, fighter: Fighter, ship: ShipConfig) -> None:
        """Spawn exhaust particles at the ship's engine nozzles."""
        f = fighter
        if not (f.is_moving_left or f.is_moving_right or f.is_moving_up or f.is_moving_down or f.is_dashing):
            return
        r, g, b = ship.color
        # Match the paired engine pods of each ship, in sprite-relative coordinates.
        spread = round(f.width * {"serpent": 10 / 52, "viper": 10 / 46, "hydra": 19 / 68}[ship.id])
        nozzles = (-spread, spread)
        jitter = 1
        cy = f.rect.bottom - 4
        for offset in nozzles:
            for _ in range(2 if f.is_dashing else 1):
                cx = f.rect.centerx + offset + random.randint(-jitter, jitter)
                self.engine_particles.append(
                    {
                        "x": float(cx),
                        "y": float(cy),
                        "vx": random.uniform(-18, 18),
                        "vy": random.uniform(18, 55),
                        "life": random.uniform(0.18, 0.35),
                        "max_life": 0.35,
                        "r": min(255, r + 80),
                        "g": min(255, g + 80),
                        "b": min(255, b + 80),
                        "size": random.randint(2, 4 if f.is_dashing else 3),
                    }
                )

    def update_engine_trail(self, dt: float) -> None:
        alive = []
        for particle in self.engine_particles:
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["life"] -= dt
            if particle["life"] > 0:
                alive.append(particle)
        self.engine_particles = alive

    def draw_engine_trail(self, surface: pygame.Surface) -> None:
        for particle in self.engine_particles:
            ratio = particle["life"] / particle["max_life"]
            s = max(1, int(particle["size"] * ratio))
            col = (int(particle["r"] * ratio), int(particle["g"] * ratio), int(particle["b"] * ratio))
            pygame.draw.circle(surface, col, (int(particle["x"]), int(particle["y"])), s)

    def update(self, dt: float) -> None:
        """Advance explosion particles and labels; trails have their own phase."""
        self.update_particles(dt)
        DamageNumber.update_all(self.damage_numbers, dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_particles(surface)
        DamageNumber.draw_all(self.damage_numbers, surface)

    def draw_scaled(self, painter) -> None:
        for particle in self.particles:
            ratio = particle['life'] / particle['max_life']
            color = tuple(int(channel * ratio) for channel in particle['color'])
            size = particle['size']
            painter.rect(color, (particle['x'] - size // 2, particle['y'] - size // 2, size, size))
        for label in self.damage_numbers:
            alpha = int(255 * max(0, label.lifetime / label.max_life))
            if alpha > 0:
                painter.blit(label._surf, (label.x - label._surf.get_width() // 2, label.y), alpha)

    def draw_engine_scaled(self, painter) -> None:
        for particle in self.engine_particles:
            ratio = particle['life'] / particle['max_life']
            color = tuple(int(particle[channel] * ratio) for channel in ('r', 'g', 'b'))
            painter.circle(color, (particle['x'], particle['y']), max(1, int(particle['size'] * ratio)))
