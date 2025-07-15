import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FIGHTER_STEP

class Fighter:
    def __init__(self):
        self.image = pygame.image.load('image/fighter.png')
        self.width, self.height = self.image.get_size()
        self.x, self.y = SCREEN_WIDTH / 2 - self.width / 2, SCREEN_HEIGHT - self.height
        self.step = FIGHTER_STEP
        self.is_moving_left, self.is_moving_right = False, False