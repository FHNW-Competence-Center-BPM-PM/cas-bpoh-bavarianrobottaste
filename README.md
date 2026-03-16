# Bavarian RoboTaste

Projektbasis fur eine Restaurant-Website der Konzeptmarke **Bavarian RoboTaste**.
Die erste Version ist bewusst leichtgewichtig aufgebaut: statisches HTML, CSS und
JavaScript ohne Build-Schritt. Dadurch laesst sich das Projekt sofort lokal oeffnen,
schnell iterieren und spaeter sauber auf React, Next.js oder ein CMS erweitern.

## Projektziele

- Eine markante Startseite fur ein futuristisch-bayerisches Restaurant
- Solide Projektstruktur fur Inhalte, Design und spaetere Features
- Dokumentation fur Architektur, Bildideen, Prompts und offene Aufgaben
- Git-Repository als Ausgangspunkt fuer Versionierung und Zusammenarbeit

## Schnellstart

1. Repository ist bereits initialisiert.
2. `index.html` direkt im Browser oeffnen oder lokal einen einfachen Server starten:

```powershell
py -m http.server 8080
```

3. Danach im Browser `http://localhost:8080` oeffnen.

## Projektstruktur

```text
.
|-- index.html
|-- styles/
|   `-- main.css
|-- scripts/
|   `-- main.js
`-- docs/
    |-- ARCHITECTURE.md
    |-- IMAGES.md
    |-- PROMPTS.md
    `-- TODO.md
```

## Dokumentation

- Architektur: [docs/ARCHITECTURE.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/ARCHITECTURE.md)
- Bildkonzept: [docs/IMAGES.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/IMAGES.md)
- Prompt-Sammlung: [docs/PROMPTS.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/PROMPTS.md)
- Roadmap und Aufgaben: [docs/TODO.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/TODO.md)

## Naechste sinnvolle Ausbaustufen

- Reservierungsformular mit echtem Versand oder API-Anbindung
- Speisekarte als CMS- oder JSON-Datenquelle
- Bildergalerie und Event-Seite
- Mehrsprachigkeit in Deutsch und Englisch
- Deployment, CI und automatisierte Qualitaetschecks

