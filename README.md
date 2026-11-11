# 🔥 HeizungsWächter

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/HatchetMan111/HeizungsWaechter.svg)](https://github.com/HatchetMan111/HeizungsWaechter/releases)

**Home Assistant Custom Integration** zur Überwachung von Gas-, Öl- und Fossil-Heizungen.  
Funktioniert mit jedem Zigbee-Thermometer in der Messbohrung des Ofenrohrs – empfohlen: **SONOFF SNZB-02LD IP65**.

---

## ✨ Funktionen

| Sensor | Einheit | Beschreibung |
|--------|---------|-------------|
| 🔥 Brenner Status | AN/AUS | Erkennt ob die Heizung brennt |
| 🌡️ Ofenrohr Temperatur | °C | Live-Temperatur vom Zigbee-Sensor |
| ⏱️ Aktuelle Laufzeit | min | Laufende Session-Dauer |
| ⏱️ Laufzeit Heute / Monat / Gesamt | min/h | Akkumulierte Brennerlaufzeit |
| ⚡ Verbrauch Heute / Monat / Gesamt | kWh | Berechneter Brennstoff-Energieverbrauch |
| 💶 Kosten Heute / Monat / Gesamt | € | Heizkosten in Euro |
| 🔁 Brennerstarts Heute / Monat / Gesamt | Starts | Taktungszähler |
| 🛢️ Brennstoff Heute / Monat / Gesamt | L / m³ / kg | Volumen bzw. Masse je Brennstoff |

---

## 🖼️ Lovelace-Card (automatisch geladen)

Die Integration bringt eine eigene **Dashboard-Card mit** (React, gebaut mit Vite).
Sie wird beim Start der Integration automatisch registriert – **kein manueller
Ressourcen-Schritt in HACS/Lovelace nötig**. Einfach HA einmal neu laden (Browser-Refresh).

Card hinzufügen über den Dashboard-Editor (**Karte hinzufügen → Benutzerdefiniert: HeizungsWächter**)
oder per YAML:

```yaml
type: custom:heizungswaechter-card
```

Die Card findet ihre Sensoren **automatisch über die Geräte-Registry** – keine Konfiguration nötig.
Bei mehreren Heizungen oder Sonderfällen stehen Optionen bereit:

```yaml
type: custom:heizungswaechter-card
title: "Ölheizung Keller"     # eigenen Titel anzeigen
device: "HeizungsWächter"     # Geräte-Name oder -ID bei mehreren Anlagen
# Alternativ: Entities manuell zuweisen (überschreibt Auto-Erkennung)
entities:
  status: sensor.ofen_status
  temperatur: sensor.ofen_temperatur
  laufzeit_aktuell: sensor.ofen_laufzeit_aktuell
  # … weitere Suffixe: laufzeit_heute/monat/gesamt, kwh_*, kosten_*, taktungen_*, volumen_*
```

**Features der Card:** animierter Flammen-Status, live tickende Session-Laufzeit,
Kacheln für Heute / Monat / Gesamt, Brennstoffverbrauch, dunkel/hell-fähig via
HA-Theme-Variablen, responsiv (Container-Query), `prefers-reduced-motion`-Unterstützung.

### Card selbst bauen

Der React/Vite-Quellcode liegt in [`frontend/`](frontend/):

```bash
cd frontend
npm install
npm run build        # baut nach custom_components/heizungswaechter/www/
```

Das fertige `heizungswaechter-card.js` ist im Repo enthalten – Endnutzer brauchen
kein Node. Die Integration serviert die Datei unter
`/heizungswaechter/heizungswaechter-card.js` und lädt sie via `add_extra_js_url`.

---

## 📦 Installation via HACS

### Schritt 1 – Custom Repository hinzufügen

1. HACS öffnen → **Integrationen**
2. Oben rechts auf **⋮ (drei Punkte)** klicken
3. **"Eigene Repositories"** auswählen
4. Folgendes eintragen:
   - **URL:** `https://github.com/HatchetMan111/HeizungsWaechter`
   - **Kategorie:** `Integration`
5. **Hinzufügen** klicken

### Schritt 2 – Integration installieren

1. In HACS nach **"HeizungsWächter"** suchen
2. **Herunterladen** klicken
3. Home Assistant **neu starten**

### Schritt 3 – Einrichten

1. **Einstellungen → Geräte & Dienste → + Integration hinzufügen**
2. Nach **"HeizungsWächter"** suchen
3. Konfigurationsformular ausfüllen

Der Temperatursensor lässt sich später jederzeit unter
**Einstellungen → Geräte & Dienste → HeizungsWächter → Konfigurieren** ändern.

---

## 🧮 Verbrauchsberechnung

Die Brennerleistung vom Typenschild ist die **Nennwärmeleistung** (Abgabe).
Der Brennstoffverbrauch ergibt sich daraus über den Wirkungsgrad:

```
Verbrauch [kWh] = Leistung [kW] × Zeit [h] ÷ Wirkungsgrad
```

| Brennstoff | Heizwert | Beispielrechnung |
|-----------|---------|-----------------|
| Heizöl EL | ~10 kWh/L | 1,00 €/L ÷ 10 = **0,10 €/kWh** |
| Erdgas H | ~10 kWh/m³ | direkt in €/kWh angeben |
| Flüssiggas | ~12,8 kWh/kg | 1,50 €/kg ÷ 12,8 = **0,12 €/kWh** |
| Pellets | ~4,8 kWh/kg | 0,35 €/kg ÷ 4,8 = **0,07 €/kWh** |

---

## 🔩 Physische Installation

Das SONOFF SNZB-02LD IP65 Thermometer wird einfach in die vorhandene Messbohrung (Schornsteinfeger-Bohrung) im Ofenrohr gesteckt.

---

## 📋 Changelog

### 1.3.0
- 🖼️ **Neue Lovelace-Card** (React + Vite): automatische Entity-Erkennung, Live-Session-Ticker, Theme-Unterstützung
- 🐛 **Fix:** Integration lud nicht (`HeizungCoordinator` → `HeizungsWaechterCoordinator` Import-Fehler)
- 🐛 **Fix:** Verbrauchsformel korrigiert – `Leistung × Zeit ÷ Wirkungsgrad` statt `× Wirkungsgrad` (Kosten/Volumen waren zu niedrig)
- 🐛 **Fix:** Optionen-Flow auf HA ≥ 2024.11-Pattern umgestellt (`self.config_entry`, kein Konstruktor-Argument)
- ⚡ Zähler-Persistenz mit debounced Store-Writes (`async_delay_save`), verlässlich auch bei HA-Neustart
- ⚡ Brenner-Zustand wird persistiert – kein Phantom-„Brennerstart" mehr nach HA-Reboot mitten in der Brennphase
- ⚡ Minütlicher Takt: Tages-/Monats-Rollover und Session-Zeit laufen auch ohne Temperaturreports weiter
- ✨ Temperatursensor ist jetzt in den Optionen nachträglich änderbar
- ✨ Status-Sensor als `device_class: enum`, Device-Version aus zentraler Konstante

### 1.2.0
- Volumen-/Massesensoren je Brennstoff (L / m³ / kg), Erdgas mit `device_class: gas`

### 1.1.0
- Config-Flow, Optionen-Flow, Übersetzungen DE/EN

---

## 📄 Lizenz

MIT License – © 2024 [HatchetMan111](https://github.com/HatchetMan111)
