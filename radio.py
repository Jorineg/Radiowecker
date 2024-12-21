#!/usr/bin/env python3
"""
Revised RadioWecker Implementation

Highlights / Changes:
1. A more detailed display layout that tries to match the user's original specification:
   - Top line: show current source (left), show time (right), show small icons for active alarms.
   - Main area: differs by source:
     • Radio view: show frequency, station name, RDS text.
     • USB view: show 3-line file explorer (with highlight on the middle line).
     • Internet Radio view: show currently selected station name.
     • Bluetooth view: show BT info (placeholder).
   - Button press states indicated by small circles or dots at the bottom (simulating sensor/hardware feedback).
2. When switching away from Internet radio, the code stops playback so it doesn't continue in the background.
3. USB folder display is now rendered as a 3-line “window,” if enough files/folders exist.
4. A simple "run_startup_commands" function demonstrates temperature reading, GIT version, and (optionally) a “git pull” or other system calls. 
   This is simplified—customize as you wish for your environment.
5. In PC mode:
   - The code uses PyGame for display (128×64 scaled up).
   - Keyboard inputs 1..5 (or any remapped set) simulate the five touch sensors.
   - python-vlc is used for audio playback (local files, streams).
6. If your CSV for Internet radio contains direct .m3u references, you may need to parse or resolve them. This code currently just attempts to play them directly with VLC. 
   If you find them to be ephemeral, consider calling an API or parsing the .m3u on each attempt.
   
To run:
- On Windows (PC_MODE=True), install python-vlc and pygame:
    pip install python-vlc pygame
- Optionally place a stations.csv in the same folder for internet radio stations:
    StationName,http://url.or.m3u
- Place at least one folder with .mp3/.wav files to test USB view (the code defaults usb_root to current working directory).
- Press keys 1..5 (mapped to power, source, menu, forward, backward).
"""

import os
import sys
import time
import random
import subprocess
from datetime import datetime

try:
    import pygame
    from pygame.locals import QUIT, KEYDOWN

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import vlc

    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False

# Attempt RPi-specific imports
try:
    import RPi.GPIO as GPIO

    RPI_HARDWARE = True
except ImportError:
    RPI_HARDWARE = False

###############################################################################
# Configurations
###############################################################################
PC_MODE = True  # Set to False on the Raspberry Pi to enable real hardware usage.
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

# Key bindings for PC_MODE
KEY_BINDINGS = {
    "power": pygame.K_1,
    "source": pygame.K_2,
    "menu": pygame.K_3,
    "forward": pygame.K_4,
    "backward": pygame.K_5,
}

###############################################################################
# Utility / Hardware Stubs
###############################################################################


def run_startup_commands(pc_mode: bool):
    """
    Example function to run on application startup:
    - Optionally run git commands
    - Check temperature
    - Display version info
    Customize or expand as needed.
    """
    # We'll just read the CPU temp, do a version check, optionally do a "git pull" if desired
    temp = get_cpu_temperature()
    commit_hash, last_change = get_git_version_info()
    if not pc_mode:
        # On a real environment, you might do something like:
        # subprocess.run(["git", "pull"], check=False)
        pass
    print(
        f"[STARTUP] CPU Temp: {temp}C | Git Commit: {commit_hash[:7]} | Last Change: {last_change}"
    )


def init_hardware():
    """
    Hardware initialization. For Pi usage, set up GPIO or i2c.
    In PC_MODE, do nothing.
    """
    if PC_MODE:
        print("[INIT] PC_MODE active. Skipping real hardware init.")
    else:
        if RPI_HARDWARE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            # Example for TTP223 sensors, or other hardware config:
            # GPIO.setup(<pin>, GPIO.IN)
            print("[INIT] Raspberry Pi hardware init done.")
        else:
            print("[INIT] Not real Pi environment, skipping hardware init.")


