#!/usr/bin/python3
import time
import RPi.GPIO as GPIO
from smbus2 import SMBus

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Constants
DISPLAY_ADDRESS = 0x3C
COMMAND_MODE = 0x00
DATA_MODE = 0x40

def send_command(bus, cmd):
    try:
        bus.write_byte_data(DISPLAY_ADDRESS, COMMAND_MODE, cmd)
        print(f"Command {hex(cmd)} sent successfully")
    except Exception as e:
        print(f"Error sending command {hex(cmd)}: {str(e)}")

try:
    print("Initializing I2C bus...")
    bus = SMBus(1)
    time.sleep(0.1)

    print("Sending initialization sequence...")
    # Display off
    send_command(bus, 0xAE)
    time.sleep(0.1)
    
    # Set display clock div
    send_command(bus, 0xD5)
    send_command(bus, 0x80)
    
    # Set multiplex
    send_command(bus, 0xA8)
    send_command(bus, 0x3F)
    
    # Set display offset
    send_command(bus, 0xD3)
    send_command(bus, 0x00)
    
    # Set start line
    send_command(bus, 0x40)
    
    # Charge pump
    send_command(bus, 0x8D)
    send_command(bus, 0x14)
    
    # Memory mode
    send_command(bus, 0x20)
    send_command(bus, 0x00)
    
    # Set segment remap
    send_command(bus, 0xA1)
    
    # COM scan direction
    send_command(bus, 0xC8)
    
    # Set COM pins
    send_command(bus, 0xDA)
    send_command(bus, 0x12)
    
    # Set contrast
    send_command(bus, 0x81)
    send_command(bus, 0xCF)
    
    # Set precharge
    send_command(bus, 0xD9)
    send_command(bus, 0xF1)
    
    # Set VCOM detect
    send_command(bus, 0xDB)
    send_command(bus, 0x40)
    
    # Display all on resume
    send_command(bus, 0xA4)
    
    # Normal display
    send_command(bus, 0xA6)
    
    # Display on
    send_command(bus, 0xAF)
    
    print("Initialization complete")

except Exception as e:
    print(f"Error: {str(e)}")
finally:
    try:
        bus.close()
    except:
        pass
    GPIO.cleanup()
