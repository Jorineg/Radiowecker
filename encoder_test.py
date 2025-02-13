#!/usr/bin/env python3

import time
import subprocess
import RPi.GPIO as GPIO
from gpio_pins import ROTARY1_A, ROTARY1_B

# Debug output
def debug(msg):
    print(f"{time.time():.3f}: {msg}")

class RotaryEncoder:
    def __init__(self, pin_a, pin_b):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.value = 50  # Start at 50%
        self.last_time = time.time()
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins with pull-up
        GPIO.setup(pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Read initial states
        self.last_a = GPIO.input(pin_a)
        self.last_b = GPIO.input(pin_b)
        
        debug(f"Initialized encoder on pins A={pin_a}, B={pin_b}")
        debug(f"Initial states: A={self.last_a}, B={self.last_b}")

    def update(self):
        """Check encoder state and return change (-1, 0, or 1)"""
        a = GPIO.input(self.pin_a)
        b = GPIO.input(self.pin_b)
        
        change = 0
        
        # Only process if at least one input changed
        if a != self.last_a or b != self.last_b:
            current_time = time.time()
            
            # Simple state detection
            if self.last_a == self.last_b:
                if a != b:  # Transition to unmatched state
                    change = 1  # Clockwise
                    debug(f"CW: A={a} B={b} (was A={self.last_a} B={self.last_b})")
            else:
                if a == b:  # Transition to matched state
                    change = -1  # Counter-clockwise
                    debug(f"CCW: A={a} B={b} (was A={self.last_a} B={self.last_b})")
            
            # Store timing for debugging
            if change != 0:
                dt = current_time - self.last_time
                debug(f"Δt = {dt*1000:.1f}ms")
                self.last_time = current_time
        
        # Save states for next time
        self.last_a = a
        self.last_b = b
        
        return change

    def set_volume(self, volume):
        """Set volume and return actual value set"""
        volume = max(0, min(100, volume))
        try:
            # Try different mixer controls
            for control in ['PCM', 'Master']:
                try:
                    cmd = ['amixer', '-M', 'get', control]
                    debug(f"Running: {' '.join(cmd)}")
                    output = subprocess.check_output(cmd).decode()
                    debug(f"Output: {output.strip()}")
                    
                    # If we got here, the control exists
                    cmd = ['amixer', '-M', 'set', control, f'{volume}%']
                    debug(f"Running: {' '.join(cmd)}")
                    output = subprocess.check_output(cmd).decode()
                    debug(f"Output: {output.strip()}")
                    return volume
                except subprocess.CalledProcessError as e:
                    debug(f"Failed: {e}")
                    continue
        except Exception as e:
            debug(f"Error: {e}")
        return volume

def main():
    try:
        # Create encoder
        encoder = RotaryEncoder(ROTARY1_A, ROTARY1_B)
        
        while True:
            # Check encoder
            change = encoder.update()
            
            # Update volume if changed
            if change != 0:
                new_volume = encoder.value + (change * 2)  # 2% steps
                # encoder.value = encoder.set_volume(new_volume)
                debug(f"Volume: {encoder.value}%")
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.001)  # 1ms polling
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
