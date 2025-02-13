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

try:
    import alsaaudio
    HAVE_ALSA = True
except ImportError:
    HAVE_ALSA = False

class VolumeControl:
    def __init__(self):
        self._volume = 50
        self._lock = threading.Lock()
        
        # Try to initialize ALSA mixer
        self.mixer = None
        if HAVE_ALSA:
            try:
                # Try different mixer controls
                for control in ['PCM', 'Master']:
                    try:
                        self.mixer = alsaaudio.Mixer(control)
                        self._volume = self.mixer.getvolume()[0]
                        break
                    except:
                        continue
            except:
                pass
        
        if not self.mixer:
            print("Warning: Using subprocess for volume control (slower)")

    def _get_current_volume(self):
        if self.mixer:
            try:
                return self.mixer.getvolume()[0]
            except:
                pass
                
        try:
            # Fallback to amixer
            for control in ['PCM', 'Master']:
                try:
                    output = subprocess.check_output(['amixer', '-M', 'get', control]).decode()
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
        
        if self.mixer:
            try:
                self.mixer.setvolume(volume)
                return volume
            except:
                pass
                
        try:
            # Fallback to amixer
            for control in ['PCM', 'Master']:
                try:
                    subprocess.run(['amixer', '-M', 'set', control, f'{volume}%'], 
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
    SEQ_CW = [0b11, 0b10, 0b00, 0b01]  # 3,2,0,1
    
    def __init__(self, pin_a, pin_b, callback):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.callback = callback
        self.last_position = -1
        self.turn_count = 0
        self.accumulated_turns = 0  # Accumulated turns since last callback
        self.running = True
        self._lock = threading.Lock()  # Lock for thread-safe access
        
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
            self.callback(turns * 2)  # *2 to maintain same volume change per turn
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
    
    try:
        while True:
            # Process encoder turns if enough time has passed
            current_time = time.time()
            if current_time - last_volume_update >= MIN_UPDATE_INTERVAL:
                encoder.process_turns()
            
            # Clear display buffer
            display.buffer.clear()
            
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
            time.sleep(0.03)  # 30fps main loop
            
    except KeyboardInterrupt:
        print("\nCleaning up...")
    finally:
        encoder.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
