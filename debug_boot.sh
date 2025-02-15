#!/bin/bash

echo "1. Overall boot analysis:"
systemd-analyze
echo

echo "2. Critical chain (shows time-critical chain of units):"
systemd-analyze critical-chain
echo

echo "3. Specific info about boot-display service:"
systemd-analyze critical-chain boot-display.service
echo

echo "4. Detailed boot-display service info:"
systemctl status boot-display.service
echo

echo "5. Boot-display service dependencies:"
systemctl list-dependencies boot-display.service
echo

echo "6. Last 50 lines of boot-display service logs:"
journalctl -u boot-display.service -n 50
echo

echo "7. Service startup timing:"
systemd-analyze blame | grep boot-display
echo

echo "8. Generating detailed boot plot..."
systemd-analyze plot > ~/boot_analysis.svg
echo "Boot analysis plot saved to ~/boot_analysis.svg"
echo

echo "9. Checking if service is being delayed:"
systemd-analyze critical-chain boot-display.service --no-pager
