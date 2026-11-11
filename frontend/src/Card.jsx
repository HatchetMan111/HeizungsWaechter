import React, { useEffect, useMemo, useRef, useState } from "react";

// Alle unique_id-Suffixe der Integration (unique_id = "<entry_id>_<suffix>")
const SUFFIXES = [
  "status",
  "temperatur",
  "laufzeit_aktuell",
  "laufzeit_heute",
  "laufzeit_monat",
  "laufzeit_gesamt",
  "kwh_heute",
  "kwh_monat",
  "kwh_gesamt",
  "kosten_heute",
  "kosten_monat",
  "kosten_gesamt",
  "taktungen_heute",
  "taktungen_monat",
  "taktungen_gesamt",
  "volumen_heute",
  "volumen_monat",
  "volumen_gesamt",
];

// ── Auto-Erkennung über die HA-Registries ────────────────────────────────────

async function discoverDevices(hass) {
  const [entities, devices] = await Promise.all([
    hass.callWS({ type: "config/entities/get" }),
    hass.callWS({ type: "config/device_registry/list" }),
  ]);

  const mine = entities.filter((e) => e.platform === "heizungswaechter");
  const byDevice = new Map();
  for (const e of mine) {
    const key = e.device_id || "_";
    if (!byDevice.has(key)) byDevice.set(key, {});
    const map = byDevice.get(key);
    const uid = e.unique_id || "";
    const idx = uid.indexOf("_");
    const suffix = idx >= 0 ? uid.slice(idx + 1) : uid;
    if (SUFFIXES.includes(suffix)) map[suffix] = e.entity_id;
  }

  const deviceById = new Map(devices.map((d) => [d.id, d]));
  return Array.from(byDevice.entries()).map(([id, map]) => {
    const dev = deviceById.get(id);
    return {
      id,
      map,
      name: dev?.name_by_user || dev?.name || "HeizungsWächter",
    };
  });
}

// ── Kleine Bausteine ─────────────────────────────────────────────────────────

function FlameIcon({ on }) {
  return (
    <svg
      className={`hw-flame${on ? " on" : ""}`}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z" />
    </svg>
  );
}

