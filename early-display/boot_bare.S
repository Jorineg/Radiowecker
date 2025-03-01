.section ".text.boot"
.global _start

_start:
    // Set up stack
    mov sp, #0x4000
    
    // Clear BSS
    ldr r4, =__bss_start
    ldr r9, =__bss_end
    mov r5, #0
    mov r6, #0
    mov r7, #0
    mov r8, #0
    
1:  // Store multiple at r4
    stmia r4!, {r5-r8}
    cmp r4, r9
    blo 1b
    
    // Jump to C code
    bl main

    // clean up
    cpsid if
    dsb sy
    isb sy

    // loop forever
    
2:  b 2b