#!/usr/bin/env python3

import time
import threading
import RPi.GPIO as GPIO
from display import OLEDDisplay, PygameDisplay
from gpio_pins import ROTARY1_A, ROTARY1_B, ROTARY1_SW
from volume_control import VolumeControl

# GPIO Pins für Rotary Encoder
ROTARY_A = ROTARY1_A  # Volume encoder pins
ROTARY_B = ROTARY1_B
ROTARY_SW = ROTARY1_SW

class RotaryEncoder:
    SEQ_CW = [0b11, 0b10, 0b00, 0b01]  # 3,2,0,1
    
    def __init__(self, pin_a, pin_b, callback):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.callback = callback
        self.sequence = 0b11
        self._running = True
        self._lock = threading.Lock()
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Start polling thread
        self.thread = threading.Thread(target=self._polling_thread)
        self.thread.daemon = True
        self.thread.start()
        
    def _polling_thread(self):
        while self._running:
            with self._lock:
                # Read current state
                a = GPIO.input(self.pin_a)
                b = GPIO.input(self.pin_b)
                
                # Calculate new state
                new_sequence = (a << 1) | b
                
                if new_sequence != self.sequence:
                    # Find positions in sequence
                    old_pos = self.SEQ_CW.index(self.sequence)
                    new_pos = self.SEQ_CW.index(new_sequence)
                    
                    # Calculate direction
                    direction = new_pos - old_pos
                    if direction in [-3, 1]:  # Clockwise
                        self.callback("CW")
                    elif direction in [-1, 3]:  # Counter-clockwise
                        self.callback("CCW")
                    
                    self.sequence = new_sequence
                    
            time.sleep(0.0002)  # Small delay to prevent CPU hogging: 0.2ms
            
    def stop(self):
        self._running = False
        self.thread.join()

def main():
    # Initialize display
    try:
        display = OLEDDisplay(128, 64)
    except:
        print("Falling back to Pygame display")
        display = PygameDisplay(128, 64)
    
    # Initialize volume control
    volume = VolumeControl()
    
    def handle_rotation(direction):
        if direction == "CW":
            vol = volume.volume_up()
        else:
            vol = volume.volume_down()
            
        # Update display
        display.buffer.clear()
        
        # Center volume text
        text = f"Volume: {vol}%"
        text_width = len(text) * 9  # 8x16 font is 9 pixels wide per char
        x = (display.width - text_width) // 2
        y = (display.height - 36) // 2  # Center vertically, leaving space for bar
        display.buffer.draw_text(x, y, text, size="8x16")
        
        # Center volume bar
        bar_width = int(display.width * 0.8)  # 80% of display width
        bar_height = 10
        x = (display.width - bar_width) // 2
        y = y + 26  # 10 pixels below text
        
        # Draw background bar
        display.buffer.draw_rect(x, y, bar_width, bar_height, False)
        
        # Draw filled portion
        if vol > 0:
            filled_width = int(bar_width * vol / 100)
            display.buffer.draw_rect(x, y, filled_width, bar_height, True)
            
        display.show()
    
    # Initialize rotary encoder
    encoder = RotaryEncoder(ROTARY_A, ROTARY_B, handle_rotation)
    
    try:
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        encoder.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
