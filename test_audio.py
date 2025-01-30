# Test mit VLC
import vlc
import time

def test_vlc():
    try:
        # Erstelle eine VLC Instance
        instance = vlc.Instance('--verbose=2', "--aout=alsa")
        
        # Erstelle einen Media Player
        player = instance.media_player_new()
        
        # Lade eine Audiodatei (ersetze mit deinem Pfad)
        media = instance.media_new("ABBA - Mamma Mia.mp3")
        player.set_media(media)

        player.audio_set_volume(50)
        
        # Starte Wiedergabe
        player.play()
        
        # Warte 10 Sekunden
        time.sleep(100)
        
        # Stoppe Wiedergabe
        player.stop()
        
    except Exception as e:
        print(f"Fehler: {e}")
        
    finally:
        player.stop()
        player.release()
        instance.release()


if __name__ == "__main__":
    # Wähle einen der Tests
    test_vlc()
    #test_pygame()