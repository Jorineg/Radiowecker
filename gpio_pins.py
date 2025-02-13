"""
GPIO Pin definitions for Radiowecker project
"""

# I2C Pins (Display) - können von mehreren Geräten gleichzeitig genutzt werden
I2C_SDA = 2
I2C_SCL = 3

# I2S Pins (Audio) - werden vom DigiAMP+ verwendet
I2S_CLK = 18
I2S_FS = 19
I2S_DIN = 20
I2S_DOUT = 21

# DigiAMP+ Control
AMP_MUTE = 22  # Wird vom DigiAMP+ für Mute-Kontrolle verwendet

# Touch-Tasten
TOUCH_POWER = 4
TOUCH_SOURCE = 14
TOUCH_MENU = 15
TOUCH_BACKWARD = 17
TOUCH_FORWARD = 27

# Rotary Encoder 1
ROTARY1_A = 23    # Encoder Pin A
ROTARY1_B = 24    # Encoder Pin B
ROTARY1_SW = 10   # Switch (Taster)

# Rotary Encoder 2
ROTARY2_A = 9     # Encoder Pin A
ROTARY2_B = 25    # Encoder Pin B
ROTARY2_SW = 8    # Switch (Taster)

# Listen von Pins nach Funktion
TOUCH_PINS = [TOUCH_POWER, TOUCH_SOURCE, TOUCH_MENU, TOUCH_BACKWARD, TOUCH_FORWARD]
ROTARY1_PINS = [ROTARY1_A, ROTARY1_B, ROTARY1_SW]
ROTARY2_PINS = [ROTARY2_A, ROTARY2_B, ROTARY2_SW]

# Reserved/Used Pins (zur Information)
I2C_PINS = [I2C_SDA, I2C_SCL]
I2S_PINS = [I2S_CLK, I2S_FS, I2S_DIN, I2S_DOUT]
