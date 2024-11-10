import machine
import time
import network
import ubinascii
import ujson
import env
from umqtt.simple import MQTTClient
import webrepl
import urequests

# Konfigurationsvariablen für Updates
CHECK_INTERVAL = 2 * 60 * 60  # 2 Stunden in Sekunden
REPO_URL = "https://api.github.com/repos/icepaule/tibberampel/releases/latest"
CURRENT_VERSION = "v1.0.4"  # Aktuelle installierte Version

# LCD-Initialisierung mit Fehlerbehandlung
lcd = None

try:
    from i2c_lcd import I2cLcd
    i2c = machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4))  # SCL (D1), SDA (D2)
    I2C_ADDR = 0x27
    lcd = I2cLcd(i2c, I2C_ADDR, 4, 20)  # LCD mit 4 Zeilen und 20 Spalten
    print("LCD initialized.")
except Exception as e:
    print("LCD initialization failed:", e)

# Pins für die LEDs (D-Bezeichnungen)
green_led = machine.Pin(15, machine.Pin.OUT)  # Grüne LED an GPIO15 (D8)
yellow_led = machine.Pin(13, machine.Pin.OUT)  # Gelbe LED an GPIO13 (D7)
red_led = machine.Pin(12, machine.Pin.OUT)     # Rote LED an GPIO12 (D6)

# Globale Variablen
current_state = "Off"
current_price = 0.0
current_power = 0
mqtt_client = None
blinking_active = False

# WiFi-Verbindung herstellen
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(dhcp_hostname=env.wifi_hostname)
    wlan.connect(env.wifi_ssid, env.wifi_password)
    while not wlan.isconnected():
        print("Attempting to connect to WiFi...")
        time.sleep(1)
    print("Connected to WiFi:", wlan.ifconfig())

# Versionsnummer von GitHub abrufen und prüfen
def check_for_update():
    try:
        print("Checking for update...")
        headers = {"User-Agent": "MicroPython"}
        response = urequests.get(REPO_URL, headers=headers)
        
        # Inhalt der Antwort zur Diagnose ausgeben
        print("Response content:", response.text)
        
        data = response.json()
        latest_version = data["tag_name"]
        download_url = data["assets"][0]["browser_download_url"]
        response.close()
        
        if latest_version != CURRENT_VERSION:
            print("New version {latest_version} found! Downloading update...")
            download_and_install_update(download_url, latest_version)
        else:
            print("No update available. Current version is up-to-date.")
    except ValueError as e:
        print("Error parsing JSON response:", e)
    except Exception as e:
        print("Error checking for update:", e)

# Update herunterladen und installieren
def download_and_install_update(url, version):
    try:
        # Alle LEDs einschalten, um das Update anzuzeigen
        green_led.on()
        yellow_led.on()
        red_led.on()
        
        # Erhalte die endgültige Download-URL durch eine zusätzliche Anfrage
        headers = {"User-Agent": "MicroPython"}
        initial_response = urequests.get(url, headers=headers)
        
        if 'location' in initial_response.headers:
            final_url = initial_response.headers['location']
            initial_response.close()
            
            # Anfrage an die endgültige URL, um den Inhalt herunterzuladen
            response = urequests.get(final_url, headers=headers)
        else:
            # Falls keine Weiterleitung vorhanden ist, nutze die ursprüngliche Antwort
            response = initial_response
        
        with open("main.py", "w") as f:
            f.write(response.text)
        
        response.close()
        print("Update downloaded and installed successfully!")
        global CURRENT_VERSION
        CURRENT_VERSION = version
        machine.reset()  # Gerät neu starten, um das Update zu aktivieren
    except Exception as e:
        print("Error downloading update:", e)


# LEDs in sicheren Zustand versetzen
def set_initial_led_state():
    green_led.off()
    yellow_led.off()
    red_led.off()

# WebREPL starten
def start_webrepl():
    webrepl.start(password=env.webrepl_password)
    print("WebREPL started with configured password.")

