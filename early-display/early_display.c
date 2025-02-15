#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <linux/i2c-dev.h>
#include <sys/ioctl.h>
#include <string.h>
#include "display_commands.h"

// Function to write to I2C with error checking
int i2c_write(int fd, const uint8_t* data, size_t length) {
    if (write(fd, data, length) != length) {
        fprintf(stderr, "Write failed\n");
        return -1;
    }
    return 0;
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
    
    // Write all initialization commands
    for (int i = 0; init_sequence[i].data != NULL; i++) {
        if (i2c_write(fd, init_sequence[i].data, init_sequence[i].length) < 0) {
            fprintf(stderr, "Init sequence failed at step %d\n", i);
            close(fd);
            return 1;
        }
        // Small delay between commands
        usleep(1000);
    }
    
    // Write the welcome screen buffer
    if (i2c_write(fd, welcome_screen_buffer, sizeof(welcome_screen_buffer)) < 0) {
        fprintf(stderr, "Failed to write welcome screen\n");
        close(fd);
        return 1;
    }
    
    close(fd);
    return 0;
}
