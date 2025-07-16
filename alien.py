import pygame
from constants import SCREEN_WIDTH, ALIAN_STEP
from random import randint

class Alian:
    def __init__(self):
        self.image = pygame.image.load('images/alian.png')
        self.width, self.height = self.image.get_size()
        self.x, self.y = randint(0, SCREEN_WIDTH - self.width), 0
        self.step = ALIAN_STEP
        self.speed = self.step

    def update_position(self):
        self.y += self.speed

    def increase_speed(self):
        self.speed += self.step / 2

    def reset(self):
        self.increase_speed()
        self.x, self.y = randint(0, SCREEN_WIDTH - self.width), 0

    def has_reached_fighter(self, fighter):
        return self.y + self.height > fighter.y