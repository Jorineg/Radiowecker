#!/bin/bash

echo "1. Overall boot analysis:"
systemd-analyze

echo -e "\n2. Critical chain (shows time-critical chain of units):"
systemd-analyze critical-chain

echo -e "\n3. Specific info about boot-display service:"
systemd-analyze plot | grep boot-display

echo -e "\n4. Detailed boot-display service info:"
systemctl status boot-display

echo -e "\n5. Boot-display service dependencies:"
systemctl list-dependencies boot-display

echo -e "\n6. Last 50 lines of boot-display service logs:"
journalctl -u boot-display -n 50
