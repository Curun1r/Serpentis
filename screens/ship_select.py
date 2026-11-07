"""Ship selection with explicit launch action and readable control hints."""
import pygame
import config
from ship import SHIPS
from ui_theme import CYAN, MUTED, DIM, BORDER, panel, text, button, heading, footer


class ShipSelectScreen:
    def __init__(self, fonts, ship_previews):
        self.fonts = fonts
        self._previews = ship_previews
        self.CARD_W, self.CARD_H, self.GAP = 300, 360, 24
        self.back_rect = pygame.Rect(166, 548, 200, 48)
        self.launch_rect = pygame.Rect(838, 548, 276, 48)

    def _card_rects(self):
        total = len(SHIPS) * self.CARD_W + (len(SHIPS) - 1) * self.GAP
        x = (config.SCREEN_WIDTH - total) // 2
        return [pygame.Rect(x + i * (self.CARD_W + self.GAP), 158, self.CARD_W, self.CARD_H)
                for i in range(len(SHIPS))]

    def draw(self, canvas, game):
        heading(canvas, self.fonts, 'HANGAR / 03 VESSELS', 'Choose your ship',
                'One run. Your flying style. Find the ship that feels right.')
        mouse = game._lmouse()
        for i, (ship, rect) in enumerate(zip(SHIPS, self._card_rects())):
            selected = i == game._ship_cursor
            panel(canvas, rect, ship.color if selected else BORDER)
            if selected or rect.collidepoint(mouse):
                pygame.draw.rect(canvas, ship.color if selected else MUTED, rect, 2, border_radius=16)
            text(canvas, self.fonts['small'], f'0{i + 1} / ' + ('SELECTED' if selected else 'AVAILABLE'),
                 (rect.x + 24, rect.y + 22), ship.color if selected else DIM)
            text(canvas, self.fonts['med'], ship.name, (rect.x + 24, rect.y + 52), ship.color)
            text(canvas, self.fonts['small'], ship.tagline, (rect.x + 24, rect.y + 94), MUTED)
            preview = self._previews[i]
            canvas.blit(preview, preview.get_rect(center=(rect.centerx, rect.y + 166)))
            for j, (label, value) in enumerate([
                ('SPEED', ship.stat_speed), ('FIREPOWER', ship.stat_fire), ('DASH', ship.stat_dash),
            ]):
                y = rect.y + 234 + j * 34
                text(canvas, self.fonts['small'], label, (rect.x + 24, y), MUTED)
                for k in range(10):
                    pygame.draw.rect(canvas, ship.color if k < value else (37, 47, 70),
                                     (rect.x + 142 + k * 13, y + 4, 9, 7), border_radius=2)
        button(canvas, self.back_rect, 'Back to menu', self.fonts['game'], hover=self.back_rect.collidepoint(mouse))
        button(canvas, self.launch_rect, f'Launch {SHIPS[game._ship_cursor].name}', self.fonts['game'],
               primary=True, focused=True, hover=self.launch_rect.collidepoint(mouse))
        text(canvas, self.fonts['small'], 'WASD / arrows  MOVE     Space / click  SHOOT     Shift  DASH     Esc  PAUSE',
             (640, 638), CYAN, anchor='center')
        footer(canvas, self.fonts['small'], 'Left / Right to choose   /   Enter to launch   /   Esc to return')

    def handle_click(self, pos, game):
        if self.back_rect.collidepoint(pos):
            game.ui_click_sound.play()
            return 'back'
        if self.launch_rect.collidepoint(pos):
            game.ui_click_sound.play()
            return 'confirm'
        for i, rect in enumerate(self._card_rects()):
            if rect.collidepoint(pos):
                game._ship_cursor = i
                game.ui_nav_sound.play()
        return None

    def handle_key(self, key, game):
        if key == pygame.K_ESCAPE:
            game.ui_click_sound.play()
            return 'back'
        if key in (pygame.K_LEFT, pygame.K_a):
            game._ship_cursor = (game._ship_cursor - 1) % len(SHIPS)
            game.ui_nav_sound.play()
        elif key in (pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
            game._ship_cursor = (game._ship_cursor + 1) % len(SHIPS)
            game.ui_nav_sound.play()
        elif key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            game.ui_click_sound.play()
            return 'confirm'
        return None
