import pygame
from fighter import Fighter
from alien import Alian
from ball import Ball
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_BACKGROUND_COLOR, FIGHTER_STEP, GAME_CAPTION


class Game:
    def __init__(self):
        pygame.display.set_caption(GAME_CAPTION)
        self.screen_width, screen_height = SCREEN_WIDTH, SCREEN_HEIGHT
        self.screen_background_color = SCREEN_BACKGROUND_COLOR
        self.creen = pygame.display.set_mode(self.screen_width, screen_height)
        self.game_font = pygame.font.Font(None, 30)
        self.game_score = 0

        self.fighter = Fighter()
        self.alian = Alian()
        self.ball = Ball(self.fighter)

        self.game_is_running = True

