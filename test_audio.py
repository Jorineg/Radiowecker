# # Test mit VLC
# import vlc
# import time

# def test_vlc():
#     try:
#         # Erstelle eine VLC Instance
#         instance = vlc.Instance('--verbose=2', "--aout=alsa")
        
#         # Erstelle einen Media Player
#         player = instance.media_player_new()
        
#         # Lade eine Audiodatei (ersetze mit deinem Pfad)
#         media = instance.media_new("ABBA - Mamma Mia.mp3")
#         player.set_media(media)

#         player.audio_set_volume(50)
        
#         # Starte Wiedergabe
#         player.play()
        
#         # Warte 10 Sekunden
#         time.sleep(100)
        
#         # Stoppe Wiedergabe
#         player.stop()
        
#     except Exception as e:
#         print(f"Fehler: {e}")
        
#     finally:
#         player.stop()
#         player.release()
#         instance.release()


# if __name__ == "__main__":
#     # Wähle einen der Tests
#     test_vlc()
#     #test_pygame()



# Test mit VLC
import vlc
import time

def test_vlc():
    try:
        # Erstelle eine VLC Instance mit folgenden Anpassungen:
        # - Verwende reines ALSA ohne Umwege über PulseAudio (falls installiert).
        # - Erhöhe das Verbose-Level für mehr Debug-Informationen.
        # - Spezifiziere das ALSA-Gerät explizit (ersetze 'hw:0,0' mit deinem tatsächlichen Gerät,
        #   finde es mit 'aplay -l').
        # - Setze das Audioformat auf 16-bit signed integer (S16_LE), um die CPU zu entlasten.
        # - Experimentiere mit manuellen Puffer- und Periodeneinstellungen (optional,
        #   entferne die #, um sie zu aktivieren).
        instance = vlc.Instance(
            '--verbose=2',
            "--aout=alsa",
            "--alsa-audio-device=hw:0,0",  # Hier dein ALSA-Gerät eintragen!
            "--audio-format=S16",
            # "--alsa-audio-buffersize=4096", # Optional: Puffergröße anpassen
            # "--alsa-audio-periods=8",      # Optional: Anzahl der Perioden anpassen
        )

        # Erstelle einen Media Player
        player = instance.media_player_new()

        # Lade eine Audiodatei (ersetze mit deinem Pfad)
        media = instance.media_new("ABBA - Mamma Mia.mp3")  # Hier deinen MP3-Dateipfad eintragen
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
    test_vlc()