/*
Minimal SD + FAT chain-loader for a known MBR layout with a
first FAT32 (0x0C) partition named "bootfs (E:)".

WHAT’S NEW IN THIS VERSION:
- We parse the MBR to locate the partition with type 0x0C (FAT32 LBA).
- Then we do the same minimal FAT32 reading logic as before.
- So this should work with your posted partition table:
Partition #0 (bootfs) => type 0x0C, 512MB
Partition #1 (rootfs) => type 0x83, 8GB (EXT4)
Partition #2 (Musik)  => type 0x0C, 51GB (FAT32)
We will pick the first 0x0C partition in the MBR, i.e. "bootfs".

CAUTION: This code is untested, purely an educational demonstration.

USAGE:
1) Place "KERNEL7L.IMG" (or "kernel7l.img") in the root of bootfs (E:).
2) Build this code along with your splash code, link it to run at
e.g. 0x4000, so as not to conflict with the standard Linux kernel
at 0x8000.
3) In config.txt set "kernel=my_splash.img" (the output binary).
4) Once your code runs and shows a splash, call chainload_linux().
*/

#include <stdint.h>
#include <stddef.h> // for size_t
#include <string.h> // for memcmp
#include "kernel_loader.h"

// --------------------------------------------------------------------
// 1. Basic MMIO access, Pi Zero 2 uses BCM2710 with base = 0x3F000000
// --------------------------------------------------------------------
#define MMIO_BASE       0x3F000000    // Pi Zero 2 W (BCM2710)


// Mailbox
#define MBOX_BASE       (MMIO_BASE + 0xB880)
#define MBOX_READ       (MBOX_BASE + 0x00)
#define MBOX_STATUS     (MBOX_BASE + 0x18)
#define MBOX_WRITE      (MBOX_BASE + 0x20)

#define MBOX_RESPONSE   0x80000000
#define MBOX_FULL       0x80000000
#define MBOX_EMPTY      0x40000000

#define MBOX_CH_PROP    8
#define MBOX_REQUEST    0x00000000
#define MBOX_TAG_LAST   0x00000000

// Power management
#define PM_RSTC (MMIO_BASE + 0x0010001c)
#define PM_WDOG (MMIO_BASE + 0x00100024)
#define PM_PASSWORD 0x5a000000
#define PM_RSTC_WRCFG_FULL_RESET 0x00000020

// EMMC registers for SD0 (primary controller)
#define EMMC_BASE (MMIO_BASE + 0x300000)

static inline void mmio_write(uint32_t reg, uint32_t val)
{
    *(volatile uint32_t *)reg = val;
}

static inline uint32_t mmio_read(uint32_t reg)
{
    return *(volatile uint32_t *)reg;
}

// Simple busy-wait
static void delay_cycles(unsigned count)
{
    for (volatile unsigned i = 0; i < count; i++)
    {
    }
}
static void wait_msec(unsigned msec)
{
    // Tweak as needed for your CPU speed
    delay_cycles(msec * 2138);
}

// GPIO register definitions for debugging LED
#define KL_GPIO_BASE (MMIO_BASE + 0x200000)
#define KL_GPFSEL_OFFSET 0x00
#define KL_GPSET_OFFSET 0x1C
#define KL_GPCLR_OFFSET 0x28
#define KL_DEBUG_PIN 22

// GPIO register definitions
#define GPFSEL3 (KL_GPIO_BASE + 0x0C)   // GPIO Function Select 3
#define GPFSEL4 (KL_GPIO_BASE + 0x10)   // GPIO Function Select 4
#define GPFSEL5 (KL_GPIO_BASE + 0x14)   // GPIO Function Select 5
#define GPPUD (KL_GPIO_BASE + 0x94)     // GPIO Pull-up/down
#define GPPUDCLK1 (KL_GPIO_BASE + 0x9C) // GPIO Pull-up/down Clock 1

