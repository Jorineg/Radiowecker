# ui.py

import time
from typing import List, Tuple, Optional
from enum import Enum


class UIMode(Enum):
    NORMAL = "normal"
    MENU = "menu"
    FILE_BROWSER = "file_browser"


class UIState:
    def __init__(self):
        # Display regions
        self.HEADER_HEIGHT = 10
        self.FOOTER_HEIGHT = 8
        self.CONTENT_START = self.HEADER_HEIGHT + 2

        # General state
        self.mode = UIMode.NORMAL
        self.standby = False

        # Sources
        self.sources = ["RADIO", "USB", "INTERNET", "BLUETOOTH", "ALARMS"]
        self.current_source = 0

        # File browser state
        self.selected_file_idx = 1

        # Menu state
        self.menu_title = ""
        self.menu_items = []
        self.menu_selected = 0

        # Status indicators
        self.alarm_mode = 0  # 0=off, 1=alarm1, 2=alarm2, 3=both
        self.volume = 50
        self.is_playing = False

        # Button states
        self.button_states = {
            "power": False,
            "source": False,
            "menu": False,
            "backward": False,
            "forward": False
        }

    def get_current_source(self) -> str:
        """Get name of current source"""
        return self.sources[self.current_source]

    def next_source(self):
        """Switch to next source"""
        self.current_source = (self.current_source + 1) % len(self.sources)
        print("Switched to source:", self.get_current_source())
        if self.get_current_source() == "USB":
            self.mode = UIMode.FILE_BROWSER
        else:
            self.mode = UIMode.NORMAL

    def toggle_standby(self):
        """Toggle standby mode"""
        self.standby = not self.standby


