#!/usr/bin/python3
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
import time

try:
    # Initialize I2C
    serial = i2c(port=1, address=0x3C)
    print("I2C initialized")
    
    # Initialize display
    device = ssd1306(serial, width=128, height=64)
    print("Display initialized")
    
    # Draw something
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="black")
        draw.text((30, 40), "Test", fill="white")
    print("Drawing completed")
    
    time.sleep(5)

except Exception as e:
    print(f"Error: {str(e)}")
    print(f"Error type: {type(e)}")
