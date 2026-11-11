import React from "react";
import { createRoot } from "react-dom/client";
import Card from "./Card.jsx";
import STYLES from "./styles.js";

const CARD_TYPE = "heizungswaechter-card";

// Lovelace-Card-Registrierung im Karten-Auswahlmenü
window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_TYPE,
  name: "HeizungsWächter",
  description:
    "Heizungs-Monitor: Brenner-Status, Ofenrohr-Temperatur, Laufzeit, Verbrauch, Kosten und Taktungen",
  preview: true,
});

class HeizungsWaechterCard extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = {};
    this._shadow = null;
    this._reactRoot = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  get hass() {
    return this._hass;
  }

  setConfig(config) {
    this._config =
      typeof config === "string" ? JSON.parse(config) : config || {};
    this._mount();
    this._render();
  }

  connectedCallback() {
    // Falls setConfig vor dem Einhängen kam, ist schon gemountet;
    // sonst jetzt mounten, damit hass sofort rendern kann.
    if (!this._reactRoot) {
      this._mount();
      this._render();
    }
  }

  _mount() {
    if (this._reactRoot) return;
    this._shadow = this.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = STYLES;
    this._shadow.appendChild(style);
    const container = document.createElement("div");
    this._shadow.appendChild(container);
    this._reactRoot = createRoot(container);
  }

  _render() {
    if (!this._reactRoot || !this._hass) return;
    this._reactRoot.render(
      React.createElement(Card, {
        hass: this._hass,
        config: this._config,
      })
    );
  }

  getCardSize() {
    return 6;
  }

  // Sowohl statisch als auch am Objekt: je nach HA-Version fragt der
  // Sections-Editor die Klassen- oder Objektmethode ab.
  static getGridOptions() {
    return { columns: 6, min_columns: 4, rows: 7, min_rows: 6 };
  }

  getGridOptions() {
    return HeizungsWaechterCard.getGridOptions();
  }

  static getStubConfig() {
    return {};
  }
}

customElements.define(CARD_TYPE, HeizungsWaechterCard);
