"""World and splash rendering; visual frame counters advance in Game."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

import config
from app_info import APP_NAME, APP_TAGLINE, APP_VERSION, DEVELOPER_NAME
from game_state import GameState
from hud import draw_hud
from ui_fx import draw_glass_panel, render_outlined, render_shadowed
from ui_theme import MUTED

if TYPE_CHECKING:
    from game import Game


def draw_world(game: Game) -> None:
    """Paint background, actors, visual overlays and HUD without advancing state."""
    cv = game._canvas
    game.background.draw(cv)

    if game.boss:
        cv.blit(game.boss.image, game.boss.rect)
    if game.mini_boss:
        cv.blit(game.mini_boss.image, game.mini_boss.rect)

    game._effects.draw_engine_trail(cv)  # trail behind ship
    if game.state != GameState.DYING:
        cv.blit(game.fighter.image, game.fighter.rect)
    game.aliens.draw(cv)
    game.balls.draw(cv)
    game.alien_bullets.draw(cv)
    game.powerups.draw(cv)
    game.explosions.draw(cv)
    game._effects.draw(cv)

    _draw_shield(cv, game)
    _draw_slow_time_tint(cv, game)
    _draw_boss_warning(cv, game)
    _draw_wave_banner(cv, game)
    _draw_hit_flash(cv, game)
    draw_hud(cv, game)


def _draw_shield(cv: pygame.Surface, game: Game) -> None:
    # Shield ring
    if game._shield_active:
        scx, scy = game.fighter.rect.center
        r = max(game.fighter.width, game.fighter.height) // 2 + 11
        pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() / 180.0)
        _sh = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(_sh, (70, 150, 255, int(140 * pulse)), (r + 2, r + 2), r, 3)
        cv.blit(_sh, (scx - r - 2, scy - r - 2))


def _draw_slow_time_tint(cv: pygame.Surface, game: Game) -> None:
    # Slow-time tint
    if game._slow_time_timer > 0:
        _st = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        _st.fill((25, 45, 180, 22))
        cv.blit(_st, (0, 0))


def _draw_boss_warning(cv: pygame.Surface, game: Game) -> None:
    # Boss / mini-boss WARNING animation
    if game._boss_warning_timer > 0:
        t = pygame.time.get_ticks() / 1000.0
        sw, sh = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        is_mini = game.wave % 5 == 3
        # Pulsing screen edge — thinner/subtler for mini-boss
        pulse_a = int(60 + 50 * math.sin(t * 8.0))
        edge = pygame.Surface((sw, sh), pygame.SRCALPHA)
        thicks = (10, 4) if is_mini else (18, 8)
        for thick, alpha in zip(thicks, (pulse_a, pulse_a // 2)):
            col = (255, 80, 0, alpha) if is_mini else (255, 20, 20, alpha)
            pygame.draw.rect(edge, col, (0, 0, sw, sh), thick)
        cv.blit(edge, (0, 0))
        # WARNING text — mini-boss uses smaller font, boss keeps big font
        if int(t * 4) % 2 == 0:
            warn_col = (255, 160, 0) if is_mini else (255, 30, 30)
            warn_txt = "MINI-BOSS" if is_mini else "!! WARNING !!"
            warn_font = game.med_font if is_mini else game.wave_font
            ws = warn_font.render(warn_txt, True, warn_col)
            cv.blit(ws, ws.get_rect(centerx=sw // 2, centery=sh // 2 - 20))
        if not is_mini:
            ss = game.game_font.render("BOSS INCOMING!", True, (255, 120, 120))
            cv.blit(ss, ss.get_rect(centerx=sw // 2, centery=sh // 2 + 40))


def _draw_wave_banner(cv: pygame.Surface, game: Game) -> None:
    # Wave banner
    if game._wave_banner_timer > 0:
        alpha = 255 if game._wave_banner_timer >= 0.5 else int(255 * game._wave_banner_timer / 0.5)
        is_boss = game.wave % 5 == 0
        is_mini = game.wave % 5 == 3 and game.wave >= 3
        if is_boss:
            b_txt, b_color, s_txt = f"BOSS WAVE  {game.wave}!", (255, 55, 55), "Defeat the boss!"
        elif is_mini:
            b_txt, b_color, s_txt = f"WAVE  {game.wave}  —  MINI-BOSS", (255, 160, 0), "A raider is coming!"
        else:
            b_txt, b_color, s_txt = f"WAVE  {game.wave}", (255, 215, 50), "New aliens incoming!"
        banner = game.wave_font.render(b_txt, True, b_color)
        banner.set_alpha(alpha)
        sub = game.game_font.render(s_txt, True, (200, 200, 200))
        sub.set_alpha(alpha)
        bx = config.SCREEN_WIDTH // 2 - banner.get_width() // 2
        by = config.SCREEN_HEIGHT // 3 - banner.get_height() // 2
        cv.blit(banner, (bx, by))
        cv.blit(sub, sub.get_rect(centerx=config.SCREEN_WIDTH // 2, top=by + banner.get_height() + 4))


def _draw_hit_flash(cv: pygame.Surface, game: Game) -> None:
    # Hit flash
    if game.flash_timer > 0:
        fs = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        fs.fill((255, 0, 0, int(game.flash_timer * 4.5)))
        cv.blit(fs, (0, 0))


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
