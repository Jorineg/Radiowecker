# hardware.py

import time
from typing import Callable, Optional
import threading
try:
    import RPi.GPIO as GPIO

    RPI_HARDWARE = True
except ImportError:
    RPI_HARDWARE = False
    import pygame  # Use pygame for Windows
    import keyboard  # Keyboard library for PC testing

class Button:
    def __init__(self, pin: int, name: str):
        self.pin = pin
        self.name = name
        self.pressed = False
        self.press_time = 0
        self.long_press_triggered = False

        # Constants
        self.DEBOUNCE_TIME = 0.05  # 50ms
        self.LONG_PRESS_TIME = 0.8  # 800ms


class PygameManager:
    _instance = None

    @staticmethod
    def get_instance():
        if PygameManager._instance is None:
            PygameManager._instance = PygameManager()
        return PygameManager._instance

    def __init__(self):
        pygame.init()
        self.button_map = {
            pygame.K_p: "power",
            pygame.K_s: "source",
            pygame.K_m: "menu",
            pygame.K_LEFT: "backward",
            pygame.K_RIGHT: "forward",
        }
        self.running = True

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False
            elif event.type == pygame.KEYDOWN:
                button_name = self.button_map.get(event.key)
                if button_name is not None:
                    return button_name, True
            elif event.type == pygame.KEYUP:
                button_name = self.button_map.get(event.key)
                if button_name is not None:
                    return button_name, False
        return None

    def cleanup(self):
        """Cleanup pygame resources"""
        pygame.quit()


class HardwareInput:
    def __init__(self, callback: Callable[[str, bool], None]):
        self.callback = callback
        self.running = True

        # Button definitions
        self.buttons = {
            "power": Button(22, "Power"),
            "source": Button(23, "Source"),
            "menu": Button(27, "Menu"),
            "backward": Button(24, "Backward"),
            "forward": Button(5, "Forward"),
        }

        if RPI_HARDWARE:
            self.setup_gpio()
        else:
            # Key mappings for PC testing
            self.key_map = {
                'p': "power",
                'm': "menu",
                's': "source",
                'right': "forward",
                'left': "backward",
            }

        # Start input thread
        self.thread = threading.Thread(target=self.input_loop, daemon=True)
        self.thread.start()

    def setup_gpio(self):
        """Setup GPIO pins for buttons"""
        GPIO.setmode(GPIO.BCM)
        for button in self.buttons.values():
            GPIO.setup(button.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def cleanup(self):
        """Cleanup GPIO and other resources"""
        self.running = False
        if RPI_HARDWARE:
            GPIO.cleanup()

    def input_loop(self):
        """Main input processing loop"""
        while self.running:
            if RPI_HARDWARE:
                self.check_gpio_buttons()
            else:
                self.check_keyboard()
            time.sleep(0.033)  # ~30 Hz polling rate

    def process_button_state(self, button_name: str, button: Button, state: bool):
        """Common button state processing logic"""
        current_time = time.time()

        if state and not button.pressed:
            # Button just pressed
            button.pressed = True
            button.press_time = current_time
            button.long_press_triggered = False

        elif state and button.pressed:
            # Button being held
            if not button.long_press_triggered and current_time - button.press_time >= button.LONG_PRESS_TIME:
                # Long press detected
                if button_name != "forward" and button_name != "backward":
                    button.long_press_triggered = True
                self.callback(button_name, True)

        elif not state and button.pressed:
            # Button released
            if current_time - button.press_time >= button.DEBOUNCE_TIME and not button.long_press_triggered:
                # Short press detected
                self.callback(button_name, False)
            button.pressed = False

    def check_gpio_buttons(self):
        """Check physical button states"""
        for name, button in self.buttons.items():
            # Read button state (inverted because of pull-up)
            state = not GPIO.input(button.pin)
            self.process_button_state(name, button, not state)

    def check_keyboard(self):
        """Check keyboard input for PC testing - sensor-like implementation"""
        for key, button_name in self.key_map.items():
            button = self.buttons[button_name]
            # Read key state directly, like a sensor
            try:
                state = keyboard.is_pressed(key)
                self.process_button_state(button_name, button, state)
            except:
                # Handle any keyboard library errors gracefully
                pass


class HardwareOutput:
    def __init__(self):
        if RPI_HARDWARE:
            GPIO.setmode(GPIO.BCM)
            # Setup PWM pins for audio amp enable
            GPIO.setup(4, GPIO.OUT)  # Amp enable
            self.amp_enabled = False
            GPIO.output(4, False)
        else:
            self.amp_enabled = False

    def set_amp_enable(self, enable: bool):
        """Enable/disable audio amplifier"""
        self.amp_enabled = enable
        if RPI_HARDWARE:
            GPIO.output(4, enable)

    def cleanup(self):
        """Cleanup on exit"""
        if RPI_HARDWARE:
            GPIO.cleanup()
