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
| ⚡ Verbrauch Heute / Monat / Gesamt | kWh | Berechneter Energieverbrauch |
| 💶 Kosten Heute / Monat / Gesamt | € | Heizkosten in Euro |
| 🔁 Brennerstarts Heute / Monat / Gesamt | Starts | Taktungszähler |

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

---

## 💡 Brennstoffpreis berechnen

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

## 📄 Lizenz

MIT License – © 2024 [HatchetMan111](https://github.com/HatchetMan111)
