.section ".text.boot"
.global _start

_start:
    // Set up stack
    mov sp, #0x8000

    // Enable GPIO for LED (GPIO 47)
    ldr r0, =0x3F200000  // GPIO base
    
    // Set GPIO 47 to output (GPFSEL4)
    ldr r2, [r0, #4]     // Load current GPFSEL4
    bic r2, r2, #(7<<21) // Clear bits 21-23 (GPIO 47's function bits)
    orr r2, r2, #(1<<21) // Set as output
    str r2, [r0, #4]     // Store back to GPFSEL4

    // Simple blink loop
1:  // Turn LED on
    mov r1, #(1<<15)     // Bit 15 for GPIO 47
    str r1, [r0, #32]    // GPSET1
    
    // Short delay
    mov r2, #0x600000
2:  subs r2, r2, #1
    bne 2b
    
    // Turn LED off
    str r1, [r0, #44]    // GPCLR1
    
    // Short delay
    mov r2, #0x600000
3:  subs r2, r2, #1
    bne 3b
    
    b 1b                 // Loop forever

halt:
    wfe
    b halt
