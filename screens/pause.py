"""A readable pause overlay with quick volume and keyboard navigation."""
import pygame

from settings_manager import Settings
from ui_theme import (TEXT, MUTED, DIM, CYAN, PURPLE, BORDER,
                      MenuFocus, panel, text, button, footer)


class PauseOverlay:
    """Return pause-menu actions to the game controller."""

    _ACTIONS = ('volume', 'resume', 'restart', 'menu', 'minimize', 'quit')

    def __init__(self, fonts: dict):
        self.game_font = fonts['game']
        self.small_font = fonts['small']
        self.med_font = fonts['med']
        self._vol_dragging = False
        self.focus = MenuFocus(self._ACTIONS)
        self.focus.select(1)

    def _layout(self, sw: int, sh: int) -> dict:
        cx, cy = sw // 2, sh // 2
        rect = pygame.Rect(cx - 220, cy - 300, 440, 600)
        sx, sy, slider_w = rect.x + 32, rect.y + 166, 376
        return {
            'panel': rect,
            'slider_x': sx, 'slider_y': sy, 'slider_w': slider_w, 'slider_h': 10,
            'slider_hit': pygame.Rect(sx - 8, sy - 12, slider_w + 16, 34),
            'resume_rect': pygame.Rect(rect.x + 32, rect.y + 216, 376, 48),
            'restart_rect': pygame.Rect(rect.x + 32, rect.y + 274, 376, 48),
            'menu_rect': pygame.Rect(rect.x + 32, rect.y + 332, 376, 48),
            'minimize_rect': pygame.Rect(rect.x + 32, rect.y + 390, 376, 48),
            'quit_rect': pygame.Rect(rect.x + 32, rect.y + 482, 376, 48),
        }

    def draw(self, canvas: pygame.Surface, game):
        lay = self._layout(game.screen_width, game.screen_height)
        s = Settings.get()
        mouse = game._lmouse()
        dimmer = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        dimmer.fill((3, 6, 16, 185))
        canvas.blit(dimmer, (0, 0))
        box = lay['panel']
        panel(canvas, box)
        text(canvas, self.small_font, 'TAKE A BREATHER', (box.centerx, box.y + 28), PURPLE,
             anchor='midtop')
        text(canvas, self.med_font, 'PAUSED', (box.centerx, box.y + 59), anchor='midtop')
        text(canvas, self.small_font, f'WAVE {game.wave}   /   SCORE {game.game_score}',
             (box.centerx, box.y + 103), MUTED, anchor='midtop')
        text(canvas, self.small_font, 'MASTER VOLUME', (box.x + 32, box.y + 136),
             CYAN if self.focus.active(0) else MUTED)
        text(canvas, self.small_font, f'{round(s.volume * 100)}%',
             (box.right - 32, box.y + 136), TEXT, anchor='topright')
        slider = pygame.Rect(lay['slider_x'], lay['slider_y'], lay['slider_w'], lay['slider_h'])
        pygame.draw.rect(canvas, BORDER, slider, border_radius=5)
        fill = slider.copy()
        fill.w = round(slider.w * s.volume)
        if fill.w:
            pygame.draw.rect(canvas, CYAN, fill, border_radius=5)
        pygame.draw.circle(canvas, TEXT, (slider.x + fill.w, slider.centery), 7)
        if self.focus.active(0):
            pygame.draw.rect(canvas, CYAN, lay['slider_hit'], 1, border_radius=8)
        for i, (name, label) in enumerate((('resume', 'RESUME FLIGHT'), ('restart', 'RESTART'),
                                           ('menu', 'MAIN MENU'), ('minimize', 'MINIMIZE'),
                                           ('quit', 'QUIT GAME')), start=1):
            rect = lay[f'{name}_rect']
            button(canvas, rect, label, self.game_font,
                   hover=rect.collidepoint(mouse), focused=self.focus.active(i),
                   primary=name == 'resume', danger=name == 'quit')
        pygame.draw.line(canvas, BORDER, (box.x + 32, box.y + 458),
                         (box.right - 32, box.y + 458))
        text(canvas, self.small_font, 'Your flight is frozen until you resume.',
             (box.centerx, box.bottom - 28), DIM, anchor='midbottom')
        footer(canvas, self.small_font,
               'UP / DOWN or TAB: focus     LEFT / RIGHT: volume     ENTER: select     ESC / P: resume')

    def surface(self, game) -> pygame.Surface:
        """Reuse pause artwork until its content, focus or hovered control changes."""
        layout = self._layout(game.screen_width, game.screen_height)
        mouse = game._lmouse()
        hover = tuple(layout[f'{action}_rect'].collidepoint(mouse) for action in self._ACTIONS[1:])
        key = (game.screen_width, game.screen_height, game.wave, game.game_score,
               Settings.get().volume, self.focus.index, hover)
        if key != getattr(self, '_surface_key', None):
            self._surface = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
            self.draw(self._surface, game)
            self._surface_key = key
        return self._surface

    def handle_click(self, lpos: tuple, game) -> str | None:
        lay = self._layout(game.screen_width, game.screen_height)
        if lay['slider_hit'].collidepoint(lpos):
            self.focus.select(0)
            self._vol_dragging = True
            self._update_volume(lpos[0], lay, game)
            return None
        for i, action in enumerate(self._ACTIONS[1:], start=1):
            if lay[f'{action}_rect'].collidepoint(lpos):
                self.focus.select(i)
                game.ui_click_sound.play()
                return action
        return None

    def handle_key(self, key: int, game) -> str | None:
        if key in (pygame.K_ESCAPE, pygame.K_p):
            self._finish_volume_drag()
            return 'resume'
        if key in (pygame.K_LEFT, pygame.K_RIGHT):
            if self.focus.active(0):
                s = Settings.get()
                delta = -0.05 if key == pygame.K_LEFT else 0.05
                s.volume = round(max(0.0, min(1.0, s.volume + delta)), 2)
                game._apply_volume()
                s.save()
                game.ui_nav_sound.play()
            return None
        action = self.focus.key(key)
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
            self._finish_volume_drag()
            game.ui_nav_sound.play()
        if action and action != 'volume':
            self._finish_volume_drag()
            game.ui_click_sound.play()
            return action
        return None

    def handle_motion(self, lpos: tuple, game):
        if self._vol_dragging:
            self._update_volume(lpos[0], self._layout(game.screen_width, game.screen_height), game)

    def handle_mouse_up(self, game):
        self._finish_volume_drag()

    def _finish_volume_drag(self):
        if self._vol_dragging:
            self._vol_dragging = False
            Settings.get().save()

    def _update_volume(self, mouse_x: int, lay: dict, game):
        s = Settings.get()
        s.volume = max(0.0, min(1.0, (mouse_x - lay['slider_x']) / lay['slider_w']))
        game._apply_volume()
