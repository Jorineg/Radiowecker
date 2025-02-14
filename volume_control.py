"""Volume control for DigiAMP+ (PCM5122 DAC)"""
import math
import alsaaudio

class VolumeControl:
    def __init__(self):
        # Initialize with Digital control for PCM5122 DAC
        try:
            self.mixer = alsaaudio.Mixer('Digital', cardindex=0)
        except alsaaudio.ALSAAudioError:
            print("Error: Could not initialize Digital mixer")
            self.mixer = None
            
    def _scale_to_hardware(self, volume: int) -> int:
        """Convert linear volume (0-100) to exponential scale for more natural volume control
        
        At volume = 0: -99999.99dB (mute)
        At volume = 25: ~ -40dB
        At volume = 50: ~ -20dB
        At volume = 75: ~ -10dB
        At volume = 100: 0dB
        """
        if volume <= 0:
            return 0
        if volume >= 100:
            return 100
            
        # Exponential scaling for more natural volume control
        # This creates a curve that gives more control in the useful volume range
        exp = 3  # Adjust this to change the curve shape
        scaled = math.pow(volume / 100.0, exp) * 100
        return int(scaled)
        
    def get_volume(self) -> int:
        """Get current volume level (0-100)"""
        if not self.mixer:
            return 50
            
        try:
            hw_vol = self.mixer.getvolume()[0]  # Returns list of volumes for each channel
            # Convert back from hardware scale to linear
            return int(math.pow(hw_vol / 100.0, 1/3) * 100)
        except:
            return 50

    def set_volume(self, volume: int):
        """Set volume level (0-100)
        
        The input volume is treated as a linear scale (0-100)
        but is converted to an exponential scale for the hardware
        to provide more natural volume control.
        """
        if not self.mixer:
            return
            
        volume = max(0, min(100, volume))  # Clamp between 0 and 100
        hw_volume = self._scale_to_hardware(volume)
        
        try:
            self.mixer.setvolume(hw_volume)
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
