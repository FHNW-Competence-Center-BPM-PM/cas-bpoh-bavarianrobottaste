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

## CMS-Produkte per ERP-ID

### `GET /api/cms/products/{erpId}`

Liefert den CMS-relevanten Produktausschnitt fuer eine ERP-ID.

```json
{
  "ok": true,
  "product": {
    "erpId": "ERP-10042",
    "page": "menu",
    "sectionKey": "main_frames",
    "category": "Chef Signature",
    "name": "Mechatronic Roast",
    "description": "Langsam gegartes Rind, Dunkelbiersauce, Selleriepueree, Wurzelgemuese und knuspriger Zwiebel-Glanz.",
    "imageUrl": "http://localhost:8080/assets/menu/bavarian-robotaste-mechatronic-roast.png",
    "price": "CHF 39"
  }
}
```

### `PUT /api/cms/products/{erpId}/price`

Aktualisiert den im CMS gespeicherten Preis anhand der ERP-ID.

```json
{
  "price": "CHF 17 / 102"
}
```

Antwort:

```json
{
  "ok": true,
  "product": {
    "erpId": "ERP-20017",
    "page": "drinks",
    "sectionKey": "sparkling",
    "category": "Sekt & Champagner",
    "name": "Winzersekt Pinot Brut",
    "description": "Pfalz · Gruener Apfel, Hefe, trockene Laenge.",
    "imageUrl": null,
    "price": "CHF 17 / 102"
  }
}
```

## Camunda-nahe Prozessschritte

1. Kontaktanfrage validieren
2. `ContactLead` speichern
3. Interne Mail an Restaurant senden
4. Danke-Mail mit Registrierungslink senden
5. optional manuellen Review-Task erzeugen
