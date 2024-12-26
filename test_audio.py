# Test mit VLC
import vlc
import time

def test_vlc():
    try:
        # Erstelle eine VLC Instance
        instance = vlc.Instance()
        
        # Erstelle einen Media Player
        player = instance.media_player_new()
        
        # Lade eine Audiodatei (ersetze mit deinem Pfad)
        media = instance.media_new("/path/to/your/audiofile.mp3")
        player.set_media(media)
        
        # Starte Wiedergabe
        player.play()
        
        # Warte 10 Sekunden
        time.sleep(10)
        
        # Stoppe Wiedergabe
        player.stop()
        
    except Exception as e:
        print(f"Fehler: {e}")

# Alternative mit pygame (einfacher zu installieren)
def test_pygame():
    try:
        import pygame
        
        pygame.mixer.init()
        pygame.mixer.music.load("a.mp3")
        pygame.mixer.music.play()
        
        # Warte 10 Sekunden
        time.sleep(10)
        
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    # Wähle einen der Tests
    test_vlc()
    #test_pygame()
