"""A self-contained guide to the controls and collectible power-ups."""
import pygame

from ui_theme import CYAN, PURPLE, GREEN, RED, TEXT, MUTED, panel, text, button, heading, footer


class ControlsScreen:
    def __init__(self, fonts):
        self.fonts = fonts
        self.back_rect = pygame.Rect(510, 602, 260, 48)

    def draw(self, canvas, game):
        heading(canvas, self.fonts, 'FLIGHT MANUAL', 'How to play',
                'Survive the waves. Collect upgrades. Make your next run your best.')
        controls = pygame.Rect(100, 158, 510, 410)
        pickups = pygame.Rect(634, 158, 546, 410)
        panel(canvas, controls, CYAN)
        panel(canvas, pickups, PURPLE)
        text(canvas, self.fonts['game'], 'YOUR CONTROLS', (128, 186), CYAN)
        for i, (keys, action) in enumerate([
            ('W A S D / arrow keys', 'Move'), ('Space / left click', 'Shoot'),
            ('Shift + direction', 'Dash'), ('Esc / P', 'Pause'), ('F11', 'Fullscreen'),
        ]):
            y = 244 + i * 52
            text(canvas, self.fonts['small'], keys, (128, y), TEXT)
            text(canvas, self.fonts['small'], action, (578, y), MUTED, anchor='topright')
        text(canvas, self.fonts['game'], 'PICKUPS & SURVIVAL', (662, 186), PURPLE)
        for i, (label, detail, color) in enumerate([
            ('TRIPLE SHOT', 'A wider shot pattern for 8 seconds.', (255, 212, 105)),
            ('SHIELD', 'Absorbs one hit. Ramming damages bosses.', CYAN),
            ('SLOW TIME', 'Slows aliens and incoming shots for 6 seconds.', PURPLE),
            ('HEART', 'Restores one life. Dropped by bosses.', RED),
        ]):
            y = 240 + i * 62
            pygame.draw.circle(canvas, color, (672, y + 8), 5)
            text(canvas, self.fonts['small'], label, (690, y), color)
            text(canvas, self.fonts['small'], detail, (690, y + 23), MUTED)
        text(canvas, self.fonts['small'], 'Enemies that escape also cost a life.', (662, 516), GREEN)
        button(canvas, self.back_rect, 'Back to menu', self.fonts['game'],
               hover=self.back_rect.collidepoint(game._lmouse()), focused=True)
        footer(canvas, self.fonts['small'], 'Esc / Enter to return   /   Tab + arrow keys navigate menus')

    def handle_key(self, key, game):
        if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            game.ui_click_sound.play()
            return 'back'
        return None

    def handle_click(self, pos, game):
        if self.back_rect.collidepoint(pos):
            game.ui_click_sound.play()
            return 'back'
        return None
