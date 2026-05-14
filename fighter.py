import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, FIGHTER_STEP, FIGHTER_SCALE


class Fighter:
    def __init__(self):
        raw_image = pygame.image.load('image/fighter.png')
        w, h = raw_image.get_size()
        self.image = pygame.transform.scale(raw_image, (int(w * FIGHTER_SCALE), int(h * FIGHTER_SCALE)))
        self.width, self.height = self.image.get_size()
        self.x, self.y = SCREEN_WIDTH / 2 - self.width / 2, SCREEN_HEIGHT - self.height
        self.step = FIGHTER_STEP
        self.is_moving_left, self.is_moving_right = False, False
        self.is_moving_up, self.is_moving_down = False, False

    def move_left(self):
        self.is_moving_left = True

    def move_right(self):
        self.is_moving_right = True

    def move_up(self):
        self.is_moving_up = True

    def move_down(self):
        self.is_moving_down = True

    def stop_moving(self):
        self.is_moving_left = False
        self.is_moving_right = False
        self.is_moving_up = False
        self.is_moving_down = False

    def update_position(self):
        if self.is_moving_left and self.x >= self.step:
            self.x -= self.step

        if self.is_moving_right and self.x <= SCREEN_WIDTH - self.width - self.step:
            self.x += self.step

        if self.is_moving_up and self.y >= SCREEN_HEIGHT // 2:
            self.y -= self.step

        if self.is_moving_down and self.y <= SCREEN_HEIGHT - self.height - self.step:
            self.y += self.step