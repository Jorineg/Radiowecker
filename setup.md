# Radiowecker Setup Guide

## 1. Initial Setup

```bash
# Install git and clone repository
sudo apt-get update
sudo apt-get install -y git
cd ~
git clone https://github.com/Jorineg/Radiowecker.git

# Install required packages
sudo apt-get install -y python3-rpi.gpio python3-luma.core python3-luma.oled
sudo apt-get install -y vlc python3-vlc
```

## 2. Audio Setup

### Configure Audio Hardware
```bash
# Edit config.txt
sudo nano /boot/firmware/config.txt

# Add these lines:
dtparam=i2s=on
dtoverlay=iqaudio-dacplus
dtparam=audio=on

# Install audio packages
sudo apt-get install -y libasound2-plugins
```

### Configure Audio Modules
```bash
# Edit modules file
sudo nano /etc/modules

# Add these lines if not present:
snd_bcm2835
snd_soc_bcm2835_i2s
snd_soc_pcm5102a
snd_soc_hifiberry_dac

# Install PulseAudio and add user to audio group
sudo apt-get install -y pulseaudio
sudo usermod -a -G audio $USER
```

## 3. Bluetooth Setup

```bash
# Install Bluetooth packages
sudo apt-get install -y bluetooth bluez bluez-tools bluez-alsa-utils

# Configure Bluetooth
sudo tee /etc/bluetooth/main.conf > /dev/null << EOL
[General]
Class = 0x41C
Enable = Source,Sink,Media,Socket
EOL

# Create BluezALSA service
sudo tee /etc/systemd/system/bluealsa.service > /dev/null << EOL
[Unit]
Description=BluezALSA proxy
Requires=bluetooth.service
After=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/bin/bluealsa -p a2dp-sink

[Install]
WantedBy=multi-user.target
EOL

# Create Bluetooth agent service
sudo tee /etc/systemd/system/bt-agent.service > /dev/null << EOL
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
EOL
```

## 4. System Configuration

### Configure Interfaces
```bash
sudo raspi-config
# Enable I2C: Interface Options -> I2C -> Yes
# Set Audio: Advanced Options -> Audio -> PulseAudio
```

### Setup Boot Display and Auto-start

```bash
# Create boot display service
sudo tee /etc/systemd/system/boot-display.service > /dev/null << EOL
[Unit]
Description=Boot Display Service
DefaultDependencies=no
After=local-fs.target
Before=network.target bluetooth.service

[Service]
Type=oneshot
User=admin
WorkingDirectory=/home/admin/Radiowecker
ExecStart=/usr/bin/python3 /home/admin/Radiowecker/boot_display.py
RemainAfterExit=yes

[Install]
WantedBy=sysinit.target
EOL

# Create main service
sudo tee /etc/systemd/system/radiowecker.service > /dev/null << EOL
[Unit]
Description=Radiowecker Service
After=network.target pulseaudio.service bluetooth.service
Wants=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/Radiowecker
ExecStart=/usr/bin/python3 /home/admin/Radiowecker/main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL
```

## 5. Final Steps

```bash
# Enable and start all services
sudo systemctl daemon-reload
sudo systemctl enable boot-display
sudo systemctl enable radiowecker
sudo systemctl enable bluealsa
sudo systemctl enable bt-agent

# Final reboot to apply all changes
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
