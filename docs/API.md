# API-Vorbereitung

## Ziel

Diese API-Skizze bereitet die spaetere Anbindung von Website, Camunda und
Restaurant-Services vor. Sie ist bewusst klein gehalten, deckt aber bereits
Kontaktaufnahme, Registrierung und Konsumhistorie ab.

## Kontakt und CRM

### `POST /api/contact-requests`

Erzeugt einen `ContactLead` und startet den Folgeprozess.

```json
{
  "firstName": "Achim",
  "lastName": "Dannecker",
  "email": "achim@example.com",
  "phone": "+41 79 555 55 55",
  "topic": "Event / Private Dining",
  "message": "Ich moechte fuer ein Team Event anfragen."
}
```

### `GET /api/contact-requests/{id}`

Liefert Status und CRM-Zuordnung fuer eine Kontaktanfrage.

## Registrierung

### `POST /api/guest-registrations`

Erstellt ein `GuestProfile`.

```json
{
  "firstName": "Achim",
  "lastName": "Dannecker",
  "email": "achim@example.com",
  "phone": "+41 79 555 55 55",
  "contactLeadId": "lead_123"
}
```

### `GET /api/guest-profiles/{guestProfileId}`

Liefert das Gastprofil.

## Besuche und Begleitgaeste

### `POST /api/visits`

Legt einen Restaurantbesuch an.

### `POST /api/visits/{visitId}/guests`

Fuegt Begleitgaeste zu einem Besuch hinzu.

## Konsumhistorie

### `POST /api/visits/{visitId}/consumption`

Speichert konsumierte Artikel zu einem Besuch.

### `GET /api/guest-profiles/{guestProfileId}/consumption`

Liefert die Konsumhistorie.

### `GET /api/guest-profiles/{guestProfileId}/visits`

Liefert vergangene Besuche inklusive Begleitgaeste.

## Camunda-nahe Prozessschritte

1. Kontaktanfrage validieren
2. `ContactLead` speichern
3. Interne Mail an Restaurant senden
4. Danke-Mail mit Registrierungslink senden
5. optional manuellen Review-Task erzeugen
