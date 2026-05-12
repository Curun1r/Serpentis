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
        self.best_score = 0
        self.fighter = Fighter()
        self.alien = Alien()
        self.ball = Ball(self.fighter)

        self.game_is_running = True
        self.clock = pygame.time.Clock()

    def run(self):
        self.show_start_screen()
        while self.game_is_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                self.handle_key_events(event)

            self.update_game_state()
            self.draw_screen()
            self.clock.tick(120)

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
            if self.game_score > self.best_score:
                self.best_score = self.game_score

        if self.alien.has_reached_fighter(self.fighter):
            self.game_is_running = False

    def draw_screen(self):
        self.screen.fill(self.screen_background_color)
        self.screen.blit(self.fighter.image, (self.fighter.x, self.fighter.y))
        self.screen.blit(self.alien.image, (self.alien.x, self.alien.y))
        if self.ball.was_fired:
            self.screen.blit(self.ball.image, (self.ball.x, self.ball.y))
        self.show_game_score()
        pygame.display.update()

    def show_game_score(self):
        score_text = self.game_font.render(f"Score: {self.game_score}   Best: {self.best_score}", True, 'white')
        self.screen.blit(score_text, (20, 20))

    def show_game_over(self):
        self.screen.fill(self.screen_background_color)

        game_over_text = self.game_font.render("Game Over", True, 'white')
        game_over_rect = game_over_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2 - 80))
        self.screen.blit(game_over_text, game_over_rect)

        score_text = self.game_font.render(f"Score: {self.game_score}", True, 'white')
        score_rect = score_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2 - 40))
        self.screen.blit(score_text, score_rect)

        try_again_rect = pygame.Rect(self.screen_width / 2 - 100, self.screen_height / 2 + 20, 200, 50)
        pygame.draw.rect(self.screen, 'green', try_again_rect, border_radius=8)
        try_again_text = self.game_font.render("Try Again", True, 'white')
        self.screen.blit(try_again_text, try_again_text.get_rect(center=try_again_rect.center))

        quit_rect = pygame.Rect(self.screen_width / 2 - 100, self.screen_height / 2 + 90, 200, 50)
        pygame.draw.rect(self.screen, (180, 50, 50), quit_rect, border_radius=8)
        quit_text = self.game_font.render("Quit", True, 'white')
        self.screen.blit(quit_text, quit_text.get_rect(center=quit_rect.center))

        pygame.display.update()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if try_again_rect.collidepoint(event.pos):
                        self.reset()
                        return
                    if quit_rect.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()

    def reset(self):
        self.game_score = 0
        self.fighter = Fighter()
        self.alien = Alien()
        self.ball = Ball(self.fighter)
        self.game_is_running = True
        self.run()

    def show_start_screen(self):
        self.screen.fill(self.screen_background_color)

        title_text = self.game_font.render("Space Shooter", True, 'white')
        title_rect = title_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2 - 40))
        self.screen.blit(title_text, title_rect)

        start_text = self.game_font.render("Press SPACE to start", True, 'yellow')
        start_rect = start_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2 + 20))
        self.screen.blit(start_text, start_rect)

        pygame.display.update()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        return