#!/usr/bin/env python3
"""
RadioWecker Implementation with On-Release Button Handling, Long Press for Menu,
and Alarm Cycle Fix
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
    "menu": pygame.K_3,  # Long-press for menu, short-press could do "Set"
    "forward": pygame.K_4,
    "backward": pygame.K_5,
}

LONG_PRESS_THRESHOLD = 1.0  # Seconds to qualify as a long press


###############################################################################
# Utility / Hardware Stubs
###############################################################################
def run_startup_commands(pc_mode: bool):
    temp = get_cpu_temperature()
    commit_hash, last_change = get_git_version_info()
    if not pc_mode:
        pass  # On a real environment, possibly a git pull or other init
    print(
        f"[STARTUP] CPU Temp: {temp}C | Git Commit: {commit_hash[:7]} | Last Change: {last_change}"
    )


def init_hardware():
    if PC_MODE:
        print("[INIT] PC_MODE active. Skipping real hardware init.")
    else:
        if RPI_HARDWARE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            print("[INIT] Raspberry Pi hardware init done.")
        else:
            print("[INIT] Not real Pi environment, skipping hardware init.")


def read_touch_sensors():
    """
    On real Pi, read GPIO pins for the 5 TTP223 sensors.
    Returns a dict: { 'power': bool, 'source': bool, 'menu': bool, 'forward': bool, 'backward': bool }
    In PC_MODE, we do key-based reading in the main loop, so we just return all False here.
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
        # Replace with actual GPIO input in real usage
        return {
            "power": False,
            "source": False,
            "menu": False,
            "forward": False,
            "backward": False,
        }


def get_cpu_temperature():
    if PC_MODE:
        return 42.0
    else:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                val = f.read().strip()
                return round(float(val) / 1000.0, 1)
        return "N/A"


def get_git_version_info():
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
    Simulate reading station name & text via RDS.
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
    return round(random.uniform(76.0, 108.0), 2)


###############################################################################
# Audio Player (uses VLC)
###############################################################################
class AudioPlayer:
    def __init__(self):
        self.instance = None
        self.player = None
        if not VLC_AVAILABLE:
            print("[AUDIO] python-vlc not available. Audio playback won't work.")
        else:
            self.instance = vlc.Instance()
            self.player = self.instance.media_player_new()

    def play(self, source: str):
        if not self.player:
            print("[AUDIO] No VLC player instance.")
            return
        media = self.instance.media_new(source)
        self.player.set_media(media)
        self.player.play()
        print(f"[AUDIO] Playing => {source}")

    def stop(self):
        if self.player:
            self.player.stop()

    def is_playing(self):
        if self.player:
            return self.player.is_playing() == 1
        return False


