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

## 6. Boot Optimization

The following steps can help reduce boot time (currently ~16s on Pi Zero 2 W):

```bash
# Disable unnecessary services
sudo systemctl disable triggerhappy.service
sudo systemctl disable keyboard-setup.service
sudo systemctl disable dphys-swapfile.service
sudo systemctl disable raspi-config.service
sudo systemctl disable avahi-daemon.service

# Optimize boot config
sudo nano /boot/firmware/config.txt

# Add these lines:
boot_delay=0
initial_turbo=60
disable_splash=1

# Optimize systemd timeouts
sudo nano /etc/systemd/system.conf

# Add or modify:
DefaultTimeoutStartSec=5s
DefaultTimeoutStopSec=5s

# Optimize time synchronization
sudo nano /etc/systemd/timesyncd.conf

# Add or modify:
[Time]
NTP=pool.ntp.org
FallbackNTP=0.pool.ntp.org 1.pool.ntp.org
PollIntervalMinSec=32
PollIntervalMaxSec=2048

# Optimize filesystem
sudo nano /etc/fstab

# Add noatime,nodiratime to root partition options:
PARTUUID=... / ext4 defaults,noatime,nodiratime 0 1
```

## 7. Usage

1. The Raspberry Pi will appear on your smartphone as a Bluetooth audio device with the hostname of the Pi
2. Connect from your smartphone
3. Select the Pi as the audio output device
4. You can now stream music from your smartphone to the Pi

## 8. Change Hostname and Bluetooth Name

The hostname is used for network identification and can be different from the Bluetooth display name:

1. Edit the hostname file (use lowercase for hostname):
```bash
sudo nano /etc/hostname
```
Replace the existing name with the desired name (e.g. "wakebox")

2. Also edit the hosts file:
```bash
sudo nano /etc/hosts
```
Change the old hostname in the line with "127.0.1.1" to the new name

3. Set a custom Bluetooth display name (can use mixed case):
```bash
# Stop bluetooth service
sudo systemctl stop bluetooth

# Change the Bluetooth name
sudo bluetoothctl << EOL
power on
system-alias 'WakeBox'
exit
EOL

# Start bluetooth service
sudo systemctl start bluetooth

# Restart the bluetooth agent
sudo systemctl restart bt-agent
```

4. Reboot the Raspberry Pi:
```bash
sudo reboot
```

After reboot, the device will be accessible via SSH using the lowercase hostname (e.g., `ssh admin@wakebox.local`) and will appear in Bluetooth device lists with the custom display name (e.g., "WakeBox").
