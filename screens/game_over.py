"""Run summary and personal records with mouse and keyboard actions."""
import pygame

from ui_theme import (TEXT, MUTED, CYAN, PURPLE, GREEN, MenuFocus,
                      panel, text, button, heading, footer, leaderboard)


class GameOverScreen:
    """Present a completed run and return retry/menu actions."""

    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.game_font = fonts['game']
        self.small_font = fonts['small']
        self.med_font = fonts['med']
        self._focus = MenuFocus(('retry', 'menu'))
        self.update_layout(1280, 720)

    def update_layout(self, sw: int, sh: int):
        cx = sw // 2
        self.try_again_rect = pygame.Rect(cx - 240, 595, 270, 52)
        self.menu_rect = pygame.Rect(cx + 46, 595, 194, 52)
        self._records_rect = pygame.Rect(cx - 410, 290, 820, 270)
        self._summary_rects = [pygame.Rect(cx - 410 + i * 280, 156, 260, 102)
                               for i in range(3)]

    def draw(self, canvas: pygame.Surface, game):
        mouse = game._lmouse()
        cx = game.screen_width // 2
        heading(canvas, self.fonts, 'RUN COMPLETE', 'GAME OVER',
                'Every flight is another chance to go further.')

        values = [('SCORE', str(game.game_score), CYAN),
                  ('WAVE REACHED', str(game.wave), PURPLE),
                  ('SHIP', game._selected_ship.name.upper(), game._selected_ship.color)]
        for rect, (label, value, accent) in zip(self._summary_rects, values):
            panel(canvas, rect, accent=accent)
            text(canvas, self.small_font, label, (rect.centerx, rect.y + 23), MUTED, anchor='center')
            text(canvas, self.med_font, value, (rect.centerx, rect.y + 65), TEXT, anchor='center')

        best_run = (game.game_score > 0 and game.score_entries
                    and game.score_entries[0]['score'] == game.game_score
                    and game.score_entries[0].get('wave') == game.wave
                    and game.score_entries[0].get('ship') == game._selected_ship.name)
        text(canvas, self.small_font,
             'PERSONAL BEST - A FLIGHT TO REMEMBER' if best_run else 'PERSONAL LEADERBOARD',
             (cx, 276), GREEN if best_run else PURPLE, anchor='center')
        current = {'score': game.game_score, 'wave': game.wave,
                   'ship': game._selected_ship.name}
        leaderboard(canvas, self._records_rect, self.fonts, game.score_entries, current=current)

        button(canvas, self.try_again_rect, 'TRY AGAIN', self.game_font,
               hover=self.try_again_rect.collidepoint(mouse), focused=self._focus.active(0), primary=True)
        button(canvas, self.menu_rect, 'MAIN MENU', self.game_font,
               hover=self.menu_rect.collidepoint(mouse), focused=self._focus.active(1))
        footer(canvas, self.small_font,
               'UP / DOWN or TAB to navigate    ENTER to select    ESC for main menu')

    def handle_click(self, lpos: tuple, game) -> str | None:
        for index, (rect, action) in enumerate(((self.try_again_rect, 'retry'),
                                                (self.menu_rect, 'menu'))):
            if rect.collidepoint(lpos):
                self._focus.select(index)
                game.ui_click_sound.play()
                return action
        return None

    def handle_key(self, key: int, game) -> str | None:
        if key == pygame.K_ESCAPE:
            game.ui_click_sound.play()
            return 'menu'
        before = self._focus.index
        action = self._focus.key(key)
        if action:
            game.ui_click_sound.play()
        elif before != self._focus.index:
            game.ui_nav_sound.play()
        return action
