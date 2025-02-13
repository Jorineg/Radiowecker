#!/usr/bin/env python3

import time
import threading
import RPi.GPIO as GPIO
from display_direct import DirectOLED
from gpio_pins import ROTARY1_A, ROTARY1_B, ROTARY1_SW
from volume_control import VolumeControl

# GPIO Pins für Rotary Encoder
ROTARY_A = ROTARY1_A  # Volume encoder pins
ROTARY_B = ROTARY1_B

class RotaryEncoder:
    SEQ_CW = [0b11, 0b10, 0b00, 0b01]  # 3,2,0,1
    
    def __init__(self, pin_a, pin_b, callback):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.callback = callback
        self.last_position = -1
        self.turn_count = 0
        self.accumulated_turns = 0
        self.running = True
        self._lock = threading.Lock()
        
        # Setup GPIO pins with pull-up
        GPIO.setup(pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Start polling thread
        self.thread = threading.Thread(target=self._polling_thread, daemon=True)
        self.thread.start()

    def _read_position(self):
        """Read current position in sequence (0-3)"""
        a = GPIO.input(self.pin_a)
        b = GPIO.input(self.pin_b)
        return (a << 1) | b

    def _polling_thread(self):
        """Dedicated thread for encoder polling"""
        while self.running:
            position = self._read_position()
            
            # First reading
            if self.last_position < 0:
                self.last_position = position
                continue
                
            # Position changed
            if position != self.last_position:
                try:
                    # Find positions in sequence
                    old_idx = self.SEQ_CW.index(self.last_position)
                    new_idx = self.SEQ_CW.index(position)
                    
                    # Compute step
                    step = (new_idx - old_idx) % 4
                    if step == 1:  # Next in sequence = CW
                        self.turn_count += 1
                        if self.turn_count >= 2:  # Complete rotation
                            self.turn_count = 0
                            with self._lock:
                                self.accumulated_turns += 1
                    elif step == 3:  # Previous in sequence = CCW
                        self.turn_count -= 1
                        if self.turn_count <= -2:  # Complete rotation
                            self.turn_count = 0
                            with self._lock:
                                self.accumulated_turns -= 1
                    else:  # Invalid sequence
                        self.turn_count = 0
                except ValueError:
                    # Invalid position, reset counter
                    self.turn_count = 0
                    
                self.last_position = position
            
            # Short sleep between polls
            time.sleep(0.0001)  # 0.1ms polling
    
    def process_turns(self):
        """Process accumulated turns and call callback if needed"""
        with self._lock:
            turns = self.accumulated_turns
            self.accumulated_turns = 0
            
        if turns != 0:
            self.callback(turns * 2)
            return True
        return False
    
    def stop(self):
        """Stop the polling thread"""
        self.running = False
        self.thread.join()

def main():
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Initialize display
    display = DirectOLED(128, 64)
    
    # Initialize volume control
    volume = VolumeControl()
    current_volume = volume._get_current_volume()
    volume_overlay_timeout = 0
    OVERLAY_DURATION = 1.0  # Show volume for 1 second
    last_volume_update = 0
    MIN_UPDATE_INTERVAL = 0.02  # Maximum 50 updates per second
    
    def volume_callback(delta):
        nonlocal current_volume, volume_overlay_timeout, last_volume_update
        current_time = time.time()
        
        # Update volume
        current_volume = volume.adjust_volume(delta)
        volume_overlay_timeout = current_time + OVERLAY_DURATION
        last_volume_update = current_time
        print(f"Volume: {current_volume}%")  # Debug output
    
    # Initialize rotary encoder with callback
    encoder = RotaryEncoder(ROTARY_A, ROTARY_B, volume_callback)
    
    # For FPS calculation
    frame_count = 0
    last_fps_time = time.time()
    next_frame_time = time.time()
    FRAME_TIME = 1.0/30.0  # Target 30fps
    
    try:
        while True:
            frame_start = time.time()
            
            # Process encoder turns if enough time has passed
            if frame_start - last_volume_update >= MIN_UPDATE_INTERVAL:
                encoder.process_turns()
            
            # Only update display if we're showing volume or it's time for next frame
            if frame_start >= next_frame_time or time.time() < volume_overlay_timeout:
                # Clear display buffer
                t1 = time.time()
                display.buffer.clear()
                t2 = time.time()
                
                # Show volume overlay if timeout not reached
                if time.time() < volume_overlay_timeout:
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
                t3 = time.time()
                
                # Update physical display
                display.show()
                t4 = time.time()
                
                # Calculate timings
                clear_time = t2 - t1
                draw_time = t3 - t2
                display_time = t4 - t3
                total_time = t4 - frame_start
                
                # Update FPS counter
                frame_count += 1
                if frame_count == 30:  # Print every 30 frames
                    current_time = time.time()
                    fps = frame_count / (current_time - last_fps_time)
                    print(f"FPS: {fps:.1f}")
                    print(f"Timings (ms): Clear={clear_time*1000:.1f}, Draw={draw_time*1000:.1f}, Display={display_time*1000:.1f}, Total={total_time*1000:.1f}")
                    frame_count = 0
                    last_fps_time = current_time
                
                # Schedule next frame
                next_frame_time = frame_start + FRAME_TIME
            
            # Small sleep to prevent CPU hogging if we have time
            sleep_time = max(0, next_frame_time - time.time())
            if sleep_time > 0.001:  # Only sleep if we have more than 1ms
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nCleaning up...")
    finally:
        encoder.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
