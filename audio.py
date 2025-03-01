# audio.py

import csv
import os
import threading
from typing import List, Tuple, Optional
from pathlib import Path
from queue import Queue, Empty
from dataclasses import dataclass
from enum import Enum, auto
import subprocess
import time


BACK = "<zurück>"
THIS_DIR = "<dieser Ordner>"

# FILE_PATH_PREFIX = "D:/"
FILE_PATH_PREFIX = ""

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


class AudioSource(Enum):
    USB = auto()
    SD_CARD = auto()
    RADIO = auto()


class AudioFile:
    def __init__(self, path: str, is_dir: bool = False, name: str = None, is_special: bool = False):
        self.path = path
        self.is_dir = is_dir
        self.is_special = is_special
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)


class AudioStation:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url


class AudioCommandType(Enum):
    PLAY_STATION = auto()
    PLAY_FILE = auto()
    STOP = auto()
    TOGGLE_PAUSE = auto()
    MUTE_BLUETOOTH = auto()
    UNMUTE_BLUETOOTH = auto()


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
        self.bluetooth_muted = False
        self.connected_bt_device = None
        self.connected_bt_device_name = None
        self.current_bt_track = None
        self.current_bt_artist = None
        self.last_bt_update = 0

        if RPI_HARDWARE:
            try:
                print("Initializing audio device...")
                # Ensure ALSA is properly configured for Bluetooth audio
                # subprocess.run(['amixer', 'sset', 'PCM', 'unmute'], check=False)
                # subprocess.run(['amixer', 'sset', 'PCM', '100%'], check=False)
                # Make sure bluealsa is running
                subprocess.run(['systemctl', 'is-active', '--quiet', 'bluealsa'], check=False)
                
                # Get currently connected Bluetooth device
                self._update_bluetooth_connection()
            except Exception as e:
                print(f"Warning: Could not initialize audio device: {e}")

        # Internet Radio
        self.stations: List[AudioStation] = []

        # USB/File playback
        self.current_dir = "/"
        self.files: List[AudioFile] = []
        
        # SD Card playback
        self.sd_card_mount_point = "/mnt/musik"  # Hardcoded mount point
        self.sd_card_dir = self.sd_card_mount_point
        self.sd_card_files: List[AudioFile] = []
        self.current_sd_file = None
        
        # Check if the SD card partition is mounted
        self._setup_sd_card_partition()

        # Initialize VLC if available
        if VLC_AVAILABLE:
            if RPI_HARDWARE:
                # Initialize ALSA
                try:
                    # subprocess.run(['alsactl', 'init'], check=False)
                    pass
                except Exception as e:
                    print(f"Warning: Could not initialize ALSA: {e}")
                self.instance = vlc.Instance("--verbose=2",
                                          "--aout=pulse",
                                          # "--alsa-audio-device=hw:0"
                                          )
            else:
                self.instance = vlc.Instance("--verbose=2")
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
        
        # Scan SD card directory
        self.scan_sd_card_directory()
        self.current_sd_file = self.sd_card_files[0] if len(self.sd_card_files) > 0 else None

        self.source = AudioSource.RADIO

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

    def scan_directory(self, directory=None):
        """Scan directory for audio files and subdirectories"""
        try:
            if directory is None:
                directory = self.current_dir
            else:
                self.current_dir = directory

            self.files = []
            
            # Check if directory exists
            if not os.path.exists(directory):
                print(f"Directory does not exist: {directory}")
                # Add a special "error" entry
                self.files.append(AudioFile(name="Directory not found", path=directory, is_dir=False, is_special=True))
                return
                
            try:
                entries = os.listdir(directory)
            except PermissionError:
                print(f"Permission denied: {directory}")
                # Add a special "error" entry
                self.files.append(AudioFile(name="Permission denied", path=directory, is_dir=False, is_special=True))
                return
            except Exception as e:
                print(f"Error listing directory {directory}: {e}")
                # Add a special "error" entry
                self.files.append(AudioFile(name=f"Error: {str(e)}", path=directory, is_dir=False, is_special=True))
                return

            # Add "this directory" option - always include it regardless of content
            # It will recursively scan for audio files when selected
            self.files.append(AudioFile(name=THIS_DIR, path=directory, is_dir=False, is_special=True))

            # Add back option if not in root directory
            if directory != "/":
                self.files.append(AudioFile(name=BACK, path=directory, is_dir=False, is_special=True))

            # Add directories
            for entry in sorted(entries):
                path = os.path.join(directory, entry)
                if os.path.isdir(path) and not entry.startswith('.'):
                    self.files.append(AudioFile(name=entry, path=path, is_dir=True))

            # Add audio files
            for entry in sorted(entries):
                path = os.path.join(directory, entry)
                if os.path.isfile(path) and self._is_audio_file(entry):
                    self.files.append(AudioFile(name=entry, path=path))
                                         
            # If no files or directories were found (empty directory)
            if len(self.files) == 0:
                self.files.append(AudioFile(name="Empty directory", path=directory, is_dir=False, is_special=True))
                
        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")
            # Clear any partial results
            self.files = []
            # Add a special "error" entry
            self.files.append(AudioFile(name=f"Error: {str(e)}", path=directory, is_dir=False, is_special=True))

    def scan_sd_card_directory(self, directory=None):
        """Scan SD card directory for audio files and subdirectories"""
        try:
            if directory is None:
                directory = self.sd_card_dir
            else:
                self.sd_card_dir = directory

            self.sd_card_files = []
            
            # Check if directory exists and is mounted
            if not os.path.exists(directory):
                print(f"SD card directory does not exist: {directory}")
                # Add a special "error" entry
                self.sd_card_files.append(AudioFile(name="SD card not mounted", path=directory, is_dir=False, is_special=True))
                return
                
            try:
                entries = os.listdir(directory)
            except PermissionError:
                print(f"Permission denied: {directory}")
                # Add a special "error" entry
                self.sd_card_files.append(AudioFile(name="Permission denied", path=directory, is_dir=False, is_special=True))
                return
            except Exception as e:
                print(f"Error listing SD card directory {directory}: {e}")
                # Add a special "error" entry
                self.sd_card_files.append(AudioFile(name=f"Error: {str(e)}", path=directory, is_dir=False, is_special=True))
                return

            # Add "this directory" option - always include it regardless of content
            # It will recursively scan for audio files when selected
            self.sd_card_files.append(AudioFile(name=THIS_DIR, path=directory, is_dir=False, is_special=True))

            # Add back option if not in root directory
            if directory != self.sd_card_mount_point:
                self.sd_card_files.append(AudioFile(name=BACK, path=directory, is_dir=False, is_special=True))

            # Add directories
            for entry in sorted(entries):
                path = os.path.join(directory, entry)
                if os.path.isdir(path) and not entry.startswith('.'):
                    self.sd_card_files.append(AudioFile(name=entry, path=path, is_dir=True))

            # Add audio files
            for entry in sorted(entries):
                path = os.path.join(directory, entry)
                if os.path.isfile(path) and self._is_audio_file(entry):
                    self.sd_card_files.append(AudioFile(name=entry, path=path))
                                         
            # If no files or directories were found (empty directory)
            if len(self.sd_card_files) == 0:
                self.sd_card_files.append(AudioFile(name="Empty directory", path=directory, is_dir=False, is_special=True))
                
        except Exception as e:
            print(f"Error scanning SD card directory {directory}: {e}")
            # Clear any partial results
            self.sd_card_files = []
            # Add a special "error" entry
            self.sd_card_files.append(AudioFile(name=f"Error: {str(e)}", path=directory, is_dir=False, is_special=True))

    def _find_audio_files_recursively(self, directory, max_files=100):
        """Find all audio files recursively in a directory and its subdirectories"""
        audio_files = []
        
        if not os.path.exists(directory) or not os.path.isdir(directory):
            print(f"Error: Directory does not exist or is not a directory: {directory}")
            return audio_files
            
        try:
            # Use os.walk for efficient recursive directory traversal
            for root, dirs, files in os.walk(directory):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # Process files in current directory
                for file in files:
                    # Skip hidden files
                    if file.startswith('.'):
                        continue
                        
                    # Check if we've reached the maximum number of files
                    if len(audio_files) >= max_files:
                        print(f"Reached maximum of {max_files} files, stopping recursive scan")
                        return audio_files
                        
                    # Check if it's an audio file
                    if self._is_audio_file(file):
                        full_path = os.path.join(root, file)
                        audio_files.append(AudioFile(full_path))
                        
                    # Print progress every 10 files
                    if len(audio_files) % 10 == 0 and len(audio_files) > 0:
                        print(f"Found {len(audio_files)} audio files so far...")
                        
        except PermissionError:
            print(f"Permission denied while scanning directory: {directory}")
        except Exception as e:
            print(f"Error finding audio files recursively: {e}")
            
        print(f"Found {len(audio_files)} audio files in total")
        return audio_files

    def _create_playlist_from_file(self, start_file: AudioFile):
        """Create a playlist starting from the given file, excluding directories and special files"""
        # Clear existing media list
        self.media_list.lock()
        while self.media_list.count() > 0:
            self.media_list.remove_index(0)
        self.media_list.unlock()  # Unlock before early returns to prevent deadlocks
        
        # If THIS_DIR is selected, create a playlist of all files in the directory and subdirectories
        if start_file.is_special and start_file.name == THIS_DIR:
            print(f"Creating recursive playlist from directory: {self.current_dir}")
            # Find all audio files recursively
            all_files = self._find_audio_files_recursively(self.current_dir, max_files=100)
            
            if all_files:
                # Shuffle the files
                import random
                random.shuffle(all_files)
                
                # Take the first 20 files (or fewer if less than 20 were found)
                playlist_files = all_files[:20]
                
                print(f"Adding {len(playlist_files)} files to playlist from recursive scan")
                
                # Add all files to media list
                self.media_list.lock()
                for file in playlist_files:
                    media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
                    self.media_list.add_media(media)
                
                self.media_list.unlock()
                
                # Set source to USB
                self.source = AudioSource.USB
                
                return True
            else:
                print("No files found in recursive scan, falling back to regular directory playback")
                # Fallback to regular directory playback if no files found recursively
                playable_files = [f for f in self.files if not f.is_dir and not f.is_special]
                
                if playable_files:
                    print(f"Adding {len(playable_files)} files to playlist from current directory")
                    # Add all files to media list
                    self.media_list.lock()
                    for file in playable_files:
                        media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
                        self.media_list.add_media(media)
                    
                    self.media_list.unlock()
                    
                    # Set source to USB
                    self.source = AudioSource.USB
                    
                    return True
                else:
                    print("No playable files found in current directory")
                    return False
                
        # Find all playable files (not directories or special files)
        playable_files = [f for f in self.files if not f.is_dir and not f.is_special]

        if not playable_files:
            print("No playable files found")
            return False

        # If start_file is a directory, start from first file in that directory
        if start_file.is_dir:
            # Scan the directory
            old_dir = self.current_dir
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

        print(f"Adding {len(playlist_order)} files to playlist from current directory")
        
        # Add files to media list
        self.media_list.lock()
        for file in playlist_order:
            media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
            self.media_list.add_media(media)

        self.media_list.unlock()
        
        # Set source to USB
        self.source = AudioSource.USB
        
        return True

    def _create_sd_card_playlist_from_file(self, start_file: AudioFile):
        """Create a playlist from SD card files starting from the given file"""
        # Clear existing media list
        self.media_list.lock()
        while self.media_list.count() > 0:
            self.media_list.remove_index(0)
        self.media_list.unlock()  # Unlock before early returns to prevent deadlocks

        # If THIS_DIR is selected, create a playlist of all files in the directory and subdirectories
        if start_file.is_special and start_file.name == THIS_DIR:
            print(f"Creating recursive playlist from SD card directory: {self.sd_card_dir}")
            # Find all audio files recursively
            all_files = self._find_audio_files_recursively(self.sd_card_dir, max_files=100)
            
            if all_files:
                # Shuffle the files
                import random
                random.shuffle(all_files)
                
                # Take the first 20 files (or fewer if less than 20 were found)
                playlist_files = all_files[:20]
                
                print(f"Adding {len(playlist_files)} files to playlist from recursive SD card scan")
                
                # Add all files to media list
                self.media_list.lock()
                for file in playlist_files:
                    media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
                    self.media_list.add_media(media)
                
                self.media_list.unlock()
                
                # Set source to SD_CARD
                self.source = AudioSource.SD_CARD
                
                return True
            else:
                print("No files found in recursive SD card scan, falling back to regular directory playback")
                # Fallback to regular directory playback if no files found recursively
                playable_files = [f for f in self.sd_card_files if not f.is_dir and not f.is_special]
                
                if playable_files:
                    print(f"Adding {len(playable_files)} files to playlist from current SD card directory")
                    # Add all files to media list
                    self.media_list.lock()
                    for file in playable_files:
                        media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
                        self.media_list.add_media(media)
                    
                    self.media_list.unlock()
                    
                    # Set source to SD_CARD
                    self.source = AudioSource.SD_CARD
                    
                    return True
                else:
                    print("No playable files found in current SD card directory")
                    return False
                
        # Find all playable files (not directories or special files)
        playable_files = [f for f in self.sd_card_files if not f.is_dir and not f.is_special]

        if not playable_files:
            print("No playable SD card files found")
            return False

        # If start_file is a directory, start from first file in that directory
        if start_file.is_dir:
            # Scan the directory
            old_dir = self.sd_card_dir
            self.scan_sd_card_directory(start_file.path)
            playable_files = [f for f in self.sd_card_files if not f.is_dir and not f.is_special]
            if not playable_files:
                self.scan_sd_card_directory(old_dir)
                print(f"No playable files found in SD card directory: {start_file.path}")
                return False
            start_file = playable_files[0]

        # Find the start index
        try:
            start_idx = playable_files.index(start_file)
        except ValueError:
            start_idx = 0

        # Create the playlist starting from start_file
        playlist_order = playable_files[start_idx:] + playable_files[:start_idx]

        print(f"Adding {len(playlist_order)} files to playlist from current SD card directory")
        
        # Add files to media list
        self.media_list.lock()
        for file in playlist_order:
            media = self.instance.media_new(FILE_PATH_PREFIX + file.path)
            self.media_list.add_media(media)

        self.media_list.unlock()
        
        # Set source to SD_CARD
        self.source = AudioSource.SD_CARD
        
        return True

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
        self.command_queue.put(AudioCommand(AudioCommandType.PLAY_STATION, station))

    def play_file(self, file: AudioFile):
        """Play a file"""
        # Stop any current playback
        if self.player and VLC_AVAILABLE:
            self.player.stop()
            
        self.current_file = file
        self.current_station = None
        self.current_sd_file = None  # Clear SD card file when playing USB file
        self.source = AudioSource.USB
        
        if VLC_AVAILABLE:
            # Create a playlist starting from this file
            if self._create_playlist_from_file(file):
                self.list_player.set_media_list(self.media_list)
                self.list_player.play()
                return
                
        # Fallback to regular file playing
        self.command_queue.put(AudioCommand(AudioCommandType.PLAY_FILE, file))

    def play_sd_card_file(self, file: AudioFile):
        """Play a file from the SD card"""
        # Stop any current playback
        if self.player and VLC_AVAILABLE:
            self.player.stop()
            
        self.current_sd_file = file
        self.current_station = None
        self.current_file = None  # Clear USB file when playing SD card file
        self.source = AudioSource.SD_CARD
        
        if VLC_AVAILABLE:
            # Create a playlist starting from this file
            if self._create_sd_card_playlist_from_file(file):
                self.list_player.set_media_list(self.media_list)
                self.list_player.play()
                return
                
        # Fallback to regular file playing
        self.command_queue.put(AudioCommand(AudioCommandType.PLAY_FILE, file))

    def stop(self):
        self.command_queue.put(AudioCommand(AudioCommandType.STOP))

    def toggle_pause(self):
        self.command_queue.put(AudioCommand(AudioCommandType.TOGGLE_PAUSE))

    def mute_bluetooth(self):
        self.command_queue.put(AudioCommand(AudioCommandType.MUTE_BLUETOOTH))

    def unmute_bluetooth(self):
        self.command_queue.put(AudioCommand(AudioCommandType.UNMUTE_BLUETOOTH))

    def _mute_bluetooth(self):
        """Deaktiviert temporär die Bluetooth-Audioausgabe"""
        self._update_bluetooth_connection()
        try:
            if self.connected_bt_device:
                # Erst muten, dann pausieren
                bt_source = f"bluez_source.{self.connected_bt_device.replace(':', '_')}.a2dp_source"
                subprocess.run(['pactl', 'set-source-mute', bt_source, '1'], check=False)
                
                # Dann Pause-Signal senden
                device_path = f"/org/bluez/hci0/dev_{self.connected_bt_device.replace(':', '_')}"
                subprocess.run(['dbus-send', '--system', '--dest=org.bluez', '--print-reply', 
                              device_path, 'org.bluez.MediaControl1.Pause'], check=False)
                self.bluetooth_muted = True
        except Exception as e:
            print(f"Fehler beim Stummschalten von Bluetooth: {e}")

    def _unmute_bluetooth(self):
        """Aktiviert die Bluetooth-Audioausgabe wieder"""
        self._update_bluetooth_connection()
        try:
            if self.connected_bt_device:
                # Erst Play-Signal senden um A2DP zu aktivieren
                device_path = f"/org/bluez/hci0/dev_{self.connected_bt_device.replace(':', '_')}"
                subprocess.run(['dbus-send', '--system', '--dest=org.bluez', '--print-reply', 
                              device_path, 'org.bluez.MediaControl1.Play'], check=False)
                
                # Kurz warten bis A2DP-Source verfügbar ist
                time.sleep(0.5)
                
                # Dann unmuten
                bt_source = f"bluez_source.{self.connected_bt_device.replace(':', '_')}.a2dp_source"
                subprocess.run(['pactl', 'set-source-mute', bt_source, '0'], check=False)
                self.bluetooth_muted = False
        except Exception as e:
            print(f"Fehler beim Entstummen von Bluetooth: {e}")

    def _play_station(self, station: AudioStation):
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
        if self.player:
            self.player.stop()
        if self.list_player:
            self.list_player.stop()
            
        # Clear the media list to ensure we don't keep playing the old playlist
        if self.media_list:
            self.media_list.lock()
            while self.media_list.count() > 0:
                self.media_list.remove_index(0)
            self.media_list.unlock()

    def _toggle_pause(self):
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
        if VLC_AVAILABLE:
            if self.player:
                self.player.stop()
            
        # No need to unmount the SD card as it's handled by the system

    def navigate_to(self, audio_file: AudioFile):
        """Navigate to directory or play file"""
        if not audio_file:
            print("Warning: Attempted to navigate to None audio_file")
            return False
            
        try:
            if audio_file.is_dir and not audio_file.is_special:
                # Store the current directory before changing it
                old_dir = self.current_dir
                
                # Scan the new directory
                self.scan_directory(audio_file.path)
                
                # Update current_file to the first file in the new directory
                if len(self.files) > 0:
                    self.current_file = self.files[0]
                else:
                    # If directory is empty, keep current_file as None
                    self.current_file = None
                
                return True
            elif audio_file.is_special and audio_file.name == BACK:
                # Go to parent directory
                parent = str(Path(self.current_dir).parent)
                
                # Store the current directory before changing it
                old_dir = self.current_dir
                
                # Scan the parent directory
                self.scan_directory(parent)
                
                # Update current_file to the first file in the parent directory
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
                    # If directory is empty, keep current_file as None
                    self.current_file = None
                
                return True
            elif audio_file.is_special and audio_file.name == THIS_DIR:
                # Play all files in current directory
                self.play_file(audio_file)
                return False
            else:
                self.play_file(audio_file)
                return False
        except Exception as e:
            print(f"Error navigating to file: {e}")
            return False

    def navigate_to_sd_card(self, audio_file: AudioFile):
        """Navigate to directory or play file on SD card"""
        if not audio_file:
            print("Warning: Attempted to navigate to None audio_file")
            return False
            
        try:
            if audio_file.is_dir and not audio_file.is_special:
                # Store the current directory before changing it
                old_dir = self.sd_card_dir
                
                # Scan the new directory
                self.scan_sd_card_directory(audio_file.path)
                
                # Update current_sd_file to the first file in the new directory
                if len(self.sd_card_files) > 0:
                    self.current_sd_file = self.sd_card_files[0]
                else:
                    # If directory is empty, keep current_sd_file as None
                    self.current_sd_file = None
                
                return True
            elif audio_file.is_special and audio_file.name == BACK:
                # Go to parent directory
                parent = str(Path(self.sd_card_dir).parent)
                
                # Store the current directory before changing it
                old_dir = self.sd_card_dir
                
                # Scan the parent directory
                self.scan_sd_card_directory(parent)
                
                # Update current_sd_file to the first file in the parent directory
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
                    # If directory is empty, keep current_sd_file as None
                    self.current_sd_file = None
                
                return True
            elif audio_file.is_special and audio_file.name == THIS_DIR:
                # Play all files in current directory
                self.play_sd_card_file(audio_file)
                return False
            else:
                self.play_sd_card_file(audio_file)
                return False
        except Exception as e:
            print(f"Error navigating to SD card file: {e}")
            return False

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
        """Aktualisiert die Information über verbundene Bluetooth-Geräte"""
        try:
            result = subprocess.run(['bluetoothctl', 'info'], capture_output=True, text=True, check=False)
            self.connected_bt_device = None
            self.connected_bt_device_name = None
            for line in result.stdout.splitlines():
                if 'Device' in line:
                    self.connected_bt_device = line.split()[1]
                if 'Name' in line:
                    self.connected_bt_device_name = line.split('Name: ')[1]
                    break
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Bluetooth-Verbindung: {e}")

    def get_bluetooth_info(self, force_update=False):
        """Gibt Informationen über das verbundene Bluetooth-Gerät zurück"""
        current_time = time.time()
        
        # Nur alle 2 Sekunden aktualisieren, außer wenn force_update
        if not force_update and current_time - self.last_bt_update < 2:
            return (self.connected_bt_device_name or "Not connected", 
                   f"{self.current_bt_track or ''}\n{self.current_bt_artist or ''}" if self.current_bt_track else None)
        
        self.last_bt_update = current_time
        self._update_bluetooth_connection()
        
        if not self.connected_bt_device:
            self.current_bt_track = None
            self.current_bt_artist = None
            return "Not connected", None
            
        try:
            # Get track information
            device_path = f"/org/bluez/hci0/dev_{self.connected_bt_device.replace(':', '_')}/player0"
            result = subprocess.run(['dbus-send', '--system', '--dest=org.bluez', '--print-reply',
                                   device_path, 'org.freedesktop.DBus.Properties.Get',
                                   'string:org.bluez.MediaPlayer1', 'string:Track'],
                                   capture_output=True, text=True, check=False)
            
            # Parse the track information
            self.current_bt_track = None
            self.current_bt_artist = None
            
            lines = result.stdout.splitlines()
            for i, line in enumerate(lines):
                # Suche nach den Schlüsseln (Title, Artist)
                if "string" in line:
                    if "Title" in line:
                        # Der Wert ist in der nächsten Zeile
                        if i + 1 < len(lines) and "variant" in lines[i+1]:
                            value_line = lines[i+1]
                            if "string" in value_line:
                                parts = value_line.split('"')
                                if len(parts) >= 2:
                                    self.current_bt_track = parts[1]
                    elif "Artist" in line:
                        # Der Wert ist in der nächsten Zeile
                        if i + 1 < len(lines) and "variant" in lines[i+1]:
                            value_line = lines[i+1]
                            if "string" in value_line:
                                parts = value_line.split('"')
                                if len(parts) >= 2:
                                    self.current_bt_artist = parts[1]
            
            track_info = None
            if self.current_bt_track:
                track_info = f"{self.current_bt_track}"
                if self.current_bt_artist:
                    track_info += f"\n{self.current_bt_artist}"
            
            return self.connected_bt_device_name or "Connected", track_info
            
        except Exception as e:
            print(f"Fehler beim Abrufen der Bluetooth-Informationen: {e}")
            return self.connected_bt_device_name or "Error", None

    def _is_audio_file(self, filename):
        """Check if a file is an audio file based on its extension"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in [".mp3", ".wav", ".ogg", ".m4a", ".flac"]
