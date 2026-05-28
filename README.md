# Serpentis

A fast-paced space shooter built with Python and Pygame. Destroy waves of aliens, survive boss fights, collect power-ups, and climb the leaderboard.

## Features

- **Endless wave system** — waves get harder every round (+1 alien, +15% speed per wave)
- **4 alien types** — standard, armoured (multi-hit), zigzag, and shooter aliens that fire back
- **Boss fights** — a procedurally-drawn boss ship every 5th wave with a HP bar
- **3 playable ships** — each with unique stats for speed, firepower, and dash
- **Dash mechanic** — short-range burst in any direction with a cooldown indicator
- **3 power-ups** — Triple Shot, Shield (absorbs one hit), Slow Time
- **Top-5 leaderboard** — persisted to disk, shown on the main menu and game-over screen
- **Settings** — volume, resolution (1024×768 → 2560×1440), difficulty, fullscreen
- **Sharp on HiDPI / Retina** — fixed 1280×720 logical canvas scaled via `pygame.SCALED`
- **Camera shake & particle effects** on hits and explosions

## Ships

| Ship | Style | Speed | Firepower | Dash |
|------|-------|:-----:|:---------:|:----:|
| **Serpent** | Balanced | ●●●●●●○○○○ | ●●●●●○○○○○ | ●●●●●●○○○○ |
| **Viper** | Speed & agility | ●●●●●●●●●○ | ●●●●○○○○○○ | ●●●●●●●●●○ |
| **Hydra** | Heavy firepower | ●●●●○○○○○○ | ●●●●●●●●●○ | ●●●●○○○○○○ |

## Controls

| Key | Action |
|-----|--------|
| `←` `→` `↑` `↓` or `WASD` | Move |
| `Space` | Shoot |
| `Shift` | Dash |
| `P` / `Esc` | Pause |
| `F11` | Toggle fullscreen |

## Requirements

- Python 3.12
- Pygame 2.x

## Installation

**Requirements:** Python 3.10+ and Pygame 2.5+

```bash
git clone git@github.com:SaruUa/serpentis.git
cd serpentis
```

**With pipenv (recommended):**
```bash
pipenv install
pipenv run python main.py
```

**With pip:**
```bash
pip install -r requirements.txt
python main.py
```

**One-click launchers:**

| Platform | File |
|----------|------|
| macOS    | double-click `run.command` |
| Linux    | double-click `run.sh` (or `bash run.sh`) |
| Windows  | double-click `run.bat` |

## Project structure

```
main.py              — entry point
game.py              — main loop, all game states and UI
fighter.py           — player ship (movement, dash)
alien.py             — Alien, ArmoredAlien, ZigzagAlien, ShooterAlien
boss.py              — boss enemy (procedurally drawn)
ball.py              — player bullet
alien_bullet.py      — enemy bullet
powerup.py           — TripleShot, Shield, SlowTime pick-ups
explosion.py         — explosion animation sprite
ship.py              — ShipConfig definitions (Serpent / Viper / Hydra)
score_manager.py     — top-5 leaderboard (JSON)
settings_manager.py  — volume, resolution, difficulty, fullscreen (JSON)
assets.py            — image / sound cache
config.py            — runtime constants (loaded from config.json)
```
