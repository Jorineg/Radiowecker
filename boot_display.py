#!/usr/bin/env python3

import time
start_time = time.time()
print(f"[{time.time() - start_time:.3f}s] Starting minimal imports...")

import sys
import signal
import fcntl
import io

def write_cmd(f, cmd):
    """Write a command byte to the display"""
    f.write(bytes([0x00, cmd]))  # Command byte is prefixed with 0x00

def write_data(f, data):
    """Write a data byte to the display"""
    if isinstance(data, int):
        data = [data]
    f.write(bytes([0x40] + list(data)))  # Data bytes are prefixed with 0x40

# Quick I2C display function without heavy dependencies
def quick_display_message():
    try:
        print(f"[{time.time() - start_time:.3f}s] Trying quick I2C display...")
        # Open I2C bus
        with io.open("/dev/i2c-1", "rb+", buffering=0) as f:
            # Set I2C slave address to 0x3C (standard for SSD1306)
            fcntl.ioctl(f, 0x0703, 0x3C)
            
            # Initialize display
            write_cmd(f, 0xAE)  # display off
            write_cmd(f, 0xD5)  # clock div
            write_cmd(f, 0x80)
            write_cmd(f, 0xA8)  # multiplex
            write_cmd(f, 0x3F)
            write_cmd(f, 0xD3)  # offset
            write_cmd(f, 0x00)
            write_cmd(f, 0x40)  # start line
            write_cmd(f, 0x8D)  # charge pump
            write_cmd(f, 0x14)
            write_cmd(f, 0x20)  # memory mode
            write_cmd(f, 0x00)
            write_cmd(f, 0xA1)  # seg remap
            write_cmd(f, 0xC8)  # com scan dec
            write_cmd(f, 0xDA)  # com pins
            write_cmd(f, 0x12)
            write_cmd(f, 0x81)  # contrast
            write_cmd(f, 0xCF)
            write_cmd(f, 0xD9)  # precharge
            write_cmd(f, 0xF1)
            write_cmd(f, 0xDB)  # vcom detect
            write_cmd(f, 0x40)
            write_cmd(f, 0xA4)  # resume
            write_cmd(f, 0xA6)  # normal
            write_cmd(f, 0xAF)  # display on

            # Set address range for full screen
            write_cmd(f, 0x21)  # column address
            write_cmd(f, 0)     # start
            write_cmd(f, 127)   # end
            write_cmd(f, 0x22)  # page address
            write_cmd(f, 0)     # start
            write_cmd(f, 7)     # end

            # Write "BOOT" in large pixels
            buffer = [0] * 1024  # 128x64 pixels = 1024 bytes
            
            # Simple "BOOT" pattern (very basic pixel art)
            pattern = [
                0x7E, 0x7E, 0x0C, 0x18, 0x7E, 0x7E,  # B
                0x7E, 0x7E, 0x66, 0x66, 0x7E, 0x7E,  # O
                0x7E, 0x7E, 0x66, 0x66, 0x7E, 0x7E,  # O
                0x7E, 0x7E, 0x18, 0x18, 0x18, 0x18   # T
            ]
            
            # Position in middle of screen (page 3-4, columns 40-70)
            for page in range(2):
                pos = 40 + (page + 3) * 128
                for i, b in enumerate(pattern):
                    buffer[pos + i] = b
            
            # Write buffer in chunks
            for i in range(0, len(buffer), 32):
                chunk = buffer[i:i+32]
                write_data(f, chunk)
                
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
