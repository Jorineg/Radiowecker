.section ".text.boot"
.global _start

_start:
    // GPIO base address for Pi Zero 2
    ldr r0, =0x3F200000
    
    // Configure GPIO 2 (SDA) as output
    ldr r2, [r0]         // Load current GPFSEL0
    bic r2, r2, #(7<<6)  // Clear bits 6-8 (GPIO 2's function bits)
    orr r2, r2, #(1<<6)  // Set as output
    str r2, [r0]         // Store back to GPFSEL0

1:  // Blink loop
    // Turn GPIO 2 high
    mov r1, #(1<<2)
    str r1, [r0, #0x1C]  // GPSET0
    
    // Delay
    mov r2, #0x500000
2:  subs r2, r2, #1
    bne 2b
    
    // Turn GPIO 2 low
    str r1, [r0, #0x28]  // GPCLR0
    
    // Delay
    mov r2, #0x500000
3:  subs r2, r2, #1
    bne 3b
    
    b 1b
