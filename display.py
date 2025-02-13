#!/usr/bin/env python3

from typing import Optional
from pygame_manager import PygameManager
import numpy as np

try:
    import RPi.GPIO as GPIO
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    from PIL import Image
    RPI_HARDWARE = True
except ImportError:
    import pygame
    RPI_HARDWARE = False

from font_5x8 import FONT_5X8, get_char as get_char_5x8, get_text_width as get_text_width_5x8
from font_8x16 import FONT_8X16, get_char as get_char_8x16, get_text_width as get_text_width_8x16


class DisplayBuffer:
    """Emulates a 1-bit display buffer like the SSD1306"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pages = (height + 7) // 8
        self.buffer = bytearray(width * self.pages)
        
    def get_buffer(self):
        """Get raw buffer data"""
        return self.buffer

    def clear(self):
        """Clear display buffer"""
        self.buffer = bytearray(self.width * self.pages)

    def set_pixel(self, x: int, y: int, on: bool):
        """Set a single pixel in the buffer"""
        if 0 <= x < self.width and 0 <= y < self.height:
            page = y // 8
            bit = y % 8
            idx = x + page * self.width
            if on:
                self.buffer[idx] |= 1 << bit
            else:
                self.buffer[idx] &= ~(1 << bit)

    def get_pixel(self, x: int, y: int) -> bool:
        """Get state of a single pixel"""
        if 0 <= x < self.width and 0 <= y < self.height:
            page = y // 8
            bit = y % 8
            idx = x + page * self.width
            return bool(self.buffer[idx] & (1 << bit))
        return False

    def draw_bitmap(self, x: int, y: int, bitmap: list, inverted: bool = False):
        """Draw a bitmap at given position"""
        for dy, row in enumerate(bitmap):
            for dx, pixel in enumerate(row):
                self.set_pixel(x + dx, y + dy, pixel != inverted)

    def draw_text(self, x: int, y: int, text: str, inverted: bool = False, size: str = "5x8"):
        """Draw text using bitmap font"""
        cursor_x = x
        
        if size == "5x8":
            get_char = get_char_5x8
            char_width = 6
        elif size == "8x16":
            get_char = get_char_8x16
            char_width = 9
        else:
            raise ValueError("Font size must be '5x8' or '8x16'")
            
        for char in text:
            bitmap = get_char(char)
            self.draw_bitmap(cursor_x, y, bitmap, inverted)
            cursor_x += char_width

    def draw_rect(self, x: int, y: int, w: int, h: int, fill: bool = False):
        """Draw a rectangle"""
        if fill:
            for dy in range(h):
                for dx in range(w):
                    self.set_pixel(x + dx, y + dy, True)
        else:
            for dx in range(w):
                self.set_pixel(x + dx, y, True)
                self.set_pixel(x + dx, y + h - 1, True)
            for dy in range(h):
                self.set_pixel(x, y + dy, True)
                self.set_pixel(x + w - 1, y + dy, True)


class Display:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.buffer = DisplayBuffer(width, height)

    def clear(self):
        self.buffer.clear()

    def show(self):
        raise NotImplementedError()


class PygameDisplay(Display):
    def __init__(self, width: int, height: int, scale: int = 4):
        super().__init__(width, height)
        self.scale = scale
        self.pygame = PygameManager.get_instance()
        self.screen = pygame.display.set_mode((width * scale, height * scale))
        pygame.display.set_caption("RadioWecker Display Emulation")
        self.pygame.set_screen(self.screen)
        
        # Create optimized surfaces
        self.base_surface = pygame.Surface((width, height))
        self.scaled_surface = pygame.Surface((width * scale, height * scale))
        
        # Pre-allocate buffer array
        self.surface_array = np.zeros((height, width), dtype=np.uint8)

    def show(self):
        try:
            # Convert display buffer to numpy array in one operation
            buffer = self.buffer.get_buffer()
            for page in range(self.height // 8):
                for x in range(self.width):
                    byte = buffer[x + page * self.width]
                    for bit in range(8):
                        y = page * 8 + bit
                        if y < self.height:
                            self.surface_array[y, x] = 255 if byte & (1 << bit) else 0
            
            # Update surface directly from array
            pygame.surfarray.blit_array(self.base_surface, self.surface_array)
            
            # Scale and display
            pygame.transform.scale(self.base_surface, 
                                (self.width * self.scale, self.height * self.scale), 
                                self.scaled_surface)
            self.screen.blit(self.scaled_surface, (0, 0))
            pygame.display.flip()
        except:
            pass


class OLEDDisplay(Display):
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        if RPI_HARDWARE:
            try:
                serial = i2c(port=1, address=0x3C)
                self.device = ssd1306(serial)
                # Create image buffer
                self.image = Image.new('1', (width, height))
            except Exception as e:
                print(f"Warning: Could not initialize OLED display: {e}")
                self.device = None
        else:
            self.device = None

    def show(self):
        if not self.device:
            return
            
        try:
            # Convert buffer to PIL image
            for y in range(self.height):
                for x in range(self.width):
                    self.image.putpixel(
                        (self.width - x - 1, self.height - y - 1),
                        1 if self.buffer.get_pixel(x, y) else 0
                    )
            
            # Display image directly
            self.device.display(self.image)
        except:
            pass
