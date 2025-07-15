import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FIGHTER_STEP

class Fighter:
    def __init__(self):
        self.image = pygame.image.load('image/fighter.png')
        self.width, self.height = self.image.get_size()
        self.x, self.y = SCREEN_WIDTH / 2 - self.width / 2, SCREEN_HEIGHT - self.height
        self.step = FIGHTER_STEP
        self.is_moving_left, self.is_moving_right = False, False

    def move_left(self):
        self.is_moving_left = True

    def move_right(self):
        self.is_moving_right = True

    def stop_moving(self):
        self.is_moving_left = False
        self.is_moving_right = False

    def update_position(self):
        if self.is_moving_left and self.x >= self.step:
            self.x -= self.step

        if self.is_moving_right and self.x <= SCREEN_WIDTH - self.width - self.step:
            self.x += self.step