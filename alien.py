import pygame
import config
from pygame.sprite import Sprite
from config import ALIEN_SPEED, ALIEN_SCALE, ALIEN_STAGGER
from random import randint
from assets import Assets


class Alien(Sprite):
    def __init__(self, index=0, speed_mult=1.0):
        super().__init__()

        # Fetch from cache — all aliens share the same source surface
        raw_image = Assets.get_image('image/alien.png')
        w, h = raw_image.get_size()
        self.image = pygame.transform.scale(raw_image, (int(w * ALIEN_SCALE), int(h * ALIEN_SCALE)))
        self.width, self.height = self.image.get_size()

        # Stagger starting positions vertically so aliens don't cluster together
        self.x = float(randint(0, config.SCREEN_WIDTH - self.width))
        self.y = float(-index * ALIEN_STAGGER)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        # speed_mult scales base speed for difficulty (0.65 easy / 1.0 normal / 1.6 hard)
        self.base_speed = float(ALIEN_SPEED) * speed_mult
        self.speed_y = self.base_speed

        # Alternate horizontal direction based on index (even = right, odd = left)
        self.speed_x = self.base_speed * 0.8 * (1 if index % 2 == 0 else -1)

    def update(self, dt):
        self.y += self.speed_y * dt
        self.x += self.speed_x * dt

        # Bounce off screen edges and clamp position so alien never goes off-screen
        if self.x <= 0:
            self.x = 0.0
            self.speed_x = abs(self.speed_x)
        elif self.x >= config.SCREEN_WIDTH - self.width:
            self.x = float(config.SCREEN_WIDTH - self.width)
            self.speed_x = -abs(self.speed_x)

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def increase_speed(self):
        """Speed up after each reset — preserves horizontal direction."""
        self.speed_y += self.base_speed * 0.3
        direction = 1 if self.speed_x > 0 else -1
        self.speed_x += direction * self.base_speed * 0.2

    def reset(self):
        """Speed up and reposition at the top of the screen."""
        self.increase_speed()
        self.x = float(randint(0, config.SCREEN_WIDTH - self.width))
        self.y = 0.0
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def has_reached_fighter(self, fighter):
        return self.rect.colliderect(fighter.rect)
