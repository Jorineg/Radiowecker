CC=gcc
CFLAGS=-Wall -Wextra -O2
TARGET=early_display

$(TARGET): early_display.c display_commands.h
	$(CC) $(CFLAGS) -o $(TARGET) early_display.c

.PHONY: clean
clean:
	rm -f $(TARGET)
