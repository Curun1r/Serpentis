"""Start / main-menu screen."""
import sys
import math
import pygame
from ship import SHIPS
from ui_fx import (draw_fancy_button, draw_glass_panel,
                   render_glowing, render_shadowed)


class StartScreen:
    """Draws the main menu and returns action strings on user interaction.

    Actions returned by handle_click():
        'play'      — Play button clicked
        'settings'  — Settings button clicked
        'quit'      — Quit button clicked
    """

    def __init__(self, fonts: dict):
        self.game_font  = fonts['game']
        self.small_font = fonts['small']
        self.wave_font  = fonts['wave']

        # Button rects — recomputed in update_layout()
        self.play_rect     = pygame.Rect(0, 0, 180, 52)
        self.settings_rect = pygame.Rect(0, 0, 180, 44)
        self.quit_rect     = pygame.Rect(0, 0, 180, 44)

        # Pre-render title with outline (no bloom — avoids overexposure)
        from ui_fx import render_outlined
        self._title_surf   = render_outlined(self.wave_font, "SERPENTIS",
                                             (210, 160, 255), (60, 10, 100),
                                             thickness=2)
        self._sub_surf     = render_shadowed(self.small_font,
                                             "A Python space shooter",
                                             (110, 110, 140))

    def update_layout(self, sw: int, sh: int):
        cx = sw // 2
        cy = sh // 2
        self.play_rect     = pygame.Rect(cx - 90, cy + 138, 180, 52)
        self.settings_rect = pygame.Rect(cx - 90, cy + 200, 180, 44)
        self.quit_rect     = pygame.Rect(cx - 90, cy + 254, 180, 44)

    # ------------------------------------------------------------------

    def draw(self, canvas: pygame.Surface, game):
        sw    = game.screen_width
        sh    = game.screen_height
        cx    = sw // 2
        cy    = sh // 2
        mouse = game._lmouse()
        t     = pygame.time.get_ticks() / 1000.0

        # ── Title ─────────────────────────────────────────────────────
        # Subtle floating animation
        float_y = int(math.sin(t * 0.9) * 5)
        ts      = self._title_surf
        canvas.blit(ts, ts.get_rect(centerx=cx, centery=36 + ts.get_height() // 2 + float_y))

        canvas.blit(self._sub_surf,
                    self._sub_surf.get_rect(centerx=cx, top=108))

        # Decorative separator line with glow dots
        line_y = 128
        pygame.draw.line(canvas, (40, 40, 65), (cx - 240, line_y), (cx + 240, line_y))
        for dot_x in (cx - 240, cx, cx + 240):
            pygame.draw.circle(canvas, (100, 70, 180), (dot_x, line_y), 3)

        # ── Leaderboard panel ─────────────────────────────────────────
        TABLE_W, TABLE_H = 580, 220
        table_x = cx - TABLE_W // 2
        table_y = 138
        table_rect = pygame.Rect(table_x, table_y, TABLE_W, TABLE_H)

        draw_glass_panel(canvas, table_rect,
                         bg_color=(10, 10, 26), bg_alpha=215,
                         border_color=(65, 45, 110))

        hdr = render_shadowed(self.small_font, "HIGH  SCORES",
                              (180, 140, 255), (30, 0, 60))
        canvas.blit(hdr, hdr.get_rect(centerx=cx, top=table_y + 10))

        pygame.draw.line(canvas, (55, 40, 90),
                         (table_x + 16, table_y + 32),
                         (table_x + TABLE_W - 16, table_y + 32))

        if game.score_entries:
            row_y = table_y + 40
            rank_colors = [(255, 215, 0), (192, 192, 192), (205, 127, 50),
                           (160, 160, 180), (140, 140, 160)]
            for idx, entry in enumerate(game.score_entries[:5]):
                rank_col = rank_colors[idx]
                rank_s   = render_shadowed(self.small_font, f"#{idx+1}", rank_col)
                score_s  = render_shadowed(self.small_font,
                                           f"{entry['score']:>6}", (220, 220, 240))
                wave_s   = render_shadowed(self.small_font,
                                           f"W.{entry['wave']:>2}", (150, 200, 150))
                ship_col = next((s.color for s in SHIPS if s.name == entry.get('ship')),
                                (160, 160, 180))
                ship_s   = render_shadowed(self.small_font,
                                           f"{entry.get('ship','?'):<8}", ship_col)
                diff     = entry.get('difficulty', 'normal')
                diff_col = {'easy': (80, 200, 80), 'normal': (80, 160, 255),
                            'hard': (255, 80, 80)}.get(diff, (160, 160, 180))
                diff_s   = render_shadowed(self.small_font, diff.upper(), diff_col)
                date_s   = render_shadowed(self.small_font,
                                           entry.get('date', ''), (80, 80, 105))
                canvas.blit(rank_s,  (table_x + 18, row_y))
                canvas.blit(score_s, (table_x + 60, row_y))
                canvas.blit(wave_s,  (table_x + 148, row_y))
                canvas.blit(ship_s,  (table_x + 210, row_y))
                canvas.blit(diff_s,  (table_x + 348, row_y))
                canvas.blit(date_s,  (table_x + 452, row_y))
                row_y += 30
        else:
            empty = render_shadowed(self.small_font,
                                    "No records yet -- be the first!",
                                    (70, 70, 90))
            canvas.blit(empty, empty.get_rect(centerx=cx, top=table_y + 80))

        # ── Buttons ───────────────────────────────────────────────────
        draw_fancy_button(canvas, self.play_rect, ">  PLAY",
                          self.game_font,
                          (30, 110, 45), (45, 165, 65),
                          self.play_rect.collidepoint(mouse),
                          border_color=(80, 220, 100))

        draw_fancy_button(canvas, self.settings_rect, "Settings",
                          self.game_font,
                          (45, 45, 72), (70, 70, 105),
                          self.settings_rect.collidepoint(mouse))

        draw_fancy_button(canvas, self.quit_rect, "Quit",
                          self.game_font,
                          (90, 25, 25), (140, 40, 40),
                          self.quit_rect.collidepoint(mouse),
                          border_color=(200, 60, 60))

        # Hint
        hint = render_shadowed(self.small_font, "SPACE to play",
                               (65, 65, 85))
        # Pulsing alpha
        hint.set_alpha(int(140 + 60 * math.sin(t * 2.2)))
        canvas.blit(hint, hint.get_rect(centerx=cx, bottom=sh - 10))

    # ------------------------------------------------------------------

    def handle_click(self, lpos: tuple, game) -> str | None:
        if self.play_rect.collidepoint(lpos):     return 'play'
        if self.settings_rect.collidepoint(lpos): return 'settings'
        if self.quit_rect.collidepoint(lpos):
            pygame.quit(); sys.exit()
        return None

    def handle_key(self, key: int, game) -> str | None:
        if key == pygame.K_SPACE: return 'play'
        return None
