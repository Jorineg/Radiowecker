#!/usr/bin/env python3

import time
import smbus2

class DisplayBuffer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pages = (height + 7) // 8
        self.buffer = bytearray(width * self.pages)
        
    def clear(self):
        """Clear the entire buffer"""
        self.buffer[:] = b'\x00' * len(self.buffer)
        
    def set_pixel(self, x: int, y: int, on: bool = True):
        """Set a single pixel in the buffer"""
        if 0 <= x < self.width and 0 <= y < self.height:
            page = y // 8
            bit = y % 8
            idx = page * self.width + x
            if on:
                self.buffer[idx] |= (1 << bit)
            else:
                self.buffer[idx] &= ~(1 << bit)
                
    def draw_rect(self, x: int, y: int, width: int, height: int, fill: bool = False):
        """Draw a rectangle"""
        for i in range(width):
            for j in range(height):
                if fill or i == 0 or i == width-1 or j == 0 or j == height-1:
                    self.set_pixel(x + i, y + j)

    def draw_text(self, x: int, y: int, text: str, size: str = "8x16"):
        """Draw text using 8x16 font"""
        # Simplified 8x16 font with just numbers and %
        # You would need to add the actual font data here
        pass

class DirectOLED:
    """Direct I2C implementation for SSD1306 OLED display"""
    def __init__(self, width=128, height=64, address=0x3C, bus=1):
        self.width = width
        self.height = height
        self.pages = (height + 7) // 8
        self.address = address
        
        # Initialize I2C
        self.i2c = smbus2.SMBus(bus)
        
        # Initialize buffer
        self.buffer = DisplayBuffer(width, height)
        self.display_buffer = bytearray(width * self.pages)
        self.last_buffer = bytearray(width * self.pages)
        
        # Initialize display
        self._init_display()
        
    def _command(self, *cmd):
        """Send command to display"""
        for c in cmd:
            self.i2c.write_byte_data(self.address, 0x00, c)
            
    def _data(self, data):
        """Send data to display using page mode"""
        # Write in chunks of 32 bytes to avoid I2C buffer limitations
        chunk_size = 32
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            # Create write command with data byte
            cmd = [0x40] + list(chunk)  # 0x40 is the data mode
            self.i2c.write_i2c_block_data(self.address, 0x40, list(chunk))
            
    def _init_display(self):
        """Initialize display with optimal settings"""
        # Display off
        self._command(0xAE)
        
        # Set clock div and oscillator
        self._command(0xD5, 0x80)
        
        # Set multiplex ratio
        self._command(0xA8, self.height - 1)
        
        # Set display offset
        self._command(0xD3, 0x00)
        
        # Set start line
        self._command(0x40)
        
        # Enable charge pump
        self._command(0x8D, 0x14)
        
        # Set memory mode to horizontal
        self._command(0x20, 0x00)
        
        # Normal display direction
        self._command(0xA0)  # Normal segment mapping
        self._command(0xC0)  # Normal COM direction
        
        # Set contrast
        self._command(0x81, 0xCF)
        
        # Set precharge
        self._command(0xD9, 0xF1)
        
        # Set COM pins
        self._command(0xDA, 0x12)
        
        # Set VCOM detect
        self._command(0xDB, 0x40)
        
        # Display on
        self._command(0xA4)  # Display ON with RAM content
        self._command(0xA6)  # Normal display (not inverted)
        self._command(0xAF)  # Display on
        
    def show(self):
        """Update display with current buffer"""
        # Copy buffer
        self.display_buffer[:] = self.buffer.buffer[:]
        
        # Only update if buffer changed
        if self.display_buffer != self.last_buffer:
            # Set column address
            self._command(0x21, 0, self.width - 1)
            
            # Set page address
            self._command(0x22, 0, self.pages - 1)
            
            # Write display buffer
            self._data(self.display_buffer)
            
            # Save current buffer
            self.last_buffer[:] = self.display_buffer[:]
