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
        """Convert display volume (0-100) to hardware volume (0-100)
        
        Display    Hardware    Effect
        0-5       0-50        Silent to very quiet (mapped to small range)
        5-100     50-100      Usable volume range (linear mapping)
        """
        if volume <= 0:
            return 0
        if volume >= 100:
            return 100
            
        if volume <= 5:
            # Map 0-5 to 0-50 (silent range)
            return int(volume * 10)
        else:
            # Map 5-100 to 50-100 (usable range)
            return int(50 + (volume - 5) * 0.526)
        
    def get_volume(self) -> int:
        """Get current volume level (0-100)"""
        if not self.mixer:
            return 50
            
        try:
            hw_vol = self.mixer.getvolume()[0]
            
            # Convert hardware volume back to display volume
            if hw_vol <= 50:
                # Map 0-50 back to 0-5
                return int(hw_vol / 10)
            else:
                # Map 50-100 back to 5-100
                return int(5 + (hw_vol - 50) / 0.526)
        except:
            return 50

    def set_volume(self, volume: int):
        """Set volume level (0-100)"""
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
