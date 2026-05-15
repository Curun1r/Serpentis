import pygame
from pygame.sprite import Sprite
from config import BALL_SPEED, BALL_SCALE
from assets import Assets


class Ball(Sprite):
    def __init__(self, fighter):
        super().__init__()

        # Fetch from cache — every shot reuses the same source surface
        raw_image = Assets.get_image('image/ball.png')
        w, h = raw_image.get_size()
        self.image = pygame.transform.scale(raw_image, (int(w * BALL_SCALE), int(h * BALL_SCALE)))
        self.width, self.height = self.image.get_size()

        self.speed = BALL_SPEED

        # Spawn the ball centered above the fighter
        self.x = float(fighter.x + fighter.width / 2 - self.width / 2)
        self.y = float(fighter.y - self.height)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

    def update(self, dt):
        # Move upward each frame
        self.y -= self.speed * dt
        self.rect.y = int(self.y)

    def is_out_of_screen(self):
        return self.rect.top < 0
