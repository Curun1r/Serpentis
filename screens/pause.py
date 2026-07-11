"""Pause overlay."""
import pygame
from settings_manager import Settings


class PauseOverlay:
    """Semi-transparent pause menu drawn over the frozen game canvas.

    Actions returned by handle_click():
        'resume'    — Resume button
        'restart'   — Restart button
        'menu'      — Main Menu button
        'quit'      — Quit button
    """

    def __init__(self, fonts: dict):
        self.game_font   = fonts['game']
        self._vol_dragging = False

    # ------------------------------------------------------------------

    def _layout(self, sw: int, sh: int) -> dict:
        cx = sw // 2
        cy = sh // 2

        panel_w, panel_h = 340, 415
        panel_x = cx - panel_w // 2
        panel_y = cy - panel_h // 2

        slider_w, slider_h = 280, 12
        slider_x = panel_x + (panel_w - slider_w) // 2
        slider_y = panel_y + 115

        btn_w, btn_h = 210, 44
        btn_x = cx - btn_w // 2

        return {
            'panel':      pygame.Rect(panel_x, panel_y, panel_w, panel_h),
            'slider_x':   slider_x,  'slider_y': slider_y,
            'slider_w':   slider_w,  'slider_h': slider_h,
            'slider_hit': pygame.Rect(slider_x - 8, slider_y - 10,
                                      slider_w + 16, slider_h + 20),
            'resume_rect':  pygame.Rect(btn_x, panel_y + 165, btn_w, btn_h),
            'restart_rect': pygame.Rect(btn_x, panel_y + 221, btn_w, btn_h),
            'menu_rect':    pygame.Rect(btn_x, panel_y + 277, btn_w, btn_h),
            'quit_rect':    pygame.Rect(btn_x, panel_y + 349, btn_w, btn_h),
        }

    # ------------------------------------------------------------------

    def draw(self, canvas: pygame.Surface, game):
        s   = Settings.get()
        lay = self._layout(game.screen_width, game.screen_height)
        cx  = game.screen_width // 2
        mouse = game._lmouse()

        # Dimmer
        dimmer = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 155))
        canvas.blit(dimmer, (0, 0))

        # Panel
        panel = lay['panel']
        panel_surf = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        panel_surf.fill((18, 18, 32, 235))
        canvas.blit(panel_surf, (panel.x, panel.y))
        pygame.draw.rect(canvas, (65, 65, 100), panel, 2, border_radius=12)

        # Title
        title = self.game_font.render("PAUSED", True, (220, 220, 255))
        canvas.blit(title, title.get_rect(center=(cx, panel.y + 42)))

        pygame.draw.line(canvas, (55, 55, 85),
                         (panel.x + 20, panel.y + 66),
                         (panel.right - 20, panel.y + 66))

        # Volume
        canvas.blit(self.game_font.render("VOLUME", True, (150, 150, 175)),
                    (lay['slider_x'], lay['slider_y'] - 26))
        sx, sy, sw, sh = lay['slider_x'], lay['slider_y'], lay['slider_w'], lay['slider_h']
        pygame.draw.rect(canvas, (55, 55, 70), (sx, sy, sw, sh), border_radius=6)
        fill_w = int(sw * s.volume)
        if fill_w > 0:
            pygame.draw.rect(canvas, (0, 190, 255), (sx, sy, fill_w, sh), border_radius=6)
        knob_x = sx + fill_w
        pygame.draw.circle(canvas, (210, 210, 210), (knob_x, sy + sh // 2), 9)
        canvas.blit(self.game_font.render(f"{int(s.volume * 100)}%", True, 'white'),
                    (sx + sw + 14, sy - 4))

        # Buttons
        btns = [
            (lay['resume_rect'],  "RESUME",    (35, 130, 55),  (55, 180, 75)),
            (lay['restart_rect'], "RESTART",   (40, 55,  130), (60, 85,  180)),
            (lay['menu_rect'],    "MAIN MENU", (60, 60,  80),  (90, 90,  120)),
        ]
        for rect, label, color, hover_color in btns:
            c = hover_color if rect.collidepoint(mouse) else color
            pygame.draw.rect(canvas, c, rect, border_radius=8)
            pygame.draw.rect(canvas, (90, 90, 130), rect, 1, border_radius=8)
            t = self.game_font.render(label, True, 'white')
            canvas.blit(t, t.get_rect(center=rect.center))

        sep_y = lay['quit_rect'].y - 12
        pygame.draw.line(canvas, (55, 55, 85),
                         (panel.x + 30, sep_y), (panel.right - 30, sep_y))
        q_rect  = lay['quit_rect']
        q_color = (185, 45, 45) if q_rect.collidepoint(mouse) else (130, 35, 35)
        pygame.draw.rect(canvas, q_color, q_rect, border_radius=8)
        pygame.draw.rect(canvas, (200, 60, 60), q_rect, 1, border_radius=8)
        qt = self.game_font.render("QUIT", True, 'white')
        canvas.blit(qt, qt.get_rect(center=q_rect.center))

        hint = self.game_font.render("ESC  /  P  to resume", True, (80, 80, 105))
        canvas.blit(hint, hint.get_rect(center=(cx, panel.bottom + 20)))

    # ------------------------------------------------------------------

    def handle_click(self, lpos: tuple, game) -> str | None:
        lay = self._layout(game.screen_width, game.screen_height)

        if lay['slider_hit'].collidepoint(lpos):
            self._vol_dragging = True
            self._update_volume(lpos[0], lay, game)
            return None
        if lay['resume_rect'].collidepoint(lpos):  return 'resume'
        if lay['restart_rect'].collidepoint(lpos): return 'restart'
        if lay['menu_rect'].collidepoint(lpos):    return 'menu'
        if lay['quit_rect'].collidepoint(lpos):    return 'quit'
        return None

    def handle_motion(self, lpos: tuple, game):
        if self._vol_dragging:
            lay = self._layout(game.screen_width, game.screen_height)
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
