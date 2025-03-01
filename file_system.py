# file_system.py - File system operations related to audio files

import os
from pathlib import Path
from typing import List
import random
from audio_types import AudioFile, SUPPORTED_AUDIO_EXTENSIONS, BACK, THIS_DIR


def is_audio_file(filename: str) -> bool:
    """Check if a file is an audio file based on its extension"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in SUPPORTED_AUDIO_EXTENSIONS


def scan_directory(directory: str, is_sd_card: bool = False, 
                   root_path: str = "/") -> List[AudioFile]:
    """Scan a directory for audio files and subdirectories"""
    result = []
    current_storage_name = "SD card" if is_sd_card else "USB"
    
    # Check if directory exists
    if not os.path.exists(directory):
        print(f"{current_storage_name} directory does not exist: {directory}")
        result.append(AudioFile(name=f"{current_storage_name} not mounted", path=directory, is_special=True))
        return result
        
    try:
        entries = os.listdir(directory)
    except PermissionError:
        print(f"Permission denied: {directory}")
        result.append(AudioFile(name="Permission denied", path=directory, is_special=True))
        return result
    except Exception as e:
        print(f"Error listing {current_storage_name} directory {directory}: {e}")
        result.append(AudioFile(name=f"Error: {str(e)}", path=directory, is_special=True))
        return result

    # Add "this directory" option - always include it regardless of content
    # It will recursively scan for audio files when selected
    result.append(AudioFile(name=THIS_DIR, path=directory, is_special=True))

    # Add back option if not in root directory
    if directory != root_path:
        result.append(AudioFile(name=BACK, path=directory, is_special=True))

    # Add directories
    for entry in sorted(entries):
        path = os.path.join(directory, entry)
        if os.path.isdir(path) and not entry.startswith('.'):
            result.append(AudioFile(name=entry, path=path, is_dir=True))

    # Add audio files
    for entry in sorted(entries):
        path = os.path.join(directory, entry)
        if os.path.isfile(path) and is_audio_file(entry):
            result.append(AudioFile(name=entry, path=path))
                                 
    # If no files or directories were found (empty directory)
    if len(result) == 0:
        result.append(AudioFile(name="Empty directory", path=directory, is_special=True))
        
    return result


def find_audio_files_recursively(directory: str, max_files=100) -> List[AudioFile]:
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
                if is_audio_file(file):
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
