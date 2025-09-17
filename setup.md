# create 3 partitions


    Boot the Pi. Log in.

    Resize the root partition to the size you want (example: 12 GB for comfort; use +8G if you truly want minimum):

    Find the current start sector of partition 2:

sudo fdisk -l /dev/mmcblk0

Note the “Start” value for /dev/mmcblk0p2 (rootfs). You must reuse this exact start sector.

Recreate partition 2 with a larger end:

sudo fdisk /dev/mmcblk0

Inside fdisk:

    p (print table, confirm start of p2)
    d → 2 (delete partition 2 only; data is safe as long as you recreate with the same start)
    n → p → 2 (new primary partition 2)
        First sector: enter the exact start you noted
        Last sector: type +12G (or +8G, +10G, etc.)
    w (write)

Reboot to re-read the partition table.

Grow the filesystem to fill the new partition:

    sudo resize2fs /dev/mmcblk0p2

    Create the FAT32 “musik” partition in the remaining space:

sudo fdisk /dev/mmcblk0

    n → p → 3 (accept defaults to use the rest of the card)
    t → 3 → c (set type to W95 FAT32 (LBA))
    w

Format it:

sudo mkfs.vfat -F 32 -n MUSIK /dev/mmcblk0p3

    Mount it permanently:

sudo mkdir -p /mnt/musik
sudo blkid /dev/mmcblk0p3

Copy the UUID. Edit /etc/fstab and add:

UUID=<the-uuid>  /mnt/musik  vfat  defaults,uid=1000,gid=1000,umask=0022  0  0

Then:

sudo mount -a