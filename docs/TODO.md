# TODO

## Produkt und UX

- [ ] Brand-Story und Positionierung finalisieren
- [ ] Echte Speisekarte mit Kategorien, Preisen und Signature Dishes definieren
- [x] Coole, visuell starke Menükarte für die Website konzipieren
- [ ] Testimonials als glaubwürdige Demo-Inhalte schreiben und visuell integrieren
- [ ] Nutzerreise für Gast, registrierten Nutzer und Admin beschreiben
- [ ] Button-Höhen im gesamten Frontend angleichen, sodass alle Buttons exakt gleich hoch sind

## Reservierung

- [ ] Tischreservierungsprozess definieren: Datum, Uhrzeit, Personenanzahl, Sonderwünsche
- [ ] Reservierungsstatus modellieren: angefragt, bestätigt, storniert, erledigt
- [ ] Verfügbare Zeitslots und Tischkapazitäten planen
- [x] Reservierungsformular im Frontend entwerfen
- [ ] Reservierungsservice mit Datenbankanbindung spezifizieren
- [ ] E-Mail-Bestätigung und Erinnerungslogik für Reservierungen vorsehen
- [ ] Raumauswahl modellieren: 4 Räume mit passenden Themen und eigenem Visualizer
- [ ] Regeln für Räume festhalten: Raum 2 bis 4 standardmäßig durch Veranstaltungen blockiert
- [ ] Tischmodell für Raum 1 umsetzen: 2 Esstische bis 4 Personen, 1 Tisch für Trinken und Snacken mit 1 bis 2 Personen, 1 Tisch nur für Trinken mit 1 bis 2 Personen
- [ ] Kalenderfunktion für Reservierungen umsetzen
- [ ] Benachrichtigungen für Reservierungen vorsehen
- [ ] Löschen von Reservierungen ermöglichen
- [ ] QR-Code für jede Reservierung erzeugen
- [ ] Absagen nur bis 5 Stunden vor Termin erlauben
- [ ] Verwaltungslink für Reservierungen bereitstellen, auch für anonyme Reservierungen
- [ ] QR-Code-Scan an Webhook anbinden, damit ein Prozess gestartet werden kann

## Accounts und Auth

- [x] User-Registrierung und Login einplanen
- [x] Minimal-Registrierung festziehen: Vorname, E-Mail, Telefon optional
- [ ] Passwort-Reset und E-Mail-Verifikation als Folgefeatures aufnehmen
- [x] Kundenkonto für Reservierungen, Bestellungen und Konsumhistorie definieren
- [ ] Rollenmodell klären: Gast, Kunde, Mitarbeiter, Admin
- [ ] Datenschutz- und Sicherheitsanforderungen für Kontodaten dokumentieren
- [x] Login und Registrierung nochmals prüfen, damit Login nach gelungener Registrierung sicher funktioniert
- [ ] Passwort-Recovery umsetzen
- [ ] Kontaktaufnahmen im Profil eines Gastes anzeigen

## Bestellungen und Konsum

- [x] Modell für Bestellungen und konsumierte Positionen definieren
- [ ] Speisen und Getränke einem Account oder Tisch zuordnen können
- [ ] Konsumhistorie pro Account speichern
- [x] Begleitgäste pro Besuch modellieren und später verknüpfbar halten
- [ ] Offene und abgeschlossene Orders unterscheiden
- [x] Schnittstelle zwischen Speisekarte, Bestellung und Account planen
- [ ] Restaurantbesuche mit Datum und konsumierten Positionen im Gastprofil anzeigen

## Zahlung

- [ ] Zahlungsfluss fachlich beschreiben, auch wenn die erste Version nur Demo-Logik hat
- [ ] Konsumierte Leistungen einem Account nach Zahlung zuordnen
- [ ] Zahlungsstatus und Referenzen im Datenmodell vorsehen
- [ ] Historie für bezahlte und offene Beträge im Kundenkonto anzeigen
- [ ] Späteren Anschluss an echte Payment-Provider architektonisch vorbereiten
- [ ] APIs implementieren, um beim Bezahlen Konsumdaten aus einer Reservierung bzw. einem Tisch in das Profil einer Person zu pushen

## E-Mail und Kommunikation

- [x] E-Mail-Service für Registrierung, Reservierung und Belegversand planen
- [x] Template-Strategie für transaktionale E-Mails definieren
- [x] Danke-Mail für Kontaktformular mit Registrierungslink vorbereiten
- [ ] Versandstatus, Fehlerfälle und Retry-Logik dokumentieren
- [x] Entscheidung treffen: Gmail SMTP für Prototyp oder Maildienst für Produktion
- [x] `.env.example` für Mail-Konfiguration vorbereiten
- [x] Absenderadresse, Empfängerlogik und Mail-Trigger pro Use Case festlegen

## Architektur und Betrieb

- [x] Docker-basierte Microservice-Architektur skizzieren
- [x] Services schneiden: Frontend, Auth, CRM, Reservations, Orders, Payments, Notifications
- [ ] Gemeinsame Datenbankstrategie oder Service-Datenhoheit klären
- [x] Lokale Entwicklungsumgebung mit Docker Compose planen
- [x] API-Grenzen, Events und gemeinsame Identifikatoren festlegen
- [ ] Logging, Monitoring und Healthchecks in der Architektur vorsehen

## Content und Recht

- [x] Bildmaterial erzeugen oder fotografieren
- [x] Impressum ergänzen
- [ ] Datenschutz ergänzen
- [ ] Fake-Testimonials intern klar als Demo-Content behandeln
- [ ] Inhalte für Kontakt, Team, Events und Anfahrt vorbereiten

## Delivery

- [ ] Frontend später auf Framework-Basis migrieren
- [ ] Deployment-Strategie für Container definieren
- [ ] CI/CD für Build, Tests und Deployment vorbereiten
- [ ] SEO-Grundlagen und strukturierte Daten einführen
- [ ] Analytics und Monitoring ergänzen
