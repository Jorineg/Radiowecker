.section ".text.boot"
.global _start

_start:
    // GPIO base address for Pi Zero 2
    ldr r0, =0x3F200000
    
    // Configure GPIO 2 (SDA) and 3 (SCL) as outputs initially
    ldr r2, [r0]         // Load current GPFSEL0
    bic r2, r2, #(7<<6)  // Clear bits 6-8 (GPIO 2's function bits)
    bic r2, r2, #(7<<9)  // Clear bits 9-11 (GPIO 3's function bits)
    orr r2, r2, #(1<<6)  // Set GPIO 2 as output
    orr r2, r2, #(1<<9)  // Set GPIO 3 as output
    str r2, [r0]         // Store back to GPFSEL0

    // Release both lines (they will be pulled up)
    mov r1, #((1<<2)|(1<<3))  // Both GPIO 2 and 3
    str r1, [r0, #0x1C]       // GPSET0

    // Longer delay for power-up
    mov r2, #0x1000000
1:  subs r2, r2, #1
    bne 1b

    // I2C Start condition
    // First pull SDA low while SCL is high
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0 - SDA low
    
    // Delay for start hold time
    mov r2, #0x1000
2:  subs r2, r2, #1
    bne 2b

    // Then pull SCL low
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x28] // GPCLR0 - SCL low

    // Delay for setup
    mov r2, #0x1000
3:  subs r2, r2, #1
    bne 3b

    // Send address (0x3C) with write bit (0)
    mov r3, #0x78       // 0x3C << 1
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
    
6:  // Data setup delay
    mov r2, #0x1000
7:  subs r2, r2, #1
    bne 7b

    // Release SCL (clock pulse)
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x1C] // GPSET0
    
    // Clock high delay
    mov r2, #0x1000
8:  subs r2, r2, #1
    bne 8b

    // Pull SCL low
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x28] // GPCLR0

    // Clock low delay
    mov r2, #0x1000
9:  subs r2, r2, #1
    bne 9b

    // Next bit
    lsl r3, r3, #1      // Shift to next bit
    subs r4, r4, #1     // Decrement bit counter
    bne 4b              // Loop if more bits

    // Check ACK: Release SDA
    mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x1C] // GPSET0 - release SDA

    // Small delay for SDA to stabilize
    mov r2, #0x1000
10: subs r2, r2, #1
    bne 10b

    // Clock high for ACK
    mov r1, #(1<<3)     // GPIO 3 (SCL)
    str r1, [r0, #0x1C] // GPSET0 - SCL high
    
    // Delay to let SDA settle
    mov r2, #0x1000
11: subs r2, r2, #1
    bne 11b

    // Read SDA (should be pulled low by device for ACK)
    ldr r1, [r0, #0x34] // GPLEV0 - read GPIO levels
    tst r1, #(1<<2)     // Test SDA
    beq 13f             // If low (ACK received), continue

    // No ACK - error blink (1 second on/off)
12: mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0 - SDA low
    mov r2, #0x1000000
    subs r2, r2, #1
    bne .-8
    str r1, [r0, #0x1C] // GPSET0 - SDA high
    mov r2, #0x1000000
    subs r2, r2, #1
    bne .-8
    b 12b               // Loop forever in error state

    // ACK received - success blink (3 seconds on, 1 off)
13: mov r1, #(1<<2)     // GPIO 2 (SDA)
    str r1, [r0, #0x28] // GPCLR0 - SDA low
    mov r2, #0x3000000
    subs r2, r2, #1
    bne .-8
    str r1, [r0, #0x1C] // GPSET0 - SDA high
    mov r2, #0x1000000
    subs r2, r2, #1
    bne .-8
    b 13b               // Loop forever in success state
