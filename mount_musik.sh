#!/bin/bash
# Simple script to mount the Musik partition

# Create mount point if it doesn't exist
if [ ! -d "/mnt/musik" ]; then
    sudo mkdir -p /mnt/musik
fi

# Check if already mounted
if ! mountpoint -q /mnt/musik; then
    # Mount the partition (hardcoded to mmcblk0p3 with label Musik)
    sudo mount -t vfat -o uid=1000,gid=1000,umask=000 /dev/mmcblk0p3 /mnt/musik
    echo "Mounted Musik partition to /mnt/musik"
else
    echo "Musik partition already mounted"
fi
