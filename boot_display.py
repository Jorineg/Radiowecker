from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
import sys
import time
import signal

def signal_handler(signum, frame):
    # Clear display on termination
    try:
        device.clear()
        device.hide()
    except:
        pass
    sys.exit(0)

def show_boot():
    try:
        global device
        serial = i2c(port=1, address=0x3C)
        device = ssd1306(serial)
        
        # Register signal handler for cleanup
        signal.signal(signal.SIGTERM, signal_handler)
        
        while True:
            with canvas(device) as draw:
                draw.text((20, 20), "Starting...", fill="white")
            time.sleep(0.1)  # Small sleep to prevent CPU hogging
            
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    show_boot()
