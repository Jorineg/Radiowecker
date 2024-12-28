# main.py

import sys
import time
from typing import Optional

from display import Display, PygameDisplay, OLEDDisplay
from audio import AudioManager
from settings import Settings
from ui import UI
from hardware import HardwareInput, HardwareOutput, RPI_HARDWARE

try:
    import pygame  # Use pygame for Windows
    RPI_HARDWARE = False
except ImportError:
    RPI_HARDWARE = True
import signal

class RadioWecker:
    def __init__(self):
        self.running = True

        # Determine if running on Pi or PC
        self.is_pi = RPI_HARDWARE

        # Initialize components
        self.init_components()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def init_components(self):
        """Initialize all system components"""
        # Create display
        if self.is_pi:
            self.display = OLEDDisplay(128, 64)
        else:
            self.display = PygameDisplay(128, 64, scale=4)

        # Create other components
        self.settings = Settings()
        self.audio = AudioManager()
        self.ui = UI(self.display, self.settings, self.audio)
        self.hardware_out = HardwareOutput()

        # Setup hardware input with UI callback
        self.hardware_in = HardwareInput(self.ui.handle_button)
        # Connect hardware input to UI for button state monitoring
        self.ui.set_hardware_input(self.hardware_in)

        # Apply initial settings
        self.apply_settings()

    def apply_settings(self):
        """Apply current settings to hardware"""
        display_settings = self.settings.get_display_settings()

        # Set display brightness
        self.hardware_out.set_display_brightness(display_settings["brightness"])

    def check_alarms(self):
        """Check and handle alarms"""
        alarm = self.settings.check_alarms()
        if alarm > 0 and not self.audio.is_playing():
            # Wake from standby
            if self.ui.state.standby:
                self.ui.state.standby = False

            # Start alarm sound/radio
            if len(self.audio.stations) > 0:
                self.audio.play_station(self.audio.stations[0])

            # Update UI alarm indicator
            self.ui.state.alarm_mode |= alarm

    def update_status(self):
        """Update various status information"""
        # Update playing status
        self.ui.state.is_playing = self.audio.is_playing()

        # Enable/disable amp based on playing state
        self.hardware_out.set_amp_enable(self.ui.state.is_playing)

    def main_loop(self):
        """Main application loop"""
        last_time = time.time()

        while self.running:
            current_time = time.time()
            if current_time - last_time >= 1:
                self.check_alarms()
                self.update_status()
                last_time = current_time

            # Process any pending audio commands
            self.audio.process_commands()

            # Update display
            self.ui.render()
            self.display.show()

            # Small sleep to prevent busy waiting
            time.sleep(0.01)

    def cleanup(self):
        """Cleanup on exit"""
        self.running = False
        self.hardware_in.cleanup()
        self.hardware_out.cleanup()
        self.audio.stop()
        self.audio.cleanup()
        self.settings.save_settings()

    def signal_handler(self, signum, frame):
        """Handle system signals"""
        self.cleanup()
        sys.exit(0)


def main():
    """Application entry point"""
    app = RadioWecker()

    try:
        app.main_loop()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Cleaning up...")
        app.cleanup()


if __name__ == "__main__":
    main()
