import pygame
import sys
import config
import random
import math
from enum import Enum
from fighter import Fighter
from alien import Alien
from ball import Ball
from config import GAME_CAPTION, STARTING_LIVES
from assets import Assets
from score_manager import ScoreManager
from settings_manager import Settings, RESOLUTIONS
from explosion import Explosion


class GameState(Enum):
    """All possible game states."""
    START     = "start"
    PLAYING   = "playing"
    PAUSED    = "paused"
    GAME_OVER = "game_over"
    SETTINGS  = "settings"


class Game:
    def __init__(self):
        pygame.display.set_caption(GAME_CAPTION)

        # Apply saved resolution immediately so config module is in sync from the start
        s = Settings.get()
        self.screen_width, self.screen_height = s.resolution
        config.SCREEN_WIDTH  = self.screen_width
        config.SCREEN_HEIGHT = self.screen_height

        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.game_font = pygame.font.Font(None, 36)
        self.clock = pygame.time.Clock()

        # Generate sounds via Assets cache — safe to call multiple times
        self.shoot_sound     = Assets.get_sound('shoot',     frequency=520, duration=0.08)
        self.hit_sound       = Assets.get_sound('hit',       frequency=220, duration=0.25)
        self.lose_life_sound = Assets.get_sound('lose_life', frequency=110, duration=0.5)
        self._apply_volume()

        # Load and scale background to current resolution
        raw_bg = Assets.get_image('image/background.png')
        self.background = pygame.transform.scale(raw_bg, (self.screen_width, self.screen_height)).convert()

        # Pre-scale heart icon for HUD (loaded once, reused every frame)
        raw_heart = Assets.get_image('image/heart.png')
        self.heart_icon = pygame.transform.smoothscale(raw_heart, (22, 22))

        # Load best score from previous session, falls back to 0 if no file exists
        self.best_score = ScoreManager.load()
        self.state = GameState.START

        # All screen-size-dependent button rects computed in one place
        self._update_button_rects()

        # Settings screen state
        self._vol_dragging = False

        # Off-screen canvas for camera shake (same size as display)
        self._canvas      = pygame.Surface((self.screen_width, self.screen_height))
        self._shake_timer = 0   # frames remaining for camera shake
        self._particles: list[dict] = []

        self._init_game()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _update_button_rects(self):
        """Recompute all rects that depend on screen dimensions."""
        cx = self.screen_width  // 2
        cy = self.screen_height // 2
        # Game-over buttons
        self.try_again_rect = pygame.Rect(cx - 100, cy + 20, 200, 50)
        self.quit_rect      = pygame.Rect(cx - 100, cy + 90, 200, 50)
        # Start-screen settings button
        self._settings_btn_rect = pygame.Rect(cx - 70, cy + 50, 140, 40)

    def _apply_volume(self):
        """Push current volume from Settings to all sound objects."""
        vol = Settings.get().volume
        for snd in (self.shoot_sound, self.hit_sound, self.lose_life_sound):
            snd.set_volume(vol)

    def _apply_resolution(self):
        """Apply the resolution stored in Settings to the display and config module."""
        s = Settings.get()
        w, h = s.resolution
        self.screen_width  = w
        self.screen_height = h
        self.screen = pygame.display.set_mode((w, h))
        config.SCREEN_WIDTH  = w
        config.SCREEN_HEIGHT = h
        # Rescale background and recreate canvas for the new window size
        raw_bg = Assets.get_image('image/background.png')
        self.background = pygame.transform.scale(raw_bg, (w, h)).convert()
        self._canvas = pygame.Surface((w, h))
        self._update_button_rects()

    def _init_game(self):
        """Reset all game state for a new round."""
        s = Settings.get()
        self.game_score  = 0
        self.lives       = STARTING_LIVES
        self.flash_timer = 0
        self.fighter = Fighter()
        self.aliens  = pygame.sprite.Group(
            *[Alien(index=i, speed_mult=s.alien_speed_mult) for i in range(s.alien_count)]
        )
        self.balls      = pygame.sprite.Group()
        self._ball_queue = []  # insertion-order list for FIFO removal
        self.explosions  = pygame.sprite.Group()
        self._particles  = []
        self._shake_timer = 0

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        """Main game loop — runs forever, switching behavior based on current state."""
        while True:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._handle_event(event)

            self.screen.blit(self.background, (0, 0))

            if   self.state == GameState.START:
                self._draw_start_screen()
            elif self.state == GameState.PLAYING:
                self._update(dt)
                self._draw()
            elif self.state == GameState.PAUSED:
                self._draw()
                self._draw_pause_overlay()
            elif self.state == GameState.GAME_OVER:
                self._draw_game_over_screen()
            elif self.state == GameState.SETTINGS:
                self._draw_settings_screen()

            pygame.display.update()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _handle_event(self, event):
        """Route input events based on the current game state."""
        if event.type == pygame.KEYDOWN:
            if self.state == GameState.START:
                if event.key == pygame.K_SPACE:
                    self.state = GameState.PLAYING

            elif self.state == GameState.PLAYING:
                if event.key in (pygame.K_LEFT,  pygame.K_a): self.fighter.move_left()
                if event.key in (pygame.K_RIGHT, pygame.K_d): self.fighter.move_right()
                if event.key in (pygame.K_UP,    pygame.K_w): self.fighter.move_up()
                if event.key in (pygame.K_DOWN,  pygame.K_s): self.fighter.move_down()
                if event.key == pygame.K_SPACE:
                    self._shoot()
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.fighter.dash()
                if event.key == pygame.K_p:
                    self.state = GameState.PAUSED

            elif self.state == GameState.PAUSED:
                if event.key == pygame.K_p:
                    self.state = GameState.PLAYING

            elif self.state == GameState.SETTINGS:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.START

        if event.type == pygame.KEYUP:
            if self.state == GameState.PLAYING:
                if event.key in (pygame.K_LEFT,  pygame.K_a): self.fighter.is_moving_left  = False
                if event.key in (pygame.K_RIGHT, pygame.K_d): self.fighter.is_moving_right = False
                if event.key in (pygame.K_UP,    pygame.K_w): self.fighter.is_moving_up    = False
                if event.key in (pygame.K_DOWN,  pygame.K_s): self.fighter.is_moving_down  = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.state == GameState.PLAYING:
                if event.button == 1:
                    self._shoot()
            elif self.state == GameState.GAME_OVER:
                if self.try_again_rect.collidepoint(event.pos):
                    self._init_game()
                    self.state = GameState.PLAYING
                if self.quit_rect.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()
            elif self.state == GameState.START:
                if self._settings_btn_rect.collidepoint(event.pos):
                    self.state = GameState.SETTINGS
            elif self.state == GameState.SETTINGS:
                self._handle_settings_click(event.pos)

        if event.type == pygame.MOUSEMOTION:
            if self.state == GameState.SETTINGS and self._vol_dragging:
                self._update_volume_from_mouse(event.pos[0])

        if event.type == pygame.MOUSEBUTTONUP:
            if self._vol_dragging:
                self._vol_dragging = False
                Settings.get().save()

    # ------------------------------------------------------------------
    # Settings screen logic
    # ------------------------------------------------------------------

    def _settings_layout(self) -> dict:
        """Compute rects for all interactive elements on the settings screen."""
        cx = self.screen_width // 2

        # Volume slider centred horizontally
        slider_w, slider_h = 400, 12
        slider_x = cx - slider_w // 2
        slider_y = 230

        # Resolution buttons
        btn_w, btn_h = 160, 44
        gap = 16
        total_res_w = 3 * btn_w + 2 * gap
        res_x0 = cx - total_res_w // 2
        res_rects = [
            pygame.Rect(res_x0 + i * (btn_w + gap), 335, btn_w, btn_h)
            for i in range(3)
        ]

        # Difficulty buttons
        diff_w = 140
        total_diff_w = 3 * diff_w + 2 * gap
        diff_x0 = cx - total_diff_w // 2
        diff_rects = [
            pygame.Rect(diff_x0 + i * (diff_w + gap), 455, diff_w, btn_h)
            for i in range(3)
        ]

        back_rect = pygame.Rect(cx - 80, 560, 160, 50)

        return {
            'slider_x': slider_x, 'slider_y': slider_y,
            'slider_w': slider_w, 'slider_h': slider_h,
            # Hit area is slightly larger than the visual bar for easier grabbing
            'slider_hit': pygame.Rect(slider_x - 8, slider_y - 10, slider_w + 16, slider_h + 20),
            'res_rects':  res_rects,
            'diff_rects': diff_rects,
            'back_rect':  back_rect,
        }

    def _handle_settings_click(self, pos: tuple[int, int]):
        lay = self._settings_layout()
        s   = Settings.get()

        # Volume slider
        if lay['slider_hit'].collidepoint(pos):
            self._vol_dragging = True
            self._update_volume_from_mouse(pos[0])
            return

        # Resolution buttons
        for i, rect in enumerate(lay['res_rects']):
            if rect.collidepoint(pos):
                s.resolution_index = i
                s.save()
                self._apply_resolution()
                return

        # Difficulty buttons
        for i, (_, dkey, _) in enumerate([
            ("EASY",   "easy",   None),
            ("NORMAL", "normal", None),
            ("HARD",   "hard",   None),
        ]):
            if lay['diff_rects'][i].collidepoint(pos):
                s.difficulty = dkey
                s.save()
                return

        # Back button
        if lay['back_rect'].collidepoint(pos):
            self.state = GameState.START

    def _update_volume_from_mouse(self, mouse_x: int):
        lay   = self._settings_layout()
        ratio = (mouse_x - lay['slider_x']) / lay['slider_w']
        s     = Settings.get()
        s.volume = max(0.0, min(1.0, ratio))
        self._apply_volume()

    # ------------------------------------------------------------------
    # Shooting helpers
    # ------------------------------------------------------------------

    def _shoot(self):
        """Fire a projectile. If 3 are already in flight, the oldest is removed first (FIFO)."""
        if len(self._ball_queue) >= 3:
            oldest = self._ball_queue.pop(0)
            oldest.kill()
        ball = Ball(self.fighter)
        self.balls.add(ball)
        self._ball_queue.append(ball)
        self.shoot_sound.play()

    def _ball_queue_remove(self, ball):
        """Remove a ball from the FIFO queue if still present (idempotent)."""
        try:
            self._ball_queue.remove(ball)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self, dt):
        """Update all game objects and check for collisions."""
        self.fighter.update(dt)
        self.aliens.update(dt)
        self.balls.update(dt)
        self.explosions.update(dt)
        self._update_particles(dt)

        # Remove balls that have left the top of the screen
        for ball in list(self.balls):
            if ball.is_out_of_screen():
                ball.kill()
                self._ball_queue_remove(ball)

        # Check ball-alien collisions — True removes the ball from its group on hit
        hits = pygame.sprite.groupcollide(self.balls, self.aliens, True, False)
        for ball in hits.keys():
            self._ball_queue_remove(ball)
        for aliens_hit in hits.values():
            for alien in aliens_hit:
                cx, cy = alien.rect.center
                # Explosion animation
                self.explosions.add(Explosion(cx, cy))
                # Particle burst
                for _ in range(12):
                    angle = random.uniform(0, math.tau)
                    speed = random.uniform(60, 190)
                    life  = random.uniform(0.35, 0.65)
                    color = random.choice([
                        (255, 220, 0), (255, 140, 0),
                        (255, 70,  0), (255, 255, 100),
                    ])
                    self._particles.append({
                        'x': float(cx), 'y': float(cy),
                        'vx': math.cos(angle) * speed,
                        'vy': math.sin(angle) * speed,
                        'life': life, 'max_life': life,
                        'color': color,
                        'size': random.randint(2, 5),
                    })
                alien.reset()
                self.game_score += 1
                if self.game_score > self.best_score:
                    self.best_score = self.game_score
                    ScoreManager.save(self.best_score)
                self.hit_sound.play()

        # Check if any alien has reached the fighter or tunneled past it
        for alien in list(self.aliens):
            passed_fighter = alien.has_reached_fighter(self.fighter)
            flew_off_screen = alien.rect.top > self.screen_height
            if passed_fighter or flew_off_screen:
                self.lives -= 1
                self.flash_timer = 20
                self._shake_timer = 5  # camera shake on life lost
                alien.reset()
                self.lose_life_sound.play()
                if self.lives <= 0:
                    self.state = GameState.GAME_OVER
                    return

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw(self):
        """Draw all game objects and effects onto the canvas, then blit to screen with shake."""
        cv = self._canvas

        # Draw the game world onto the off-screen canvas
        cv.blit(self.background, (0, 0))
        cv.blit(self.fighter.image, self.fighter.rect)
        self.aliens.draw(cv)
        self.balls.draw(cv)
        self.explosions.draw(cv)
        self._draw_particles(cv)

        # Red tint flash when a life is lost — SRCALPHA ensures proper per-pixel blending
        if self.flash_timer > 0:
            alpha = int(self.flash_timer * 4.5)   # max ~90 at timer=20 — subtle tint only
            flash_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            flash_surface.fill((255, 0, 0, alpha))
            cv.blit(flash_surface, (0, 0))
            self.flash_timer -= 1

        self._draw_hud(cv)

        # Camera shake — pick a random offset while timer is active
        if self._shake_timer > 0:
            ox = random.randint(-8, 8)
            oy = random.randint(-5, 5)
            self._shake_timer -= 1
        else:
            ox, oy = 0, 0

        self.screen.fill((0, 0, 0))          # black border visible only during shake
        self.screen.blit(cv, (ox, oy))

    def _update_particles(self, dt: float):
        """Advance all active particles and discard expired ones."""
        alive = []
        for p in self._particles:
            p['x']    += p['vx'] * dt
            p['y']    += p['vy'] * dt
            p['vy']   += 90.0 * dt   # gentle gravity
            p['life'] -= dt
            if p['life'] > 0:
                alive.append(p)
        self._particles = alive

    def _draw_particles(self, surface: pygame.Surface):
        """Draw all active particles as tiny fading rectangles."""
        for p in self._particles:
            ratio = p['life'] / p['max_life']
            r = int(p['color'][0] * ratio)
            g = int(p['color'][1] * ratio)
            b = int(p['color'][2] * ratio)
            s = p['size']
            pygame.draw.rect(surface, (r, g, b),
                             (int(p['x']) - s // 2, int(p['y']) - s // 2, s, s))

    def _draw_hud(self, surface: pygame.Surface):
        """Draw the heads-up display: score, best score, lives (heart icons), and dash indicator."""
        score_text = self.game_font.render(
            f"Score: {self.game_score}   Best: {self.best_score}   Lives:",
            True, 'white'
        )
        surface.blit(score_text, (20, 20))

        # Heart icons drawn right after the text
        hearts_x = 20 + score_text.get_width() + 6
        hearts_y = 20 + score_text.get_height() // 2 - self.heart_icon.get_height() // 2
        for i in range(self.lives):
            surface.blit(self.heart_icon, (hearts_x + i * 26, hearts_y))

        # Dash cooldown bar — shown below the score line
        bar_x, bar_y, bar_w, bar_h = 20, 52, 80, 6
        ratio = self.fighter.dash_cooldown_ratio  # 0.0 = ready, 1.0 = just used
        if ratio > 0:
            pygame.draw.rect(surface, (60, 60, 60),  (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            fill_w = int(bar_w * (1.0 - ratio))
            if fill_w > 0:
                pygame.draw.rect(surface, (0, 220, 255), (bar_x, bar_y, fill_w, bar_h), border_radius=3)
            label = self.game_font.render("DASH", True, (120, 120, 120))
        else:
            pygame.draw.rect(surface, (0, 220, 255), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            label = self.game_font.render("DASH", True, (0, 220, 255))
        surface.blit(
            pygame.transform.scale(label, (int(label.get_width() * 0.6), int(label.get_height() * 0.6))),
            (bar_x + bar_w + 6, bar_y - 2)
        )

    def _draw_start_screen(self):
        """Draw the initial start screen with title, prompt, and settings button."""
        cx = self.screen_width  // 2
        cy = self.screen_height // 2

        title_text = self.game_font.render("Space Shooter", True, 'white')
        self.screen.blit(title_text, title_text.get_rect(center=(cx, cy - 40)))

        start_text = self.game_font.render("Press SPACE to start", True, 'yellow')
        self.screen.blit(start_text, start_text.get_rect(center=(cx, cy + 10)))

        pygame.draw.rect(self.screen, (60, 60, 90), self._settings_btn_rect, border_radius=8)
        btn_text = self.game_font.render("Settings", True, 'white')
        self.screen.blit(btn_text, btn_text.get_rect(center=self._settings_btn_rect.center))

    def _draw_pause_overlay(self):
        """Draw the pause message over the frozen game screen."""
        pause_text = self.game_font.render("PAUSED — press P to continue", True, 'yellow')
        pause_rect = pause_text.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
        self.screen.blit(pause_text, pause_rect)

    def _draw_game_over_screen(self):
        """Draw the game over screen with final score and action buttons."""
        cx = self.screen_width  // 2
        cy = self.screen_height // 2

        game_over_text = self.game_font.render("Game Over", True, 'white')
        self.screen.blit(game_over_text, game_over_text.get_rect(center=(cx, cy - 80)))

        score_text = self.game_font.render(f"Score: {self.game_score}", True, 'white')
        self.screen.blit(score_text, score_text.get_rect(center=(cx, cy - 40)))

        pygame.draw.rect(self.screen, 'green', self.try_again_rect, border_radius=8)
        try_again_text = self.game_font.render("Try Again", True, 'white')
        self.screen.blit(try_again_text, try_again_text.get_rect(center=self.try_again_rect.center))

        pygame.draw.rect(self.screen, (180, 50, 50), self.quit_rect, border_radius=8)
        quit_text = self.game_font.render("Quit", True, 'white')
        self.screen.blit(quit_text, quit_text.get_rect(center=self.quit_rect.center))

    def _draw_settings_screen(self):
        """Draw the settings screen with volume slider, resolution and difficulty selectors."""
        s   = Settings.get()
        lay = self._settings_layout()
        cx  = self.screen_width // 2

        # ── Title ──────────────────────────────────────────────────────
        title = self.game_font.render("SETTINGS", True, 'white')
        self.screen.blit(title, title.get_rect(center=(cx, 110)))

        # ── Volume ────────────────────────────────────────────────────
        self.screen.blit(
            self.game_font.render("VOLUME", True, (160, 160, 160)),
            (lay['slider_x'], lay['slider_y'] - 30)
        )
        sx, sy, sw, sh = lay['slider_x'], lay['slider_y'], lay['slider_w'], lay['slider_h']
        pygame.draw.rect(self.screen, (55, 55, 65), (sx, sy, sw, sh), border_radius=6)
        fill_w = int(sw * s.volume)
        if fill_w > 0:
            pygame.draw.rect(self.screen, (0, 200, 255), (sx, sy, fill_w, sh), border_radius=6)
        # Knob
        knob_x = sx + fill_w
        pygame.draw.circle(self.screen, (220, 220, 220), (knob_x, sy + sh // 2), 9)
        pct = self.game_font.render(f"{int(s.volume * 100)}%", True, 'white')
        self.screen.blit(pct, (sx + sw + 14, sy - 4))

        # ── Resolution ────────────────────────────────────────────────
        self.screen.blit(
            self.game_font.render("RESOLUTION", True, (160, 160, 160)),
            (lay['res_rects'][0].x, lay['res_rects'][0].y - 28)
        )
        res_labels = ["1024×768", "1280×720", "1920×1080"]
        for i, (rect, lbl) in enumerate(zip(lay['res_rects'], res_labels)):
            color = (0, 150, 210) if i == s.resolution_index else (50, 50, 68)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            if i == s.resolution_index:
                pygame.draw.rect(self.screen, (0, 210, 255), rect, 2, border_radius=8)
            t = self.game_font.render(lbl, True, 'white')
            self.screen.blit(t, t.get_rect(center=rect.center))

        # ── Difficulty ────────────────────────────────────────────────
        self.screen.blit(
            self.game_font.render("DIFFICULTY", True, (160, 160, 160)),
            (lay['diff_rects'][0].x, lay['diff_rects'][0].y - 28)
        )
        diff_items = [
            ("EASY",   "easy",   (55, 170, 55)),
            ("NORMAL", "normal", (0,  150, 210)),
            ("HARD",   "hard",   (190, 50, 50)),
        ]
        for i, (dlbl, dkey, dcolor) in enumerate(diff_items):
            rect  = lay['diff_rects'][i]
            color = dcolor if dkey == s.difficulty else (50, 50, 68)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            if dkey == s.difficulty:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=8)
            t = self.game_font.render(dlbl, True, 'white')
            self.screen.blit(t, t.get_rect(center=rect.center))

        # ── Back ──────────────────────────────────────────────────────
        pygame.draw.rect(self.screen, (65, 65, 85), lay['back_rect'], border_radius=8)
        back_t = self.game_font.render("BACK", True, 'white')
        self.screen.blit(back_t, back_t.get_rect(center=lay['back_rect'].center))

        hint = self.game_font.render("ESC to go back", True, (90, 90, 100))
        self.screen.blit(hint, hint.get_rect(center=(cx, lay['back_rect'].bottom + 22)))
