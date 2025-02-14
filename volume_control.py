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
        
        Maps the user-visible volume (0-100) to hardware volume (0-100)
        in a way that provides useful volume control:
        
        User    Hardware    dB
        0       0          mute
        20      50         -51.5dB  (very quiet)
        40      75         -25.8dB  (quiet)
        60      87         -13.4dB  (medium)
        80      95         -5.2dB   (loud)
        100     100        0dB      (maximum)
        """
        if volume <= 0:
            return 0
        if volume >= 100:
            return 100
            
        # Linear interpolation in three ranges for better control
        if volume < 20:
            # 0-20 -> 0-50 (very low volumes)
            return int(volume * 2.5)
        elif volume < 60:
            # 20-60 -> 50-87 (normal listening range)
            return int(50 + (volume - 20) * 0.925)
        else:
            # 60-100 -> 87-100 (high volumes)
            return int(87 + (volume - 60) * 0.325)
        
    def _hardware_to_display(self, hw_vol: int) -> int:
        """Convert hardware volume (0-100) back to display volume (0-100)
        
        This is the inverse of _scale_to_hardware
        """
        if hw_vol <= 0:
            return 0
        if hw_vol >= 100:
            return 100
            
        # Inverse of the linear interpolation
        if hw_vol < 50:
            # 0-50 -> 0-20
            return int(hw_vol / 2.5)
        elif hw_vol < 87:
            # 50-87 -> 20-60
            return int(20 + (hw_vol - 50) / 0.925)
        else:
            # 87-100 -> 60-100
            return int(60 + (hw_vol - 87) / 0.325)
        
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
