# i2c_lcd.py
import time

class I2cLcd:
    # LCD-Kommandos
    LCD_CLEAR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE_SET = 0x04
    LCD_DISPLAY_CONTROL = 0x08
    LCD_CURSOR_SHIFT = 0x10
    LCD_FUNCTION_SET = 0x20
    LCD_SET_CGRAM_ADDR = 0x40
    LCD_SET_DDRAM_ADDR = 0x80

    # Flags für LCD-Einstellungen
    ENTRY_LEFT = 0x02
    ENTRY_SHIFT_DECREMENT = 0x00
    DISPLAY_ON = 0x04
    DISPLAY_OFF = 0x00
    CURSOR_ON = 0x02
    CURSOR_OFF = 0x00
    BLINK_ON = 0x01
    BLINK_OFF = 0x00
    FUNCTION_2LINE = 0x08
    FUNCTION_5x8DOTS = 0x00

    def __init__(self, i2c, address, rows, cols):
        self.i2c = i2c
        self.address = address
        self.rows = rows
        self.cols = cols
        self.display_control = self.DISPLAY_ON | self.CURSOR_OFF | self.BLINK_OFF
        self.display_function = self.FUNCTION_2LINE | self.FUNCTION_5x8DOTS
        self.init_lcd()

    def init_lcd(self):
        time.sleep(0.05)
        self.send_command(0x03)
        time.sleep(0.005)
        self.send_command(0x03)
        time.sleep(0.00015)
        self.send_command(0x03)
        self.send_command(0x02)
        self.send_command(self.LCD_FUNCTION_SET | self.display_function)
        self.send_command(self.LCD_DISPLAY_CONTROL | self.display_control)
        self.clear()
        self.send_command(self.LCD_ENTRY_MODE_SET | self.ENTRY_LEFT | self.ENTRY_SHIFT_DECREMENT)

    def clear(self):
        self.send_command(self.LCD_CLEAR)
        time.sleep(0.002)

    def move_to(self, row, col):
        addr = col + 0x40 * row
        self.send_command(self.LCD_SET_DDRAM_ADDR | addr)

    def putstr(self, string):
        for char in string:
            self.send_data(ord(char))

    def send_command(self, cmd):
        self.i2c.writeto(self.address, bytearray([0x80, cmd]))

    def send_data(self, data):
        self.i2c.writeto(self.address, bytearray([0x40, data]))