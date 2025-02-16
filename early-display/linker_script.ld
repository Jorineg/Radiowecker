SECTIONS
{
    /* Kernel load address for Pi Zero 2 */
    . = 0x80000;
    
    .text : {
        KEEP(*(.text.boot))  /* Keep boot code first */
        *(.text*)
    }
    
    .rodata : {
        *(.rodata*)
    }
    
    .data : {
        *(.data*)
    }
    
    .bss : {
        . = ALIGN(16);
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    }
    
    /DISCARD/ : {
        *(.comment)
        *(.gnu*)
        *(.note*)
        *(.eh_frame*)
    }
}
