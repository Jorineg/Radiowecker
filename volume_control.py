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
        
        Display    Hardware
        0-20      0-50     (silent to very quiet)
        20-60     50-80    (quiet to medium)
        60-100    80-100   (medium to maximum)
        """
        if volume <= 0:
            return 0
        if volume >= 100:
            return 100
            
        # Linear interpolation in three ranges
        if volume <= 20:
            # 0-20 -> 0-50
            return int(volume * 2.5)  # Faktor 2.5
        elif volume <= 60:
            # 20-60 -> 50-80
            return int(50 + (volume - 20) * 0.75)  # Faktor 0.75
        else:
            # 60-100 -> 80-100
            return int(80 + (volume - 60) * 0.5)  # Faktor 0.5
        
    def _hardware_to_display(self, hw_vol: int) -> int:
        """Convert hardware volume (0-100) back to display volume (0-100)"""
        if hw_vol <= 0:
            return 0
        if hw_vol >= 100:
            return 100
            
        # Inverse mapping with different factors
        if hw_vol <= 50:
            # 0-50 -> 0-20
            return int(hw_vol / 2.5)  # Durch 2.5
        elif hw_vol <= 80:
            # 50-80 -> 20-60
            return int(20 + (hw_vol - 50) / 0.75)  # Durch 0.75
        else:
            # 80-100 -> 60-100
            return int(60 + (hw_vol - 80) / 0.5)  # Durch 0.5
        
    def get_volume(self) -> int:
        """Get current volume level (0-100)"""
        if not self.mixer:
            return 50
            
        try:
            hw_vol = self.mixer.getvolume()[0]
            return self._hardware_to_display(hw_vol)
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
