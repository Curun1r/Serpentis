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
from powerup import TripleShotPowerUp, ShieldPowerUp, SlowTimePowerUp, HeartPowerUp
from config import GAME_CAPTION, STARTING_LIVES
from assets import Assets
from score_manager import ScoreManager
from settings_manager import Settings
from explosion import Explosion
from ship import ShipConfig, SHIPS

from screens.start      import StartScreen
from screens.ship_select import ShipSelectScreen
from screens.game_over  import GameOverScreen
from screens.settings   import SettingsScreen
from screens.pause      import PauseOverlay


class GameState(Enum):
    START       = "start"
    SHIP_SELECT = "ship_select"
    PLAYING     = "playing"
    PAUSED      = "paused"
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
        self.shoot_sound     = Assets.get_sound('shoot',     frequency=520, duration=0.08)
        self.hit_sound       = Assets.get_sound('hit',       frequency=220, duration=0.25)
        self.lose_life_sound = Assets.get_sound('lose_life', frequency=110, duration=0.5)
        self.powerup_sound   = Assets.get_sound('powerup',   frequency=740, duration=0.22)
        self._apply_volume()

        # ── Assets ────────────────────────────────────────────────────────
        raw_bg = Assets.get_image('image/background.png')
        self.background = pygame.transform.scale(raw_bg, (_LOGICAL_W, _LOGICAL_H)).convert()

        raw_heart = Assets.get_image('image/heart.png')
        self.heart_icon = pygame.transform.smoothscale(raw_heart, (22, 22))

        # Pre-tinted fighter preview sprites for the ship-select cards
        raw_fighter = Assets.get_image('image/fighter.png')
        fw, fh = raw_fighter.get_size()
        _prev_h = 80
        _prev_w = int(fw * (_prev_h / fh))
        _prev_base = pygame.transform.scale(raw_fighter, (_prev_w, _prev_h))
        self._ship_previews: list[pygame.Surface] = []
        for _ship in SHIPS:
            _s = _prev_base.copy()
            r, g, b = _ship.color
            _s.fill((min(255, r + 120), min(255, g + 120), min(255, b + 120)),
                    special_flags=pygame.BLEND_RGB_MULT)
            self._ship_previews.append(_s)

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

        self.state = GameState.START
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
                    self.lose_life_sound, self.powerup_sound):
            snd.set_volume(vol)

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
        self.lives              = STARTING_LIVES
        self.flash_timer        = 0
        self.wave               = 0
        self.fighter            = Fighter(ship=self._selected_ship)
        self.balls              = pygame.sprite.Group()
        self._ball_queue        = []
        self.explosions         = pygame.sprite.Group()
        self.alien_bullets      = pygame.sprite.Group()
        self.powerups           = pygame.sprite.Group()
        self.boss               = None
        self._particles         = []
        self._shake_timer       = 0
        self._wave_banner_timer = 0.0
        self._triple_shot_timer = 0.0
        self._shield_active     = False
        self._slow_time_timer   = 0.0
        self._boss_kill_delay   = 0.0   # seconds remaining before next wave after boss dies
        self._start_wave(1)

    def _start_wave(self, wave_num: int):
        self.wave               = wave_num
        self.alien_bullets      = pygame.sprite.Group()
        self.powerups           = pygame.sprite.Group()
        self._wave_banner_timer = 2.8

        if wave_num % 5 == 0:
            self.boss   = Boss(wave_num)
            self.aliens = pygame.sprite.Group()
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
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._handle_event(event)

            # Menu screens get a fresh background each frame;
            # gameplay states manage their own canvas via _draw().
            if self.state not in (GameState.PLAYING, GameState.PAUSED):
                self._canvas.blit(self.background, (0, 0))
                self._shake_ox = self._shake_oy = 0

            if   self.state == GameState.START:
                self._start_screen.draw(self._canvas, self)
            elif self.state == GameState.SHIP_SELECT:
                self._ship_screen.draw(self._canvas, self)
            elif self.state == GameState.PLAYING:
                self._update(dt)
                self._draw()
            elif self.state == GameState.PAUSED:
                self._draw()
                self._pause.draw(self._canvas, self)
            elif self.state == GameState.GAME_OVER:
                self._gameover.draw(self._canvas, self)
            elif self.state == GameState.SETTINGS:
                self._settings.draw(self._canvas, self)

            # Scale logical canvas to physical display (with shake offset)
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
                    self.state = GameState.SHIP_SELECT

            elif self.state == GameState.SHIP_SELECT:
                action = self._ship_screen.handle_key(event.key, self)
                if action == 'confirm': self._confirm_ship()
                elif action == 'back':  self.state = GameState.START

            elif self.state == GameState.PLAYING:
                if event.key in (pygame.K_LEFT,  pygame.K_a): self.fighter.move_left()
                if event.key in (pygame.K_RIGHT, pygame.K_d): self.fighter.move_right()
                if event.key in (pygame.K_UP,    pygame.K_w): self.fighter.move_up()
                if event.key in (pygame.K_DOWN,  pygame.K_s): self.fighter.move_down()
                if event.key == pygame.K_SPACE:                self._shoot()
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT): self.fighter.dash()
                if event.key in (pygame.K_p, pygame.K_ESCAPE): self.state = GameState.PAUSED

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

            if self.state == GameState.PLAYING and event.button == 1:
                self._shoot()

            elif self.state == GameState.START:
                action = self._start_screen.handle_click(lpos, self)
                if   action == 'play':     self.state = GameState.SHIP_SELECT
                elif action == 'settings': self.state = GameState.SETTINGS
                elif action == 'quit':     pygame.quit(); sys.exit()

            elif self.state == GameState.SHIP_SELECT:
                action = self._ship_screen.handle_click(lpos, self)
                if action == 'confirm': self._confirm_ship()

            elif self.state == GameState.GAME_OVER:
                action = self._gameover.handle_click(lpos, self)
                if   action == 'retry': self._init_game(); self.state = GameState.PLAYING
                elif action == 'menu':  self._init_game(); self.state = GameState.START

            elif self.state == GameState.SETTINGS:
                action = self._settings.handle_click(lpos, self)
                if   action == 'back':       self.state = GameState.START
                elif action == 'fullscreen': self._toggle_fullscreen()
                elif action == 'resolution': self._apply_resolution()

            elif self.state == GameState.PAUSED:
                action = self._pause.handle_click(lpos, self)
                if   action == 'resume':  self.state = GameState.PLAYING
                elif action == 'restart': self._init_game(); self.state = GameState.PLAYING
                elif action == 'menu':    self._init_game(); self.state = GameState.START
                elif action == 'quit':    pygame.quit(); sys.exit()

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
        self.state = GameState.PLAYING

    # ------------------------------------------------------------------
    # Shooting
    # ------------------------------------------------------------------

    def _shoot(self):
        if self._triple_shot_timer > 0:
            angles = [-18, 0, 18]
            limit  = 9
        else:
            ship   = self._selected_ship
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

        if self._boss_kill_delay > 0:
            self._boss_kill_delay -= dt
            if self._boss_kill_delay <= 0:
                self._boss_kill_delay = 0.0
                self._start_wave(self.wave + 1)
            return   # freeze enemy spawning / wave check during delay

        slow = 0.30 if self._slow_time_timer > 0 else 1.0

        self.fighter.update(dt)
        self.powerups.update(dt)
        self.aliens.update(dt * slow)
        self.balls.update(dt)
        self.explosions.update(dt)
        self.alien_bullets.update(dt * slow)
        self._update_particles(dt)

        self._update_boss(dt)
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
                self._take_damage()
                if self.state == GameState.GAME_OVER:
                    return

        for alien in list(self.aliens):
            if alien.has_reached_fighter(self.fighter) or alien.is_off_screen():
                alien.kill()
                self._take_damage()
                if self.state == GameState.GAME_OVER:
                    return

        if self.boss is None and len(self.aliens) == 0:
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
                    self._boss_kill_delay = 3.0   # pause before next wave
                    return
                else:
                    self.hit_sound.play()

        if self.boss and self.boss.rect.colliderect(self.fighter.rect):
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
            self.lives = min(self.lives + 1, STARTING_LIVES + 2)
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
            self.state = GameState.GAME_OVER
            self.score_entries = ScoreManager.add_entry(
                self.game_score, self.wave, self._selected_ship.name)
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
        cv.blit(self.background, (0, 0))

        if self.boss:
            cv.blit(self.boss.image, self.boss.rect)

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

        # Boss-kill delay countdown banner
        if self._boss_kill_delay > 0:
            secs = math.ceil(self._boss_kill_delay)
            txt  = self.wave_font.render("BOSS  DEFEATED!", True, (255, 215, 0))
            sub  = self.game_font.render(f"Next wave in  {secs}…", True, (200, 200, 200))
            cv.blit(txt, txt.get_rect(centerx=config.SCREEN_WIDTH // 2,
                                      centery=config.SCREEN_HEIGHT // 3))
            cv.blit(sub, sub.get_rect(centerx=config.SCREEN_WIDTH // 2,
                                      top=config.SCREEN_HEIGHT // 3 + txt.get_height() // 2 + 8))

        # Wave banner
        if self._wave_banner_timer > 0:
            alpha    = 255 if self._wave_banner_timer >= 0.5 else int(255 * self._wave_banner_timer / 0.5)
            is_boss  = (self.wave % 5 == 0)
            b_txt    = f"BOSS WAVE  {self.wave}!" if is_boss else f"WAVE  {self.wave}"
            b_color  = (255, 55, 55) if is_boss else (255, 215, 50)
            s_txt    = "Defeat the boss!" if is_boss else "New aliens incoming!"
            banner   = self.wave_font.render(b_txt, True, b_color);  banner.set_alpha(alpha)
            sub      = self.game_font.render(s_txt, True, (200, 200, 200)); sub.set_alpha(alpha)
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

    def _draw_hud(self, surface: pygame.Surface):
        self._draw_boss_hp_bar(surface)
        self._draw_powerup_hud(surface)

        score_text = self.game_font.render(
            f"Score: {self.game_score}   Best: {self.best_score}"
            f"   Wave: {self.wave}   Lives:",
            True, 'white')
        surface.blit(score_text, (20, 20))

        hearts_x = 20 + score_text.get_width() + 6
        hearts_y = 20 + score_text.get_height() // 2 - self.heart_icon.get_height() // 2
        for i in range(self.lives):
            surface.blit(self.heart_icon, (hearts_x + i * 26, hearts_y))

        bar_x, bar_y, bar_w, bar_h = 20, 52, 80, 6
        ratio = self.fighter.dash_cooldown_ratio
        if ratio > 0:
            pygame.draw.rect(surface, (60, 60, 60),   (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            fill_w = int(bar_w * (1.0 - ratio))
            if fill_w > 0:
                pygame.draw.rect(surface, (0, 220, 255), (bar_x, bar_y, fill_w, bar_h), border_radius=3)
            label = self.game_font.render("DASH", True, (120, 120, 120))
        else:
            pygame.draw.rect(surface, (0, 220, 255), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            label = self.game_font.render("DASH", True, (0, 220, 255))
        surface.blit(
            pygame.transform.scale(label, (int(label.get_width() * 0.6), int(label.get_height() * 0.6))),
            (bar_x + bar_w + 6, bar_y - 2))

    def _draw_boss_hp_bar(self, surface: pygame.Surface):
        if not self.boss:
            return
        ratio = self.boss.hp_ratio
        bar_w = min(520, config.SCREEN_WIDTH - 80)
        bar_h = 22
        bx    = config.SCREEN_WIDTH  // 2 - bar_w // 2
        by    = config.SCREEN_HEIGHT - 44

        pygame.draw.rect(surface, (30, 8,  45), (bx - 2, by - 2, bar_w + 4, bar_h + 4), border_radius=5)
        pygame.draw.rect(surface, (55, 18, 75), (bx, by, bar_w, bar_h), border_radius=4)

        if ratio > 0:
            fill_w = max(1, int(bar_w * ratio))
            color  = (50, 200, 55) if ratio > 0.66 else (225, 175, 0) if ratio > 0.33 else (215, 38, 38)
            pygame.draw.rect(surface, color, (bx, by, fill_w, bar_h), border_radius=4)

        pygame.draw.rect(surface, (175, 28, 215), (bx, by, bar_w, bar_h), 2, border_radius=4)

        lbl = self.game_font.render(f"BOSS  HP: {self.boss.hp} / {self.boss.max_hp}",
                                    True, (215, 175, 255))
        surface.blit(lbl, lbl.get_rect(centerx=config.SCREEN_WIDTH // 2, bottom=by - 5))

    def _draw_powerup_hud(self, surface: pygame.Surface):
        lines = []
        if self._triple_shot_timer > 0:
            lines.append((f"3x SHOT  {self._triple_shot_timer:.1f}s", (255, 210, 0)))
        if self._shield_active:
            lines.append(("SHIELD  ACTIVE", (70, 150, 255)))
        if self._slow_time_timer > 0:
            lines.append((f"SLOW TIME  {self._slow_time_timer:.1f}s", (165, 75, 255)))

        x, y = config.SCREEN_WIDTH - 18, 20
        for text, color in lines:
            surf = self.game_font.render(text, True, color)
            surface.blit(surf, (x - surf.get_width(), y))
            y += surf.get_height() + 4