// Power tags
#define TAG_SET_POWER          0x00028001
#define TAG_SET_CLK_RATE       0x00038002
#define DEV_ID_SD              0  // Power domain ID for eMMC/SD
#define CLK_ID_EMMC            1  // Clock ID for eMMC/SD

// Debug LED functions using GPIO22
static void debug_led_init(void)
{
    uint32_t reg = mmio_read(KL_GPIO_BASE + KL_GPFSEL_OFFSET + (KL_DEBUG_PIN / 10) * 4);
    reg &= ~(7 << ((KL_DEBUG_PIN % 10) * 3)); // Clear bits
    reg |= 1 << ((KL_DEBUG_PIN % 10) * 3);    // Set as output
    mmio_write(KL_GPIO_BASE + KL_GPFSEL_OFFSET + (KL_DEBUG_PIN / 10) * 4, reg);
}

static void debug_led_on(void)
{
    mmio_write(KL_GPIO_BASE + KL_GPCLR_OFFSET, 1 << KL_DEBUG_PIN);
}

static void debug_led_off(void)
{
    mmio_write(KL_GPIO_BASE + KL_GPSET_OFFSET, 1 << KL_DEBUG_PIN);
}

static void debug_led_blink(int count)
{
    for (int i = 0; i < count; i++)
    {
        debug_led_on();
        wait_msec(700);
        debug_led_off();
        wait_msec(700);
    }
}

static void debug_led_blink_fast(int count)
{
    for (int i = 0; i < count; i++)
    {
        debug_led_on();
        wait_msec(200);
        debug_led_off();
        wait_msec(200);
    }
}

static void debug_led_success(void)
{
    // Long-short-long pattern
    debug_led_on();
    wait_msec(1000);
    debug_led_off();
    wait_msec(300);

    debug_led_on();
    wait_msec(300);
    debug_led_off();
    wait_msec(300);

    debug_led_on();
    wait_msec(1000);
    debug_led_off();
}

// Mailbox communication
static void mbox_write(uint32_t channel, volatile uint32_t *data)
{
    uint32_t value = ((uint32_t)(uintptr_t)data & ~0xF) | (channel & 0xF);

    // Wait until mailbox is not full
    while (mmio_read(MBOX_STATUS) & MBOX_FULL)
    {
    }

    // Write value
    mmio_write(MBOX_WRITE, value);
}

static uint32_t mbox_read(uint32_t channel)
{
    uint32_t value;

    // Wait until mailbox has data
    while (1)
    {
        while (mmio_read(MBOX_STATUS) & MBOX_EMPTY)
        {
        }

        value = mmio_read(MBOX_READ);
        if ((value & 0xF) == channel)
            break;
    }

    return value & ~0xF;
}

int power_on_sd(void)
{
    // 16 words for mailbox
    static volatile uint32_t __attribute__((aligned(16))) mbox[16];
    for (int i = 0; i < 16; i++)
        mbox[i] = 0;

    mbox[0] = 15 * 4;       // buffer size in bytes
    mbox[1] = MBOX_REQUEST; // request

    // set power state
    mbox[2] = TAG_SET_POWER;
    mbox[3] = 8;         // buffer size
    mbox[4] = 8;         // req/resp size
    mbox[5] = DEV_ID_SD; // 0 for SD
    // bit0=1=power on, bit1=1=wait for stable
    mbox[6] = 3;

    // set clock rate
    mbox[7] = TAG_SET_CLK_RATE;
    mbox[8] = 12;
    mbox[9] = 8;
    mbox[10] = CLK_ID_EMMC; // 1
    mbox[11] = 400000;      // 400 kHz
    mbox[12] = 0;           // skip turbo=0

    // end tag
    mbox[13] = MBOX_TAG_LAST;

    mbox_write(MBOX_CH_PROP, mbox);
    (void)mbox_read(MBOX_CH_PROP);

    if ((mbox[1] & MBOX_RESPONSE) == 0)
    {
        // Overall mailbox call failed
        return -1;
    }
    // Check if the domain actually powered up
    if ((mbox[6] & 1) == 0)
    {
        // bit0 not set => not powered
        return -2;
    }
    return 0;
}

