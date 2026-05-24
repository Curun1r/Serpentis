import math
import pygame
import config
from pygame.sprite import Sprite
from config import BALL_SPEED, BALL_SCALE
from assets import Assets


class Ball(Sprite):
    def __init__(self, fighter, angle_deg: float = 0.0):
        super().__init__()

        # Fetch from cache — every shot reuses the same source surface
        raw_image = Assets.get_image('image/ball.png')
        w, h = raw_image.get_size()
        self.image = pygame.transform.scale(raw_image, (int(w * BALL_SCALE), int(h * BALL_SCALE)))
        self.width, self.height = self.image.get_size()

        # Velocity components — angle 0 = straight up, positive = right
        angle_rad = math.radians(angle_deg)
        speed     = BALL_SPEED
        self.vx   =  math.sin(angle_rad) * speed
        self.vy   = -math.cos(angle_rad) * speed   # negative = upward

        # Spawn centred above the fighter
        self.x = float(fighter.x + fighter.width  / 2 - self.width  / 2)
        self.y = float(fighter.y - self.height)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def is_out_of_screen(self):
        return (self.rect.bottom < 0 or
                self.rect.right  < 0 or
                self.rect.left   > config.SCREEN_WIDTH)
