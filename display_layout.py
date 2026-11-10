"""Desktop detection and aspect-preserving layout for the game canvas."""
import pygame


DEFAULT_SIZE = (1280, 720)
_display_index = 0


def open_window(size: tuple[int, int], fullscreen: bool, display_index: int) -> pygame.Surface:
    """Prefer desktop fullscreen, which leaves app switching to the OS.

    pygame 2.6's set_mode(FULLSCREEN) requests an exclusive display even at
    desktop size. Toggling a desktop-sized window selects SDL desktop fullscreen
    without adding a renderer or changing the game's pixel scaling.
    """
    desktop_fullscreen = fullscreen and pygame.display.get_driver() not in ('dummy', 'offscreen')
    flags = pygame.FULLSCREEN if fullscreen and not desktop_fullscreen else 0
    screen = pygame.display.set_mode(size, flags, display=display_index, vsync=0)
    if desktop_fullscreen:
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass  # Some window managers do not support toggling desktop fullscreen.
        screen = pygame.display.get_surface()
        if not screen.get_flags() & pygame.FULLSCREEN:
            screen = pygame.display.set_mode(size, pygame.FULLSCREEN, display=display_index, vsync=0)
    # System shortcuts and the pointer must remain available on every platform.
    pygame.event.set_grab(False)
    pygame.event.set_keyboard_grab(False)
    return screen


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
                 logical_size: tuple[int, int] = DEFAULT_SIZE, fill: bool = False) -> pygame.Rect:
    """Center the largest proportional canvas that fits inside the display."""
    width, height = display_size
    logical_width, logical_height = logical_size
    if min(width, height, logical_width, logical_height) <= 0:
        raise ValueError('Display and logical dimensions must be positive')
    if fill:
        return pygame.Rect(0, 0, width, height)
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


def game_canvas_size(aspect_ratio: str, native_size: tuple[int, int]) -> tuple[int, int]:
    """Logical playfield bounds; render_canvas_size controls framebuffer pixels."""
    ratios = {'16:9': 16 / 9, '16:10': 16 / 10, '4:3': 4 / 3, '21:9': 21 / 9}
    ratio = native_size[0] / native_size[1] if aspect_ratio == 'auto' else ratios.get(aspect_ratio, 16 / 9)
    # Keep the HUD usable on portrait displays while supporting up to 32:9.
    return max(960, min(2560, round(720 * ratio))), 720


def render_canvas_size(logical_size: tuple[int, int], resolution: tuple[int, int]) -> tuple[int, int]:
    """Cover the selected HD pixel budget while retaining the world's ratio."""
    width, height = logical_size
    scale = max(resolution[0] / width, resolution[1] / height)
    return round(width * scale), round(height * scale)
