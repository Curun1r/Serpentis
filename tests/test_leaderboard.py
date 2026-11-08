"""User-facing filter, pagination, and navigation behavior for saved runs."""
from types import SimpleNamespace
from unittest.mock import Mock

import pygame
import pytest

from screens.leaderboard import LeaderboardScreen


@pytest.fixture
def browser(pygame_context):
    fonts = {key: pygame.font.Font(None, size) for key, size in
             [('small', 26), ('game', 36), ('med', 52), ('wave', 86)]}
    records = [{'score': 100 - i, 'wave': 1 + i, 'ship': ['Serpent', 'Viper', 'Hydra'][i % 3],
                'difficulty': ['easy', 'normal', 'hard'][i % 3], 'date': '07.11.2026',
                'duration': 61 + i, 'aspect_ratio': '16:9'} for i in range(19)]
    game = SimpleNamespace(score_entries=records, best_score=100,
                           screen_width=1280, screen_height=720,
                           ui_click_sound=Mock(), ui_nav_sound=Mock(), _lmouse=lambda: (-1, -1))
    return LeaderboardScreen(fonts), game


def test_pagination_shows_different_runs_and_clamps_at_last_page(browser):
    screen, game = browser
    first_page = screen.visible_entries(game)
    assert len(first_page) == 8
    assert screen.page_count(game) == 3
    screen.handle_key(pygame.K_PAGEDOWN, game)
    second_page = screen.visible_entries(game)
    assert first_page != second_page
    assert {row['score'] for row in first_page}.isdisjoint(row['score'] for row in second_page)
    for _ in range(5):
        screen.handle_click(screen.next_rect.center, game)
    assert screen.page == 2
    assert len(screen.visible_entries(game)) == 3
    screen.handle_key(pygame.K_PAGEUP, game)
    assert screen.page == 1


def test_ship_filter_and_reset_are_clickable(browser):
    screen, game = browser
    screen.page = 2
    screen.handle_click(screen.ship_rect.center, game)
    assert screen.page == 0
    assert {row['ship'] for row in screen.filtered_entries(game)} == {'Serpent'}
    screen.handle_click(screen.reset_rect.center, game)
    assert len(screen.filtered_entries(game)) == 19


def test_keyboard_can_filter_difficulty_and_choose_sort(browser):
    screen, game = browser
    screen.handle_key(pygame.K_DOWN, game)
    screen.handle_key(pygame.K_DOWN, game)
    screen.handle_key(pygame.K_RIGHT, game)
    assert {row['difficulty'] for row in screen.filtered_entries(game)} == {'easy'}
    screen.handle_key(pygame.K_DOWN, game)
    screen.handle_key(pygame.K_RIGHT, game)
    entries = screen.filtered_entries(game)
    assert [row['wave'] for row in entries] == sorted((row['wave'] for row in entries), reverse=True)


def test_empty_results_keep_one_page_and_no_rows(browser):
    screen, game = browser
    screen.ship_index = 1  # Serpent records in this fixture are Easy only.
    screen.difficulty_index = 3
    screen.page = 9
    assert screen.page_count(game) == 1
    assert screen.visible_entries(game) == []
    assert screen.page == 0


def test_return_and_mouse_wheel_navigation(browser):
    screen, game = browser
    screen.handle_wheel(pygame.event.Event(pygame.MOUSEWHEEL, y=-1), game)
    assert screen.page == 1
    assert screen.handle_key(pygame.K_ESCAPE, game) == 'back'
    assert screen.handle_click(screen.back_rect.center, game) == 'back'
    screen.focus.select(6)
    assert screen.handle_key(pygame.K_LEFT, game) is None
    assert screen.handle_key(pygame.K_RETURN, game) == 'back'