void sd_gpio_init(void)
{
    uint32_t sel4 = mmio_read(GPFSEL4);
    uint32_t sel5 = mmio_read(GPFSEL5);

    // Clear bits for GPIO48..53
    sel4 &= ~((7 << 24) | (7 << 27));
    sel5 &= ~((7 << 0) | (7 << 3) | (7 << 6) | (7 << 9));

    // ALT3 for GPIO48..53
    sel4 |= (7 << 24) | (7 << 27);
    sel5 |= (7 << 0) | (7 << 3) | (7 << 6) | (7 << 9);

    mmio_write(GPFSEL4, sel4);
    mmio_write(GPFSEL5, sel5);

    // Pull-ups
    mmio_write(GPPUD, 2); // 2=enable pull-up
    wait_msec(1);
    mmio_write(GPPUDCLK1, 0x3F << 16); // bits for 48..53
    wait_msec(1);
    mmio_write(GPPUDCLK1, 0);
}

// --------------------------------------------------------------------
// 2. EMMC (SD) controller register definitions (simplistic version)
// --------------------------------------------------------------------
#define EMMC_ARG2 (EMMC_BASE + 0x00)
#define EMMC_BLKSIZECNT (EMMC_BASE + 0x04)
#define EMMC_ARG1 (EMMC_BASE + 0x08)
#define EMMC_CMDTM (EMMC_BASE + 0x0C)
#define EMMC_RESP0 (EMMC_BASE + 0x10)
#define EMMC_RESP1 (EMMC_BASE + 0x14)
#define EMMC_RESP2 (EMMC_BASE + 0x18)
#define EMMC_RESP3 (EMMC_BASE + 0x1C)
#define EMMC_DATA (EMMC_BASE + 0x20)
#define EMMC_STATUS (EMMC_BASE + 0x24)
#define EMMC_CONTROL0 (EMMC_BASE + 0x28)
#define EMMC_CONTROL1 (EMMC_BASE + 0x2C)
#define EMMC_INTERRUPT (EMMC_BASE + 0x30)
#define EMMC_IRPT_MASK (EMMC_BASE + 0x34)
#define EMMC_IRPT_EN (EMMC_BASE + 0x38)
#define EMMC_CONTROL2 (EMMC_BASE + 0x3C)

// Simple CMDTM flags
#define CMD_RSPNS_48 (2 << 16)
#define CMD_NEED_APP (1 << 15)

// Some commands
#define GO_IDLE_STATE 0
#define SEND_IF_COND 8
#define APP_CMD 55
#define SD_SEND_OP_COND 41
#define SET_BLOCKLEN 16
#define READ_SINGLE_BLOCK 17

// --------------------------------------------------------------------
// 3. Minimal global state
// --------------------------------------------------------------------
static uint32_t is_sdhc = 0;
static uint32_t fat_start_lba;
static uint32_t sectors_per_cluster;
static bpb_t bpb;

// --------------------------------------------------------------------
// 4. Send command (bare)
static int sd_send_command(uint32_t cmd_idx, uint32_t arg, uint32_t resp48)
{
    // Clear interrupt
    mmio_write(EMMC_INTERRUPT, 0xffffffff);

    // Write arg
    mmio_write(EMMC_ARG1, arg);

    // command + response
    uint32_t cmd_val = cmd_idx & 0x3F;
    if (resp48)
    {
        cmd_val |= CMD_RSPNS_48;
    }
    mmio_write(EMMC_CMDTM, cmd_val);

    // Wait for CMD_DONE
    while (!(mmio_read(EMMC_INTERRUPT) & 0x1))
    {
        // spin
    }
    mmio_write(EMMC_INTERRUPT, 0x1); // clear

    return 0; // ignoring errors
}