def read_touch_sensors():
    """
    On Raspberry Pi, read the 5 TTP223 sensors from GPIO pins.
    Returns a dict: { 'power': bool, 'source': bool, 'menu': bool, 'forward': bool, 'backward': bool }
    In PC_MODE, we do key-based reading in the main loop, so this returns all False here.
    """
    if PC_MODE:
        return {
            "power": False,
            "source": False,
            "menu": False,
            "forward": False,
            "backward": False,
        }
    else:
        # Real code would read GPIO pins.
        return {
            "power": False,
            "source": False,
            "menu": False,
            "forward": False,
            "backward": False,
        }


def get_cpu_temperature():
    """
    Get the CPU temperature. On Pi, read from /sys.
    Returns a float or string if PC_MODE.
    """
    if PC_MODE:
        return 42.0
    else:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                val = f.read().strip()
                return round(float(val) / 1000.0, 1)
        return "N/A"


def get_git_version_info():
    """
    Retrieve git commit hash and last change time.
    In PC_MODE, returns placeholders.
    """
    if PC_MODE:
        return ("DemoCommitHash", "2024-12-20 10:00:00")
    else:
        try:
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], encoding="utf-8"
            ).strip()
            last_change = subprocess.check_output(
                ["git", "log", "-1", "--format=%cd"], encoding="utf-8"
            ).strip()
            return (commit_hash, last_change)
        except:
            return ("UnknownHash", "UnknownDate")


###############################################################################
# Radio FM stubs
###############################################################################


def read_radio_rds():
    """
    If we had a real RDA5807 or TEA5767 module, read station name & text via RDS.
    PC_MODE returns random station name & text.
    """
    station_names = ["RadioOne", "ClassicFM", "JazzBeats", "LocalNews"]
    station_texts = [
        "All the hits!",
        "Mostly classical tunes.",
        "Cool jazz tracks.",
        "News and talk radio.",
    ]
    return random.choice(station_names), random.choice(station_texts)


def search_radio(direction):
    """
    Simulate searching for next/previous radio frequency.
    Return new frequency as float.
    """
    return round(random.uniform(76.0, 108.0), 2)


###############################################################################
# Audio Player (uses VLC)
###############################################################################


class AudioPlayer:
    """
    A minimal audio player that uses python-vlc to play local files or streams.
    """

    def __init__(self):
        self.instance = None
        self.player = None
        if not VLC_AVAILABLE:
            print("[AUDIO] python-vlc not available. Audio playback won't work.")
        else:
            self.instance = vlc.Instance()
            self.player = self.instance.media_player_new()

    def play(self, source: str):
        """
        Play local file or network stream from 'source' (path or URL).
        """
        if not self.player:
            print("[AUDIO] No VLC player instance.")
            return
        media = self.instance.media_new(source)
        self.player.set_media(media)
        self.player.play()
        print(f"[AUDIO] Playing => {source}")

    def stop(self):
        """
        Stop playback if playing.
        """
        if self.player:
            self.player.stop()

    def is_playing(self):
        """
        Return True if the player is currently playing something.
        """
        if self.player:
            return self.player.is_playing() == 1
        return False


###############################################################################
# USB File Navigation
###############################################################################


def list_audio_files(path: str):
    """
    Return a list of (name, is_dir) for .mp3/.wav plus subfolders,
    plus "zurueck" and "dieser Ordner" as feasible.
    """
    if not os.path.isdir(path):
        return []

    items = []
    # Add pseudo-options:
    items.append(("zurueck", False))
    items.append(("dieser Ordner", False))

    try:
        dir_entries = os.listdir(path)
    except OSError:
        return items

    # Sort for consistency
    sorted_list = sorted(dir_entries, key=str.lower)
    for entry in sorted_list:
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            items.append((entry, True))
        else:
            lower_entry = entry.lower()
            if lower_entry.endswith(".mp3") or lower_entry.endswith(".wav"):
                items.append((entry, False))
    return items


###############################################################################
# Internet Radio (CSV Loader)
###############################################################################


