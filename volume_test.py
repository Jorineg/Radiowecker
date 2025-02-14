#!/usr/bin/env python3

import time
import threading
import RPi.GPIO as GPIO
from display import OLEDDisplay, PygameDisplay
from gpio_pins import ROTARY1_A, ROTARY1_B, ROTARY1_SW
from volume_control import VolumeControl
import numpy as np

# GPIO Pins für Rotary Encoder
ROTARY_A = ROTARY1_A  # Volume encoder pins
ROTARY_B = ROTARY1_B
ROTARY_SW = ROTARY1_SW

last_polling = time.time()

class RotaryEncoder:
    # Encoder sequence for clockwise rotation: 3,2,0,1,3
    # Each position: (MSB) pin_a,pin_b (LSB)
    SEQ_CW = [0b11, 0b10, 0b00, 0b01]  # 3,2,0,1
    
    def __init__(self, pin_a, pin_b, callback):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.callback = callback
        self.last_position = -1
        self.turn_count = 0
        self.accumulated_ticks = 0  # Gesammelte Ticks
        self.last_callback = 0  # Zeit des letzten Callbacks
        self._running = True
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Get initial position
        self._read_position()
        
        # Start callback thread
        self.callback_thread = threading.Thread(target=self._callback_thread)
        self.callback_thread.daemon = True
        self.callback_thread.start()
        
    def _read_position(self):
        """Read current position in sequence (0-3)"""
        a = GPIO.input(self.pin_a)
        b = GPIO.input(self.pin_b)
        return (a << 1) | b
        
    def update(self):
        """Check encoder state and update if needed"""
        position = self._read_position()
        
        global last_polling
        time_delta = time.time() - last_polling
        last_polling = time.time()
        print(f"time_delta={time_delta*1000:.1f}ms")

        # First reading
        if self.last_position < 0:
            self.last_position = position
            return
            
        # Position changed
        if position != self.last_position:
            # Find positions in sequence
            try:
                old_idx = self.SEQ_CW.index(self.last_position)
                new_idx = self.SEQ_CW.index(position)
                
                # Compute step
                step = (new_idx - old_idx) % 4

  
                print(f"old={old_idx}, new={new_idx}, step={step}, tc={self.turn_count}, at={self.accumulated_ticks}, td={time_delta:.3f}")
                if step == 1:  # Next in sequence = CW
                    self.turn_count += 1
                    if self.turn_count >= 2:  # Complete rotation
                        self.turn_count = 0
                        self.accumulated_ticks += 1  # Ein Tick nach oben
                elif step == 3:  # Previous in sequence = CCW
                    self.turn_count -= 1
                    if self.turn_count <= -2:  # Complete rotation
                        self.turn_count = 0
                        self.accumulated_ticks -= 1  # Ein Tick nach unten
                else:  # Invalid sequence
                    self.turn_count = 0
            except ValueError:
                # Invalid state, reset
                self.turn_count = 0
                
            self.last_position = position
            
    def _callback_thread(self):
        """Thread für periodische Callbacks"""
        while self._running:
            if self.accumulated_ticks != 0:
                self.callback(self.accumulated_ticks)  # Callback mit Anzahl der Ticks
                self.accumulated_ticks = 0  # Reset
            time.sleep(0.01)  # 10ms sleep
            
    def stop(self):
        self._running = False
        self.callback_thread.join()

def main():
    # Initialize display
    try:
        display = OLEDDisplay(128, 64)
    except:
        print("Falling back to Pygame display")
        display = PygameDisplay(128, 64)
    
    # Initialize volume control
    volume = VolumeControl()
    
    def handle_rotation(ticks):
        # Ticks * 2 für schnellere Änderung
        if ticks > 0:
            vol = volume.volume_up(step=ticks * 2)
        else:
            vol = volume.volume_down(step=-ticks * 2)
            
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
        times = np.array([])
        while True:
            times = np.append(times, time.time())
            encoder.update()  # Poll encoder
            time.sleep(0.0001)  # 0.1ms polling interval
            
    except KeyboardInterrupt:
        # calculate mean interval of times
        mean_interval = sum(times[1:] - times[:-1]) / len(times[1:])
        print(f"Mean interval: {mean_interval*1000:.1f}ms")
        encoder.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
