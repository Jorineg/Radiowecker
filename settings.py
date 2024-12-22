# settings.py

import json
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List
from dataclasses import dataclass
from time import localtime


@dataclass
class MenuItem:
    name: str
    value_type: str  # "int", "time", "bool", "status"
    value: Any
    min_val: int = None
    max_val: int = None
    step: int = 1
    unit: str = ""

    def increase(self):
        if self.value_type == "int":
            self.value = min(self.max_val, self.value + self.step)
        elif self.value_type == "time":
            self.value = (self.value + 1) % (60 if self.max_val == 59 else 24)
        elif self.value_type == "bool":
            self.value = not self.value

    def decrease(self):
        if self.value_type == "int":
            self.value = max(self.min_val, self.value - self.step)
        elif self.value_type == "time":
            self.value = (self.value - 1) % (60 if self.max_val == 59 else 24)
        elif self.value_type == "bool":
            self.value = not self.value

    def format_value(self) -> List[str]:
        """Format value for display, returns list of lines"""
        if self.value_type == "time":
            return [f"{self.value:02d}"]
        elif self.value_type == "bool":
            return ["AN" if self.value else "AUS"]
        elif self.value_type == "status":
            return self.value.split("\n")
        return [f"{self.value}{self.unit}"]


class Settings:
    def __init__(self):
        # Menu items
        self.items: List[MenuItem] = [
            MenuItem("Wecker1 Stunden", "time", 7, 0, 23),
            MenuItem("Wecker1 Minuten", "time", 0, 0, 59),
            MenuItem("Wecker2 Stunden", "time", 8, 0, 23),
            MenuItem("Wecker2 Minuten", "time", 0, 0, 59),
            MenuItem("Display Kontrast", "int", 128, 0, 255),
            MenuItem("Uhr im Standby", "bool", True),
            MenuItem("Helligkeit", "int", 100, 10, 100, 10, "%"),
            MenuItem("Status Info", "status", ""),  # Status menu item
        ]

        self.current_item = 0
        self.config_file = "settings.json"
        self.load_settings()

    def next_item(self) -> bool:
        """Move to next menu item. Returns True if moved, False if at last item"""
        if self.current_item < len(self.items) - 1:
            self.current_item += 1
            return True
        return False

    def at_last_item(self) -> bool:
        """Check if we're at the last menu item"""
        return self.current_item >= len(self.items) - 1

    def get_next_item(self) -> MenuItem:
        """Get next menu item without moving to it"""
        next_idx = self.current_item + 1
        if next_idx < len(self.items):
            return self.items[next_idx]
        return None

    def prev_item(self):
        """Move to previous menu item"""
        self.current_item = (self.current_item - 1) % len(self.items)

    def get_current_item(self) -> MenuItem:
        """Get currently selected menu item"""
        item = self.items[self.current_item]
        
        # Update status info dynamically
        if item.value_type == "status":
            git_info = get_git_info()
            cpu_temp = get_cpu_temp()
            item.value = f"{git_info}\n{cpu_temp}"
            
        return item

    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    for item in self.items:
                        if item.name in data:
                            item.value = data[item.name]
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Save settings to JSON file"""
        try:
            data = {item.name: item.value for item in self.items}
            with open(self.config_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get_value(self, name: str) -> Any:
        """Get value of a setting by name"""
        for item in self.items:
            if item.name == name:
                return item.value
        return None

    def check_alarms(self) -> int:
        """Check if any alarm should trigger
        Returns: 0=none, 1=alarm1, 2=alarm2"""
        current = localtime()
        h, m = current.tm_hour, current.tm_min

        # Check Alarm 1
        if h == self.get_value("Wecker1 Stunden") and m == self.get_value(
            "Wecker1 Minuten"
        ):
            return 1

        # Check Alarm 2
        if h == self.get_value("Wecker2 Stunden") and m == self.get_value(
            "Wecker2 Minuten"
        ):
            return 2

        return 0

    def get_display_settings(self) -> Dict[str, int]:
        """Get display-related settings"""
        return {
            "contrast": self.get_value("Display Kontrast"),
            "brightness": self.get_value("Helligkeit"),
            "show_clock": self.get_value("Uhr im Standby"),
        }

    def reset_to_first(self):
        """Reset selection to first menu item"""
        self.current_item = 0


def get_git_info():
    try:
        # Get last commit hash
        hash_cmd = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                capture_output=True, text=True)
        commit_hash = hash_cmd.stdout.strip() if hash_cmd.returncode == 0 else "N/A"
        
        # Get last modified date
        date_cmd = subprocess.run(['git', 'log', '-1', '--format=%cd', '--date=format:%d.%m.%y'],
                                capture_output=True, text=True)
        last_change = date_cmd.stdout.strip() if date_cmd.returncode == 0 else "N/A"
        
        return f"Ver: {last_change}, {commit_hash}"
    except:
        return "Ver: N/A"

def get_cpu_temp():
    try:
        # For Raspberry Pi
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000
        return f"Temp: {temp:.1f}°C"
    except:
        return "Temp: N/A"
