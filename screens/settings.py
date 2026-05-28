"""Settings screen."""
import pygame
from settings_manager import Settings, RESOLUTIONS


class SettingsScreen:
    """Volume, resolution, difficulty, fullscreen toggle.

    Actions returned by handle_click():
        'back'          — Back button or ESC
        'fullscreen'    — fullscreen toggle clicked (caller should apply)
        'resolution'    — resolution changed (caller should apply)
    """

    def __init__(self, fonts: dict):
        self.game_font = fonts['game']
        self._vol_dragging = False

    # ------------------------------------------------------------------

    def _layout(self, sw: int) -> dict:
        cx = sw // 2

        slider_w, slider_h = 400, 12
        slider_x = cx - slider_w // 2
        slider_y = 230

        btn_w, btn_h = 130, 44
        gap = 12
        total_res_w = 4 * btn_w + 3 * gap
        res_x0 = cx - total_res_w // 2
        res_rects = [
            pygame.Rect(res_x0 + i * (btn_w + gap), 335, btn_w, btn_h)
            for i in range(4)
        ]

        diff_w = 140
        total_diff_w = 3 * diff_w + 2 * gap
        diff_x0 = cx - total_diff_w // 2
        diff_rects = [
            pygame.Rect(diff_x0 + i * (diff_w + gap), 455, diff_w, btn_h)
            for i in range(3)
        ]

        return {
            'slider_x':   slider_x,   'slider_y': slider_y,
            'slider_w':   slider_w,   'slider_h': slider_h,
            'slider_hit': pygame.Rect(slider_x - 8, slider_y - 10,
                                      slider_w + 16, slider_h + 20),
            'res_rects':       res_rects,
            'diff_rects':      diff_rects,
            'fullscreen_rect': pygame.Rect(cx - 150, 508, 300, 42),
            'back_rect':       pygame.Rect(cx - 80,  568, 160, 50),
        }

    # ------------------------------------------------------------------

    def draw(self, canvas: pygame.Surface, game):
        s   = Settings.get()
        lay = self._layout(game.screen_width)
        cx  = game.screen_width // 2

        # Title
        title = self.game_font.render("SETTINGS", True, 'white')
        canvas.blit(title, title.get_rect(center=(cx, 110)))

        # Volume
        canvas.blit(self.game_font.render("VOLUME", True, (160, 160, 160)),
                    (lay['slider_x'], lay['slider_y'] - 30))
        sx, sy, sw, sh = lay['slider_x'], lay['slider_y'], lay['slider_w'], lay['slider_h']
        pygame.draw.rect(canvas, (55, 55, 65), (sx, sy, sw, sh), border_radius=6)
        fill_w = int(sw * s.volume)
        if fill_w > 0:
            pygame.draw.rect(canvas, (0, 200, 255), (sx, sy, fill_w, sh), border_radius=6)
        knob_x = sx + fill_w
        pygame.draw.circle(canvas, (220, 220, 220), (knob_x, sy + sh // 2), 9)
        canvas.blit(self.game_font.render(f"{int(s.volume * 100)}%", True, 'white'),
                    (sx + sw + 14, sy - 4))

        # Resolution
        canvas.blit(self.game_font.render("RESOLUTION", True, (160, 160, 160)),
                    (lay['res_rects'][0].x, lay['res_rects'][0].y - 28))
        res_labels = ["1024×768", "1280×720", "1920×1080", "2560×1440"]
        for i, (rect, lbl) in enumerate(zip(lay['res_rects'], res_labels)):
            color = (0, 150, 210) if i == s.resolution_index else (50, 50, 68)
            pygame.draw.rect(canvas, color, rect, border_radius=8)
            if i == s.resolution_index:
                pygame.draw.rect(canvas, (0, 210, 255), rect, 2, border_radius=8)
            t = self.game_font.render(lbl, True, 'white')
            canvas.blit(t, t.get_rect(center=rect.center))

        # Difficulty
        canvas.blit(self.game_font.render("DIFFICULTY", True, (160, 160, 160)),
                    (lay['diff_rects'][0].x, lay['diff_rects'][0].y - 28))
        diff_items = [("EASY", "easy", (55, 170, 55)),
                      ("NORMAL", "normal", (0, 150, 210)),
                      ("HARD", "hard", (190, 50, 50))]
        for i, (dlbl, dkey, dcolor) in enumerate(diff_items):
            rect  = lay['diff_rects'][i]
            color = dcolor if dkey == s.difficulty else (50, 50, 68)
            pygame.draw.rect(canvas, color, rect, border_radius=8)
            if dkey == s.difficulty:
                pygame.draw.rect(canvas, (255, 255, 255), rect, 2, border_radius=8)
            canvas.blit(self.game_font.render(dlbl, True, 'white'),
                        self.game_font.render(dlbl, True, 'white').get_rect(center=rect.center))

        # Fullscreen toggle
        fs        = s.fullscreen
        fs_rect   = lay['fullscreen_rect']
        fs_color  = (0, 145, 195)  if fs else (50, 50, 68)
        fs_border = (0, 210, 255)  if fs else (70, 70, 95)
        pygame.draw.rect(canvas, fs_color,  fs_rect, border_radius=8)
        pygame.draw.rect(canvas, fs_border, fs_rect, 2, border_radius=8)
        fs_t = self.game_font.render("FULLSCREEN:  ON" if fs else "FULLSCREEN:  OFF",
                                     True, 'white')
        canvas.blit(fs_t, fs_t.get_rect(center=fs_rect.center))

        # Back button
        pygame.draw.rect(canvas, (65, 65, 85), lay['back_rect'], border_radius=8)
        back_t = self.game_font.render("BACK", True, 'white')
        canvas.blit(back_t, back_t.get_rect(center=lay['back_rect'].center))

        hint = self.game_font.render("ESC to go back  •  F11 to toggle fullscreen",
                                     True, (90, 90, 100))
        canvas.blit(hint, hint.get_rect(center=(cx, lay['back_rect'].bottom + 22)))

    # ------------------------------------------------------------------

    def handle_click(self, lpos: tuple, game) -> str | None:
        lay = self._layout(game.screen_width)
        s   = Settings.get()

        if lay['slider_hit'].collidepoint(lpos):
            self._vol_dragging = True
            self._update_volume(lpos[0], lay, game)
            return None

        for i, rect in enumerate(lay['res_rects']):
            if rect.collidepoint(lpos):
                s.resolution_index = i
                s.save()
                return 'resolution'

        diff_keys = ['easy', 'normal', 'hard']
        for i, rect in enumerate(lay['diff_rects']):
            if rect.collidepoint(lpos):
                s.difficulty = diff_keys[i]
                s.save()
                return None

        if lay['fullscreen_rect'].collidepoint(lpos):
            return 'fullscreen'

        if lay['back_rect'].collidepoint(lpos):
            return 'back'

        return None

    def handle_motion(self, lpos: tuple, game):
        if self._vol_dragging:
            lay = self._layout(game.screen_width)
            self._update_volume(lpos[0], lay, game)

    def handle_mouse_up(self, game):
        if self._vol_dragging:
            self._vol_dragging = False
            Settings.get().save()

    def _update_volume(self, mouse_x: int, lay: dict, game):
        ratio = (mouse_x - lay['slider_x']) / lay['slider_w']
        s = Settings.get()
        s.volume = max(0.0, min(1.0, ratio))
        game._apply_volume()
