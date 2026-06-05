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
from boss import Boss, MiniBoss
from powerup import TripleShotPowerUp, ShieldPowerUp, SlowTimePowerUp, HeartPowerUp
from config import GAME_CAPTION, STARTING_LIVES
from assets import Assets
from score_manager import ScoreManager
from settings_manager import Settings
from explosion import Explosion
from ship import ShipConfig, SHIPS
from ship_sprites import build_ship
from background import StarBackground
from ui_fx import draw_glass_panel, render_shadowed, render_outlined, draw_glow_circle
from music import MusicPlayer

from screens.start      import StartScreen
from screens.ship_select import ShipSelectScreen
from screens.game_over  import GameOverScreen
from screens.settings   import SettingsScreen
from screens.pause      import PauseOverlay


class GameState(Enum):
    LOADING     = "loading"
    START       = "start"
    SHIP_SELECT = "ship_select"
    PLAYING     = "playing"
    PAUSED      = "paused"
    DYING       = "dying"     # death animation before game over
    GAME_OVER   = "game_over"
    SETTINGS    = "settings"


# Fixed logical game-world resolution — all sprites and physics live in this space.
# The canvas is scaled up to the real display size so higher resolutions look crisp.
_LOGICAL_W, _LOGICAL_H = 1280, 720


