"""Desktop detection and aspect-preserving layout for the game canvas."""
import pygame


DEFAULT_SIZE = (1280, 720)
_display_index = 0


def remember_display(index: int) -> None:
    """Track the monitor reported by SDL's WINDOWDISPLAYCHANGED event."""
    global _display_index
    _display_index = max(0, int(index))


def current_display_index() -> int:
    """Return the last monitor reported by the window, or the primary display.

    Do not construct temporary pygame._sdl2 Window wrappers here. pygame 2.6.1
    stores their address in SDL window data without retaining them, leaving a
    dangling pointer when later window events are translated.
    """
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        return 0
    return _display_index


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
