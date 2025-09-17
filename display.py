#!/usr/bin/env python3

from typing import Optional
from pygame_manager import PygameManager
import numpy as np
import time
import threading
try:
    import pygame  # Ensure pygame is available when using PygameDisplay
except ImportError:
    pygame = None

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
        if pygame is None:
            raise ImportError("pygame is required for PygameDisplay but is not installed")
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
    # SSD1306 commands
    SET_CONTRAST = 0x81
    SET_ENTIRE_ON = 0xA4
    SET_NORM_INV = 0xA6
    SET_DISP = 0xAE
    SET_MEM_ADDR = 0x20
    SET_COL_ADDR = 0x21
    SET_PAGE_ADDR = 0x22
    SET_DISP_START_LINE = 0x40
    SET_SEG_REMAP = 0xA0
    SET_MUX_RATIO = 0xA8
    SET_COM_OUT_DIR = 0xC0
    SET_DISP_OFFSET = 0xD3
    SET_COM_PIN_CFG = 0xDA
    SET_DISP_CLK_DIV = 0xD5
    SET_PRECHARGE = 0xD9
    SET_VCOM_DESEL = 0xDB
    SET_CHARGE_PUMP = 0x8D

    def __init__(self, width: int, height: int):
        # Initialize base class first to set up buffer and pages
        super().__init__(width, height)
        
        if RPI_HARDWARE:
            try:
                # Initialize I2C
                serial = i2c(port=1, address=0x3C)
                self.device = ssd1306(serial)
                
                # Initialize display with optimal settings
                self._init_display()
                
                # Pre-allocate display buffer using pages from base class
                self.display_buffer = bytearray(self.width * self.buffer.pages)
                self.last_buffer = bytearray(self.width * self.buffer.pages)
                
                # Setup display thread
                self._update_requested = False
                self._display_lock = threading.Lock()
                self._display_thread = threading.Thread(target=self._display_update_thread, daemon=True)
                self._display_thread.start()
                
            except Exception as e:
                print(f"Warning: Could not initialize OLED display: {e}")
                self.device = None
        else:
            self.device = None
            
    def _display_update_thread(self):
        """Background thread for display updates"""
        while True:
            # Check if update is needed
            with self._display_lock:
                if self._update_requested:
                    try:
                        # Write entire buffer in one operation
                        self.device.data(self.display_buffer)
                        self._update_requested = False
                    except Exception as e:
                        print(f"Display update failed: {e}")
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.001)

    def _init_display(self):
        """Initialize display with optimal settings"""
        self.device.command(self.SET_DISP | 0x00)  # display off
        
        # Hardware configuration
        self.device.command(self.SET_DISP_CLK_DIV)
        self.device.command(0x80)  # Suggested ratio
        
        self.device.command(self.SET_MUX_RATIO)
        self.device.command(self.height - 1)
        
        self.device.command(self.SET_DISP_OFFSET)
        self.device.command(0x00)
        
        self.device.command(self.SET_DISP_START_LINE | 0x00)
        self.device.command(self.SET_CHARGE_PUMP)
        self.device.command(0x14)  # Enable charge pump
        
        # Memory addressing settings - set once during init
        self.device.command(self.SET_MEM_ADDR)
        self.device.command(0x00)  # Horizontal addressing mode
        
        # Set full display address range once during init
        self.device.command(self.SET_COL_ADDR)
        self.device.command(0)
        self.device.command(self.width - 1)
        self.device.command(self.SET_PAGE_ADDR)
        self.device.command(0)
        self.device.command(self.buffer.pages - 1)
        
        # Set segment re-map: column address 127 is mapped to SEG0
        self.device.command(self.SET_SEG_REMAP | 0x00)  # No flip
        
        # Set COM output scan direction: normal mode
        self.device.command(self.SET_COM_OUT_DIR | 0x00)  # Normal mode
        
        self.device.command(self.SET_COM_PIN_CFG)
        self.device.command(0x12)
        
        self.device.command(self.SET_CONTRAST)
        self.device.command(0xCF)
        
        self.device.command(self.SET_PRECHARGE)
        self.device.command(0xF1)
        
        self.device.command(self.SET_VCOM_DESEL)
        self.device.command(0x40)
        
        # Display settings
        self.device.command(self.SET_ENTIRE_ON)  # Output follows RAM
        self.device.command(self.SET_NORM_INV)   # Not inverted
        self.device.command(self.SET_DISP | 0x01)  # Display on

    def show(self):
        if not self.device:
            return
            
        try:
            # Copy buffer directly (no flipping needed anymore)
            self.display_buffer[:] = self.buffer.get_buffer()
            
            # Only update if buffer changed
            if self.display_buffer != self.last_buffer:
                # Save current buffer
                self.last_buffer[:] = self.display_buffer[:]
                
                # Request update in background thread
                with self._display_lock:
                    self._update_requested = True
                
        except Exception as e:
            print(f"Display update failed: {e}")
            pass
