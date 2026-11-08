"""Resolution-independent HUD drawn with native-resolution fonts and geometry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from settings_manager import Settings
from ui_theme import MUTED

if TYPE_CHECKING:
    from game import Game
    from world_painter import WorldPainter


def draw_hud(p: WorldPainter, game: Game) -> None:
    if Settings.get().show_fps:
        limit = str(Settings.get().fps) if Settings.get().fps else "Unlimited"
        p.text(
            game.small_font,
            f"{game.current_fps:.0f} FPS / {limit}",
            MUTED,
            (20, game.screen_height - 12),
            anchor="bottomleft",
        )
    _draw_boss_bars(p, game)
    _draw_powerups(p, game)

    p.panel((10, 10, 310, 62), bg_color=(8, 8, 22), bg_alpha=200, border_color=(50, 50, 80), radius=10)
    p.text(game.game_font, f"Score  {game.game_score}", (255, 255, 255), (20, 16), shadow=(0, 0, 0))
    wave_color = (255, 80, 80) if game.wave % 5 == 0 else (255, 215, 50)
    p.text(game.small_font, f"WAVE {game.wave}", wave_color, (20, 40), shadow=(0, 0, 0))
    p.text(game.small_font, f"Best {game.best_score}", MUTED, (300, 40), anchor="topright", shadow=(0, 0, 0))
    for i in range(game.lives):
        p.blit(game.heart_icon, (300 - game.lives * 26 + i * 26, 14))

    ratio = game.fighter.dash_cooldown_ratio
    ready = ratio == 0
    p.rect((30, 30, 45), (20, 78, 90, 6), border_radius=3)
    fill_width = int(90 * (1 - ratio))
    if fill_width > 0:
        p.rect((0, 220, 255) if ready else (0, 120, 160), (20, 78, fill_width, 6), border_radius=3)
    p.rect((50, 50, 75), (20, 78, 90, 6), 1, border_radius=3)
    p.text(
        game.small_font,
        "DASH  READY" if ready else "DASH",
        (0, 220, 255) if ready else MUTED,
        (118, 74),
        shadow=(0, 0, 0),
    )


def _draw_boss_bars(p: WorldPainter, game: Game) -> None:
    if game.boss:
        names = {1: "PHANTOM", 2: "RAVAGER", 3: "LEVIATHAN"}
        name = names.get(getattr(game.boss, "_tier", 1), "BOSS")
        _draw_enemy_bar(p, game, game.boss, name, mini=False)
    if game.mini_boss:
        _draw_enemy_bar(p, game, game.mini_boss, "RAIDER", mini=True)


def _draw_enemy_bar(p, game, enemy, name, mini):
    ratio = enemy.hp_ratio
    width, height = (360, 14) if mini else (min(560, game.screen_width - 80), 20)
    x = (game.screen_width - width) // 2
    y = game.screen_height - (44 if mini else 48)
    border = (0, 180, 140) if mini else (160, 30, 210)
    p.panel(
        (x - 12, y - 28, width + 24, height + 36),
        bg_color=(15, 35, 30) if mini else (20, 5, 30),
        bg_alpha=210,
        border_color=border,
        radius=8,
    )
    p.rect((20, 55, 45) if mini else (40, 12, 55), (x, y, width, height), border_radius=5)
    if ratio > 0:
        fill = max(1, int(width * ratio))
        if mini:
            color = (0, 200, 155) if ratio > 0.5 else (200, 160, 0) if ratio > 0.25 else (210, 80, 0)
        else:
            color = (45, 195, 55) if ratio > 0.66 else (220, 170, 0) if ratio > 0.33 else (210, 35, 35)
        p.rect(color, (x, y, fill, height), border_radius=5)
        p.rect(tuple(min(255, c + 60) for c in color), (x, y, fill, height // 3), border_radius=5)
    p.rect(border, (x, y, width, height), 2, border_radius=5)
    p.text(
        game.game_font,
        f"{name}   {enemy.hp} / {enemy.max_hp}",
        (180, 255, 230) if mini else (220, 180, 255),
        (game.screen_width // 2, y - 4),
        anchor="midbottom",
        shadow=(0, 40, 30) if mini else (60, 0, 90),
    )


def _draw_powerups(p: WorldPainter, game: Game) -> None:
    lines = []
    if game._triple_shot_timer > 0:
        lines.append((f"3x  {game._triple_shot_timer:.1f}s", (255, 210, 0)))
    if game._shield_active:
        lines.append(("SHIELD", (70, 150, 255)))
    if game._slow_time_timer > 0:
        lines.append((f"SLOW  {game._slow_time_timer:.1f}s", (165, 75, 255)))
    if not lines:
        return
    x = game.screen_width - 14
    p.panel(
        (x - 130, 14, 130, len(lines) * 28 + 10),
        bg_color=(10, 10, 25),
        bg_alpha=190,
        border_color=(60, 40, 90),
        radius=8,
    )
    for i, (label, color) in enumerate(lines):
        p.text(game.small_font, label, color, (x - 8, 22 + i * 28), anchor="topright", shadow=(0, 0, 0))
