"""Start / main-menu screen."""
import sys
import pygame
from ship import SHIPS


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
        self.play_rect     = pygame.Rect(0, 0, 160, 48)
        self.settings_rect = pygame.Rect(0, 0, 160, 40)
        self.quit_rect     = pygame.Rect(0, 0, 160, 40)

    def update_layout(self, sw: int, sh: int):
        cx = sw // 2
        cy = sh // 2
        self.play_rect     = pygame.Rect(cx - 80, cy + 145, 160, 48)
        self.settings_rect = pygame.Rect(cx - 80, cy + 203, 160, 40)
        self.quit_rect     = pygame.Rect(cx - 80, cy + 253, 160, 40)

    # ------------------------------------------------------------------

    def draw(self, canvas: pygame.Surface, game):
        sw = game.screen_width
        sh = game.screen_height
        cx = sw // 2
        cy = sh // 2
        mouse = game._lmouse()

        # Title
        title = self.wave_font.render("SERPENTIS", True, (180, 120, 255))
        canvas.blit(title, title.get_rect(centerx=cx, top=36))

        sub = self.small_font.render("A Python space shooter", True, (90, 90, 110))
        canvas.blit(sub, sub.get_rect(centerx=cx, top=106))

        # Top-5 leaderboard panel
        TABLE_W, TABLE_H = 580, 220
        table_x = cx - TABLE_W // 2
        table_y = 138

        panel = pygame.Surface((TABLE_W, TABLE_H), pygame.SRCALPHA)
        panel.fill((14, 14, 30, 210))
        canvas.blit(panel, (table_x, table_y))
        pygame.draw.rect(canvas, (55, 55, 85),
                         pygame.Rect(table_x, table_y, TABLE_W, TABLE_H), 1, border_radius=8)

        hdr = self.small_font.render("HIGH  SCORES", True, (160, 130, 255))
        canvas.blit(hdr, hdr.get_rect(centerx=cx, top=table_y + 10))
        pygame.draw.line(canvas, (50, 50, 80),
                         (table_x + 16, table_y + 32), (table_x + TABLE_W - 16, table_y + 32))

        if game.score_entries:
            row_y = table_y + 40
            for idx, entry in enumerate(game.score_entries[:5]):
                rank_col = [(255, 215, 0), (192, 192, 192), (205, 127, 50),
                            (160, 160, 180), (140, 140, 160)][idx]
                canvas.blit(self.small_font.render(f"#{idx+1}", True, rank_col),
                            (table_x + 18, row_y))
                canvas.blit(self.small_font.render(f"{entry['score']:>6}", True, (220, 220, 240)),
                            (table_x + 60, row_y))
                canvas.blit(self.small_font.render(f"W.{entry['wave']:>2}", True, (160, 200, 160)),
                            (table_x + 148, row_y))
                ship_col = next((s.color for s in SHIPS if s.name == entry.get('ship')),
                                (160, 160, 180))
                canvas.blit(self.small_font.render(f"{entry.get('ship', '?'):<8}", True, ship_col),
                            (table_x + 218, row_y))
                canvas.blit(self.small_font.render(entry.get('date', ''), True, (90, 90, 110)),
                            (table_x + 370, row_y))
                row_y += 30
        else:
            empty = self.small_font.render("No records yet — be the first!", True, (70, 70, 90))
            canvas.blit(empty, empty.get_rect(centerx=cx, top=table_y + 80))

        # Buttons
        def _btn(rect, label, base_col, hover_col):
            col = hover_col if rect.collidepoint(mouse) else base_col
            pygame.draw.rect(canvas, col, rect, border_radius=8)
            t = self.game_font.render(label, True, 'white')
            canvas.blit(t, t.get_rect(center=rect.center))

        _btn(self.play_rect,     ">  PLAY",  (35, 120, 50),  (50, 170, 70))
        _btn(self.settings_rect, "Settings", (55, 55, 80),   (80, 80, 115))
        _btn(self.quit_rect,     "Quit",     (100, 30, 30),  (150, 45, 45))

        hint = self.small_font.render("SPACE to play", True, (65, 65, 80))
        canvas.blit(hint, hint.get_rect(centerx=cx, bottom=sh - 10))

    def handle_click(self, lpos: tuple, game) -> str | None:
        if self.play_rect.collidepoint(lpos):     return 'play'
        if self.settings_rect.collidepoint(lpos): return 'settings'
        if self.quit_rect.collidepoint(lpos):     return 'quit'
        return None
