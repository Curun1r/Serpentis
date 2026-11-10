"""A fleet-colored menu pointer with a fallback for unsupported desktop cursors."""

import pygame

from game_state import GameState


def build_cursor() -> pygame.Surface:
    """Draw once at the OS cursor size; the tip is the exact click hotspot."""
    image = pygame.Surface((32, 32), pygame.SRCALPHA)
    hull = [(3, 2), (3, 24), (9, 19), (14, 29), (19, 26), (14, 17), (25, 17)]
    pygame.draw.polygon(image, (8, 14, 32), hull)
    pygame.draw.lines(image, (2, 5, 14), True, hull, 3)
    pygame.draw.lines(image, (70, 220, 255), True, hull, 1)
    pygame.draw.polygon(image, (155, 110, 235), [(7, 10), (7, 17), (14, 14)])
    pygame.draw.line(image, (225, 250, 255), (4, 4), (12, 12), 2)
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
