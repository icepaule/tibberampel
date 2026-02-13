from machine import I2C, Pin
from i2c_lcd import I2cLcd
import time

# Initialisierung des I2C-Busses und des LCD-Displays
i2c = I2C(scl=Pin(5), sda=Pin(4))  # SCL auf D2 (GPIO4), SDA auf D3 (GPIO0)
I2C_ADDR = 0x27  # Die I2C-Adresse für das LCD, die du gefunden hast
lcd = I2cLcd(i2c, I2C_ADDR, 4, 20)  # 4 Zeilen, 20 Zeichen

# Testanzeige auf dem LCD
try:
    lcd.clear()
    time.sleep(0.1)  # Pause nach dem Clear-Befehl
    lcd.move_to(0, 0)
    lcd.putstr("Test HD44780 4x20")
    time.sleep(1)

    lcd.move_to(0, 1)
    lcd.putstr("Zeile 2 sichtbar?")
    time.sleep(1)

    lcd.move_to(0, 2)
    lcd.putstr("Zeile 3 sichtbar?")
    time.sleep(1)

    lcd.move_to(0, 3)
    lcd.putstr("Zeile 4 sichtbar?")
    time.sleep(2)

    # LCD löschen und Erfolgsmeldung anzeigen
    time.sleep(0.1)
    lcd.putstr("4x20 LCD erfolgreich!")
except Exception as e:
    print("Fehler bei LCD-Anzeige:", e)