import pygame
import sys
from enum import Enum
from fighter import Fighter
from alien import Alien
from ball import Ball
from config import SCREEN_WIDTH, SCREEN_HEIGHT, GAME_CAPTION, ALIEN_COUNT, STARTING_LIVES
from assets import Assets
from score_manager import ScoreManager


class GameState(Enum):
    """All possible game states."""
    START = "start"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"


class Game:
    def __init__(self):
        pygame.display.set_caption(GAME_CAPTION)
        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.game_font = pygame.font.Font(None, 36)
        self.clock = pygame.time.Clock()

        # Generate sounds via Assets cache — safe to call multiple times
        self.shoot_sound = Assets.get_sound('shoot', frequency=520, duration=0.08)
        self.hit_sound = Assets.get_sound('hit', frequency=220, duration=0.25)
        self.lose_life_sound = Assets.get_sound('lose_life', frequency=110, duration=0.5)

        # Load starfield background via Assets cache
        self.background = Assets.get_image('image/background.png').convert()

        # Load best score from previous session, falls back to 0 if no file exists
        self.best_score = ScoreManager.load()
        self.state = GameState.START

        # Game over screen button rects defined once and reused every round
        self.try_again_rect = pygame.Rect(self.screen_width / 2 - 100, self.screen_height / 2 + 20, 200, 50)
        self.quit_rect = pygame.Rect(self.screen_width / 2 - 100, self.screen_height / 2 + 90, 200, 50)

        self._init_game()

    def _init_game(self):
        """Reset all game state for a new round."""
        self.game_score = 0
        self.lives = STARTING_LIVES
        self.flash_timer = 0
        self.fighter = Fighter()
        self.aliens = pygame.sprite.Group(*[Alien(index=i) for i in range(ALIEN_COUNT)])
        self.balls = pygame.sprite.Group()

    def run(self):
        """Main game loop — runs forever, switching behavior based on current state."""
        while True:
            # dt = seconds elapsed since last frame, used for frame-rate-independent movement
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._handle_event(event)

            self.screen.blit(self.background, (0, 0))

            if self.state == GameState.START:
                self._draw_start_screen()
            elif self.state == GameState.PLAYING:
                self._update(dt)
                self._draw()
            elif self.state == GameState.PAUSED:
                # Draw the game underneath the pause overlay
                self._draw()
                self._draw_pause_overlay()
            elif self.state == GameState.GAME_OVER:
                self._draw_game_over_screen()

            pygame.display.update()

    def _handle_event(self, event):
        """Route input events based on the current game state."""
        if event.type == pygame.KEYDOWN:
            if self.state == GameState.START:
                if event.key == pygame.K_SPACE:
                    self.state = GameState.PLAYING

            elif self.state == GameState.PLAYING:
                # Arrow keys and WASD both control the fighter
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.fighter.move_left()
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.fighter.move_right()
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.fighter.move_up()
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    self.fighter.move_down()
                if event.key == pygame.K_SPACE:
                    self.balls.add(Ball(self.fighter))
                    self.shoot_sound.play()
                if event.key == pygame.K_p:
                    self.state = GameState.PAUSED

            elif self.state == GameState.PAUSED:
                if event.key == pygame.K_p:
                    self.state = GameState.PLAYING

        if event.type == pygame.KEYUP:
            if self.state == GameState.PLAYING:
                # Stop movement only for the released key, not all directions
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.fighter.is_moving_left = False
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.fighter.is_moving_right = False
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.fighter.is_moving_up = False
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    self.fighter.is_moving_down = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.state == GameState.GAME_OVER:
                if self.try_again_rect.collidepoint(event.pos):
                    self._init_game()
                    self.state = GameState.PLAYING
                if self.quit_rect.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

    def _update(self, dt):
        """Update all game objects and check for collisions."""
        self.fighter.update(dt)
        self.aliens.update(dt)
        self.balls.update(dt)

        # Remove balls that have left the top of the screen
        for ball in list(self.balls):
            if ball.is_out_of_screen():
                ball.kill()

        # Check ball-alien collisions — True removes the ball from its group on hit
        hits = pygame.sprite.groupcollide(self.balls, self.aliens, True, False)
        for aliens_hit in hits.values():
            for alien in aliens_hit:
                alien.reset()
                self.game_score += 1
                if self.game_score > self.best_score:
                    self.best_score = self.game_score
                    ScoreManager.save(self.best_score)
                self.hit_sound.play()

        # Check if any alien has reached the fighter
        for alien in list(self.aliens):
            if alien.has_reached_fighter(self.fighter):
                self.lives -= 1
                self.flash_timer = 20
                alien.reset()
                self.lose_life_sound.play()
                if self.lives <= 0:
                    self.state = GameState.GAME_OVER

    def _draw(self):
        """Draw all game objects and effects."""
        self.screen.blit(self.fighter.image, self.fighter.rect)
        self.aliens.draw(self.screen)
        self.balls.draw(self.screen)

        # Red screen flash when a life is lost, fades out over 20 frames
        if self.flash_timer > 0:
            flash_surface = pygame.Surface((self.screen_width, self.screen_height))
            flash_surface.fill((255, 0, 0))
            flash_surface.set_alpha(self.flash_timer * 6)
            self.screen.blit(flash_surface, (0, 0))
            self.flash_timer -= 1

        self._draw_hud()

    def _draw_hud(self):
        """Draw the heads-up display: score, best score, and remaining lives."""
        score_text = self.game_font.render(
            f"Score: {self.game_score}   Best: {self.best_score}   Lives: {'♥ ' * self.lives}",
            True, 'white'
        )
        self.screen.blit(score_text, (20, 20))

    def _draw_start_screen(self):
        """Draw the initial start screen with title and prompt."""
        title_text = self.game_font.render("Space Shooter", True, 'white')
        title_rect = title_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2 - 40))
        self.screen.blit(title_text, title_rect)

        start_text = self.game_font.render("Press SPACE to start", True, 'yellow')
        start_rect = start_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2 + 20))
        self.screen.blit(start_text, start_rect)

    def _draw_pause_overlay(self):
        """Draw the pause message over the frozen game screen."""
        pause_text = self.game_font.render("PAUSED — press P to continue", True, 'yellow')
        pause_rect = pause_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2))
        self.screen.blit(pause_text, pause_rect)

    def _draw_game_over_screen(self):
        """Draw the game over screen with final score and action buttons."""
        game_over_text = self.game_font.render("Game Over", True, 'white')
        game_over_rect = game_over_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2 - 80))
        self.screen.blit(game_over_text, game_over_rect)

        score_text = self.game_font.render(f"Score: {self.game_score}", True, 'white')
        score_rect = score_text.get_rect(center=(self.screen_width / 2, self.screen_height / 2 - 40))
        self.screen.blit(score_text, score_rect)

        pygame.draw.rect(self.screen, 'green', self.try_again_rect, border_radius=8)
        try_again_text = self.game_font.render("Try Again", True, 'white')
        self.screen.blit(try_again_text, try_again_text.get_rect(center=self.try_again_rect.center))

        pygame.draw.rect(self.screen, (180, 50, 50), self.quit_rect, border_radius=8)
        quit_text = self.game_font.render("Quit", True, 'white')
        self.screen.blit(quit_text, quit_text.get_rect(center=self.quit_rect.center))

