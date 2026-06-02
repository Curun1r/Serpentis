import os
import pygame
from game import Game

# Ensure the working directory is always the folder that contains main.py,
# regardless of how the game was launched (double-click, terminal, shortcut).
os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    pygame.init()
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    pygame.mixer.set_num_channels(16)
    pygame.mixer.set_reserved(2)   # channels 0 and 1 reserved for dash + music
    game = Game()
    game.run()
    pygame.quit()
