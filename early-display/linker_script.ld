ENTRY(_start)

SECTIONS
{
    /* Kernel load address for Pi Zero 2 W */
    . = 0x80000;
    
    /* Add alignment for the start of the kernel */
    . = ALIGN(8);
    
    .text : {
        __text_start = .;
        KEEP(*(.text.boot))  /* Keep boot code first */
        *(.text .text.* .gnu.linkonce.t*)
        __text_end = .;
    }
    
    . = ALIGN(8);
    
    .rodata : {
        __rodata_start = .;
        *(.rodata .rodata.* .gnu.linkonce.r*)
        __rodata_end = .;
    }
    
    . = ALIGN(8);
    
    .data : {
        __data_start = .;
        *(.data .data.* .gnu.linkonce.d*)
        __data_end = .;
    }
    
    . = ALIGN(8);
    
    .bss (NOLOAD) : {
        . = ALIGN(16);
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        __bss_end = .;
    }
    
    . = ALIGN(8);
    
    /* Add a known end location */
    __end = .;
    
    /DISCARD/ : {
        *(.comment)
        *(.gnu*)
        *(.note*)
        *(.eh_frame*)
    }
}

__bss_size = (__bss_end - __bss_start) >> 3;
