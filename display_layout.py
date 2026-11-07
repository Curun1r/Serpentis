"""Desktop detection and aspect-preserving layout for the game canvas."""
import pygame


DEFAULT_SIZE = (1280, 720)


def current_display_index() -> int:
    """Return the monitor containing the existing window, or the primary display."""
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        return 0
    try:
        from pygame._sdl2.video import Window
        return max(0, int(Window.from_display_module().display_index))
    except (ImportError, AttributeError, RuntimeError, ValueError, pygame.error):
        return 0


def get_native_resolution(display_index: int | None = None) -> tuple[int, int]:
    """Read the current desktop mode without changing the monitor's resolution.

    This respects macOS display scaling and external monitors. It does not force
    the panel's maximum pixel mode or change the user's desktop settings.
    """
    if not pygame.display.get_init():
        return DEFAULT_SIZE
    try:
        desktops = pygame.display.get_desktop_sizes()
        if not desktops:
            return DEFAULT_SIZE
        index = current_display_index() if display_index is None else display_index
        if not 0 <= index < len(desktops):
            index = 0
        width, height = desktops[index]
        if width > 0 and height > 0:
            return int(width), int(height)
    except (pygame.error, RuntimeError, TypeError, ValueError):
        pass
    return DEFAULT_SIZE


def fit_viewport(display_size: tuple[int, int],
                 logical_size: tuple[int, int] = DEFAULT_SIZE) -> pygame.Rect:
    """Center the largest proportional canvas that fits inside the display."""
    width, height = display_size
    logical_width, logical_height = logical_size
    if min(width, height, logical_width, logical_height) <= 0:
        raise ValueError('Display and logical dimensions must be positive')
    if width * logical_height <= height * logical_width:
        view_width, view_height = width, max(1, width * logical_height // logical_width)
    else:
        view_width, view_height = max(1, height * logical_width // logical_height), height
    return pygame.Rect((width - view_width) // 2, (height - view_height) // 2,
                       view_width, view_height)


def choose_window_size(native_size: tuple[int, int]) -> tuple[int, int]:
    """Leave room for window borders, the menu bar and the Dock/taskbar."""
    width, height = native_size
    return max(1, width - 80), max(1, height - 120)
