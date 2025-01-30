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


import vlc
import time

def test_vlc():
    try:
        # Erstelle eine VLC-Instanz mit folgenden Anpassungen:
        instance = vlc.Instance(
            '--verbose=2',
            '--aout=alsa',
            '--alsa-audio-device=hw:0,0'  # Ersetze 'hw:0,0' mit deinem ALSA-Gerät!
        )

        # Erstelle einen MediaPlayer
        player = instance.media_player_new()

        # Erstelle ein Media-Objekt und setze Optionen für 16-Bit Audio
        # WICHTIG: Hier den korrekten Pfad zu deiner MP3-Datei eintragen!
        media = instance.media_new("ABBA - Mamma Mia.mp3")
        media.add_option('audio-format=S16') # Das wird leider nicht funktionieren
        media.add_option('samplerate=48000') # aber vermutlich auch nicht nötig
        # media.add_option('sout-alsa-buffersize=4096') # optional. Besser bei instance
        # media.add_option('sout-alsa-periods=8') # s.o.
        media.add_option('sout=#transcode{acodec=s16l,channels=2,samplerate=48000}:alsa') # WICHTIG! FIX!
        media.add_option('sout-transcode-ab=128') # optional, für niedrigere bitrate, zum testen

        # Setze das Media-Objekt im Player
        player.set_media(media)

        # Setze die Lautstärke
        player.audio_set_volume(50)  # 50% Lautstärke

        # Starte die Wiedergabe
        player.play()

        # Warte 10 Sekunden
        time.sleep(10)

        # Stoppe die Wiedergabe
        player.stop()

    except Exception as e:
        print(f"Fehler: {e}")

    finally:
        # Stop und Release, auch im Fehlerfall
        try:
            player.stop()
            player.release()
        except:
            pass
        instance.release()

if __name__ == "__main__":
    test_vlc()