// --------------------------------------------------------------------
// 5. Initialize SD card
int sd_init(void)
{
    // Power on the SD controller
    if (power_on_sd() != 0)
    {
        debug_led_blink_fast(1); // Power-on failed
        return -1;
    }

    // Configure GPIO pins for SD0 (internal SD slot)
    sd_gpio_init();

    debug_led_blink(4); // Starting EMMC init

    // Full reset of EMMC controller
    mmio_write(EMMC_CONTROL1, 1 << 24);     // Reset host
    mmio_write(EMMC_CONTROL2, 0);           // Clear control2
    mmio_write(EMMC_INTERRUPT, 0xFFFFFFFF); // Clear all interrupts
    mmio_write(EMMC_IRPT_EN, 0);            // Disable all interrupts
    mmio_write(EMMC_IRPT_MASK, 0xFFFFFFFF); // Mask all interrupts
    wait_msec(10);                          // Let it reset

    // Wait for reset completion
    while (mmio_read(EMMC_CONTROL1) & (1 << 24))
    {
    }
    debug_led_blink(5); // Reset complete

    // Set initial clock state
    uint32_t c1 = mmio_read(EMMC_CONTROL1);
    c1 &= ~0xFF00;     // Clear clock divider bits (only bits 15:8)
    c1 |= (0x80 << 8); // Set divider to 128 (slow but safe)
    c1 |= (1 << 2);    // Internal clock enable
    mmio_write(EMMC_CONTROL1, c1);

    // Wait for clock stable with timeout
    int timeout = 100; // 100ms timeout
    while (!(mmio_read(EMMC_CONTROL1) & (1 << 1)))
    {
        if (--timeout <= 0)
        {
            debug_led_blink_fast(5); // Error - Clock failed to stabilize
            return -1;
        }
        wait_msec(1);
    }
    debug_led_blink(6); // Clock stable

    // Enable SD clock output
    c1 |= (1 << 5); // SD clock enable
    mmio_write(EMMC_CONTROL1, c1);
    wait_msec(10);      // Let clock stabilize
    debug_led_blink(7); // Clock enabled

    // GO_IDLE_STATE
    sd_send_command(GO_IDLE_STATE, 0, 0);
    debug_led_blink(8); // GO_IDLE_STATE sent

    // SEND_IF_COND (voltage check)
    sd_send_command(SEND_IF_COND, 0x1AA, 1);
    uint32_t r = mmio_read(EMMC_RESP0);
    if ((r & 0xFF) != 0xAA)
    {
        return -1;
    }
    debug_led_blink(9); // Voltage check passed

    // ACMD41 loop
    int acmd41_attempts = 0;
    while (1)
    {
        if (acmd41_attempts++ > 1000)
        {
            return -1;
        }

        // APP_CMD
        sd_send_command(APP_CMD, 0, 1);
        // SD_SEND_OP_COND
        sd_send_command(SD_SEND_OP_COND, 0x40000000, 1);
        r = mmio_read(EMMC_RESP0);
        if (r & 0x80000000)
        {
            // Ready
            break;
        }
        wait_msec(1); // Add small delay between attempts
    }
    debug_led_blink(10); // ACMD41 complete

    // Check SDHC
    if (r & 0x40000000)
    {
        is_sdhc = 1;
    }

    // CMD16: set block length = 512
    sd_send_command(SET_BLOCKLEN, 512, 1);
    debug_led_blink(11); // Init complete

    return 0;
}