# Aktualisieren der LCD-Anzeige
def update_lcd():
    if lcd:
        try:
            lcd.clear()
            lcd.move_to(0, 0)
            lcd.putstr("State: {}".format(current_state))
            lcd.move_to(0, 1)
            lcd.putstr("Power: {} W".format(current_power))
            lcd.move_to(0, 2)
            lcd.putstr("Price: {:.4f} €/kWh".format(current_price))
        except Exception as e:
            print("Error updating LCD:", e)

# Berechnung und Anzeige der Kosten
def calculate_and_display_cost():
    if current_power > 0 and current_price > 0:
        power_in_kwh = current_power / 1000
        cost_in_euro = power_in_kwh * current_price
        print("Current cost: {:.4f} € (Power: {} W, Price: {:.4f} €/kWh)".format(cost_in_euro, current_power, current_price))

# LED-Status basierend auf Preis einstellen
def set_traffic_light_based_on_price(price):
    global current_state, blinking_active
    set_initial_led_state()
    
    if price < 0.10:
        green_led.on()
        blinking_active = True
        current_state = "Very Cheap (Blinking Green)"
    elif price < 0.20:
        green_led.on()
        blinking_active = False
        current_state = "Cheap (Green)"
    elif price < 0.30:
        yellow_led.on()
        blinking_active = False
        current_state = "Normal (Yellow)"
    elif price < 0.40:
        red_led.on()
        blinking_active = False
        current_state = "Expensive (Red)"
    else:
        blinking_active = True
        current_state = "Very Expensive (Blinking Red)"
    
    update_lcd()

# Blinken der LEDs, wenn das Blinken aktiviert ist
def blink_led():
    if blinking_active:
        if current_state == "Very Cheap (Blinking Green)":
            green_led.toggle()
        elif current_state == "Very Expensive (Blinking Red)":
            red_led.toggle()
        time.sleep(0.5)

# MQTT Callback für eingehende Nachrichten
def mqtt_callback(topic, msg):
    global current_price, current_power
    topic = topic.decode('utf-8')
    msg = msg.decode('utf-8')
    print("Topic received: {}, Message received: {}".format(topic, msg))

    if topic == env.mqtt_topic:
        pass
    elif topic == env.mqtt_price_topic:
        try:
            current_price = float(msg)
            print("Price updated to: {:.4f} €/kWh".format(current_price))
            set_traffic_light_based_on_price(current_price)
            calculate_and_display_cost()
        except ValueError:
            print("Invalid price value:", msg)
    elif topic == env.mqtt_power_topic:
        try:
            current_power = int(msg)
            print("Power consumption updated to: {} W".format(current_power))
            calculate_and_display_cost()
        except ValueError:
            print("Invalid power value:", msg)

# Verbindet mit dem MQTT-Server und abonniert Themen
def mqtt_connect_and_get_initial_price_level():
    global mqtt_client
    while True:
        try:
            client_id = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
            mqtt_client = MQTTClient(client_id, env.mqtt_server, port=env.mqtt_port, user=env.mqtt_username, password=env.mqtt_password)
            mqtt_client.set_callback(mqtt_callback)
            mqtt_client.connect()
            mqtt_client.subscribe(env.mqtt_topic)
            mqtt_client.subscribe(env.mqtt_power_topic)
            mqtt_client.subscribe(env.mqtt_price_topic)
            print("Connected to {} and subscribed to topics.".format(env.mqtt_server))
            break
        except Exception as e:
            print("MQTT connection failed:", e)
            time.sleep(5)

# Hauptprogramm
def main():
    connect_wifi()
    set_initial_led_state()
    start_webrepl()
    
    # Initiale Update-Prüfung direkt nach dem Einschalten
    check_for_update()
    
    mqtt_connect_and_get_initial_price_level()

    last_check_time = time.time()
    last_update_time = time.time()

    while True:
        mqtt_client.check_msg()
        current_time = time.time()
        
        # Jede Minute auf Nachrichten prüfen
        if current_time - last_update_time >= 60:
            mqtt_client.check_msg()
            last_update_time = current_time
        
        # Alle zwei Stunden auf Updates prüfen
        if current_time - last_check_time >= CHECK_INTERVAL:
            check_for_update()
            last_check_time = current_time
        
        # Blinken der LEDs, falls aktiviert
        blink_led()

if __name__ == "__main__":
    main()
