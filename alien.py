import pygame
from constants import SCREEN_WIDTH, ALIEN_STEP
from random import randint

class Alien:
    def __init__(self):
        self.image = pygame.image.load('image/alien.png')
        self.width, self.height = self.image.get_size()
        self.x, self.y = randint(0, SCREEN_WIDTH - self.width), 0
        self.step = ALIEN_STEP
        self.speed_y = self.step
        self.speed_x = self.step * 0.8

    def update_position(self):
        self.y += self.speed_y
        self.x += self.speed_x
        if self.x <= 0 or self.x >= SCREEN_WIDTH - self.width:
            self.speed_x *= -1

    def increase_speed(self):
        self.speed_y += self.step / 2
        self.speed_x += self.step / 4

    def reset(self):
        self.increase_speed()
        self.x, self.y = randint(0, SCREEN_WIDTH - self.width), 0

    def has_reached_fighter(self, fighter):
        return self.y + self.height > fighter.y