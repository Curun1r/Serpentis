import pygame
import sys
from random import randint

# Initialize Pygame
def run_game():
    pygame.init()

    # Set fonts for the game
    game_font = pygame.font.Font(None, 50)
    second_game_font = pygame.font.Font(None, 25)

    # Set screen dimensions and background color
    screen_width, screen_height = 1000, 650
    screen_fill_color = (32, 52, 71)
    screen = pygame.display.set_mode((screen_width, screen_height))

    pygame.display.set_caption("Awesome Shooter Game")

    # Load fighter image and set initial position
    fighter_image = pygame.image.load('image/fighter.png')
    fighter_width, fighter_height = fighter_image.get_size()
    fighter_x, fighter_y = screen_width / 2 - fighter_width / 2, screen_height - fighter_height
    fighter_is_moving_left, fighter_is_moving_right = False, False
    FIGHTER_STEP = 3.8  # Fighter movement speed

    # Load ball image and set initial state
    ball_image = pygame.image.load('image/ball.png')
    ball_width, ball_height = ball_image.get_size()
    ball_x, ball_y = 0, 0
    ball_was_fired = False
    BALL_STEP = 4.4  # Ball movement speed

    # Load alien image and set random initial position
    alien_image = pygame.image.load('image/alien.png')
    alien_width, alien_height = alien_image.get_size()
    alien_x, alien_y = randint(0, screen_width - alien_width), 0
    alien_speed = 1.6  # Alien movement speed

    game_is_running = True
    game_score = 0

    while game_is_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.KEYDOWN:
                # Move fighter or fire-ball based on key press
                if event.key == pygame.K_LEFT:
                    fighter_is_moving_left = True
                if event.key == pygame.K_RIGHT:
                    fighter_is_moving_right = True
                if event.key == pygame.K_SPACE:
                    ball_was_fired = True
                    ball_x = fighter_x + fighter_width / 2 - ball_width / 2
                    ball_y = fighter_y - ball_height
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    fighter_is_moving_left = False
                if event.key == pygame.K_RIGHT:
                    fighter_is_moving_right = False

        # Ensure fighter stays within screen bounds
        if fighter_is_moving_left and fighter_x >= FIGHTER_STEP:
            fighter_x -= FIGHTER_STEP
        if fighter_is_moving_right and fighter_x <= screen_width - fighter_width - FIGHTER_STEP:
            fighter_x += FIGHTER_STEP

        alien_y += alien_speed  # Move alien downward

        # Reset ball if it goes off-screen
        if ball_was_fired and ball_y + ball_height < 0:
            ball_was_fired = False
        if ball_was_fired:
            ball_y -= BALL_STEP  # Move ball upward

        screen.fill(screen_fill_color)  # Clear screen with background color
        screen.blit(fighter_image, (fighter_x, fighter_y))  # Draw fighter
        screen.blit(alien_image, (alien_x, alien_y))  # Draw alien

        if ball_was_fired:
            screen.blit(ball_image, (ball_x, ball_y))  # Draw ball

        # Display score
        game_score_text = second_game_font.render(f"Your Score is: {game_score}", True, 'olive')
        screen.blit(game_score_text, (20, 20))

        pygame.time.Clock().tick(128)  # Control game speed
        pygame.display.update()  # Update screen

        # End game if alien reaches the bottom
        if alien_y + alien_height > fighter_y:
            game_is_running = False

        # Check if ball hits the alien
        if ball_was_fired and \
                alien_x < ball_x < alien_x + alien_width - ball_width and \
                alien_y < ball_y < alien_y + alien_height - ball_height:
            ball_was_fired = False
            alien_x, alien_y = randint(0, screen_width - alien_width), 0  # Reset alien
            alien_speed += 0.15  # Increase alien speed
            game_score += 1  # Increase score

# Showing Game Over
    screen.fill(screen_fill_color)
    game_over_text = game_font.render("Game Over", True, 'olive')
    screen.blit(game_over_text, game_over_text.get_rect(center=(screen_width/2, screen_height/2 - 50)))

    try_again_text = second_game_font.render("Press R to try again or Q to exit", True, 'white')
    screen.blit(try_again_text, try_again_text.get_rect(center=(screen_width/2, screen_height/2 + 20)))

    pygame.display.update()

    # Waiting for the user's decision
    waiting_for_input = True
    while waiting_for_input:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:  # game replay
                    waiting_for_input = False
                    run_game()
                elif event.key == pygame.K_q:  # exit
                    pygame.quit()
                    sys.exit()

# Launching the game
run_game()
