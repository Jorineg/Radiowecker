# audio.py - Main Audio Manager class for the Radiowecker project

import csv
import os
import threading
import time
from typing import List, Tuple, Optional, Dict
from queue import Queue, Empty
import subprocess

# Import our modular components
from audio_types import (
    AudioSource, AudioFile, AudioStation, AudioCommandType, 
    AudioCommand, BACK, THIS_DIR, FILE_PATH_PREFIX, SUPPORTED_AUDIO_EXTENSIONS
)
from file_system import scan_directory as fs_scan_directory, find_audio_files_recursively
from bluetooth_utils import get_bluetooth_info, toggle_bluetooth_mute, get_connected_bluetooth_device

# Try importing optional dependencies
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


class AudioManager:
    def __init__(self):
        # VLC-related variables
        self.instance = None
        self.player = None
        self.media_list = None
        self.list_player = None
        self.command_queue = Queue()
        
        # Bluetooth-related variables
        self.bluetooth_muted = False
        self.connected_bt_device = None
        self.connected_bt_device_name = None
        self.current_bt_track = None
        self.current_bt_artist = None
        self.last_bt_update = 0

        # Initialize hardware-specific components
        self._init_hardware()

        # Sources and content variables
        self.source = AudioSource.RADIO
        
        # File system variables
        self._init_filesystems()
        
        # VLC initialization
        self._init_vlc()
        
        # Load stations, scan directories
        self.load_stations()
        self.scan_directory()
        self.scan_sd_card_directory()
        
        # Initialize current item references
        self.current_station = self.stations[0] if self.stations else None
        self.current_file = self.files[0] if self.files else None
        self.current_sd_file = self.sd_card_files[0] if self.sd_card_files else None

    def _init_hardware(self):
        """Initialize hardware-specific components"""
        if RPI_HARDWARE:
            try:
                print("Initializing audio device...")
                # Ensure bluealsa is running
                subprocess.run(['systemctl', 'is-active', '--quiet', 'bluealsa'], check=False)
                # Get currently connected Bluetooth device
                self._update_bluetooth_connection()
            except Exception as e:
                print(f"Warning: Could not initialize audio device: {e}")

    def _init_filesystems(self):
        """Initialize filesystem-related variables"""
        # USB/File playback
        self.current_dir = "/"
        self.files: List[AudioFile] = []
        
        # SD Card playback
        self.sd_card_mount_point = "/mnt/musik"  # Hardcoded mount point
        self.sd_card_dir = self.sd_card_mount_point
        self.sd_card_files: List[AudioFile] = []
        
        # Check if the SD card partition is mounted
        self._setup_sd_card_partition()

    def _init_vlc(self):
        """Initialize VLC if available"""
        if not VLC_AVAILABLE:
            print("VLC not available")
            return
            
        if RPI_HARDWARE:
            # Add audio normalization filter to balance loudness across all audio sources
            self.instance = vlc.Instance("--verbose=2", "--aout=pulse",
                                        "--audio-filter=normvol",
                                        "--norm-max-level=1.8",
                                        "--norm-buff-size=20")
        else:
            # Add audio normalization filter to balance loudness across all audio sources
            self.instance = vlc.Instance("--verbose=2",
                                        "--audio-filter=normvol",
                                        "--norm-max-level=1.8",
                                        "--norm-buff-size=20")
            
        self.player = self.instance.media_player_new()
        self.media_list = self.instance.media_list_new()
        self.list_player = self.instance.media_list_player_new()
        self.list_player.set_media_player(self.player)

    def load_stations(self, filename: str = "stations.csv"):
        """Load internet radio stations from CSV file"""
        self.stations = []
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

    def scan_directory(self, directory=None):
        """Scan directory for audio files and subdirectories"""
        try:
            if directory is None:
                directory = self.current_dir
            else:
                self.current_dir = directory

            self.files = fs_scan_directory(directory, is_sd_card=False, root_path="/")
                
        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")
            # Clear any partial results
            self.files = []
            # Add a special "error" entry
            self.files.append(AudioFile(name=f"Error: {str(e)}", path=directory, is_special=True))

    def scan_sd_card_directory(self, directory=None):
        """Scan SD card directory for audio files and subdirectories"""
        try:
            if directory is None:
                directory = self.sd_card_dir
            else:
                self.sd_card_dir = directory

            self.sd_card_files = fs_scan_directory(directory, is_sd_card=True, root_path=self.sd_card_mount_point)
                
        except Exception as e:
            print(f"Error scanning SD card directory {directory}: {e}")
            # Clear any partial results
            self.sd_card_files = []
            # Add a special "error" entry
            self.sd_card_files.append(AudioFile(name=f"Error: {str(e)}", path=directory, is_special=True))

    def _clear_media_list(self):
        """Clear the existing media list"""
        if not self.media_list:
            return
            
        self.media_list.lock()
        try:
            while self.media_list.count() > 0:
                self.media_list.remove_index(0)
        finally:
            self.media_list.unlock()

    def _create_playlist(self, start_file: AudioFile, files_list: List[AudioFile], directory: str, 
                        is_sd_card: bool = False):
        """Create a playlist starting from the given file"""
        # Clear existing media list
        self._clear_media_list()
        
        # If THIS_DIR is selected, create a playlist of all files in the directory and subdirectories
        if start_file.is_special and start_file.name == THIS_DIR:
            source_name = "SD card" if is_sd_card else "directory"
            print(f"Creating recursive playlist from {source_name}: {directory}")
            
            # Find all audio files recursively
            all_files = find_audio_files_recursively(directory, max_files=100)
            
            if all_files:
                # Shuffle the files
                import random
                random.shuffle(all_files)
                
                # Take the first 30 files (or fewer if less than 30 were found)
                playlist_files = all_files[:30]
                
                print(f"Adding {len(playlist_files)} files to playlist from recursive {source_name} scan")
                
                # Add all files to media list
                self.media_list.lock()
                try:
                    for file in playlist_files:
                        media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
                        self.media_list.add_media(media)
                finally:
                    self.media_list.unlock()
                
                # Set source
                self.source = AudioSource.SD_CARD if is_sd_card else AudioSource.USB
                
                return True
            else:
                print(f"No files found in recursive {source_name} scan, falling back to regular directory playback")
                # Fallback to regular directory playback if no files found recursively
                playable_files = [f for f in files_list if not f.is_dir and not f.is_special]
                
                if playable_files:
                    print(f"Adding {len(playable_files)} files to playlist from current {source_name}")
                    # Add all files to media list
                    self.media_list.lock()
                    try:
                        for file in playable_files:
                            media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
                            self.media_list.add_media(media)
                    finally:
                        self.media_list.unlock()
                    
                    # Set source
                    self.source = AudioSource.SD_CARD if is_sd_card else AudioSource.USB
                    
                    return True
                else:
                    print(f"No playable files found in current {source_name}")
                    return False
                
        # Find all playable files (not directories or special files)
        playable_files = [f for f in files_list if not f.is_dir and not f.is_special]

        if not playable_files:
            print("No playable files found")
            return False

        # If start_file is a directory, start from first file in that directory
        if start_file.is_dir:
            # Scan the directory
            old_dir = self.sd_card_dir if is_sd_card else self.current_dir
            
            if is_sd_card:
                self.scan_sd_card_directory(start_file.path)
                playable_files = [f for f in self.sd_card_files if not f.is_dir and not f.is_special]
                if not playable_files:
                    self.scan_sd_card_directory(old_dir)
                    print(f"No playable files found in SD card directory: {start_file.path}")
                    return False
            else:
                self.scan_directory(start_file.path)
                playable_files = [f for f in self.files if not f.is_dir and not f.is_special]
                if not playable_files:
                    self.scan_directory(old_dir)
                    print(f"No playable files found in directory: {start_file.path}")
                    return False
                    
            start_file = playable_files[0]

        # Find the start index
        try:
            start_idx = playable_files.index(start_file)
        except ValueError:
            start_idx = 0

        # Create the playlist starting from start_file
        playlist_order = playable_files[start_idx:] + playable_files[:start_idx]

        source_name = "SD card" if is_sd_card else "directory" 
        print(f"Adding {len(playlist_order)} files to playlist from current {source_name}")
        
        # Add files to media list
        self.media_list.lock()
        try:
            for file in playlist_order:
                media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
                self.media_list.add_media(media)
        finally:
            self.media_list.unlock()
        
        # Set source
        self.source = AudioSource.SD_CARD if is_sd_card else AudioSource.USB
        
        return True

    def _create_playlist_from_file(self, start_file: AudioFile):
        """Create a playlist starting from the given file in USB mode"""
        return self._create_playlist(start_file, self.files, self.current_dir, is_sd_card=False)

    def _create_sd_card_playlist_from_file(self, start_file: AudioFile):
        """Create a playlist from SD card files starting from the given file"""
        return self._create_playlist(start_file, self.sd_card_files, self.sd_card_dir, is_sd_card=True)

    def process_commands(self):
        """Process any pending audio commands - should be called from main thread"""
        try:
            while True:  # Process all pending commands
                command = self.command_queue.get_nowait()
                if command.command_type == AudioCommandType.PLAY_STATION:
                    self._play_station(command.data)
                elif command.command_type == AudioCommandType.PLAY_FILE:
                    self._play_file(command.data)
                elif command.command_type == AudioCommandType.STOP:
                    self._stop()
                elif command.command_type == AudioCommandType.TOGGLE_PAUSE:
                    self._toggle_pause()
                elif command.command_type == AudioCommandType.MUTE_BLUETOOTH:
                    self._mute_bluetooth()
                elif command.command_type == AudioCommandType.UNMUTE_BLUETOOTH:
                    self._unmute_bluetooth()
                self.command_queue.task_done()
        except Empty:
            pass  # No more commands to process

    def play_station(self, station: AudioStation):
        """Queue a command to play a radio station"""
        self.command_queue.put(AudioCommand(AudioCommandType.PLAY_STATION, station))

    def _play_media(self, file: AudioFile, is_sd_card: bool = False):
        """Common code for playing a file from USB or SD card"""
        # Stop any current playback
        if VLC_AVAILABLE:
            # Stop both the player and list_player to ensure any current playlist is stopped
            if self.player:
                self.player.stop()
            if self.list_player:
                self.list_player.stop()
                
            # Clear the media list to ensure we don't keep playing the old playlist
            self._clear_media_list()
            
        # Update source tracking variables
        if is_sd_card:
            self.current_sd_file = file
            self.current_file = None
            self.source = AudioSource.SD_CARD
        else:
            self.current_file = file
            self.current_sd_file = None
            self.source = AudioSource.USB
            
        self.current_station = None
        
        if VLC_AVAILABLE:
            # Create a playlist starting from this file
            playlist_created = False
            if is_sd_card:
                playlist_created = self._create_sd_card_playlist_from_file(file)
            else:
                playlist_created = self._create_playlist_from_file(file)
                
            if playlist_created:
                self.list_player.set_media_list(self.media_list)
                self.list_player.play()
                return
                
        # Fallback to regular file playing
        self.command_queue.put(AudioCommand(AudioCommandType.PLAY_FILE, file))

    def play_file(self, file: AudioFile):
        """Play a file from USB"""
        self._play_media(file, is_sd_card=False)

    def play_sd_card_file(self, file: AudioFile):
        """Play a file from the SD card"""
        self._play_media(file, is_sd_card=True)

    def stop(self):
        """Stop playback"""
        self.command_queue.put(AudioCommand(AudioCommandType.STOP))

    def toggle_pause(self):
        """Toggle pause/play state"""
        self.command_queue.put(AudioCommand(AudioCommandType.TOGGLE_PAUSE))

    def mute_bluetooth(self):
        """Mute Bluetooth audio"""
        self.command_queue.put(AudioCommand(AudioCommandType.MUTE_BLUETOOTH))

    def unmute_bluetooth(self):
        """Unmute Bluetooth audio"""
        self.command_queue.put(AudioCommand(AudioCommandType.UNMUTE_BLUETOOTH))

    def _mute_bluetooth(self):
        """Temporarily disable Bluetooth audio output"""
        # Use Bluetooth utilities
        self.bluetooth_muted = toggle_bluetooth_mute(mute=True)

    def _unmute_bluetooth(self):
        """Re-enable Bluetooth audio output"""
        # Use Bluetooth utilities
        self.bluetooth_muted = not toggle_bluetooth_mute(mute=False)

    def _play_station(self, station: AudioStation):
        """Internal method to play a radio station"""
        if not self.player:
            print("VLC not initialized... returning")
            return

        self.current_station = station
        self.current_file = None
        self.current_sd_file = None
        self.source = AudioSource.RADIO

        try:
            # Stop any existing playback
            self._stop()
            
            # Create media without additional options (they're already set in the instance)
            media = self.instance.media_new(station.url)
            self.player.set_media(media)
            self.player.play()
            print(f"Playing station: {station.name}. VLC play() called")
        except Exception as e:
            print(f"Error playing station: {e}")

    def _play_file(self, file: AudioFile):
        """Internal method to play a file"""
        if not self.player:
            return

        self.current_file = file
        self.current_station = None

        try:
            # Stop any existing playback
            self._stop()
            if self._create_playlist_from_file(file):
                self.list_player.set_media_list(self.media_list)
                self.list_player.play()
        except Exception as e:
            print(f"Error playing file: {e}")

    def _stop(self):
        """Stop all playback"""
        if self.player:
            self.player.stop()
        if self.list_player:
            self.list_player.stop()
            
        # Clear the media list to ensure we don't keep playing the old playlist
        self._clear_media_list()

    def _toggle_pause(self):
        """Toggle pause/play state"""
        if self.player:
            if self.player.is_playing():
                self.player.pause()
            else:
                self.player.play()

    def _setup_sd_card_partition(self):
        """Check if the SD card partition is mounted"""
        if not RPI_HARDWARE:
            # For testing on non-Pi hardware
            self.sd_card_dir = "/"
            return
            
        try:
            # Check if the mount point exists and is mounted
            if os.path.exists(self.sd_card_mount_point):
                # Check if it's mounted
                import subprocess
                mount_result = subprocess.run(['findmnt', self.sd_card_mount_point], 
                                         capture_output=True, text=True, check=False)
                
                if mount_result.returncode == 0:
                    print(f"SD card partition mounted at {self.sd_card_mount_point}")
                else:
                    print(f"SD card mount point exists but is not mounted")
            else:
                print(f"SD card mount point {self.sd_card_mount_point} does not exist")
                
        except Exception as e:
            print(f"Error checking SD card mount: {e}")

    def cleanup(self):
        """Cleanup resources"""
        if VLC_AVAILABLE and self.player:
            self.player.stop()

    def _navigate_common(self, audio_file: AudioFile, is_sd_card: bool = False):
        """Common navigation logic for both USB and SD card"""
        if not audio_file:
            print("Warning: Attempted to navigate to None audio_file")
            return False
            
        try:
            if audio_file.is_dir and not audio_file.is_special:
                # Store the current directory before changing it
                old_dir = self.sd_card_dir if is_sd_card else self.current_dir
                
                # Scan the new directory
                if is_sd_card:
                    self.scan_sd_card_directory(audio_file.path)
                    # Update current_file to the first file in the new directory
                    if len(self.sd_card_files) > 0:
                        self.current_sd_file = self.sd_card_files[0]
                    else:
                        self.current_sd_file = None
                else:
                    self.scan_directory(audio_file.path)
                    # Update current_file to the first file in the new directory
                    if len(self.files) > 0:
                        self.current_file = self.files[0]
                    else:
                        self.current_file = None
                
                return True
                
            elif audio_file.is_special and audio_file.name == BACK:
                # Go to parent directory
                from pathlib import Path
                current_dir = self.sd_card_dir if is_sd_card else self.current_dir
                parent = str(Path(current_dir).parent)
                
                # Store the current directory before changing it
                old_dir = current_dir
                
                # Scan the parent directory
                if is_sd_card:
                    self.scan_sd_card_directory(parent)
                    # Update current_file to find the directory we came from
                    if len(self.sd_card_files) > 0:
                        # Try to find the directory we just came from
                        for i, file in enumerate(self.sd_card_files):
                            if file.is_dir and file.path == old_dir:
                                self.current_sd_file = file
                                break
                        else:
                            # If not found, use the first file
                            self.current_sd_file = self.sd_card_files[0]
                    else:
                        self.current_sd_file = None
                else:
                    self.scan_directory(parent)
                    # Update current_file to find the directory we came from
                    if len(self.files) > 0:
                        # Try to find the directory we just came from
                        for i, file in enumerate(self.files):
                            if file.is_dir and file.path == old_dir:
                                self.current_file = file
                                break
                        else:
                            # If not found, use the first file
                            self.current_file = self.files[0]
                    else:
                        self.current_file = None
                
                return True
                
            elif audio_file.is_special and audio_file.name == THIS_DIR:
                # Explicitly stop any current playback before playing all files in current directory
                if VLC_AVAILABLE:
                    if self.player:
                        self.player.stop()
                    if self.list_player:
                        self.list_player.stop()
                    self._clear_media_list()
                
                # Play all files in current directory
                if is_sd_card:
                    self.play_sd_card_file(audio_file)
                else:
                    self.play_file(audio_file)
                return False
                
            else:
                # Explicitly stop any current playback before playing the file
                if VLC_AVAILABLE:
                    if self.player:
                        self.player.stop()
                    if self.list_player:
                        self.list_player.stop()
                    self._clear_media_list()
                
                # Play the file
                if is_sd_card:
                    self.play_sd_card_file(audio_file)
                else:
                    self.play_file(audio_file)
                return False
                
        except Exception as e:
            storage_type = "SD card" if is_sd_card else "file"
            print(f"Error navigating to {storage_type}: {e}")
            return False

    def navigate_to(self, audio_file: AudioFile):
        """Navigate to directory or play file in USB mode"""
        return self._navigate_common(audio_file, is_sd_card=False)

    def navigate_to_sd_card(self, audio_file: AudioFile):
        """Navigate to directory or play file on SD card"""
        return self._navigate_common(audio_file, is_sd_card=True)

    def get_current_files(self) -> List[AudioFile]:
        """Get files in current directory"""
        return self.files

    def get_sd_card_files(self) -> List[AudioFile]:
        """Get files in current SD card directory"""
        return self.sd_card_files

    def get_stations(self) -> List[AudioStation]:
        """Get available radio stations"""
        return self.stations

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.player and self.player.is_playing() == 1

    def get_current_info(self) -> Tuple[str, str]:
        """Get current playing info (source, name)"""
        if self.source == AudioSource.RADIO and self.current_station:
            return "RADIO", self.current_station.name
        elif self.source == AudioSource.USB and self.current_file:
            return "USB", self.current_file.name
        elif self.source == AudioSource.SD_CARD and self.current_sd_file:
            return "SD_CARD", self.current_sd_file.name
        else:
            # Default to radio if nothing is set
            return "RADIO", ""

    def set_volume(self, volume: int):
        """Set volume (0-100)"""
        self.volume = max(0, min(100, volume))
        if self.player:
            self.player.audio_set_volume(self.volume)

    def _update_bluetooth_connection(self):
        """Update information about connected Bluetooth devices"""
        self.connected_bt_device_name = get_connected_bluetooth_device()
        if self.connected_bt_device_name:
            # Extract device address from name
            import re
            self.connected_bt_device = re.search(r'([0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2})', 
                                            self.connected_bt_device_name, re.IGNORECASE)
            if self.connected_bt_device:
                self.connected_bt_device = self.connected_bt_device.group(1)

    def get_bluetooth_info(self, force_update=False):
        """Get information about the connected Bluetooth device"""
        current_time = time.time()
        
        # Only update every 2 seconds, unless force_update is True
        if not force_update and current_time - self.last_bt_update < 2:
            return (self.connected_bt_device_name or "Not connected", 
                   f"{self.current_bt_track or ''}\n{self.current_bt_artist or ''}" if self.current_bt_track else None)
        
        self.last_bt_update = current_time
        
        bt_title, bt_artist, bt_status = get_bluetooth_info()
        self.current_bt_track = bt_title
        self.current_bt_artist = bt_artist
        
        if not bt_title or bt_title == "Unknown Title":
            # No track info
            return self.connected_bt_device_name or "Not connected", None
        
        track_info = bt_title
        if bt_artist and bt_artist != "Unknown Artist":
            track_info += f"\n{bt_artist}"
            
        return self.connected_bt_device_name or "Connected", track_info