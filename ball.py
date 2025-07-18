import pygame
from constants import BALL_STEP

class Ball:
    def __init__(self, fighter):
        self.image = pygame.image.load('image/ball.png')
        self.width, self.height = self.image.get_size()
        self.x, self.y = 0, 0
        self.step = BALL_STEP
        self.was_fired = False
        self.fighter = fighter

    def fire(self):
        self.was_fired = True
        self.x = self.fighter.x + self.fighter.width / 2 - self.width / 2
        self.y = self.fighter.y - self.fighter.height

    def update_position(self):
        if self.was_fired:
            self.y -=self.step

    def is_out_of_screen(self):
        return self.y > self.height < 0

    def reset(self):
        self.was_fired = False

    def is_collision(self, alien):
        return (
            alien.x < self.x < alien.x + alien.width - self.width and
            alien.y < self.y < alien.y + alien.height - self.height
        )