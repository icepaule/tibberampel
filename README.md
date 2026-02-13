# Tibber Strompreis-Ampel

Eine physische LED-Ampel die den aktuellen Strompreis von [Tibber](https://tibber.com/) visualisiert. Guenstiger Strom? Gruen. Normal? Gelb. Teuer? Rot. So einfach.

## Ueberblick

```
┌──────────┐     ┌──────────────┐     ┌────────┐     ┌─────────────────┐
│  Tibber   │────►│ Home         │────►│ Node-  │────►│ ESP8266         │
│  Cloud    │ API │ Assistant    │ HA  │ RED    │MQTT │ Tasmota         │
│           │     │ Sensor       │     │ Flow   │     │ 3x LED Ampel    │
└──────────┘     └──────────────┘     └────────┘     └─────────────────┘
                  sensor.tibber_       Ampel-         cmnd/tibber-ampel/
                  preis_status         Logik          POWER1/2/3
```

**Tibber** liefert den Strompreis → **Home Assistant** berechnet das Preis-Level → **Node-RED** steuert die LEDs → **Tasmota** schaltet die Ampel.

## Devices

| Device | Hostname | Tasmota Topic | Status |
|--------|----------|---------------|--------|
| **Tibber-Ampel-1** | Tibber-Ampel-01 | `tibber-ampel` | Aktiv |
| **Tibber-Ampel-2** | Tibber-Ampel-02 | `tibber-ampel-2` | Geplant |

## Hardware

### LED-Ampel-Modul

[AZ-Delivery LED Ampel Modul](https://www.az-delivery.de/en/products/led-ampel-modul) - Ein fertiges PCB mit 3 LEDs (Rot, Gelb, Gruen) im Ampel-Format, kompatibel mit Arduino und ESP8266/ESP32.

### Mikrocontroller

- **ESP8266** (ESP-8266MOD) mit CH340 USB-Serial Adapter
- **Firmware**: [Tasmota](https://tasmota.github.io/) 15.2.0
- **Flash**: 4 MB

### Pin-Belegung

| LED | Farbe | GPIO | D-Pin | Tasmota Component |
|-----|-------|------|-------|-------------------|
| Oben | Rot | GPIO12 | D6 | Relay1 (POWER1) |
| Mitte | Gelb | GPIO13 | D7 | Relay2 (POWER2) |
| Unten | Gruen | GPIO15 | D8 | Relay3 (POWER3) |

### Tasmota GPIO Template

```json
{"NAME":"Tibber Ampel","GPIO":[0,0,0,0,0,0,0,0,224,225,0,226,0],"FLAG":0,"BASE":18}
```

## Software-Stack

| Komponente | Funktion |
|-----------|----------|
| [Tibber Integration](https://www.home-assistant.io/integrations/tibber/) | Strompreis-Daten aus der Tibber Cloud |
| [Home Assistant](https://www.home-assistant.io/) | Template-Sensor berechnet Preis-Level |
| [Node-RED](https://nodered.org/) (HA Addon) | Automatisierungs-Flow: Preis → LED-Befehle |
| [Mosquitto](https://mosquitto.org/) (HA Addon) | MQTT Broker |
| [Tasmota](https://tasmota.github.io/) | ESP8266 Firmware, empfaengt MQTT-Befehle |

## Preis-Level

Der Template-Sensor `sensor.tibber_preis_status` in Home Assistant berechnet:

| Status | Preis | LED | Beschreibung |
|--------|-------|-----|-------------|
| `günstig` | < 21 ct/kWh | Gruen | Unter 70% vom Tagesdurchschnitt |
| `normal` | 21 - 39 ct/kWh | Gelb | Durchschnittlicher Bereich |
| `teuer` | > 39 ct/kWh | Rot | Ueber 130% vom Tagesdurchschnitt |

Die Schwellwerte koennen im HA Template-Sensor angepasst werden (siehe `homeassistant/`).

## Node-RED Flow

Die Ampel-Steuerung laeuft als Node-RED Flow im Home Assistant. Detaillierte Dokumentation und den importierbaren Flow findest du in [`nodered/`](nodered/).

### Flow-Diagramm

```
  ┌───────────────────┐    ┌─────────────┐    ┌──────────────────┐
  │ Tibber Preis       │    │             │ 1→ │ POWER1 (Rot)     │──► MQTT
  │ Status             │───►│ Ampel-Logik │ 2→ │ POWER2 (Gelb)    │──► MQTT
  │ [HA sensor]        │    │ [function]  │ 3→ │ POWER3 (Gruen)   │──► MQTT
  └───────────────────┘    └─────────────┘    └──────────────────┘

  ┌─────────────────────┐
  │ Test: guenstig      │──┐
  │ Test: normal        │──┼──► Ampel-Logik (manueller Test)
  │ Test: teuer         │──┘
  └─────────────────────┘
```

### Ampel-Logik (Function Node)

```javascript
var status = msg.payload;
var rot = "OFF", gelb = "OFF", gruen = "OFF";

switch(status) {
    case "günstig": gruen = "ON"; break;
    case "normal":  gelb  = "ON"; break;
    case "teuer":   rot   = "ON"; break;
    default:        gelb  = "ON"; break;  // Fallback
}

return [
    {payload: rot},    // Output 1 → POWER1 (Rot)
    {payload: gelb},   // Output 2 → POWER2 (Gelb)
    {payload: gruen}   // Output 3 → POWER3 (Gruen)
];
```

## Installation

### 1. Tasmota flashen

```bash
# Flash-Backup erstellen (optional)
esptool.py -p /dev/ttyUSB0 -b 57600 read_flash 0x00000 0x400000 backup.bin

# Tasmota flashen
esptool.py -p /dev/ttyUSB0 erase_flash
esptool.py -p /dev/ttyUSB0 write_flash -fs 4MB -fm dout 0x0 tasmota.bin.gz
```

### 2. Tasmota konfigurieren

Ueber die Tasmota-Konsole (Web-UI oder Serial):

```
Backlog Hostname Tibber-Ampel-01; Module 0; Gpio12 224; Gpio13 225; Gpio15 226; PowerOnState 0; MqttHost <BROKER_IP>; MqttPort 1883; Topic tibber-ampel
```

Vollstaendige Konfiguration: siehe [`tasmota/tasmota_config.txt`](tasmota/tasmota_config.txt)

### 3. Home Assistant Template-Sensor

Der Sensor `sensor.tibber_preis_status` muss in HA existieren. Beispiel-Konfiguration in [`homeassistant/`](homeassistant/).

### 4. Node-RED Flow importieren

1. Node-RED in HA oeffnen
2. **Import** > Inhalt von [`nodered/tibber_ampel_flow.json`](nodered/tibber_ampel_flow.json) einfuegen
3. MQTT-Broker und HA-Server Nodes auf lokale Konfiguration setzen
4. **Deploy**

Detaillierte Anleitung: siehe [`nodered/README.md`](nodered/README.md)

## MQTT Topics

| Richtung | Topic | Funktion |
|----------|-------|----------|
| Command | `cmnd/tibber-ampel/POWER1` | Rote LED (an/aus) |
| Command | `cmnd/tibber-ampel/POWER2` | Gelbe LED (an/aus) |
| Command | `cmnd/tibber-ampel/POWER3` | Gruene LED (an/aus) |
| Status | `stat/tibber-ampel/POWER1..3` | LED Status-Feedback |
| Telemetry | `tele/tibber-ampel/STATE` | Periodischer Gesamtstatus |

## Projektstruktur

```
tibberampel/
├── README.md                          # Diese Datei
├── nodered/
│   ├── README.md                      # Node-RED Flow Dokumentation
│   └── tibber_ampel_flow.json         # Importierbarer Node-RED Flow
├── tasmota/
│   └── tasmota_config.txt             # Tasmota Konsolen-Befehle
├── homeassistant/
│   └── tibber_ampel.yaml              # HA Automation (Alternative zu Node-RED)
└── micropython-legacy/
    ├── boot.py                        # Alter Boot-Loader mit OTA
    ├── main.py                        # Alte Ampel-Logik (MicroPython)
    ├── env.py.example                 # Beispiel-Konfiguration
    ├── i2c_lcd.py                     # LCD-Treiber (HD44780)
    └── i2c_scan.py                    # I2C-Scanner
```

## Zweite Ampel hinzufuegen (Tibber-Ampel-2)

Um eine zweite identische Ampel aufzusetzen:

1. **Tasmota** auf dem zweiten ESP flashen und konfigurieren:
   ```
   Backlog Hostname Tibber-Ampel-02; Topic tibber-ampel-2; ...
   ```
2. **Node-RED**: Den Flow duplizieren und die MQTT-Topics auf `tibber-ampel-2` aendern
3. Optional: Anderen Sensor als Trigger verwenden (z.B. fuer einen anderen Raum)

## Legacy: MicroPython

Die alte MicroPython-Version liegt in [`micropython-legacy/`](micropython-legacy/). Sie wurde durch die Tasmota + Node-RED Loesung ersetzt, da:

- Der ESP8266 mit MicroPython die Tibber-API-Abfrage und LED-Steuerung gleichzeitig machen musste → langsam und instabil
- Kein MQTT-Broker noetig war, aber dafuer ein ioBroker tibberlink Adapter
- OTA-Updates ueber GitHub Releases umstaendlich waren

Die neue Architektur trennt die Logik sauber: HA + Node-RED machen die smarte Arbeit, der ESP schaltet nur LEDs.

## Lizenz

Siehe [LICENSE](LICENSE).
