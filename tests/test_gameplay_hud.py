"""Flight information stays compact and wave announcements leave the action clear."""

import pygame
import pytest

import rendering
from boss import Boss
from mini_boss import MiniBoss
from settings_manager import Settings


@pytest.mark.parametrize('aspect', ['4:3', '16:10', '21:9'])
@pytest.mark.parametrize('wave', [2, 3, 5])
@pytest.mark.parametrize('warning', [False, True])
def test_compact_hud_and_lower_notices_do_not_overlap(gameplay, monkeypatch, aspect, wave, warning):
    game = gameplay
    Settings.get().aspect_ratio = aspect
    game._init_game()
    game._start_wave(wave)
    game.game_score, game.best_score, game.lives = 999999, 999999, 7
    game._wave_banner_timer = 1
    game._boss_warning_timer = 1 if warning and wave in (3, 5) else 0
    if not warning:
        if wave == 3:
            game.mini_boss = MiniBoss(wave)
        elif wave == 5:
            game.boss = Boss(wave)

    painter = game._painter
    labels, panels, hearts = [], [], []
    draw_text, draw_panel, draw_image = painter.text, painter.panel, painter.blit

    def text(font, value, color, position, **kwargs):
        bounds = draw_text(font, value, color, position, **kwargs)
        labels.append((value, font, bounds))
        return bounds

    def panel(rect, **kwargs):
        panels.append(pygame.Rect(rect))
        draw_panel(rect, **kwargs)

    def blit(image, position, **kwargs):
        if image is game.heart_icon:
            hearts.append(pygame.Rect(position, image.get_size()))
        return draw_image(image, position, **kwargs)

    monkeypatch.setattr(painter, 'text', text)
    monkeypatch.setattr(painter, 'panel', panel)
    monkeypatch.setattr(painter, 'blit', blit)
    rendering.draw_world(game)

    hud = next(rect for rect in panels if rect.topleft == (10, 10))
    assert hud.w < 310 and hud.h < 62
    assert hud.w * hud.h <= 310 * 62 * .75
    score = next(rect for label, _, rect in labels if label.startswith('Score'))
    best = next(rect for label, _, rect in labels if label.startswith('Best'))
    wave_label = next(rect for label, font, rect in labels if label.startswith('WAVE') and font is game.hud_small_font)
    assert len(hearts) == 7
    assert all(hud.contains(rect) for rect in (score, best, wave_label, *hearts))
    assert not any(score.colliderect(heart) for heart in hearts)
    assert not wave_label.colliderect(best)

    title = next(rect for _, font, rect in labels if font is game.notice_font)
    subtitle = next(rect for label, _, rect in labels
                    if label.endswith('incoming!') or label.startswith('Defeat'))
    notice = title.union(subtitle)
    assert notice.centerx == pytest.approx(game.screen_width / 2, abs=1)
    assert notice.top > game.screen_height * .7
    assert notice.bottom <= game.screen_height - 90
    assert not notice.colliderect(game.fighter.rect)
    # Active boss bars are recorded before the top-left HUD panel.
    assert all(not notice.colliderect(rect) for rect in panels if rect is not hud)
    assert not any(label == '!! WARNING !!' for label, _, _ in labels)
    for font in (game.hud_font, game.hud_small_font, game.notice_font):
        assert painter._fonts[font].get_height() > font.get_height()


def test_warning_notice_remains_visible_until_the_boss_arrives(gameplay, monkeypatch):
    game = gameplay
    game._start_wave(5)
    game._wave_banner_timer = 0
    game._boss_warning_timer = .3
    calls = []
    draw_text = game._painter.text

    def text(*args, **kwargs):
        calls.append(kwargs['alpha'])
        return draw_text(*args, **kwargs)

    monkeypatch.setattr(game._painter, 'text', text)
    rendering._draw_wave_banner(game._painter, game)
    assert len(calls) == 2 and all(0 < alpha < 255 for alpha in calls)
    assert game._boss_warning_timer == .3
    calls.clear()
    game._boss_warning_timer = 0
    rendering._draw_wave_banner(game._painter, game)
    assert calls == []
