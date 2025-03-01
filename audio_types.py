# audio_types.py - Basic data structures and constants for the audio system

from enum import Enum, auto
from dataclasses import dataclass
import os
from typing import Any

# Constants
BACK = "<zurück>"
THIS_DIR = "<dieser Ordner>"
FILE_PATH_PREFIX = ""
SUPPORTED_AUDIO_EXTENSIONS = [".mp3", ".wav", ".ogg", ".m4a", ".flac"]

class AudioSource(Enum):
    USB = auto()
    SD_CARD = auto()
    RADIO = auto()


class AudioFile:
    def __init__(self, path: str, is_dir: bool = False, name: str = None, is_special: bool = False):
        self.path = path
        self.is_dir = is_dir
        self.is_special = is_special
        self.name = name if name else os.path.basename(path)


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
    data: Any = None