// --------------------------------------------------------------------
// 6. Read a single 512-byte block from the card
static int sd_read_block(uint32_t lba, void *buf)
{
    mmio_write(EMMC_INTERRUPT, 0xffffffff);
    // 1 block == 512 bytes
    mmio_write(EMMC_BLKSIZECNT, (1 << 16) | 512);

    // READ_SINGLE_BLOCK
    sd_send_command(READ_SINGLE_BLOCK, lba, 1);

    // Wait for READ_RDY
    while (!(mmio_read(EMMC_INTERRUPT) & 0x20))
    {
        // spin
    }
    // Read 512 bytes
    volatile uint32_t *dst = (volatile uint32_t *)buf;
    for (int i = 0; i < 128; i++)
    {
        dst[i] = mmio_read(EMMC_DATA);
    }

    mmio_write(EMMC_INTERRUPT, 0xffff0001);

    return 0;
}

// --------------------------------------------------------------------
// 7. Minimal MBR structures
// --------------------------------------------------------------------
#pragma pack(push, 1)
typedef struct
{
    uint8_t status;
    uint8_t first_chs[3];
    uint8_t type;
    uint8_t last_chs[3];
    uint32_t lba;
    uint32_t sectors;
} mbr_part_t;

typedef struct
{
    uint8_t code[446];
    mbr_part_t part[4];
    uint16_t sig;
} mbr_t;
#pragma pack(pop)

// --------------------------------------------------------------------
// 8. Bare function to find the partition with type=0x0C
//    Return start_lba in *out_lba.
//    We do not check if signature=0xAA55. This is minimal code.
// --------------------------------------------------------------------
static int find_fat32_partition(void)
{
    // Read sector 0 (the MBR)
    static mbr_t mbr;
    sd_read_block(0, &mbr);

    // Look at the 4 entries
    for (int i = 0; i < 4; i++)
    {
        if (mbr.part[i].type == 0x0C)
        {
            // Found a FAT32 (LBA) partition
            return mbr.part[i].lba;
        }
    }
    // Not found
    return -1;
}

// --------------------------------------------------------------------
// 9. Global to store FAT info
// --------------------------------------------------------------------
static uint32_t cluster_to_lba(uint32_t cluster)
{
    return fat_start_lba + (cluster - 2) * sectors_per_cluster;
}

// --------------------------------------------------------------------
// 10. FAT init, given the partition start LBA
// --------------------------------------------------------------------
static int fat_init(uint32_t part_lba)
{
    // Read the FAT32 boot sector
    sd_read_block(part_lba, &bpb);

    if (bpb.bytes_per_sec != 512)
    {
        return -1;
    }
    sectors_per_cluster = bpb.secs_per_cluster;
    uint32_t reserved_sectors = bpb.rsvd_sec_cnt;
    uint32_t fat_size = (bpb.fat_sz16 != 0) ? bpb.fat_sz16 : bpb.fat_sz32;
    uint32_t total_fats = bpb.num_fats;

    // The first data sector:
    fat_start_lba = part_lba + reserved_sectors + (total_fats * fat_size);
    return 0;
}

// --------------------------------------------------------------------
// 11. Find "KERNEL7L.IMG" in the root directory (FAT32: root = cluster 2).
//     We skip actually reading the FAT chain. We assume the root directory
//     fits in cluster 2 alone, or we read a few subsequent clusters contiguously.
//     The short name must be "KERNEL7LIMG". (8 chars + "IMG".)
// --------------------------------------------------------------------
static int my_memcmp(const void *a, const void *b, size_t n)
{
    const uint8_t *p1 = (const uint8_t *)a;
    const uint8_t *p2 = (const uint8_t *)b;
    for (size_t i = 0; i < n; i++)
    {
        if (p1[i] != p2[i])
        {
            return (p1[i] < p2[i]) ? -1 : 1;
        }
    }
    return 0;
}

