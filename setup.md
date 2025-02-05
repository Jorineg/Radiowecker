# alles installieren mit -y

install git 

git clone https://github.com/Jorineg/Radiowecker.git

sudo apt-get update

sudo apt-get install python3-rpi.gpio
sudo apt-get install python3-luma.core python3-luma.oled


install vlc and python vlc (ohne pip)

-- sound --
    Config.txt bearbeiten

sudo nano /boot/config.txt (falsch! moved to /boot/firmware/config.txt)

Füge diese Zeilen hinzu:

dtparam=i2s=on
dtoverlay=hifiberry-dac
dtparam=audio=on

sudo apt-get install -y libasound2-plugins

sudo nano /etc/modules
Füge diese Zeilen hinzu (falls nicht vorhanden):
snd_bcm2835
snd_soc_bcm2835_i2s
snd_soc_pcm5102a
snd_soc_hifiberry_dac


sudo apt-get install -y pulseaudio

sudo usermod -a -G audio $USER

sudo reboot
--- end first part ---



--- second part ---

I2S aktivieren
sudo raspi-config
advanced -> audio -> set audio output to pulse audio

sudo raspi-config

Dann navigiere zu:

    "Interface Options" (oder "Interfacing Options")
    "I2C"
    Wähle "Yes" um I2C zu aktivieren


# Raspberry Pi als Bluetooth Audio Receiver einrichten

## Benötigte Pakete installieren

```bash
sudo apt-get update
sudo apt-get install -y bluetooth bluez bluez-tools bluez-alsa-utils
```

## Bluetooth-Konfiguration

1. Erstelle die Datei `/etc/bluetooth/main.conf` falls sie nicht existiert:
```bash
sudo nano /etc/bluetooth/main.conf
```

2. Füge folgende Konfiguration hinzu:
```
[General]
Class = 0x41C
Enable = Source,Sink,Media,Socket
```

## Bluez-ALSA Konfiguration

1. Erstelle die Datei `/etc/systemd/system/bluealsa.service`:
```bash
sudo nano /etc/systemd/system/bluealsa.service
```

2. Füge folgendes hinzu:
```
[Unit]
Description=BluezALSA proxy
Requires=bluetooth.service
After=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/bin/bluealsa -p a2dp-sink

[Install]
WantedBy=multi-user.target
```

5. Aktiviere und starte die Dienste:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bluealsa
sudo systemctl start bluealsa
```

## Bluetooth Agent Konfiguration

1. Erstelle die Datei `/etc/systemd/system/bt-agent.service`:
```bash
sudo nano /etc/systemd/system/bt-agent.service
```

2. Füge folgendes hinzu:
```
[Unit]
Description=Bluetooth Auth Agent
After=bluetooth.service
PartOf=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/bin/bt-agent -c NoInputNoOutput
ExecStartPost=/bin/sleep 1
ExecStartPost=/bin/hciconfig hci0 piscan
ExecStartPost=/bin/hciconfig hci0 sspmode 1
ExecStartPost=/bin/hciconfig hci0 class 0x41C
ExecStartPost=/usr/bin/bluetoothctl discoverable on
ExecStartPost=/usr/bin/bluetoothctl pairable on

[Install]
WantedBy=bluetooth.target
```

3. Aktiviere und starte den Dienst neu:
```bash
sudo systemctl daemon-reload
sudo systemctl restart bt-agent
```

## Raspberry Pi neu starten
```bash
sudo reboot
```

## Verwendung

1. Der Raspberry Pi erscheint nun auf Ihrem Smartphone als Bluetooth-Audiogerät mit dem Hostnamen des Pi
2. Verbinden Sie sich von Ihrem Smartphone aus
3. Wählen Sie den Pi als Audioausgabegerät
4. Sie können nun Musik von Ihrem Smartphone auf den Pi streamen

## Fehlerbehebung

Falls der Pi nicht erkannt wird:
```bash
# Bluetooth-Dienst neustarten
sudo systemctl restart bluetooth

# Status überprüfen
sudo systemctl status bluetooth
sudo systemctl status bluealsa
sudo systemctl status bt-agent


bluetoothctl show
```


Wenn der Pi nicht gefunden wird:
1. Prüfen Sie ob Bluetooth eingeschaltet ist: `power on`
2. Stellen Sie sicher, dass der Pi sichtbar ist: `discoverable on`
3. Aktivieren Sie das Pairing: `pairable on`
4. Setzen Sie einen freundlichen Namen: `system-alias 'RadioPi'`

## Hostname ändern

Der Hostname wird als Bluetooth-Gerätename verwendet. Um ihn zu ändern:

1. Bearbeite die Datei `/etc/hostname`:
```bash
sudo nano /etc/hostname
```
Ersetze den bestehenden Namen durch den gewünschten Namen (z.B. "RadioPi")

2. Bearbeite auch die Datei `/etc/hosts`:
```bash
sudo nano /etc/hosts
```
Ändere den alten Hostnamen in der Zeile mit "127.0.1.1" zum neuen Namen

3. Raspberry Pi neu starten:
```bash
sudo reboot
```