###############################################################################
# USB File Navigation
###############################################################################
def list_audio_files(path: str):
    if not os.path.isdir(path):
        return []
    items = []
    items.append(("zurueck", False))
    items.append(("dieser Ordner", False))

    try:
        dir_entries = os.listdir(path)
    except OSError:
        return items

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
        self.alarm_mode = 0  # 0: none, 1: alarm1, 2: alarm2, 3: both
        self.wecker1_hour = 6
        self.wecker1_minute = 0
        self.wecker2_hour = 7
        self.wecker2_minute = 30

        # Standby
        self.standby = False

        # Sources
        self.sources = ["RADIO", "USB", "INTERNET", "BLUETOOTH"]
        self.current_source_idx = 0
        self.current_source = self.sources[self.current_source_idx]

        # Audio
        self.player = AudioPlayer()

        # Radio
        self.current_radio_freq = 101.0
        self.radio_station_name = ""
        self.radio_station_text = ""

        # Internet radio
        self.stations = read_station_csv("stations.csv")
        self.current_station_idx = 0

        # USB
        self.usb_root = os.getcwd()
        self.current_usb_path = self.usb_root
        self.usb_items = list_audio_files(self.current_usb_path)
        self.usb_selection_index = 0

        # Display
        self.display_contrast = 100
        self.show_clock_on_standby = True

        # Git info
        self.commit_hash, self.last_change_time = get_git_version_info()

        # Menu
        self.in_settings_menu = False

        # Button press tracking (on-release approach)
        self.button_states = {
            "power": {"down": False, "time": 0, "handled": False},
            "source": {"down": False, "time": 0, "handled": False},
            "menu": {"down": False, "time": 0, "handled": False},
            "forward": {"down": False, "time": 0, "handled": False},
            "backward": {"down": False, "time": 0, "handled": False},
        }

        init_hardware()
        run_startup_commands(pc_mode=self.pc_mode)

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
                            self.update_button_state_pygame(ev.key, True)
                        # For on-release detection, check if user released a key
                        if ev.type == pygame.KEYUP:
                            self.update_button_state_pygame(ev.key, False)

                    self.handle_button_state_logic()
                    self.draw_display()
                    pygame.display.flip()
                    self.clock.tick(20)

            else:
                # Pi or no Pygame
                while True:
                    self.check_alarms()
                    sensor_state = read_touch_sensors()
                    self.update_button_state_pi(sensor_state)
                    self.handle_button_state_logic()
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print("[APP] KeyboardInterrupt -> Exiting application.")
        finally:
            self.player.stop()
            if RPI_HARDWARE:
                GPIO.cleanup()

    ###########################################################################
    # On-Release Button Handling
    ###########################################################################
    def update_button_state_pygame(self, key, pressed):
        for name, binding in KEY_BINDINGS.items():
            if key == binding:
                btn_state = self.button_states[name]
                if pressed:
                    if not btn_state["down"]:
                        btn_state["down"] = True
                        btn_state["time"] = time.time()  # mark press time
                        btn_state["handled"] = False
                else:
                    # Key was released
                    btn_state["down"] = False

    def update_button_state_pi(self, sensor_state):
        """
        In Pi mode, sensor_state is a dict of booleans.
        We'll do similar press/release tracking as pygame, checking each button.
        """
        for name in self.button_states.keys():
            currently_pressed = sensor_state[name]
            btn_state = self.button_states[name]
            if currently_pressed and not btn_state["down"]:
                # Just pressed
                btn_state["down"] = True
                btn_state["time"] = time.time()
                btn_state["handled"] = False
            elif not currently_pressed and btn_state["down"]:
                # Just released
                btn_state["down"] = False

    def handle_button_state_logic(self):
        """
        Check each button's release, see if it's a short press or long press.
        Also check if forward+backward were pressed simultaneously at any point.
        """
        # First, gather which buttons are currently pressed
        pressed_buttons = [b for b, st in self.button_states.items() if st["down"]]

        # If forward & backward are pressed right now, do nothing; we'll wait for release
        # so we don't accidentally do next/previous. We'll only act on release detection.

        # We'll track which buttons have been released in this loop:
        released_buttons = []
        for bname, st in self.button_states.items():
            if not st["down"] and not st["handled"]:
                # This means it was just released now
                released_buttons.append(bname)

        # If none were released, nothing to do
        if not released_buttons:
            return

        # Check if forward and backward are both in released set => cycle alarm once
        # But only if they were pressed at the same time (overlapping press).
        # We'll confirm they actually overlapped in time for at least some fraction.
        # A simpler approach: if both are in released_buttons, we do the alarm cycle.
        # That prevents double-advancement. We'll then mark them as handled.
        if "forward" in released_buttons and "backward" in released_buttons:
            # Check overlap or at least that both were pressed before
            fwd_down_time = self.button_states["forward"]["time"]
            bwd_down_time = self.button_states["backward"]["time"]
            # Rough check if they were pressed within ~0.2s of each other
            # or if they were both "down" at once
            # For a simpler approach, we just do the cycle once:
            self.cycle_alarm_mode()
            self.button_states["forward"]["handled"] = True
            self.button_states["backward"]["handled"] = True
            return

        # Now handle each released button individually if not handled
        for btn_name in released_buttons:
            btn_state = self.button_states[btn_name]
            if btn_state["handled"]:
                continue  # already used in a combined press

            press_duration = time.time() - btn_state["time"]

            # Mark it handled so we don't process it more than once
            btn_state["handled"] = True

            if btn_name == "power":
                self.handle_power_release()
            elif btn_name == "source":
                self.handle_source_release()
            elif btn_name == "menu":
                self.handle_menu_release(press_duration)
            elif btn_name == "forward":
                self.handle_forward_release()
            elif btn_name == "backward":
                self.handle_backward_release()

    ###########################################################################
    # Handle Individual Button Releases
    ###########################################################################
    def handle_power_release(self):
        self.toggle_standby()

    def handle_source_release(self):
        if self.standby:
            return
        self.cycle_source()

    def handle_menu_release(self, press_duration):
        """
        If press_duration exceeds LONG_PRESS_THRESHOLD => open menu
        Otherwise, short-press could do some 'set' actions
        """
        if self.standby:
            return
        if press_duration >= LONG_PRESS_THRESHOLD:
            # Long press => open/close menu
            self.toggle_menu()
        else:
            # Short press => do something else
            # For example "set" (like setting alarm time?), or just placeholder
            print("[MENU] Short-press set action (placeholder).")

    def handle_forward_release(self):
        if self.standby:
            return
        # If user pressed forward alone, do normal next action
        # If forward & backward were pressed simultaneously, that was handled above
        src = self.sources[self.current_source_idx]
        if src == "RADIO":
            self.radio_search_up()
        elif src == "USB":
            self.usb_move_selection("down")
        elif src == "INTERNET":
            self.internet_radio_next()
        elif src == "BLUETOOTH":
            pass

    def handle_backward_release(self):
        if self.standby:
            return
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
    # Menu Handling
    ###########################################################################
    def enter_menu(self):
        if not self.in_settings_menu:
            self.in_settings_menu = True
            print("[MENU] Entering settings menu... (placeholder)")

    def exit_menu(self):
        if self.in_settings_menu:
            self.in_settings_menu = False
            print("[MENU] Exiting settings menu.")

    def toggle_menu(self):
        if self.in_settings_menu:
            self.exit_menu()
        else:
            self.enter_menu()

    ###########################################################################
    # Alarm Handling
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

    def cycle_alarm_mode(self):
        """
        0 => none,
        1 => alarm1 only,
        2 => alarm2 only,
        3 => both
        """
        self.alarm_mode = (self.alarm_mode + 1) % 4
        if self.alarm_mode == 0:
            self.wecker1_active = False
            self.wecker2_active = False
            print("[ALARM] Both alarms off (mode=0).")
        elif self.alarm_mode == 1:
            self.wecker1_active = True
            self.wecker2_active = False
            print("[ALARM] Alarm1 on, Alarm2 off (mode=1).")
        elif self.alarm_mode == 2:
            self.wecker1_active = False
            self.wecker2_active = True
            print("[ALARM] Alarm1 off, Alarm2 on (mode=2).")
        elif self.alarm_mode == 3:
            self.wecker1_active = True
            self.wecker2_active = True
            print("[ALARM] Alarm1 on, Alarm2 on (mode=3).")

    ###########################################################################
    # Standby & Source
    ###########################################################################
    def toggle_standby(self):
        self.standby = not self.standby
        if self.standby:
            print("[APP] Entering standby => stopping audio.")
            self.player.stop()
        else:
            print("[APP] Waking up => re-activating current source.")
            self.switch_source(self.sources[self.current_source_idx])

    def cycle_source(self):
        self.player.stop()
        self.current_source_idx = (self.current_source_idx + 1) % len(self.sources)
        self.current_source = self.sources[self.current_source_idx]
        self.switch_source(self.current_source)

    def switch_source(self, source_name):
        print(f"[APP] Switching source => {source_name}")
        if source_name == "RADIO":
            self.update_radio_info()
        elif source_name == "USB":
            # No immediate playback, user picks file/folder
            pass
        elif source_name == "INTERNET":
            if self.stations:
                name, url = self.stations[self.current_station_idx]
                print(f"[APP] Internet radio => {name} | {url}")
                self.player.play(url)
        elif source_name == "BLUETOOTH":
            print("[APP] Bluetooth source selected. Pair/connect externally.")

    ###########################################################################
    # Radio
    ###########################################################################
    def update_radio_info(self):
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
    # USB
    ###########################################################################
    def refresh_usb_items(self):
        self.usb_items = list_audio_files(self.current_usb_path)

    def usb_move_selection(self, direction: str):
        if not self.usb_items:
            return
        max_idx = len(self.usb_items) - 1
        if direction == "up":
            self.usb_selection_index = (self.usb_selection_index - 1) % (max_idx + 1)
        else:
            self.usb_selection_index = (self.usb_selection_index + 1) % (max_idx + 1)

    def usb_select_item(self):
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
            files_to_play = [
                os.path.join(self.current_usb_path, itm[0])
                for itm in self.usb_items
                if (not itm[1]) and itm[0] not in ["zurueck", "dieser Ordner"]
            ]
            if files_to_play:
                self.player.stop()
                self.player.play(files_to_play[0])
            return
        full_path = os.path.join(self.current_usb_path, name)
        if is_dir:
            self.current_usb_path = full_path
            self.refresh_usb_items()
            self.usb_selection_index = 0
        else:
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
    # Display Rendering (PC_MODE + PyGame Demo)
    ###########################################################################
    def draw_display(self):
        """
        Renders text info in PC_MODE using PyGame. For a real device with an I2C display,
        you'd integrate an OLED or LCD library in place of or alongside this code.
        If the display is not showing content, ensure pygame is installed and you
        have a graphics environment. On a headless system, you might not see the window.
        """
        if not self.screen:
            return
        framesurf = pygame.Surface((DISPLAY_WIDTH, DISPLAY_HEIGHT))
        framesurf.fill((0, 0, 0))
        font_small = pygame.font.SysFont(None, 10)
        font_medium = pygame.font.SysFont(None, 12)

        # Top row: source, time, alarm icons
        source_str = self.sources[self.current_source_idx]
        time_str = time.strftime("%H:%M", time.localtime())
        alarm_str = ""
        if self.wecker1_active:
            alarm_str += "1"
        if self.wecker2_active:
            alarm_str += "2"

        surf_source = font_medium.render(source_str, True, (255, 255, 255))
        framesurf.blit(surf_source, (0, 0))

        if alarm_str:
            surf_alarm = font_small.render(f"[{alarm_str}]", True, (255, 255, 255))
            framesurf.blit(surf_alarm, (len(source_str) * 6 + 2, 2))

        surf_time = font_medium.render(time_str, True, (255, 255, 255))
        framesurf.blit(surf_time, (DISPLAY_WIDTH - surf_time.get_width(), 0))

        main_y = 14
        # Standby display
        if self.standby:
            if self.show_clock_on_standby:
                stand_surf = font_medium.render("Standby Mode", True, (200, 200, 200))
                framesurf.blit(stand_surf, (0, main_y))
                main_y += 12
                time_standby = time.strftime("%H:%M:%S", time.localtime())
                time_surf = font_medium.render(time_standby, True, (255, 255, 255))
                framesurf.blit(time_surf, (0, main_y))
        else:
            # If in menu, show a placeholder. Otherwise source-specific view.
            if self.in_settings_menu:
                menu_surf = font_medium.render(
                    "Settings Menu...", True, (180, 180, 255)
                )
                framesurf.blit(menu_surf, (0, main_y))
            else:
                source = self.sources[self.current_source_idx]
                if source == "RADIO":
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
                    if not self.usb_items:
                        self._blit_line(framesurf, font_medium, "No items", main_y)
                    else:
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
                    if not self.stations:
                        self._blit_line(
                            framesurf,
                            font_medium,
                            "No internet stations loaded.",
                            main_y,
                        )
                    else:
                        station_name, station_url = self.stations[
                            self.current_station_idx
                        ]
                        self._blit_line(
                            framesurf, font_medium, f"Station: {station_name}", main_y
                        )
                        main_y += 12
                        self._blit_line(framesurf, font_small, station_url, main_y)
                elif source == "BLUETOOTH":
                    self._blit_line(framesurf, font_medium, "Bluetooth Source", main_y)
                    main_y += 12
                    self._blit_line(
                        framesurf, font_small, "(Pair externally...)", main_y
                    )

        # Bottom row: debug labels for buttons
        y_indicator = DISPLAY_HEIGHT - 8
        button_labels = ["Pwr", "Src", "Menu", "Fwd", "Bwd"]
        x_offset = 0
        for bl in button_labels:
            surf_b = font_small.render(bl, True, (100, 255, 100))
            framesurf.blit(surf_b, (x_offset, y_indicator))
            x_offset += surf_b.get_width() + 4

        scaled_surf = pygame.transform.scale(
            framesurf,
            (DISPLAY_WIDTH * self.screen_scale, DISPLAY_HEIGHT * self.screen_scale),
        )
        self.screen.blit(scaled_surf, (0, 0))

    def _blit_line(self, surf, font, text, y):
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
