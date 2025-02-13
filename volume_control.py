"""Volume control for ALSA/PulseAudio"""
import subprocess
import re
from typing import Optional

class VolumeControl:
    def __init__(self):
        # Try to detect if we're using ALSA or Pulse
        try:
            subprocess.run(['pulseaudio', '--version'], capture_output=True)
            self.use_pulse = True
        except FileNotFoundError:
            self.use_pulse = False

    def get_volume(self) -> int:
        """Get current volume level (0-100)"""
        if self.use_pulse:
            try:
                result = subprocess.run(['pactl', 'get-sink-volume', '@DEFAULT_SINK@'], 
                                     capture_output=True, text=True)
                match = re.search(r'(\d+)%', result.stdout)
                if match:
                    return int(match.group(1))
            except:
                pass
        else:
            try:
                result = subprocess.run(['amixer', 'get', 'Master'], 
                                     capture_output=True, text=True)
                match = re.search(r'(\d+)%', result.stdout)
                if match:
                    return int(match.group(1))
            except:
                pass
        return 50  # Default if we can't get the actual volume

    def set_volume(self, volume: int):
        """Set volume level (0-100)"""
        volume = max(0, min(100, volume))  # Clamp between 0 and 100
        if self.use_pulse:
            try:
                subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{volume}%'])
            except:
                pass
        else:
            try:
                subprocess.run(['amixer', 'set', 'Master', f'{volume}%'])
            except:
                pass

    def volume_up(self, step: int = 5):
        """Increase volume by step"""
        current = self.get_volume()
        self.set_volume(current + step)
        return self.get_volume()

    def volume_down(self, step: int = 5):
        """Decrease volume by step"""
        current = self.get_volume()
        self.set_volume(current - step)
        return self.get_volume()
