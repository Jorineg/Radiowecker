# audio.py

import csv
import os
from typing import List, Tuple, Optional
from pathlib import Path

try:
    import vlc

    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False


class AudioStation:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url


class AudioFile:
    def __init__(self, path: str, is_dir: bool = False):
        self.path = path
        self.name = os.path.basename(path)
        self.is_dir = is_dir


class AudioManager:
    def __init__(self):
        self.instance = None
        self.player = None
        self.volume = 50

        # Internet Radio
        self.stations: List[AudioStation] = []

        # USB/File playback
        self.current_dir = "/"
        self.files: List[AudioFile] = []

        # Initialize VLC if available
        if VLC_AVAILABLE:
            self.instance = vlc.Instance()
            self.player = self.instance.media_player_new()
            self.player.audio_set_volume(self.volume)

        # Load stations
        self.load_stations()
        self.current_station = self.stations[0]

        # Scan directory
        self.scan_directory()
        self.current_file = self.files[0]

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
            self.files.append(AudioFile(parent, is_dir=True))

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

    def play_station(self, station: AudioStation):
        """Play internet radio station"""
        if not self.player:
            return

        self.current_station = station
        self.current_file = None

        try:
            media = self.instance.media_new(station.url)
            self.player.set_media(media)
            self.player.play()
        except Exception as e:
            print(f"Error playing station: {e}")

    def play_file(self, audio_file: AudioFile):
        """Play audio file"""
        if not self.player or audio_file.is_dir:
            return

        self.current_file = audio_file
        self.current_station = None

        try:
            media = self.instance.media_new(audio_file.path)
            self.player.set_media(media)
            self.player.play()
        except Exception as e:
            print(f"Error playing file: {e}")

    def stop(self):
        """Stop playback"""
        if self.player:
            self.player.stop()

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
        if audio_file.is_dir:
            self.scan_directory(audio_file.path)
        else:
            self.play_file(audio_file)

    def get_current_files(self) -> List[AudioFile]:
        """Get files in current directory"""
        return self.files

    def get_stations(self) -> List[AudioStation]:
        """Get available radio stations"""
        return self.stations