def read_station_csv(csv_path: str):
    """
    Return list of (station_name, url) from CSV lines.
    Format: station_name,stream_url
    """
    if not os.path.isfile(csv_path):
        return []
    stations = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            name, url = line.split(",", 1)
            stations.append((name.strip(), url.strip()))
    return stations


###############################################################################
# Main Application
###############################################################################


class RadioWecker:
    def __init__(self, pc_mode=True):
        self.pc_mode = pc_mode

        # Alarms
        self.wecker1_active = False
        self.wecker2_active = False
        self.wecker1_hour = 6
        self.wecker1_minute = 0
        self.wecker2_hour = 7
        self.wecker2_minute = 30

        # Standby
        self.standby = False

        # Sources
        self.sources = ["RADIO", "USB", "INTERNET", "BLUETOOTH"]
        self.current_source_idx = 0  # 0 => RADIO
        self.current_source = self.sources[self.current_source_idx]

        # Audio / Player
        self.player = AudioPlayer()

        # For radio
        self.current_radio_freq = 101.0
        self.radio_station_name = ""
        self.radio_station_text = ""

        # For internet radio
        self.stations = read_station_csv("stations.csv")
        self.current_station_idx = 0

        # USB browsing
        self.usb_root = os.getcwd()
        self.current_usb_path = self.usb_root
        self.usb_items = list_audio_files(self.current_usb_path)
        self.usb_selection_index = 0

        # For display
        self.display_contrast = 100
        self.show_clock_on_standby = True

        # Git info
        self.commit_hash, self.last_change_time = get_git_version_info()

        # hardware init
        init_hardware()

        # Possibly run some commands (git, temp check, etc.)
        run_startup_commands(pc_mode=self.pc_mode)

        # PyGame init if PC_MODE
        self.screen = None
        self.clock = None
        if self.pc_mode and PYGAME_AVAILABLE:
            pygame.init()
            self.screen_scale = 4
            self.screen = pygame.display.set_mode(
                (DISPLAY_WIDTH * self.screen_scale, DISPLAY_HEIGHT * self.screen_scale)
            )
            pygame.display.set_caption("RadioWecker Simulation")
            self.clock = pygame.time.Clock()

    ###########################################################################
    # Standby & Source
    ###########################################################################
    def toggle_standby(self):
        self.standby = not self.standby
        if self.standby:
            print("[APP] Entering standby => stopping audio.")
            self.player.stop()
        else:
            print("[APP] Waking up from standby => re-activating current source.")
            self.switch_source(self.sources[self.current_source_idx])

    def cycle_source(self):
        # Stop existing playback if we switch away from it
        self.player.stop()
        self.current_source_idx = (self.current_source_idx + 1) % len(self.sources)
        self.current_source = self.sources[self.current_source_idx]
        self.switch_source(self.current_source)

    def switch_source(self, source_name):
        """
        Switch audio input to the specified source, possibly start playback.
        """
        print(f"[APP] Switching source => {source_name}")
        if source_name == "RADIO":
            self.update_radio_info()
        elif source_name == "USB":
            # No immediate playback. User picks file/folder in the USB view.
            pass
        elif source_name == "INTERNET":
            # Play the currently selected station
            if self.stations:
                name, url = self.stations[self.current_station_idx]
                print(f"[APP] Internet radio => {name} | {url}")
                self.player.play(url)
        elif source_name == "BLUETOOTH":
            # Typically rely on system-level BT sink. We do placeholder here.
            print("[APP] Bluetooth source selected. Pair/connect externally.")
        else:
            pass

    ###########################################################################
    # Radio
    ###########################################################################
    def update_radio_info(self):
        """
        Read the 'radio' (mock RDS) info.
        """
        self.radio_station_name, self.radio_station_text = read_radio_rds()
        print(
            f"[RADIO] Freq: {self.current_radio_freq} | Station: {self.radio_station_name} | Text: {self.radio_station_text}"
        )

    def radio_search_up(self):
        self.current_radio_freq = search_radio("up")
        self.update_radio_info()

    def radio_search_down(self):
        self.current_radio_freq = search_radio("down")
        self.update_radio_info()

    ###########################################################################
    # Alarms
    ###########################################################################
    def check_alarms(self):
        now = time.localtime()
        h, m = now.tm_hour, now.tm_min
        # Alarm 1
        if self.wecker1_active and h == self.wecker1_hour and m == self.wecker1_minute:
            if self.standby:
                print("[ALARM] Wecker1 triggered => waking device.")
                self.toggle_standby()
        # Alarm 2
        if self.wecker2_active and h == self.wecker2_hour and m == self.wecker2_minute:
            if self.standby:
                print("[ALARM] Wecker2 triggered => waking device.")
                self.toggle_standby()

    ###########################################################################
    # USB
    ###########################################################################
    def refresh_usb_items(self):
        self.usb_items = list_audio_files(self.current_usb_path)

    def usb_move_selection(self, direction: str):
        """
        direction = 'up' or 'down', shift the selection index.
        """
        if not self.usb_items:
            return
        max_idx = len(self.usb_items) - 1
        if direction == "up":
            self.usb_selection_index = (self.usb_selection_index - 1) % (max_idx + 1)
        else:
            self.usb_selection_index = (self.usb_selection_index + 1) % (max_idx + 1)

    def usb_select_item(self):
        """
        Execute the 'menu press' behavior on the currently selected USB item.
        """
        if not self.usb_items:
            return
        name, is_dir = self.usb_items[self.usb_selection_index]
        if name == "zurueck":
            parent = os.path.dirname(self.current_usb_path)
            if parent and os.path.exists(parent):
                self.current_usb_path = parent
            self.refresh_usb_items()
            self.usb_selection_index = 0
            return
        if name == "dieser Ordner":
            # Play entire folder
            files_to_play = [
                os.path.join(self.current_usb_path, itm[0])
                for itm in self.usb_items
                if (not itm[1]) and itm[0] not in ["zurueck", "dieser Ordner"]
            ]
            if files_to_play:
                self.player.stop()
                # Start playing first file
                self.player.play(files_to_play[0])
                # Additional logic could loop or queue in an advanced scenario
            return
        full_path = os.path.join(self.current_usb_path, name)
        if is_dir:
            # Enter directory
            self.current_usb_path = full_path
            self.refresh_usb_items()
            self.usb_selection_index = 0
        else:
            # Single file
            self.player.stop()
            self.player.play(full_path)

    ###########################################################################
    # Internet Radio
    ###########################################################################
    def internet_radio_next(self):
        if not self.stations:
            return
        self.current_station_idx = (self.current_station_idx + 1) % len(self.stations)
        name, url = self.stations[self.current_station_idx]
        print(f"[NET RADIO] Next => {name} | {url}")
        self.player.stop()
        self.player.play(url)

    def internet_radio_prev(self):
        if not self.stations:
            return
        self.current_station_idx = (self.current_station_idx - 1) % len(self.stations)
        name, url = self.stations[self.current_station_idx]
        print(f"[NET RADIO] Prev => {name} | {url}")
        self.player.stop()
        self.player.play(url)

    ###########################################################################
    # Menu Toggling (Example)
    ###########################################################################
    def toggle_alarm1(self):
        self.wecker1_active = not self.wecker1_active
        print(f"[ALARM] Wecker1 => {self.wecker1_active}")

    def toggle_alarm2(self):
        self.wecker2_active = not self.wecker2_active
        print(f"[ALARM] Wecker2 => {self.wecker2_active}")

    ###########################################################################
    # Main Loop
    ###########################################################################
    def run(self):
        print("[APP] Starting main loop. Press Ctrl+C to exit.")
        try:
            if self.pc_mode and PYGAME_AVAILABLE:
                while True:
                    self.check_alarms()
                    events = pygame.event.get()
                    for ev in events:
                        if ev.type == QUIT:
                            pygame.quit()
                            return
                        if ev.type == KEYDOWN:
                            self.handle_keypress(ev.key)
                    self.draw_display()
                    pygame.display.flip()
                    self.clock.tick(10)  # ~10 FPS
            else:
                # Pi or no Pygame
                while True:
                    self.check_alarms()
                    button_states = read_touch_sensors()
                    self.handle_button_states(button_states)
                    # On real hardware, you'd update OLED display here
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("[APP] KeyboardInterrupt -> Exiting application.")
        finally:
            self.player.stop()
            if RPI_HARDWARE:
                GPIO.cleanup()

    def handle_button_states(self, bs: dict):
        """Handle the booleans from TTP223 sensors in Pi mode."""
        if bs["power"]:
            self.toggle_standby()
            time.sleep(0.3)
        if not self.standby:
            if bs["source"]:
                self.cycle_source()
                time.sleep(0.3)
            if bs["menu"]:
                # For demonstration, toggle alarm1
                self.toggle_alarm1()
                time.sleep(0.3)
            if bs["forward"]:
                self.handle_forward()
                time.sleep(0.3)
            if bs["backward"]:
                self.handle_backward()
                time.sleep(0.3)

    def handle_keypress(self, key):
        """
        PC_MODE: interpret key events as sensor presses.
        """
        if key == KEY_BINDINGS["power"]:
            self.toggle_standby()
        if self.standby:
            return  # no further actions if in standby
        if key == KEY_BINDINGS["source"]:
            self.cycle_source()
        elif key == KEY_BINDINGS["menu"]:
            # Example: toggle alarm1
            self.toggle_alarm1()
        elif key == KEY_BINDINGS["forward"]:
            self.handle_forward()
        elif key == KEY_BINDINGS["backward"]:
            self.handle_backward()

    def handle_forward(self):
        src = self.sources[self.current_source_idx]
        if src == "RADIO":
            self.radio_search_up()
        elif src == "USB":
            self.usb_move_selection("down")
        elif src == "INTERNET":
            self.internet_radio_next()
        elif src == "BLUETOOTH":
            pass

    def handle_backward(self):
        src = self.sources[self.current_source_idx]
        if src == "RADIO":
            self.radio_search_down()
        elif src == "USB":
            self.usb_move_selection("up")
        elif src == "INTERNET":
            self.internet_radio_prev()
        elif src == "BLUETOOTH":
            pass

    ###########################################################################
    # Display Rendering (PC_MODE with PyGame)
    ###########################################################################
    def draw_display(self):
        """
        Render a 128x64 'virtual' screen, replicating the final device's layout:
          - top row: source name (left), time (right), alarm icons
          - main area: depends on source
          - bottom row or corners: button press states (for debug)
        """
        if not self.screen:
            return
        # Create small surface for 128x64
        framesurf = pygame.Surface((DISPLAY_WIDTH, DISPLAY_HEIGHT))
        framesurf.fill((0, 0, 0))
        font_small = pygame.font.SysFont(None, 10)
        font_medium = pygame.font.SysFont(None, 12)

        # 1) Top row
        source_str = self.sources[self.current_source_idx]
        time_str = time.strftime("%H:%M", time.localtime())
        alarm_str = ""
        if self.wecker1_active:
            alarm_str += "1"
        if self.wecker2_active:
            alarm_str += "2"

        # Draw source name top-left
        surf_source = font_medium.render(source_str, True, (255, 255, 255))
        framesurf.blit(surf_source, (0, 0))

        # Draw alarm icons next to source (small bells or just "W1/W2"?)
        if alarm_str:
            surf_alarm = font_small.render(f"[{alarm_str}]", True, (255, 255, 255))
            framesurf.blit(surf_alarm, (len(source_str) * 6 + 2, 2))

        # Draw time top-right
        surf_time = font_medium.render(time_str, True, (255, 255, 255))
        framesurf.blit(surf_time, (DISPLAY_WIDTH - surf_time.get_width(), 0))

        # 2) Main area: depends on source
        main_y = 14
        if self.standby:
            # Show "Standby" if user wants a standby display
            if self.show_clock_on_standby:
                stand_surf = font_medium.render("Standby Mode", True, (200, 200, 200))
                framesurf.blit(stand_surf, (0, main_y))
                main_y += 12
                # Show time bigger?
                time_standby = time.strftime("%H:%M:%S", time.localtime())
                time_surf = font_medium.render(time_standby, True, (255, 255, 255))
                framesurf.blit(time_surf, (0, main_y))
            # Nothing else
        else:
            source = self.sources[self.current_source_idx]
            if source == "RADIO":
                # Display freq, station name, RDS text
                line1 = f"Freq: {self.current_radio_freq:.2f} MHz"
                line2 = f"Station: {self.radio_station_name}"
                line3 = f"RDS: {self.radio_station_text}"
                self._blit_line(framesurf, font_medium, line1, main_y)
                main_y += 12
                self._blit_line(framesurf, font_medium, line2, main_y)
                main_y += 12
                self._blit_line(framesurf, font_medium, line3, main_y)
                main_y += 12

            elif source == "USB":
                # Show the 3-line file explorer
                # The middle line is the "selected" item
                if not self.usb_items:
                    self._blit_line(framesurf, font_medium, "No items", main_y)
                else:
                    # We show up to 3 lines: index-1, index, index+1
                    for offset in [-1, 0, 1]:
                        idx = self.usb_selection_index + offset
                        if 0 <= idx < len(self.usb_items):
                            name, is_dir = self.usb_items[idx]
                            marker = ">" if offset == 0 else " "
                            label = name + ("/" if is_dir else "")
                            self._blit_line(
                                framesurf, font_medium, f"{marker}{label}", main_y
                            )
                            main_y += 12

            elif source == "INTERNET":
                # Show station name
                if not self.stations:
                    self._blit_line(
                        framesurf, font_medium, "No internet stations loaded.", main_y
                    )
                else:
                    station_name, station_url = self.stations[self.current_station_idx]
                    self._blit_line(
                        framesurf, font_medium, f"Station: {station_name}", main_y
                    )
                    main_y += 12
                    self._blit_line(framesurf, font_small, station_url, main_y)
                    main_y += 10

            elif source == "BLUETOOTH":
                self._blit_line(framesurf, font_medium, "Bluetooth Source", main_y)
                main_y += 12
                self._blit_line(framesurf, font_small, "(Pair externally...)", main_y)
                main_y += 10

        # 3) Show small button press indicators at the bottom
        # No actual states in PC mode, but let's show placeholders
        # (In Pi mode, you'd read real sensor states)
        y_indicator = DISPLAY_HEIGHT - 8
        button_labels = ["Pwr", "Src", "Menu", "Fwd", "Bwd"]
        x_offset = 0
        for bl in button_labels:
            surf_b = font_small.render(bl, True, (100, 255, 100))
            framesurf.blit(surf_b, (x_offset, y_indicator))
            x_offset += surf_b.get_width() + 4

        # Scale up
        scaled_surf = pygame.transform.scale(
            framesurf,
            (DISPLAY_WIDTH * self.screen_scale, DISPLAY_HEIGHT * self.screen_scale),
        )
        self.screen.blit(scaled_surf, (0, 0))

    def _blit_line(self, surf, font, text, y):
        """
        Helper to draw a line of text on the given surface.
        """
        render = font.render(text, True, (255, 255, 255))
        surf.blit(render, (0, y))


###############################################################################
# Main
###############################################################################


def main():
    app = RadioWecker(pc_mode=PC_MODE)
    app.run()


if __name__ == "__main__":
    main()
