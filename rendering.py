"""World and splash rendering; visual frame counters advance in Game."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from app_info import APP_NAME, APP_TAGLINE, APP_VERSION, DEVELOPER_NAME
from game_state import GameState
from hud import draw_hud
from ui_fx import draw_glass_panel, render_outlined, render_shadowed
from ui_theme import MUTED

if TYPE_CHECKING:
    from game import Game


def draw_world(game: Game) -> None:
    """Paint directly at the configured resolution, keeping world units stable."""
    p = game._painter
    game.background.draw_scaled(p)
    for enemy in (game.boss, game.mini_boss):
        if enemy:
            p.sprite(enemy)
    game._effects.draw_engine_scaled(p)
    if game.state != GameState.DYING:
        p.sprite(game.fighter)
    for group in (game.aliens, game.balls, game.alien_bullets, game.powerups, game.explosions):
        p.group(group)
    game._effects.draw_scaled(p)

    if game._shield_active:
        radius = max(game.fighter.width, game.fighter.height) // 2 + 11
        pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() / 180)
        p.circle((70, 150, 255, int(140 * pulse)), game.fighter.rect.center, radius, 3)
    if game._slow_time_timer > 0:
        p.tint((25, 45, 180, 22))
    _draw_warning(p, game)
    _draw_wave_banner(p, game)
    if game.flash_timer > 0:
        p.tint((255, 0, 0, int(game.flash_timer * 4.5)))
    draw_hud(p, game)


def _draw_warning(p, game):
    if game._boss_warning_timer <= 0:
        return
    t = pygame.time.get_ticks() / 1000
    mini = game.wave % 5 == 3
    alpha = int(60 + 50 * math.sin(t * 8))
    for width, opacity in zip((10, 4) if mini else (18, 8), (alpha, alpha // 2)):
        color = (255, 80, 0, opacity) if mini else (255, 20, 20, opacity)
        # Borders use a transparent full-frame layer so alpha blends correctly.
        layer = pygame.Surface(p.surface.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(layer, color, layer.get_rect(), max(1, round(width * p.scale)))
        p.surface.blit(layer, (0, 0))
    if int(t * 4) % 2 == 0:
        p.text(
            game.med_font if mini else game.wave_font,
            "MINI-BOSS" if mini else "!! WARNING !!",
            (255, 160, 0) if mini else (255, 30, 30),
            (p.width // 2, p.height // 2 - 20),
            anchor="center",
        )
    if not mini:
        p.text(game.game_font, "BOSS INCOMING!", (255, 120, 120), (p.width // 2, p.height // 2 + 40), anchor="center")


def _draw_wave_banner(p, game):
    if game._wave_banner_timer <= 0:
        return
    alpha = 255 if game._wave_banner_timer >= 0.5 else int(255 * game._wave_banner_timer / 0.5)
    if game.wave % 5 == 0:
        title, color, subtitle = f"BOSS WAVE  {game.wave}!", (255, 55, 55), "Defeat the boss!"
    elif game.wave % 5 == 3 and game.wave >= 3:
        title, color, subtitle = f"WAVE  {game.wave}  —  MINI-BOSS", (255, 160, 0), "A raider is coming!"
    else:
        title, color, subtitle = f"WAVE  {game.wave}", (255, 215, 50), "New aliens incoming!"
    bounds = p.text(game.wave_font, title, color, (p.width // 2, p.height // 3), anchor="center", alpha=alpha)
    p.text(game.game_font, subtitle, (200, 200, 200), (p.width // 2, bounds.bottom + 4), anchor="midtop", alpha=alpha)


def draw_loading(game: Game) -> None:
    """Splash screen shown for ~2.5 s on startup."""
    cv = game._menu_canvas
    cx = cv.get_width() // 2
    cy = cv.get_height() // 2
    t = pygame.time.get_ticks() / 1000.0

    # Animated background already drawn by StarBackground.draw()
    # (called before this method in run())

    TOTAL = 2.5
    elapsed = max(0.0, TOTAL - game._loading_timer)
    progress = min(1.0, elapsed / TOTAL)

    # Title with outline — rendered fresh (cheap at 60fps for a 2.5s splash)
    glow_alpha = int(210 + 45 * math.sin(t * 2.5))
    title = render_outlined(game.wave_font, APP_NAME.upper(), (210, 160, 255), (60, 10, 100), thickness=2)
    title.set_alpha(glow_alpha)
    cv.blit(title, title.get_rect(centerx=cx, centery=cy - 70))

    # Subtitle
    sub = render_shadowed(game.game_font, APP_TAGLINE, (120, 110, 160), (0, 0, 0))
    cv.blit(sub, sub.get_rect(centerx=cx, centery=cy - 5))

    # Glass panel for bar
    bar_w, bar_h = 360, 12
    bar_x = cx - bar_w // 2
    bar_y = cy + 52
    draw_glass_panel(
        cv,
        pygame.Rect(bar_x - 12, bar_y - 12, bar_w + 24, bar_h + 28),
        bg_color=(12, 8, 28),
        bg_alpha=210,
        border_color=(80, 40, 130),
        radius=8,
    )

    # Bar track + fill
    pygame.draw.rect(cv, (30, 20, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
    fill = int(bar_w * progress)
    if fill > 0:
        # Gradient: purple → cyan
        for fx in range(fill):
            ratio = fx / max(bar_w - 1, 1)
            r = int(130 + (0 - 130) * ratio)
            g = int(40 + (190 - 40) * ratio)
            b = int(220 + (255 - 220) * ratio)
            pygame.draw.line(cv, (r, g, b), (bar_x + fx, bar_y), (bar_x + fx, bar_y + bar_h))
        # Shine
        pygame.draw.rect(cv, (255, 255, 255, 40), (bar_x, bar_y, fill, bar_h // 3), border_radius=6)
    pygame.draw.rect(cv, (100, 60, 180), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)

    # Percentage text
    pct = render_shadowed(game.small_font, f"Loading...  {int(progress * 100)}%", (150, 110, 200), (0, 0, 0))
    cv.blit(pct, pct.get_rect(centerx=cx, top=bar_y + bar_h + 8))

    # Version tag
    ver = render_shadowed(game.small_font, f"{APP_NAME} v{APP_VERSION}   |   Developer: {DEVELOPER_NAME}", MUTED)
    cv.blit(ver, ver.get_rect(centerx=cx, bottom=cv.get_height() - 14))
