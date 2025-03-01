# ui.py

import time
from typing import List, Tuple, Optional
from enum import Enum
from volume_control import VolumeControl


class UIMode(Enum):
    NORMAL = "normal"
    MENU = "menu"
    FILE_BROWSER = "file_browser"
    SD_CARD_BROWSER = "sd_card_browser"
    VOLUME = "volume"


class UIState:
    def __init__(self):
        # Display regions
        self.HEADER_HEIGHT = 10
        self.FOOTER_HEIGHT = 8
        self.CONTENT_START = self.HEADER_HEIGHT + 2

        # General state
        self.mode = UIMode.NORMAL
        self.standby = False
        self.volume_overlay_timeout = 0

        # Sources
        self.sources = ["RADIO", "USB", "SD_CARD", "INTERNET", "BLUETOOTH"]
        self.current_source = 0

        # Volume control
        self.volume_control = VolumeControl()
        self.volume = self.volume_control.get_volume()

        # Status indicators
        self.alarm_mode = 0
        self.is_playing = False
        
        # File browser index
        self.selected_file_idx = 1

        # Button states
        self.button_states = {
            "power": False,
            "source": False,
            "menu": False,
            "alarm1": False,
            "alarm2": False
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
        elif self.get_current_source() == "SD_CARD":
            self.mode = UIMode.SD_CARD_BROWSER
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
        self.hardware_in = None
        self.hardware_out = hardware_out
        self.last_volume_change = 0
        self.VOLUME_OVERLAY_DURATION = 2.0

    def set_hardware_input(self, hardware_in):
        """Set hardware input reference to get button states"""
        self.hardware_in = hardware_in

    def render(self):
        """Main render function"""
        self.display.clear()

        if self.state.standby:
            if self.settings.get_value("Uhr im Standby"):
                self.render_standby_clock()
            else:
                for y in range(self.display.height):
                    for x in range(self.display.width):
                        self.display.buffer.set_pixel(x, y, False)
        else:
            current_time = time.time()
            if current_time < self.state.volume_overlay_timeout:
                self.render_volume_overlay()
            else:
                self.render_header()

                if self.state.mode == UIMode.MENU:
                    self.render_menu()
                elif self.state.mode == UIMode.FILE_BROWSER:
                    self.render_file_browser()
                elif self.state.mode == UIMode.SD_CARD_BROWSER:
                    self.render_sd_card_browser()
                else:
                    self.render_normal()

        self.render_button_indicators()
        self.display.show()

    def render_header(self):
        """Render status bar"""
        time_str = time.strftime("%H:%M")
        self.display.buffer.draw_text(self.display.width - 30, 0, time_str)

        source = self.state.get_current_source()
        self.display.buffer.draw_text(0, 0, source)

        if self.state.alarm_mode & 1:
            self.display.buffer.draw_text(60, 0, "A1")
        if self.state.alarm_mode & 2:
            self.display.buffer.draw_text(75, 0, "A2")

        self.display.buffer.draw_rect(
            0, self.state.HEADER_HEIGHT, self.display.width, 1, True
        )

    def render_footer(self):
        """Render footer with status"""
        y = self.display.height - self.state.FOOTER_HEIGHT

        if self.state.is_playing:
            self.display.buffer.draw_text(self.display.width - 12, y, "▶")

    def render_button_indicators(self):
        """Render button press indicators at bottom edge"""
        if not self.hardware_in:
            return

        y = self.display.height - 1
        button_width = 1
        spacing = (self.display.width - (5 * button_width)) // 6

        buttons = ["power", "source", "menu", "alarm1", "alarm2"]

        for i, button in enumerate(buttons):
            x = spacing + i * (button_width + spacing)
            if self.hardware_in.buttons[button].pressed:
                self.display.buffer.set_pixel(x, y, True)

    def render_normal(self):
        """Render normal mode content"""
        y = self.state.CONTENT_START
        source = self.state.get_current_source()

        if source == "RADIO":
            freq = "101.5 MHz"
            self.display.buffer.draw_text(0, y, freq)

        elif source == "INTERNET":
            if self.audio.current_station:
                self.display.buffer.draw_text(0, y, self.audio.current_station.name)

        elif source == "USB":
            if self.audio.current_file:
                self.display.buffer.draw_text(0, y, self.audio.current_file.name)
                
        elif source == "SD_CARD":
            if self.audio.current_sd_file:
                self.display.buffer.draw_text(0, y, self.audio.current_sd_file.name)

        elif source == "BLUETOOTH":
            device_name, track_info = self.audio.get_bluetooth_info()
            self.display.buffer.draw_text(0, y, f"Device: {device_name}")
            if track_info:
                inofs = track_info.split('\n')
                self.display.buffer.draw_text(0, y + 10, inofs[0])
                if len(inofs) > 1:
                    self.display.buffer.draw_text(0, y + 20, inofs[1])

    def render_menu(self):
        """Render settings menu"""
        y = self.state.CONTENT_START

        self.display.buffer.draw_text(0, y, self.state.menu_title)
        y += 12

        item = self.settings.get_current_item()
        self.display.buffer.draw_text(0, y, item.name)
        y += 10

        value_lines = item.format_value()
        if "Wecker" in item.name:
            alarm_num = "1" if "Wecker1" in item.name else "2"
            hours = None
            minutes = None

            for setting in self.settings.items:
                if f"Wecker{alarm_num} Stunden" in setting.name:
                    hours = setting.value
                elif f"Wecker{alarm_num} Minuten" in setting.name:
                    minutes = setting.value
                if hours is not None and minutes is not None:
                    break

            if hours is not None and minutes is not None:
                value_lines = [f"{hours:02d}:{minutes:02d}"]

        for line in value_lines:
            self.display.buffer.draw_text(0, y, line)
            y += 10

    def render_file_browser(self):
        """Render file browser"""
        files = self.audio.get_current_files()
        if not files or len(files) == 0:
            self.display.clear()
            self.display.write_line(0, "No files found")
            return

        # Get current file based on index
        current_idx = self.state.selected_file_idx
        if current_idx >= len(files):
            current_idx = 0
            self.state.selected_file_idx = 0

        # Calculate which files to display
        start_idx = max(0, current_idx - 1)
        end_idx = min(len(files), start_idx + 4)
        
        # Adjust start_idx if we have fewer than 4 files to display
        if end_idx - start_idx < 4:
            start_idx = max(0, end_idx - 4)

        self.display.clear()
        
        # Display files
        line = 0
        for i in range(start_idx, end_idx):
            file = files[i]
            prefix = ">" if i == current_idx else " "
            
            # Add play indicator if this is the currently playing file
            if (self.audio.current_file and self.audio.current_file == file and 
                self.audio.source == AudioSource.USB):
                prefix = "▶"
                
            name = file.name
            if len(name) > 19:
                name = name[:16] + "..."
                
            self.display.write_line(line, f"{prefix}{name}")
            line += 1

    def render_sd_card_browser(self):
        """Render SD card browser"""
        files = self.audio.get_sd_card_files()
        if not files or len(files) == 0:
            self.display.clear()
            self.display.write_line(0, "No SD card files")
            return

        # Get current file based on index
        current_idx = self.state.selected_file_idx
        if current_idx >= len(files):
            current_idx = 0
            self.state.selected_file_idx = 0

        # Calculate which files to display
        start_idx = max(0, current_idx - 1)
        end_idx = min(len(files), start_idx + 4)
        
        # Adjust start_idx if we have fewer than 4 files to display
        if end_idx - start_idx < 4:
            start_idx = max(0, end_idx - 4)

        self.display.clear()
        
        # Display files
        line = 0
        for i in range(start_idx, end_idx):
            file = files[i]
            prefix = ">" if i == current_idx else " "
            
            # Add play indicator if this is the currently playing file
            if (self.audio.current_sd_file and self.audio.current_sd_file == file and 
                self.audio.source == AudioSource.SD_CARD):
                prefix = "▶"
                
            name = file.name
            if len(name) > 19:
                name = name[:16] + "..."
                
            self.display.write_line(line, f"{prefix}{name}")
            line += 1

    def render_standby_clock(self):
        """Render large centered clock for standby mode"""
        time_str = time.strftime("%H:%M")
        x = (self.display.width - len(time_str) * 9) // 2
        y = (self.display.height - 16) // 2
        self.display.buffer.draw_text(x, y, time_str, size="8x16")

    def render_volume_overlay(self):
        """Render volume overlay with number and progress bar"""
        self.display.clear()

        volume_text = f"{self.state.volume}%"
        text_width = len(volume_text) * 8
        x = (self.display.width - text_width) // 2
        y = (self.display.height - 16) // 2

        self.display.buffer.draw_text(x, y, volume_text, size="8x16")

        bar_width = int((self.display.width * 0.8))
        bar_height = 4
        bar_x = (self.display.width - bar_width) // 2
        bar_y = y + 20

        for i in range(bar_width):
            self.display.buffer.set_pixel(bar_x + i, bar_y, True)
            self.display.buffer.set_pixel(bar_x + i, bar_y + bar_height, True)
        self.display.buffer.set_pixel(bar_x, bar_y + 1, True)
        self.display.buffer.set_pixel(bar_x, bar_y + 2, True)
        self.display.buffer.set_pixel(bar_x + bar_width - 1, bar_y + 1, True)
        self.display.buffer.set_pixel(bar_x + bar_width - 1, bar_y + 2, True)

        fill_width = int((bar_width - 2) * self.state.volume / 100)
        for y in range(bar_y + 1, bar_y + bar_height):
            for x in range(bar_x + 1, bar_x + 1 + fill_width):
                self.display.buffer.set_pixel(x, y, True)

    def handle_button(self, button: str, pressed: bool):
        """Handle button and encoder events"""
        current_time = time.time()

        if button.startswith("volume_"):
            if pressed:
                if button == "volume_cw":
                    self.state.volume = self.state.volume_control.volume_up(2)
                    self.state.volume_overlay_timeout = current_time + self.VOLUME_OVERLAY_DURATION
                elif button == "volume_ccw":
                    self.state.volume = self.state.volume_control.volume_down(2)
                    self.state.volume_overlay_timeout = current_time + self.VOLUME_OVERLAY_DURATION
                elif button == "volume_press":
                    # Toggle mute functionality could be added here
                    pass
            return
        elif button.startswith("control_"):
            if pressed:
                current_source = self.state.get_current_source()
                
                if current_source == "INTERNET":
                    # Internet radio station navigation
                    if button == "control_cw":
                        # Next station
                        stations = self.audio.get_stations()
                        if stations:
                            current_idx = 0
                            if self.audio.current_station:
                                try:
                                    current_idx = stations.index(self.audio.current_station)
                                except ValueError:
                                    pass
                            next_idx = (current_idx + 1) % len(stations)
                            self.audio.play_station(stations[next_idx])
                    elif button == "control_ccw":
                        # Previous station
                        stations = self.audio.get_stations()
                        if stations:
                            current_idx = 0
                            if self.audio.current_station:
                                try:
                                    current_idx = stations.index(self.audio.current_station)
                                except ValueError:
                                    pass
                            prev_idx = (current_idx - 1) % len(stations)
                            self.audio.play_station(stations[prev_idx])
                    elif button == "control_press":
                        # Toggle play/pause for current station
                        self.audio.toggle_pause()
                
                elif current_source == "USB":
                    # USB file navigation
                    if button == "control_cw":
                        self.select_next_file()
                    elif button == "control_ccw":
                        self.select_prev_file()
                    elif button == "control_press":
                        self.select_file()
                
                elif current_source == "SD_CARD":
                    # SD card file navigation
                    if button == "control_cw":
                        self.select_next_sd_file()
                    elif button == "control_ccw":
                        self.select_prev_sd_file()
                    elif button == "control_press":
                        self.select_sd_file()
                
                elif current_source == "BLUETOOTH":
                    # Bluetooth controls
                    if button == "control_cw":
                        # Next track (if supported by connected device)
                        pass
                    elif button == "control_ccw":
                        # Previous track (if supported by connected device)
                        pass
                    elif button == "control_press":
                        # Play/pause toggle
                        self.audio.toggle_pause()
            return

        if not pressed:
            return

        if button == "power":
            self.state.toggle_standby()
            if self.state.standby:
                self.hardware_out.set_amp_enable(False)
            else:
                self.hardware_out.set_amp_enable(True)
        elif button == "source" and not self.state.standby:
            # Stop current playback when changing sources
            self.audio.stop()
            
            # Change to next source
            self.state.next_source()
        elif button == "menu" and not self.state.standby:
            if self.state.mode == UIMode.MENU:
                self.state.mode = UIMode.NORMAL
            else:
                self.show_main_menu()

    def handle_encoder(self, direction: str):
        """Handle encoder events"""
        if direction == "cw":
            self.state.volume = self.state.volume_control.volume_up(2)
            self.state.volume_overlay_timeout = time.time() + self.VOLUME_OVERLAY_DURATION
        elif direction == "ccw":
            self.state.volume = self.state.volume_control.volume_down(2)
            self.state.volume_overlay_timeout = time.time() + self.VOLUME_OVERLAY_DURATION

    def select_next_file(self):
        """Select next file in browser"""
        files = self.audio.get_current_files()
        if not files or len(files) == 0:
            return
            
        # Find current file index
        current_idx = self.state.selected_file_idx
        if self.audio.current_file:
            try:
                current_idx = files.index(self.audio.current_file)
            except ValueError:
                pass
                
        # Make sure current_idx is valid
        if current_idx >= len(files):
            current_idx = 0
                
        # Update to next file
        next_idx = (current_idx + 1) % len(files)
        self.state.selected_file_idx = next_idx
        self.audio.current_file = files[next_idx]

    def select_prev_file(self):
        """Select previous file in browser"""
        files = self.audio.get_current_files()
        if not files or len(files) == 0:
            return
            
        # Find current file index
        current_idx = self.state.selected_file_idx
        if self.audio.current_file:
            try:
                current_idx = files.index(self.audio.current_file)
            except ValueError:
                pass
                
        # Make sure current_idx is valid
        if current_idx >= len(files):
            current_idx = 0
                
        # Update to previous file
        prev_idx = (current_idx - 1) % len(files)
        self.state.selected_file_idx = prev_idx
        self.audio.current_file = files[prev_idx]

    def select_file(self):
        """Select current file in USB browser"""
        files = self.audio.get_current_files()
        if not files or len(files) == 0:
            print("No USB files available")
            return

        # Get current file based on index
        current_idx = self.state.selected_file_idx
        if current_idx >= len(files):
            print(f"Warning: selected_file_idx {current_idx} out of range, resetting to 0")
            current_idx = 0
            self.state.selected_file_idx = 0
            
        if self.audio.current_file:
            try:
                current_idx = files.index(self.audio.current_file)
            except ValueError:
                print(f"Warning: current_file not found in files list")
                pass
                
        print(f"Selecting USB file at index {current_idx} of {len(files)} files")
        file = files[current_idx]
        if self.audio.navigate_to(file):
            # Reset selection to first item when navigating to a new directory
            self.state.selected_file_idx = 0
            print(f"Navigated to directory: {file.path}")
        else:
            print(f"Selected file: {file.path}")
            
        # Keep the USB_BROWSER mode even when playing a file
        # This allows the user to see what's playing and select other files

    def select_next_sd_file(self):
        """Select next file in SD card browser"""
        files = self.audio.get_sd_card_files()
        if not files or len(files) == 0:
            return
            
        # Find current file index
        current_idx = self.state.selected_file_idx
        if self.audio.current_sd_file:
            try:
                current_idx = files.index(self.audio.current_sd_file)
            except ValueError:
                pass
                
        # Make sure current_idx is valid
        if current_idx >= len(files):
            current_idx = 0
                
        # Update to next file
        next_idx = (current_idx + 1) % len(files)
        self.state.selected_file_idx = next_idx
        self.audio.current_sd_file = files[next_idx]

    def select_prev_sd_file(self):
        """Select previous file in SD card browser"""
        files = self.audio.get_sd_card_files()
        if not files or len(files) == 0:
            return
            
        # Find current file index
        current_idx = self.state.selected_file_idx
        if self.audio.current_sd_file:
            try:
                current_idx = files.index(self.audio.current_sd_file)
            except ValueError:
                pass
                
        # Make sure current_idx is valid
        if current_idx >= len(files):
            current_idx = 0
                
        # Update to previous file
        prev_idx = (current_idx - 1) % len(files)
        self.state.selected_file_idx = prev_idx
        self.audio.current_sd_file = files[prev_idx]

    def select_sd_file(self):
        """Select current file in SD card browser"""
        files = self.audio.get_sd_card_files()
        if not files or len(files) == 0:
            print("No SD card files available")
            return

        # Get current file based on index
        current_idx = self.state.selected_file_idx
        if current_idx >= len(files):
            print(f"Warning: selected_file_idx {current_idx} out of range, resetting to 0")
            current_idx = 0
            self.state.selected_file_idx = 0
            
        if self.audio.current_sd_file:
            try:
                current_idx = files.index(self.audio.current_sd_file)
            except ValueError:
                print(f"Warning: current_sd_file not found in files list")
                pass
                
        print(f"Selecting SD file at index {current_idx} of {len(files)} files")
        file = files[current_idx]
        if self.audio.navigate_to_sd_card(file):
            # Reset selection to first item when navigating to a new directory
            self.state.selected_file_idx = 0
            print(f"Navigated to directory: {file.path}")
        else:
            print(f"Selected file: {file.path}")
            
        # Keep the SD_CARD_BROWSER mode even when playing a file
        # This allows the user to see what's playing and select other files

    def show_main_menu(self):
        """Show main menu"""
        self.state.mode = UIMode.MENU
