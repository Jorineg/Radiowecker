#!/usr/bin/env python3

import time
import subprocess
import RPi.GPIO as GPIO
from gpio_pins import ROTARY1_A, ROTARY1_B

# Debug output
def debug(msg):
    print(f"{time.time():.3f}: {msg}")

class RotaryEncoder:
    # Encoder sequence for clockwise rotation: 3,2,0,1,3
    # Each position: (MSB) pin_a,pin_b (LSB)
    SEQ_CW = [0b11, 0b10, 0b00, 0b01]  # 3,2,0,1
    
    def __init__(self, pin_a, pin_b):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.value = 50  # Start at 50%
        self.last_time = time.time()
        self.last_position = -1
        self.turn_count = 0
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins with pull-up
        GPIO.setup(pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Get initial position
        self._read_position()
        
        debug(f"Initialized encoder on pins A={pin_a}, B={pin_b}")
        debug(f"Initial position: {self.last_position}")

    def _read_position(self):
        """Read current position in sequence (0-3)"""
        a = GPIO.input(self.pin_a)
        b = GPIO.input(self.pin_b)
        return (a << 1) | b

    def update(self):
        """Check encoder state and return change (-2, 0, or +2)"""
        position = self._read_position()
        
        # First reading
        if self.last_position < 0:
            self.last_position = position
            return 0
            
        # Position changed
        if position != self.last_position:
            current_time = time.time()
            dt = current_time - self.last_time
            debug(f"Position: {position} (was {self.last_position}) dt={dt*1000:.1f}ms")
            
            # Find positions in sequence
            old_idx = self.SEQ_CW.index(self.last_position)
            new_idx = self.SEQ_CW.index(position)
            
            # Compute step
            step = (new_idx - old_idx) % 4
            if step == 1:  # Next in sequence = CW
                self.turn_count += 1
                if self.turn_count >= 2:  # Complete rotation
                    self.turn_count = 0
                    self.value = min(100, self.value + 2)
                    debug(f"CW -> {self.value}%")
                    self.last_position = position
                    self.last_time = current_time
                    return 2
            elif step == 3:  # Previous in sequence = CCW
                self.turn_count -= 1
                if self.turn_count <= -2:  # Complete rotation
                    self.turn_count = 0
                    self.value = max(0, self.value - 2)
                    debug(f"CCW -> {self.value}%")
                    self.last_position = position
                    self.last_time = current_time
                    return -2
            else:  # Invalid sequence
                self.turn_count = 0
                
            self.last_position = position
            self.last_time = current_time
            
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
                # encoder.set_volume(new_volume)
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.001)  # 1ms polling
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
