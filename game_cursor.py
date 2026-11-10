"""A fleet-colored menu pointer with a fallback for unsupported desktop cursors."""

import pygame

from game_state import GameState


def build_cursor() -> pygame.Surface:
    """A swept-wing interceptor: smooth edges, pale nose and inset blue canopy."""
    scale = 4
    artwork = pygame.Surface((32 * scale, 32 * scale), pygame.SRCALPHA)

    def points(vertices):
        return [(round(x * scale), round(y * scale)) for x, y in vertices]

    def polygon(color, vertices):
        pygame.draw.polygon(artwork, color, points(vertices))

    def line(color, start, end, width=1):
        pygame.draw.line(artwork, color, *points((start, end)), round(width * scale))

    hull = [(3, 2), (27, 13), (17, 16), (13, 27)]
    polygon((2, 7, 17), [(x + 1, y + 1) for x, y in hull])
    polygon((15, 34, 55), hull)
    pygame.draw.lines(artwork, (3, 10, 23), True, points(hull), 2 * scale)
    polygon((48, 102, 143), [(5, 5), (24, 13), (15, 14)])
    polygon((29, 66, 103), [(5, 5), (15, 14), (13, 24)])

    # Asymmetric leading edges give the small hull depth without a heavy outline.
    line((212, 241, 255), (3, 2), (27, 13))
    line((84, 182, 225), (3, 2), (13, 27))
    line((56, 116, 153), (27, 13), (17, 16))
    line((43, 91, 132), (17, 16), (13, 27))
    line((24, 49, 77), (6, 5), (16, 15))

    polygon((8, 27, 47), [(7, 6), (16, 11), (11, 16)])
    polygon((106, 213, 245), [(8, 7), (14, 11), (11, 14)])
    line((226, 250, 255), (8, 7), (11, 10), .75)
    # Small engine lights tie the pointer to the fleet's cyan/violet palette.
    line((178, 156, 247), (19, 15.5), (21, 15), .75)
    line((99, 213, 247), (14.5, 20), (14, 22), .75)

    image = pygame.transform.smoothscale(artwork, (32, 32))
    # Keep a fully opaque click tip after filtering, at the existing OS hotspot.
    image.set_at((3, 2), (226, 250, 255, 255))
    return image


class GameCursor:
    """Use an OS cursor when available, keeping drawing out of the combat loop."""

    HOTSPOT = (3, 2)

    def __init__(self):
        self.image = build_cursor()
        self._previous = pygame.mouse.get_cursor()
        self._native = True
        self._visible = None
        self._closed = False
        try:
            pygame.mouse.set_cursor(pygame.cursors.Cursor(self.HOTSPOT, self.image))
        except pygame.error:
            self._native = False

    def update(self, state: GameState, focused: bool) -> bool:
        show = focused and state not in (GameState.PLAYING, GameState.DYING)
        # Release visibility outside the game even when using a software pointer.
        visible = not focused or (show and self._native)
        if visible != self._visible:
            pygame.mouse.set_visible(visible)
            self._visible = visible
        return show

    def draw(self, screen: pygame.Surface, state: GameState, focused: bool) -> None:
        show = self.update(state, focused)
        if show and not self._native and pygame.mouse.get_focused():
            x, y = pygame.mouse.get_pos()
            screen.blit(self.image, (x - self.HOTSPOT[0], y - self.HOTSPOT[1]))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._native:
            try:
                pygame.mouse.set_cursor(self._previous)
            except pygame.error:
                pass
        pygame.mouse.set_visible(True)
