# CRM und Gastprofil

## Ziel

Jede Kontaktanfrage soll nicht nur eine E-Mail ausloesen, sondern auch in einer
spaeteren CRM-Datenbank als verwertbarer Kontakt landen. Wenn sich die Person danach
registriert, soll aus diesem Kontakt ein wiedererkennbarer Gast mit Historie werden.

## Kernidee

- Kontaktanfrage erzeugt einen `ContactLead`
- Danke-Mail bestaetigt den Eingang und motiviert zur Registrierung
- Registrierung erzeugt ein `GuestProfile`
- bestehender `ContactLead` wird mit dem `GuestProfile` verknuepft
- spaetere Besuche, Bestellungen und Begleitgaeste werden an das Profil angehaengt

## Empfohlene Entitaeten

### ContactLead

- `id`
- `firstName`
- `lastName`
- `email`
- `phone` optional
- `topic`
- `message`
- `source`
- `status`
- `createdAt`
- `forwardedAt` optional
- `convertedGuestProfileId` optional

### GuestProfile

- `id`
- `firstName`
- `lastName`
- `email`
- `phone` optional
- `marketingConsent` optional
- `createdAt`
- `registrationSource`
- `contactLeadId` optional

Bewusst nicht im MVP:

- Geburtsdatum

## Besuchs- und Konsumhistorie

### Visit

- `id`
- `guestProfileId`
- `visitDate`
- `reservationId` optional
- `tableId` optional
- `partySize`
- `notes` optional

### VisitGuest

- `id`
- `visitId`
- `displayName`
- `relationship` optional
- `isRegisteredGuest`
- `linkedGuestProfileId` optional

### ConsumptionEntry

- `id`
- `visitId`
- `guestProfileId`
- `menuItemId` optional
- `itemName`
- `category`
- `quantity`
- `unitPrice`
- `totalPrice`
- `consumedAt`

## Verknuepfungslogik

Fuer die erste Version reicht eine pragmatische Verknuepfung:

- primaer ueber dieselbe E-Mail-Adresse
- sekundar ueber Telefonnummer, wenn vorhanden
- bei Unsicherheit manuelle Pruefung im Admin- oder CRM-Backend

## Minimaler Registrierungsumfang

- Vorname
- Nachname
- E-Mail
- Telefon optional

## Empfohlener Registrierungsablauf

1. Gast erfasst Vorname, Nachname, E-Mail und optional Telefon.
2. System sendet einen Verifikationscode an die E-Mail-Adresse.
3. Gast bestaetigt den Code.
4. Gast setzt ein Passwort.
5. Danach wird das `GuestProfile` aktiviert und kann mit spaeteren Besuchen verknuepft werden.

## Fachlicher Flow

1. Gast sendet Kontaktformular.
2. `ContactLead` wird gespeichert.
3. Interne Weiterleitung an das Restaurant wird ausgeloest.
4. Gast erhaelt Danke-Mail mit Registrierungslink.
5. Registrierung erstellt `GuestProfile`.
6. Bestehender `ContactLead` wird auf `converted` gesetzt.
7. Spaetere Besuche und Konsumdaten werden an `GuestProfile` gehaengt.
