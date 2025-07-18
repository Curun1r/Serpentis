import pygame
import sys
from fighter import Fighter
from alien import Alien
from ball import Ball
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_BACKGROUND_COLOR, GAME_CAPTION


class Game:
    def __init__(self):
        pygame.display.set_caption(GAME_CAPTION)
        self.screen_width, self.screen_height = SCREEN_WIDTH, SCREEN_HEIGHT
        self.screen_background_color = SCREEN_BACKGROUND_COLOR
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.game_font = pygame.font.Font(None, 30)
        self.game_score = 0
        self.fighter = Fighter()
        self.alien = Alien()
        self.ball = Ball(self.fighter)

        self.game_is_running = True

    def run(self):
        while self.game_is_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                self.handle_key_events(event)

            self.update_game_state()
            self.draw_screen()

        self.show_game_over()

    def handle_key_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.fighter.move_left()
            if event.key == pygame.K_RIGHT:
                self.fighter.move_right()
            if event.key == pygame.K_SPACE:
                self.ball.fire()

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                self.fighter.stop_moving()

    def update_game_state(self):
        self.fighter.update_position()
        self.alien.update_position()
        self.ball.update_position()

        if self.ball.is_out_of_screen():
            self.ball.reset()

        if self.ball.is_collision(self.alien):
            self.ball.reset()
            self.alien.reset()
            self.game_score += 1

        if self.alien.has_reached_fighter(self.fighter):
            self.game_is_running = False

    def draw_screen(self):
        self.screen.fill(self.screen_background_color)
        self.screen.blit(self.fighter.image, (self.fighter.x, self.fighter.y))
        self.screen.blit(self.alien.image, (self.alien.x, self.alien.y))
        if self.ball.was_fired:
            self.screen.blit(self.alien.image, (self.alien.x, self.alien.y))
        self.show_game_score()
        pygame.display.update()

    def show_game_score(self):
        game_score_text = self.game_font.render(f"Your Score is {self.game_score}", True, 'white')
        self.screen.blit(game_score_text, (20, 20))

    def show_game_over(self):
        game_over_text = self.game_font.render(f"Game Over", True, 'olive')
        game_over_rectangle = game_over_text.get_rect()
        game_over_rectangle.center = (self.screen_width / 2, self.screen.height / 2)
        self.screen.blit(game_over_text, game_over_rectangle)
        pygame.display.update()
        pygame.time.wait(5000)