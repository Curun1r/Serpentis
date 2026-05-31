"""Ship configuration for the ship-select screen.

Each ShipConfig defines the mechanical properties of one playable vessel.
All multipliers are relative to the baseline constants in config.py.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ShipConfig:
    # Identity
    id:          str
    name:        str
    tagline:     str
    color:       tuple[int, int, int]   # accent colour used in UI

    # Stats (multipliers on config.py baseline values)
    speed_mult:          float   # > 1 = faster
    dash_cooldown_mult:  float   # < 1 = recharges faster
    dash_duration_mult:  float   # > 1 = longer dash burst

    # Shooting
    default_shots:  int   # bullets fired per keypress (no powerup active)
    max_bullets:    int   # max player bullets on screen at once

    # Display stat bars  (0–10 scale, used in the selection screen)
    stat_speed:     int
    stat_fire:      int
    stat_dash:      int


# ---------------------------------------------------------------------------
# Three ships — balanced / speedster / gunner
# ---------------------------------------------------------------------------

SHIPS: list[ShipConfig] = [
    ShipConfig(
        id='serpent',
        name='Serpent',
        tagline='Balanced fighter',
        color=(80, 200, 255),
        # ── Stats ──────────────────────────────────────────
        speed_mult=1.0,
        dash_cooldown_mult=1.0,
        dash_duration_mult=1.0,
        default_shots=1,
        max_bullets=4,
        stat_speed=6, stat_fire=6, stat_dash=6,
    ),
    ShipConfig(
        id='viper',
        name='Viper',
        tagline='Speed & agility',
        color=(80, 255, 110),
        # ── Stats ──────────────────────────────────────────
        speed_mult=1.45,
        dash_cooldown_mult=0.50,
        dash_duration_mult=1.45,
        default_shots=1,
        max_bullets=3,
        stat_speed=9, stat_fire=4, stat_dash=9,
    ),
    ShipConfig(
        id='hydra',
        name='Hydra',
        tagline='Heavy firepower',
        color=(255, 120, 50),
        # ── Stats ──────────────────────────────────────────
        speed_mult=0.75,
        dash_cooldown_mult=1.30,
        dash_duration_mult=0.85,
        default_shots=2,   # fires two spread bullets by default
        max_bullets=6,
        stat_speed=4, stat_fire=9, stat_dash=4,
    ),
]
