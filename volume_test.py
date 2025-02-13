#!/usr/bin/env python3

import time
import threading
import subprocess
import RPi.GPIO as GPIO
from display import OLEDDisplay, PygameDisplay
from gpio_pins import ROTARY1_A, ROTARY1_B, ROTARY1_SW

# GPIO Pins für Rotary Encoder
ROTARY_A = ROTARY1_A  # Volume encoder pins
ROTARY_B = ROTARY1_B
ROTARY_SW = ROTARY1_SW

class VolumeControl:
    def __init__(self):
        self._volume = self._get_current_volume()
        self._lock = threading.Lock()

    def _get_current_volume(self):
        try:
            # Try different mixer controls
            for control in ['PCM', 'Master']:
                try:
                    output = subprocess.check_output(['amixer', 'get', control]).decode()
                    for line in output.split('\n'):
                        if 'Playback' in line and '%' in line:
                            return int(line.split('[')[1].split('%')[0])
                except:
                    continue
        except:
            pass
        return 50

    def _set_volume(self, volume):
        volume = max(0, min(100, volume))
        try:
            # Try different mixer controls
            for control in ['PCM', 'Master']:
                try:
                    subprocess.run(['amixer', 'set', control, f'{volume}%'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
                    return volume
                except:
                    continue
        except:
            pass
        return volume

    def adjust_volume(self, delta):
        with self._lock:
            self._volume = self._set_volume(self._volume + delta)
        return self._volume

class RotaryEncoder:
    def __init__(self, pin_a, pin_b, callback):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.callback = callback
        self.last_encoded = 0
        self.value = 0
        
        # Setup GPIO pins with pull-up
        GPIO.setup(pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Read initial states
        self.last_state_a = GPIO.input(pin_a)
        self.last_state_b = GPIO.input(pin_b)
        
        # Add event detection with debounce
        try:
            GPIO.add_event_detect(pin_a, GPIO.BOTH, callback=self._update, bouncetime=1)
            GPIO.add_event_detect(pin_b, GPIO.BOTH, callback=self._update, bouncetime=1)
            self.use_polling = False
        except:
            print("Warning: Could not set up GPIO events. Falling back to polling mode.")
            self.use_polling = True

    def _update(self, channel=None):
        try:
            state_a = GPIO.input(self.pin_a)
            state_b = GPIO.input(self.pin_b)
            
            if state_a != self.last_state_a or state_b != self.last_state_b:
                # Determine rotation direction from state changes
                if self.last_state_a == self.last_state_b:
                    if state_a != state_b:
                        # Clockwise
                        self.value += 2
                        self.callback(2)
                else:
                    if state_a == state_b:
                        # Counter-clockwise
                        self.value -= 2
                        self.callback(-2)
                
                self.last_state_a = state_a
                self.last_state_b = state_b
        except:
            pass

    def check_state(self):
        """Polling mode update - call this regularly if events failed"""
        if self.use_polling:
            self._update()

def main():
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Initialize display based on platform
    try:
        display = OLEDDisplay(128, 64)
    except:
        display = PygameDisplay(128, 64)
    
    # Initialize volume control
    volume = VolumeControl()
    current_volume = volume._get_current_volume()
    volume_overlay_timeout = 0
    OVERLAY_DURATION = 1.0  # Show volume for 1 second
    
    def volume_callback(delta):
        nonlocal current_volume, volume_overlay_timeout
        current_volume = volume.adjust_volume(delta)
        volume_overlay_timeout = time.time() + OVERLAY_DURATION
    
    # Initialize rotary encoder with callback
    encoder = RotaryEncoder(ROTARY_A, ROTARY_B, volume_callback)
    
    try:
        while True:
            # Clear display buffer
            display.buffer.clear()
            
            # Check encoder in polling mode if events failed
            encoder.check_state()
            
            # Show volume overlay if timeout not reached
            if time.time() < volume_overlay_timeout:
                # Draw volume text
                volume_text = f"{current_volume}%"
                text_width = len(volume_text) * 9  # 8 pixels per char + 1 spacing
                x = (display.width - text_width) // 2
                y = (display.height - 16) // 2
                display.buffer.draw_text(x, y, volume_text, size="8x16")
                
                # Draw volume bar
                bar_width = int((display.width * 0.8))
                bar_height = 4
                x = (display.width - bar_width) // 2
                y = display.height - 10
                
                # Background bar
                display.buffer.draw_rect(x, y, bar_width, bar_height, False)
                
                # Filled portion
                filled_width = int((bar_width * current_volume) / 100)
                if filled_width > 0:
                    display.buffer.draw_rect(x, y, filled_width, bar_height, True)
            
            # Update physical display
            display.show()
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\nCleaning up...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
