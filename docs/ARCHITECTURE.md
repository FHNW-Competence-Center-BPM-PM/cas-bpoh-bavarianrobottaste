# Architektur

## Zielbild

Die erste Projektversion ist eine statische Brand- und Landingpage fur das Restaurant
**Bavarian RoboTaste**. Die Struktur ist absichtlich klein gehalten, damit Inhalte,
Design und Markensprache zuerst schnell entwickelt werden koennen.

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

## Architekturentscheidungen

- Kein Framework in Phase 1
  - Vorteil: null Setup, schnell editierbar, sofort deploybar
- Keine externen UI-Abhaengigkeiten
  - Vorteil: volle gestalterische Kontrolle und geringe Komplexitaet
- Dokumentation direkt im Repo
  - Vorteil: Marke, Inhalte und Technik bleiben in einer gemeinsamen Quelle

## Moegliche Phase-2-Erweiterung

- Wechsel auf `Next.js` oder `Astro`, falls Content-Modelle und mehrere Seiten wachsen
- Headless CMS fur Menu, Events und News
- Formular-Backend mit E-Mail-Versand
- Bildoptimierung, SEO-Metadaten, Analytics und Cookie-Management
- Tests fur Interaktionen und visuelle Regressionen

## Inhaltsmodule fuer spaeter

- Startseite
- Speisekarte
- Reservierung
- Event-Abende
- Team / Story
- Presse / Galerie
- Kontakt / Anfahrt

