"""Browse saved runs with filters, sorting and keyboard-accessible pagination."""
import math

import pygame

from score_manager import MAX_ENTRIES, ScoreManager
from ship import SHIPS
from ui_theme import (TEXT, MUTED, DIM, CYAN, PURPLE, GREEN, RED, BORDER,
                      MenuFocus, panel, text, button, heading, footer)


class LeaderboardScreen:
    PAGE_SIZE = 8
    SHIPS = ('all', 'Serpent', 'Viper', 'Hydra')
    DIFFICULTIES = ('all', 'easy', 'normal', 'hard')
    SORTS = ('score', 'wave', 'date')
    ACTIONS = ('ship', 'difficulty', 'sort', 'reset', 'prev', 'next', 'back')

    def __init__(self, fonts):
        self.fonts = fonts
        self.ship_index = self.difficulty_index = self.sort_index = self.page = 0
        self.focus = MenuFocus(self.ACTIONS)
        self.ship_rect = pygame.Rect(80, 246, 270, 42)
        self.difficulty_rect = pygame.Rect(362, 246, 270, 42)
        self.sort_rect = pygame.Rect(644, 246, 270, 42)
        self.reset_rect = pygame.Rect(930, 246, 270, 42)
        self.prev_rect = pygame.Rect(80, 632, 160, 44)
        self.next_rect = pygame.Rect(252, 632, 160, 44)
        self.back_rect = pygame.Rect(980, 632, 220, 44)
        self.table_rect = pygame.Rect(80, 308, 1120, 300)

    def filtered_entries(self, game):
        return ScoreManager.query(game.score_entries, ship=self.SHIPS[self.ship_index],
                                  difficulty=self.DIFFICULTIES[self.difficulty_index],
                                  sort=self.SORTS[self.sort_index])

    def page_count(self, game):
        return max(1, math.ceil(len(self.filtered_entries(game)) / self.PAGE_SIZE))

    def visible_entries(self, game):
        records = self.filtered_entries(game)
        self.page = max(0, min(self.page, max(0, math.ceil(len(records) / self.PAGE_SIZE) - 1)))
        start = self.page * self.PAGE_SIZE
        return records[start:start + self.PAGE_SIZE]

    def draw(self, canvas, game):
        records = self.filtered_entries(game)
        rows = self.visible_entries(game)
        mouse = game._lmouse()
        heading(canvas, self.fonts, 'PERSONAL RECORDS', 'LEADERBOARD',
                f'Your top {MAX_ENTRIES} saved runs. Compare ships, challenges and your longest flights.')
        stats = [('MATCHING RUNS', str(len(records)), CYAN),
                 ('BEST SCORE', str(max((e['score'] for e in records), default=0)), PURPLE),
                 ('HIGHEST WAVE', str(max((e['wave'] for e in records), default=0)), GREEN)]
        for i, (label, value, accent) in enumerate(stats):
            rect = pygame.Rect(80 + i * 380, 148, 360, 76)
            panel(canvas, rect, accent)
            text(canvas, self.fonts['small'], label, (rect.x + 24, rect.y + 15), MUTED)
            text(canvas, self.fonts['game'], value, (rect.right - 24, rect.centery + 4),
                 TEXT, anchor='midright')
        labels = (f'SHIP / {self.SHIPS[self.ship_index].upper()}',
                  f'MODE / {self.DIFFICULTIES[self.difficulty_index].upper()}',
                  f'SORT / {self.SORTS[self.sort_index].upper()}', 'RESET FILTERS',
                  'PREVIOUS', 'NEXT', 'BACK')
        for i, (action, label) in enumerate(zip(self.ACTIONS, labels)):
            rect = getattr(self, f'{action}_rect')
            button(canvas, rect, label, self.fonts['small'] if i < 4 else self.fonts['game'],
                   hover=rect.collidepoint(mouse), focused=self.focus.active(i),
                   primary=i < 3)
        panel(canvas, self.table_rect)
        columns = [('RANK', 104), ('SCORE', 184), ('WAVE', 306), ('SHIP', 408),
                   ('MODE', 558), ('DATE', 710), ('TIME', 890), ('SCREEN', 1040)]
        for label, x in columns:
            text(canvas, self.fonts['small'], label, (x, 327), DIM)
        pygame.draw.line(canvas, BORDER, (100, 353), (1180, 353))
        if not rows:
            text(canvas, self.fonts['game'], 'No matching runs yet.', (640, 438), TEXT, anchor='center')
            text(canvas, self.fonts['small'], 'Try another filter or launch a new flight.',
                 (640, 474), MUTED, anchor='center')
        for i, entry in enumerate(rows):
            y = 368 + i * 29
            rank = self.page * self.PAGE_SIZE + i + 1
            if i % 2 == 0:
                pygame.draw.rect(canvas, (18, 29, 49), (94, y - 4, 1092, 27), border_radius=4)
            ship_color = next((s.color for s in SHIPS if s.name.casefold() == entry.get('ship', '').casefold()), MUTED)
            difficulty = entry.get('difficulty', 'normal')
            seconds = int(entry.get('duration', 0))
            duration = f'{seconds // 60:02}:{seconds % 60:02}' if seconds > 0 else '--:--'
            values = [(str(rank), CYAN), (str(entry['score']), TEXT), (str(entry['wave']), MUTED),
                      (entry.get('ship', '?').title(), ship_color),
                      (difficulty.upper(), {'easy': GREEN, 'hard': RED}.get(difficulty, CYAN)),
                      (entry.get('date', '') or '-', MUTED), (duration, MUTED),
                      (entry.get('aspect_ratio', '16:9'), MUTED)]
            for column, ((_, x), (value, color)) in enumerate(zip(columns, values)):
                right = columns[column + 1][1] - 12 if column + 1 < len(columns) else 1184
                value = str(value)
                while value and self.fonts['small'].size(value)[0] > right - x:
                    value = value[:-4] + '...' if len(value) > 3 else ''
                text(canvas, self.fonts['small'], value, (x, y), color)
        text(canvas, self.fonts['small'], f'PAGE {self.page + 1} / {self.page_count(game)}',
             (640, 654), CYAN, anchor='center')
        footer(canvas, self.fonts['small'],
               'TAB / UP / DOWN: focus   LEFT / RIGHT: change   PAGE UP / DOWN: pages   ESC: back')

    def _change_page(self, delta, game):
        old = self.page
        self.page = max(0, min(self.page + delta, self.page_count(game) - 1))
        if self.page != old:
            game.ui_nav_sound.play()

    def _activate(self, action, game, delta=1):
        if action == 'back':
            game.ui_click_sound.play()
            return 'back'
        if action == 'ship':
            self.ship_index = (self.ship_index + delta) % len(self.SHIPS)
            self.page = 0
        elif action == 'difficulty':
            self.difficulty_index = (self.difficulty_index + delta) % len(self.DIFFICULTIES)
            self.page = 0
        elif action == 'sort':
            self.sort_index = (self.sort_index + delta) % len(self.SORTS)
            self.page = 0
        elif action == 'reset':
            self.ship_index = self.difficulty_index = self.sort_index = self.page = 0
        elif action in ('prev', 'next'):
            self._change_page(-1 if action == 'prev' else 1, game)
            return None
        game.ui_nav_sound.play()
        return None

    def handle_click(self, pos, game):
        for i, action in enumerate(self.ACTIONS):
            if getattr(self, f'{action}_rect').collidepoint(pos):
                self.focus.select(i)
                return self._activate(action, game)
        return None

    def handle_key(self, key, game):
        if key == pygame.K_ESCAPE:
            return self._activate('back', game)
        if key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            self._change_page(-1 if key == pygame.K_PAGEUP else 1, game)
            return None
        if key in (pygame.K_LEFT, pygame.K_RIGHT):
            if self.focus.index < 0:
                self.focus.select(0)
            if self.focus.index in (4, 5):
                self._change_page(-1 if key == pygame.K_LEFT else 1, game)
            elif self.focus.index < 3:
                return self._activate(self.ACTIONS[self.focus.index], game,
                                      -1 if key == pygame.K_LEFT else 1)
            return None
        before = self.focus.index
        action = self.focus.key(key)
        if before != self.focus.index:
            game.ui_nav_sound.play()
        if action:
            return self._activate(action, game)
        return None

    def handle_wheel(self, event, game):
        self._change_page(-event.y, game)
