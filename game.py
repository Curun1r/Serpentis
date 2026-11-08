"""Application controller: setup, screen transitions and ordered frame execution."""

from __future__ import annotations

import random
import sys

import pygame

import combat
import config
import rendering
from alien import Alien, ArmoredAlien, ShooterAlien, ZigzagAlien
from assets import Assets
from background import StarBackground
from config import GAME_CAPTION
from display_layout import (
    choose_window_size,
    current_display_index,
    fit_viewport,
    game_canvas_size,
    get_native_resolution,
    remember_display,
)
from effects import VisualEffects
from fighter import Fighter
from frame_timing import FrameLimiter
from game_state import GameState
from music import MusicPlayer
from score_manager import ScoreManager
from screens.controls import ControlsScreen
from screens.game_over import GameOverScreen
from screens.leaderboard import LeaderboardScreen
from screens.pause import PauseOverlay
from screens.settings import SettingsScreen
from screens.ship_select import ShipSelectScreen
from screens.start import StartScreen
from settings_manager import Settings
from ship import SHIPS, ShipConfig
from ship_sprites import build_ship

# Menus retain their design size. Gameplay uses the chosen ratio at height 720.
_LOGICAL_W, _LOGICAL_H = 1280, 720


class MenuContext:
    """Keep menu layouts at 1280x720 while delegating run state to the game."""

    screen_width, screen_height = _LOGICAL_W, _LOGICAL_H

    def __init__(self, game):
        object.__setattr__(self, "_game", game)

    def __getattr__(self, name):
        return getattr(self._game, name)

    def __setattr__(self, name, value):
        setattr(self._game, name, value)


