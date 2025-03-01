.section ".text.boot"
.global _start

_start:
    // GPIO base address for Pi Zero 2
    ldr r0, =0x3F200000
    
    // Configure GPIO 2 (SDA) and 3 (SCL) as outputs
    ldr r2, [r0]         // Load current GPFSEL0
    bic r2, r2, #(7<<6)  // Clear bits 6-8 (GPIO 2's function bits)
    bic r2, r2, #(7<<9)  // Clear bits 9-11 (GPIO 3's function bits)
    orr r2, r2, #(1<<6)  // Set GPIO 2 as output
    orr r2, r2, #(1<<9)  // Set GPIO 3 as output
    str r2, [r0]         // Store back to GPFSEL0

    // Release both lines (they will be pulled up)
    mov r1, #((1<<2)|(1<<3))  // Both GPIO 2 and 3
    str r1, [r0, #0x1C]       // GPSET0

    // Long delay for power-up (about 3 seconds)
    mov r2, #0x3000000
1:  subs r2, r2, #1
    bne 1b

    // I2C Start condition - pull SDA low while SCL is high
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0 - SDA low

    // Delay (about 1 second)
    mov r2, #0x1000000
2:  subs r2, r2, #1
    bne 2b

    // Pull SCL low
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x28] // GPCLR0 - SCL low

    // Now blink SDA to show we reached this point
3:  // Blink loop - 1 second on, 1 second off
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0 - SDA high
    
    mov r2, #0x1000000
4:  subs r2, r2, #1
    bne 4b
    
    str r1, [r0, #0x28] // GPCLR0 - SDA low
    
    mov r2, #0x1000000
5:  subs r2, r2, #1
    bne 5b
    
    b 3b                // Loop forever
