#!/usr/bin/env python3

import time
import sys
import signal
import fcntl
import io

# Log file for capturing I2C commands
log_file = open("/tmp/display_commands.txt", "w")

def log_bytes(prefix, data):
    """Log bytes in C array format"""
    if isinstance(data, int):
        data = [data]
    hex_str = ", ".join(f"0x{b:02X}" for b in data)
    log_file.write(f"// {prefix}\n")
    log_file.write(f"uint8_t {prefix.lower().replace(' ', '_')}[] = {{{hex_str}}};\n")
    log_file.flush()

def write_cmd(f, cmd):
    """Write a command byte to the display"""
    data = bytes([0x00, cmd])
    log_bytes(f"Command 0x{cmd:02X}", list(data))
    f.write(data)

def write_data(f, data):
    """Write a data byte to the display"""
    if isinstance(data, int):
        data = [data]
    full_data = bytes([0x40] + list(data))
    log_bytes("Data", list(full_data))
    f.write(full_data)

def show_boot():
    try:
        print(f"[{time.time() - start_time:.3f}s] Importing display module...")
        from display import OLEDDisplay
        print(f"[{time.time() - start_time:.3f}s] Display module imported")
        
        print(f"[{time.time() - start_time:.3f}s] Starting display init...")
        global display
        display = OLEDDisplay(128, 64)
        
        # Capture one frame of the welcome message
        display.clear()
        welcome_text = "Welcome"
        x_pos_welcome = (128 - len(welcome_text) * 8) // 2
        display.buffer.draw_text(x_pos_welcome, 10, welcome_text, size="8x16")
        
        status_text = "starting up..."
        x_pos_status = (128 - len(status_text) * 5) // 2
        display.buffer.draw_text(x_pos_status, 40, status_text, size="5x8")
        
        # Get the raw buffer
        buffer_data = display.buffer.get_buffer()
        log_bytes("Welcome Screen Buffer", list(buffer_data))
        
        # Now continue with normal display
        while True:
            display.clear()
            display.buffer.draw_text(x_pos_welcome, 10, welcome_text, size="8x16")
            display.buffer.draw_text(x_pos_status, 40, status_text, size="5x8")
            display.show()
            time.sleep(0.1)
            
    except Exception as e:
        print(f"[{time.time() - start_time:.3f}s] Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        log_file.close()

if __name__ == "__main__":
    start_time = time.time()
    show_boot()
