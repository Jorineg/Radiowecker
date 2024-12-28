# audio.py

import csv
import os
from typing import List, Tuple, Optional
from pathlib import Path

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


class AudioManager:
    def __init__(self):
        self.instance = None
        self.player = None
        self.media_list = None
        self.list_player = None

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
            self.player.audio_set_volume(100)
        else:
            print("VLC not available")

        # Load stations
        self.load_stations()
        self.current_station = self.stations[0]

        # Scan directory
        self.scan_directory()
        self.current_file = self.files[0] if len(self.files) > 0 else None
        # self.current_file = None

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

    def play_station(self, station: AudioStation):
        """Play internet radio station"""
        if not self.player:
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
        except Exception as e:
            print(f"Error playing station: {e}")

    def play_file(self, audio_file: AudioFile):
        """Play audio file"""
        if not self.player:
            return

        self.current_file = audio_file
        self.current_station = None

        try:
            if self._create_playlist_from_file(audio_file):
                self.list_player.set_media_list(self.media_list)
                self.list_player.play()
        except Exception as e:
            print(f"Error playing file: {e}")

    def stop(self):
        """Stop playback"""
        if self.player:
            self.player.stop()

    def cleanup(self):
        """Cleanup resources"""
        if self.player:
            self.player.stop()
            self.player.release()
        if self.instance:
            self.instance.release()

    def pause(self):
        """Toggle pause"""
        if self.player:
            self.player.pause()

    def set_volume(self, volume: int):
        """Set volume (0-100)"""
        self.volume = max(0, min(100, volume))
        if self.player:
            self.player.audio_set_volume(self.volume)

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
