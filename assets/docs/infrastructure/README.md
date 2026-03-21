# Infrastruktur-Overlay-Daten

Die Dateien in diesem Ordner enthalten die Inhalte fuer die interaktiven Overlays der beiden Infrastruktur-Grafiken.

Dateien:
- `hw-network-overlays.json`
- `services-overlays.json`

## Aufbau

Jede Datei hat diese Grundstruktur:

```json
{
  "view": "hw-network",
  "title": "HW & Netzwerk",
  "description": "Kurzbeschreibung der Datei",
  "hotspots": [
    {
      "id": "vm-cas-bpoh",
      "title": "Titel im Overlay",
      "text": "Freitext fuer die Hauptbeschreibung",
      "meta": [
        {
          "label": "Typ",
          "value": "Cloud / VM"
        }
      ]
    }
  ]
}
```

## Regeln

- `id` muss exakt zur Hotspot-ID im Frontend passen.
- `title` ist die Ueberschrift im Overlay.
- `text` ist der Haupttext.
- `meta` ist eine Liste aus Label/Wert-Paaren fuer Zusatzinfos.
- Die Reihenfolge der `hotspots` ist frei, wichtig ist nur die passende `id`.

## Aktuelle Hotspot-IDs

`hw-network-overlays.json`
- `vm-cas-bpoh`
- `kassensystem`
- `raspberry-pi`
- `unitree-g1`
- `hue-hub`
- `hue-light-strips`
- `hue-lampe`
- `tablet-cluster`

`services-overlays.json`
- `camunda`
- `n8n`
- `power-automate`
- `crm`
- `erp-ready2order`
- `ngrok-traefik`
- `hue-rest-api`
- `g1-api`

## Naechster Schritt

Der naechste sinnvolle Schritt ist, `scripts/main.js` so umzustellen, dass die Overlay-Texte nicht mehr hart im Code stehen, sondern direkt aus diesen JSON-Dateien geladen werden.
