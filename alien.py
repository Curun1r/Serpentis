import pygame
from pygame.sprite import Sprite
from constants import SCREEN_WIDTH, ALIEN_SPEED, ALIEN_SCALE
from random import randint


class Alien(Sprite):
    def __init__(self, index=0):
        super().__init__()

        # Load and scale the alien image
        raw_image = pygame.image.load('image/alien.png')
        w, h = raw_image.get_size()
        self.image = pygame.transform.scale(raw_image, (int(w * ALIEN_SCALE), int(h * ALIEN_SCALE)))
        self.width, self.height = self.image.get_size()

        # Stagger starting positions vertically so aliens don't cluster together
        self.x = float(randint(0, SCREEN_WIDTH - self.width))
        self.y = float(-index * 250)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        self.base_speed = float(ALIEN_SPEED)
        self.speed_y = self.base_speed

        # Alternate horizontal direction based on index (even = right, odd = left)
        self.speed_x = self.base_speed * 0.8 * (1 if index % 2 == 0 else -1)

    def update(self, dt):
        self.y += self.speed_y * dt
        self.x += self.speed_x * dt

        # Bounce off screen edges
        if self.x <= 0 or self.x >= SCREEN_WIDTH - self.width:
            self.speed_x *= -1

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def increase_speed(self):
        # Increase vertical speed and preserve horizontal direction when speeding up
        self.speed_y += self.base_speed * 0.3
        direction = 1 if self.speed_x > 0 else -1
        self.speed_x += direction * self.base_speed * 0.2

    def reset(self):
        # Speed up and reposition at the top of the screen
        self.increase_speed()
        self.x = float(randint(0, SCREEN_WIDTH - self.width))
        self.y = 0.0
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def has_reached_fighter(self, fighter):
        return self.rect.bottom > fighter.rect.top
