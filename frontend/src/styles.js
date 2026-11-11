// Styles für die Shadow-DOM der Card.
// Verwendet HA-Theme-Variablen, damit die Card in hell/dunkel und
// jedem Theme automatisch passt.
const STYLES = `
:host {
  display: block;
}

ha-card {
  padding: 14px 16px 12px;
  color: var(--primary-text-color);
  --hw-accent: #ff7a3d;
  --hw-accent-dim: rgba(255, 122, 61, 0.16);
  --hw-good: var(--state-icon-color, #4caf50);
  --hw-muted: var(--secondary-text-color, #8b949e);
}

.hw-body {
  container-type: inline-size;
}

/* ── Kopfzeile ─────────────────────────────────────────────── */
.hw-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.hw-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05em;
  font-weight: 600;
  letter-spacing: 0.01em;
  min-width: 0;
}

.hw-title span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hw-flame {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  fill: var(--hw-muted);
  transition: fill 0.4s ease;
}

.hw-flame.on {
  fill: var(--hw-accent);
  animation: hw-flicker 1.6s ease-in-out infinite;
}

@keyframes hw-flicker {
  0%, 100% { transform: scale(1); opacity: 0.95; }
  30%      { transform: scale(1.07); opacity: 1; }
  60%      { transform: scale(0.97); opacity: 0.88; }
}

@media (prefers-reduced-motion: reduce) {
  .hw-flame.on { animation: none; }
}

.hw-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.78em;
  font-weight: 600;
  background: var(--secondary-background-color, #eceff1);
  color: var(--hw-muted);
  white-space: nowrap;
}

.hw-chip .hw-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.hw-chip.on {
  background: var(--hw-accent-dim);
  color: var(--hw-accent);
}

.hw-chip.on .hw-dot {
  animation: hw-pulse 1.6s ease-in-out infinite;
}

.hw-chip.offline {
  background: var(--error-color, #f44336);
  color: #fff;
}

@keyframes hw-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.35; }
}

/* ── Temperatur ────────────────────────────────────────────── */
.hw-temp-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 2px 12px;
}

.hw-temp {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.hw-temp-value {
  font-size: 2.2em;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.hw-temp-unit {
  font-size: 1em;
  font-weight: 600;
  color: var(--hw-muted);
}

.hw-temp-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.hw-temp-label {
  font-size: 0.85em;
  color: var(--hw-muted);
}

.hw-sub {
  font-size: 0.8em;
  color: var(--hw-muted);
}

.hw-session {
  font-size: 0.85em;
  font-weight: 600;
  color: var(--hw-accent);
  font-variant-numeric: tabular-nums;
}

/* ── Sektionen / Kacheln ───────────────────────────────────── */
.hw-section {
  padding-top: 8px;
}

.hw-section-title {
  font-size: 0.72em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--hw-muted);
  margin-bottom: 6px;
}

.hw-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.hw-tile {
  background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
  border-radius: 10px;
  padding: 8px 10px;
  min-width: 0;
}

.hw-tile-label {
  font-size: 0.72em;
  color: var(--hw-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hw-tile-value {
  font-size: 1.02em;
  font-weight: 700;
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@container (max-width: 360px) {
  .hw-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* ── Fußzeile ──────────────────────────────────────────────── */
.hw-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
  font-size: 0.78em;
  color: var(--hw-muted);
  flex-wrap: wrap;
}

.hw-footer strong {
  color: var(--primary-text-color);
  font-weight: 600;
}

/* ── Zustände: Laden / Fehler / leer ───────────────────────── */
.hw-placeholder {
  padding: 20px 4px;
  text-align: center;
  color: var(--hw-muted);
  font-size: 0.9em;
}

.hw-error {
  padding: 16px 4px;
  text-align: center;
  color: var(--error-color, #f44336);
  font-size: 0.9em;
}
`;

export default STYLES;
