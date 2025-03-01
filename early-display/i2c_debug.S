.section ".text.boot"
.global _start

// Macro to create a specific duty cycle
.macro DUTY_CYCLE percentage, duration
    mov r6, #\duration   // How many cycles to run
1:  
    mov r1, #(1<<2)      // GPIO 2
    str r1, [r0, #0x1C]  // High
    mov r2, #\percentage // High time
2:  subs r2, r2, #1
    bne 2b
    
    str r1, [r0, #0x28]  // Low
    mov r2, #(1000-\percentage) // Low time
3:  subs r2, r2, #1
    bne 3b
    
    subs r6, r6, #1
    bne 1b
.endm

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

    // Initial HIGH to show we started
    mov r1, #((1<<2)|(1<<3))  // Both GPIO 2 and 3
    str r1, [r0, #0x1C]       // GPSET0
    mov r2, #0x800000         // ~1.3s
4:  subs r2, r2, #1
    bne 4b

    // Stage 1: Show 20% duty cycle (~0.66V)
    DUTY_CYCLE 200, 0x100000

    // I2C Start condition
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0 - SDA low

    // Stage 2: Show 40% duty cycle (~1.32V)
    DUTY_CYCLE 400, 0x100000

    // Pull SCL low
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x28] // GPCLR0 - SCL low

    // Stage 3: Show 60% duty cycle (~2V)
    DUTY_CYCLE 600, 0x100000

    // Send address (0x3C << 1 = 0x78)
    mov r3, #0x78       // Device address
    mov r4, #8          // 8 bits to send

    // Stage 4: Show 80% duty cycle (~2.64V)
    DUTY_CYCLE 800, 0x100000

    // If we get here, loop with a unique pattern
    // 0.5s high, 0.1s low (~2.75V average)
5:  mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0 - high
    mov r2, #0x200000   // ~0.5s
    subs r2, r2, #1
    bne .-8
    str r1, [r0, #0x28] // GPCLR0 - low
    mov r2, #0x080000   // ~0.1s
    subs r2, r2, #1
    bne .-8
    b 5b
