# audio.py

import csv
import os
import threading
from typing import List, Tuple, Optional
from pathlib import Path
from queue import Queue
from dataclasses import dataclass
from enum import Enum, auto

BACK = "<zurück>"
THIS_DIR = "<dieser Ordner>"

FILE_PATH_PREFIX = "D:/"

try:
    import vlc

    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False

try:
    import RPi.GPIO as GPIO

    RPI_HARDWARE = True
except ImportError:
    RPI_HARDWARE = False


class AudioStation:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url


class AudioFile:
    def __init__(self, path: str, is_dir: bool = False, name: str = None):
        self.path = path
        self.is_special = False
        if name:
            self.is_special = True
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.is_dir = is_dir


class AudioCommandType(Enum):
    PLAY_STATION = auto()
    PLAY_FILE = auto()
    STOP = auto()
    TOGGLE_PAUSE = auto()


@dataclass
class AudioCommand:
    command_type: AudioCommandType
    data: any = None


class AudioManager:
    def __init__(self):
        self.instance = None
        self.player = None
        self.media_list = None
        self.list_player = None
        self.command_queue = Queue()
        self._running = True
        self._command_thread = threading.Thread(target=self._process_commands, daemon=True)
        self._command_thread.start()

        # Internet Radio
        self.stations: List[AudioStation] = []

        # USB/File playback
        self.current_dir = "/"
        self.files: List[AudioFile] = []

        # Initialize VLC if available
        if VLC_AVAILABLE:
            if RPI_HARDWARE:
                self.instance = vlc.Instance("--aout=pulse", "--verbose=2", "--network-caching=1000")
            else:
                self.instance = vlc.Instance()
            self.player = self.instance.media_player_new()
            
            self.media_list = self.instance.media_list_new()
            self.list_player = self.instance.media_list_player_new()
            self.list_player.set_media_player(self.player)
        else:
            print("VLC not available")

        # Load stations
        self.load_stations()
        self.current_station = self.stations[0]

        # Scan directory
        self.scan_directory()
        self.current_file = self.files[0] if len(self.files) > 0 else None

    def load_stations(self, filename: str = "stations.csv"):
        """Load internet radio stations from CSV file"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                self.stations = [
                    AudioStation(name.strip(), url.strip())
                    for name, url in reader
                    if name and url  # Skip empty lines
                ]
        except FileNotFoundError:
            print(f"Warning: {filename} not found")
            # Add some default stations
            self.stations = [
                AudioStation("Radio Example 1", "http://example.com/stream1"),
                AudioStation("Radio Example 2", "http://example.com/stream2"),
            ]

    def scan_directory(self, path: str = None):
        """Scan directory for audio files"""
        if path:
            self.current_dir = path

        self.files.clear()

        # Add parent directory if not in root
        if self.current_dir != "/":
            parent = str(Path(self.current_dir).parent)
            self.files.append(AudioFile(parent, is_dir=True, name=BACK))

        try:
            # Add directories first
            for item in sorted(os.listdir(self.current_dir)):
                full_path = os.path.join(self.current_dir, item)
                if os.path.isdir(full_path):
                    self.files.append(AudioFile(full_path, is_dir=True))

            # Then add audio files
            for item in sorted(os.listdir(self.current_dir)):
                full_path = os.path.join(self.current_dir, item)
                if os.path.isfile(full_path):
                    ext = os.path.splitext(item)[1].lower()
                    if ext in [".mp3", ".wav", ".ogg", ".m4a"]:
                        self.files.append(AudioFile(full_path))
        except PermissionError:
            print(f"Permission denied: {self.current_dir}")
        except Exception as e:
            print(f"Error scanning directory: {e}")

        # Add current directory
        self.files.append(AudioFile(self.current_dir, is_dir=True, name=THIS_DIR))

    def _process_commands(self):
        while self._running:
            try:
                command = self.command_queue.get(timeout=0.5)
                if command.command_type == AudioCommandType.PLAY_STATION:
                    self._play_station(command.data)
                elif command.command_type == AudioCommandType.PLAY_FILE:
                    self._play_file(command.data)
                elif command.command_type == AudioCommandType.STOP:
                    self._stop()
                elif command.command_type == AudioCommandType.TOGGLE_PAUSE:
                    self._toggle_pause()
                self.command_queue.task_done()
            except queue.Empty:
                continue

    def play_station(self, station: AudioStation):
        self.command_queue.put(AudioCommand(AudioCommandType.PLAY_STATION, station))

    def play_file(self, file: AudioFile):
        self.command_queue.put(AudioCommand(AudioCommandType.PLAY_FILE, file))

    def stop(self):
        self.command_queue.put(AudioCommand(AudioCommandType.STOP))

    def toggle_pause(self):
        self.command_queue.put(AudioCommand(AudioCommandType.TOGGLE_PAUSE))

    def _play_station(self, station: AudioStation):
        if not self.player:
            print("VLC not initialized... returning")
            return

        self.current_station = station
        self.current_file = None

        try:
            # Stop any existing playback
            self.stop()
            
            # Create media without additional options (they're already set in the instance)
            media = self.instance.media_new(station.url)
            self.player.set_media(media)
            self.player.play()
            print(f"Playing station: {station.name}. VLC play() called")
        except Exception as e:
            print(f"Error playing station: {e}")

    def _play_file(self, file: AudioFile):
        if not self.player:
            return

        self.current_file = file
        self.current_station = None

        try:
            if self._create_playlist_from_file(file):
                self.list_player.set_media_list(self.media_list)
                self.list_player.play()
        except Exception as e:
            print(f"Error playing file: {e}")

    def _stop(self):
        if self.player:
            self.player.stop()

    def _toggle_pause(self):
        if self.player:
            if self.player.is_playing():
                self.player.pause()
            else:
                self.player.play()

    def _create_playlist_from_file(self, start_file: AudioFile):
        """Create a playlist starting from the given file, excluding directories and special files"""
        # Clear existing media list
        self.media_list.lock()
        while self.media_list.count() > 0:
            self.media_list.remove_index(0)

        # Find all playable files (not directories or special files)
        playable_files = [f for f in self.files if not f.is_dir and not f.is_special]

        if not playable_files:
            self.media_list.unlock()
            return False

        # If start_file is a directory, start from first file in that directory
        if start_file.is_dir:
            # Scan the directory
            old_dir = self.current_dir
            self.scan_directory(start_file.path)
            playable_files = [f for f in self.files if not f.is_dir and not f.is_special]
            if not playable_files:
                self.scan_directory(old_dir)
                self.media_list.unlock()
                return False
            start_file = playable_files[0]

        # Find the start index
        try:
            start_idx = playable_files.index(start_file)
        except ValueError:
            start_idx = 0

        # Create the playlist starting from start_file
        playlist_order = playable_files[start_idx:] + playable_files[:start_idx]

        # Add files to media list
        for file in playlist_order:
            media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
            self.media_list.add_media(media)

        self.media_list.unlock()
        return True

    def cleanup(self):
        self._running = False
        if self._command_thread.is_alive():
            self._command_thread.join(timeout=1.0)
        if self.player:
            self.player.stop()
        if self.instance:
            self.instance.release()

    def navigate_to(self, audio_file: AudioFile):
        """Navigate to directory or play file"""
        if audio_file.is_dir and not audio_file.is_special:
            self.scan_directory(audio_file.path)
            return True
        elif audio_file.is_special and audio_file.name == BACK:
            # go to parent directory
            parent = str(Path(self.current_dir).parent)
            self.scan_directory(parent)
            return True
        else:
            self.play_file(audio_file)
            return False

    def get_current_files(self) -> List[AudioFile]:
        """Get files in current directory"""
        return self.files

    def get_stations(self) -> List[AudioStation]:
        """Get available radio stations"""
        return self.stations

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.player and self.player.is_playing() == 1

    def get_current_info(self) -> Tuple[str, str]:
        """Get current playing info (source, name)"""
        if self.current_station:
            return "RADIO", self.current_station.name
        elif self.current_file:
            return "USB", self.current_file.name
        return "", ""

    def set_volume(self, volume: int):
        """Set volume (0-100)"""
        self.volume = max(0, min(100, volume))
        if self.player:
            self.player.audio_set_volume(self.volume)
