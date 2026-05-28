"""Game-over screen."""
import pygame
from ship import SHIPS


class GameOverScreen:
    """Run summary + top-5 leaderboard + action buttons.

    Actions returned by handle_click():
        'retry'  — Try Again button
        'menu'   — Menu button
    """

    def __init__(self, fonts: dict):
        self.wave_font  = fonts['wave']
        self.game_font  = fonts['game']
        self.small_font = fonts['small']

        self.try_again_rect = pygame.Rect(0, 0, 210, 48)
        self.menu_rect      = pygame.Rect(0, 0, 130, 48)

    def update_layout(self, sw: int, sh: int):
        cx = sw // 2
        cy = sh // 2
        # Total width: 210 + 20 gap + 130 = 360, centred
        self.try_again_rect = pygame.Rect(cx - 180, cy + 165, 210, 48)
        self.menu_rect      = pygame.Rect(cx + 50,  cy + 165, 130, 48)

    # ------------------------------------------------------------------

    def draw(self, canvas: pygame.Surface, game):
        sw    = game.screen_width
        sh    = game.screen_height
        cx    = sw // 2
        cy    = sh // 2
        mouse = game._lmouse()

        # Title
        go_surf = self.wave_font.render("GAME  OVER", True, (255, 80, 80))
        canvas.blit(go_surf, go_surf.get_rect(centerx=cx, top=28))

        details = (f"Score: {game.game_score}    Wave: {game.wave}"
                   f"    Ship: {game._selected_ship.name}")
        det_surf = self.game_font.render(details, True, (210, 210, 230))
        canvas.blit(det_surf, det_surf.get_rect(centerx=cx, top=106))

        # New-best badge
        if game.score_entries and game.score_entries[0]['score'] == game.game_score:
            badge = self.game_font.render("★  NEW  BEST!", True, (255, 215, 0))
            canvas.blit(badge, badge.get_rect(centerx=cx, top=140))

        # Leaderboard panel
        TABLE_W, TABLE_H = 580, 198
        table_x = cx - TABLE_W // 2
        table_y = 172

        panel = pygame.Surface((TABLE_W, TABLE_H), pygame.SRCALPHA)
        panel.fill((14, 14, 30, 215))
        canvas.blit(panel, (table_x, table_y))
        pygame.draw.rect(canvas, (60, 60, 90),
                         pygame.Rect(table_x, table_y, TABLE_W, TABLE_H), 1, border_radius=8)

        hdr = self.small_font.render("TOP  SCORES", True, (160, 130, 255))
        canvas.blit(hdr, hdr.get_rect(centerx=cx, top=table_y + 8))
        pygame.draw.line(canvas, (50, 50, 80),
                         (table_x + 16, table_y + 30), (table_x + TABLE_W - 16, table_y + 30))

        row_y = table_y + 38
        for idx, entry in enumerate(game.score_entries[:5]):
            is_this  = (entry['score'] == game.game_score and
                        entry.get('ship') == game._selected_ship.name)
            rank_col = [(255, 215, 0), (192, 192, 192), (205, 127, 50),
                        (160, 160, 180), (140, 140, 160)][idx]
            txt_col  = (255, 255, 200) if is_this else (200, 200, 220)

            canvas.blit(self.small_font.render(f"#{idx+1}", True, rank_col),
                        (table_x + 16, row_y))
            canvas.blit(self.small_font.render(f"{entry['score']:>6}", True, txt_col),
                        (table_x + 58, row_y))
            canvas.blit(self.small_font.render(f"W.{entry['wave']:>2}", True, (160, 200, 160)),
                        (table_x + 148, row_y))
            ship_col = next((s.color for s in SHIPS if s.name == entry.get('ship')),
                            (160, 160, 180))
            canvas.blit(self.small_font.render(f"{entry.get('ship','?'):<8}", True, ship_col),
                        (table_x + 218, row_y))
            canvas.blit(self.small_font.render(entry.get('date', ''), True, (85, 85, 105)),
                        (table_x + 368, row_y))
            row_y += 29

        # Buttons
        ta_col  = (50, 170, 70)  if self.try_again_rect.collidepoint(mouse) else (35, 120, 50)
        men_col = (80, 80, 115)  if self.menu_rect.collidepoint(mouse)      else (55, 55, 80)

        pygame.draw.rect(canvas, ta_col,  self.try_again_rect, border_radius=8)
        pygame.draw.rect(canvas, men_col, self.menu_rect,      border_radius=8)

        ta_t  = self.game_font.render("Try Again", True, 'white')
        men_t = self.game_font.render("Menu",      True, 'white')
        canvas.blit(ta_t,  ta_t.get_rect(center=self.try_again_rect.center))
        canvas.blit(men_t, men_t.get_rect(center=self.menu_rect.center))

    def handle_click(self, lpos: tuple, game) -> str | None:
        if self.try_again_rect.collidepoint(lpos): return 'retry'
        if self.menu_rect.collidepoint(lpos):      return 'menu'
        return None
