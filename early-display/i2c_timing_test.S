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

    // Delay for power-up (about 1 second)
    mov r2, #0x400000
1:  subs r2, r2, #1
    bne 1b

    // I2C Start sequence with proper timing
    // Start condition - pull SDA low while SCL is high
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0 - SDA low

    // Short delay (4.7µs)
    mov r2, #400
2:  subs r2, r2, #1
    bne 2b

    // Pull SCL low
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x28] // GPCLR0 - SCL low

    // Short delay
    mov r2, #400
3:  subs r2, r2, #1
    bne 3b

    // Send address byte (0x3C << 1 = 0x78)
    mov r3, #0x78       // Device address
    mov r4, #8          // 8 bits to send

4:  // Bit send loop
    // Put bit on SDA
    tst r3, #0x80       // Test MSB
    beq 5f              // If 0, jump to set SDA low
    
    // Release SDA (pull-up will take it high)
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0
    b 6f
    
5:  // Pull SDA low
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0

6:  // Data setup delay (4.7µs)
    mov r2, #400
7:  subs r2, r2, #1
    bne 7b

    // Release SCL (clock pulse)
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x1C] // GPSET0

    // Clock high time (4.7µs)
    mov r2, #400
8:  subs r2, r2, #1
    bne 8b

    // Pull SCL low
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x28] // GPCLR0

    // Clock low time (4.7µs)
    mov r2, #400
9:  subs r2, r2, #1
    bne 9b

    // Next bit
    lsl r3, r3, #1      // Shift to next bit
    subs r4, r4, #1     // Decrement bit counter
    bne 4b              // Loop if more bits

    // After sending address byte, before ACK check
    // Debug pattern: 2s high, 2s low (twice)
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    mov r5, #2          // Do this twice
11: str r1, [r0, #0x1C] // GPSET0 - high
    mov r2, #0x800000   // ~2s
    subs r2, r2, #1
    bne .-8
    str r1, [r0, #0x28] // GPCLR0 - low
    mov r2, #0x800000   // ~2s
    subs r2, r2, #1
    bne .-8
    subs r5, r5, #1
    bne 11b

    // Release SDA for ACK
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0

    // Short delay
    mov r2, #400
10: subs r2, r2, #1
    bne 10b

    // Clock high for ACK
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x1C] // GPSET0

    // Wait and check ACK
    mov r2, #400
11: subs r2, r2, #1
    bne 11b

    // Read SDA (should be low for ACK)
    ldr r1, [r0, #0x34] // GPLEV0
    tst r1, #(1<<2)     // Test SDA
    beq 13f             // If low (ACK), jump to success

    // No ACK - pattern: 1s on, 3s off
12: mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0 - high
    mov r2, #0x400000   // ~1s
    subs r2, r2, #1
    bne .-8
    str r1, [r0, #0x28] // GPCLR0 - low
    mov r2, #0xC00000   // ~3s
    subs r2, r2, #1
    bne .-8
    b 12b

    // ACK received - pattern: 3s on, 1s off
13: mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0 - high
    mov r2, #0xC00000   // ~3s
    subs r2, r2, #1
    bne .-8
    str r1, [r0, #0x28] // GPCLR0 - low
    mov r2, #0x400000   // ~1s
    subs r2, r2, #1
    bne .-8
    b 13b
