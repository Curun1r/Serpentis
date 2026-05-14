import pygame
from constants import BALL_STEP, BALL_SCALE


class Ball:
    def __init__(self, fighter):
        raw_image = pygame.image.load('image/ball.png')
        w, h = raw_image.get_size()
        self.image = pygame.transform.scale(raw_image, (int(w * BALL_SCALE), int(h * BALL_SCALE)))
        self.width, self.height = self.image.get_size()
        self.step = BALL_STEP
        self.x = fighter.x + fighter.width / 2 - self.width / 2
        self.y = fighter.y - self.height

    def update_position(self):
        self.y -= self.step

    def is_out_of_screen(self):
        return self.y < 0

    def is_collision(self, alien):
        return (
            alien.x < self.x < alien.x + alien.width - self.width and
            alien.y < self.y < alien.y + alien.height - self.height
        )