static int fat_find_file(uint32_t *start_cluster, uint32_t *file_size)
{
    // For minimal code, we assume the root directory is cluster=2,
    // and we read a limited number of clusters contiguously.
    // "KERNEL7LIMG" is the short name of "KERNEL7L.IMG".
    const char target_name[11] = "KERNEL7LIMG";

    uint8_t sector_buf[512];
    // Check up to 8 clusters (which might be up to 4KB if cluster=8 sectors).
    for (int cluster_offset = 0; cluster_offset < 8; cluster_offset++)
    {
        for (int s = 0; s < sectors_per_cluster; s++)
        {
            uint32_t sector_num = fat_start_lba + ((2 - 2 + cluster_offset) * sectors_per_cluster) + s;
            sd_read_block(sector_num, sector_buf);

            fat32_dirent_t *dir = (fat32_dirent_t *)sector_buf;
            for (int i = 0; i < (512 / sizeof(fat32_dirent_t)); i++)
            {
                if (dir[i].name[0] == 0x00)
                {
                    // end of directory
                    return -1;
                }
                if (dir[i].name[0] == 0xE5)
                {
                    // deleted
                    continue;
                }
                // Compare
                if (my_memcmp(dir[i].name, target_name, 11) == 0)
                {
                    *start_cluster = (dir[i].cluster_hi << 16) | dir[i].cluster_lo;
                    *file_size = dir[i].size;
                    return 0;
                }
            }
        }
    }
    return -1;
}

// --------------------------------------------------------------------
// 12. Load the file contiguously from start_cluster => 0x8000
// --------------------------------------------------------------------
static int fat_load_file(uint32_t start_cluster, uint32_t file_size, void *load_addr)
{
    uint8_t *dst = (uint8_t *)load_addr;

    // read contiguous clusters into dst
    uint32_t current_cluster = start_cluster;
    uint32_t bytes_remaining = file_size;
    uint32_t cluster_size = bpb.secs_per_cluster * 512;

    while (bytes_remaining > 0)
    {
        uint32_t lba = cluster_to_lba(current_cluster);
        uint32_t sectors_to_read = (bytes_remaining > cluster_size) ? bpb.secs_per_cluster : ((bytes_remaining + 511) / 512);

        for (uint32_t i = 0; i < sectors_to_read; i++)
        {
            if (sd_read_block(lba + i, dst + (i * 512)) != 0)
            {
                return -1;
            }
        }

        if (bytes_remaining <= cluster_size)
            break;

        bytes_remaining -= cluster_size;
        dst += cluster_size;

        // Get next cluster from FAT
        uint32_t fat_offset = current_cluster * 4;
        uint32_t fat_sector = fat_start_lba + (fat_offset / 512);
        uint32_t fat_index = (fat_offset % 512) / 4;

        uint32_t fat_buffer[128];
        if (sd_read_block(fat_sector, fat_buffer) != 0)
            return -1;

        current_cluster = fat_buffer[fat_index] & 0x0FFFFFFF;
        if (current_cluster >= 0x0FFFFFF8)
            break;
    }

    return 0;
}

// --------------------------------------------------------------------
// 13. Public function to chain-load kernel7l.img from your “bootfs (E:)”
// --------------------------------------------------------------------
void chainload_linux(void)
{
    uint32_t start_cluster, file_size;

    debug_led_init(); // Initialize debug LED
    debug_led_off();  // Turn on LED to show we're starting

    wait_msec(1000);
    debug_led_blink_fast(2);

    // Initialize SD card
    if (sd_init() < 0)
    {
        debug_led_blink(3); // 3 blinks = SD init error
        return;
    }

    wait_msec(1000);
    debug_led_blink_fast(2);

    // Find FAT32 partition
    int fat32_lba = find_fat32_partition();
    if (fat32_lba < 0)
    {
        debug_led_blink(4); // 4 blinks = partition error
        return;
    }

    wait_msec(1000);
    debug_led_blink_fast(2);

    // Initialize FAT
    if (fat_init(fat32_lba) < 0)
    {
        debug_led_blink(5); // 5 blinks = FAT init error
        return;
    }

    wait_msec(1000);
    debug_led_blink_fast(2);

    // Find kernel file
    if (fat_find_file(&start_cluster, &file_size) < 0)
    {
        debug_led_blink(6); // 6 blinks = file not found
        return;
    }

    wait_msec(1000);
    debug_led_blink_fast(2);

    // Load the file
    if (fat_load_file(start_cluster, file_size, (void *)0x8000) < 0)
    {
        debug_led_blink(7); // 7 blinks = file load error
        return;
    }

    debug_led_success(); // Show success pattern
    wait_msec(500);      // Wait a bit before jumping to kernel

    // Jump to the loaded kernel
    ((void (*)(void))0x8000)();
}

