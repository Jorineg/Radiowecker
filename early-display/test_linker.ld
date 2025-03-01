ENTRY(_start)

SECTIONS
{
    . = 0x8000;     /* Kernel load address */
    
    .text : {
        KEEP(*(.text.boot))
        *(.text)
    }
    
    /DISCARD/ : {
        *(.comment)
        *(.gnu*)
        *(.note*)
        *(.eh_frame*)
    }
}
