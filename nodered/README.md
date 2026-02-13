# Node-RED Flow: Tibber Ampel

Dieser Flow steuert die Tibber Strompreis-Ampel ueber Node-RED in Home Assistant.

## Voraussetzungen

- **Node-RED Addon** in Home Assistant installiert
- **node-red-contrib-home-assistant-websocket** Palette installiert (fuer HA-Nodes)
- **MQTT Broker** (z.B. Mosquitto Addon) konfiguriert und in Node-RED als Server hinterlegt
- **Home Assistant Server** in Node-RED konfiguriert (HA Companion Integration)
- **sensor.tibber_preis_status** Template-Sensor in HA (siehe `homeassistant/`)

## Flow importieren

1. Node-RED oeffnen (Home Assistant > Seitenleiste > Node-RED)
2. Menue (oben rechts) > **Import** > **Clipboard**
3. Inhalt von `tibber_ampel_flow.json` einfuegen
4. **Import** klicken
5. Den MQTT-Broker-Node und HA-Server-Node auf eure lokalen Konfigurationen setzen
6. **Deploy** klicken

## Flow-Architektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Tab: Tibber Ampel                                                          │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  Tibber Strompreis-Ampel (Tasmota ESP8266)          [comment]   │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  ┌───────────────────┐    ┌─────────────┐    ┌──────────────────┐          │
│  │ Tibber Preis       │    │             │ 1→ │ POWER1 (Rot)     │──► MQTT  │
│  │ Status             │───►│ Ampel-Logik │ 2→ │ POWER2 (Gelb)    │──► MQTT  │
│  │ [HA state-changed] │    │ [function]  │ 3→ │ POWER3 (Gruen)   │──► MQTT  │
│  └───────────────────┘    │             │    └──────────────────┘          │
│   sensor.tibber_           │  switch()   │    ┌──────────────────┐          │
│   preis_status             │  guenstig→3 │───►│ Ampel Status     │          │
│                            │  normal  →2 │    │ [debug]          │          │
│                            │  teuer   →1 │    └──────────────────┘          │
│                            └─────────────┘                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  Test-Buttons (zum Testen ohne echte Preisaenderung)  [comment] │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  ┌────────────────────────┐                                                 │
│  │ Test: guenstig (Gruen) │──┐                                              │
│  │ [inject]               │  │                                              │
│  ├────────────────────────┤  ├──► Ampel-Logik (gleicher Function-Node)      │
│  │ Test: normal (Gelb)    │──┤                                              │
│  │ [inject]               │  │                                              │
│  ├────────────────────────┤  │                                              │
│  │ Test: teuer (Rot)      │──┘                                              │
│  │ [inject]               │                                                 │
│  └────────────────────────┘                                                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  MQTT Topics (Tasmota)                                [comment] │       │
│  └──────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Node-Beschreibung

### 1. Tibber Preis Status (server-state-changed)
- Ueberwacht `sensor.tibber_preis_status` in Home Assistant
- Gibt den aktuellen State als `msg.payload` weiter: `"günstig"`, `"normal"` oder `"teuer"`
- `outputInitially: true` → sendet den aktuellen Status sofort beim Deploy
- `outputOnlyOnStateChange: true` → reagiert nur auf echte Aenderungen
- Ignoriert `unknown` und `unavailable` States

### 2. Ampel-Logik (function)
- Empfaengt den Preis-Status und mappt ihn auf 3 Ausgaenge:
  - **Output 1** (Rot): `ON` wenn `teuer`, sonst `OFF`
  - **Output 2** (Gelb): `ON` wenn `normal`, sonst `OFF`
  - **Output 3** (Gruen): `ON` wenn `günstig`, sonst `OFF`
- **Fallback**: Bei unbekanntem Status → Gelb
- Setzt einen visuellen Node-Status (farbiger Punkt) zur schnellen Kontrolle

### 3. MQTT Out Nodes (mqtt out)
- Senden `ON`/`OFF` an die Tasmota MQTT Command-Topics:
  - `cmnd/tibber-ampel/POWER1` → Rote LED (GPIO12)
  - `cmnd/tibber-ampel/POWER2` → Gelbe LED (GPIO13)
  - `cmnd/tibber-ampel/POWER3` → Gruene LED (GPIO15)
- QoS 1 (mindestens einmal zugestellt)
- Kein Retain (aktueller Befehl, kein persistenter State)

### 4. Test-Inject Nodes
- 3 manuelle Trigger-Buttons zum Testen aller LEDs ohne echte Preisaenderung
- Nuetzlich nach dem ersten Setup oder bei Fehlersuche

### 5. Debug Node
- Zeigt alle MQTT-Befehle in der Node-RED Debug-Sidebar
- Kann bei Bedarf deaktiviert werden

## MQTT Topics (Referenz)

| Richtung | Topic | Funktion |
|----------|-------|----------|
| Command  | `cmnd/tibber-ampel/POWER1` | Rote LED schalten |
| Command  | `cmnd/tibber-ampel/POWER2` | Gelbe LED schalten |
| Command  | `cmnd/tibber-ampel/POWER3` | Gruene LED schalten |
| Status   | `stat/tibber-ampel/POWER1` | Rot Status-Feedback |
| Status   | `stat/tibber-ampel/POWER2` | Gelb Status-Feedback |
| Status   | `stat/tibber-ampel/POWER3` | Gruen Status-Feedback |
| Telemetry | `tele/tibber-ampel/STATE` | Periodischer Gesamtstatus |

## Anpassung fuer weitere Ampeln

Der Flow kann fuer weitere Ampeln dupliziert werden. Aendere dazu:
1. Den Tasmota `Topic` auf dem neuen ESP (z.B. `tibber-ampel-2`)
2. Die MQTT-Topics in den 3 MQTT-Out-Nodes
3. Optional: Einen anderen HA-Sensor als Trigger
