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
        self.last_seq = 0
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins with pull-up
        GPIO.setup(pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Read initial states and compute sequence number
        a = GPIO.input(pin_a)
        b = GPIO.input(pin_b)
        self.last_seq = (a << 1) | b
        
        debug(f"Initialized encoder on pins A={pin_a}, B={pin_b}")
        debug(f"Initial state: seq={self.last_seq} (A={a}, B={b})")

    def update(self):
        """Check encoder state and return change (-2, 0, or +2)"""
        a = GPIO.input(self.pin_a)
        b = GPIO.input(self.pin_b)
        
        # Convert states to sequence number (0-3)
        seq = (a << 1) | b
        
        # Compute difference from last position
        diff = (seq - self.last_seq) % 4
        
        # Only process if changed
        if diff != 0:
            current_time = time.time()
            dt = current_time - self.last_time
            debug(f"State: seq={seq} (A={a}, B={b}) diff={diff} dt={dt*1000:.1f}ms")
            
            # Store timing for debugging
            self.last_time = current_time
            
            # Store new state
            self.last_seq = seq
            
            # Return change value
            if diff == 1:  # Clockwise
                self.value = min(100, self.value + 2)
                debug(f"CW -> {self.value}%")
                return 2
            elif diff == 3:  # Counter-clockwise
                self.value = max(0, self.value - 2)
                debug(f"CCW -> {self.value}%")
                return -2
        
        return 0

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
                new_volume = encoder.value
                encoder.set_volume(new_volume)
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.001)  # 1ms polling
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
