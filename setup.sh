#!/bin/bash

# Radiowecker Setup Script
# This script automates the setup process for the Radiowecker project.
# You can still follow the steps manually by reading through this script.

echo "Starting Radiowecker Setup..."

# Function to print section headers
print_section() {
    echo
    echo "====================================="
    echo "$1"
    echo "====================================="
}

# 1. Initial Setup
print_section "1. Initial Setup"

echo "Updating package lists..."
sudo apt-get update

echo "Installing required packages..."
sudo apt-get install -y git python3 python3-pip python3-venv python3-rpi.gpio python3-luma.core python3-luma.oled \
    vlc python3-vlc python3-numpy libasound2-plugins \
    pulseaudio bluetooth bluez bluez-tools bluez-alsa-utils \
    pulseaudio-module-bluetooth network-manager

# Clone repository
echo "Cloning Radiowecker repository..."
cd /home/$USER
if [ ! -d "Radiowecker" ]; then
    git clone https://github.com/Jorineg/Radiowecker.git
else
    echo "Radiowecker directory already exists, skipping clone"
fi
cd Radiowecker

# 1.1 Python environment and dependencies
print_section "1.1 Python Environment"

echo "Setting up Python virtual environment and installing requirements..."

# Create venv in project directory if not exists
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Upgrade pip and install requirements
python -m pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt not found, skipping pip install"
fi

# 2. Audio Setup
print_section "2. Audio Setup"

echo "Configuring audio hardware..."
# Backup original config
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.bak

# Add audio configuration
echo "
# Audio Configuration
dtparam=i2s=on
dtoverlay=iqaudio-dacplus
dtparam=audio=on
# I2C Configuration
dtparam=i2c_arm=on,i2c_arm_baudrate=400000" | sudo tee -a /boot/firmware/config.txt

# Configure audio modules
echo "
# Audio modules
snd_bcm2835
snd_soc_bcm2835_i2s
snd_soc_pcm5102a
snd_soc_hifiberry_dac" | sudo tee -a /etc/modules

# Add user to audio group
sudo usermod -a -G audio $USER

# 3. Bluetooth Setup
print_section "3. Bluetooth Setup"

# Configure Bluetooth
sudo tee /etc/bluetooth/main.conf > /dev/null << EOL
[General]
Class = 0x41C
Enable = Source,Sink,Media,Socket
EOL

# 4. Create System Services
print_section "4. Creating System Services"

# Install Wi-Fi importer script
echo "Installing Wi-Fi importer script..."
sudo install -m 0755 -d /usr/local/sbin
sudo install -m 0755 scripts/import-wifi.sh /usr/local/sbin/import-wifi.sh

# Function to install a service file
install_service() {
    local service_name=$1
    echo "Installing $service_name service..."
    if [ -f "services/$service_name" ]; then
        sed "s/%USER%/$USER/g; s|%HOME%|/home/$USER|g" "services/$service_name" | sudo tee "/etc/systemd/system/$service_name" > /dev/null
    else
        echo "Warning: Service file $service_name not found!"
        return 1
    fi
}

# Install all service files
install_service "bluealsa.service"
install_service "bt-agent.service"
install_service "boot-display.service"
install_service "radiowecker.service"
install_service "digiamp-init.service"
install_service "radiowecker-amp.service"
install_service "wifi-importer.service"

# 5. Enable Services
print_section "5. Enabling Services"

# Reload systemd to recognize new services
sudo systemctl daemon-reload

# Enable all required services
echo "Enabling required services..."
sudo systemctl enable boot-display
sudo systemctl enable radiowecker
sudo systemctl enable bluealsa
sudo systemctl enable bt-agent
sudo systemctl enable digiamp-init
sudo systemctl enable radiowecker-amp
sudo systemctl enable wifi-importer

# Disable unnecessary services
echo "Disabling unnecessary services..."
sudo systemctl disable keyboard-setup.service
sudo systemctl disable dphys-swapfile.service
sudo systemctl disable raspi-config.service
sudo systemctl disable avahi-daemon.service

# Install git hook for service updates
print_section "Installing Git Hooks"
echo "Setting up git hook for automatic service updates..."
if [ -d ".git/hooks" ]; then
    # Make sure git-hooks directory exists
    mkdir -p git-hooks
    
    # Install post-merge hook
    cp git-hooks/post-merge .git/hooks/
    chmod +x .git/hooks/post-merge
    echo "Git hooks installed successfully"
else
    echo "Warning: .git directory not found, skipping git hooks installation"
fi

# 6. Final Steps
print_section "6. Final Steps"

echo "Setup completed successfully!"
echo "The system needs to be rebooted to apply all changes."
echo "Would you like to reboot now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]
then
    sudo reboot
else
    echo "Please remember to reboot your system manually to apply all changes."
fi
