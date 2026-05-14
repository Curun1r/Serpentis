import pygame
from constants import SCREEN_WIDTH, ALIEN_STEP, ALIEN_SCALE
from random import randint

class Alien:
    def __init__(self, index=0):
        raw_image = pygame.image.load('image/alien.png')
        w, h = raw_image.get_size()
        self.image = pygame.transform.scale(raw_image, (int(w * ALIEN_SCALE), int(h * ALIEN_SCALE)))
        self.width, self.height = self.image.get_size()
        self.x = randint(0, SCREEN_WIDTH - self.width)
        self.y = -index * 250
        self.step = ALIEN_STEP
        self.speed_y = self.step
        self.speed_x = self.step * 0.8 * (1 if index % 2 == 0 else -1)

    def update_position(self):
        self.y += self.speed_y
        self.x += self.speed_x
        if self.x <= 0 or self.x >= SCREEN_WIDTH - self.width:
            self.speed_x *= -1

    def increase_speed(self):
        self.speed_y += self.step / 2
        direction = 1 if self.speed_x > 0 else -1
        self.speed_x += direction * self.step / 4

    def reset(self):
        self.increase_speed()
        self.x, self.y = randint(0, SCREEN_WIDTH - self.width), 0

    def has_reached_fighter(self, fighter):
        return self.y + self.height > fighter.y