"""Native desktop selection and canvas proportions across monitor sizes."""
import pygame
import pytest

import display_layout


@pytest.fixture
def desktops(monkeypatch):
    monkeypatch.setattr(pygame.display, 'get_init', lambda: True)
    monkeypatch.setattr(pygame.display, 'get_desktop_sizes', lambda: [(3024, 1964), (2560, 1440), (3440, 1440)])


def test_native_resolution_uses_monitor_containing_window(desktops, monkeypatch):
    monkeypatch.setattr(display_layout, 'current_display_index', lambda: 1)
    assert display_layout.get_native_resolution() == (2560, 1440)


@pytest.mark.parametrize(('index', 'expected'), [(0, (3024, 1964)), (2, (3440, 1440)), (9, (3024, 1964))])
def test_native_resolution_explicit_monitor(desktops, index, expected):
    assert display_layout.get_native_resolution(index) == expected


def test_current_monitor_uses_remembered_window_event(monkeypatch):
    monkeypatch.setattr(pygame.display, 'get_init', lambda: True)
    monkeypatch.setattr(pygame.display, 'get_surface', lambda: pygame.Surface((1, 1)))
    monkeypatch.setattr(display_layout, '_display_index', 0)
    display_layout.remember_display(2)
    assert display_layout.current_display_index() == 2


def test_no_window_uses_primary_monitor(monkeypatch):
    monkeypatch.setattr(pygame.display, 'get_init', lambda: True)
    monkeypatch.setattr(pygame.display, 'get_surface', lambda: None)
    assert display_layout.current_display_index() == 0


def test_uninitialized_display_returns_safe_default(monkeypatch):
    monkeypatch.setattr(pygame.display, 'get_init', lambda: False)
    assert display_layout.get_native_resolution() == (1280, 720)


def test_unavailable_desktop_returns_safe_default(monkeypatch):
    monkeypatch.setattr(pygame.display, 'get_init', lambda: True)
    def unavailable():
        raise pygame.error('No display backend')
    monkeypatch.setattr(pygame.display, 'get_desktop_sizes', unavailable)
    assert display_layout.get_native_resolution() == (1280, 720)


@pytest.mark.parametrize(('size', 'expected'), [
    ((1280, 720), (0, 0, 1280, 720)),
    ((1920, 1080), (0, 0, 1920, 1080)),
    ((1024, 768), (0, 96, 1024, 576)),
    ((3440, 1440), (440, 0, 2560, 1440)),
    ((3024, 1964), (0, 131, 3024, 1701)),
])
def test_viewport_preserves_aspect_ratio_and_centers(size, expected):
    viewport = display_layout.fit_viewport(size)
    assert viewport == pygame.Rect(expected)
    assert pygame.Rect((0, 0), size).contains(viewport)


@pytest.mark.parametrize('size', [(3024, 1964), (1280, 720), (80, 100), (1, 1)])
def test_automatic_window_fits_desktop_with_room_for_system_ui(size):
    width, height = display_layout.choose_window_size(size)
    assert 0 < width <= size[0]
    assert 0 < height <= size[1]
