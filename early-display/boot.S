.section ".text.boot"
.global _start

_start:
    // Set up stack pointer
    mov sp, #0x8000
    
    // Clear BSS
    ldr r4, =__bss_start
    ldr r9, =__bss_end
    mov r5, #0
    mov r6, #0
    mov r7, #0
    mov r8, #0
    b       2f

1:
    // Store multiple at r4
    stmia r4!, {r5-r8}

2:
    // Loop until we hit bss_end
    cmp r4, r9
    blo 1b

    // Jump to our main() function
    bl      main
    
    // Loop forever if main returns
1:  wfe
    b       1b