class Game:
    def __init__(self):
        pygame.display.set_caption(GAME_CAPTION)

        s = Settings.get()
        self.screen_width  = _LOGICAL_W
        self.screen_height = _LOGICAL_H
        config.SCREEN_WIDTH  = _LOGICAL_W
        config.SCREEN_HEIGHT = _LOGICAL_H

        # Physical display size (chosen by user in Settings)
        self._disp_w, self._disp_h = s.resolution
        # Scale factors: transform display-space mouse coords → logical (1280×720) coords
        self._mouse_sx = _LOGICAL_W / self._disp_w
        self._mouse_sy = _LOGICAL_H / self._disp_h
        # Camera-shake offset — set by _draw(), consumed by run()
        self._shake_ox = self._shake_oy = 0

        # pygame.SCALED prevents the OS compositor from applying blurry bilinear filtering
        # (critical on macOS Retina / HiDPI displays).
        _flags = (pygame.FULLSCREEN | pygame.SCALED) if s.fullscreen else pygame.SCALED
        self.screen = pygame.display.set_mode((self._disp_w, self._disp_h), _flags)

        # ── Fonts ──────────────────────────────────────────────────────────
        fonts = {
            'game':  pygame.font.Font(None, 36),
            'med':   pygame.font.Font(None, 52),
            'small': pygame.font.Font(None, 26),
            'wave':  pygame.font.Font(None, 86),
        }
        self.game_font  = fonts['game']
        self.med_font   = fonts['med']
        self.small_font = fonts['small']
        self.wave_font  = fonts['wave']
        self.clock = pygame.time.Clock()

        # ── Sounds ────────────────────────────────────────────────────────
        # Shoot: laser chirp (900 Hz → 120 Hz, 0.13 s)
        self.shoot_sound     = Assets.make_chirp('shoot',    900, 120, 0.13, 0.45)
        # Dash: whoosh (350 Hz → 60 Hz, 0.20 s) — on dedicated channel to avoid cutoff
        self._dash_snd_raw   = Assets.make_chirp('dash',     350,  60, 0.20, 0.55)
        self._dash_channel   = pygame.mixer.Channel(0)   # reserved — never stolen
        # Hit / lose-life / powerup: keep as sine tones
        self.hit_sound       = Assets.make_chirp('hit',       180,  40, 0.12, 0.50)
        self.lose_life_sound = Assets.get_sound('lose_life', frequency=110, duration=0.5)
        self.powerup_sound   = Assets.get_sound('powerup',   frequency=740, duration=0.22)
        # UI sounds
        self.ui_click_sound  = Assets.make_chirp('ui_click', 700, 500, 0.06, 0.30)
        self.ui_nav_sound    = Assets.make_chirp('ui_nav',   900, 700, 0.04, 0.22)
        self._apply_volume()

        # ── Music ─────────────────────────────────────────────────────────
        self._music = MusicPlayer()
        self._music.set_volume(Settings.get().volume * 0.5)
        self._music.play_menu()

        # ── Assets ────────────────────────────────────────────────────────
        self.background = StarBackground(_LOGICAL_W, _LOGICAL_H)

        raw_heart = Assets.get_image('image/heart.png')
        self.heart_icon = pygame.transform.smoothscale(raw_heart, (22, 22))

        # Procedural ship preview sprites for the ship-select cards
        _prev_h = 80
        self._ship_previews: list[pygame.Surface] = []
        for _ship in SHIPS:
            raw = build_ship(_ship.id)
            rw, rh = raw.get_size()
            _prev_w = int(rw * (_prev_h / rh))
            self._ship_previews.append(
                pygame.transform.smoothscale(raw, (_prev_w, _prev_h))
            )

        # ── Persistent state ──────────────────────────────────────────────
        self.best_score, self.score_entries = ScoreManager.load()
        self._selected_ship: ShipConfig = SHIPS[0]
        self._ship_cursor: int = 0

        # ── Screen objects ────────────────────────────────────────────────
        self._start_screen  = StartScreen(fonts)
        self._ship_screen   = ShipSelectScreen(fonts, self._ship_previews)
        self._gameover      = GameOverScreen(fonts)
        self._settings      = SettingsScreen(fonts)
        self._pause         = PauseOverlay(fonts)
        self._update_screen_layouts()

        # ── Canvas & particles ────────────────────────────────────────────
        self._canvas      = pygame.Surface((_LOGICAL_W, _LOGICAL_H))
        self._shake_timer = 0
        self._particles: list[dict] = []

        # Fade transition system
        self._fade_alpha      = 255       # start fully black, fade in on launch
        self._fade_dir        = -1        # -1 = fade in, +1 = fade out
        self._fade_speed      = 420.0     # alpha units per second
        self._fade_next_state: GameState | None = None

        self.state = GameState.LOADING
        self._loading_timer = 2.5   # seconds to show splash
        self._init_game()

    # ------------------------------------------------------------------
    # Layout & display helpers
    # ------------------------------------------------------------------

    def _update_screen_layouts(self):
        """Notify all screens of the current logical dimensions."""
        sw, sh = self.screen_width, self.screen_height
        self._start_screen.update_layout(sw, sh)
        self._gameover.update_layout(sw, sh)

    def _apply_volume(self):
        vol = Settings.get().volume
        for snd in (self.shoot_sound, self.hit_sound,
                    self.lose_life_sound, self.powerup_sound,
                    self.ui_click_sound, self.ui_nav_sound):
            snd.set_volume(vol)
        if hasattr(self, '_dash_channel'):
            self._dash_channel.set_volume(vol * 0.55)
        if hasattr(self, '_music'):
            self._music.set_volume(vol * 0.5)

    def _apply_resolution(self):
        """Recreate the display at the resolution stored in Settings."""
        s = Settings.get()
        self._disp_w, self._disp_h = s.resolution
        self._mouse_sx = _LOGICAL_W / self._disp_w
        self._mouse_sy = _LOGICAL_H / self._disp_h
        flags = (pygame.FULLSCREEN | pygame.SCALED) if s.fullscreen else pygame.SCALED
        self.screen = pygame.display.set_mode((self._disp_w, self._disp_h), flags)
        self._update_screen_layouts()

    def _toggle_fullscreen(self):
        s = Settings.get()
        s.fullscreen = not s.fullscreen
        s.save()
        self._apply_resolution()

    def _fade_to(self, next_state: GameState):
        """Start a fade-out → switch state → fade-in transition."""
        if self._fade_next_state is not None:
            return   # already fading
        self._fade_next_state = next_state
        self._fade_dir   = 1    # fade out first

    # ------------------------------------------------------------------
    # Coordinate helpers (display-space → logical 1280×720)
    # ------------------------------------------------------------------

    def _lpos(self, pos: tuple[int, int]) -> tuple[int, int]:
        return (int(pos[0] * self._mouse_sx), int(pos[1] * self._mouse_sy))

    def _lmouse(self) -> tuple[int, int]:
        return self._lpos(pygame.mouse.get_pos())

    # ------------------------------------------------------------------
    # Game initialisation
    # ------------------------------------------------------------------

    def _init_game(self):
        """Reset all gameplay state for a new round."""
        self.game_score         = 0
        self.lives              = Settings.get().starting_lives
        self.flash_timer        = 0
        self.wave               = 0
        self.fighter            = Fighter(ship=self._selected_ship)
        self.balls              = pygame.sprite.Group()
        self._ball_queue        = []
        self.explosions         = pygame.sprite.Group()
        self.alien_bullets      = pygame.sprite.Group()
        self.powerups           = pygame.sprite.Group()
        self.boss               = None
        self.mini_boss          = None
        self._boss_warning_timer  = 0.0   # countdown before boss spawns
        self._pending_boss_wave   = 0     # wave number waiting for warning to end
        self._particles         = []
        self._engine_particles: list[dict] = []
        self._shake_timer       = 0
        self._wave_banner_timer = 0.0
        self._triple_shot_timer = 0.0
        self._shield_active     = False
        self._slow_time_timer   = 0.0
        self._death_timer       = 0.0   # countdown for DYING state
        self._start_wave(1)

    def _start_wave(self, wave_num: int, extra_delay: float = 0.0):
        self.wave               = wave_num
        self.alien_bullets      = pygame.sprite.Group()
        self.powerups           = pygame.sprite.Group()
        self._wave_banner_timer = 2.8 + extra_delay
        self.mini_boss          = None

        if wave_num % 5 == 0:
            # Full boss — show warning first, spawn after delay
            self.boss  = None
            self.aliens = pygame.sprite.Group()
            self._boss_warning_timer = 2.8
            self._pending_boss_wave  = wave_num
        elif wave_num % 5 == 3 and wave_num >= 3:
            # Mini-boss wave
            self.boss      = None
            self.mini_boss = MiniBoss(wave_num)
            self.aliens    = pygame.sprite.Group()
            self._boss_warning_timer = 1.8
            self._pending_boss_wave  = -wave_num   # negative = mini-boss signal
        else:
            self.boss   = None
            self.aliens = pygame.sprite.Group(*self._make_wave_aliens(wave_num))

    def _make_wave_aliens(self, wave_num: int) -> list:
        s     = Settings.get()
        count = s.alien_count + (wave_num - 1)
        speed = s.alien_speed_mult * (1.0 + (wave_num - 1) * 0.15)
        speed = min(speed, s.alien_speed_mult * 4.0)
        aliens = []
        for i in range(count):
            roll = random.random()
            if   wave_num >= 4 and roll < 0.15: cls = ShooterAlien
            elif wave_num >= 3 and roll < 0.30: cls = ZigzagAlien
            elif wave_num >= 2 and roll < 0.30: cls = ArmoredAlien
            else:                               cls = Alien
            aliens.append(cls(index=i, speed_mult=speed))
        return aliens

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        while True:
            dt = self.clock.tick(Settings.get().fps) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._handle_event(event)

            # Menu screens get a fresh background each frame;
            # gameplay states manage their own canvas via _draw().
            self.background.update(dt)
            if self.state not in (GameState.PLAYING, GameState.PAUSED):
                self.background.draw(self._canvas)
                self._shake_ox = self._shake_oy = 0

            if   self.state == GameState.LOADING:
                self._loading_timer -= dt
                self._draw_loading()
                if self._loading_timer <= 0:
                    self.state = GameState.START
            elif self.state == GameState.START:
                self._start_screen.draw(self._canvas, self)
            elif self.state == GameState.SHIP_SELECT:
                self._ship_screen.draw(self._canvas, self)
            elif self.state == GameState.PLAYING:
                self._update(dt)
                self._draw()
            elif self.state == GameState.DYING:
                self._update_dying(dt)
                self._draw()
            elif self.state == GameState.PAUSED:
                self._draw()
                self._pause.draw(self._canvas, self)
            elif self.state == GameState.GAME_OVER:
                self._gameover.draw(self._canvas, self)
            elif self.state == GameState.SETTINGS:
                self._settings.draw(self._canvas, self)

            # ── Fade overlay ──────────────────────────────────────────
            self._fade_alpha += self._fade_dir * self._fade_speed * dt
            if self._fade_dir == 1 and self._fade_alpha >= 255:
                # Fully black — switch state, then fade in
                self._fade_alpha = 255
                if self._fade_next_state is not None:
                    self.state = self._fade_next_state
                    self._fade_next_state = None
                self._fade_dir = -1
            elif self._fade_dir == -1:
                self._fade_alpha = max(0.0, self._fade_alpha)

            if self._fade_alpha > 1:
                fade_surf = pygame.Surface((_LOGICAL_W, _LOGICAL_H))
                fade_surf.fill((0, 0, 0))
                fade_surf.set_alpha(int(self._fade_alpha))
                self._canvas.blit(fade_surf, (0, 0))

            # ── Scale to display ──────────────────────────────────────
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
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self._toggle_fullscreen()

            if self.state == GameState.START:
                if event.key == pygame.K_SPACE:
                    self._fade_to(GameState.SHIP_SELECT)

            elif self.state == GameState.SHIP_SELECT:
                action = self._ship_screen.handle_key(event.key, self)
                if action == 'confirm': self._confirm_ship()
                elif action == 'back':  self._fade_to(GameState.START)

            elif self.state == GameState.PLAYING:
                if event.key in (pygame.K_LEFT,  pygame.K_a): self.fighter.move_left()
                if event.key in (pygame.K_RIGHT, pygame.K_d): self.fighter.move_right()
                if event.key in (pygame.K_UP,    pygame.K_w): self.fighter.move_up()
                if event.key in (pygame.K_DOWN,  pygame.K_s): self.fighter.move_down()
                if event.key == pygame.K_SPACE:                self._shoot()
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    if self.fighter.dash_cooldown_ratio == 0:
                        self._dash_channel.play(self._dash_snd_raw)
                    self.fighter.dash()
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = GameState.PAUSED
                    self._music.pause()

            elif self.state == GameState.PAUSED:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = GameState.PLAYING
                    self._music.resume()

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

            if self.state == GameState.PLAYING and event.button == 1:
                self._shoot()

            elif self.state == GameState.START:
                action = self._start_screen.handle_click(lpos, self)
                if   action == 'play':     self._fade_to(GameState.SHIP_SELECT)
                elif action == 'settings': self._fade_to(GameState.SETTINGS)
                elif action == 'quit':     pygame.quit(); sys.exit()

            elif self.state == GameState.SHIP_SELECT:
                action = self._ship_screen.handle_click(lpos, self)
                if action == 'confirm': self._confirm_ship()

            elif self.state == GameState.GAME_OVER:
                action = self._gameover.handle_click(lpos, self)
                if action == 'retry':
                    self._init_game(); self._music.play_battle()
                    self._fade_to(GameState.PLAYING)
                elif action == 'menu':
                    self._init_game(); self._music.play_menu()
                    self._fade_to(GameState.START)

            elif self.state == GameState.SETTINGS:
                action = self._settings.handle_click(lpos, self)
                if   action == 'back':       self._fade_to(GameState.START)
                elif action == 'fullscreen': self._toggle_fullscreen()
                elif action == 'resolution': self._apply_resolution()

            elif self.state == GameState.PAUSED:
                action = self._pause.handle_click(lpos, self)
                if   action == 'resume':
                    self.state = GameState.PLAYING
                    self._music.resume()
                elif action == 'restart':
                    self._init_game(); self._music.resume()
                    self._fade_to(GameState.PLAYING)
                elif action == 'menu':
                    self._init_game(); self._music.play_menu()
                    self._fade_to(GameState.START)
                elif action == 'quit':
                    pygame.quit(); sys.exit()

        if event.type == pygame.MOUSEMOTION:
            lpos = self._lpos(event.pos)
            if   self.state == GameState.SETTINGS: self._settings.handle_motion(lpos, self)
            elif self.state == GameState.PAUSED:   self._pause.handle_motion(lpos, self)

        if event.type == pygame.MOUSEBUTTONUP:
            self._settings.handle_mouse_up(self)
            self._pause.handle_mouse_up(self)

    # ------------------------------------------------------------------
    # Ship selection
    # ------------------------------------------------------------------

    def _confirm_ship(self):
        self._selected_ship = SHIPS[self._ship_cursor]
        self._init_game()
        self._music.play_battle()
        self._fade_to(GameState.PLAYING)

    # ------------------------------------------------------------------
    # Shooting
    # ------------------------------------------------------------------

    def _shoot(self):
        ship = self._selected_ship
        if self._triple_shot_timer > 0:
            if ship.default_shots >= 2:
                # Heavy firepower ship: 4-shot spread
                angles = [-24, -8, 8, 24]
                limit  = 12
            else:
                angles = [-18, 0, 18]
                limit  = 9
        else:
            angles = [-10, 10] if ship.default_shots == 2 else [0]
            limit  = ship.max_bullets

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
        try:
            self._ball_queue.remove(ball)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Update (gameplay)
    # ------------------------------------------------------------------

    def _update(self, dt):
        if self._wave_banner_timer > 0: self._wave_banner_timer -= dt
        if self._triple_shot_timer > 0: self._triple_shot_timer -= dt
        if self._slow_time_timer   > 0: self._slow_time_timer   -= dt

        # Boss/mini-boss warning countdown
        if self._boss_warning_timer > 0:
            self._boss_warning_timer -= dt
            if self._boss_warning_timer <= 0:
                self._boss_warning_timer = 0.0
                pw = self._pending_boss_wave
                self._pending_boss_wave = 0
                if pw > 0:
                    self.boss = Boss(pw)
                elif pw < 0:
                    self.mini_boss = MiniBoss(-pw)

        slow = 0.30 if self._slow_time_timer > 0 else 1.0

        self.fighter.update(dt)
        self._spawn_engine_trail()
        self._update_engine_trail(dt)
        self.powerups.update(dt)
        self.aliens.update(dt * slow)
        self.balls.update(dt)
        self.explosions.update(dt)
        self.alien_bullets.update(dt * slow)
        self._update_particles(dt)

        self._update_boss(dt)
        self._update_mini_boss(dt)
        if self.state == GameState.GAME_OVER:
            return

        for ball in list(self.balls):
            if ball.is_out_of_screen():
                ball.kill()
                self._ball_queue_remove(ball)

        for ab in list(self.alien_bullets):
            if ab.is_off_screen():
                ab.kill()

        for pu in list(self.powerups):
            if pu.is_off_screen():
                pu.kill()
                continue
            if pu.rect.colliderect(self.fighter.rect):
                self._apply_powerup(pu)
                pu.kill()

        for alien in self.aliens:
            if isinstance(alien, ShooterAlien):
                for cx, cy in alien.drain_shots():
                    self.alien_bullets.add(AlienBullet(cx, cy))

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

        for ab in list(self.alien_bullets):
            if ab.rect.colliderect(self.fighter.rect):
                ab.kill()
                if self._shield_active:
                    self._shield_active = False
                    self.flash_timer  = 6
                    self._shake_timer = 2
                else:
                    self._take_damage()
                if self.state == GameState.GAME_OVER:
                    return

        for alien in list(self.aliens):
            reached = alien.has_reached_fighter(self.fighter)
            off     = alien.is_off_screen()
            if reached or off:
                alien.kill()
                # Shield absorbs direct collision but NOT enemies that slip past
                if reached and self._shield_active:
                    self._shield_active = False
                    self.flash_timer  = 6
                    self._shake_timer = 2
                    self._spawn_particles(alien.rect.centerx, alien.rect.centery,
                                         count=10, colors=[(70, 150, 255), (180, 220, 255)])
                else:
                    self._take_damage()
                if self.state == GameState.GAME_OVER:
                    return

        if (self.boss is None and self.mini_boss is None
                and len(self.aliens) == 0
                and self._pending_boss_wave == 0
                and self._boss_warning_timer <= 0):
            self._start_wave(self.wave + 1)

    def _update_boss(self, dt: float):
        if not self.boss:
            return

        self.boss.update(dt)

        for shot in self.boss.drain_shots():
            self.alien_bullets.add(AlienBullet(*shot))

        for ball in list(self.balls):
            if ball.rect.colliderect(self.boss.hit_rect):
                ball.kill()
                self._ball_queue_remove(ball)
                if self.boss.take_hit():
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
                    # Drop a heart at boss centre
                    self.powerups.add(HeartPowerUp(cx, cy))
                    self.boss = None
                    self._start_wave(self.wave + 1, extra_delay=2.0)
                    return
                else:
                    self.hit_sound.play()

        if self.boss and self.boss.rect.colliderect(self.fighter.rect):
            if self._shield_active:
                self._shield_active = False
                self.flash_timer  = 6
                self._shake_timer = 2
                # Shield rams the boss — deal damage to it
                if self.boss.take_hit(2):
                    pass   # boss HP handled normally; death checked next frame
            else:
                self._take_damage()

    def _update_mini_boss(self, dt: float):
        if not self.mini_boss:
            return
        self.mini_boss.update(dt)

        for shot in self.mini_boss.drain_shots():
            self.alien_bullets.add(AlienBullet(*shot))

        for ball in list(self.balls):
            if ball.rect.colliderect(self.mini_boss.hit_rect):
                ball.kill()
                self._ball_queue_remove(ball)
                if self.mini_boss.take_hit():
                    cx, cy = self.mini_boss.rect.center
                    for _ in range(4):
                        ox = random.randint(-35, 35)
                        oy = random.randint(-35, 35)
                        self.explosions.add(Explosion(cx + ox, cy + oy))
                    self._spawn_particles(cx, cy, count=25,
                                         colors=[(0, 220, 170), (0, 180, 140),
                                                 (255, 215, 0), (200, 255, 230)])
                    self.game_score += self.mini_boss.SCORE
                    if self.game_score > self.best_score:
                        self.best_score = self.game_score
                        ScoreManager.save(self.best_score)
                    self.hit_sound.play()
                    self.powerups.add(HeartPowerUp(cx, cy))   # always drops heart
                    self.mini_boss = None
                    self._start_wave(self.wave + 1, extra_delay=1.5)
                    return
                else:
                    self.hit_sound.play()

        if self.mini_boss and self.mini_boss.rect.colliderect(self.fighter.rect):
            if self._shield_active:
                self._shield_active = False
                self.flash_timer  = 6
                self._shake_timer = 2
                self.mini_boss.take_hit(2)
            else:
                self._take_damage()

    def _maybe_drop_powerup(self, cx: int, cy: int):
        if random.random() > 0.25:
            return
        roll = random.random()
        if   roll < 0.40: pu = TripleShotPowerUp(cx, cy)
        elif roll < 0.72: pu = SlowTimePowerUp(cx, cy)
        else:             pu = ShieldPowerUp(cx, cy)
        self.powerups.add(pu)

    def _apply_powerup(self, pu):
        if isinstance(pu, TripleShotPowerUp):
            self._triple_shot_timer = TripleShotPowerUp.DURATION
        elif isinstance(pu, ShieldPowerUp):
            self._shield_active = True
        elif isinstance(pu, SlowTimePowerUp):
            self._slow_time_timer = SlowTimePowerUp.DURATION
        elif isinstance(pu, HeartPowerUp):
            self.lives = min(self.lives + 1, Settings.get().starting_lives + 2)
        self.powerup_sound.play()

    def _take_damage(self):
        if self._shield_active:
            self._shield_active = False
            self.flash_timer  = 6
            self._shake_timer = 2
            return
        self.lives       -= 1
        self.flash_timer  = 20
        self._shake_timer = 5
        self.lose_life_sound.play()
        if self.lives <= 0:
            # Trigger death animation before showing game over
            cx, cy = self.fighter.rect.centerx, self.fighter.rect.centery
            for _ in range(10):
                ox = random.randint(-40, 40)
                oy = random.randint(-40, 40)
                self.explosions.add(Explosion(cx + ox, cy + oy))
            self._spawn_particles(cx, cy, count=60,
                                  colors=[(255, 220, 50), (255, 120, 0),
                                          (255, 60, 0),   (255, 255, 200)])
            self._shake_timer = 18
            self.state        = GameState.DYING
            self._death_timer = 1.8
            self.score_entries = ScoreManager.add_entry(
                self.game_score, self.wave, self._selected_ship.name,
                Settings.get().difficulty)
            self.best_score = max(self.best_score, self.game_score)

    def _spawn_particles(self, cx: int, cy: int, count: int = 12, colors=None):
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
    # Draw (gameplay only — menu screens draw themselves)
    # ------------------------------------------------------------------

    def _draw(self):
        cv = self._canvas
        self.background.draw(cv)

        if self.boss:
            cv.blit(self.boss.image, self.boss.rect)
        if self.mini_boss:
            cv.blit(self.mini_boss.image, self.mini_boss.rect)

        self._draw_engine_trail(cv)          # trail behind ship
        if self.state != GameState.DYING:
            cv.blit(self.fighter.image, self.fighter.rect)
        self.aliens.draw(cv)
        self.balls.draw(cv)
        self.alien_bullets.draw(cv)
        self.powerups.draw(cv)
        self.explosions.draw(cv)
        self._draw_particles(cv)

        # Shield ring
        if self._shield_active:
            scx, scy = self.fighter.rect.center
            r     = max(self.fighter.width, self.fighter.height) // 2 + 11
            pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() / 180.0)
            _sh   = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(_sh, (70, 150, 255, int(140 * pulse)), (r + 2, r + 2), r, 3)
            cv.blit(_sh, (scx - r - 2, scy - r - 2))

        # Slow-time tint
        if self._slow_time_timer > 0:
            _st = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            _st.fill((25, 45, 180, 22))
            cv.blit(_st, (0, 0))

        # Boss / mini-boss WARNING animation
        if self._boss_warning_timer > 0:
            t       = pygame.time.get_ticks() / 1000.0
            sw, sh  = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
            is_mini = (self.wave % 5 == 3)
            # Pulsing red screen edges
            pulse_a = int(80 + 70 * math.sin(t * 8.0))
            edge    = pygame.Surface((sw, sh), pygame.SRCALPHA)
            for thick, alpha in ((18, pulse_a), (8, pulse_a // 2)):
                col = (255, 80, 0, alpha) if is_mini else (255, 20, 20, alpha)
                pygame.draw.rect(edge, col, (0, 0, sw, sh), thick)
            cv.blit(edge, (0, 0))
            # WARNING text — flashes
            if int(t * 4) % 2 == 0:
                warn_col = (255, 160, 0) if is_mini else (255, 30, 30)
                warn_txt = "!! MINI-BOSS !!" if is_mini else "!! WARNING !!"
                ws = self.wave_font.render(warn_txt, True, warn_col)
                cv.blit(ws, ws.get_rect(centerx=sw // 2, centery=sh // 2 - 30))
            sub_txt  = "A raider approaches!" if is_mini else "BOSS INCOMING!"
            sub_col  = (255, 200, 100) if is_mini else (255, 120, 120)
            ss = self.game_font.render(sub_txt, True, sub_col)
            cv.blit(ss, ss.get_rect(centerx=sw // 2, centery=sh // 2 + 40))

        # Wave banner
        if self._wave_banner_timer > 0:
            alpha    = 255 if self._wave_banner_timer >= 0.5 else int(255 * self._wave_banner_timer / 0.5)
            is_boss  = (self.wave % 5 == 0)
            is_mini  = (self.wave % 5 == 3 and self.wave >= 3)
            if is_boss:
                b_txt, b_color, s_txt = f"BOSS WAVE  {self.wave}!", (255, 55, 55), "Defeat the boss!"
            elif is_mini:
                b_txt, b_color, s_txt = f"WAVE  {self.wave}  —  MINI-BOSS", (255, 160, 0), "A raider is coming!"
            else:
                b_txt, b_color, s_txt = f"WAVE  {self.wave}", (255, 215, 50), "New aliens incoming!"
            banner = self.wave_font.render(b_txt, True, b_color);  banner.set_alpha(alpha)
            sub    = self.game_font.render(s_txt, True, (200, 200, 200)); sub.set_alpha(alpha)
            bx = config.SCREEN_WIDTH  // 2 - banner.get_width() // 2
            by = config.SCREEN_HEIGHT // 3 - banner.get_height() // 2
            cv.blit(banner, (bx, by))
            cv.blit(sub, sub.get_rect(centerx=config.SCREEN_WIDTH // 2,
                                      top=by + banner.get_height() + 4))

        # Hit flash
        if self.flash_timer > 0:
            fs = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            fs.fill((255, 0, 0, int(self.flash_timer * 4.5)))
            cv.blit(fs, (0, 0))
            self.flash_timer -= 1

        self._draw_hud(cv)

        # Camera shake
        if self._shake_timer > 0:
            self._shake_ox = random.randint(-8, 8)
            self._shake_oy = random.randint(-5, 5)
            self._shake_timer -= 1
        else:
            self._shake_ox = self._shake_oy = 0

    def _update_particles(self, dt: float):
        alive = []
        for p in self._particles:
            p['x']    += p['vx'] * dt
            p['y']    += p['vy'] * dt
            p['vy']   += 90.0 * dt
            p['life'] -= dt
            if p['life'] > 0:
                alive.append(p)
        self._particles = alive

    def _draw_particles(self, surface: pygame.Surface):
        for p in self._particles:
            ratio = p['life'] / p['max_life']
            r = int(p['color'][0] * ratio)
            g = int(p['color'][1] * ratio)
            b = int(p['color'][2] * ratio)
            s = p['size']
            pygame.draw.rect(surface, (r, g, b),
                             (int(p['x']) - s // 2, int(p['y']) - s // 2, s, s))

    # ------------------------------------------------------------------
    # Engine trail
    # ------------------------------------------------------------------

    def _spawn_engine_trail(self):
        """Spawn 1-2 exhaust particles at the ship's engine position."""
        f = self.fighter
        if not (f.is_moving_left or f.is_moving_right or
                f.is_moving_up  or f.is_moving_down or f.is_dashing):
            return
        ship  = self._selected_ship
        r, g, b = ship.color
        cx = f.rect.centerx + random.randint(-4, 4)
        cy = f.rect.bottom  - 4
        for _ in range(2 if f.is_dashing else 1):
            self._engine_particles.append({
                'x': float(cx), 'y': float(cy),
                'vx': random.uniform(-18, 18),
                'vy': random.uniform(18, 55),
                'life': random.uniform(0.18, 0.35),
                'max_life': 0.35,
                'r': min(255, r + 80), 'g': min(255, g + 80), 'b': min(255, b + 80),
                'size': random.randint(2, 4 if f.is_dashing else 3),
            })

    def _update_engine_trail(self, dt: float):
        alive = []
        for p in self._engine_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt
            if p['life'] > 0:
                alive.append(p)
        self._engine_particles = alive

    def _draw_engine_trail(self, surface: pygame.Surface):
        for p in self._engine_particles:
            ratio = p['life'] / p['max_life']
            alpha = int(220 * ratio)
            s     = max(1, int(p['size'] * ratio))
            col   = (int(p['r'] * ratio), int(p['g'] * ratio), int(p['b'] * ratio))
            pygame.draw.circle(surface, col, (int(p['x']), int(p['y'])), s)

    # ------------------------------------------------------------------
    # Death animation state
    # ------------------------------------------------------------------

    def _update_dying(self, dt: float):
        """Run explosions/particles during death; then fade to GAME_OVER."""
        self.explosions.update(dt)
        self._update_particles(dt)
        if self._shake_timer > 0:
            self._shake_timer -= 1
        self._death_timer -= dt
        if self._death_timer <= 0:
            self._music.stop()
            self._fade_to(GameState.GAME_OVER)

    def _draw_hud(self, surface: pygame.Surface):
        self._draw_boss_hp_bar(surface)
        self._draw_mini_boss_hp_bar(surface)
        self._draw_powerup_hud(surface)

        sw = config.SCREEN_WIDTH

        # ── Left HUD panel ────────────────────────────────────────────
        panel_w, panel_h = 310, 62
        draw_glass_panel(surface, pygame.Rect(10, 10, panel_w, panel_h),
                         bg_color=(8, 8, 22), bg_alpha=200,
                         border_color=(50, 50, 80), radius=10)

        # Score
        sc = render_shadowed(self.game_font,
                             f"Score  {self.game_score}", (255, 255, 255))
        surface.blit(sc, (20, 16))

        # Wave badge
        wave_col = (255, 80, 80) if self.wave % 5 == 0 else (255, 215, 50)
        wv = render_shadowed(self.small_font, f"WAVE {self.wave}", wave_col)
        surface.blit(wv, (20, 40))

        # Best score
        bs = render_shadowed(self.small_font,
                             f"Best {self.best_score}", (100, 100, 140))
        surface.blit(bs, (panel_w - bs.get_width() - 10, 40))

        # Hearts — right-aligned inside panel
        hx = panel_w - 10 - self.lives * 26
        hy = 14
        for i in range(self.lives):
            surface.blit(self.heart_icon, (hx + i * 26, hy))

        # ── Dash bar ──────────────────────────────────────────────────
        bar_x, bar_y, bar_w, bar_h = 20, 78, 90, 6
        ratio = self.fighter.dash_cooldown_ratio
        ready = ratio == 0
        pygame.draw.rect(surface, (30, 30, 45),
                         (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        fill_w = int(bar_w * (1.0 - ratio))
        fill_col = (0, 220, 255) if ready else (0, 120, 160)
        if fill_w > 0:
            pygame.draw.rect(surface, fill_col,
                             (bar_x, bar_y, fill_w, bar_h), border_radius=3)
        pygame.draw.rect(surface, (50, 50, 75),
                         (bar_x, bar_y, bar_w, bar_h), 1, border_radius=3)
        dash_label = render_shadowed(self.small_font,
                                     "DASH  READY" if ready else "DASH",
                                     (0, 220, 255) if ready else (80, 100, 110))
        surface.blit(dash_label, (bar_x + bar_w + 8, bar_y - 4))

    def _draw_boss_hp_bar(self, surface: pygame.Surface):
        if not self.boss:
            return
        ratio = self.boss.hp_ratio
        sw    = config.SCREEN_WIDTH
        bar_w = min(560, sw - 80)
        bar_h = 20
        bx    = sw // 2 - bar_w // 2
        by    = config.SCREEN_HEIGHT - 48

        # Panel behind bar
        draw_glass_panel(surface,
                         pygame.Rect(bx - 12, by - 28, bar_w + 24, bar_h + 36),
                         bg_color=(20, 5, 30), bg_alpha=210,
                         border_color=(120, 20, 160), radius=8)

        # Bar track
        pygame.draw.rect(surface, (40, 12, 55),
                         (bx, by, bar_w, bar_h), border_radius=5)

        if ratio > 0:
            fill_w = max(1, int(bar_w * ratio))
            if   ratio > 0.66: bar_col = (45, 195, 55)
            elif ratio > 0.33: bar_col = (220, 170, 0)
            else:              bar_col = (210, 35, 35)
            pygame.draw.rect(surface, bar_col,
                             (bx, by, fill_w, bar_h), border_radius=5)
            # Shimmer highlight on bar
            pygame.draw.rect(surface, tuple(min(255, c + 60) for c in bar_col),
                             (bx, by, fill_w, bar_h // 3), border_radius=5)

        pygame.draw.rect(surface, (160, 30, 210),
                         (bx, by, bar_w, bar_h), 2, border_radius=5)

        # Boss name + HP text
        tier_names = {1: "Phantom", 2: "Ravager", 3: "Leviathan"}
        name  = tier_names.get(getattr(self.boss, '_tier', 1), "BOSS")
        label = render_shadowed(self.game_font,
                                f"{name.upper()}   {self.boss.hp} / {self.boss.max_hp}",
                                (220, 180, 255), (60, 0, 90))
        surface.blit(label, label.get_rect(
            centerx=sw // 2, bottom=by - 4))

    def _draw_mini_boss_hp_bar(self, surface: pygame.Surface):
        if not self.mini_boss:
            return
        ratio = self.mini_boss.hp_ratio
        sw    = config.SCREEN_WIDTH
        bar_w, bar_h = 360, 14
        bx = sw // 2 - bar_w // 2
        by = config.SCREEN_HEIGHT - 44
        draw_glass_panel(surface,
                         pygame.Rect(bx - 10, by - 24, bar_w + 20, bar_h + 30),
                         bg_color=(15, 35, 30), bg_alpha=210,
                         border_color=(0, 160, 120), radius=8)
        pygame.draw.rect(surface, (20, 55, 45), (bx, by, bar_w, bar_h), border_radius=5)
        if ratio > 0:
            fill_w   = max(1, int(bar_w * ratio))
            bar_col  = (0, 200, 155) if ratio > 0.5 else (200, 160, 0) if ratio > 0.25 else (210, 80, 0)
            pygame.draw.rect(surface, bar_col, (bx, by, fill_w, bar_h), border_radius=5)
            pygame.draw.rect(surface, tuple(min(255, c + 50) for c in bar_col),
                             (bx, by, fill_w, bar_h // 3), border_radius=5)
        pygame.draw.rect(surface, (0, 180, 140), (bx, by, bar_w, bar_h), 2, border_radius=5)
        label = render_shadowed(self.game_font,
                                f"RAIDER   {self.mini_boss.hp} / {self.mini_boss.max_hp}",
                                (180, 255, 230), (0, 40, 30))
        surface.blit(label, label.get_rect(centerx=sw // 2, bottom=by - 4))

    def _draw_powerup_hud(self, surface: pygame.Surface):
        lines = []
        if self._triple_shot_timer > 0:
            lines.append((f"3x  {self._triple_shot_timer:.1f}s", (255, 210, 0)))
        if self._shield_active:
            lines.append(("SHIELD", (70, 150, 255)))
        if self._slow_time_timer > 0:
            lines.append((f"SLOW  {self._slow_time_timer:.1f}s", (165, 75, 255)))
        if not lines:
            return

        sw   = config.SCREEN_WIDTH
        px   = sw - 14
        py   = 14
        pw   = 130
        ph   = len(lines) * 28 + 10
        draw_glass_panel(surface, pygame.Rect(px - pw, py, pw, ph),
                         bg_color=(10, 10, 25), bg_alpha=190,
                         border_color=(60, 40, 90), radius=8)
        ty = py + 8
        for text, color in lines:
            s = render_shadowed(self.small_font, text, color)
            surface.blit(s, (px - s.get_width() - 8, ty))
            ty += 28

    # ------------------------------------------------------------------
    # Loading screen
    # ------------------------------------------------------------------

    def _draw_loading(self):
        """Splash screen shown for ~2.5 s on startup."""
        cv = self._canvas
        cx = _LOGICAL_W // 2
        cy = _LOGICAL_H // 2
        t  = pygame.time.get_ticks() / 1000.0

        # Animated background already drawn by StarBackground.draw()
        # (called before this method in run())

        TOTAL    = 2.5
        elapsed  = max(0.0, TOTAL - self._loading_timer)
        progress = min(1.0, elapsed / TOTAL)

        # Title with outline — rendered fresh (cheap at 60fps for a 2.5s splash)
        glow_alpha = int(210 + 45 * math.sin(t * 2.5))
        title = render_outlined(self.wave_font, "SERPENTIS",
                                (210, 160, 255), (60, 10, 100), thickness=2)
        title.set_alpha(glow_alpha)
        cv.blit(title, title.get_rect(centerx=cx, centery=cy - 70))

        # Subtitle
        sub = render_shadowed(self.game_font,
                              "A Python space shooter",
                              (120, 110, 160), (0, 0, 0))
        cv.blit(sub, sub.get_rect(centerx=cx, centery=cy - 5))

        # Glass panel for bar
        bar_w, bar_h = 360, 12
        bar_x = cx - bar_w // 2
        bar_y = cy + 52
        draw_glass_panel(cv, pygame.Rect(bar_x - 12, bar_y - 12,
                                         bar_w + 24, bar_h + 28),
                         bg_color=(12, 8, 28), bg_alpha=210,
                         border_color=(80, 40, 130), radius=8)

        # Bar track + fill
        pygame.draw.rect(cv, (30, 20, 50),
                         (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        fill = int(bar_w * progress)
        if fill > 0:
            # Gradient: purple → cyan
            for fx in range(fill):
                ratio = fx / max(bar_w - 1, 1)
                r = int(130 + (0   - 130) * ratio)
                g = int(40  + (190 - 40)  * ratio)
                b = int(220 + (255 - 220) * ratio)
                pygame.draw.line(cv, (r, g, b),
                                 (bar_x + fx, bar_y),
                                 (bar_x + fx, bar_y + bar_h))
            # Shine
            pygame.draw.rect(cv, (255, 255, 255, 40),
                             (bar_x, bar_y, fill, bar_h // 3), border_radius=6)
        pygame.draw.rect(cv, (100, 60, 180),
                         (bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)

        # Percentage text
        pct = render_shadowed(self.small_font,
                              f"Loading...  {int(progress * 100)}%",
                              (150, 110, 200), (0, 0, 0))
        cv.blit(pct, pct.get_rect(centerx=cx, top=bar_y + bar_h + 8))

        # Version tag
        ver = render_shadowed(self.small_font,
                              "v1.7.0  -  Yehor Petrenko",
                              (50, 45, 70))
        cv.blit(ver, ver.get_rect(centerx=cx, bottom=_LOGICAL_H - 14))
