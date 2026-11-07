"""Display, sound, and difficulty preferences with mouse and keyboard controls."""
import pygame

from settings_manager import Settings, FRAMERATES, RESOLUTIONS
from ui_theme import (TEXT, MUTED, DIM, CYAN, GREEN, RED, BORDER,
                      MenuFocus, panel, text, button, heading, footer)


class SettingsScreen:
    """Return display actions to Game while persisting other preferences directly."""

    _ROWS = ('volume', 'resolution', 'fps', 'difficulty', 'fullscreen', 'back')
    _DIFFICULTIES = ('easy', 'normal', 'hard')

    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.game_font = fonts['game']
        self.small_font = fonts['small']
        self._vol_dragging = False
        self.focus = MenuFocus(self._ROWS)

    def _layout(self, sw: int) -> dict:
        dx = (sw - 1280) // 2
        slider_x, slider_y, slider_w, slider_h = dx + 132, 222, 564, 10
        return {
            'panel': pygame.Rect(dx + 100, 154, 720, 488),
            'display_panel': pygame.Rect(dx + 844, 154, 336, 488),
            'slider_x': slider_x, 'slider_y': slider_y,
            'slider_w': slider_w, 'slider_h': slider_h,
            'slider_hit': pygame.Rect(slider_x - 8, slider_y - 12, slider_w + 16, 34),
            'auto_rect': pygame.Rect(dx + 132, 300, 124, 42),
            'res_rects': [pygame.Rect(dx + 264 + i * 132, 300, 124, 42)
                          for i in range(len(RESOLUTIONS))],
            'fps_rects': [pygame.Rect(dx + 132 + i * 166, 406, 154, 42)
                          for i in range(len(FRAMERATES))],
            'diff_rects': [pygame.Rect(dx + 132 + i * 222, 506, 210, 42)
                           for i in range(len(self._DIFFICULTIES))],
            'fullscreen_rect': pygame.Rect(dx + 868, 218, 288, 48),
            'back_rect': pygame.Rect(dx + 868, 568, 288, 48),
        }

    def draw(self, canvas: pygame.Surface, game):
        s = Settings.get()
        lay = self._layout(game.screen_width)
        mouse = game._lmouse()
        heading(canvas, self.fonts, 'MAKE IT YOURS', 'SETTINGS',
                'Tune your display, sound and challenge. Changes save automatically.')
        panel(canvas, lay['panel'])
        panel(canvas, lay['display_panel'], accent=CYAN)
        x = lay['panel'].x + 32
        text(canvas, self.small_font, 'MASTER VOLUME', (x, 180),
             CYAN if self.focus.active(0) else MUTED)
        text(canvas, self.game_font, f'{round(s.volume * 100)}%', (lay['panel'].right - 32, 178),
             anchor='topright')
        slider = pygame.Rect(lay['slider_x'], lay['slider_y'], lay['slider_w'], lay['slider_h'])
        pygame.draw.rect(canvas, BORDER, slider, border_radius=5)
        fill = slider.copy()
        fill.w = round(slider.w * s.volume)
        if fill.w:
            pygame.draw.rect(canvas, CYAN, fill, border_radius=5)
        pygame.draw.circle(canvas, TEXT, (slider.x + fill.w, slider.centery), 7)
        if self.focus.active(0):
            pygame.draw.rect(canvas, CYAN, lay['slider_hit'], 1, border_radius=8)
        text(canvas, self.small_font, 'RESOLUTION', (x, 264),
             CYAN if self.focus.active(1) else MUTED)
        button(canvas, lay['auto_rect'], 'AUTO', self.small_font,
               hover=lay['auto_rect'].collidepoint(mouse),
               focused=self.focus.active(1) and s.auto_resolution,
               primary=s.auto_resolution)
        for i, rect in enumerate(lay['res_rects']):
            active = not s.auto_resolution and i == s.resolution_index
            label = f'{RESOLUTIONS[i][0]}x{RESOLUTIONS[i][1]}'
            button(canvas, rect, label, self.small_font, hover=rect.collidepoint(mouse),
                   focused=self.focus.active(1) and active, primary=active)
        text(canvas, self.small_font, 'FRAME RATE', (x, 370),
             CYAN if self.focus.active(2) else MUTED)
        for i, rect in enumerate(lay['fps_rects']):
            active = i == s.fps_index
            button(canvas, rect, f'{FRAMERATES[i]} FPS', self.small_font,
                   hover=rect.collidepoint(mouse), primary=active,
                   focused=self.focus.active(2) and active)
        text(canvas, self.small_font, 'DIFFICULTY', (x, 470),
             CYAN if self.focus.active(3) else MUTED)
        for i, rect in enumerate(lay['diff_rects']):
            active = self._DIFFICULTIES[i] == s.difficulty
            button(canvas, rect, self._DIFFICULTIES[i].upper(), self.game_font,
                   hover=rect.collidepoint(mouse), primary=active,
                   focused=self.focus.active(3) and active)
        descriptions = {
            'easy': ('5 lives / slower enemies / gentler bosses', GREEN),
            'normal': ('3 lives / balanced speed / standard bosses', CYAN),
            'hard': ('2 lives / faster enemies / stronger bosses', RED),
        }
        desc, color = descriptions[s.difficulty]
        text(canvas, self.small_font, desc, (x, 568), color)
        text(canvas, self.small_font, 'Applied to your next flight.', (x, 598), DIM)

        dx = lay['display_panel'].x + 24
        text(canvas, self.small_font, 'DISPLAY MODE', (dx, 180), MUTED)
        rect = lay['fullscreen_rect']
        button(canvas, rect, 'FULLSCREEN' if s.fullscreen else 'WINDOWED', self.game_font,
               hover=rect.collidepoint(mouse), focused=self.focus.active(4), primary=s.fullscreen)
        native_w, native_h = s.native_resolution
        text(canvas, self.small_font, 'CONNECTED DISPLAY', (dx, 304), MUTED)
        text(canvas, self.game_font, f'{native_w} x {native_h}', (dx, 334), CYAN)
        text(canvas, self.small_font, 'Auto matches this display.', (dx, 384), TEXT)
        text(canvas, self.small_font, 'Use fullscreen for the full canvas.', (dx, 412), MUTED)
        text(canvas, self.small_font, 'F11 toggles fullscreen anytime.', (dx, 460), DIM)
        rect = lay['back_rect']
        button(canvas, rect, 'BACK TO MENU', self.game_font,
               hover=rect.collidepoint(mouse), focused=self.focus.active(5))
        footer(canvas, self.small_font,
               'UP / DOWN or TAB: focus     LEFT / RIGHT: change     ENTER: select     ESC: back')

    def handle_click(self, lpos: tuple, game) -> str | None:
        lay = self._layout(game.screen_width)
        s = Settings.get()
        if lay['slider_hit'].collidepoint(lpos):
            self.focus.select(0)
            self._vol_dragging = True
            self._update_volume(lpos[0], lay, game)
            return None
        if lay['auto_rect'].collidepoint(lpos):
            self.focus.select(1)
            s.auto_resolution = True
            s.save()
            game.ui_click_sound.play()
            return 'resolution'
        for i, rect in enumerate(lay['res_rects']):
            if rect.collidepoint(lpos):
                self.focus.select(1)
                s.auto_resolution = False
                s.resolution_index = i
                s.save()
                game.ui_click_sound.play()
                return 'resolution'
        for i, rect in enumerate(lay['fps_rects']):
            if rect.collidepoint(lpos):
                self.focus.select(2)
                s.fps_index = i
                s.save()
                game.ui_click_sound.play()
                return None
        for i, rect in enumerate(lay['diff_rects']):
            if rect.collidepoint(lpos):
                self.focus.select(3)
                s.difficulty = self._DIFFICULTIES[i]
                s.save()
                game.ui_click_sound.play()
                return None
        if lay['fullscreen_rect'].collidepoint(lpos):
            self.focus.select(4)
            game.ui_click_sound.play()
            return 'fullscreen'
        if lay['back_rect'].collidepoint(lpos):
            self.focus.select(5)
            self._finish_volume_drag()
            game.ui_click_sound.play()
            return 'back'
        return None

    def handle_key(self, key: int, game) -> str | None:
        if key == pygame.K_ESCAPE:
            self._finish_volume_drag()
            return 'back'
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
            self._finish_volume_drag()
            self.focus.key(key)
            game.ui_nav_sound.play()
            return None
        if key not in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return None
        if self.focus.index < 0:
            self.focus.select(0)
        s = Settings.get()
        row = self._ROWS[self.focus.index]
        delta = -1 if key == pygame.K_LEFT else 1
        adjusting = key in (pygame.K_LEFT, pygame.K_RIGHT)
        if row == 'back':
            return 'back' if not adjusting else None
        if row == 'fullscreen':
            return 'fullscreen'
        if row == 'resolution':
            if adjusting:
                current = 0 if s.auto_resolution else s.resolution_index + 1
                choice = (current + delta) % (len(RESOLUTIONS) + 1)
                s.auto_resolution = choice == 0
                if choice:
                    s.resolution_index = choice - 1
                s.save()
            game.ui_click_sound.play()
            return 'resolution'
        if adjusting:
            if row == 'volume':
                s.volume = round(max(0.0, min(1.0, s.volume + delta * 0.05)), 2)
                game._apply_volume()
            elif row == 'fps':
                s.fps_index = (s.fps_index + delta) % len(FRAMERATES)
            elif row == 'difficulty':
                index = self._DIFFICULTIES.index(s.difficulty)
                s.difficulty = self._DIFFICULTIES[(index + delta) % len(self._DIFFICULTIES)]
            s.save()
            game.ui_nav_sound.play()
        return None

    def handle_motion(self, lpos: tuple, game):
        if self._vol_dragging:
            self._update_volume(lpos[0], self._layout(game.screen_width), game)

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
