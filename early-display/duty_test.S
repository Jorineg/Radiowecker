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

    // Initial 3s high to show we're starting
    mov r1, #(1<<2)      // GPIO 2
    str r1, [r0, #0x1C]  // GPSET0 - high
    mov r2, #0xC00000    // ~3s
1:  subs r2, r2, #1
    bne 1b

    // Now show different duty cycles to help debug:
    
    // Pattern 1: 20% duty cycle (should read ~0.66V)
2:  mov r1, #(1<<2)      // GPIO 2
    str r1, [r0, #0x1C]  // High
    mov r2, #200         // Stay high for 200 cycles
3:  subs r2, r2, #1
    bne 3b
    
    str r1, [r0, #0x28]  // Low
    mov r2, #800         // Stay low for 800 cycles
4:  subs r2, r2, #1
    bne 4b
    
    mov r3, #0x100000    // Do this for ~1 second
5:  subs r3, r3, #1
    bne 2b
    
    // Pattern 2: 50% duty cycle (should read ~1.65V)
6:  mov r1, #(1<<2)      // GPIO 2
    str r1, [r0, #0x1C]  // High
    mov r2, #500         // Stay high for 500 cycles
7:  subs r2, r2, #1
    bne 7b
    
    str r1, [r0, #0x28]  // Low
    mov r2, #500         // Stay low for 500 cycles
8:  subs r2, r2, #1
    bne 8b
    
    mov r3, #0x100000    // Do this for ~1 second
9:  subs r3, r3, #1
    bne 6b
    
    // Pattern 3: 80% duty cycle (should read ~2.64V)
10: mov r1, #(1<<2)      // GPIO 2
    str r1, [r0, #0x1C]  // High
    mov r2, #800         // Stay high for 800 cycles
11: subs r2, r2, #1
    bne 11b
    
    str r1, [r0, #0x28]  // Low
    mov r2, #200         // Stay low for 200 cycles
12: subs r2, r2, #1
    bne 12b
    
    mov r3, #0x100000    // Do this for ~1 second
13: subs r3, r3, #1
    bne 10b
    
    b 2b                 // Loop through all patterns again