class Game:
    """Own application/run state and coordinate screens, simulation and drawing.

    Combat rules live in combat.py, drawing in rendering.py/hud.py, and
    transient visual state in VisualEffects. Game controls their execution order.
    """

    def __init__(self) -> None:
        pygame.display.set_caption(GAME_CAPTION)

        self.screen_width = _LOGICAL_W
        self.screen_height = _LOGICAL_H
        config.SCREEN_WIDTH = _LOGICAL_W
        config.SCREEN_HEIGHT = _LOGICAL_H

        self._display_index = current_display_index()
        self._open_display()
        self._shake_ox = self._shake_oy = 0

        fonts = self._load_fonts()
        self._frame_limiter = FrameLimiter()

        self._load_sounds()
        self._load_visual_assets()

        # ── Persistent state ──────────────────────────────────────────────
        self.best_score, self.score_entries = ScoreManager.load()
        self._selected_ship: ShipConfig = SHIPS[0]
        self._ship_cursor: int = 0

        self._create_screens(fonts)

        # ── Canvas & visual effects ────────────────────────────────────────────
        self._canvas = pygame.Surface((_LOGICAL_W, _LOGICAL_H))
        self._effects = VisualEffects(self.game_font)

        # Fade transition system
        self._fade_alpha = 255  # start fully black, fade in on launch
        self._fade_dir = -1  # -1 = fade in, +1 = fade out
        self._fade_speed = 420.0  # alpha units per second
        self._fade_next_state: GameState | None = None

        self.state = GameState.LOADING
        self._loading_timer = 2.5  # seconds to show splash
        self._init_game()

        # ── Music ─────────────────────────────────────────────────────────
        self._music = MusicPlayer()
        self._music.set_volume(Settings.get().volume * 0.5)
        self._music.play_menu()

    def _load_fonts(self) -> dict[str, pygame.font.Font]:
        fonts = {
            "game": pygame.font.Font(None, 36),
            "med": pygame.font.Font(None, 52),
            "small": pygame.font.Font(None, 26),
            "wave": pygame.font.Font(None, 86),
        }
        self.game_font = fonts["game"]
        self.med_font = fonts["med"]
        self.small_font = fonts["small"]
        self.wave_font = fonts["wave"]

        return fonts

    def _load_sounds(self) -> None:
        # Shoot: laser chirp (900 Hz → 120 Hz, 0.13 s)
        self.shoot_sound = Assets.make_chirp("shoot", 900, 120, 0.13, 0.45)
        # Dash: whoosh (350 Hz → 60 Hz, 0.20 s) — on dedicated channel to avoid cutoff
        self._dash_snd_raw = Assets.make_chirp("dash", 350, 60, 0.20, 0.55)
        self._dash_channel = pygame.mixer.Channel(0)  # reserved — never stolen
        # Hit / lose-life / powerup: keep as sine tones
        self.hit_sound = Assets.make_chirp("hit", 180, 40, 0.12, 0.50)
        self.lose_life_sound = Assets.get_sound("lose_life", frequency=110, duration=0.5)
        self.powerup_sound = Assets.get_sound("powerup", frequency=740, duration=0.22)
        # Shield break: electric burst (550 Hz → 60 Hz, 0.22 s)
        self.shield_break_sound = Assets.make_chirp("shield_break", 550, 60, 0.22, 0.65)
        # UI sounds
        self.ui_click_sound = Assets.make_chirp("ui_click", 700, 500, 0.06, 0.30)
        self.ui_nav_sound = Assets.make_chirp("ui_nav", 900, 700, 0.04, 0.22)
        self._apply_volume()

    def _load_visual_assets(self) -> None:
        self.background = StarBackground(_LOGICAL_W, _LOGICAL_H)

        raw_heart = Assets.get_image("image/heart.png")
        self.heart_icon = pygame.transform.smoothscale(raw_heart, (22, 22))

        # Procedural ship preview sprites for the ship-select cards
        preview_height = 80
        self._ship_previews: list[pygame.Surface] = []
        for ship in SHIPS:
            raw = build_ship(ship.id)
            rw, rh = raw.get_size()
            preview_width = int(rw * (preview_height / rh))
            self._ship_previews.append(pygame.transform.smoothscale(raw, (preview_width, preview_height)))

    def _create_screens(self, fonts: dict[str, pygame.font.Font]) -> None:
        self._start_screen = StartScreen(fonts)
        self._ship_screen = ShipSelectScreen(fonts, self._ship_previews)
        self._gameover = GameOverScreen(fonts)
        self._settings = SettingsScreen(fonts)
        self._pause = PauseOverlay(fonts)
        self._controls = ControlsScreen(fonts)
        self._leaderboard = LeaderboardScreen(fonts)
        self._leaderboard_return = GameState.START
        self._menu_context = MenuContext(self)
        self._menu_canvas = pygame.Surface((_LOGICAL_W, _LOGICAL_H))
        self._menu_background = StarBackground(_LOGICAL_W, _LOGICAL_H)
        self._update_screen_layouts()

    # ------------------------------------------------------------------
    # Layout & display helpers
    # ------------------------------------------------------------------

    def _update_screen_layouts(self) -> None:
        """Keep menus at their fixed design size, independently of the playfield."""
        sw, sh = _LOGICAL_W, _LOGICAL_H
        self._start_screen.update_layout(sw, sh)
        self._gameover.update_layout(sw, sh)

    def _apply_volume(self) -> None:
        vol = Settings.get().volume
        for snd in (
            self.shoot_sound,
            self.hit_sound,
            self.lose_life_sound,
            self.powerup_sound,
            self.shield_break_sound,
            self.ui_click_sound,
            self.ui_nav_sound,
        ):
            snd.set_volume(vol)
        if hasattr(self, "_dash_channel"):
            self._dash_channel.set_volume(vol * 0.55)
        if hasattr(self, "_music"):
            self._music.set_volume(vol * 0.5)

    def _open_display(self, display_index: int | None = None) -> None:
        s = Settings.get()
        self._display_index = current_display_index() if display_index is None else display_index
        self._display_index = max(0, min(self._display_index, pygame.display.get_num_displays() - 1))
        remember_display(self._display_index)
        self._native_mode = get_native_resolution(self._display_index)
        if s.auto_resolution:
            size = self._native_mode if s.fullscreen else choose_window_size(self._native_mode)
        else:
            size = s.resolution
        flags = pygame.SCALED | (pygame.FULLSCREEN if s.fullscreen else 0)
        self.screen = pygame.display.set_mode(size, flags, display=self._display_index, vsync=0)
        self._disp_w, self._disp_h = self.screen.get_size()
        self._viewport = fit_viewport((self._disp_w, self._disp_h))

    def _apply_resolution(self, display_index: int | None = None) -> None:
        """Recreate the window on its current monitor and preserve game proportions."""
        self._open_display(display_index)
        self._update_screen_layouts()

    @property
    def current_fps(self) -> float:
        return self._frame_limiter.fps

    def _present(self, frame: pygame.Surface | None = None) -> None:
        """Render the active canvas at its true ratio, with clipped camera shake."""
        frame = self._canvas if frame is None else frame
        self._viewport = fit_viewport((self._disp_w, self._disp_h), frame.get_size())
        view = self._viewport
        scaled = frame if view.size == frame.get_size() else pygame.transform.smoothscale(frame, view.size)
        self.screen.fill((0, 0, 0))
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(view)
        self.screen.blit(
            scaled,
            (
                view.x + round(self._shake_ox * view.w / frame.get_width()),
                view.y + round(self._shake_oy * view.h / frame.get_height()),
            ),
        )
        self.screen.set_clip(previous_clip)
        pygame.display.update()

    def _toggle_fullscreen(self) -> None:
        s = Settings.get()
        s.fullscreen = not s.fullscreen
        s.save()
        self._apply_resolution()

    def _fade_to(self, next_state: GameState) -> None:
        """Start a fade-out → switch state → fade-in transition."""
        if self._fade_next_state is not None:
            return  # already fading
        self._fade_next_state = next_state
        self._fade_dir = 1  # fade out first

    # ------------------------------------------------------------------
    # Coordinate helpers (display-space → active logical canvas)
    # ------------------------------------------------------------------

    def _lpos(self, pos: tuple[int, int]) -> tuple[int, int]:
        world = self.state in (GameState.PLAYING, GameState.DYING, GameState.PAUSED)
        size = self._canvas.get_size() if world else (_LOGICAL_W, _LOGICAL_H)
        view = fit_viewport((self._disp_w, self._disp_h), size)
        if not view.collidepoint(pos):
            return (-1, -1)
        return (int((pos[0] - view.x) * size[0] / view.w), int((pos[1] - view.y) * size[1] / view.h))

    def _lmouse(self) -> tuple[int, int]:
        return self._lpos(pygame.mouse.get_pos())

    # ------------------------------------------------------------------
    # Game initialisation
    # ------------------------------------------------------------------

    def _init_game(self) -> None:
        """Reset all gameplay state for a new round."""
        self._run_aspect = Settings.get().aspect_ratio
        size = game_canvas_size(self._run_aspect, self._native_mode)
        self.screen_width, self.screen_height = size
        config.SCREEN_WIDTH, config.SCREEN_HEIGHT = size
        self._canvas = pygame.Surface(size)
        self.background = StarBackground(*size)
        self._run_elapsed = 0.0
        self.game_score = 0
        self.lives = Settings.get().starting_lives
        self.flash_timer = 0
        self.wave = 0
        self.fighter = Fighter(ship=self._selected_ship)
        self.balls = pygame.sprite.Group()
        self._ball_queue = []
        self.explosions = pygame.sprite.Group()
        self.alien_bullets = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.boss = None
        self.mini_boss = None
        self._boss_warning_timer = 0.0  # countdown before boss spawns
        self._pending_boss_wave = 0  # wave number waiting for warning to end
        self._effects.reset()
        self._wave_banner_timer = 0.0
        self._triple_shot_timer = 0.0
        self._shield_active = False
        self._slow_time_timer = 0.0
        self._death_timer = 0.0  # countdown for DYING state
        self._start_wave(1)

    def _start_wave(self, wave_num: int, extra_delay: float = 0.0) -> None:
        self.wave = wave_num
        self.alien_bullets = pygame.sprite.Group()
        # Pickups remain collectible between waves; _init_game clears them on restart.
        self._wave_banner_timer = 2.8 + extra_delay
        self.mini_boss = None

        if wave_num % 5 == 0:
            # Full boss — show warning first, spawn after delay
            self.boss = None
            self.aliens = pygame.sprite.Group()
            self._boss_warning_timer = 2.8
            self._pending_boss_wave = wave_num
        elif wave_num % 5 == 3 and wave_num >= 3:
            # Mini-boss wave — do NOT instantiate MiniBoss here; the warning
            # timer callback below creates it so it only spawns once.
            self.boss = None
            self.mini_boss = None
            self.aliens = pygame.sprite.Group()
            self._boss_warning_timer = 1.2
            self._pending_boss_wave = -wave_num  # negative = mini-boss signal
        else:
            self.boss = None
            self.aliens = pygame.sprite.Group(*self._make_wave_aliens(wave_num))

    def _make_wave_aliens(self, wave_num: int) -> list[Alien]:
        s = Settings.get()
        count = s.alien_count + (wave_num - 1)
        speed = s.alien_speed_mult * (1.0 + (wave_num - 1) * 0.15)
        speed = min(speed, s.alien_speed_mult * 4.0)
        aliens = []
        for i in range(count):
            roll = random.random()
            if wave_num >= 4 and roll < 0.15:
                cls = ShooterAlien
            elif wave_num >= 3 and roll < 0.30:
                cls = ZigzagAlien
            elif wave_num >= 2 and roll < 0.30:
                cls = ArmoredAlien
            else:
                cls = Alien
            aliens.append(cls(index=i, speed_mult=speed))
        return aliens

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Process input, build a frame, apply its transition and present it."""
        while True:
            dt = min(self._frame_limiter.tick(Settings.get().fps), 0.1)
            self._process_events()
            frame = self._advance_frame(dt)
            self._update_fade(dt, frame)
            self._present(frame)

    def _process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            self._handle_event(event)

    def _advance_frame(self, dt: float) -> pygame.Surface:
        """Advance the active screen and paint its world or menu canvas."""
        world = self.state in (GameState.PLAYING, GameState.PAUSED, GameState.DYING)
        frame = self._canvas if world else self._menu_canvas
        self.background.update(dt)
        self._menu_background.update(dt)
        if not world:
            self._menu_background.draw(frame)
            self._shake_ox = self._shake_oy = 0

        if self.state == GameState.LOADING:
            self._loading_timer -= dt
            self._draw_loading()
            if self._loading_timer <= 0:
                self.state = GameState.START
        elif self.state == GameState.PLAYING:
            self._update(dt)
            self._draw()
        elif self.state == GameState.DYING:
            self._update_dying(dt)
            self._draw()
        elif self.state == GameState.PAUSED:
            self._draw()
            self._pause.draw(frame, self)
        else:
            screen = self._menu_screen()
            if screen:
                screen.draw(frame, self._menu_context)
        return frame

    def _update_fade(self, dt: float, frame: pygame.Surface) -> None:
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
            fade_surf = pygame.Surface(frame.get_size())
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(int(self._fade_alpha))
            frame.blit(fade_surf, (0, 0))

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _handle_screen_action(self, action: str | None) -> None:
        if not action or self._fade_next_state is not None:
            return
        if action == "quit":
            sys.exit()
        if action == "leaderboard":
            self._leaderboard_return = self.state
            self._leaderboard.page = 0
            self._fade_to(GameState.LEADERBOARD)
            return
        if self.state == GameState.LEADERBOARD and action == "back":
            self._fade_to(self._leaderboard_return)
            return
        if self.state == GameState.START:
            target = {
                "play": GameState.SHIP_SELECT,
                "settings": GameState.SETTINGS,
                "controls": GameState.CONTROLS,
            }.get(action)
            if target:
                self._fade_to(target)
        elif self.state == GameState.SHIP_SELECT:
            if action == "confirm":
                self._confirm_ship()
            elif action == "back":
                self._fade_to(GameState.START)
        elif self.state == GameState.CONTROLS and action == "back":
            self._fade_to(GameState.START)
        elif self.state == GameState.SETTINGS:
            self._settings.handle_mouse_up(self)
            if action == "back":
                self._fade_to(GameState.START)
            elif action == "fullscreen":
                self._toggle_fullscreen()
            elif action == "resolution":
                self._apply_resolution()
        elif self.state in (GameState.GAME_OVER, GameState.PAUSED):
            self._pause.handle_mouse_up(self)
            if action == "resume":
                self.state = GameState.PLAYING
                self._music.resume()
            elif action in ("retry", "restart", "menu"):
                self._init_game()
                if action == "menu":
                    self._music.play_menu()
                    self._fade_to(GameState.START)
                else:
                    self._music.play_battle()
                    self._music.resume()
                    self._fade_to(GameState.PLAYING)

    def _menu_screen(self):
        return {
            GameState.START: self._start_screen,
            GameState.SHIP_SELECT: self._ship_screen,
            GameState.SETTINGS: self._settings,
            GameState.CONTROLS: self._controls,
            GameState.PAUSED: self._pause,
            GameState.GAME_OVER: self._gameover,
            GameState.LEADERBOARD: self._leaderboard,
        }.get(self.state)

    def _handle_event(self, event: pygame.event.Event) -> None:
        """Route one SDL event; each handler owns one input or display concern."""
        if event.type == pygame.MOUSEWHEEL and self.state == GameState.LEADERBOARD:
            self._leaderboard.handle_wheel(event, self._menu_context)
        elif event.type == pygame.WINDOWDISPLAYCHANGED:
            self._handle_monitor_change(event)
        elif event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)
        elif event.type == pygame.KEYUP and self.state in (GameState.PLAYING, GameState.PAUSED):
            self._handle_keyup(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_pointer_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._settings.handle_mouse_up(self)
            self._pause.handle_mouse_up(self)

    def _handle_monitor_change(self, event: pygame.event.Event) -> None:
        index = getattr(event, "display_index", current_display_index())
        index = max(0, min(index, pygame.display.get_num_displays() - 1))
        remember_display(index)
        if Settings.get().auto_resolution and (
            index != self._display_index or get_native_resolution(index) != self._native_mode
        ):
            self._apply_resolution(index)
        else:
            self._display_index = index
            self._native_mode = get_native_resolution(index)
        return

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_F11:
            self._toggle_fullscreen()
            return
        if self.state == GameState.PLAYING:
            if key in (pygame.K_LEFT, pygame.K_a):
                self.fighter.move_left()
            if key in (pygame.K_RIGHT, pygame.K_d):
                self.fighter.move_right()
            if key in (pygame.K_UP, pygame.K_w):
                self.fighter.move_up()
            if key in (pygame.K_DOWN, pygame.K_s):
                self.fighter.move_down()
            if key == pygame.K_SPACE:
                self._shoot()
            if key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                if self.fighter.dash_cooldown_ratio == 0:
                    self._dash_channel.play(self._dash_snd_raw)
                self.fighter.dash()
            if key in (pygame.K_p, pygame.K_ESCAPE):
                self._pause.focus.select(1)
                self.state = GameState.PAUSED
                self._music.pause()
        else:
            screen = self._menu_screen()
            if screen:
                self._handle_screen_action(
                    screen.handle_key(key, self if self.state == GameState.PAUSED else self._menu_context)
                )

    def _handle_keyup(self, key: int) -> None:
        if key in (pygame.K_LEFT, pygame.K_a):
            self.fighter.is_moving_left = False
        if key in (pygame.K_RIGHT, pygame.K_d):
            self.fighter.is_moving_right = False
        if key in (pygame.K_UP, pygame.K_w):
            self.fighter.is_moving_up = False
        if key in (pygame.K_DOWN, pygame.K_s):
            self.fighter.is_moving_down = False

    def _handle_click(self, display_pos: tuple[int, int]) -> None:
        pos = self._lpos(display_pos)
        if pos == (-1, -1):
            return
        if self.state == GameState.PLAYING:
            self._shoot()
        else:
            screen = self._menu_screen()
            if screen:
                self._handle_screen_action(
                    screen.handle_click(pos, self if self.state == GameState.PAUSED else self._menu_context)
                )

    def _handle_pointer_motion(self, display_pos: tuple[int, int]) -> None:
        pos = self._lpos(display_pos)
        if pos != (-1, -1):
            if self.state == GameState.SETTINGS:
                self._settings.handle_motion(pos, self._menu_context)
            elif self.state == GameState.PAUSED:
                self._pause.handle_motion(pos, self)

    # ------------------------------------------------------------------
    # Ship selection
    # ------------------------------------------------------------------

    def _confirm_ship(self) -> None:
        self._selected_ship = SHIPS[self._ship_cursor]
        self._init_game()
        self._music.play_battle()
        self._fade_to(GameState.PLAYING)

    # ------------------------------------------------------------------
    # Shooting
    # ------------------------------------------------------------------

    def _shoot(self) -> None:
        combat.shoot(self)

    # ------------------------------------------------------------------
    # Update (gameplay)
    # ------------------------------------------------------------------

    def _update(self, dt: float) -> None:
        combat.update(self, dt)

    def _update_boss(self, dt: float) -> None:
        combat.update_boss(self, dt)

    def _update_mini_boss(self, dt: float) -> None:
        combat.update_mini_boss(self, dt)

    def _maybe_drop_powerup(self, cx: int, cy: int) -> None:
        combat.maybe_drop_powerup(self, cx, cy)

    def _take_damage(self) -> None:
        combat.take_damage(self)

    # ------------------------------------------------------------------
    # Draw (gameplay only — menu screens draw themselves)
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        rendering.draw_world(self)
        if self.flash_timer > 0:
            self.flash_timer -= 1
        self._shake_ox, self._shake_oy = self._effects.advance_shake()

    # ------------------------------------------------------------------
    # Engine trail
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Death animation state
    # ------------------------------------------------------------------

    def _update_dying(self, dt: float) -> None:
        """Run explosions/particles during death; then fade to GAME_OVER."""
        self.explosions.update(dt)
        self._effects.update(dt)
        if self._effects.shake_frames > 0:
            self._effects.shake_frames -= 1
        self._death_timer -= dt
        if self._death_timer <= 0:
            self._music.stop()
            self._fade_to(GameState.GAME_OVER)

    # ------------------------------------------------------------------
    # Loading screen
    # ------------------------------------------------------------------

    def _draw_loading(self) -> None:
        rendering.draw_loading(self)
