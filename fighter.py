import pygame
import config
from pygame.sprite import Sprite
from config import FIGHTER_SPEED, FIGHTER_SCALE
from assets import Assets

DASH_MULTIPLIER = 4.0   # dash is 4× normal speed
DASH_DURATION   = 0.15  # seconds the dash lasts (baseline)
DASH_COOLDOWN   = 0.8   # seconds before can dash again (baseline)


class Fighter(Sprite):
    def __init__(self, ship=None):
        """Create the player fighter.

        *ship* is an optional ShipConfig that overrides speed, dash timing, and
        firing behaviour.  Pass None (or omit) to use the balanced baseline.
        """
        super().__init__()

        # Fetch from cache — avoids reloading if Fighter is recreated each round
        raw_image = Assets.get_image('image/fighter.png')
        w, h = raw_image.get_size()
        # scale() returns a new surface so we can safely tint without touching the cache
        self.image = pygame.transform.scale(raw_image, (int(w * FIGHTER_SCALE), int(h * FIGHTER_SCALE)))

        # Tint the sprite to match the selected ship's accent colour.
        # BLEND_RGB_MULT multiplies RGB per-pixel — shifts hue without washing out to white.
        # Alpha channel is untouched so transparent areas stay transparent.
        if ship:
            r, g, b = ship.color
            tint_col = (min(255, r + 120), min(255, g + 120), min(255, b + 120))
            self.image.fill(tint_col, special_flags=pygame.BLEND_RGB_MULT)
        self.width, self.height = self.image.get_size()

        # Use float coordinates for smooth sub-pixel movement, sync to rect for rendering
        self.x = float(config.SCREEN_WIDTH / 2 - self.width / 2)
        self.y = float(config.SCREEN_HEIGHT - self.height)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        # Apply ship-specific multipliers (defaults to 1× if no ship given)
        speed_m  = ship.speed_mult         if ship else 1.0
        cd_m     = ship.dash_cooldown_mult if ship else 1.0
        dur_m    = ship.dash_duration_mult if ship else 1.0

        self.speed          = FIGHTER_SPEED * speed_m
        self._DASH_COOLDOWN = DASH_COOLDOWN * cd_m
        self._DASH_DURATION = DASH_DURATION * dur_m

        self.is_moving_left = self.is_moving_right = False
        self.is_moving_up = self.is_moving_down = False

        # Dash state
        self._dash_timer    = 0.0   # > 0 while dash is active
        self._dash_cooldown = 0.0   # > 0 while on cooldown
        self._dash_vx       = 0.0   # normalized dash direction X
        self._dash_vy       = 0.0   # normalized dash direction Y

    # ------------------------------------------------------------------
    # Dash
    # ------------------------------------------------------------------

    def dash(self):
        """Start a dash in the current movement direction.
        Ignored if on cooldown or the fighter is not moving."""
        if self._dash_cooldown > 0:
            return

        vx = (-1.0 if self.is_moving_left  else 0.0) + \
             ( 1.0 if self.is_moving_right else 0.0)
        vy = (-1.0 if self.is_moving_up    else 0.0) + \
             ( 1.0 if self.is_moving_down  else 0.0)

        if vx == 0.0 and vy == 0.0:
            return  # not moving — nothing to dash towards

        # Normalize so diagonal dash has the same distance as cardinal
        length = (vx ** 2 + vy ** 2) ** 0.5
        self._dash_vx = vx / length
        self._dash_vy = vy / length
        self._dash_timer    = self._DASH_DURATION
        self._dash_cooldown = self._DASH_COOLDOWN

    @property
    def is_dashing(self) -> bool:
        return self._dash_timer > 0

    @property
    def dash_cooldown_ratio(self) -> float:
        """0.0 = ready, 1.0 = just used. For HUD indicator."""
        return self._dash_cooldown / self._DASH_COOLDOWN

    # ------------------------------------------------------------------
    # Update — reads config.SCREEN_WIDTH/HEIGHT live so resolution changes apply
    # ------------------------------------------------------------------

    def update(self, dt):
        sw = config.SCREEN_WIDTH
        sh = config.SCREEN_HEIGHT

        if self._dash_timer > 0:
            # Dash overrides normal movement — fly in the locked direction
            self._dash_timer -= dt
            dash_speed = self.speed * DASH_MULTIPLIER
            self.x = max(0.0, min(float(sw - self.width),  self.x + self._dash_vx * dash_speed * dt))
            self.y = max(0.0, min(float(sh - self.height), self.y + self._dash_vy * dash_speed * dt))
        else:
            if self._dash_cooldown > 0:
                self._dash_cooldown -= dt

            # Normal movement within screen bounds
            if self.is_moving_left  and self.x > 0:
                self.x -= self.speed * dt
            if self.is_moving_right and self.x < sw - self.width:
                self.x += self.speed * dt
            if self.is_moving_up    and self.y > 0:
                self.y -= self.speed * dt
            if self.is_moving_down  and self.y < sh - self.height:
                self.y += self.speed * dt

        # Sync float position to rect for collision and rendering
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    # ------------------------------------------------------------------
    # Movement helpers
    # ------------------------------------------------------------------

    def move_left(self):  self.is_moving_left  = True
    def move_right(self): self.is_moving_right = True
    def move_up(self):    self.is_moving_up    = True
    def move_down(self):  self.is_moving_down  = True
