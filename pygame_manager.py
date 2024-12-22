# pygame_manager.py

import pygame

class PygameManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = PygameManager()
        return cls._instance
    
    def __init__(self):
        if not pygame.get_init():
            pygame.init()
        self.screen = None
        
    def set_screen(self, screen):
        self.screen = screen
        
    def get_screen(self):
        return self.screen
