#!/usr/bin/env python3
import vlc
import time
import signal
import sys
import subprocess

def signal_handler(sig, frame):
    print('\nStopping playback...')
    if 'player' in globals():
        player.stop()
        player.release()
    if 'instance' in globals():
        instance.release()
    sys.exit(0)

def test_radio():
    global player, instance
    try:
        # Initialize ALSA
        subprocess.run(['alsactl', 'init'], check=False)
        
        # Create VLC instance with ALSA audio output
        instance = vlc.Instance('--verbose=2',
                              '--aout=pulse',
                              # '--alsa-audio-device=hw:0'
                              )
        
        # Create media player
        player = instance.media_player_new()
        
        # Radio stream URL
        url = "http://f111.rndfnk.com/ard/rbb/rbb888/live/mp3/128/stream.mp3?cid=01FCTB5577PTDND5C4WBNVMQ9E&sid=2qVemp3Xe1Z7MPq2Wxxjtm6Y5rQ&token=bLHTWEDkmkyKE-o0ROeXgvhaaAHPbH-IhB6CgmNa0b8&tvf=v5se87InExhmMTExLnJuZGZuay5jb20"
        
        # Create media from URL
        media = instance.media_new(url)
        player.set_media(media)
        
        # Start playback
        print("Starting radio playback...")
        player.play()
        
        # Keep the script running
        print("Press Ctrl+C to stop playback")
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        if 'player' in globals():
            player.stop()
            player.release()
        if 'instance' in globals():
            instance.release()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    test_radio()