// --------------------------------------------------------------------
// Demo main() if used standalone
// int main(void)
// {
//     chainload_linux();
//     while (1)
//     {
//     }
//     return 0;
// }



// Based on your error where the SD card initialization is failing at the clock stabilization stage, let's fix the sd_init() function. The issue is likely in the clock configuration and stability check.

// Here's a replacement for your sd_init() function with improved initialization sequence and better error handling:

// int sd_init(void)
// {
//     // Power on the SD controller
//     if (power_on_sd() != 0)
//     {
//         debug_led_blink_fast(1); // Power-on failed
//         return -1;
//     }

//     // Configure GPIO pins for SD0 (internal SD slot)
//     sd_gpio_init();

//     debug_led_blink(4); // Starting EMMC init

//     // Full reset of EMMC controller
//     mmio_write(EMMC_CONTROL0, 0);           // Reset control0
//     mmio_write(EMMC_CONTROL1, 0x0000000F);  // Reset host circuit, data lines, command line
//     wait_msec(10);                          // Let it reset
    
//     // Clear reset bits
//     mmio_write(EMMC_CONTROL1, 0);
//     wait_msec(10);                          // Wait for reset to complete
    
//     // Reset again with just the host bit
//     mmio_write(EMMC_CONTROL1, 1 << 24);     // Reset host
//     wait_msec(10);                          // Let it reset

//     // Wait for reset completion with timeout
//     int timeout = 100; // 100ms timeout
//     while (mmio_read(EMMC_CONTROL1) & (1 << 24))
//     {
//         if (--timeout <= 0)
//         {
//             debug_led_blink_fast(2); // Error - Reset failed
//             return -1;
//         }
//         wait_msec(1);
//     }
    
//     // Clear and enable interrupts
//     mmio_write(EMMC_CONTROL2, 0);           // Clear control2
//     mmio_write(EMMC_INTERRUPT, 0xFFFFFFFF); // Clear all interrupts
//     mmio_write(EMMC_IRPT_MASK, 0xFFFFFFFF); // Mask all interrupts
//     mmio_write(EMMC_IRPT_EN, 0x00FF00F7);   // Enable interrupts we care about
    
//     debug_led_blink(5); // Reset complete

//     // Set initial clock state - use a very conservative divider for stability
//     uint32_t c1 = mmio_read(EMMC_CONTROL1);
//     c1 &= ~(0xFFFF << 8);  // Clear clock divider bits
//     c1 |= (0xF0 << 8);     // Set divider to 240 (very slow but stable)
//     c1 |= (1 << 2);        // Internal clock enable
//     mmio_write(EMMC_CONTROL1, c1);

//     // Wait for clock stable with timeout - longer timeout for stability
//     timeout = 1000; // 1000ms timeout
//     while (!(mmio_read(EMMC_CONTROL1) & (1 << 1)))
//     {
//         if (--timeout <= 0)
//         {
//             debug_led_blink_fast(5); // Error - Clock failed to stabilize
//             return -1;
//         }
//         wait_msec(1);
//     }
//     debug_led_blink(6); // Clock stable

//     // Enable SD clock output
//     c1 = mmio_read(EMMC_CONTROL1);
//     c1 |= (1 << 5); // SD clock enable
//     mmio_write(EMMC_CONTROL1, c1);
//     wait_msec(20);      // Let clock stabilize
//     debug_led_blink(7); // Clock enabled

