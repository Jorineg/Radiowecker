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
                    
            time.sleep(0.001)  # Small delay to prevent CPU hogging
            
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
        display.buffer.draw_text(0, 0, f"Volume: {vol}%", size="5x8")
        display.buffer.draw_rect(0, 20, int(vol * 1.28), 10, fill=True)  # Volume bar
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
