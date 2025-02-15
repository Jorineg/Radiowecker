/* boot_i2c_bitbang.c /
/
This code runs at very early startup (for example in bootcode.bin)
and it does not rely on Linux or standard library functions.
It bit-bangs the I²C protocol on two GPIO pins (SDA, SCL) and
sends the SSD1306 initialization commands and welcome screen data.

(Make sure that display_commands.h is in your include path.)
*/

#include <stdint.h>
#include <stddef.h>

#ifdef LINUX_BUILD
    #include <stdio.h>
    #include <sys/mman.h>
    #include <fcntl.h>
    #include <unistd.h>
    
    static void *gpio_map;
    #define GPIO_ADDR(offset) ((volatile uint32_t *)((char *)gpio_map + offset))
#else
    #define GPIO_ADDR(offset) ((volatile uint32_t *)(GPIO_BASE + offset))
#endif

#include "display_commands.h"  // Contains welcome_screen_buffer & welcome_screen_buffer_size

/*
For the Raspberry Pi Zero 2 (BCM2710-based) the peripheral base is
usually 0x3F000000. Adjust PERIPHERAL_BASE if needed.
*/
#define PERIPHERAL_BASE 0x3F000000
#define GPIO_BASE       (PERIPHERAL_BASE + 0x200000)

// Offsets for GPIO registers (amounts in bytes)
#define GPFSEL_OFFSET   0x00  // Function select registers
#define GPSET_OFFSET    0x1C  // Output set registers
#define GPCLR_OFFSET    0x28  // Output clear registers

// I2C speed delay (busy-wait loop count; adjust as needed for ~400kHz)
#define I2C_DELAY_COUNT 50

// Which GPIO pins to use for bit-banging I²C?
#define SDA_PIN 2
#define SCL_PIN 3

// SSD1306 I²C address
#define SSD1306_ADDR 0x3C

//---------------------------------------------------------------------
// Simple busy–wait delay for I²C timing
static inline void i2c_delay(void)
{
volatile int i;
for (i = 0; i < I2C_DELAY_COUNT; i++) { asm volatile("nop"); }
}

//---------------------------------------------------------------------
// Set the function (mode) of a GPIO pin.
// mode 0 = input, 1 = output. (Other modes not used here.)
static inline void gpio_set_mode(uint32_t pin, uint32_t mode)
{
volatile uint32_t *gpfsel = GPIO_ADDR((pin / 10) * 4);
uint32_t shift = (pin % 10) * 3;
uint32_t value = *gpfsel;
value &= ~(7 << shift);      // clear the three bits for this pin
value |= (mode << shift);    // set mode (1 = output)
*gpfsel = value;
}

//---------------------------------------------------------------------
// Set or clear a GPIO pin (assumes the pin is output).
static inline void gpio_set(uint32_t pin)
{
volatile uint32_t *gpset = GPIO_ADDR(GPSET_OFFSET);
*gpset = (1 << pin);
}

static inline void gpio_clear(uint32_t pin)
{
volatile uint32_t *gpclr = GPIO_ADDR(GPCLR_OFFSET);
*gpclr = (1 << pin);
}

//---------------------------------------------------------------------
// I2C bit-banging low–level routines
//
// To send a start condition, we make sure that SDA and SCL are high,
// then pull SDA low (while SCL is still high) and finally pull SCL low.
static void i2c_start(void)
{
gpio_set(SDA_PIN);
gpio_set(SCL_PIN);
i2c_delay();
gpio_clear(SDA_PIN);  // SDA goes low while SCL high
i2c_delay();
gpio_clear(SCL_PIN);
i2c_delay();
}

// For a stop condition the sequence is reversed.
static void i2c_stop(void)
{
gpio_clear(SDA_PIN);
i2c_delay();
gpio_set(SCL_PIN);
i2c_delay();
gpio_set(SDA_PIN);
i2c_delay();
}

//---------------------------------------------------------------------
// Send one byte (MSB first) on I²C.
// After sending 8 bits we “clock” an ACK (by releasing SDA) but ignore it.
static int i2c_write_byte(uint8_t byte)
{
int i;
for (i = 0; i < 8; i++) {
if (byte & 0x80)
gpio_set(SDA_PIN);    // send bit ‘1’
else
gpio_clear(SDA_PIN);  // send bit ‘0’
i2c_delay();
gpio_set(SCL_PIN);      // clock high
i2c_delay();
gpio_clear(SCL_PIN);    // clock low
i2c_delay();
byte <<= 1;             // shift to next bit
}
// ACK clock: release SDA (leave it high) and clock one extra bit.
gpio_set(SDA_PIN);
i2c_delay();
gpio_set(SCL_PIN);
i2c_delay();
gpio_clear(SCL_PIN);
i2c_delay();
return 0;
}

