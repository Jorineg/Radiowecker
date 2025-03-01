# bluetooth_utils.py - Bluetooth audio management utilities

import subprocess
import time
from typing import Tuple, Optional


def get_bluetooth_info() -> Tuple[str, str, str]:
    """
    Get information about the currently playing Bluetooth track
    Returns title, artist, status
    """
    try:
        # Get status with bluetoothctl
        process = subprocess.Popen(
            ["bluetoothctl", "info"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT
        )
        stdout, _ = process.communicate(timeout=2)
        bt_info = stdout.decode('utf-8')
        
        # Default values
        title = "Unknown Title"
        artist = "Unknown Artist"
        status = "Stopped"
        
        # Check if device is connected
        if "Connected: yes" not in bt_info:
            return "No Device", "Not Connected", "Stopped"
            
        # Parse track info
        if "Track Title:" in bt_info:
            title_line = [line for line in bt_info.split('\n') if "Track Title:" in line]
            if title_line:
                title = title_line[0].split("Track Title:")[1].strip()
        
        if "Track Artist:" in bt_info:
            artist_line = [line for line in bt_info.split('\n') if "Track Artist:" in line]
            if artist_line:
                artist = artist_line[0].split("Track Artist:")[1].strip()
        
        if "Track Status:" in bt_info:
            status_line = [line for line in bt_info.split('\n') if "Track Status:" in line]
            if status_line:
                status = status_line[0].split("Track Status:")[1].strip()
                
        return title, artist, status
        
    except Exception as e:
        print(f"Error getting Bluetooth info: {e}")
        return "Error", str(e), "Error"


def toggle_bluetooth_mute(mute: bool = True) -> bool:
    """
    Toggle Bluetooth audio mute state
    Returns True if successful, False otherwise
    """
    try:
        # Get the default sink
        sink_process = subprocess.Popen(
            ["pactl", "get-default-sink"], 
            stdout=subprocess.PIPE
        )
        sink_output, _ = sink_process.communicate(timeout=2)
        default_sink = sink_output.decode('utf-8').strip()
        
        # Check if this looks like a Bluetooth sink
        if "bluez" not in default_sink and "bluetooth" not in default_sink:
            print(f"Warning: Default sink {default_sink} doesn't appear to be Bluetooth")
        
        # Set the volume
        volume_cmd = ["pactl", "set-sink-volume", default_sink, "0%" if mute else "100%"]
        subprocess.run(volume_cmd, check=True, timeout=2)
        
        # Set mute state 
        mute_cmd = ["pactl", "set-sink-mute", default_sink, "1" if mute else "0"]
        subprocess.run(mute_cmd, check=True, timeout=2)
        
        print(f"Bluetooth {'muted' if mute else 'unmuted'} successfully")
        return True
        
    except Exception as e:
        print(f"Error {'muting' if mute else 'unmuting'} Bluetooth: {e}")
        return False


def get_connected_bluetooth_device() -> Optional[str]:
    """Get the name of the currently connected Bluetooth device, or None if none is connected"""
    try:
        process = subprocess.Popen(
            ["bluetoothctl", "info"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT
        )
        stdout, _ = process.communicate(timeout=2)
        bt_info = stdout.decode('utf-8')
        
        # Check if device is connected
        if "Connected: yes" not in bt_info:
            return None
            
        # Try to get device name
        if "Name:" in bt_info:
            name_line = [line for line in bt_info.split('\n') if "Name:" in line]
            if name_line:
                return name_line[0].split("Name:")[1].strip()
                
        # Fallback to device address
        if "Device " in bt_info:
            addr_line = [line for line in bt_info.split('\n') if "Device " in line]
            if addr_line:
                return addr_line[0].split("Device ")[1].strip()
                
        return "Unknown Device"
    except Exception as e:
        print(f"Error getting Bluetooth device: {e}")
        return None
