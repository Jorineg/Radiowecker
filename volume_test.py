#!/usr/bin/env python3

import time
import threading
from display import OLEDDisplay, PygameDisplay
from gpio_pins import ROTARY1_A, ROTARY1_B, ROTARY1_SW
from volume_control import VolumeControl
import numpy as np
import pigpio


# GPIO Pins für Rotary Encoder
ROTARY_A = ROTARY1_A  # Volume encoder pins
ROTARY_B = ROTARY1_B
ROTARY_SW = ROTARY1_SW


pi = pigpio.pi()
pos = 0
last = (pi.read(ROTARY_A) << 1) | pi.read(ROTARY_B)


def main():
    # Initialize display
    try:
        display = OLEDDisplay(128, 64)
    except:
        print("Falling back to Pygame display")
        display = PygameDisplay(128, 64)
    
    # Initialize volume control
    volume = VolumeControl()


    def handle_rotation():
        global pos
        ticks = -pos
        pos = 0
        # Ticks * 2 für schnellere Änderung
        if ticks > 0:
            vol = volume.volume_up(step=ticks * 2)
        else:
            vol = volume.volume_down(step=-ticks * 2)
            
        # Update display
        display.buffer.clear()
        
        # Center volume text
        text = f"Volume: {vol}%"
        text_width = len(text) * 9  # 8x16 font is 9 pixels wide per char
        x = (display.width - text_width) // 2
        y = (display.height - 36) // 2  # Center vertically, leaving space for bar
        display.buffer.draw_text(x, y, text, size="8x16")
        
        # Center volume bar
        bar_width = int(display.width * 0.8)  # 80% of display width
        bar_height = 10
        x = (display.width - bar_width) // 2
        y = y + 26  # 10 pixels below text
        
        # Draw background bar
        display.buffer.draw_rect(x, y, bar_width, bar_height, False)
        
        # Draw filled portion
        if vol > 0:
            filled_width = int(bar_width * vol / 100)
            display.buffer.draw_rect(x, y, filled_width, bar_height, True)
            
        display.show()
    


    for g in (ROTARY_A, ROTARY_B):
        pi.set_mode(g, pigpio.INPUT)
        pi.set_pull_up_down(g, pigpio.PUD_UP)
        # pi.set_glitch_filter(g, 2000)  # debounce


    def cbf(gpio, level, tick):
        global last, pos
        s = (pi.read(ROTARY_A) << 1) | pi.read(ROTARY_B)
        if(s == last):
            return
        print(s)
        if s != last and s in (0, 3):             # only when A==B
            prevA = (last >> 1) & 1
            nowA  = (s    >> 1) & 1
            if nowA == prevA:
                pos += 1  # cw (or ccw depending on wiring)
            else:
                pos -= 1
        last = s

    c1 = pi.callback(ROTARY_A, pigpio.EITHER_EDGE, cbf)
    c2 = pi.callback(ROTARY_B, pigpio.EITHER_EDGE, cbf)

    
    while True:
        time.sleep(0.03)
        handle_rotation()

if __name__ == "__main__":
    main()
