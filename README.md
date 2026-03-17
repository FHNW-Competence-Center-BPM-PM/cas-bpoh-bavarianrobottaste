# Bavarian RoboTaste

Projektbasis fur eine Restaurant-Website der Konzeptmarke **Bavarian RoboTaste**.
Die erste Version ist bewusst leichtgewichtig aufgebaut: statisches HTML, CSS und
JavaScript ohne Build-Schritt. Dadurch laesst sich das Projekt sofort lokal oeffnen,
schnell iterieren und spaeter sauber zu einer vollwertigen Plattform mit Frontend,
Microservices, Datenbank, Reservierungen, Bestellungen und Bezahlbezug erweitern.

## Projektziele

- Eine markante Startseite fur ein futuristisch-bayerisches Restaurant
- Solide Projektstruktur fur Inhalte, Design und spaetere Features
- Dokumentation fur Architektur, Bildideen, Prompts und offene Aufgaben
- Git-Repository als Ausgangspunkt fuer Versionierung und Zusammenarbeit
- Zielbild fur eine produktionsnahe Restaurantplattform mit Accounts, Reservierungen,
  Bestellungen, E-Mail-Kommunikation und Zahlungszuordnung

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
    |-- API.md
    |-- CRM.md
    |-- IMAGES.md
    |-- PROMPTS.md
    `-- TODO.md
```

## Dokumentation

- Architektur: [docs/ARCHITECTURE.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/ARCHITECTURE.md)
- API-Vorbereitung: [docs/API.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/API.md)
- CRM- und Gastmodell: [docs/CRM.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/CRM.md)
- Bildkonzept: [docs/IMAGES.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/IMAGES.md)
- Prompt-Sammlung: [docs/PROMPTS.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/PROMPTS.md)
- Roadmap und Aufgaben: [docs/TODO.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/TODO.md)
- E-Mail-Strategie: [docs/EMAIL.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/EMAIL.md)

## Naechste sinnvolle Ausbaustufen

- Tischreservierung mit Zeitfenstern, Personenanzahl und Statusverwaltung
- Nutzerkonto mit Registrierung, Login und Historie
- E-Mail-Versand fur Reservierungsbestaetigungen und Account-bezogene Nachrichten
- Bestell- und Konsumtracking pro Nutzerkonto
- Zahlungsbezug, damit konsumierte Positionen einem Account zugeordnet werden
- Docker-basierte Microservice-Architektur mit Datenbank
- Erweiterte Website-Inhalte: interaktive Menukarte und Testimonials
- Mail-Entscheidung vorbereiten: Gmail SMTP fuer Prototyp oder spaeter Maildienst

## Produkt-Roadmap in Kurzform

- Frontend
  - Landingpage zu einer mehrseitigen Erlebnis-Website ausbauen
  - Menukarte visuell hochwertig und dynamisch pflegbar machen
  - Testimonials, Reservierungsflow und Account-Bereich ergaenzen
- Backend
  - Reservierungsservice, Auth-Service, Order-Service und Notification-Service planen
  - Persistenz fuer Nutzer, Reservierungen, Orders, Zahlungen und E-Mail-Events
- Betrieb
  - Services per Docker Compose lokal starten
  - Spaeter CI, Tests, Deployment und Observability aufsetzen
