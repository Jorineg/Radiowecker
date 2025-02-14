"""Volume control for ALSA"""
import subprocess
import re
from typing import Optional

class VolumeControl:
    def __init__(self):
        # Initialize with Master volume control
        self.control = 'Master'
        self.card = '0'
        
    def get_volume(self) -> int:
        """Get current volume level (0-100)"""
        try:
            result = subprocess.run(['amixer', '-c', self.card, 'get', self.control], 
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
        try:
            subprocess.run(['amixer', '-c', self.card, 'set', self.control, f'{volume}%'])
        except:
            pass

    def volume_up(self, step: int = 2):
        """Increase volume by step"""
        current = self.get_volume()
        self.set_volume(current + step)
        return self.get_volume()

    def volume_down(self, step: int = 2):
        """Decrease volume by step"""
        current = self.get_volume()
        self.set_volume(current - step)
        return self.get_volume()
