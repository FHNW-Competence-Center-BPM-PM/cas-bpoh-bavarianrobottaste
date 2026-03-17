# TODO

## Produkt und UX

- Brand-Story und Positionierung finalisieren
- Echte Speisekarte mit Kategorien, Preisen und Signature Dishes definieren
- Coole, visuell starke Menukarte fuer die Website konzipieren
- Testimonials als glaubwuerdige Demo-Inhalte schreiben und visuell integrieren
- Nutzerreise fuer Gast, registrierten Nutzer und Admin beschreiben
- Button-Hoehen im gesamten Frontend angleichen, sodass alle Buttons exakt gleich hoch sind

## Reservierung

- Tischreservierungsprozess definieren: Datum, Uhrzeit, Personenanzahl, Sonderwuensche
- Reservierungsstatus modellieren: angefragt, bestaetigt, storniert, erledigt
- Verfuegbare Zeitslots und Tischkapazitaeten planen
- Reservierungsformular im Frontend entwerfen
- Reservierungsservice mit Datenbankanbindung spezifizieren
- E-Mail-Bestaetigung und Erinnerungslogik fuer Reservierungen vorsehen
- Raumauswahl modellieren: 4 Raeume mit passenden Themen und eigenem Visualizer
- Regeln fuer Raeume festhalten: Raum 2 bis 4 standardmaessig durch Veranstaltungen blockiert
- Tischmodell fuer Raum 1 umsetzen: 2 Esstische bis 4 Personen, 1 Tisch fuer Trinken und Snacken mit 1 bis 2 Personen, 1 Tisch nur fuer Trinken mit 1 bis 2 Personen
- Kalenderfunktion fuer Reservierungen umsetzen
- Benachrichtigungen fuer Reservierungen vorsehen
- Loeschen von Reservierungen ermoeglichen
- QR-Code fuer jede Reservierung erzeugen
- Absagen nur bis 5 Stunden vor Termin erlauben
- Verwaltungslink fuer Reservierungen bereitstellen, auch fuer anonyme Reservierungen
- QR-Code-Scan an Webhook anbinden, damit ein Prozess gestartet werden kann

## Accounts und Auth

- User-Registrierung und Login einplanen
- Minimal-Registrierung festziehen: Vorname, E-Mail, Telefon optional
- Passwort-Reset und E-Mail-Verifikation als Folgefeatures aufnehmen
- Kundenkonto fuer Reservierungen, Bestellungen und Konsumhistorie definieren
- Rollenmodell klaeren: Gast, Kunde, Mitarbeiter, Admin
- Datenschutz- und Sicherheitsanforderungen fuer Kontodaten dokumentieren
- Login und Registrierung nochmals pruefen, damit Login nach gelungener Registrierung sicher funktioniert
- Passwort-Recovery umsetzen
- Kontaktaufnahmen im Profil eines Gastes anzeigen

## Bestellungen und Konsum

- Modell fuer Bestellungen und konsumierte Positionen definieren
- Speisen und Getraenke einem Account oder Tisch zuordnen koennen
- Konsumhistorie pro Account speichern
- Begleitgaeste pro Besuch modellieren und spaeter verknuepfbar halten
- Offene und abgeschlossene Orders unterscheiden
- Schnittstelle zwischen Speisekarte, Bestellung und Account planen
- Restaurantbesuche mit Datum und konsumierten Positionen im Gastprofil anzeigen

## Zahlung

- Zahlungsfluss fachlich beschreiben, auch wenn die erste Version nur Demo-Logik hat
- Konsumierte Leistungen einem Account nach Zahlung zuordnen
- Zahlungsstatus und Referenzen im Datenmodell vorsehen
- Historie fuer bezahlte und offene Betraege im Kundenkonto anzeigen
- Spaeteren Anschluss an echte Payment-Provider architektonisch vorbereiten
- APIs implementieren, um beim Bezahlen Konsumdaten aus einer Reservierung bzw. einem Tisch in das Profil einer Person zu pushen

## E-Mail und Kommunikation

- E-Mail-Service fuer Registrierung, Reservierung und Belegversand planen
- Template-Strategie fuer transaktionale E-Mails definieren
- Danke-Mail fuer Kontaktformular mit Registrierungslink vorbereiten
- Versandstatus, Fehlerfaelle und Retry-Logik dokumentieren
- Entscheidung treffen: Gmail SMTP fuer Prototyp oder Maildienst fuer Produktion
- `.env.example` fuer Mail-Konfiguration vorbereiten
- Absenderadresse, Empfaengerlogik und Mail-Trigger pro Use Case festlegen

## Architektur und Betrieb

- Docker-basierte Microservice-Architektur skizzieren
- Services schneiden: Frontend, Auth, CRM, Reservations, Orders, Payments, Notifications
- Gemeinsame Datenbankstrategie oder Service-Datenhoheit klaeren
- Lokale Entwicklungsumgebung mit Docker Compose planen
- API-Grenzen, Events und gemeinsame Identifikatoren festlegen
- Logging, Monitoring und Healthchecks in der Architektur vorsehen

## Content und Recht

- Bildmaterial erzeugen oder fotografieren
- Impressum und Datenschutz ergaenzen
- Fake-Testimonials intern klar als Demo-Content behandeln
- Inhalte fuer Kontakt, Team, Events und Anfahrt vorbereiten

## Delivery

- Frontend spaeter auf Framework-Basis migrieren
- Deployment-Strategie fuer Container definieren
- CI/CD fuer Build, Tests und Deployment vorbereiten
- SEO-Grundlagen und strukturierte Daten einfuehren
- Analytics und Monitoring ergaenzen
