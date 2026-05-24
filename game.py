import pygame
import sys
import config
import random
import math
from enum import Enum
from fighter import Fighter
from alien import Alien, ArmoredAlien, ZigzagAlien, ShooterAlien
from alien_bullet import AlienBullet
from ball import Ball
from boss import Boss
from powerup import TripleShotPowerUp, ShieldPowerUp, SlowTimePowerUp
from config import GAME_CAPTION, STARTING_LIVES
from assets import Assets
from score_manager import ScoreManager
from settings_manager import Settings, RESOLUTIONS
from explosion import Explosion
from ship import ShipConfig, SHIPS


class GameState(Enum):
    """All possible game states."""
    START       = "start"
    SHIP_SELECT = "ship_select"
    PLAYING     = "playing"
    PAUSED      = "paused"
    GAME_OVER   = "game_over"
    SETTINGS    = "settings"


# Fixed logical game-world resolution — sprites and physics always live in this space.
# The canvas is scaled up to the real display size, so higher resolutions look crisp.
_LOGICAL_W, _LOGICAL_H = 1280, 720


class Game:
    def __init__(self):
        pygame.display.set_caption(GAME_CAPTION)

        # The display always runs at the logical resolution.
        # pygame.SCALED lets pygame (not the OS compositor) handle HiDPI upscaling,
        # which prevents macOS/Windows from applying blurry bilinear filtering on top.
        s = Settings.get()
        # Game-world / layout space is always 1280×720 — all positions are in these coords
        self.screen_width  = _LOGICAL_W
        self.screen_height = _LOGICAL_H
        config.SCREEN_WIDTH  = _LOGICAL_W
        config.SCREEN_HEIGHT = _LOGICAL_H

        # Physical display size (from settings; can differ from the logical canvas)
        self._disp_w, self._disp_h = s.resolution
        # Scale factors for transforming display-space mouse coords → logical (1280×720) coords
        self._mouse_sx = _LOGICAL_W / self._disp_w
        self._mouse_sy = _LOGICAL_H / self._disp_h
        # Camera-shake offset (set by _draw, consumed by run)
        self._shake_ox = 0
        self._shake_oy = 0

        # pygame.SCALED prevents the OS compositor from applying blurry bilinear filtering
        # (critical on macOS Retina / HiDPI).  We run the display at the user-chosen physical
        # resolution; our 1280×720 canvas is manually scaled to fill it each frame.
        _fs_flags = (pygame.FULLSCREEN | pygame.SCALED) if s.fullscreen else pygame.SCALED
        self.screen = pygame.display.set_mode((self._disp_w, self._disp_h), _fs_flags)
        self.game_font  = pygame.font.Font(None, 36)
        self.med_font   = pygame.font.Font(None, 52)   # ship names in selection cards
        self.small_font = pygame.font.Font(None, 26)   # stat labels / table rows
        self.wave_font  = pygame.font.Font(None, 86)   # large font for wave announcements
        self.clock = pygame.time.Clock()

        # Generate sounds via Assets cache — safe to call multiple times
        self.shoot_sound     = Assets.get_sound('shoot',     frequency=520, duration=0.08)
        self.hit_sound       = Assets.get_sound('hit',       frequency=220, duration=0.25)
        self.lose_life_sound = Assets.get_sound('lose_life', frequency=110, duration=0.5)
        self.powerup_sound   = Assets.get_sound('powerup',   frequency=740, duration=0.22)
        self._apply_volume()

        # Single background scaled to logical resolution — used everywhere
        raw_bg = Assets.get_image('image/background.png')
        self.background = pygame.transform.scale(raw_bg, (_LOGICAL_W, _LOGICAL_H)).convert()

        # Pre-scale heart icon for HUD (loaded once, reused every frame)
        raw_heart = Assets.get_image('image/heart.png')
        self.heart_icon = pygame.transform.smoothscale(raw_heart, (22, 22))

        # Pre-build fighter preview sprites for the ship-select cards (scaled down, colour-tinted)
        raw_fighter = Assets.get_image('image/fighter.png')
        fw, fh = raw_fighter.get_size()
        _prev_h = 80
        _prev_w = int(fw * (_prev_h / fh))
        _prev_base = pygame.transform.scale(raw_fighter, (_prev_w, _prev_h))
        self._ship_previews: list[pygame.Surface] = []
        for _ship in SHIPS:
            _s = _prev_base.copy()
            _tint = pygame.Surface((_prev_w, _prev_h), pygame.SRCALPHA)
            _tint.fill((*_ship.color, 90))
            _s.blit(_tint, (0, 0))
            self._ship_previews.append(_s)

        # Load leaderboard from previous sessions
        self.best_score, self.score_entries = ScoreManager.load()

        # Ship-selection state
        self._selected_ship: ShipConfig = SHIPS[0]
        self._ship_cursor: int = 0   # index currently highlighted in select screen

        self.state = GameState.START

        # All screen-size-dependent button rects computed in one place
        self._update_button_rects()


        # Settings screen state
        self._vol_dragging = False

        # Off-screen canvas — always logical size (1280×720); scaled to display each frame
        self._canvas      = pygame.Surface((_LOGICAL_W, _LOGICAL_H))
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

        # ── Game-over buttons ─────────────────────────────
        # Total width: 210 + 20 gap + 130 = 360; centred → start at cx-180
        self.try_again_rect  = pygame.Rect(cx - 180, cy + 165, 210, 48)
        self.menu_go_rect    = pygame.Rect(cx + 50,  cy + 165, 130, 48)

        # ── Start-screen buttons (lower-right cluster) ────
        # Scores occupy the lower-centre; buttons sit at bottom-right
        self._play_btn_rect      = pygame.Rect(cx - 80, cy + 145, 160, 48)
        self._settings_btn_rect  = pygame.Rect(cx - 80, cy + 203, 160, 40)
        self._quit_start_rect    = pygame.Rect(cx - 80, cy + 253, 160, 40)

    def _apply_volume(self):
        """Push current volume from Settings to all sound objects."""
        vol = Settings.get().volume
        for snd in (self.shoot_sound, self.hit_sound,
                    self.lose_life_sound, self.powerup_sound):
            snd.set_volume(vol)

    def _apply_resolution(self):
        """Recreate the display at the resolution stored in Settings.

        The logical canvas (1280×720) never changes — all game code draws at logical coords.
        The display surface is sized to the user's chosen resolution; we scale the canvas
        to fill it each frame.  pygame.SCALED prevents the OS compositor from adding blur.
        """
        s = Settings.get()
        self._disp_w, self._disp_h = s.resolution
        self._mouse_sx = _LOGICAL_W / self._disp_w
        self._mouse_sy = _LOGICAL_H / self._disp_h
        flags = (pygame.FULLSCREEN | pygame.SCALED) if s.fullscreen else pygame.SCALED
        self.screen = pygame.display.set_mode((self._disp_w, self._disp_h), flags)
        self._update_button_rects()

    # ------------------------------------------------------------------
    # Logical-coordinate helpers (transforms display-space → 1280×720 space)
    # ------------------------------------------------------------------

    def _lpos(self, pos: tuple[int, int]) -> tuple[int, int]:
        """Convert a display-space position to logical (1280×720) coordinates."""
        return (int(pos[0] * self._mouse_sx), int(pos[1] * self._mouse_sy))

    def _lmouse(self) -> tuple[int, int]:
        """Return the current mouse position in logical (1280×720) coordinates."""
        return self._lpos(pygame.mouse.get_pos())

    def _toggle_fullscreen(self):
        """Flip the fullscreen flag and immediately apply it."""
        s = Settings.get()
        s.fullscreen = not s.fullscreen
        s.save()
        self._apply_resolution()

    def _init_game(self):
        """Reset all game state for a new round (wave 1)."""
        self.game_score        = 0
        self.lives             = STARTING_LIVES
        self.flash_timer       = 0
        self.wave              = 0   # set to 1 by _start_wave below
        self.fighter           = Fighter(ship=self._selected_ship)
        self.balls             = pygame.sprite.Group()
        self._ball_queue       = []
        self.explosions        = pygame.sprite.Group()
        self.alien_bullets     = pygame.sprite.Group()
        self.powerups          = pygame.sprite.Group()
        self.boss              = None
        self._particles        = []
        self._shake_timer      = 0
        self._wave_banner_timer = 0.0
        # Power-up state
        self._triple_shot_timer = 0.0   # > 0 while 3× shot is active
        self._shield_active     = False  # absorbs one hit
        self._slow_time_timer   = 0.0   # > 0 while slow is active
        self._start_wave(1)

    def _start_wave(self, wave_num: int):
        """Spawn a fresh wave of enemies.  Every 5th wave is a boss fight."""
        self.wave              = wave_num
        self.alien_bullets     = pygame.sprite.Group()
        self.powerups          = pygame.sprite.Group()
        self._wave_banner_timer = 2.8

        if wave_num % 5 == 0:
            # Boss wave — no regular aliens
            self.boss   = Boss(wave_num)
            self.aliens = pygame.sprite.Group()
        else:
            self.boss   = None
            self.aliens = pygame.sprite.Group(*self._make_wave_aliens(wave_num))

    def _make_wave_aliens(self, wave_num: int) -> list:
        """Return a list of alien sprites tuned for *wave_num* and current difficulty."""
        s     = Settings.get()
        count = s.alien_count + (wave_num - 1)          # +1 alien per wave
        # Speed grows 15 % per wave, capped at 4× the difficulty baseline
        speed = s.alien_speed_mult * (1.0 + (wave_num - 1) * 0.15)
        speed = min(speed, s.alien_speed_mult * 4.0)

        aliens = []
        for i in range(count):
            roll = random.random()
            if   wave_num >= 4 and roll < 0.15:   cls = ShooterAlien
            elif wave_num >= 3 and roll < 0.30:   cls = ZigzagAlien
            elif wave_num >= 2 and roll < 0.30:   cls = ArmoredAlien
            else:                                  cls = Alien
            aliens.append(cls(index=i, speed_mult=speed))
        return aliens

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

            # For non-gameplay states draw the background onto the canvas directly.
            # (_draw() already does its own canvas clear for PLAYING/PAUSED.)
            if self.state not in (GameState.PLAYING, GameState.PAUSED):
                self._canvas.blit(self.background, (0, 0))
                self._shake_ox = 0
                self._shake_oy = 0

            if   self.state == GameState.START:
                self._draw_start_screen()
            elif self.state == GameState.SHIP_SELECT:
                self._draw_ship_select_screen()
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

            # Scale the logical canvas (1280×720) up to the chosen display resolution and
            # apply the camera-shake offset computed by _draw().
            if self._disp_w != _LOGICAL_W or self._disp_h != _LOGICAL_H:
                scaled = pygame.transform.smoothscale(
                    self._canvas, (self._disp_w, self._disp_h))
            else:
                scaled = self._canvas
            self.screen.fill((0, 0, 0))
            self.screen.blit(scaled, (self._shake_ox, self._shake_oy))

            pygame.display.update()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _handle_event(self, event):
        """Route input events based on the current game state."""
        if event.type == pygame.KEYDOWN:
            # F11 toggles fullscreen from any screen
            if event.key == pygame.K_F11:
                self._toggle_fullscreen()

            if self.state == GameState.START:
                if event.key == pygame.K_SPACE:
                    self.state = GameState.SHIP_SELECT

            elif self.state == GameState.SHIP_SELECT:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.START
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self._ship_cursor = (self._ship_cursor - 1) % len(SHIPS)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._ship_cursor = (self._ship_cursor + 1) % len(SHIPS)
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._confirm_ship_select()

            elif self.state == GameState.PLAYING:
                if event.key in (pygame.K_LEFT,  pygame.K_a): self.fighter.move_left()
                if event.key in (pygame.K_RIGHT, pygame.K_d): self.fighter.move_right()
                if event.key in (pygame.K_UP,    pygame.K_w): self.fighter.move_up()
                if event.key in (pygame.K_DOWN,  pygame.K_s): self.fighter.move_down()
                if event.key == pygame.K_SPACE:
                    self._shoot()
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.fighter.dash()
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = GameState.PAUSED

            elif self.state == GameState.PAUSED:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
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
            lpos = self._lpos(event.pos)
            if self.state == GameState.PLAYING:
                if event.button == 1:
                    self._shoot()
            elif self.state == GameState.PAUSED:
                self._handle_pause_click(lpos)
            elif self.state == GameState.GAME_OVER:
                if self.try_again_rect.collidepoint(lpos):
                    self._init_game()
                    self.state = GameState.PLAYING
                elif self.menu_go_rect.collidepoint(lpos):
                    self._init_game()
                    self.state = GameState.START
            elif self.state == GameState.START:
                if self._play_btn_rect.collidepoint(lpos):
                    self.state = GameState.SHIP_SELECT
                elif self._settings_btn_rect.collidepoint(lpos):
                    self.state = GameState.SETTINGS
                elif self._quit_start_rect.collidepoint(lpos):
                    pygame.quit()
                    sys.exit()
            elif self.state == GameState.SHIP_SELECT:
                self._handle_ship_select_click(lpos)
            elif self.state == GameState.SETTINGS:
                self._handle_settings_click(lpos)

        if event.type == pygame.MOUSEMOTION:
            if self._vol_dragging:
                lx = self._lpos(event.pos)[0]
                if self.state == GameState.SETTINGS:
                    self._update_volume_from_mouse(lx)
                elif self.state == GameState.PAUSED:
                    self._update_pause_volume_from_mouse(lx)

        if event.type == pygame.MOUSEBUTTONUP:
            if self._vol_dragging:
                self._vol_dragging = False
                Settings.get().save()  # persist volume regardless of which screen it was changed on

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

        # Resolution buttons  (4 options now — 1024, 1280, 1920, 2560)
        btn_w, btn_h = 130, 44
        gap = 12
        total_res_w = 4 * btn_w + 3 * gap
        res_x0 = cx - total_res_w // 2
        res_rects = [
            pygame.Rect(res_x0 + i * (btn_w + gap), 335, btn_w, btn_h)
            for i in range(4)
        ]

        # Difficulty buttons
        diff_w = 140
        total_diff_w = 3 * diff_w + 2 * gap
        diff_x0 = cx - total_diff_w // 2
        diff_rects = [
            pygame.Rect(diff_x0 + i * (diff_w + gap), 455, diff_w, btn_h)
            for i in range(3)
        ]

        fullscreen_rect = pygame.Rect(cx - 150, 508, 300, 42)
        back_rect       = pygame.Rect(cx - 80,  568, 160, 50)

        return {
            'slider_x': slider_x, 'slider_y': slider_y,
            'slider_w': slider_w, 'slider_h': slider_h,
            # Hit area is slightly larger than the visual bar for easier grabbing
            'slider_hit':     pygame.Rect(slider_x - 8, slider_y - 10, slider_w + 16, slider_h + 20),
            'res_rects':      res_rects,
            'diff_rects':     diff_rects,
            'fullscreen_rect': fullscreen_rect,
            'back_rect':      back_rect,
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

        # Fullscreen toggle
        if lay['fullscreen_rect'].collidepoint(pos):
            self._toggle_fullscreen()
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
    # Pause menu logic
    # ------------------------------------------------------------------

    def _pause_layout(self) -> dict:
        """Compute rects for all interactive elements on the pause menu."""
        cx = self.screen_width  // 2
        cy = self.screen_height // 2

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
            'slider_hit': pygame.Rect(slider_x - 8, slider_y - 10, slider_w + 16, slider_h + 20),
            'resume_rect':    pygame.Rect(btn_x, panel_y + 165, btn_w, btn_h),
            'restart_rect':   pygame.Rect(btn_x, panel_y + 221, btn_w, btn_h),
            'menu_rect':      pygame.Rect(btn_x, panel_y + 277, btn_w, btn_h),
            # Quit is separated by a larger gap — it's a destructive action
            'quit_rect':      pygame.Rect(btn_x, panel_y + 349, btn_w, btn_h),
        }

    def _handle_pause_click(self, pos: tuple[int, int]):
        lay = self._pause_layout()

        if lay['slider_hit'].collidepoint(pos):
            self._vol_dragging = True
            self._update_pause_volume_from_mouse(pos[0])
            return

        if lay['resume_rect'].collidepoint(pos):
            self.state = GameState.PLAYING
            return

        if lay['restart_rect'].collidepoint(pos):
            self._init_game()
            self.state = GameState.PLAYING
            return

        if lay['menu_rect'].collidepoint(pos):
            self._init_game()
            self.state = GameState.START
            return

        if lay['quit_rect'].collidepoint(pos):
            pygame.quit()
            sys.exit()

    def _update_pause_volume_from_mouse(self, mouse_x: int):
        lay   = self._pause_layout()
        ratio = (mouse_x - lay['slider_x']) / lay['slider_w']
        s     = Settings.get()
        s.volume = max(0.0, min(1.0, ratio))
        self._apply_volume()

    # ------------------------------------------------------------------
    # Ship-selection helpers
    # ------------------------------------------------------------------

    def _ship_card_rects(self) -> list[pygame.Rect]:
        """Return the bounding Rect for each ship card on the select screen."""
        CARD_W, CARD_H = 265, 375
        GAP   = 45
        total = len(SHIPS) * CARD_W + (len(SHIPS) - 1) * GAP
        start_x = (config.SCREEN_WIDTH - total) // 2
        card_y  = 118
        return [
            pygame.Rect(start_x + i * (CARD_W + GAP), card_y, CARD_W, CARD_H)
            for i in range(len(SHIPS))
        ]

    def _confirm_ship_select(self):
        """Lock in the highlighted ship and start a new game."""
        self._selected_ship = SHIPS[self._ship_cursor]
        self._init_game()
        self.state = GameState.PLAYING

    def _handle_ship_select_click(self, pos: tuple[int, int]):
        rects = self._ship_card_rects()
        for i, rect in enumerate(rects):
            if rect.collidepoint(pos):
                if i == self._ship_cursor:
                    # Second click on already-highlighted card → confirm
                    self._confirm_ship_select()
                else:
                    # First click → just highlight
                    self._ship_cursor = i
                return

    # ------------------------------------------------------------------
    # Shooting helpers
    # ------------------------------------------------------------------

    def _shoot(self):
        """Fire bullets based on active power-up and ship characteristics, FIFO-limited."""
        if self._triple_shot_timer > 0:
            # Triple-shot powerup always fires 3 bullets regardless of ship
            angles = [-18, 0, 18]
            limit  = 9
        else:
            ship = self._selected_ship
            if ship.default_shots == 2:
                angles = [-10, 10]     # Hydra dual-cannon spread
            else:
                angles = [0]
            limit = ship.max_bullets

        # Trim oldest bullets to stay within the queue limit
        while len(self._ball_queue) + len(angles) > limit:
            if self._ball_queue:
                self._ball_queue.pop(0).kill()
            else:
                break

        for ang in angles:
            ball = Ball(self.fighter, angle_deg=ang)
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
        # ── Countdown timers ───────────────────────────────────────────
        if self._wave_banner_timer > 0: self._wave_banner_timer -= dt
        if self._triple_shot_timer > 0: self._triple_shot_timer -= dt
        if self._slow_time_timer   > 0: self._slow_time_timer   -= dt

        # Slow-time factor: aliens & their bullets move at 30 % when active
        slow = 0.30 if self._slow_time_timer > 0 else 1.0

        # ── Physics updates ────────────────────────────────────────────
        self.fighter.update(dt)
        self.powerups.update(dt)
        self.aliens.update(dt * slow)
        self.balls.update(dt)
        self.explosions.update(dt)
        self.alien_bullets.update(dt * slow)
        self._update_particles(dt)

        # ── Boss ───────────────────────────────────────────────────────
        self._update_boss(dt)
        if self.state == GameState.GAME_OVER:
            return

        # ── Player bullets leaving screen ─────────────────────────────
        for ball in list(self.balls):
            if ball.is_out_of_screen():
                ball.kill()
                self._ball_queue_remove(ball)

        # ── Alien bullets leaving screen ───────────────────────────────
        for ab in list(self.alien_bullets):
            if ab.is_off_screen():
                ab.kill()

        # ── Power-up collection ────────────────────────────────────────
        for pu in list(self.powerups):
            if pu.is_off_screen():
                pu.kill()
                continue
            if pu.rect.colliderect(self.fighter.rect):
                self._apply_powerup(pu)
                pu.kill()

        # ── ShooterAlien fires ─────────────────────────────────────────
        for alien in self.aliens:
            if isinstance(alien, ShooterAlien):
                for cx, cy in alien.drain_shots():
                    self.alien_bullets.add(AlienBullet(cx, cy))

        # ── Player bullets → aliens ────────────────────────────────────
        hits = pygame.sprite.groupcollide(self.balls, self.aliens, True, False)
        for ball in hits.keys():
            self._ball_queue_remove(ball)
        for aliens_hit in hits.values():
            for alien in aliens_hit:
                if not alien.alive():
                    continue
                cx, cy = alien.rect.center
                if alien.take_hit():
                    alien.kill()
                    self.explosions.add(Explosion(cx, cy))
                    self._spawn_particles(cx, cy)
                    self._maybe_drop_powerup(cx, cy)
                    self.game_score += alien.SCORE
                    if self.game_score > self.best_score:
                        self.best_score = self.game_score
                        ScoreManager.save(self.best_score)
                else:
                    self._spawn_particles(cx, cy, count=5,
                                         colors=[(90, 140, 255), (160, 195, 255)])
                self.hit_sound.play()

        # ── Alien bullets → fighter ────────────────────────────────────
        for ab in list(self.alien_bullets):
            if ab.rect.colliderect(self.fighter.rect):
                ab.kill()
                self._take_damage()
                if self.state == GameState.GAME_OVER:
                    return

        # ── Aliens reaching / passing fighter ─────────────────────────
        for alien in list(self.aliens):
            if alien.has_reached_fighter(self.fighter) or alien.is_off_screen():
                alien.kill()
                self._take_damage()
                if self.state == GameState.GAME_OVER:
                    return

        # ── Wave complete (non-boss waves only) ────────────────────────
        if self.boss is None and len(self.aliens) == 0:
            self._start_wave(self.wave + 1)

    def _update_boss(self, dt: float):
        """Handle boss movement, shooting, and collision with player bullets."""
        if not self.boss:
            return

        self.boss.update(dt)   # boss is immune to slow-time

        # Boss fires
        for shot in self.boss.drain_shots():
            self.alien_bullets.add(AlienBullet(*shot))

        # Player bullets → boss
        for ball in list(self.balls):
            if ball.rect.colliderect(self.boss.rect):
                ball.kill()
                self._ball_queue_remove(ball)
                if self.boss.take_hit():
                    # Boss defeated — big explosion burst
                    cx, cy = self.boss.rect.center
                    for _ in range(7):
                        ox = random.randint(-55, 55)
                        oy = random.randint(-55, 55)
                        self.explosions.add(Explosion(cx + ox, cy + oy))
                    self._spawn_particles(cx, cy, count=40,
                                         colors=[(255, 100, 255), (200, 50, 255),
                                                 (255, 215,   0), (255,  80,  80)])
                    self.game_score += self.boss.SCORE
                    if self.game_score > self.best_score:
                        self.best_score = self.game_score
                        ScoreManager.save(self.best_score)
                    self.hit_sound.play()
                    self.boss = None
                    self._start_wave(self.wave + 1)
                    return   # start fresh next frame
                else:
                    self.hit_sound.play()

        # Boss body collides with fighter
        if self.boss and self.boss.rect.colliderect(self.fighter.rect):
            self._take_damage()

    def _maybe_drop_powerup(self, cx: int, cy: int):
        """25 % chance to drop a random power-up when an alien dies."""
        if random.random() > 0.25:
            return
        roll = random.random()
        if   roll < 0.40:  pu = TripleShotPowerUp(cx, cy)
        elif roll < 0.72:  pu = SlowTimePowerUp(cx, cy)
        else:              pu = ShieldPowerUp(cx, cy)
        self.powerups.add(pu)

    def _apply_powerup(self, pu):
        """Activate the collected power-up effect."""
        if isinstance(pu, TripleShotPowerUp):
            self._triple_shot_timer = TripleShotPowerUp.DURATION
        elif isinstance(pu, ShieldPowerUp):
            self._shield_active = True
        elif isinstance(pu, SlowTimePowerUp):
            self._slow_time_timer = SlowTimePowerUp.DURATION
        self.powerup_sound.play()

    def _take_damage(self):
        """Subtract one life (or absorb with shield); trigger visual feedback; check game-over."""
        if self._shield_active:
            # Shield absorbs the hit
            self._shield_active = False
            self.flash_timer   = 6
            self._shake_timer  = 2
            return
        self.lives       -= 1
        self.flash_timer  = 20
        self._shake_timer = 5
        self.lose_life_sound.play()
        if self.lives <= 0:
            self.state = GameState.GAME_OVER
            # Persist the completed run to the leaderboard (once per session)
            self.score_entries = ScoreManager.add_entry(
                self.game_score, self.wave, self._selected_ship.name
            )
            self.best_score = max(self.best_score, self.game_score)

    def _spawn_particles(self, cx: int, cy: int, count: int = 12, colors=None):
        """Emit *count* debris particles from (cx, cy)."""
        if colors is None:
            colors = [(255, 220, 0), (255, 140, 0), (255, 70, 0), (255, 255, 100)]
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(60, 190)
            life  = random.uniform(0.35, 0.65)
            self._particles.append({
                'x': float(cx), 'y': float(cy),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': life, 'max_life': life,
                'color': random.choice(colors),
                'size': random.randint(2, 5),
            })

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw(self):
        """Draw all game objects and effects onto the canvas, then blit to screen with shake."""
        cv = self._canvas

        cv.blit(self.background, (0, 0))

        # Boss
        if self.boss:
            cv.blit(self.boss.image, self.boss.rect)

        cv.blit(self.fighter.image, self.fighter.rect)
        self.aliens.draw(cv)
        self.balls.draw(cv)
        self.alien_bullets.draw(cv)
        self.powerups.draw(cv)
        self.explosions.draw(cv)
        self._draw_particles(cv)

        # Shield ring around fighter
        if self._shield_active:
            scx, scy = self.fighter.rect.center
            r = max(self.fighter.width, self.fighter.height) // 2 + 11
            pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() / 180.0)
            a     = int(140 * pulse)
            _sh = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(_sh, (70, 150, 255, a), (r + 2, r + 2), r, 3)
            cv.blit(_sh, (scx - r - 2, scy - r - 2))

        # Slow-time blue tint overlay
        if self._slow_time_timer > 0:
            _st = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            _st.fill((25, 45, 180, 22))
            cv.blit(_st, (0, 0))

        # Wave announcement banner (fades out in last 0.5 s)
        if self._wave_banner_timer > 0:
            alpha = 255
            if self._wave_banner_timer < 0.5:
                alpha = int(255 * self._wave_banner_timer / 0.5)
            is_boss = (self.wave % 5 == 0)
            banner_txt   = f"BOSS WAVE  {self.wave}!" if is_boss else f"WAVE  {self.wave}"
            banner_color = (255, 55, 55)  if is_boss else (255, 215, 50)
            sub_txt      = "Defeat the boss!"        if is_boss else "New aliens incoming!"
            banner = self.wave_font.render(banner_txt, True, banner_color)
            banner.set_alpha(alpha)
            sub = self.game_font.render(sub_txt, True, (200, 200, 200))
            sub.set_alpha(alpha)
            bx = config.SCREEN_WIDTH  // 2 - banner.get_width() // 2
            by = config.SCREEN_HEIGHT // 3 - banner.get_height() // 2
            cv.blit(banner, (bx, by))
            cv.blit(sub, sub.get_rect(centerx=config.SCREEN_WIDTH // 2,
                                      top=by + banner.get_height() + 4))

        # Red tint flash when a life is lost — SRCALPHA ensures proper per-pixel blending
        if self.flash_timer > 0:
            alpha = int(self.flash_timer * 4.5)   # max ~90 at timer=20 — subtle tint only
            flash_surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((255, 0, 0, alpha))
            cv.blit(flash_surface, (0, 0))
            self.flash_timer -= 1

        self._draw_hud(cv)

        # Camera shake — pick a random offset while timer is active.
        # The offset is stored and applied by run() when blitting to the display.
        if self._shake_timer > 0:
            self._shake_ox = random.randint(-8, 8)
            self._shake_oy = random.randint(-5, 5)
            self._shake_timer -= 1
        else:
            self._shake_ox = 0
            self._shake_oy = 0

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
        """Draw HUD: score, wave, lives, dash bar, boss HP bar, power-up timers."""
        self._draw_boss_hp_bar(surface)
        self._draw_powerup_hud(surface)

        score_text = self.game_font.render(
            f"Score: {self.game_score}   Best: {self.best_score}"
            f"   Wave: {self.wave}   Lives:",
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

    def _draw_boss_hp_bar(self, surface: pygame.Surface):
        """Draw the boss HP bar at the bottom of the screen (only during boss fights)."""
        if not self.boss:
            return
        ratio  = self.boss.hp_ratio
        bar_w  = min(520, config.SCREEN_WIDTH - 80)
        bar_h  = 22
        bx     = config.SCREEN_WIDTH  // 2 - bar_w // 2
        by     = config.SCREEN_HEIGHT - 44

        # Background track
        pygame.draw.rect(surface, (30, 8, 45),  (bx - 2, by - 2, bar_w + 4, bar_h + 4), border_radius=5)
        pygame.draw.rect(surface, (55, 18, 75), (bx, by, bar_w, bar_h), border_radius=4)

        # HP fill — colour shifts green → yellow → red as HP drops
        if ratio > 0:
            fill_w = max(1, int(bar_w * ratio))
            if   ratio > 0.66: color = (50, 200, 55)
            elif ratio > 0.33: color = (225, 175, 0)
            else:              color = (215, 38, 38)
            pygame.draw.rect(surface, color, (bx, by, fill_w, bar_h), border_radius=4)

        # Glowing border
        pygame.draw.rect(surface, (175, 28, 215), (bx, by, bar_w, bar_h), 2, border_radius=4)

        # Label above bar
        lbl = self.game_font.render(
            f"BOSS  HP: {self.boss.hp} / {self.boss.max_hp}", True, (215, 175, 255))
        surface.blit(lbl, lbl.get_rect(
            centerx=config.SCREEN_WIDTH // 2, bottom=by - 5))

    def _draw_powerup_hud(self, surface: pygame.Surface):
        """Draw active power-up timers at the top-right of the screen."""
        lines = []
        if self._triple_shot_timer > 0:
            lines.append((f"3x SHOT  {self._triple_shot_timer:.1f}s", (255, 210, 0)))
        if self._shield_active:
            lines.append(("SHIELD  ACTIVE", (70, 150, 255)))
        if self._slow_time_timer > 0:
            lines.append((f"SLOW TIME  {self._slow_time_timer:.1f}s", (165, 75, 255)))

        x = config.SCREEN_WIDTH - 18
        y = 20
        for text, color in lines:
            surf = self.game_font.render(text, True, color)
            surface.blit(surf, (x - surf.get_width(), y))
            y += surf.get_height() + 4

    def _draw_ship_select_screen(self):
        """Three side-by-side ship cards; click once to highlight, again (or SPACE) to confirm."""
        screen = self._canvas   # draw to logical canvas
        sw = config.SCREEN_WIDTH

        # ── Title ────────────────────────────────────────────────────────
        title = self.med_font.render("SELECT YOUR SHIP", True, (210, 210, 255))
        screen.blit(title, title.get_rect(centerx=sw // 2, top=22))

        hint = self.small_font.render(
            "← → to browse   •   click to select   •   SPACE / second click to confirm   •   ESC to go back",
            True, (90, 90, 110))
        screen.blit(hint, hint.get_rect(centerx=sw // 2, top=70))

        # ── Cards ─────────────────────────────────────────────────────────
        rects   = self._ship_card_rects()
        mouse   = self._lmouse()
        CARD_W  = rects[0].w
        CARD_H  = rects[0].h

        for i, (ship, rect) in enumerate(zip(SHIPS, rects)):
            is_sel  = (i == self._ship_cursor)
            is_hover = rect.collidepoint(mouse) and not is_sel

            # Card background
            bg_alpha = 230 if is_sel else (180 if is_hover else 160)
            card_surf = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
            card_surf.fill((15, 15, 35, bg_alpha))
            screen.blit(card_surf, rect.topleft)

            # Border
            border_col = ship.color if is_sel else (70, 70, 90)
            border_w   = 3 if is_sel else 1
            pygame.draw.rect(screen, border_col, rect, border_w, border_radius=10)

            # Subtle inner glow on selected card
            if is_sel:
                glow = pygame.Surface((CARD_W - 6, CARD_H - 6), pygame.SRCALPHA)
                glow.fill((*ship.color, 18))
                screen.blit(glow, (rect.x + 3, rect.y + 3))

            cx = rect.centerx

            # Ship name
            name_col  = ship.color if is_sel else (160, 160, 185)
            name_surf = self.med_font.render(ship.name.upper(), True, name_col)
            screen.blit(name_surf, name_surf.get_rect(centerx=cx, top=rect.y + 14))

            # Tagline
            tag_surf = self.small_font.render(ship.tagline, True, (120, 120, 140))
            screen.blit(tag_surf, tag_surf.get_rect(centerx=cx, top=rect.y + 62))

            # Divider
            pygame.draw.line(screen, (50, 50, 75),
                             (rect.x + 16, rect.y + 86), (rect.right - 16, rect.y + 86))

            # Fighter preview (tinted)
            prev = self._ship_previews[i]
            pw, ph = prev.get_size()
            screen.blit(prev, (cx - pw // 2, rect.y + 96))

            # Stat bars
            BAR_W, BAR_H = 148, 9
            bar_x = rect.x + 56
            stat_y = rect.y + 196
            for label, val in (("SPD", ship.stat_speed),
                               ("GUN", ship.stat_fire),
                               ("DSH", ship.stat_dash)):
                lbl = self.small_font.render(label, True, (130, 130, 155))
                screen.blit(lbl, (rect.x + 14, stat_y - 1))
                pygame.draw.rect(screen, (35, 35, 55),
                                 (bar_x, stat_y + 1, BAR_W, BAR_H), border_radius=3)
                fill_w = int(BAR_W * val / 10)
                if fill_w > 0:
                    col = ship.color if is_sel else (90, 90, 115)
                    pygame.draw.rect(screen, col,
                                     (bar_x, stat_y + 1, fill_w, BAR_H), border_radius=3)
                stat_y += 28

            # "SELECTED" badge at bottom of highlighted card
            if is_sel:
                badge_rect = pygame.Rect(rect.x + 20, rect.bottom - 44, CARD_W - 40, 30)
                badge_surf = pygame.Surface((badge_rect.w, badge_rect.h), pygame.SRCALPHA)
                badge_surf.fill((*ship.color, 200))
                screen.blit(badge_surf, badge_rect.topleft)
                pygame.draw.rect(screen, (255, 255, 255), badge_rect, 1, border_radius=4)
                badge_txt = self.small_font.render("SELECTED  —  SPACE TO START", True, (10, 10, 20))
                screen.blit(badge_txt, badge_txt.get_rect(center=badge_rect.center))

    def _draw_start_screen(self):
        """Main menu: game title, top-5 leaderboard, and action buttons."""
        screen = self._canvas   # draw to logical canvas
        cx = self.screen_width  // 2
        cy = self.screen_height // 2
        mouse = self._lmouse()

        # ── Title ─────────────────────────────────────────────────────────
        title = self.wave_font.render("SERPENTIS", True, (180, 120, 255))
        screen.blit(title, title.get_rect(centerx=cx, top=36))

        sub = self.small_font.render("A Python space shooter", True, (90, 90, 110))
        screen.blit(sub, sub.get_rect(centerx=cx, top=106))

        # ── Top-5 leaderboard panel ───────────────────────────────────────
        TABLE_W, TABLE_H = 580, 220
        table_x = cx - TABLE_W // 2
        table_y = 138

        panel = pygame.Surface((TABLE_W, TABLE_H), pygame.SRCALPHA)
        panel.fill((14, 14, 30, 210))
        screen.blit(panel, (table_x, table_y))
        pygame.draw.rect(screen, (55, 55, 85),
                         pygame.Rect(table_x, table_y, TABLE_W, TABLE_H), 1, border_radius=8)

        hdr = self.small_font.render("HIGH  SCORES", True, (160, 130, 255))
        screen.blit(hdr, hdr.get_rect(centerx=cx, top=table_y + 10))
        pygame.draw.line(screen, (50, 50, 80),
                         (table_x + 16, table_y + 32), (table_x + TABLE_W - 16, table_y + 32))

        if self.score_entries:
            row_y  = table_y + 40
            for idx, entry in enumerate(self.score_entries[:5]):
                rank_col = [(255, 215, 0), (192, 192, 192), (205, 127, 50),
                            (160, 160, 180), (140, 140, 160)][idx]
                rank_t = self.small_font.render(f"#{idx+1}", True, rank_col)
                screen.blit(rank_t, (table_x + 18, row_y))

                score_t = self.small_font.render(f"{entry['score']:>6}", True, (220, 220, 240))
                screen.blit(score_t, (table_x + 60, row_y))

                wave_t = self.small_font.render(f"W.{entry['wave']:>2}", True, (160, 200, 160))
                screen.blit(wave_t, (table_x + 148, row_y))

                ship_col = next((s.color for s in SHIPS if s.name == entry.get('ship')),
                                (160, 160, 180))
                ship_t = self.small_font.render(f"{entry.get('ship', '?'):<8}", True, ship_col)
                screen.blit(ship_t, (table_x + 218, row_y))

                date_t = self.small_font.render(entry.get('date', ''), True, (90, 90, 110))
                screen.blit(date_t, (table_x + 370, row_y))
                row_y += 30
        else:
            empty = self.small_font.render("No records yet — be the first!", True, (70, 70, 90))
            screen.blit(empty, empty.get_rect(centerx=cx, top=table_y + 80))

        # ── Buttons ───────────────────────────────────────────────────────
        def _btn(rect, label, base_col, hover_col):
            col = hover_col if rect.collidepoint(mouse) else base_col
            pygame.draw.rect(screen, col, rect, border_radius=8)
            t = self.game_font.render(label, True, 'white')
            screen.blit(t, t.get_rect(center=rect.center))

        _btn(self._play_btn_rect,     "▶  PLAY",   (35, 120, 50),  (50, 170, 70))
        _btn(self._settings_btn_rect, "Settings",  (55, 55, 80),   (80, 80, 115))
        _btn(self._quit_start_rect,   "Quit",      (100, 30, 30),  (150, 45, 45))

        hint = self.small_font.render("SPACE to play", True, (65, 65, 80))
        screen.blit(hint, hint.get_rect(centerx=cx, bottom=self.screen_height - 10))

    def _draw_pause_overlay(self):
        """Draw a full pause menu panel over the frozen game screen."""
        screen = self._canvas   # draw to logical canvas
        s   = Settings.get()
        lay = self._pause_layout()
        cx  = self.screen_width // 2

        # ── Dark background dimmer ────────────────────────────────────
        dimmer = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 155))
        screen.blit(dimmer, (0, 0))

        # ── Panel background ──────────────────────────────────────────
        panel = lay['panel']
        panel_surf = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        panel_surf.fill((18, 18, 32, 235))
        screen.blit(panel_surf, (panel.x, panel.y))
        pygame.draw.rect(screen, (65, 65, 100), panel, 2, border_radius=12)

        # ── Title ─────────────────────────────────────────────────────
        title = self.game_font.render("PAUSED", True, (220, 220, 255))
        screen.blit(title, title.get_rect(center=(cx, panel.y + 42)))

        # ── Divider ───────────────────────────────────────────────────
        pygame.draw.line(screen, (55, 55, 85),
                         (panel.x + 20, panel.y + 66),
                         (panel.right - 20, panel.y + 66))

        # ── Volume label ──────────────────────────────────────────────
        vol_label = self.game_font.render("VOLUME", True, (150, 150, 175))
        screen.blit(vol_label, (lay['slider_x'], lay['slider_y'] - 26))

        # ── Volume slider ─────────────────────────────────────────────
        sx, sy, sw, sh = lay['slider_x'], lay['slider_y'], lay['slider_w'], lay['slider_h']
        pygame.draw.rect(screen, (55, 55, 70), (sx, sy, sw, sh), border_radius=6)
        fill_w = int(sw * s.volume)
        if fill_w > 0:
            pygame.draw.rect(screen, (0, 190, 255), (sx, sy, fill_w, sh), border_radius=6)
        knob_x = sx + fill_w
        pygame.draw.circle(screen, (210, 210, 210), (knob_x, sy + sh // 2), 9)
        pct = self.game_font.render(f"{int(s.volume * 100)}%", True, 'white')
        screen.blit(pct, (sx + sw + 14, sy - 4))

        # ── Buttons ───────────────────────────────────────────────────
        mouse_pos = self._lmouse()
        btns = [
            (lay['resume_rect'],  "RESUME",     (35, 130, 55),  (55, 180, 75)),
            (lay['restart_rect'], "RESTART",    (40,  55, 130), (60,  85, 180)),
            (lay['menu_rect'],    "MAIN MENU",  (60,  60,  80), (90,  90, 120)),
        ]
        for rect, label, color, hover_color in btns:
            c = hover_color if rect.collidepoint(mouse_pos) else color
            pygame.draw.rect(screen, c, rect, border_radius=8)
            pygame.draw.rect(screen, (90, 90, 130), rect, 1, border_radius=8)
            t = self.game_font.render(label, True, 'white')
            screen.blit(t, t.get_rect(center=rect.center))

        # Thin divider before destructive QUIT button
        sep_y = lay['quit_rect'].y - 12
        pygame.draw.line(screen, (55, 55, 85),
                         (panel.x + 30, sep_y), (panel.right - 30, sep_y))
        q_rect = lay['quit_rect']
        q_color = (185, 45, 45) if q_rect.collidepoint(mouse_pos) else (130, 35, 35)
        pygame.draw.rect(screen, q_color, q_rect, border_radius=8)
        pygame.draw.rect(screen, (200, 60, 60), q_rect, 1, border_radius=8)
        qt = self.game_font.render("QUIT", True, 'white')
        screen.blit(qt, qt.get_rect(center=q_rect.center))

        # ── ESC hint ──────────────────────────────────────────────────
        hint = self.game_font.render("ESC  /  P  to resume", True, (80, 80, 105))
        screen.blit(hint, hint.get_rect(center=(cx, panel.bottom + 20)))

    def _draw_game_over_screen(self):
        """Game-over screen: run summary + top-5 leaderboard + action buttons."""
        screen = self._canvas   # draw to logical canvas
        cx    = self.screen_width  // 2
        cy    = self.screen_height // 2
        mouse = self._lmouse()

        # ── Run summary ───────────────────────────────────────────────────
        go_surf = self.wave_font.render("GAME  OVER", True, (255, 80, 80))
        screen.blit(go_surf, go_surf.get_rect(centerx=cx, top=28))

        details = (f"Score: {self.game_score}    Wave: {self.wave}"
                   f"    Ship: {self._selected_ship.name}")
        det_surf = self.game_font.render(details, True, (210, 210, 230))
        screen.blit(det_surf, det_surf.get_rect(centerx=cx, top=106))

        # New-best badge
        if self.score_entries and self.score_entries[0]['score'] == self.game_score:
            badge = self.game_font.render("★  NEW  BEST!", True, (255, 215, 0))
            screen.blit(badge, badge.get_rect(centerx=cx, top=140))

        # ── Leaderboard panel ─────────────────────────────────────────────
        TABLE_W, TABLE_H = 580, 198
        table_x = cx - TABLE_W // 2
        table_y = 172

        panel = pygame.Surface((TABLE_W, TABLE_H), pygame.SRCALPHA)
        panel.fill((14, 14, 30, 215))
        screen.blit(panel, (table_x, table_y))
        pygame.draw.rect(screen, (60, 60, 90),
                         pygame.Rect(table_x, table_y, TABLE_W, TABLE_H), 1, border_radius=8)

        hdr = self.small_font.render("TOP  SCORES", True, (160, 130, 255))
        screen.blit(hdr, hdr.get_rect(centerx=cx, top=table_y + 8))
        pygame.draw.line(screen, (50, 50, 80),
                         (table_x + 16, table_y + 30), (table_x + TABLE_W - 16, table_y + 30))

        row_y = table_y + 38
        for idx, entry in enumerate(self.score_entries[:5]):
            # Highlight the current run
            is_this = (entry['score'] == self.game_score and
                       entry.get('ship') == self._selected_ship.name)
            rank_col = [(255, 215, 0), (192, 192, 192), (205, 127, 50),
                        (160, 160, 180), (140, 140, 160)][idx]
            txt_col  = (255, 255, 200) if is_this else (200, 200, 220)

            screen.blit(
                self.small_font.render(f"#{idx+1}", True, rank_col),
                (table_x + 16, row_y))
            screen.blit(
                self.small_font.render(f"{entry['score']:>6}", True, txt_col),
                (table_x + 58, row_y))
            screen.blit(
                self.small_font.render(f"W.{entry['wave']:>2}", True, (160, 200, 160)),
                (table_x + 148, row_y))
            ship_col = next((s.color for s in SHIPS if s.name == entry.get('ship')),
                            (160, 160, 180))
            screen.blit(
                self.small_font.render(f"{entry.get('ship','?'):<8}", True, ship_col),
                (table_x + 218, row_y))
            screen.blit(
                self.small_font.render(entry.get('date', ''), True, (85, 85, 105)),
                (table_x + 368, row_y))
            row_y += 29

        # ── Buttons ───────────────────────────────────────────────────────
        ta_col  = (50, 170, 70)  if self.try_again_rect.collidepoint(mouse) else (35, 120, 50)
        men_col = (80, 80, 115)  if self.menu_go_rect.collidepoint(mouse)   else (55, 55, 80)

        pygame.draw.rect(screen, ta_col,  self.try_again_rect, border_radius=8)
        pygame.draw.rect(screen, men_col, self.menu_go_rect,   border_radius=8)

        screen.blit(
            self.game_font.render("Try Again", True, 'white'),
            self.game_font.render("Try Again", True, 'white').get_rect(center=self.try_again_rect.center))
        screen.blit(
            self.game_font.render("Menu", True, 'white'),
            self.game_font.render("Menu", True, 'white').get_rect(center=self.menu_go_rect.center))

    def _draw_settings_screen(self):
        """Draw the settings screen with volume slider, resolution and difficulty selectors."""
        screen = self._canvas   # draw to logical canvas
        s   = Settings.get()
        lay = self._settings_layout()
        cx  = self.screen_width // 2

        # ── Title ──────────────────────────────────────────────────────
        title = self.game_font.render("SETTINGS", True, 'white')
        screen.blit(title, title.get_rect(center=(cx, 110)))

        # ── Volume ────────────────────────────────────────────────────
        screen.blit(
            self.game_font.render("VOLUME", True, (160, 160, 160)),
            (lay['slider_x'], lay['slider_y'] - 30)
        )
        sx, sy, sw, sh = lay['slider_x'], lay['slider_y'], lay['slider_w'], lay['slider_h']
        pygame.draw.rect(screen, (55, 55, 65), (sx, sy, sw, sh), border_radius=6)
        fill_w = int(sw * s.volume)
        if fill_w > 0:
            pygame.draw.rect(screen, (0, 200, 255), (sx, sy, fill_w, sh), border_radius=6)
        # Knob
        knob_x = sx + fill_w
        pygame.draw.circle(screen, (220, 220, 220), (knob_x, sy + sh // 2), 9)
        pct = self.game_font.render(f"{int(s.volume * 100)}%", True, 'white')
        screen.blit(pct, (sx + sw + 14, sy - 4))

        # ── Resolution ────────────────────────────────────────────────
        screen.blit(
            self.game_font.render("RESOLUTION", True, (160, 160, 160)),
            (lay['res_rects'][0].x, lay['res_rects'][0].y - 28)
        )
        res_labels = ["1024×768", "1280×720", "1920×1080", "2560×1440"]
        for i, (rect, lbl) in enumerate(zip(lay['res_rects'], res_labels)):
            color = (0, 150, 210) if i == s.resolution_index else (50, 50, 68)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            if i == s.resolution_index:
                pygame.draw.rect(screen, (0, 210, 255), rect, 2, border_radius=8)
            t = self.game_font.render(lbl, True, 'white')
            screen.blit(t, t.get_rect(center=rect.center))

        # ── Difficulty ────────────────────────────────────────────────
        screen.blit(
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
            pygame.draw.rect(screen, color, rect, border_radius=8)
            if dkey == s.difficulty:
                pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=8)
            t = self.game_font.render(dlbl, True, 'white')
            screen.blit(t, t.get_rect(center=rect.center))

        # ── Fullscreen toggle ─────────────────────────────────────────
        fs    = s.fullscreen
        fs_rect  = lay['fullscreen_rect']
        fs_color = (0, 145, 195) if fs else (50, 50, 68)
        fs_border = (0, 210, 255) if fs else (70, 70, 95)
        pygame.draw.rect(screen, fs_color,  fs_rect, border_radius=8)
        pygame.draw.rect(screen, fs_border, fs_rect, 2, border_radius=8)
        fs_label = "FULLSCREEN:  ON" if fs else "FULLSCREEN:  OFF"
        fs_t = self.game_font.render(fs_label, True, 'white')
        screen.blit(fs_t, fs_t.get_rect(center=fs_rect.center))

        # ── Back ──────────────────────────────────────────────────────
        pygame.draw.rect(screen, (65, 65, 85), lay['back_rect'], border_radius=8)
        back_t = self.game_font.render("BACK", True, 'white')
        screen.blit(back_t, back_t.get_rect(center=lay['back_rect'].center))

        hint = self.game_font.render("ESC to go back  •  F11 to toggle fullscreen",
                                     True, (90, 90, 100))
        screen.blit(hint, hint.get_rect(center=(cx, lay['back_rect'].bottom + 22)))
