"""Shared visual language and keyboard focus for Serpentis menus."""
import pygame

from ship import SHIPS
from ui_fx import draw_glass_panel

TEXT = (235, 241, 255)
MUTED = (161, 175, 201)
DIM = (127, 145, 176)
CYAN = (91, 219, 255)
PURPLE = (184, 151, 255)
GREEN = (125, 230, 174)
RED = (255, 129, 149)
BORDER = (57, 70, 104)


def text(surface, font, value, pos, color=TEXT, anchor='topleft'):
    rendered = font.render(str(value), True, color)
    rect = rendered.get_rect(**{anchor: pos})
    surface.blit(rendered, rect)
    return rect


def panel(surface, rect, accent=PURPLE):
    draw_glass_panel(surface, rect, bg_color=(13, 20, 38), bg_alpha=238,
                     border_color=BORDER, radius=16)
    pygame.draw.line(surface, accent, (rect.x + 22, rect.y + 1), (rect.x + 62, rect.y + 1), 2)


def button(surface, rect, label, font, *, hover=False, focused=False, primary=False, danger=False):
    accent = RED if danger else CYAN
    fill = (27, 60, 78) if primary else (25, 34, 56)
    if danger:
        fill = (49, 29, 46)
    if hover or focused:
        fill = tuple(min(255, c + 14) for c in fill)
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    border = accent if primary or focused else (BORDER if not hover else MUTED)
    pygame.draw.rect(surface, border, rect, 2 if focused else 1, border_radius=10)
    if focused:
        pygame.draw.rect(surface, accent, (rect.x + 9, rect.centery - 8, 3, 16), border_radius=1)
    text(surface, font, label, rect.center, RED if danger else TEXT, anchor='center')


def heading(surface, fonts, kicker, title, subtitle):
    cx = surface.get_width() // 2
    text(surface, fonts['small'], kicker, (cx, 34), CYAN, anchor='center')
    text(surface, fonts['med'], title, (cx, 76), TEXT, anchor='center')
    text(surface, fonts['small'], subtitle, (cx, 116), MUTED, anchor='center')


def footer(surface, font, label):
    text(surface, font, label, (surface.get_width() // 2, surface.get_height() - 30), MUTED, anchor='center')


class MenuFocus:
    """Focus appears on keyboard use; mouse hover is otherwise the only highlight."""

    def __init__(self, actions):
        self.actions = tuple(actions)
        self.index = -1

    def active(self, index):
        return self.index == index

    def select(self, index):
        self.index = index

    def key(self, key):
        if key in (pygame.K_DOWN, pygame.K_TAB, pygame.K_UP):
            step = -1 if key == pygame.K_UP else 1
            if self.index < 0:
                self.index = 0 if step > 0 else len(self.actions) - 1
            else:
                self.index = (self.index + step) % len(self.actions)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.index < 0:
                self.index = 0
            return self.actions[self.index]
        return None


def leaderboard(surface, rect, fonts, entries, current=None):
    panel(surface, rect)
    font = fonts['small']
    columns = [('RANK', .04), ('SCORE', .16), ('WAVE', .32), ('SHIP', .47), ('MODE', .70)]
    if rect.w >= 800:
        columns[-1] = ('MODE', .65)
        columns.append(('DATE', .81))
    for label, ratio in columns:
        text(surface, font, label, (rect.x + int(rect.w * ratio), rect.y + 20), DIM)
    pygame.draw.line(surface, BORDER, (rect.x + 20, rect.y + 48), (rect.right - 20, rect.y + 48))
    if not entries:
        text(surface, fonts['game'], 'Your first record awaits.', rect.center, TEXT, anchor='center')
        text(surface, font, 'Launch a run and make it count.', (rect.centerx, rect.centery + 30),
             MUTED, anchor='center')
        return
    row_h = min(54, (rect.h - 64) // 5)
    for index, entry in enumerate(entries[:5]):
        y = rect.y + 62 + index * row_h
        selected = current and all(entry.get(key) == current.get(key) for key in ('score', 'wave', 'ship'))
        if selected:
            pygame.draw.rect(surface, (25, 52, 67), (rect.x + 10, y - 7, rect.w - 20, row_h - 3),
                             border_radius=6)
        ship_color = next((ship.color for ship in SHIPS if ship.name == entry.get('ship')), MUTED)
        difficulty = entry.get('difficulty', 'normal')
        values = [
            (f'{index + 1:02}', CYAN if index == 0 else DIM),
            (str(entry['score']), TEXT), (f"{entry['wave']:02}", MUTED),
            (entry.get('ship', '?'), ship_color),
            (difficulty.upper(), {'easy': GREEN, 'hard': RED}.get(difficulty, CYAN)),
            (entry.get('date', ''), MUTED),
        ]
        for (_, ratio), (value, color) in zip(columns, values):
            text(surface, font, value, (rect.x + int(rect.w * ratio), y), color)
