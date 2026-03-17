# E-Mail-Versand

## Ziel

Der E-Mail-Versand wird fuer diese Produktfluesse benoetigt:

- Reservierungsbestaetigung
- Reservierungserinnerung
- Kontaktbestaetigung mit Registrierungslink
- Registrierung
- E-Mail-Verifikation
- Passwort-Reset
- Kontaktformular
- Zahlungsbeleg
- interne Benachrichtigungen an das Restaurant

## Grundsaetzliche Optionen

### 1. Gmail per SMTP

Geeignet fuer:

- ersten Prototyp
- interne Tests
- kleine manuelle Ablaeufe

Benoetigt:

- Gmail-Adresse als Absender
- aktivierte Zwei-Faktor-Authentifizierung
- Google App-Passwort
- SMTP-Zugangsdaten in `.env` oder Docker-Secrets

Typische Variablen:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=restaurant@example.com
SMTP_PASS=app-passwort
MAIL_FROM="Bavarian RoboTaste <restaurant@example.com>"
```

Hinweise:

- normales Google-Passwort reicht nicht
- App-Passwort funktioniert nur mit aktivierter Zwei-Faktor-Authentifizierung
- fuer Produktion ist SMTP mit Gmail eher begrenzt

### 2. Gmail API / Google Workspace API

Geeignet fuer:

- technisch sauberere Google-Integration
- kontrolliertere Authentifizierung
- professionellere Google-basierte Zustellung

Benoetigt:

- Google-Cloud-Projekt
- aktivierte Gmail API
- OAuth-Client oder passende Server-Strategie
- Credentials
- definierte Absenderidentitaet

Zusaetzliche Punkte:

- Token-Handling
- sichere Secret-Ablage
- Erneuerung von Credentials
- saubere Freigabe der benoetigten Scopes

### 3. Dedizierter Maildienst

Empfohlene Kandidaten:

- Resend
- Postmark
- SendGrid

Geeignet fuer:

- Transaktionsmails in Produktion
- bessere Zustellbarkeit
- Webhooks fuer Status und Fehler
- klare Trennung zwischen Produktlogik und Mail-Infrastruktur

Empfehlung fuer Bavarian RoboTaste:

- kurzzeitig `Gmail SMTP` fuer einen lokalen Prototyp
- spaeter Wechsel auf `Resend` oder `Postmark` fuer produktionsnahe Transaktionsmails

## Was konkret vorbereitet werden muss

### Fachlich

- Welche Mailtypen werden im MVP wirklich gebraucht
- Welche Ereignisse loesen eine Mail aus
- Wer ist Absender
- Wer ist Empfaenger
- Welche Inhalte und Sprachen werden benoetigt

### Technisch

- eigener Notification- oder Mail-Service
- HTML- und Text-Templates
- Template-Variablen pro Mailtyp
- Versand-Logging
- Retry-Logik
- Fehlerbehandlung
- Testmodus fuer lokale Entwicklung

### Infrastruktur

- `.env.example` vorbereiten
- Secrets nicht ins Repo committen
- Docker-Weitergabe der Mail-Variablen
- spaeter SPF, DKIM und DMARC fuer echte Domain einrichten

## Minimaler Prototyp

Fuer einen ersten lokalen Stand reicht:

1. Gmail-Konto mit Zwei-Faktor-Authentifizierung
2. App-Passwort erzeugen
3. SMTP-Zugangsdaten in `.env` ablegen
4. Notification-Service oder Backend-Service mit Mailer anbinden
5. Testmail fuer Reservierungsbestaetigung versenden

## Kontaktformular als erster echter Mail-Flow

Wenn jemand eine Nachricht ueber das Kontaktformular sendet, sollte der Ablauf so
vorbereitet sein:

1. Anfrage im CRM als `ContactLead` speichern
2. interne Weiterleitung an Restaurant oder Backoffice versenden
3. Danke-Mail an den Gast senden
4. in der Danke-Mail einen Registrierungslink platzieren

## Inhalt der Danke-Mail

Ziel der Mail:

- Eingang der Anfrage bestaetigen
- Vertrauen schaffen
- Registrierung motivieren

Vorschlag fuer die Kernbotschaft:

- Danke fuer die Nachricht
- wir leiten die Anfrage intern weiter
- wenn du dich registrierst, wartet bei jedem Restaurantbesuch eine Ueberraschung
- hier geht es zur Registrierung

Wichtige Template-Variablen:

- `firstName`
- `topic`
- `messagePreview`
- `registrationUrl`
- `supportEmail`

## Finaler erster deutscher Mailtext

Betreff:

`Danke fuer deine Nachricht an Bavarian RoboTaste`

Text:

```text
Hallo {firstName}

vielen Dank fuer deine Nachricht an Bavarian RoboTaste.

Wir haben deine Anfrage erhalten und leiten sie intern weiter. Unser Team meldet sich so schnell wie moeglich bei dir.

Wenn du dich schon jetzt registrierst, koennen wir deine kuenftigen Besuche besser begleiten. Ausserdem wartet bei jedem Restaurantbesuch eine kleine Ueberraschung auf dich.

Hier kannst du dich registrieren:
{registrationUrl}

Beste Gruesse
Bavarian RoboTaste
```

## Offene Entscheidung

Vor Umsetzung sollte festgelegt werden:

- nur lokaler Prototyp mit Gmail SMTP
- oder direkt produktionsnaeher mit dediziertem Maildienst

Fuer den spaeteren Ausbau ist ein dedizierter Maildienst die robustere Wahl.
