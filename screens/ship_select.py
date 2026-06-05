"""Ship-selection screen."""
import pygame
import config
from ship import SHIPS


class ShipSelectScreen:
    """Three side-by-side ship cards.

    Actions returned by handle_click() / handle_key():
        'confirm'   — ship chosen, start the game
        'back'      — ESC pressed, return to start screen
    """

    def __init__(self, fonts: dict, ship_previews: list):
        self.med_font   = fonts['med']
        self.small_font = fonts['small']
        self._badge_font = pygame.font.Font(None, 20)

        self._previews = ship_previews   # pre-tinted surfaces from Game.__init__

        # Card geometry (fixed; depends on screen width via _card_rects())
        self.CARD_W = 290
        self.CARD_H = 410
        self.GAP    = 30

    # ------------------------------------------------------------------

    def _card_rects(self) -> list[pygame.Rect]:
        total   = len(SHIPS) * self.CARD_W + (len(SHIPS) - 1) * self.GAP
        start_x = (config.SCREEN_WIDTH - total) // 2
        card_y  = 118
        return [
            pygame.Rect(start_x + i * (self.CARD_W + self.GAP), card_y,
                        self.CARD_W, self.CARD_H)
            for i in range(len(SHIPS))
        ]

    # ------------------------------------------------------------------

    def draw(self, canvas: pygame.Surface, game):
        sw    = config.SCREEN_WIDTH
        mouse = game._lmouse()
        rects = self._card_rects()

        # Title
        title = self.med_font.render("SELECT YOUR SHIP", True, (210, 210, 255))
        canvas.blit(title, title.get_rect(centerx=sw // 2, top=22))

        hint = self.small_font.render(
            "← → to browse   •   click to select   •   SPACE / second click to confirm   •   ESC to go back",
            True, (90, 90, 110))
        canvas.blit(hint, hint.get_rect(centerx=sw // 2, top=70))

        for i, (ship, rect) in enumerate(zip(SHIPS, rects)):
            is_sel   = (i == game._ship_cursor)
            is_hover = rect.collidepoint(mouse) and not is_sel

            # Card background
            bg_alpha = 230 if is_sel else (180 if is_hover else 160)
            card_surf = pygame.Surface((self.CARD_W, self.CARD_H), pygame.SRCALPHA)
            card_surf.fill((15, 15, 35, bg_alpha))
            canvas.blit(card_surf, rect.topleft)

            # Border
            border_col = ship.color if is_sel else (70, 70, 90)
            border_w   = 3 if is_sel else 1
            pygame.draw.rect(canvas, border_col, rect, border_w, border_radius=10)

            if is_sel:
                glow = pygame.Surface((self.CARD_W - 6, self.CARD_H - 6), pygame.SRCALPHA)
                glow.fill((*ship.color, 18))
                canvas.blit(glow, (rect.x + 3, rect.y + 3))

            cx = rect.centerx

            # Ship name
            name_col  = ship.color if is_sel else (160, 160, 185)
            name_surf = self.med_font.render(ship.name.upper(), True, name_col)
            canvas.blit(name_surf, name_surf.get_rect(centerx=cx, top=rect.y + 14))

            # Tagline
            tag_surf = self.small_font.render(ship.tagline, True, (120, 120, 140))
            canvas.blit(tag_surf, tag_surf.get_rect(centerx=cx, top=rect.y + 62))

            # Divider
            pygame.draw.line(canvas, (50, 50, 75),
                             (rect.x + 16, rect.y + 86), (rect.right - 16, rect.y + 86))

            # Fighter preview (tinted)
            prev = self._previews[i]
            pw, ph = prev.get_size()
            canvas.blit(prev, (cx - pw // 2, rect.y + 96))

            # Stat bars
            BAR_W, BAR_H = 148, 9
            bar_x  = rect.x + 56
            stat_y = rect.y + 196
            for label, val in (("SPD", ship.stat_speed),
                               ("GUN", ship.stat_fire),
                               ("DSH", ship.stat_dash)):
                lbl = self.small_font.render(label, True, (130, 130, 155))
                canvas.blit(lbl, (rect.x + 14, stat_y - 1))
                pygame.draw.rect(canvas, (35, 35, 55),
                                 (bar_x, stat_y + 1, BAR_W, BAR_H), border_radius=3)
                fill_w = int(BAR_W * val / 10)
                if fill_w > 0:
                    col = ship.color if is_sel else (90, 90, 115)
                    pygame.draw.rect(canvas, col,
                                     (bar_x, stat_y + 1, fill_w, BAR_H), border_radius=3)
                stat_y += 28

            # Selected badge
            if is_sel:
                badge_rect = pygame.Rect(rect.x + 12, rect.bottom - 46,
                                         self.CARD_W - 24, 32)
                badge_surf = pygame.Surface((badge_rect.w, badge_rect.h), pygame.SRCALPHA)
                badge_surf.fill((*ship.color, 200))
                canvas.blit(badge_surf, badge_rect.topleft)
                pygame.draw.rect(canvas, (255, 255, 255), badge_rect, 1, border_radius=4)
                badge_txt = self._badge_font.render(
                    "SELECTED  ·  SPACE / CLICK TO START", True, (10, 10, 20))
                canvas.blit(badge_txt, badge_txt.get_rect(center=badge_rect.center))

    def handle_click(self, lpos: tuple, game) -> str | None:
        for i, rect in enumerate(self._card_rects()):
            if rect.collidepoint(lpos):
                if i == game._ship_cursor:
                    game.ui_click_sound.play()
                    return 'confirm'
                game._ship_cursor = i
                game.ui_nav_sound.play()
                return None
        return None

    def handle_key(self, key: int, game) -> str | None:
        if key == pygame.K_ESCAPE:
            game.ui_click_sound.play()
            return 'back'
        if key in (pygame.K_LEFT, pygame.K_a):
            game._ship_cursor = (game._ship_cursor - 1) % len(SHIPS)
            game.ui_nav_sound.play()
        elif key in (pygame.K_RIGHT, pygame.K_d):
            game._ship_cursor = (game._ship_cursor + 1) % len(SHIPS)
            game.ui_nav_sound.play()
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            game.ui_click_sound.play()
            return 'confirm'
        return None
