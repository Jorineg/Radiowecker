.section ".text.boot"
.global _start

_start:
    // GPIO base address for Pi Zero 2
    ldr r0, =0x3F200000
    
    // Configure GPIO 2 as output
    ldr r2, [r0]         // Load current GPFSEL0
    bic r2, r2, #(7<<6)  // Clear bits 6-8 (GPIO 2's function bits)
    orr r2, r2, #(1<<6)  // Set GPIO 2 as output
    str r2, [r0]         // Store back to GPFSEL0

    // Initial 3s high
    mov r1, #(1<<2)      // GPIO 2
    str r1, [r0, #0x1C]  // GPSET0 - high
    mov r2, #0xC00000    // ~3s
1:  subs r2, r2, #1
    bne 1b

    // Simple alternating pattern:
    // 2 seconds all high, 2 seconds all low
2:  mov r1, #(1<<2)      // GPIO 2
    str r1, [r0, #0x1C]  // High
    mov r2, #0x800000    // ~2s
3:  subs r2, r2, #1
    bne 3b
    
    str r1, [r0, #0x28]  // Low
    mov r2, #0x800000    // ~2s
4:  subs r2, r2, #1
    bne 4b
    
    b 2b                 // Loop forever
