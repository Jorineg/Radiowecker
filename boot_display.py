#!/usr/bin/env python3

import time
start_time = time.time()
print(f"[{time.time() - start_time:.3f}s] Starting minimal imports...")

import sys
import signal
import fcntl
import io

# Quick I2C display function without heavy dependencies
def quick_display_message():
    try:
        print(f"[{time.time() - start_time:.3f}s] Trying quick I2C display...")
        # Open I2C bus
        with io.open("/dev/i2c-1", "rb+", buffering=0) as f:
            # Set I2C slave address to 0x3C (standard for SSD1306)
            fcntl.ioctl(f, 0x0703, 0x3C)
            
            # Initialize display
            init_sequence = bytes([
                0x00, 0xAE,  # display off
                0x00, 0xD5, 0x00, 0x80,  # clock div
                0x00, 0xA8, 0x00, 0x3F,  # multiplex
                0x00, 0xD3, 0x00, 0x00,  # offset
                0x00, 0x40,  # start line
                0x00, 0x8D, 0x00, 0x14,  # charge pump
                0x00, 0x20, 0x00, 0x00,  # memory mode
                0x00, 0xA1,  # seg remap
                0x00, 0xC8,  # com scan dec
                0x00, 0xDA, 0x00, 0x12,  # com pins
                0x00, 0x81, 0x00, 0xCF,  # contrast
                0x00, 0xD9, 0x00, 0xF1,  # precharge
                0x00, 0xDB, 0x00, 0x40,  # vcom detect
                0x00, 0xA4,  # resume
                0x00, 0xA6,  # normal (not inverted)
                0x00, 0xAF,  # display on
            ])
            f.write(init_sequence)
            
            # Write "BOOT" in large pixels
            buffer = [0] * 1024  # 128x64 pixels = 1024 bytes
            # Simple "BOOT" pattern (very basic pixel art)
            boot_pattern = [
                0x00, 0x7E, 0x7E, 0x0C, 0x18, 0x7E, 0x7E, 0x00,  # B
                0x00, 0x7E, 0x7E, 0x66, 0x66, 0x66, 0x66, 0x00,  # O
                0x00, 0x7E, 0x7E, 0x66, 0x66, 0x66, 0x66, 0x00,  # O
                0x00, 0x7E, 0x7E, 0x18, 0x18, 0x18, 0x18, 0x00,  # T
            ]
            
            # Position in middle of screen
            pos = 256 + 32  # Middle row, slightly left of center
            for b in boot_pattern:
                buffer[pos] = b
                pos += 1
            
            # Write to display
            for i in range(0, len(buffer), 16):
                chunk = bytes([0x40] + list(buffer[i:i+16]))
                f.write(chunk)
                
        print(f"[{time.time() - start_time:.3f}s] Quick display message shown")
        return True
    except Exception as e:
        print(f"[{time.time() - start_time:.3f}s] Quick display failed: {e}")
        return False

def signal_handler(signum, frame):
    # Clear display on termination
    try:
        display.clear()
        display.show()
    except:
        pass
    sys.exit(0)

def show_boot():
    try:
        # Try quick display first
        quick_display_message()
        
        print(f"[{time.time() - start_time:.3f}s] Importing display module...")
        from display import OLEDDisplay
        print(f"[{time.time() - start_time:.3f}s] Display module imported")
        
        print(f"[{time.time() - start_time:.3f}s] Starting display init...")
        global display
        # Initialize display with retries
        for i in range(20):  # try for 2 seconds
            try:
                display = OLEDDisplay(128, 64)
                print(f"[{time.time() - start_time:.3f}s] Display initialized after {i+1} tries")
                break
            except Exception as e:
                print(f"[{time.time() - start_time:.3f}s] Init attempt {i+1} failed: {e}")
                time.sleep(0.1)
        else:
            print("Could not initialize display", file=sys.stderr)
            sys.exit(1)
        
        print(f"[{time.time() - start_time:.3f}s] Setting up signal handler...")
        signal.signal(signal.SIGTERM, signal_handler)
        print(f"[{time.time() - start_time:.3f}s] Starting main loop...")
        
        while True:
            display.clear()
            
            # Draw "Welcome" centered with large font
            welcome_text = "Welcome"
            x_pos_welcome = (128 - len(welcome_text) * 8) // 2
            display.buffer.draw_text(x_pos_welcome, 10, welcome_text, size="8x16")
            
            status_text = "starting up..."
            x_pos_status = (128 - len(status_text) * 5) // 2
            display.buffer.draw_text(x_pos_status, 40, status_text, size="5x8")
            
            display.show()
            time.sleep(0.1)
            
    except Exception as e:
        print(f"[{time.time() - start_time:.3f}s] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    print(f"[{time.time() - start_time:.3f}s] Starting main...")
    show_boot()
