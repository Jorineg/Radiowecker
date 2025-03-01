#ifndef KERNEL_LOADER_H
#define KERNEL_LOADER_H

#include <stdint.h>
#include <stddef.h>

// FAT32 BPB (BIOS Parameter Block) structure
#pragma pack(push, 1)
typedef struct {
    uint8_t     jmp_boot[3];
    uint8_t     oem_name[8];
    uint16_t    bytes_per_sec;
    uint8_t     secs_per_cluster;
    uint16_t    rsvd_sec_cnt;
    uint8_t     num_fats;
    uint16_t    root_ent_cnt;
    uint16_t    tot_sec16;
    uint8_t     media;
    uint16_t    fat_sz16;
    uint16_t    sec_per_trk;
    uint16_t    num_heads;
    uint32_t    hidd_sec;
    uint32_t    tot_sec32;
    uint32_t    fat_sz32;
    uint16_t    ext_flags;
    uint16_t    fs_ver;
    uint32_t    root_clus;
    uint16_t    fs_info;
    uint16_t    bk_boot_sec;
    uint8_t     reserved[12];
    uint8_t     drv_num;
    uint8_t     reserved1;
    uint8_t     boot_sig;
    uint32_t    vol_id;
    uint8_t     vol_lab[11];
    uint8_t     fil_sys_type[8];
} bpb_t;

// FAT32 directory entry structure
typedef struct {
    uint8_t     name[11];
    uint8_t     attr;
    uint8_t     nt_res;
    uint8_t     crt_time_tenth;
    uint16_t    crt_time;
    uint16_t    crt_date;
    uint16_t    lst_acc_date;
    uint16_t    cluster_hi;
    uint16_t    wrt_time;
    uint16_t    wrt_date;
    uint16_t    cluster_lo;
    uint32_t    size;
} fat32_dirent_t;

// Function declarations
void chainload_linux(void);
int sd_init(void);

#endif // KERNEL_LOADER_H