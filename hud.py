"""Score, lives, cooldowns and boss/power-up indicators."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

import config
from settings_manager import Settings
from ui_fx import draw_glass_panel, render_shadowed
from ui_theme import MUTED

if TYPE_CHECKING:
    from game import Game


def draw_hud(surface: pygame.Surface, game: Game) -> None:
    if Settings.get().show_fps:
        cap = Settings.get().fps
        limit = str(cap) if cap else "Unlimited"
        label = game.small_font.render(f"{game.current_fps:.0f} FPS / {limit}", True, MUTED)
        surface.blit(label, (20, surface.get_height() - label.get_height() - 12))
    _draw_boss_hp_bar(surface, game)
    _draw_mini_boss_hp_bar(surface, game)
    _draw_powerup_hud(surface, game)

    # ── Left HUD panel ────────────────────────────────────────────
    panel_w, panel_h = 310, 62
    draw_glass_panel(
        surface,
        pygame.Rect(10, 10, panel_w, panel_h),
        bg_color=(8, 8, 22),
        bg_alpha=200,
        border_color=(50, 50, 80),
        radius=10,
    )

    # Score
    sc = render_shadowed(game.game_font, f"Score  {game.game_score}", (255, 255, 255))
    surface.blit(sc, (20, 16))

    # Wave badge
    wave_col = (255, 80, 80) if game.wave % 5 == 0 else (255, 215, 50)
    wv = render_shadowed(game.small_font, f"WAVE {game.wave}", wave_col)
    surface.blit(wv, (20, 40))

    # Best score
    bs = render_shadowed(game.small_font, f"Best {game.best_score}", MUTED)
    surface.blit(bs, (panel_w - bs.get_width() - 10, 40))

    # Hearts — right-aligned inside panel
    hx = panel_w - 10 - game.lives * 26
    hy = 14
    for i in range(game.lives):
        surface.blit(game.heart_icon, (hx + i * 26, hy))

    # ── Dash bar ──────────────────────────────────────────────────
    bar_x, bar_y, bar_w, bar_h = 20, 78, 90, 6
    ratio = game.fighter.dash_cooldown_ratio
    ready = ratio == 0
    pygame.draw.rect(surface, (30, 30, 45), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
    fill_w = int(bar_w * (1.0 - ratio))
    fill_col = (0, 220, 255) if ready else (0, 120, 160)
    if fill_w > 0:
        pygame.draw.rect(surface, fill_col, (bar_x, bar_y, fill_w, bar_h), border_radius=3)
    pygame.draw.rect(surface, (50, 50, 75), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=3)
    dash_label = render_shadowed(game.small_font, "DASH  READY" if ready else "DASH", (0, 220, 255) if ready else MUTED)
    surface.blit(dash_label, (bar_x + bar_w + 8, bar_y - 4))


def _draw_boss_hp_bar(surface: pygame.Surface, game: Game) -> None:
    if not game.boss:
        return
    ratio = game.boss.hp_ratio
    sw = config.SCREEN_WIDTH
    bar_w = min(560, sw - 80)
    bar_h = 20
    bx = sw // 2 - bar_w // 2
    by = config.SCREEN_HEIGHT - 48

    # Panel behind bar
    draw_glass_panel(
        surface,
        pygame.Rect(bx - 12, by - 28, bar_w + 24, bar_h + 36),
        bg_color=(20, 5, 30),
        bg_alpha=210,
        border_color=(120, 20, 160),
        radius=8,
    )

    # Bar track
    pygame.draw.rect(surface, (40, 12, 55), (bx, by, bar_w, bar_h), border_radius=5)

    if ratio > 0:
        fill_w = max(1, int(bar_w * ratio))
        if ratio > 0.66:
            bar_col = (45, 195, 55)
        elif ratio > 0.33:
            bar_col = (220, 170, 0)
        else:
            bar_col = (210, 35, 35)
        pygame.draw.rect(surface, bar_col, (bx, by, fill_w, bar_h), border_radius=5)
        # Shimmer highlight on bar
        pygame.draw.rect(
            surface, tuple(min(255, c + 60) for c in bar_col), (bx, by, fill_w, bar_h // 3), border_radius=5
        )

    pygame.draw.rect(surface, (160, 30, 210), (bx, by, bar_w, bar_h), 2, border_radius=5)

    # Boss name + HP text
    tier_names = {1: "Phantom", 2: "Ravager", 3: "Leviathan"}
    name = tier_names.get(getattr(game.boss, "_tier", 1), "BOSS")
    label = render_shadowed(
        game.game_font, f"{name.upper()}   {game.boss.hp} / {game.boss.max_hp}", (220, 180, 255), (60, 0, 90)
    )
    surface.blit(label, label.get_rect(centerx=sw // 2, bottom=by - 4))


def _draw_mini_boss_hp_bar(surface: pygame.Surface, game: Game) -> None:
    if not game.mini_boss:
        return
    ratio = game.mini_boss.hp_ratio
    sw = config.SCREEN_WIDTH
    bar_w, bar_h = 360, 14
    bx = sw // 2 - bar_w // 2
    by = config.SCREEN_HEIGHT - 44
    draw_glass_panel(
        surface,
        pygame.Rect(bx - 10, by - 24, bar_w + 20, bar_h + 30),
        bg_color=(15, 35, 30),
        bg_alpha=210,
        border_color=(0, 160, 120),
        radius=8,
    )
    pygame.draw.rect(surface, (20, 55, 45), (bx, by, bar_w, bar_h), border_radius=5)
    if ratio > 0:
        fill_w = max(1, int(bar_w * ratio))
        bar_col = (0, 200, 155) if ratio > 0.5 else (200, 160, 0) if ratio > 0.25 else (210, 80, 0)
        pygame.draw.rect(surface, bar_col, (bx, by, fill_w, bar_h), border_radius=5)
        pygame.draw.rect(
            surface, tuple(min(255, c + 50) for c in bar_col), (bx, by, fill_w, bar_h // 3), border_radius=5
        )
    pygame.draw.rect(surface, (0, 180, 140), (bx, by, bar_w, bar_h), 2, border_radius=5)
    label = render_shadowed(
        game.game_font, f"RAIDER   {game.mini_boss.hp} / {game.mini_boss.max_hp}", (180, 255, 230), (0, 40, 30)
    )
    surface.blit(label, label.get_rect(centerx=sw // 2, bottom=by - 4))


def _draw_powerup_hud(surface: pygame.Surface, game: Game) -> None:
    lines = []
    if game._triple_shot_timer > 0:
        lines.append((f"3x  {game._triple_shot_timer:.1f}s", (255, 210, 0)))
    if game._shield_active:
        lines.append(("SHIELD", (70, 150, 255)))
    if game._slow_time_timer > 0:
        lines.append((f"SLOW  {game._slow_time_timer:.1f}s", (165, 75, 255)))
    if not lines:
        return

    sw = config.SCREEN_WIDTH
    px = sw - 14
    py = 14
    pw = 130
    ph = len(lines) * 28 + 10
    draw_glass_panel(
        surface,
        pygame.Rect(px - pw, py, pw, ph),
        bg_color=(10, 10, 25),
        bg_alpha=190,
        border_color=(60, 40, 90),
        radius=8,
    )
    ty = py + 8
    for text, color in lines:
        s = render_shadowed(game.small_font, text, color)
        surface.blit(s, (px - s.get_width() - 8, ty))
        ty += 28
