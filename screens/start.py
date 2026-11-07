"""Main menu: launch actions, personal records, and a glimpse of the fleet."""
import pygame

from app_info import APP_NAME, APP_VERSION
from ship import SHIPS
from ui_theme import (TEXT, MUTED, DIM, CYAN, PURPLE, BORDER, MenuFocus,
                      panel, text, button, footer, leaderboard)


class StartScreen:
    """Return play/settings/controls/quit actions for mouse or keyboard input."""

    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.game_font = fonts['game']
        self.small_font = fonts['small']
        self.wave_font = fonts['wave']
        self._focus = MenuFocus(('play', 'settings', 'controls', 'quit'))
        self.update_layout(1280, 720)

    def update_layout(self, sw: int, sh: int):
        left = sw // 2 - 560
        self.play_rect = pygame.Rect(left, 302, 368, 58)
        self.settings_rect = pygame.Rect(left, 374, 368, 48)
        self.controls_rect = pygame.Rect(left, 434, 368, 48)
        self.quit_rect = pygame.Rect(left, 494, 368, 48)
        self._records_rect = pygame.Rect(sw // 2 - 90, 140, 650, 352)
        self._fleet_rect = pygame.Rect(sw // 2 - 90, 526, 650, 110)

    def draw(self, canvas: pygame.Surface, game):
        mouse = game._lmouse()
        left = self.play_rect.x
        text(canvas, self.small_font, 'ARCADE / ENDLESS SURVIVAL', (left, 82), CYAN)
        text(canvas, self.wave_font, APP_NAME.upper(), (left - 3, 120), TEXT)
        text(canvas, self.game_font, 'A serpent among the stars.', (left, 192), PURPLE)
        pygame.draw.line(canvas, BORDER, (left, 238), (left + 368, 238))
        text(canvas, self.small_font, 'Choose your ship. Take on the next wave.', (left, 254), MUTED)
        text(canvas, self.small_font, 'Make every run your best.', (left, 277), MUTED)

        actions = [
            (self.play_rect, 'PLAY', True, False),
            (self.settings_rect, 'SETTINGS', False, False),
            (self.controls_rect, 'HOW TO PLAY', False, False),
            (self.quit_rect, 'QUIT', False, True),
        ]
        for index, (rect, label, primary, danger) in enumerate(actions):
            button(canvas, rect, label, self.game_font,
                   hover=rect.collidepoint(mouse), focused=self._focus.active(index),
                   primary=primary, danger=danger)

        text(canvas, self.small_font, f'VERSION {APP_VERSION}', (left, 604), DIM)
        text(canvas, self.small_font, 'Built with Python & pygame', (left, 626), MUTED)
        text(canvas, self.small_font, 'PERSONAL LEADERBOARD',
             (self._records_rect.x, 108), PURPLE)
        leaderboard(canvas, self._records_rect, self.fonts, game.score_entries)

        panel(canvas, self._fleet_rect, accent=CYAN)
        for index, ship in enumerate(SHIPS):
            cx = self._fleet_rect.x + 110 + index * 215
            preview = game._ship_previews[index]
            height = 48
            width = max(1, round(preview.get_width() * height / preview.get_height()))
            image = pygame.transform.smoothscale(preview, (width, height))
            canvas.blit(image, image.get_rect(center=(cx, self._fleet_rect.y + 34)))
            text(canvas, self.small_font, ship.name.upper(),
                 (cx, self._fleet_rect.bottom - 24), ship.color, anchor='center')

        footer(canvas, self.small_font,
               'UP / DOWN or TAB to navigate    ENTER to select    SPACE to play')

    def handle_click(self, lpos: tuple, game) -> str | None:
        for index, (rect, action) in enumerate(zip(
                (self.play_rect, self.settings_rect, self.controls_rect, self.quit_rect),
                ('play', 'settings', 'controls', 'quit'))):
            if rect.collidepoint(lpos):
                self._focus.select(index)
                game.ui_click_sound.play()
                return action
        return None

    def handle_key(self, key: int, game) -> str | None:
        # Space is a direct launch shortcut, independent of the highlighted item.
        if key == pygame.K_SPACE:
            game.ui_click_sound.play()
            return 'play'
        before = self._focus.index
        action = self._focus.key(key)
        if action:
            game.ui_click_sound.play()
        elif before != self._focus.index:
            game.ui_nav_sound.play()
        return action
