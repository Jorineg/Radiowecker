# hardware.py

import time
from typing import Callable, Optional
import threading
from gpio_pins import *  # Import GPIO pin definitions
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
        self.last_press_time = 0
        self.DEBOUNCE_TIME = 0.05  # 50ms


class RotaryEncoder:
    def __init__(self, pin_a: int, pin_b: int, pin_sw: int, name: str):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.pin_sw = pin_sw
        self.name = name
        self.last_state_a = 0
        self.last_state_b = 0
        self.switch_pressed = False
        self.last_press_time = 0
        self.DEBOUNCE_TIME = 0.05  # 50ms


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
            pygame.K_LEFT: "alarm1",   # Changed from backward
            pygame.K_RIGHT: "alarm2",  # Changed from forward
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
            "power": Button(TOUCH_POWER, "Power"),
            "source": Button(TOUCH_SOURCE, "Source"),
            "menu": Button(TOUCH_MENU, "Menu"),
            "alarm1": Button(TOUCH_BACKWARD, "Alarm 1"),  # Renamed from backward
            "alarm2": Button(TOUCH_FORWARD, "Alarm 2"),   # Renamed from forward
        }

        # Rotary Encoder definitions
        self.encoders = {
            "volume": RotaryEncoder(ROTARY1_A, ROTARY1_B, ROTARY1_SW, "Volume"),
            "control": RotaryEncoder(ROTARY2_A, ROTARY2_B, ROTARY2_SW, "Control")
        }

        if RPI_HARDWARE:
            # Ensure GPIO mode is set before any GPIO operations
            GPIO.setwarnings(False)  # Disable warnings
            GPIO.setmode(GPIO.BCM)
            self.setup_gpio()
        else:
            # Key mappings for PC testing
            self.key_map = {
                'p': "power",
                'm': "menu",
                's': "source",
                '1': "alarm1",
                '2': "alarm2",
                # Encoder simulation keys
                'up': "volume_up",
                'down': "volume_down",
                'v': "volume_press",
                'right': "control_right",
                'left': "control_left",
                'c': "control_press",
            }

        # Start input thread
        self.thread = threading.Thread(target=self.input_loop, daemon=True)
        self.thread.start()

    def setup_gpio(self):
        """Setup GPIO pins for buttons and encoders"""
        # Setup touch buttons with pull-down (active high)
        for button in self.buttons.values():
            GPIO.setup(button.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Setup encoders with pull-up (active low)
        for encoder in self.encoders.values():
            GPIO.setup(encoder.pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(encoder.pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(encoder.pin_sw, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def process_button(self, button_name: str, button: Button, state: bool):
        """Simplified button processing - only handle press with debounce"""
        current_time = time.time()
        
        if state and not button.pressed:
            if current_time - button.last_press_time >= button.DEBOUNCE_TIME:
                button.pressed = True
                button.last_press_time = current_time
                self.callback(button_name, True)
        elif not state and button.pressed:
            button.pressed = False

    def process_encoder(self, encoder: RotaryEncoder):
        """Process rotary encoder state"""
        if not RPI_HARDWARE:
            return
            
        # Read current states (inverted because of pull-up)
        state_a = not GPIO.input(encoder.pin_a)
        state_b = not GPIO.input(encoder.pin_b)
        state_sw = not GPIO.input(encoder.pin_sw)
        
        # Process rotary movement
        if state_a != encoder.last_state_a:
            if state_a != state_b:
                self.callback(f"{encoder.name.lower()}_ccw", True)  # Counter-clockwise
            else:
                self.callback(f"{encoder.name.lower()}_cw", True)   # Clockwise
        
        # Process switch with debounce
        current_time = time.time()
        if state_sw and not encoder.switch_pressed:
            if current_time - encoder.last_press_time >= encoder.DEBOUNCE_TIME:
                encoder.switch_pressed = True
                encoder.last_press_time = current_time
                self.callback(f"{encoder.name.lower()}_press", True)
        elif not state_sw and encoder.switch_pressed:
            encoder.switch_pressed = False
        
        # Update last states
        encoder.last_state_a = state_a
        encoder.last_state_b = state_b

    def check_gpio_buttons(self):
        """Check physical button and encoder states"""
        # Check touch buttons
        for name, button in self.buttons.items():
            state = GPIO.input(button.pin)  # Active high for touch buttons
            self.process_button(name, button, state)
        
        # Check encoders
        for encoder in self.encoders.values():
            self.process_encoder(encoder)

    def check_keyboard(self):
        """Check keyboard input for PC testing"""
        for key, action in self.key_map.items():
            try:
                if keyboard.is_pressed(key):
                    if action in self.buttons:
                        self.process_button(action, self.buttons[action], True)
                    else:
                        # Simulate encoder actions directly
                        self.callback(action, True)
            except:
                pass

    def input_loop(self):
        """Main input processing loop"""
        while self.running:
            if RPI_HARDWARE:
                self.check_gpio_buttons()
            else:
                self.check_keyboard()
            time.sleep(0.033)  # ~30 Hz polling rate

    def cleanup(self):
        """Cleanup GPIO and other resources"""
        self.running = False
        if RPI_HARDWARE:
            GPIO.cleanup()


class HardwareOutput:
    def __init__(self):
        if RPI_HARDWARE:
            # Ensure GPIO mode is set before any GPIO operations
            GPIO.setwarnings(False)  # Disable warnings
            GPIO.setmode(GPIO.BCM)
            # Setup PWM pins for audio amp enable
            GPIO.setup(AMP_MUTE, GPIO.OUT)  # Amp enable
            self.amp_enabled = False
            GPIO.output(AMP_MUTE, False)
        else:
            self.amp_enabled = False

    def set_amp_enable(self, enable: bool):
        """Enable/disable audio amplifier"""
        self.amp_enabled = enable
        if RPI_HARDWARE:
            GPIO.output(AMP_MUTE, enable)

    def cleanup(self):
        """Cleanup on exit"""
        if RPI_HARDWARE:
            GPIO.cleanup()
