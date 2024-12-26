#!/usr/bin/python3
import smbus2
import time

# Create SMBus object
bus = smbus2.SMBus(1)

try:
    # Try to write a command to the display
    bus.write_byte_data(0x3C, 0x00, 0xAE)  # Display off
    print("Write successful")
    time.sleep(1)
    bus.write_byte_data(0x3C, 0x00, 0xAF)  # Display on
    print("Display should be on now")
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    bus.close()
