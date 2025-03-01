.section ".text.boot"
.global _start

_start:
    // GPIO base address for Pi Zero 2
    ldr r0, =0x3F200000
    
    // Turn LED off first to see if we're executing
    mov r1, #(1<<15)     // Bit 15 for GPIO 47
    str r1, [r0, #44]    // GPCLR1 - turn off
    
    // Wait a bit
    mov r2, #0x1000000
1:  subs r2, #1
    bne 1b
    
    // Turn LED on
    str r1, [r0, #32]    // GPSET1 - turn on
    
    // Infinite loop
2:  b 2b