//---------------------------------------------------------------------
// i2c_write() sends a sequence of bytes in one transaction.
// It sends a START condition, the slave address (with write bit), the
// bytes in the data buffer, and then a STOP condition.
static int i2c_write(const uint8_t *data, size_t length)
{
i2c_start();
// Send slave address with write (0) flag.
i2c_write_byte((SSD1306_ADDR << 1) | 0);
for (size_t i = 0; i < length; i++) {
i2c_write_byte(data[i]);
}
i2c_stop();
return 0;
}

//---------------------------------------------------------------------
// To send a single command we must send two bytes:
// first a control byte (0x00) then the command itself.
static int write_cmd(uint8_t cmd)
{
uint8_t buf[2];
buf[0] = 0x00;  // control byte for commands
buf[1] = cmd;
return i2c_write(buf, 2);
}

// To send display data we send a control byte of 0x40 first and then
// the data bytes (here we “stream” the entire buffer).
static int write_data(const uint8_t *data, size_t length)
{
i2c_start();
i2c_write_byte((SSD1306_ADDR << 1) | 0);
i2c_write_byte(0x40);  // control byte for data
for (size_t i = 0; i < length; i++) {
i2c_write_byte(data[i]);
}
i2c_stop();
return 0;
}

#ifdef LINUX_BUILD
int init_gpio(void) {
    int mem_fd;
    if ((mem_fd = open("/dev/mem", O_RDWR|O_SYNC)) < 0) {
        printf("Can't open /dev/mem\n");
        return -1;
    }

    gpio_map = mmap(
        NULL,
        4*1024,
        PROT_READ|PROT_WRITE,
        MAP_SHARED,
        mem_fd,
        GPIO_BASE
    );

    close(mem_fd);

    if (gpio_map == MAP_FAILED) {
        printf("mmap error\n");
        return -1;
    }
    return 0;
}
#else
#define init_gpio() 0
#endif

//---------------------------------------------------------------------
// main() – this is our boot-entry code.
// It sets up the two GPIO pins, sends the SSD1306’s initialization
// sequence and then writes the welcome image to the display.
int main(void)
{
    if (init_gpio() != 0) {
        #ifdef LINUX_BUILD
            printf("GPIO initialization failed\n");
        #endif
        return -1;
    }

    // Set up GPIO pins for I²C
    gpio_set_mode(SDA_PIN, 1);  // output
    gpio_set_mode(SCL_PIN, 1);  // output

    // Make sure both lines are high initially.
    gpio_set(SDA_PIN);
    gpio_set(SCL_PIN);

    // SSD1306 initialization command sequence.
    const uint8_t init_commands[] = {
    0xAE,        // Display off.
    0xD5, 0x80,  // Set display clock divisor.
    0xA8, 0x3F,  // Set multiplex ratio (1/64 duty).
    0xD3, 0x00,  // Set display offset.
    0x40,        // Set start line address.
    0x8D, 0x14,  // Enable charge pump.
    0x20, 0x00,  // Memory addressing mode: horizontal.
    0xA0,        // Segment remap (normal).
    0xC0,        // COM output scan direction (normal).
    0xDA, 0x12,  // Set COM pins hardware configuration.
    0x81, 0xCF,  // Set contrast control.
    0xD9, 0xF1,  // Set pre-charge period.
    0xDB, 0x40,  // Set VCOMH deselect level.
    0xA4,        // Disable entire display on.
    0xA6,        // Set normal display (non-inverted).
    0xAF         // Display on.
    };

    // Send each initialization command.
    for (size_t i = 0; i < sizeof(init_commands); i++) {
    if (write_cmd(init_commands[i]) != 0) {
        // In this early–boot example we simply loop on error.
        while (1);
    }
    i2c_delay();
    }

    // Set display addressing to cover the full screen.
    write_cmd(0x21);  // Set column address command.
    write_cmd(0);     // Start column 0.
    write_cmd(127);   // End column 127 (for a 128px wide display).
    write_cmd(0x22);  // Set page address command.
    write_cmd(0);     // Start page 0.
    write_cmd(7);     // End page 7 (for a 64px tall display – 8 pages).

    // Now write the welcome screen image data.
    write_data(welcome_screen_buffer, welcome_screen_buffer_size);

    #ifdef LINUX_BUILD
        // Cleanup for Linux version
        munmap(gpio_map, 4*1024);
    #endif

    return 0;
}