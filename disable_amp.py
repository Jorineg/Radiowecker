import RPi.GPIO as GPIO
from gpio_pins import AMP_MUTE

GPIO.setmode(GPIO.BCM)
GPIO.setup(AMP_MUTE, GPIO.OUT)  # Amp enable
GPIO.output(AMP_MUTE, False)