class UI:
    def __init__(self, display, settings, audio, hardware_out):
        self.display = display
        self.settings = settings
        self.audio = audio
        self.state = UIState()
        self.hardware_in = None  # Will be set from outside
        self.hardware_out = hardware_out

    def set_hardware_input(self, hardware_in):
        """Set hardware input reference to get button states"""
        self.hardware_in = hardware_in

    def render(self):
        """Main render function"""
        self.display.clear()

        if self.state.standby:
            if self.settings.get_value("Uhr im Standby"):
                # Show only large clock on black background when in standby
                self.render_standby_clock()
            else:
                # Black screen when clock disabled in standby
                for y in range(self.display.height):
                    for x in range(self.display.width):
                        self.display.buffer.set_pixel(x, y, False)
        else:
            # Normal UI when not in standby
            self.render_header()

            if self.state.mode == UIMode.MENU:
                self.render_menu()
            elif self.state.mode == UIMode.FILE_BROWSER:
                self.render_file_browser()
            else:
                self.render_normal()

        # Always render button indicators
        self.render_button_indicators()
        
        self.display.show()

    def render_header(self):
        """Render status bar"""
        # Time
        time_str = time.strftime("%H:%M")
        self.display.buffer.draw_text(self.display.width - 30, 0, time_str)

        # Source
        source = self.state.get_current_source()
        self.display.buffer.draw_text(0, 0, source)

        # Alarm indicators
        if self.state.alarm_mode & 1:
            self.display.buffer.draw_text(60, 0, "A1")
        if self.state.alarm_mode & 2:
            self.display.buffer.draw_text(75, 0, "A2")

        # Draw separator line
        self.display.buffer.draw_rect(
            0, self.state.HEADER_HEIGHT, self.display.width, 1, True
        )

    def render_footer(self):
        """Render footer with status"""
        y = self.display.height - self.state.FOOTER_HEIGHT

        # Play status
        if self.state.is_playing:
            self.display.buffer.draw_text(self.display.width - 12, y, "▶")

    def render_button_indicators(self):
        """Render button press indicators at bottom edge"""
        if not self.hardware_in:
            return

        y = self.display.height - 1
        button_width = 1
        spacing = (self.display.width - (5 * button_width)) // 6  # 5 buttons, 6 spaces
        
        # Button order from left to right: power, source, menu, backward, forward
        buttons = ["power", "source", "menu", "backward", "forward"]
        
        # Draw indicators for currently pressed buttons
        for i, button in enumerate(buttons):
            x = spacing + i * (button_width + spacing)
            if self.hardware_in.buttons[button].pressed:
                self.display.buffer.draw_rect(x, y, button_width, button_width, True)

    def render_normal(self):
        """Render normal mode content"""
        y = self.state.CONTENT_START
        source = self.state.get_current_source()

        if source == "RADIO":
            # Show frequency
            freq = "101.5 MHz"  # Get from radio module
            self.display.buffer.draw_text(0, y, freq)

        elif source == "INTERNET":
            # Show station
            if self.audio.current_station:
                self.display.buffer.draw_text(0, y, self.audio.current_station.name)

        elif source == "USB":
            # Show current file
            if self.audio.current_file:
                self.display.buffer.draw_text(0, y, self.audio.current_file.name)

        elif source == "BLUETOOTH":
            # Show BT status and track
            device_name, track_info = self.audio.get_bluetooth_info()
            self.display.buffer.draw_text(0, y, f"Device: {device_name}")
            if track_info:
                inofs = track_info.split('\n')
                self.display.buffer.draw_text(0, y + 10, inofs[0])
                if len(inofs) > 1:
                    self.display.buffer.draw_text(0, y + 20, inofs[1])

        elif source == "ALARMS":
            # Show alarm times
            alarm_1 = f"{self.settings.get_value('Wecker1 Stunden'):02d}:{self.settings.get_value('Wecker1 Minuten'):02d}"
            alarm_2 = f"{self.settings.get_value('Wecker2 Stunden'):02d}:{self.settings.get_value('Wecker2 Minuten'):02d}"
            self.display.buffer.draw_text(0, y, f"Alarm 1: {alarm_1}")
            y += 10
            self.display.buffer.draw_text(0, y, f"Alarm 2: {alarm_2}")
            y += 10

    def render_menu(self):
        """Render settings menu"""
        y = self.state.CONTENT_START

        # Menu title
        self.display.buffer.draw_text(0, y, self.state.menu_title)
        y += 12

        # Current item
        item = self.settings.get_current_item()
        self.display.buffer.draw_text(0, y, item.name)
        y += 10

        # Value
        value_lines = item.format_value()
        if "Wecker" in item.name:
            # For alarm settings, show complete time HH:MM
            alarm_num = "1" if "Wecker1" in item.name else "2"
            hours = None
            minutes = None
            
            # Find the corresponding hours/minutes values
            for setting in self.settings.items:
                if f"Wecker{alarm_num} Stunden" in setting.name:
                    hours = setting.value
                elif f"Wecker{alarm_num} Minuten" in setting.name:
                    minutes = setting.value
                if hours is not None and minutes is not None:
                    break
            
            if hours is not None and minutes is not None:
                value_lines = [f"{hours:02d}:{minutes:02d}"]

        # Draw each line of the value
        for line in value_lines:
            self.display.buffer.draw_text(0, y, line)
            y += 10

    def render_file_browser(self):
        """Render file browser"""
        y = self.state.CONTENT_START
        files = self.audio.get_current_files()

        get_file = lambda i: files[i%len(files)]
       
        # Draw visible files
        # always three rows, selected file is in the middle
        for i in range(self.state.selected_file_idx - 1, self.state.selected_file_idx + 4):
            file = get_file(i)
            highlight = i == self.state.selected_file_idx

            # Add folder indicator
            name = f"[{file.name}]" if file.is_dir and not file.is_special else file.name
            self.display.buffer.draw_text(0, y, (">" if highlight else " ") + name)
            y += 10

    def render_standby_clock(self):
        """Render large centered clock for standby mode"""
        time_str = time.strftime("%H:%M")
        # Center the time using 8x16 font
        x = (self.display.width - len(time_str) * 9) // 2  # 8 pixels per char + 1 pixel spacing
        y = (self.display.height - 16) // 2  # 16 pixels high
        self.display.buffer.draw_text(x, y, time_str, size="8x16")

    def handle_button(self, button: str, long_press: bool):
        """Handle button press"""
        if button == "power":
            self.state.toggle_standby()
            self.hardware_out.set_amp_enable(not self.state.standby)
            return

        if self.state.standby:
            return

        if self.state.mode == UIMode.MENU:
            self.handle_menu_button(button, long_press)
        elif self.state.mode == UIMode.FILE_BROWSER:
            self.handle_browser_button(button, long_press)
        else:
            self.handle_normal_button(button, long_press)

    def handle_menu_button(self, button: str, long_press: bool):
        """Handle button in menu mode"""
        if button == "menu" and long_press:
            # Long press always exits menu
            self.state.mode = UIMode.NORMAL
            self.settings.save_settings()
            self.settings.reset_to_first()  # Reset position after saving
        elif button == "forward":
            self.settings.get_current_item().increase()
        elif button == "backward":
            self.settings.get_current_item().decrease()
        elif button == "menu":
            # Short press - move to next item or exit if at last item
            if not self.settings.next_item():  # If we can't move to next item
                self.state.mode = UIMode.NORMAL  # Exit menu
                self.settings.save_settings()
                self.settings.reset_to_first()  # Reset position after saving


    def next_source(self):
        """Switch to next source"""
        self.audio.stop()
        self.state.next_source()
        if self.state.get_current_source() == "INTERNET":
            self.audio.play_station(self.audio.current_station)

        if self.state.get_current_source() == "BLUETOOTH":
            self.audio.unmute_bluetooth()
        else:
            self.audio.mute_bluetooth()

    def handle_browser_button(self, button: str, long_press: bool):
        """Handle button in file browser mode"""
        if button == "menu" and long_press:
            self.state.mode = UIMode.NORMAL
        elif button == "forward":
            self.select_next_file()
        elif button == "backward":
            self.select_prev_file()
        elif button == "menu" and not long_press:
            self.select_file()
        elif button == "menu" and long_press:
            self.state.mode = UIMode.MENU
        elif button == "source":
            self.next_source()

    def handle_normal_button(self, button: str, long_press: bool):
        """Handle button in normal mode"""
        if button == "menu" and long_press:
            self.state.mode = UIMode.MENU
        elif button == "source":
            self.next_source()
        elif button == "forward":
            self.handle_forward()
        elif button == "backward":
            self.handle_backward()

    def handle_forward(self):
        """Handle forward in normal mode"""
        source = self.state.get_current_source()
        if source == "RADIO":
            # Seek up
            pass
        elif source == "INTERNET":
            # Next station
            stations = self.audio.get_stations()
            if stations:
                idx = stations.index(self.audio.current_station)
                next_station = stations[(idx + 1) % len(stations)]
                self.audio.play_station(next_station)
        elif source == "ALARMS":
            # toggle second bit
            self.state.alarm_mode = self.state.alarm_mode ^ 2

    def handle_backward(self):
        """Handle backward in normal mode"""
        source = self.state.get_current_source()
        if source == "RADIO":
            # Seek down
            pass
        elif source == "INTERNET":
            # Previous station
            stations = self.audio.get_stations()
            if stations:
                idx = stations.index(self.audio.current_station)
                prev_station = stations[(idx - 1) % len(stations)]
                self.audio.play_station(prev_station)
        elif source == "ALARMS":
            # toggle first bit
            self.state.alarm_mode = self.state.alarm_mode ^ 1
    def select_next_file(self):
        """Select next file in browser"""
        files = self.audio.get_current_files()
        if not files:
            return
        self.state.selected_file_idx = (self.state.selected_file_idx + 1) % len(files)

    def select_prev_file(self):
        """Select previous file in browser"""
        files = self.audio.get_current_files()
        if not files:
            return
        self.state.selected_file_idx = (self.state.selected_file_idx - 1) % len(files)

    def select_file(self):
        """Select current file in browser"""
        files = self.audio.get_current_files()
        if not files:
            return

        file = files[self.state.selected_file_idx]
        if self.audio.navigate_to(file):
            self.state.selected_file_idx = 1

        # Exit browser if we selected a file (not dir)
        # if not file.is_dir:
        #     self.state.mode = UIMode.NORMAL