//     // Set data timeout
//     uint32_t c2 = mmio_read(EMMC_CONTROL2);
//     c2 &= ~(0xF << 16);  // Clear timeout bits
//     c2 |= (0xE << 16);   // Set timeout to maximum value
//     mmio_write(EMMC_CONTROL2, c2);
//     wait_msec(10);

//     // GO_IDLE_STATE - reset card to idle state
//     sd_send_command(GO_IDLE_STATE, 0, 0);
//     wait_msec(100);      // Give card time to reset
//     debug_led_blink(8); // GO_IDLE_STATE sent

//     // SEND_IF_COND (voltage check)
//     sd_send_command(SEND_IF_COND, 0x1AA, 1);
//     uint32_t r = mmio_read(EMMC_RESP0);
//     if ((r & 0xFF) != 0xAA)
//     {
//         debug_led_blink_fast(3); // Voltage check failed
//         return -1;
//     }
//     debug_led_blink(9); // Voltage check passed

//     // ACMD41 loop - initialize the card
//     int acmd41_attempts = 0;
//     while (1)
//     {
//         if (acmd41_attempts++ > 1000)
//         {
//             debug_led_blink_fast(4); // ACMD41 failed
//             return -1;
//         }

//         // APP_CMD
//         sd_send_command(APP_CMD, 0, 1);
//         // SD_SEND_OP_COND - request HCS (SDHC support)
//         sd_send_command(SD_SEND_OP_COND, 0x40FF8000, 1);
//         r = mmio_read(EMMC_RESP0);
//         if (r & 0x80000000)
//         {
//             // Card is ready
//             break;
//         }
//         wait_msec(10); // Add small delay between attempts
//     }
//     debug_led_blink(10); // ACMD41 complete

//     // Check SDHC
//     if (r & 0x40000000)
//     {
//         is_sdhc = 1;
//     }

//     // CMD16: set block length = 512 bytes
//     sd_send_command(SET_BLOCKLEN, 512, 1);
//     wait_msec(10);
//     debug_led_blink(11); // Init complete

//     return 0;
// }

// Additionally, let's also update the sd_send_command function to be more robust:

// static int sd_send_command(uint32_t cmd_idx, uint32_t arg, uint32_t resp48)
// {
//     // Wait until command line is free
//     int timeout = 1000;
//     while ((mmio_read(EMMC_STATUS) & (1 << 1)) && --timeout)
//     {
//         wait_msec(1);
//     }
//     if (timeout == 0) return -1;

//     // Clear interrupt status
//     mmio_write(EMMC_INTERRUPT, 0xffffffff);

//     // Write arg
//     mmio_write(EMMC_ARG1, arg);

//     // Prepare command
//     uint32_t cmd_val = (cmd_idx & 0x3F) << 24;
    
//     // Add response type
//     if (resp48)
//     {
//         cmd_val |= CMD_RSPNS_48;
//     }
    
//     // If it's an APP_CMD
//     if (cmd_idx == APP_CMD)
//     {
//         cmd_val |= CMD_NEED_APP;
//     }
    
//     // Send command
//     mmio_write(EMMC_CMDTM, cmd_val);

//     // Wait for command completion
//     timeout = 1000;
//     while (!(mmio_read(EMMC_INTERRUPT) & 0x1) && --timeout)
//     {
//         wait_msec(1);
//     }
    
//     if (timeout == 0) return -1;
    
//     // Clear the command complete status
//     mmio_write(EMMC_INTERRUPT, 0x1);

//     return 0;
// }

// These changes should help resolve the clock stabilization issue by:

//     Using a more conservative clock divider
//     Adding proper timeout handling
//     Improving the reset sequence
//     Adding more wait times between critical operations
//     Making the command sending more robust