function TileRow({ title, tiles }) {
  return (
    <div className="hw-section">
      <div className="hw-section-title">{title}</div>
      <div className="hw-grid">
        {tiles.map((t) => (
          <div className="hw-tile" key={t.label}>
            <div className="hw-tile-label">{t.label}</div>
            <div className="hw-tile-value">{t.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Haupt-Card ───────────────────────────────────────────────────────────────

function Card({ hass, config }) {
  const [devices, setDevices] = useState(null);
  const [failed, setFailed] = useState(false);
  const [, forceTick] = useState(0);

  // Geräte-Erkennung: einmal beim Mounten
  useEffect(() => {
    let alive = true;
    discoverDevices(hass)
      .then((d) => {
        if (alive) {
          setDevices(d);
          setFailed(false);
        }
      })
      .catch(() => {
        if (alive) setFailed(true);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sekundentakt für die laufende Brenner-Session
  useEffect(() => {
    const id = setInterval(() => forceTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  // Manuell konfigurierte Entities überschreiben die Auto-Erkennung
  const manual = config.entities && typeof config.entities === "object" ? config.entities : null;

  const device = useMemo(() => {
    if (!devices || devices.length === 0) return null;
    if (config.device) {
      const found = devices.find(
        (d) => d.name === config.device || d.id === config.device
      );
      if (found) return found;
    }
    return devices[0];
  }, [devices, config.device]);

  const entityMap = manual || (device && device.map) || {};

  const get = (suffix) => {
    const entityId = entityMap[suffix];
    if (!entityId) return null;
    const s = hass.states[entityId];
    if (!s || s.state === "unknown" || s.state === "unavailable") return null;
    return s;
  };

  const num = (suffix) => {
    const s = get(suffix);
    if (!s) return null;
    const n = parseFloat(s.state);
    return Number.isFinite(n) ? n : null;
  };

  const unitOf = (suffix) => {
    const s = get(suffix);
    return (s && s.attributes && s.attributes.unit_of_measurement) || "";
  };

  const lang = hass.language || "de";
  const nf = (value, digits) =>
    new Intl.NumberFormat(lang, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(value);

  const fmtMinutes = (mins) => {
    if (mins == null) return "–";
    if (mins < 60) return `${nf(mins, 0)} min`;
    const h = Math.floor(mins / 60);
    const m = Math.round(mins % 60);
    return `${nf(h, 0)} h ${nf(m, 0)} min`;
  };

  const fmtHours = (hours) => {
    if (hours == null) return "–";
    if (hours < 10) return `${nf(hours, 1)} h`;
    return `${nf(hours, 0)} h`;
  };

  const fmtSession = (sec) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    return `${m}:${String(s).padStart(2, "0")} min`;
  };

  const statusRaw = get("status");
  const hasStatusEntity = Boolean(entityMap.status);
  const burnerOn = Boolean(statusRaw && statusRaw.state === "AN");
  const sensorOffline = hasStatusEntity && !statusRaw;

  const temp = num("temperatur");
  const threshold =
    statusRaw && statusRaw.attributes
      ? statusRaw.attributes["schwellwert_°C"]
      : null;

  // Laufende Session: Basis aus dem Sensor, Sekunden lokal weiterlaufen lassen
  const sessionSensor = num("laufzeit_aktuell");
  const lastSessionVal = useRef(null);
  const [sessionBase, setSessionBase] = useState({ base: 0, at: Date.now() });

  useEffect(() => {
    if (burnerOn && sessionSensor !== null) {
      if (sessionSensor !== lastSessionVal.current) {
        lastSessionVal.current = sessionSensor;
        setSessionBase({ base: sessionSensor * 60, at: Date.now() });
      }
    } else if (!burnerOn) {
      lastSessionVal.current = null;
      setSessionBase({ base: 0, at: Date.now() });
    }
  }, [burnerOn, sessionSensor]);

  const sessionSec = burnerOn
    ? Math.max(
        0,
        sessionBase.base + (Date.now() - sessionBase.at) / 1000
      )
    : 0;

  // Kachel-Zeilen
  const kwhToday = num("kwh_heute");
  const costToday = num("kosten_heute");
  const cyclesToday = num("taktungen_heute");
  const runtimeToday = num("laufzeit_heute");

  const kwhMonth = num("kwh_monat");
  const costMonth = num("kosten_monat");
  const cyclesMonth = num("taktungen_monat");
  const runtimeMonth = num("laufzeit_monat");

  const kwhTotal = num("kwh_gesamt");
  const costTotal = num("kosten_gesamt");
  const cyclesTotal = num("taktungen_gesamt");
  const runtimeTotal = num("laufzeit_gesamt");

  const volToday = num("volumen_heute");
  const volMonth = num("volumen_monat");
  const volUnit = unitOf("volumen_heute") || unitOf("volumen_monat");

  const tilesToday = [
    { label: "Laufzeit", value: fmtMinutes(runtimeToday) },
    { label: "Energie", value: kwhToday == null ? "–" : `${nf(kwhToday, 2)} kWh` },
    { label: "Kosten", value: costToday == null ? "–" : `${nf(costToday, 2)} €` },
    { label: "Starts", value: cyclesToday == null ? "–" : nf(cyclesToday, 0) },
  ];

  const tilesMonth = [
    { label: "Laufzeit", value: fmtHours(runtimeMonth) },
    { label: "Energie", value: kwhMonth == null ? "–" : `${nf(kwhMonth, 2)} kWh` },
    { label: "Kosten", value: costMonth == null ? "–" : `${nf(costMonth, 2)} €` },
    { label: "Starts", value: cyclesMonth == null ? "–" : nf(cyclesMonth, 0) },
  ];

  const tilesTotal = [
    { label: "Laufzeit", value: fmtHours(runtimeTotal) },
    { label: "Energie", value: kwhTotal == null ? "–" : `${nf(kwhTotal, 2)} kWh` },
    { label: "Kosten", value: costTotal == null ? "–" : `${nf(costTotal, 2)} €` },
    { label: "Starts", value: cyclesTotal == null ? "–" : nf(cyclesTotal, 0) },
  ];

  // Zustände: laden / fehlgeschlagen / keine Geräte.
  // Bei manuell konfigurierten Entities ist keine Auto-Erkennung nötig.
  if (failed && !manual) {
    return (
      <ha-card>
        <div className="hw-error">
          HeizungsWächter-Card konnte die Entities nicht laden.
          <br />
          Alternativ manuell setzen:
          <br />
          <code>entities: {`{ status: sensor.…, … }`}</code>
        </div>
      </ha-card>
    );
  }

  if (!devices && !manual) {
    return (
      <ha-card>
        <div className="hw-placeholder">Lade HeizungsWächter-Konfiguration…</div>
      </ha-card>
    );
  }

  if (devices && devices.length === 0 && !manual) {
    return (
      <ha-card>
        <div className="hw-placeholder">
          Kein HeizungsWächter-Gerät gefunden.
          <br />
          Integration unter Einstellungen → Geräte &amp; Dienste einrichten.
        </div>
      </ha-card>
    );
  }

  const title = config.title || (device && device.name) || "HeizungsWächter";

  return (
    <ha-card>
      <div className="hw-body">
        <div className="hw-header">
          <div className="hw-title">
            <FlameIcon on={burnerOn} />
            <span>{title}</span>
          </div>
          <div
            className={`hw-chip${burnerOn ? " on" : ""}${
              sensorOffline ? " offline" : ""
            }`}
          >
            <span className="hw-dot" />
            {sensorOffline ? "Sensor offline" : burnerOn ? "Brennt" : "Aus"}
          </div>
        </div>

        <div className="hw-temp-row">
          <div className="hw-temp">
            <span className="hw-temp-value">
              {temp == null ? "–" : nf(temp, 1)}
            </span>
            <span className="hw-temp-unit">°C</span>
          </div>
          <div className="hw-temp-info">
            <div className="hw-temp-label">Ofenrohr</div>
            {threshold != null && (
              <div className="hw-sub">Schwellwert {nf(threshold, 0)} °C</div>
            )}
            {burnerOn && (
              <div className="hw-session">Brennt seit {fmtSession(sessionSec)}</div>
            )}
          </div>
        </div>

        <TileRow title="Heute" tiles={tilesToday} />
        <TileRow title="Monat" tiles={tilesMonth} />
        <TileRow title="Gesamt" tiles={tilesTotal} />

        <div className="hw-footer">
          <span>
            Brennstoff heute:{" "}
            <strong>
              {volToday == null
                ? "–"
                : `${nf(volToday, 1)} ${volUnit}`.trim()}
            </strong>
          </span>
          <span>
            Monat:{" "}
            <strong>
              {volMonth == null
                ? "–"
                : `${nf(volMonth, 1)} ${volUnit}`.trim()}
            </strong>
          </span>
        </div>
      </div>
    </ha-card>
  );
}

export default Card;
