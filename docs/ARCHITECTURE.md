# Architektur

## Zielbild

Die erste Projektversion ist eine statische Brand- und Landingpage fur das Restaurant
**Bavarian RoboTaste**. Die Struktur ist absichtlich klein gehalten, damit Inhalte,
Design und Markensprache zuerst schnell entwickelt werden koennen.

Das Zielbild wurde nun erweitert: Aus der Brand-Seite soll eine Restaurantplattform
mit folgenden Kernfunktionen entstehen:

- Tischreservierung
- Nutzerregistrierung und Login
- E-Mail-Versand fur transaktionale Nachrichten
- Bestellung und Konsumtracking pro Account
- Zahlungszuordnung zu einem Kundenkonto
- Docker-basierter Betrieb als Microservice-System mit Datenbank

## Bausteine

- `index.html`
  - semantische Seitenstruktur mit Hero, Konzept, Menu, Erlebnis und Kontakt
- `styles/main.css`
  - Design-Tokens per CSS-Variablen
  - responsive Layouts mit Grid
  - visuelle Richtung aus warmen Naturtoenen und futuristischen Akzenten
- `scripts/main.js`
  - kleines Enhancement fur Scroll-Reveal-Animationen
- `docs/*`
  - Projektwissen, Bildideen, Prompts und Roadmap

## Zielarchitektur Phase 2+

Vorgeschlagene Zielstruktur:

- `frontend`
  - Website, Menukarte, Testimonials, Reservierung, Login, Kundenkonto
- `services/auth`
  - Registrierung, Login, Session oder Token-Verwaltung
- `services/crm`
  - Kontaktanfragen, Leads, Gastprofile und spaetere CRM-Sichten
- `services/reservations`
  - Tischreservierungen, Zeitslots, Personenanzahl, Statusmodell
- `services/orders`
  - Bestellungen, konsumierte Positionen, Zuordnung zu Nutzerkonten
- `services/payments`
  - Zahlungsstatus, Zahlungsreferenzen, Zuordnung zur Konsumhistorie
- `services/notifications`
  - E-Mail-Versand fur Reservierungen, Registrierung und Belege
- `database`
  - relationale Hauptdatenbank, z. B. PostgreSQL
- `infra`
  - Docker Compose, lokale Entwicklungsumgebung, spaeter CI/CD

## Architekturentscheidungen

- Kein Framework in Phase 1
  - Vorteil: null Setup, schnell editierbar, sofort deploybar
- Keine externen UI-Abhaengigkeiten
  - Vorteil: volle gestalterische Kontrolle und geringe Komplexitaet
- Dokumentation direkt im Repo
  - Vorteil: Marke, Inhalte und Technik bleiben in einer gemeinsamen Quelle
- Microservice-Zielbild erst nach stabiler Produktdefinition umsetzen
  - Vorteil: keine vorschnelle technische Komplexitaet vor validierten Anforderungen
- Account- und Zahlungsdaten strikt serverseitig modellieren
  - Vorteil: bessere Nachvollziehbarkeit, Sicherheit und spaetere Erweiterbarkeit

## Domainen und Datenobjekte

- `User`
  - Profil, Kontaktinformationen, Login-Daten, Rollen
- `ContactLead`
  - Kontaktanfrage, Kanal, Nachricht, Status, spaetere Konvertierung zu Gastprofil
- `GuestProfile`
  - registrierter Gast, Kontaktkanal, optionale Telefonnummer, CRM-Verknuepfung
- `Reservation`
  - Datum, Uhrzeit, Anzahl Personen, Status, Sonderwuensche, Benutzerbezug
- `Visit`
  - konkreter Restaurantbesuch, Tisch, Gruppenkontext, Reservierungsbezug
- `VisitGuest`
  - Begleitgaeste eines Besuchs, optional mit spaeterer Profilverknuepfung
- `MenuItem`
  - Name, Kategorie, Preis, Beschreibung, Verfuegbarkeit
- `Order`
  - Positionen, Mengen, Status, Tischbezug, Benutzerbezug
- `ConsumptionLedger`
  - sammelt konsumierte Leistungen pro Account
- `Payment`
  - Betrag, Status, Referenz, Zeitstempel, Order- oder Ledger-Bezug
- `EmailEvent`
  - Empfaenger, Template, Versandstatus, Fehlerdetails

## E-Mail-Architektur

Der E-Mail-Versand sollte als eigener Baustein gedacht werden, auch wenn der erste
Prototyp technisch noch direkt aus einem Backend-Service senden kann.

Empfohlene Stufen:

- Phase 1
  - lokaler Prototyp via Gmail SMTP
  - Versand aus einem einfachen Notification-Service
- Phase 2
  - Umstieg auf dedizierten Maildienst wie Resend oder Postmark
  - Webhooks für Zustellung, Fehler und Bounces
  - klar versionierte Templates

Benötigte Konfiguration:

- Absenderadresse
- SMTP- oder API-Credentials
- Template-Namen
- Empfängerlogik je Use Case
- sichere Secret-Ablage via `.env` oder Docker-Secrets

Wichtige Mail-Use-Cases:

- Reservierungsbestätigung
- Reservierungserinnerung
- Kontaktbestaetigung mit Registrierungslink
- Registrierung
- E-Mail-Verifikation
- Passwort-Reset
- Kontaktformular
- Zahlungsbeleg

Siehe auch: [docs/EMAIL.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/EMAIL.md)

## CRM- und Registrierungsfluss

Empfohlene erste Stufen:

- Kontaktformular erzeugt `ContactLead`
- Camunda oder ein Backend-Workflow stoest interne Weiterleitung und Danke-Mail an
- Danke-Mail enthaelt einen Registrierungslink
- Registrierung legt `GuestProfile` an
- spaetere Besuche und konsumierte Artikel werden an das `GuestProfile` gehaengt

Siehe auch: [docs/CRM.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/CRM.md)
Siehe auch: [docs/API.md](/c:/Users/achim.dannecker/source/repos/BavarianRoboTaste/docs/API.md)

## Technische Leitlinien fuer den Ausbau

- Frontend auf `Next.js`, `Astro` oder aehnliches SSR/Hybrid-Framework migrieren
- API-Schnittstellen klar nach Domainen trennen statt frueh alles in einem Monolithen zu mischen
- Headless CMS optional nur fur redaktionelle Inhalte wie Menu, Events und Testimonials
- Formular- und Account-Prozesse ueber serverseitige APIs und persistente Datenhaltung abbilden
- Docker Compose fuer lokale Entwicklung nutzen, spaeter Container-Orchestrierung evaluieren
- Bildoptimierung, SEO-Metadaten, Analytics, Monitoring und Logging frueh mitdenken
- Tests fuer API-Flows, Auth, Reservierungen und Bezahlzuordnung einplanen

## Inhaltsmodule fuer spaeter

- Startseite
- Speisekarte
- Reservierung
- Login / Registrierung
- Kundenkonto mit Reservierungen, Bestellungen und Zahlungsverlauf
- Event-Abende
- Testimonials
- Team / Story
- Presse / Galerie
- Kontakt / Anfahrt
