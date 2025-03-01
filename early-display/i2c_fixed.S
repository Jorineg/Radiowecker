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

    // Initial delay (2s actual)
    mov r2, #0x800000
1:  subs r2, r2, #1
    bne 1b

    // I2C Start condition
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0 - SDA low

    // Short delay
    mov r2, #100        // Adjusted for actual CPU speed
2:  subs r2, r2, #1
    bne 2b

    // Pull SCL low
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x28] // GPCLR0 - SCL low

    // Send address (0x3C << 1 = 0x78)
    mov r3, #0x78       // Device address
    mov r4, #8          // 8 bits to send

3:  // Bit send loop
    // Put bit on SDA
    tst r3, #0x80       // Test MSB
    beq 4f              // If 0, jump to set SDA low
    
    // Release SDA (pull-up will take it high)
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0
    b 5f
    
4:  // Pull SDA low
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0

5:  // Brief delay
    mov r2, #50         // Adjusted for actual CPU speed
6:  subs r2, r2, #1
    bne 6b

    // Clock pulse
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x1C] // GPSET0
    
    mov r2, #50
7:  subs r2, r2, #1
    bne 7b

    str r1, [r0, #0x28] // GPCLR0

    // Next bit
    lsl r3, r3, #1      // Shift to next bit
    subs r4, r4, #1     // Decrement bit counter
    bne 3b              // Loop if more bits

    // Release SDA for ACK
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0

    // Brief delay
    mov r2, #50
8:  subs r2, r2, #1
    bne 8b

    // Clock high for ACK
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x1C] // GPSET0

    // Wait and check ACK
    mov r2, #50
9:  subs r2, r2, #1
    bne 9b

    // Read SDA (should be low for ACK)
    ldr r1, [r0, #0x34] // GPLEV0
    tst r1, #(1<<2)     // Test SDA
    beq 11f             // If low (ACK), jump to success

    // No ACK - pattern: 1s on, 3s off (will appear as ~0.7s/2s)
10: mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0 - high
    mov r2, #0x400000   // ~0.7s
    subs r2, r2, #1
    bne .-8
    str r1, [r0, #0x28] // GPCLR0 - low
    mov r2, #0xC00000   // ~2s
    subs r2, r2, #1
    bne .-8
    b 10b

    // ACK received - pattern: 3s on, 1s off (will appear as ~2s/0.7s)
11: mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0 - high
    mov r2, #0xC00000   // ~2s
    subs r2, r2, #1
    bne .-8
    str r1, [r0, #0x28] // GPCLR0 - low
    mov r2, #0x400000   // ~0.7s
    subs r2, r2, #1
    bne .-8
    b 11b
