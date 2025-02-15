#!/usr/bin/env python3

from display import OLEDDisplay
import sys
import signal
import time

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
        global display
        # Initialize display (128x64 is standard for SSD1306)
        display = OLEDDisplay(128, 64)
        
        # Register signal handler for cleanup
        signal.signal(signal.SIGTERM, signal_handler)
        
        while True:
            display.clear()
            
            # Draw "Welcome" centered with large font
            welcome_text = "Welcome"
            # Calculate center position for 8x16 font
            x_pos_welcome = (128 - len(welcome_text) * 8) // 2  # 8 pixels per char in 8x16 font
            display.buffer.draw_text(x_pos_welcome, 10, welcome_text, size="8x16")
            
            # Draw "starting up..." centered with small font
            status_text = "starting up..."
            # Calculate center position for 5x8 font
            x_pos_status = (128 - len(status_text) * 5) // 2  # 5 pixels per char in 5x8 font
            display.buffer.draw_text(x_pos_status, 40, status_text, size="5x8")
            
            display.show()
            time.sleep(0.1)  # Small sleep to prevent CPU hogging
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    show_boot()
