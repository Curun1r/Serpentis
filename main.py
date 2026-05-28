import os
import pygame
from game import Game

# Ensure the working directory is always the folder that contains main.py,
# regardless of how the game was launched (double-click, terminal, shortcut).
os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    pygame.init()
    pygame.mixer.init()
    game = Game()
    game.run()
    pygame.quit()
