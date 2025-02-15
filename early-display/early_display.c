#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <linux/i2c-dev.h>
#include <sys/ioctl.h>
#include <string.h>
#include "display_commands.h"

// Structure for command sequences
struct i2c_command {
    const uint8_t* data;
    size_t length;
};

// Function to write to I2C with error checking
int i2c_write(int fd, const uint8_t* data, size_t length) {
    ssize_t written = write(fd, data, length);
    if (written != (ssize_t)length) {
        fprintf(stderr, "Write failed\n");
        return -1;
    }
    return 0;
}

// Function to write a single command byte
int write_cmd(int fd, uint8_t cmd) {
    uint8_t buf[2] = {0x00, cmd};  // Command byte prefixed with 0x00
    return i2c_write(fd, buf, sizeof(buf));
}

// Function to write data bytes
int write_data(int fd, const uint8_t* data, size_t length) {
    // Data bytes are prefixed with 0x40
    uint8_t* buf = malloc(length + 1);
    if (!buf) return -1;
    
    buf[0] = 0x40;
    memcpy(buf + 1, data, length);
    
    int result = i2c_write(fd, buf, length + 1);
    free(buf);
    return result;
}

int main() {
    int fd;
    
    // Open I2C bus
    fd = open("/dev/i2c-1", O_RDWR);
    if (fd < 0) {
        fprintf(stderr, "Failed to open I2C bus\n");
        return 1;
    }
    
    // Set I2C slave address
    if (ioctl(fd, I2C_SLAVE, 0x3C) < 0) {
        fprintf(stderr, "Failed to set I2C slave address\n");
        close(fd);
        return 1;
    }
    
    // Initialize display
    const uint8_t init_commands[] = {
        0xAE,  // display off
        0xD5, 0x80,  // clock div
        0xA8, 0x3F,  // multiplex
        0xD3, 0x00,  // offset
        0x40,  // start line
        0x8D, 0x14,  // charge pump
        0x20, 0x00,  // memory mode
        0xA1,  // seg remap
        0xC8,  // com scan dec
        0xDA, 0x12,  // com pins
        0x81, 0xCF,  // contrast
        0xD9, 0xF1,  // precharge
        0xDB, 0x40,  // vcom detect
        0xA4,  // resume
        0xA6,  // normal
        0xAF   // display on
    };
    
    // Send init commands
    for (size_t i = 0; i < sizeof(init_commands); i++) {
        if (write_cmd(fd, init_commands[i]) < 0) {
            fprintf(stderr, "Init sequence failed at step %zu\n", i);
            close(fd);
            return 1;
        }
        usleep(1000);  // Small delay between commands
    }
    
    // Set address for full screen
    write_cmd(fd, 0x21);  // column address
    write_cmd(fd, 0);     // start
    write_cmd(fd, 127);   // end
    write_cmd(fd, 0x22);  // page address
    write_cmd(fd, 0);     // start
    write_cmd(fd, 7);     // end
    
    // Write the welcome screen buffer
    if (write_data(fd, welcome_screen_buffer, sizeof(welcome_screen_buffer)) < 0) {
        fprintf(stderr, "Failed to write welcome screen\n");
        close(fd);
        return 1;
    }
    
    close(fd);
    return 0;
}
