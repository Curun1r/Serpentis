import pygame
from pygame.sprite import Sprite
from config import SCREEN_HEIGHT, SCREEN_WIDTH, FIGHTER_SPEED, FIGHTER_SCALE
from assets import Assets


class Fighter(Sprite):
    def __init__(self):
        super().__init__()

        # Fetch from cache — avoids reloading if Fighter is recreated each round
        raw_image = Assets.get_image('image/fighter.png')
        w, h = raw_image.get_size()
        self.image = pygame.transform.scale(raw_image, (int(w * FIGHTER_SCALE), int(h * FIGHTER_SCALE)))
        self.width, self.height = self.image.get_size()

        # Use float coordinates for smooth sub-pixel movement, sync to rect for rendering
        self.x = float(SCREEN_WIDTH / 2 - self.width / 2)
        self.y = float(SCREEN_HEIGHT - self.height)
        self.rect = self.image.get_rect(x=int(self.x), y=int(self.y))

        self.speed = FIGHTER_SPEED
        self.is_moving_left = self.is_moving_right = False
        self.is_moving_up = self.is_moving_down = False

    def update(self, dt):
        # Move horizontally within screen bounds
        if self.is_moving_left and self.x > 0:
            self.x -= self.speed * dt
        if self.is_moving_right and self.x < SCREEN_WIDTH - self.width:
            self.x += self.speed * dt

        # Restrict vertical movement to the bottom half of the screen
        if self.is_moving_up and self.y > SCREEN_HEIGHT // 2:
            self.y -= self.speed * dt
        if self.is_moving_down and self.y < SCREEN_HEIGHT - self.height:
            self.y += self.speed * dt

        # Sync float position to rect for collision and rendering
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def move_left(self): self.is_moving_left = True
    def move_right(self): self.is_moving_right = True
    def move_up(self): self.is_moving_up = True
    def move_down(self): self.is_moving_down = True

    def stop_moving(self):
        self.is_moving_left = self.is_moving_right = False
        self.is_moving_up = self.is_moving_down = False
