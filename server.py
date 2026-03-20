import hashlib
import html
import json
import mimetypes
import os
import secrets
import smtplib
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PENDING_REGISTRATIONS_FILE = DATA_DIR / "pending_registrations.json"
GUEST_PROFILES_FILE = DATA_DIR / "guest_profiles.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
PRODUCTS_DB_FILE = DATA_DIR / "products.db"


def load_local_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


load_local_env()

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))
REGISTRATION_CODE_TTL_MINUTES = int(os.environ.get("REGISTRATION_CODE_TTL_MINUTES", "15"))
PASSWORD_HASH_ITERATIONS = 200_000
DATA_LOCK = threading.Lock()
RESERVATION_BOOKING_WINDOW_DAYS = 21
RESERVATION_CANCELLATION_NOTICE_HOURS = 5


def app_timezone():
    try:
        return ZoneInfo(os.environ.get("APP_TIMEZONE", "Europe/Zurich"))
    except Exception:
        return timezone(timedelta(hours=1))


LOCAL_TIMEZONE = app_timezone()

RESERVATION_SLOTS = [
    {"key": "early", "label": "17:30 - 20:00", "start": "17:30", "end": "20:00"},
    {"key": "late", "label": "20:30 - 23:30", "start": "20:30", "end": "23:30"},
]
DEMO_RESERVATION_EMAIL = "demo-reservations@bavarian-robotaste.local"

RESERVATION_ROOMS = [
    {
        "id": "raum-1",
        "name": "König-Ludwig Resonanzsaal",
        "tagline": "Große Abende, kuratierte Menüs und geschlossene Gesellschaften.",
        "theme": "Messing, Samt und orchestrierte Dinner-Inszenierung.",
        "status": "event_only",
        "eventTableRange": "Tisch 5 - 11",
        "defaultStatusNote": "Dieser Raum ist in den kommenden 2 Wochen durch Veranstaltungen ausgebucht.",
        "tables": [],
    },
    {
        "id": "raum-2",
        "name": "Alpen-Algorithmus Atelier",
        "tagline": "Private Tastings, Partner-Events und Produktpräsentationen.",
        "theme": "Warme Hölzer, präzise Lichtlinien und ruhige Tech-Ästhetik.",
        "status": "event_only",
        "eventTableRange": "Tisch 12 - 18",
        "defaultStatusNote": "Dieser Raum ist in den kommenden 2 Wochen durch Veranstaltungen ausgebucht.",
        "tables": [],
    },
    {
        "id": "raum-3",
        "name": "Neon-Brauwerk Forum",
        "tagline": "Markenabende, Launches und robotische Showmomente.",
        "theme": "Braukultur trifft Lichtchoreografie und digitale Bühne.",
        "status": "event_only",
        "eventTableRange": "Tisch 19 - 24",
        "defaultStatusNote": "Dieser Raum ist in den kommenden 2 Wochen durch Veranstaltungen ausgebucht.",
        "tables": [],
    },
    {
        "id": "raum-4",
        "name": "Servierwerk Lounge",
        "tagline": "Der regulär buchbare Gastraum für Dinner, Aperitif und spätere Drinks.",
        "theme": "Smart Dining mit IoT-Tischen, warmem Licht und entspannter Präzision.",
        "status": "bookable",
        "eventTableRange": "",
        "defaultStatusNote": "In diesem Raum sind individuelle Tischreservierungen möglich.",
        "tables": [
            {
                "id": "table-1",
                "label": "Tisch 1",
                "kind": "dining",
                "kindLabel": "Dinner",
                "capacityMin": 1,
                "capacityMax": 4,
                "description": "Klassischer Dinner-Tisch für bis zu vier Gäste.",
            },
            {
                "id": "table-2",
                "label": "Tisch 2",
                "kind": "dining",
                "kindLabel": "Dinner",
                "capacityMin": 1,
                "capacityMax": 4,
                "description": "Klassischer Dinner-Tisch für bis zu vier Gäste.",
            },
            {
                "id": "table-3",
                "label": "Tisch 3",
                "kind": "aperitif",
                "kindLabel": "Drinks & Starter",
                "capacityMin": 1,
                "capacityMax": 2,
                "description": "Kleiner Tisch für Aperitif, Snacks und Starter.",
            },
            {
                "id": "table-4",
                "label": "Tisch 4",
                "kind": "bar",
                "kindLabel": "Nur Drinks",
                "capacityMin": 1,
                "capacityMax": 4,
                "description": "Lounge-Tisch für reine Drinks ohne Dinner-Setup.",
            },
        ],
    },
]

PRODUCT_SECTIONS = [
    {"page": "menu", "key": "starter", "tag": "Starter", "title": "Der Einstieg ist leicht, präzise und bewusst neugierig.", "sort_order": 1},
    {"page": "menu", "key": "main_frames", "tag": "Main Frames", "title": "Signature Plates für Gäste, die klassisches Comfort Food neu erleben wollen.", "sort_order": 2},
    {"page": "menu", "key": "dessert_drinks", "tag": "Dessert und Drinks", "title": "Das Finale bleibt warm, dunkel, elegant und ein wenig theatralisch.", "sort_order": 3},
    {"page": "drinks", "key": "red_wine", "tag": "Rotweine", "title": "Dunkle Frucht, Würze und Tiefe für die schweren Takte des Abends.", "sort_order": 1},
    {"page": "drinks", "key": "white_wine", "tag": "Weißweine", "title": "Hell, klar und mit genug Rückgrat für Präzision im Glas.", "sort_order": 2},
    {"page": "drinks", "key": "rose", "tag": "Rosé", "title": "Leichtfüßig im Auftakt, ernsthaft genug für eine klare Handschrift.", "sort_order": 3},
    {"page": "drinks", "key": "sparkling", "tag": "Sekt & Champagner", "title": "Perlage mit Haltung, von festlich bis präzise mineralisch.", "sort_order": 4},
    {"page": "drinks", "key": "beer", "tag": "Lokale Premium-Biere", "title": "Regional gebraut, handwerklich ernst genommen und bewusst kuratiert.", "sort_order": 5},
    {"page": "drinks", "key": "cocktails", "tag": "Cocktails", "title": "Barhandwerk mit Haltung, nicht bloß Effekt.", "sort_order": 6},
    {"page": "drinks", "key": "softs", "tag": "Softdrinks, Wasser & Café", "title": "Auch die stilleren Begleiter bekommen bei uns Präzision und Stil.", "sort_order": 7},
]

PRODUCT_SEED = [
    {"page": "menu", "section_key": "starter", "sort_order": 1, "category": "Starter", "title": "Alpine Data Salad", "teaser": "Apfel, Gartenkräuter, gepickelte Gurke, Senfperlen, Brezn-Crunch.", "ingredients": "Apfel, Gartenkräuter, gepickelte Gurke, Senfperlen und Brezn-Crunch.", "price": "CHF 14", "image_path": "assets/menu/bavarian-robotaste-alpine-data-salad.png", "quote_text": "Einfachheit ist die höchste Stufe der Vollendung.", "quote_author": "Leonardo da Vinci", "special_heading_1": "Herkunft", "special_content_1": "Bio-Kräuter aus der Region, Schweizer Äpfel, hausgemachte Pickles und Brezn-Chips.", "special_heading_2": "Qualität", "special_content_2": "Frisch, saisonal und leicht: ein bewusst reduzierter Auftakt mit lokaler Produktqualität.", "featured": 0},
    {"page": "menu", "section_key": "starter", "sort_order": 2, "category": "Starter", "title": "Sensor Pretzel Bites", "teaser": "Laugenchips mit Obazda-Creme, Rauchpaprika und Schnittlauch.", "ingredients": "Laugenchips mit Obazda-Creme, Rauchpaprika und Schnittlauch.", "price": "CHF 12", "image_path": "assets/menu/bavarian-robotaste-sensor-pretzel-bites.png", "quote_text": "Der Appetit ist die Stimme der Materie.", "quote_author": "Ludwig Feuerbach", "special_heading_1": "Herkunft", "special_content_1": "Frisch gebackene Laugenbasis, cremiger Käseaufstrich und regionale Kräuter.", "special_heading_2": "Qualität", "special_content_2": "Kleiner Gang mit maximaler Textur: salzig, cremig, knusprig und klar bayerisch.", "featured": 0},
    {"page": "menu", "section_key": "starter", "sort_order": 3, "category": "Starter", "title": "Neon Broth Shot", "teaser": "Klare Rinderessenz mit Wurzelgemüse und feinem Kräuteröl.", "ingredients": "Klare Rinderessenz mit Wurzelgemüse und feinem Kräuteröl.", "price": "CHF 11", "image_path": "assets/menu/bavarian-robotaste-neon-broth-shot.png", "quote_text": "Tiefe entsteht aus Konzentration.", "quote_author": "Novalis", "special_heading_1": "Herkunft", "special_content_1": "Lang gezogene Brühe, saisonales Wurzelgemüse und hausgemachtes Kräuteröl.", "special_heading_2": "Qualität", "special_content_2": "Sauberer Geschmack, handwerkliche Geduld und hochwertige Grundprodukte im Fokus.", "featured": 0},
    {"page": "menu", "section_key": "main_frames", "sort_order": 1, "category": "Chef Signature", "title": "Mechatronic Roast", "teaser": "Langsam gegartes Rind, Dunkelbiersauce, Selleriepüree, Wurzelgemüse und knuspriger Zwiebel-Glanz.", "ingredients": "Langsam gegartes Rind, Dunkelbiersauce, Selleriepüree, Wurzelgemüse und knuspriger Zwiebel-Glanz.", "price": "CHF 39", "image_path": "assets/menu/bavarian-robotaste-mechatronic-roast.png", "quote_text": "Man soll dem Leib etwas Gutes bieten, damit die Seele Lust hat, darin zu wohnen.", "quote_author": "Winston Churchill", "special_heading_1": "Herkunft", "special_content_1": "Regional bezogenes Rind, Bio-Wurzelgemüse, dunkles Malz und handwerklich gekochter Jus.", "special_heading_2": "Qualität", "special_content_2": "Alle Hauptkomponenten stammen aus lokaler oder regionaler Produktion, bevorzugt in Bio-Qualität.", "featured": 1},
    {"page": "menu", "section_key": "main_frames", "sort_order": 2, "category": "Vegetarisch", "title": "Bot Garden Knödel", "teaser": "Kräuterknödel, Pilzjus, glasierte Karotten, Petersilienstaub.", "ingredients": "Kräuterknödel, Pilzjus, glasierte Karotten und Petersilienstaub.", "price": "CHF 26", "image_path": "assets/menu/bavarian-robotaste-bot-garden-knoedel.png", "quote_text": "Die Natur eilt nicht, und dennoch wird alles vollendet.", "quote_author": "Laotse", "special_heading_1": "Herkunft", "special_content_1": "Bio-Kräuter, Karotten vom Hof, Pilze aus kontrollierter Zucht und hausgemachte Knödelmasse.", "special_heading_2": "Qualität", "special_content_2": "Vegetarisches Hauptgericht mit saisonalem Gemüse, hoher Produktgüte und bewusst elegantem Aufbau.", "featured": 0},
    {"page": "menu", "section_key": "main_frames", "sort_order": 3, "category": "Fisch", "title": "Autonomous Alpine Trout", "teaser": "Forelle mit Dill, Kartoffelschaum, Gurke und Zitronenbutter.", "ingredients": "Forelle mit Dill, Kartoffelschaum, Gurke und Zitronenbutter.", "price": "CHF 34", "image_path": "assets/menu/bavarian-robotaste-autonomous-alpine-trout.png", "quote_text": "Im Einfachen ruht das Wahre.", "quote_author": "Johann Wolfgang von Goethe", "special_heading_1": "Herkunft", "special_content_1": "Forelle aus alpiner Zucht, frische Gurke, Dill und cremiger Kartoffelaufbau.", "special_heading_2": "Qualität", "special_content_2": "Fein, regional und klar ausbalanciert mit Fokus auf Frische, Wasserqualität und handwerklicher Präzision.", "featured": 0},
    {"page": "menu", "section_key": "dessert_drinks", "sort_order": 1, "category": "Dessert", "title": "Black Forest Circuit", "teaser": "Schokolade, Kirsche, Espresso, Rauchsalz und Spiegelglas-Finish.", "ingredients": "Schokolade, Kirsche, Espresso, Rauchsalz und Spiegelglas-Finish.", "price": "CHF 16", "image_path": "assets/menu/bavarian-robotaste-black-forest-circuit.png", "quote_text": "Der Geschmack ist das Gedächtnis des Herzens.", "quote_author": "Jean-Jacques Rousseau", "special_heading_1": "Herkunft", "special_content_1": "Dunkle Schokolade, eingelegte Kirschen, Espressoreduktion und fein gesetzte Dessertstruktur.", "special_heading_2": "Qualität", "special_content_2": "Premium-Dessert mit klarer Texturarbeit, bewusst dosierter Süße und hochwertigen Einzelkomponenten.", "featured": 0},
    {"page": "menu", "section_key": "dessert_drinks", "sort_order": 2, "category": "Drink", "title": "Signal Spritz", "teaser": "Alpenbitter, Tonic, Rosmarin und Zitrusnebel.", "ingredients": "Alpenbitter, Tonic, Rosmarin und Zitrusnebel.", "price": "CHF 13", "image_path": "assets/menu/bavarian-robotaste-signal-spritz.png", "quote_text": "Das Leichte muss man leicht nehmen.", "quote_author": "Heinrich Heine", "special_heading_1": "Herkunft", "special_content_1": "Bittere Kräuter, feine Zitrusnoten und frischer Rosmarin mit bewusst leichter Struktur.", "special_heading_2": "Qualität", "special_content_2": "Klarer Aperitif mit hochwertigen Botanicals, präziser Balance und markanter Duftsignatur.", "featured": 0},
    {"page": "menu", "section_key": "dessert_drinks", "sort_order": 3, "category": "Drink", "title": "Brass Barrel Old Fashioned", "teaser": "Dunkler Whisky, Waldhonig, Bitters und Orangenzeste.", "ingredients": "Dunkler Whisky, Waldhonig, Bitters und Orangenzeste.", "price": "CHF 18", "image_path": "assets/menu/bavarian-robotaste-brass-barrel-old-fashioned.png", "quote_text": "In der Ruhe liegt die Kraft.", "quote_author": "Konfuzius", "special_heading_1": "Herkunft", "special_content_1": "Kräftige Fassnoten, regionaler Honig und klassische Bar-Handschrift mit tiefer Aromatik.", "special_heading_2": "Qualität", "special_content_2": "Bewusst langsam gebauter Signature Drink mit klarer Balance, Wärme und Tiefe.", "featured": 0},
    {"page": "drinks", "section_key": "red_wine", "sort_order": 1, "category": "Rotwein", "title": "Pinot Noir Réserve 2022", "teaser": "Baden, Deutschland · Sauerkirsche, Kräuter, seidiger Zug.", "ingredients": "Eleganter Pinot Noir mit Sauerkirsche, Waldbeeren und feiner Würze.", "price": "CHF 15 / 98", "image_path": "", "quote_text": "Der Wein ist unter den Getränken das Nützlichste.", "quote_author": "Platon", "special_heading_1": "Herkunft", "special_content_1": "Kleine Parzellenlage, schonender Ausbau im Holz, handgelesen und bewusst limitiert.", "special_heading_2": "Qualität", "special_content_2": "Feine Gerbstoffe, lange Länge und eine stilvolle Kühle für präzise Speisenbegleitung.", "featured": 0},
    {"page": "drinks", "section_key": "red_wine", "sort_order": 2, "category": "Rotwein", "title": "Blaufränkisch Alte Reben 2021", "teaser": "Burgenland, Österreich · Dunkle Frucht, Pfeffer, mineralischer Kern.", "ingredients": "Würziger Blaufränkisch mit Brombeere, Pfeffer und tiefer mineralischer Note.", "price": "CHF 16 / 104", "image_path": "", "quote_text": "Charakter zeigt sich in der Begrenzung.", "quote_author": "Friedrich Nietzsche", "special_heading_1": "Herkunft", "special_content_1": "Alte Rebanlagen, niedrige Erträge und ein Ausbau, der Struktur vor Lautstärke setzt.", "special_heading_2": "Qualität", "special_content_2": "Markante Frische und Spannung, ideal zu kräftigen Fleischgängen und dunklen Jus.", "featured": 0},
    {"page": "drinks", "section_key": "red_wine", "sort_order": 3, "category": "Rotwein", "title": "Barbera Superiore 2020", "teaser": "Piemont, Italien · Pflaume, Kakao, seidige Säure.", "ingredients": "Saftige Barbera mit Pflaume, Kakao, Säurezug und dunkler Wärme.", "price": "CHF 17 / 112", "image_path": "", "quote_text": "Tiefe entsteht, wenn Form und Kraft einander tragen.", "quote_author": "Aristoteles", "special_heading_1": "Herkunft", "special_content_1": "Traditionelles Weingut mit biologischer Bewirtschaftung und langem Ausbau im großen Holz.", "special_heading_2": "Qualität", "special_content_2": "Großzügig und doch präzise, mit vibrierender Säure und kulinarischer Vielseitigkeit.", "featured": 0},
    {"page": "drinks", "section_key": "white_wine", "sort_order": 1, "category": "Weißwein", "title": "Riesling Steinblick 2023", "teaser": "Mosel, Deutschland · Zitrus, weißer Pfirsich, vibrierende Säure.", "ingredients": "Feiner Riesling mit Zitrus, Steinobst und geradlinigem Säurezug.", "price": "CHF 14 / 89", "image_path": "", "quote_text": "Klarheit ist die Höflichkeit des Denkens.", "quote_author": "José Ortega y Gasset", "special_heading_1": "Herkunft", "special_content_1": "Steile Lagen, kühle Nächte und selektive Handlese für maximale Klarheit.", "special_heading_2": "Qualität", "special_content_2": "Lebendig, präzise und ideal für Kräuter, Forelle und feine Säurebilder.", "featured": 0},
    {"page": "drinks", "section_key": "white_wine", "sort_order": 2, "category": "Weißwein", "title": "Sauvignon Blanc Kalk 2023", "teaser": "Südsteiermark, Österreich · Kräuter, Stachelbeere, Kalkzug.", "ingredients": "Frischer Sauvignon Blanc mit Stachelbeere, Kräutern und feinem Kalkton.", "price": "CHF 15 / 94", "image_path": "", "quote_text": "Maß ist nicht Enge, sondern Form.", "quote_author": "Rainer Maria Rilke", "special_heading_1": "Herkunft", "special_content_1": "Aus kalkreichen Böden mit betont kühlem Ausbau und präzisem Hefelager.", "special_heading_2": "Qualität", "special_content_2": "Hell, geradlinig und aromatisch ohne Lautstärke, ideal als Speisenwein.", "featured": 0},
    {"page": "drinks", "section_key": "white_wine", "sort_order": 3, "category": "Weißwein", "title": "Chardonnay Fumé 2022", "teaser": "Burgund-Stil · Gelbe Frucht, Haselnuss, sanfter Holzrahmen.", "ingredients": "Chardonnay mit gelber Frucht, feinem Holz und cremiger Struktur.", "price": "CHF 17 / 108", "image_path": "", "quote_text": "Reife ist geordnete Kraft.", "quote_author": "Thomas von Aquin", "special_heading_1": "Herkunft", "special_content_1": "Selektive Lese, teilweiser Ausbau im Barrique und lange Reife auf der Feinhefe.", "special_heading_2": "Qualität", "special_content_2": "Substanzreich, präzise und warm im Nachhall, ideal zu komplexeren Tellern.", "featured": 0},
    {"page": "drinks", "section_key": "rose", "sort_order": 1, "category": "Rosé", "title": "Rosé Cuvée Roselight 2023", "teaser": "Provence-Stil · Himbeere, Zeste, salziger Zug.", "ingredients": "Trockener Rosé mit roten Beeren, Kräutern und feinem Zitruszug.", "price": "CHF 13 / 84", "image_path": "", "quote_text": "Leichtigkeit ist eine Form von Disziplin.", "quote_author": "Albert Camus", "special_heading_1": "Herkunft", "special_content_1": "Schonende Pressung, kurze Maischestandzeit und kühler Ausbau.", "special_heading_2": "Qualität", "special_content_2": "Elegant statt beliebig, mit Struktur und feiner Speisenfreundlichkeit.", "featured": 0},
    {"page": "drinks", "section_key": "rose", "sort_order": 2, "category": "Rosé", "title": "Pinot Rosé Reserve 2023", "teaser": "Schweiz · Erdbeere, Hagebutte, kühle Frische.", "ingredients": "Kühler Pinot-Rosé mit Erdbeere, Hagebutte und straffer Linie.", "price": "CHF 14 / 91", "image_path": "", "quote_text": "Anmut ist die Form des Gleichgewichts.", "quote_author": "Friedrich Schiller", "special_heading_1": "Herkunft", "special_content_1": "Selektive Pinot-Trauben aus höher gelegenen Lagen.", "special_heading_2": "Qualität", "special_content_2": "Fein, präzise und ideal als strukturierter Aperitif oder leichter Essensbegleiter.", "featured": 0},
    {"page": "drinks", "section_key": "rose", "sort_order": 3, "category": "Rosé", "title": "Rosato di Lago 2023", "teaser": "Norditalien · Grapefruit, Kräuter, leichte Wärme.", "ingredients": "Rosato mit Grapefruit, Kräutern und mediterranem Nachhall.", "price": "CHF 15 / 95", "image_path": "", "quote_text": "Der Stil ist die Ordnung des Gefühls.", "quote_author": "Gustave Flaubert", "special_heading_1": "Herkunft", "special_content_1": "Leicht gekühlter Ausbau aus norditalienischen See-Lagen.", "special_heading_2": "Qualität", "special_content_2": "Lebendig, sonnig und doch fein gebaut, ideal zu Gemüse und Fisch.", "featured": 0},
    {"page": "drinks", "section_key": "sparkling", "sort_order": 1, "category": "Sekt & Champagner", "title": "Crémant Blanc de Blancs", "teaser": "Elsass · Brioche, Zitrus, feine Perlage.", "ingredients": "Feine Perlage, Brioche, Zitrus und ein sehr sauberer Auftakt.", "price": "CHF 16 / 96", "image_path": "", "quote_text": "Feiern heißt, dem Augenblick Form geben.", "quote_author": "Hannah Arendt", "special_heading_1": "Herkunft", "special_content_1": "Traditionelle Flaschengärung mit langer Hefelagerung.", "special_heading_2": "Qualität", "special_content_2": "Lebendig, trocken und hochwertig, ideal für den ersten Eindruck des Abends.", "featured": 0},
    {"page": "drinks", "section_key": "sparkling", "sort_order": 2, "category": "Sekt & Champagner", "title": "Winzersekt Pinot Brut", "teaser": "Pfalz · Grüner Apfel, Hefe, trockene Länge.", "ingredients": "Pinot-Sekt mit Apfel, Hefe, Struktur und trockenem Kern.", "price": "CHF 17 / 102", "image_path": "", "quote_text": "Wert entsteht aus Sorgfalt.", "quote_author": "Immanuel Kant", "special_heading_1": "Herkunft", "special_content_1": "Kleine Produktion, traditionelle Methode und präzise Dosage.", "special_heading_2": "Qualität", "special_content_2": "Deutscher Premium-Sekt mit Substanz und exzellenter Speisenbegleitung.", "featured": 0},
    {"page": "drinks", "section_key": "sparkling", "sort_order": 3, "category": "Sekt & Champagner", "title": "Champagne Premier Cru Brut", "teaser": "Champagne · Kreide, Zitrus, Brioche, Länge.", "ingredients": "Komplexer Champagner mit Zitrus, Kreide, Brioche und langem Finale.", "price": "CHF 22 / 148", "image_path": "", "quote_text": "Das Besondere zeigt sich in der Nuance.", "quote_author": "Marcel Proust", "special_heading_1": "Herkunft", "special_content_1": "Premier-Cru-Herkunft, klassische Assemblage und lange Flaschenreife.", "special_heading_2": "Qualität", "special_content_2": "Festlich, mineralisch und tief gebaut, ohne in Opulenz zu kippen.", "featured": 0},
    {"page": "drinks", "section_key": "beer", "sort_order": 1, "category": "Lokales Premium-Bier", "title": "Zürcher Kellerbier", "teaser": "Regional · Brotkruste, Heu, milde Würze.", "ingredients": "Unfiltriertes Kellerbier mit Brotkruste, Heu und feiner Hopfenwürze.", "price": "CHF 9", "image_path": "", "quote_text": "Nähe ist eine Form von Qualität.", "quote_author": "Martin Heidegger", "special_heading_1": "Herkunft", "special_content_1": "Kleine lokale Brauerei, langsame Reifung und regionale Rohstoffe.", "special_heading_2": "Qualität", "special_content_2": "Handwerklich, weich und tief genug für ernsthafte Speisenbegleitung.", "featured": 0},
    {"page": "drinks", "section_key": "beer", "sort_order": 2, "category": "Lokales Premium-Bier", "title": "Alpen Pale Ale", "teaser": "Schweiz · Grapefruit, Kräuter, klarer Biss.", "ingredients": "Frisches Pale Ale mit Grapefruit, Kräutern und präzisem Bitterzug.", "price": "CHF 10", "image_path": "", "quote_text": "Freiheit zeigt sich im klaren Profil.", "quote_author": "John Stuart Mill", "special_heading_1": "Herkunft", "special_content_1": "Kleine Schweizer Manufaktur mit Aromahopfen und klarer Handschrift.", "special_heading_2": "Qualität", "special_content_2": "Modern, sauber gebraut und ideal für smarte, leichtere Gerichte.", "featured": 0},
    {"page": "drinks", "section_key": "beer", "sort_order": 3, "category": "Lokales Premium-Bier", "title": "Bavarian Dark Lager", "teaser": "Regionale Braukunst · Malz, Karamell, sanfte Röste.", "ingredients": "Dunkles Lager mit Malz, Karamell und feiner Röstnote.", "price": "CHF 10", "image_path": "", "quote_text": "Wärme ist die Form, in der sich Nähe zeigt.", "quote_author": "Simone Weil", "special_heading_1": "Herkunft", "special_content_1": "Traditionsnahe Brauart mit modernem Feinschliff und regionalem Malzprofil.", "special_heading_2": "Qualität", "special_content_2": "Sanft, malzig und elegant, ideal zu Röstaromen, Fleisch und Abendwärme.", "featured": 0},
    {"page": "drinks", "section_key": "cocktails", "sort_order": 1, "category": "Cocktail", "title": "Signal Spritz", "teaser": "Alpenbitter, Tonic, Rosmarin, Zitrusnebel.", "ingredients": "Alpenbitter, Tonic, Rosmarin und Zitrusnebel.", "price": "CHF 13", "image_path": "", "quote_text": "Das Leichte muss man leicht nehmen.", "quote_author": "Heinrich Heine", "special_heading_1": "Herkunft", "special_content_1": "Botanicals, klare Zitrusstruktur und frische Kräuter für einen präzisen Aperitif.", "special_heading_2": "Qualität", "special_content_2": "Leicht, duftig und sauber gebaut, mit hoher Trinkigkeit und klarem Charakter.", "featured": 0},
    {"page": "drinks", "section_key": "cocktails", "sort_order": 2, "category": "Cocktail", "title": "Brass Barrel Old Fashioned", "teaser": "Whisky, Waldhonig, Bitters, Orangenzeste.", "ingredients": "Dunkler Whisky, Waldhonig, Bitters und Orangenzeste.", "price": "CHF 18", "image_path": "", "quote_text": "In der Ruhe liegt die Kraft.", "quote_author": "Konfuzius", "special_heading_1": "Herkunft", "special_content_1": "Reife Fassnoten, regionaler Honig und klassische Bartechnik.", "special_heading_2": "Qualität", "special_content_2": "Langsam gebaut, konzentriert und warm – ein Drink mit Tiefe und Ruhe.", "featured": 0},
    {"page": "drinks", "section_key": "cocktails", "sort_order": 3, "category": "Cocktail", "title": "Circuit Negroni", "teaser": "Gin, Bitter, Vermouth, Zedernote.", "ingredients": "Gin, Bitter, Vermouth und eine feine Zedernote.", "price": "CHF 16", "image_path": "", "quote_text": "Der Geschmack des Ernstes ist niemals oberflächlich.", "quote_author": "Seneca", "special_heading_1": "Herkunft", "special_content_1": "Klassische italienische Struktur mit leicht rauchiger Signatur.", "special_heading_2": "Qualität", "special_content_2": "Markant, erwachsen und ideal für Gäste, die Bitterkeit als Stil verstehen.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 1, "category": "Softdrink", "title": "Hausgemachte Kräuter-Limonade", "teaser": "Zitrone, Kräuter, feine Kohlensäure.", "ingredients": "Zitrone, Kräuter und feine Kohlensäure.", "price": "CHF 7", "image_path": "", "quote_text": "Frische ist eine Form von Aufmerksamkeit.", "quote_author": "Simone de Beauvoir", "special_heading_1": "Profil", "special_content_1": "Hausgemacht, kräutrig und bewusst leicht für einen lebendigen Auftakt.", "special_heading_2": "Servieridee", "special_content_2": "Ideal als alkoholfreie Begleitung zu leichten Speisen und Mittagsgängen.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 2, "category": "Softdrink", "title": "Cloudy Apple Soda", "teaser": "Apfelschorle mit naturtrübem Saft.", "ingredients": "Naturtrüber Apfelsaft und sprudelndes Wasser.", "price": "CHF 6", "image_path": "", "quote_text": "Das Naheliegende verdient Sorgfalt.", "quote_author": "Theodor W. Adorno", "special_heading_1": "Profil", "special_content_1": "Fruchtbetont, klar und unkompliziert mit bewusst regionaler Anmutung.", "special_heading_2": "Servieridee", "special_content_2": "Passt gut zu Vorspeisen, Nachmittagsgästen und allen, die es unaufgeregt mögen.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 3, "category": "Softdrink", "title": "Ginger Citrus Fizz", "teaser": "Ingwer, Limette, leichte Schärfe.", "ingredients": "Ingwer, Limette und prickelnde Frische.", "price": "CHF 7", "image_path": "", "quote_text": "Spannung braucht Balance.", "quote_author": "Heraklit", "special_heading_1": "Profil", "special_content_1": "Leicht scharf, zitrisch und belebend mit klarer Frischelinie.", "special_heading_2": "Servieridee", "special_content_2": "Guter Match für kräftigere Teller oder als alkoholfreier Aperitif.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 4, "category": "Wasser", "title": "Still Water Premium", "teaser": "Leises Mineralwasser, 75 cl.", "ingredients": "Stilles Mineralwasser, 75 cl.", "price": "CHF 8", "image_path": "", "quote_text": "Klarheit trägt alles.", "quote_author": "Meister Eckhart", "special_heading_1": "Profil", "special_content_1": "Ruhig, mineralisch und bewusst zurückhaltend.", "special_heading_2": "Servieridee", "special_content_2": "Für den Tisch, für Zwischengänge und als neutrale Begleitung über den ganzen Abend.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 5, "category": "Wasser", "title": "Sparkling Water Premium", "teaser": "Feine Kohlensäure, 75 cl.", "ingredients": "Mineralwasser mit feiner Kohlensäure, 75 cl.", "price": "CHF 8", "image_path": "", "quote_text": "Lebendigkeit zeigt sich im Detail.", "quote_author": "Henri Bergson", "special_heading_1": "Profil", "special_content_1": "Fein perlend und elegant ohne dominante Härte.", "special_heading_2": "Servieridee", "special_content_2": "Passt zu nahezu allen Speisen und hält den Gaumen präsent.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 6, "category": "Café", "title": "Espresso", "teaser": "Kräftig, dunkel, präzise.", "ingredients": "Dunkel gerösteter Espresso.", "price": "CHF 4.5", "image_path": "", "quote_text": "Konzentration ist verdichtete Zeit.", "quote_author": "Walter Benjamin", "special_heading_1": "Profil", "special_content_1": "Kräftig, klar und bewusst ohne Umwege serviert.", "special_heading_2": "Servieridee", "special_content_2": "Für den Abschluss, die Pause oder als kurzer Fokusmoment zwischendurch.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 7, "category": "Café", "title": "Doppelter Espresso", "teaser": "Mehr Tiefe, längerer Zug.", "ingredients": "Doppelter Shot aus dunkel gerösteten Bohnen.", "price": "CHF 6", "image_path": "", "quote_text": "Mehr Intensität verlangt mehr Form.", "quote_author": "Paul Valéry", "special_heading_1": "Profil", "special_content_1": "Kräftiger gebaut mit zusätzlicher Tiefe und Röstaromatik.", "special_heading_2": "Servieridee", "special_content_2": "Für lange Gespräche, späte Reservierungen oder einen klaren Nachgang.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 8, "category": "Café", "title": "Americano", "teaser": "Verlängerter Espresso mit Klarheit.", "ingredients": "Espresso und heißes Wasser.", "price": "CHF 5", "image_path": "", "quote_text": "Länge braucht Struktur.", "quote_author": "Umberto Eco", "special_heading_1": "Profil", "special_content_1": "Leichter als Espresso, aber mit klarer aromatischer Linie.", "special_heading_2": "Servieridee", "special_content_2": "Gut für einen längeren Kaffeemoment ohne Schwere.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 9, "category": "Café", "title": "Cappuccino", "teaser": "Milchschaum, Balance, Wärme.", "ingredients": "Espresso, Milch und feiner Schaum.", "price": "CHF 5.5", "image_path": "", "quote_text": "Wärme ist auch eine Textur.", "quote_author": "Virginia Woolf", "special_heading_1": "Profil", "special_content_1": "Rund, weich und ausgewogen mit cremigem Finish.", "special_heading_2": "Servieridee", "special_content_2": "Für entspannte Tageszeiten, Dessertmomente und eine sanfte Landung.", "featured": 0},
    {"page": "drinks", "section_key": "softs", "sort_order": 10, "category": "Café", "title": "Flat White", "teaser": "Kräftiger Espresso und fein gezogene Milch.", "ingredients": "Doppelter Espresso und fein texturierte Milch.", "price": "CHF 5.8", "image_path": "", "quote_text": "Präzision kann sehr weich wirken.", "quote_author": "Ingeborg Bachmann", "special_heading_1": "Profil", "special_content_1": "Mehr Kaffeezug als Cappuccino, aber mit seidiger Milchstruktur.", "special_heading_2": "Servieridee", "special_content_2": "Ideal für Gäste, die Kaffeeintensität mit ruhigem Mundgefühl suchen.", "featured": 0},
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)


def now_iso() -> str:
    return now_utc().isoformat()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def db_connection() -> sqlite3.Connection:
    ensure_data_dir()
    connection = sqlite3.connect(PRODUCTS_DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_products_db() -> None:
    with db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS product_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page TEXT NOT NULL,
                section_key TEXT NOT NULL,
                tag TEXT NOT NULL,
                title TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                UNIQUE(page, section_key)
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page TEXT NOT NULL,
                section_key TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                erp_id TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                teaser TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                price TEXT NOT NULL,
                image_path TEXT NOT NULL DEFAULT '',
                quote_text TEXT NOT NULL,
                quote_author TEXT NOT NULL,
                special_heading_1 TEXT NOT NULL,
                special_content_1 TEXT NOT NULL,
                special_heading_2 TEXT NOT NULL,
                special_content_2 TEXT NOT NULL,
                featured INTEGER NOT NULL DEFAULT 0
            );
            """
        )

        product_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(products)").fetchall()
        }
        if "erp_id" not in product_columns:
            connection.execute(
                """
                ALTER TABLE products
                ADD COLUMN erp_id TEXT NOT NULL DEFAULT ''
                """
            )

        connection.execute("UPDATE products SET erp_id = '' WHERE erp_id IS NULL")

        section_count = connection.execute("SELECT COUNT(*) FROM product_sections").fetchone()[0]
        product_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]

        if section_count == 0:
            connection.executemany(
                """
                INSERT INTO product_sections (page, section_key, tag, title, sort_order)
                VALUES (:page, :key, :tag, :title, :sort_order)
                """,
                PRODUCT_SECTIONS,
            )

        if product_count == 0:
            connection.executemany(
                """
                INSERT INTO products (
                    page, section_key, sort_order, erp_id, category, title, teaser, ingredients, price,
                    image_path, quote_text, quote_author, special_heading_1, special_content_1,
                    special_heading_2, special_content_2, featured
                ) VALUES (
                    :page, :section_key, :sort_order, '', :category, :title, :teaser, :ingredients, :price,
                    :image_path, :quote_text, :quote_author, :special_heading_1, :special_content_1,
                    :special_heading_2, :special_content_2, :featured
                )
                """,
                PRODUCT_SEED,
            )


def ensure_reservations_db() -> None:
    with db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY,
                reservation_code TEXT NOT NULL UNIQUE,
                reservation_date TEXT NOT NULL,
                slot_key TEXT NOT NULL,
                room_id TEXT NOT NULL,
                table_id TEXT NOT NULL,
                guests INTEGER NOT NULL,
                guest_name TEXT NOT NULL,
                guest_email TEXT NOT NULL,
                guest_phone TEXT NOT NULL DEFAULT '',
                occasion TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                cancel_token TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'requested',
                cancelled_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )

        reservation_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(reservations)").fetchall()
        }
        if "cancel_token" not in reservation_columns:
            connection.execute(
                """
                ALTER TABLE reservations
                ADD COLUMN cancel_token TEXT NOT NULL DEFAULT ''
                """
            )
        if "cancelled_at" not in reservation_columns:
            connection.execute(
                """
                ALTER TABLE reservations
                ADD COLUMN cancelled_at TEXT NOT NULL DEFAULT ''
                """
            )

        rows_without_token = connection.execute(
            """
            SELECT id
            FROM reservations
            WHERE cancel_token = ''
            """
        ).fetchall()
        for row in rows_without_token:
            connection.execute(
                """
                UPDATE reservations
                SET cancel_token = ?
                WHERE id = ?
                """,
                (secrets.token_urlsafe(24), row["id"]),
            )


def ensure_demo_reservations() -> None:
    base_date = datetime.now().date()
    demo_rows = [
        {
            "reservation_date": (base_date + timedelta(days=1)).isoformat(),
            "slot_key": "early",
            "room_id": "raum-4",
            "table_id": "table-2",
            "guests": 4,
            "guest_name": "Demo Dinner Crew",
            "occasion": "Dinner",
            "notes": "Demo-Reservierung für Kalenderbefüllung",
        },
        {
            "reservation_date": (base_date + timedelta(days=2)).isoformat(),
            "slot_key": "early",
            "room_id": "raum-4",
            "table_id": "table-3",
            "guests": 2,
            "guest_name": "Demo Aperitif Duo",
            "occasion": "Date Night",
            "notes": "Demo-Reservierung für Kalenderbefüllung",
        },
        {
            "reservation_date": (base_date + timedelta(days=3)).isoformat(),
            "slot_key": "late",
            "room_id": "raum-4",
            "table_id": "table-4",
            "guests": 4,
            "guest_name": "Demo Afterwork Circle",
            "occasion": "Afterwork Drinks",
            "notes": "Demo-Reservierung für Kalenderbefüllung",
        },
        {
            "reservation_date": (base_date + timedelta(days=5)).isoformat(),
            "slot_key": "early",
            "room_id": "raum-4",
            "table_id": "table-1",
            "guests": 2,
            "guest_name": "Demo Business Pair",
            "occasion": "Business Dinner",
            "notes": "Demo-Reservierung für Kalenderbefüllung",
        },
        {
            "reservation_date": (base_date + timedelta(days=7)).isoformat(),
            "slot_key": "late",
            "room_id": "raum-4",
            "table_id": "table-2",
            "guests": 3,
            "guest_name": "Demo Late Dinner",
            "occasion": "Geburtstag",
            "notes": "Demo-Reservierung für Kalenderbefüllung",
        },
        {
            "reservation_date": (base_date + timedelta(days=10)).isoformat(),
            "slot_key": "early",
            "room_id": "raum-4",
            "table_id": "table-4",
            "guests": 4,
            "guest_name": "Demo Lounge Table",
            "occasion": "Dinner",
            "notes": "Demo-Reservierung für Kalenderbefüllung",
        },
        {
            "reservation_date": "2026-03-21",
            "slot_key": "early",
            "room_id": "raum-4",
            "table_id": "table-1",
            "guests": 4,
            "guest_name": "Demo Full House Early 1",
            "occasion": "Dinner",
            "notes": "Demo-Vollbelegung für Kalenderhighlight",
        },
        {
            "reservation_date": "2026-03-21",
            "slot_key": "early",
            "room_id": "raum-4",
            "table_id": "table-2",
            "guests": 4,
            "guest_name": "Demo Full House Early 2",
            "occasion": "Dinner",
            "notes": "Demo-Vollbelegung für Kalenderhighlight",
        },
        {
            "reservation_date": "2026-03-21",
            "slot_key": "early",
            "room_id": "raum-4",
            "table_id": "table-3",
            "guests": 2,
            "guest_name": "Demo Full House Early 3",
            "occasion": "Aperitif",
            "notes": "Demo-Vollbelegung für Kalenderhighlight",
        },
        {
            "reservation_date": "2026-03-21",
            "slot_key": "early",
            "room_id": "raum-4",
            "table_id": "table-4",
            "guests": 4,
            "guest_name": "Demo Full House Early 4",
            "occasion": "Drinks",
            "notes": "Demo-Vollbelegung für Kalenderhighlight",
        },
        {
            "reservation_date": "2026-03-21",
            "slot_key": "late",
            "room_id": "raum-4",
            "table_id": "table-1",
            "guests": 4,
            "guest_name": "Demo Full House Late 1",
            "occasion": "Dinner",
            "notes": "Demo-Vollbelegung für Kalenderhighlight",
        },
        {
            "reservation_date": "2026-03-21",
            "slot_key": "late",
            "room_id": "raum-4",
            "table_id": "table-2",
            "guests": 4,
            "guest_name": "Demo Full House Late 2",
            "occasion": "Dinner",
            "notes": "Demo-Vollbelegung für Kalenderhighlight",
        },
        {
            "reservation_date": "2026-03-21",
            "slot_key": "late",
            "room_id": "raum-4",
            "table_id": "table-3",
            "guests": 2,
            "guest_name": "Demo Full House Late 3",
            "occasion": "Aperitif",
            "notes": "Demo-Vollbelegung für Kalenderhighlight",
        },
        {
            "reservation_date": "2026-03-21",
            "slot_key": "late",
            "room_id": "raum-4",
            "table_id": "table-4",
            "guests": 4,
            "guest_name": "Demo Full House Late 4",
            "occasion": "Drinks",
            "notes": "Demo-Vollbelegung für Kalenderhighlight",
        },
    ]

    with db_connection() as connection:
        for row in demo_rows:
            existing_row = connection.execute(
                """
                SELECT id
                FROM reservations
                WHERE guest_email = ?
                  AND reservation_date = ?
                  AND slot_key = ?
                  AND room_id = ?
                  AND table_id = ?
                """,
                (
                    DEMO_RESERVATION_EMAIL,
                    row["reservation_date"],
                    row["slot_key"],
                    row["room_id"],
                    row["table_id"],
                ),
            ).fetchone()
            if existing_row:
                continue

            connection.execute(
                """
                INSERT INTO reservations (
                    id, reservation_code, reservation_date, slot_key, room_id, table_id, guests,
                    guest_name, guest_email, guest_phone, occasion, notes, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"reservation_{secrets.token_hex(8)}",
                    secrets.token_hex(4).upper(),
                    row["reservation_date"],
                    row["slot_key"],
                    row["room_id"],
                    row["table_id"],
                    row["guests"],
                    row["guest_name"],
                    DEMO_RESERVATION_EMAIL,
                    "",
                    row["occasion"],
                    row["notes"],
                    "confirmed",
                    now_iso(),
                ),
            )


def page_products(page: str) -> list[dict]:
    with db_connection() as connection:
        sections = connection.execute(
            """
            SELECT page, section_key, tag, title, sort_order
            FROM product_sections
            WHERE page = ?
            ORDER BY sort_order, id
            """,
            (page,),
        ).fetchall()
        products = connection.execute(
            """
            SELECT page, section_key, sort_order, erp_id, category, title, teaser, ingredients, price, image_path,
                   quote_text, quote_author, special_heading_1, special_content_1,
                   special_heading_2, special_content_2, featured
            FROM products
            WHERE page = ?
            ORDER BY section_key, sort_order, id
            """,
            (page,),
        ).fetchall()

    products_by_section: dict[str, list[dict]] = {}
    for product in products:
        products_by_section.setdefault(product["section_key"], []).append(
            {
                "erpId": product["erp_id"],
                "category": product["category"],
                "title": product["title"],
                "teaser": product["teaser"],
                "ingredients": product["ingredients"],
                "price": product["price"],
                "imagePath": product["image_path"],
                "quote": {"text": product["quote_text"], "author": product["quote_author"]},
                "specialSections": [
                    {"heading": product["special_heading_1"], "content": product["special_content_1"]},
                    {"heading": product["special_heading_2"], "content": product["special_content_2"]},
                ],
                "featured": bool(product["featured"]),
            }
        )

    return [
        {
            "key": section["section_key"],
            "tag": section["tag"],
            "title": section["title"],
            "products": products_by_section.get(section["section_key"], []),
        }
        for section in sections
    ]


def product_by_erp_id(erp_id: str) -> sqlite3.Row | None:
    with db_connection() as connection:
        return connection.execute(
            """
            SELECT erp_id, page, section_key, category, title, teaser, ingredients, price, image_path
            FROM products
            WHERE erp_id = ?
            """,
            (erp_id,),
        ).fetchone()


def update_product_price_by_erp_id(erp_id: str, price: str) -> sqlite3.Row | None:
    with db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE products
            SET price = ?
            WHERE erp_id = ?
            """,
            (price, erp_id),
        )
        if cursor.rowcount == 0:
            return None

        return connection.execute(
            """
            SELECT erp_id, page, section_key, category, title, teaser, ingredients, price, image_path
            FROM products
            WHERE erp_id = ?
            """,
            (erp_id,),
        ).fetchone()


def read_json_file(path: Path, fallback):
    ensure_data_dir()
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_file(path: Path, payload) -> None:
    ensure_data_dir()
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def reservation_room(room_id: str) -> dict | None:
    return next((room for room in RESERVATION_ROOMS if room["id"] == room_id), None)


def reservation_slot(slot_key: str) -> dict | None:
    return next((slot for slot in RESERVATION_SLOTS if slot["key"] == slot_key), None)


def reservation_table(room: dict, table_id: str) -> dict | None:
    return next((table for table in room["tables"] if table["id"] == table_id), None)


def reservation_window() -> tuple[str, str]:
    today = datetime.now().date()
    max_day = today + timedelta(days=RESERVATION_BOOKING_WINDOW_DAYS)
    return today.isoformat(), max_day.isoformat()


def reservation_start_at(date_value: str, slot_key: str) -> datetime:
    slot = reservation_slot(slot_key)
    if not slot:
        raise ValueError("Der ausgewählte Zeitslot wurde nicht gefunden.")
    return datetime.strptime(f"{date_value} {slot['start']}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TIMEZONE)


def reservation_cancellation_deadline(date_value: str, slot_key: str) -> datetime:
    return reservation_start_at(date_value, slot_key) - timedelta(hours=RESERVATION_CANCELLATION_NOTICE_HOURS)


def reservation_config() -> dict:
    min_date, max_date = reservation_window()
    return {
        "bookingWindowDays": RESERVATION_BOOKING_WINDOW_DAYS,
        "minDate": min_date,
        "maxDate": max_date,
        "slots": RESERVATION_SLOTS,
        "rooms": RESERVATION_ROOMS,
    }


def iso_date_range(start_date: str, days: int) -> list[str]:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    return [(start + timedelta(days=offset)).isoformat() for offset in range(days)]


def validate_reservation_date(date_value: str) -> None:
    min_date, max_date = reservation_window()
    if not date_value:
        raise ValueError("Bitte ein Reservierungsdatum auswählen.")
    if date_value < min_date or date_value > max_date:
        raise ValueError("Reservierungen sind nur bis drei Wochen im Voraus möglich.")
    if datetime.strptime(date_value, "%Y-%m-%d").date().weekday() == 0:
        raise ValueError("Montag ist Ruhetag.")


def reservations_for_date(date_value: str, slot_key: str, room_id: str) -> list[sqlite3.Row]:
    with db_connection() as connection:
        return connection.execute(
            """
            SELECT id, reservation_code, reservation_date, slot_key, room_id, table_id, guests, guest_name,
                   guest_email, guest_phone, occasion, notes, status, created_at
            FROM reservations
            WHERE reservation_date = ? AND slot_key = ? AND room_id = ? AND status != 'cancelled'
            """,
            (date_value, slot_key, room_id),
        ).fetchall()


def reservation_by_id(reservation_id: str) -> sqlite3.Row | None:
    with db_connection() as connection:
        return connection.execute(
            """
            SELECT id, reservation_code, reservation_date, slot_key, room_id, table_id, guests, guest_name,
                   guest_email, guest_phone, occasion, notes, cancel_token, status, cancelled_at, created_at
            FROM reservations
            WHERE id = ?
            """,
            (reservation_id,),
        ).fetchone()


def reservations_for_guest_email(email: str, base_url: str | None = None) -> list[dict]:
    normalized_email = normalize_email(email)
    with db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, reservation_code, reservation_date, slot_key, room_id, table_id, guests, guest_name,
                   guest_email, guest_phone, occasion, notes, cancel_token, status, cancelled_at, created_at
            FROM reservations
            WHERE lower(guest_email) = ?
            ORDER BY reservation_date DESC, slot_key DESC, created_at DESC
            """,
            (normalized_email,),
        ).fetchall()

    resolved_base_url = base_url or reservation_public_base_url()
    return [reservation_details_payload(row, resolved_base_url) for row in rows]


def available_tables(date_value: str, slot_key: str, room_id: str, guests: int | None = None) -> list[dict]:
    room = reservation_room(room_id)
    if not room:
        raise ValueError("Der ausgewählte Raum wurde nicht gefunden.")
    if not reservation_slot(slot_key):
        raise ValueError("Der ausgewählte Zeitslot wurde nicht gefunden.")
    validate_reservation_date(date_value)

    if room["status"] != "bookable":
        return []

    reserved_table_ids = {row["table_id"] for row in reservations_for_date(date_value, slot_key, room_id)}
    tables: list[dict] = []
    for table in room["tables"]:
        fits_guest_count = guests is None or (table["capacityMin"] <= guests <= table["capacityMax"])
        if table["id"] in reserved_table_ids:
            availability = "reserved"
        elif not fits_guest_count:
            availability = "capacity_mismatch"
        else:
            availability = "available"

        tables.append(
            {
                **table,
                "availability": availability,
                "isAvailable": availability == "available",
            }
        )

    return tables


def reservation_calendar_days(start_date: str, days: int, slot_key: str, room_id: str, guests: int | None = None) -> list[dict]:
    room = reservation_room(room_id)
    if not room:
        raise ValueError("Der ausgewählte Raum wurde nicht gefunden.")
    if not reservation_slot(slot_key):
        raise ValueError("Der ausgewählte Zeitslot wurde nicht gefunden.")
    if days < 1 or days > 42:
        raise ValueError("Der Kalenderbereich muss zwischen 1 und 42 Tagen liegen.")

    min_date, max_date = reservation_window()
    entries: list[dict] = []

    for date_value in iso_date_range(start_date, days):
        if date_value < min_date:
            state = "past"
            summary = "Vergangen"
            free_tables = 0
        elif date_value > max_date:
            state = "outside_window"
            summary = "Außerhalb des 3-Wochen-Fensters"
            free_tables = 0
        elif datetime.strptime(date_value, "%Y-%m-%d").date().weekday() == 0:
            state = "closed"
            summary = "Montag ist Ruhetag"
            free_tables = 0
            slot_counts = {slot["key"]: 0 for slot in RESERVATION_SLOTS}
        elif room["status"] != "bookable":
            state = "event_only"
            summary = room["defaultStatusNote"]
            free_tables = 0
            slot_counts = {slot["key"]: 0 for slot in RESERVATION_SLOTS}
        else:
            slot_counts = {}
            for reservation_slot_item in RESERVATION_SLOTS:
                slot_tables = available_tables(date_value, reservation_slot_item["key"], room_id, guests)
                slot_counts[reservation_slot_item["key"]] = len([table for table in slot_tables if table["isAvailable"]])

            free_tables = slot_counts.get(slot_key, 0)
            if free_tables > 0:
                state = "available"
                summary = f"{free_tables} Tisch(e) frei"
            else:
                state = "fully_booked"
                summary = "Keine passenden Tische frei"

        entries.append(
            {
                "date": date_value,
                "state": state,
                "summary": summary,
                "freeTables": free_tables,
                "slotCounts": slot_counts,
            }
        )

    return entries


def reservation_public_base_url(host: str | None = None) -> str:
    configured = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    if host:
        return f"http://{host}"
    return f"http://localhost:{PORT}"


def reservation_qr_image_url(base_url: str, reservation_id: str) -> str:
    return f"{base_url}/reservations/qr-image/{quote(reservation_id, safe='')}.svg"


def reservation_qr_page_url(base_url: str, reservation_id: str) -> str:
    return f"{base_url}/reservations/qr/{quote(reservation_id, safe='')}"


def reservation_cancel_url(base_url: str, reservation_id: str, cancel_token: str) -> str:
    return (
        f"{base_url}/reservations/cancel?"
        f"reservationId={quote(reservation_id, safe='')}&token={quote(cancel_token, safe='')}"
    )


def format_reservation_datetime(date_value: str, slot_key: str) -> str:
    start_at = reservation_start_at(date_value, slot_key)
    slot = reservation_slot(slot_key)
    return f"{start_at.strftime('%A, %d.%m.%Y')} · {slot['label']}"


def qr_mask(mask_id: int, x: int, y: int) -> bool:
    if mask_id == 0:
        return (x + y) % 2 == 0
    raise ValueError("Unsupported QR mask.")


def qr_gf_multiply(left: int, right: int) -> int:
    result = 0
    for _ in range(8):
        if right & 1:
            result ^= left
        right >>= 1
        carry = left & 0x80
        left = (left << 1) & 0xFF
        if carry:
            left ^= 0x1D
    return result


def qr_rs_generator(degree: int) -> list[int]:
    result = [1]
    root = 1
    for _ in range(degree):
        next_result = [0] * (len(result) + 1)
        for index, coefficient in enumerate(result):
            next_result[index] ^= qr_gf_multiply(coefficient, root)
            next_result[index + 1] ^= coefficient
        result = next_result
        root = qr_gf_multiply(root, 0x02)
    return result


def qr_rs_remainder(data: list[int], degree: int) -> list[int]:
    generator = qr_rs_generator(degree)
    remainder = [0] * degree
    for value in data:
        factor = value ^ remainder[0]
        remainder = remainder[1:] + [0]
        for index, coefficient in enumerate(generator[:-1]):
            remainder[index] ^= qr_gf_multiply(coefficient, factor)
    return remainder


def qr_format_bits(mask_id: int) -> int:
    data = (0b01 << 3) | mask_id
    bits = data << 10
    generator = 0x537
    for shift in range(14, 9, -1):
        if (bits >> shift) & 1:
            bits ^= generator << (shift - 10)
    return ((data << 10) | bits) ^ 0x5412


def reservation_qr_matrix(payload: str) -> list[list[bool]]:
    version = 5
    size = 17 + version * 4
    data_capacity = 108
    ecc_codewords = 26
    encoded = payload.encode("utf-8")
    if len(encoded) > data_capacity - 2:
        raise ValueError("Die Reservierungs-ID ist für den lokalen QR-Code zu lang.")

    bit_buffer: list[int] = []

    def append_bits(value: int, length: int):
        for shift in range(length - 1, -1, -1):
            bit_buffer.append((value >> shift) & 1)

    append_bits(0b0100, 4)
    append_bits(len(encoded), 8)
    for byte in encoded:
        append_bits(byte, 8)

    max_bits = data_capacity * 8
    append_bits(0, min(4, max_bits - len(bit_buffer)))
    while len(bit_buffer) % 8 != 0:
        bit_buffer.append(0)

    data_codewords = []
    for index in range(0, len(bit_buffer), 8):
        value = 0
        for bit in bit_buffer[index:index + 8]:
            value = (value << 1) | bit
        data_codewords.append(value)

    pad_bytes = [0xEC, 0x11]
    while len(data_codewords) < data_capacity:
        data_codewords.append(pad_bytes[len(data_codewords) % 2])

    codewords = data_codewords + qr_rs_remainder(data_codewords, ecc_codewords)
    data_bits = []
    for codeword in codewords:
        append_target = []
        for shift in range(7, -1, -1):
            append_target.append((codeword >> shift) & 1)
        data_bits.extend(append_target)

    matrix: list[list[bool | None]] = [[None] * size for _ in range(size)]
    is_function = [[False] * size for _ in range(size)]

    def set_function(x: int, y: int, value: bool):
        if 0 <= x < size and 0 <= y < size:
            matrix[y][x] = value
            is_function[y][x] = True

    def draw_finder(origin_x: int, origin_y: int):
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                x = origin_x + dx
                y = origin_y + dy
                if not (0 <= x < size and 0 <= y < size):
                    continue
                if 0 <= dx <= 6 and 0 <= dy <= 6:
                    value = dx in {0, 6} or dy in {0, 6} or (2 <= dx <= 4 and 2 <= dy <= 4)
                else:
                    value = False
                set_function(x, y, value)

    def draw_alignment(center_x: int, center_y: int):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                set_function(center_x + dx, center_y + dy, max(abs(dx), abs(dy)) != 1)

    draw_finder(0, 0)
    draw_finder(size - 7, 0)
    draw_finder(0, size - 7)
    draw_alignment(30, 30)

    for index in range(8, size - 8):
        set_function(index, 6, index % 2 == 0)
        set_function(6, index, index % 2 == 0)

    for index in range(9):
        if index != 6:
            set_function(8, index, False)
            set_function(index, 8, False)
    for index in range(8):
        set_function(size - 1 - index, 8, False)
        if index < 7:
            set_function(8, size - 7 + index, False)

    set_function(8, size - 8, True)

    bit_index = 0
    upward = True
    right = size - 1
    while right >= 1:
        if right == 6:
            right -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for y in rows:
            for x in [right, right - 1]:
                if is_function[y][x]:
                    continue
                bit = data_bits[bit_index] if bit_index < len(data_bits) else 0
                bit_index += 1
                if qr_mask(0, x, y):
                    bit ^= 1
                matrix[y][x] = bool(bit)
        upward = not upward
        right -= 2

    format_bits = qr_format_bits(0)
    for index in range(6):
        set_function(8, index, ((format_bits >> index) & 1) != 0)
    set_function(8, 7, ((format_bits >> 6) & 1) != 0)
    set_function(8, 8, ((format_bits >> 7) & 1) != 0)
    set_function(7, 8, ((format_bits >> 8) & 1) != 0)
    for index in range(9, 15):
        set_function(14 - index, 8, ((format_bits >> index) & 1) != 0)
    for index in range(8):
        set_function(size - 1 - index, 8, ((format_bits >> index) & 1) != 0)
    for index in range(8, 15):
        set_function(8, size - 15 + index, ((format_bits >> index) & 1) != 0)

    return [[bool(cell) for cell in row] for row in matrix]


def reservation_qr_svg(payload: str, module_size: int = 14, quiet_zone: int = 4) -> str:
    matrix = reservation_qr_matrix(payload)
    size = len(matrix)
    full_size = (size + quiet_zone * 2) * module_size
    rects = []
    for y, row in enumerate(matrix):
        for x, cell in enumerate(row):
            if cell:
                rects.append(
                    f'<rect x="{(x + quiet_zone) * module_size}" y="{(y + quiet_zone) * module_size}" '
                    f'width="{module_size}" height="{module_size}" />'
                )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {full_size} {full_size}" '
        f'width="{full_size}" height="{full_size}" shape-rendering="crispEdges">'
        f'<rect width="{full_size}" height="{full_size}" fill="#ffffff"/>'
        f'<g fill="#111111">{"".join(rects)}</g></svg>'
    )


def reservation_qr_email_markup(payload: str, module_size: int = 5, quiet_zone: int = 4) -> str:
    matrix = reservation_qr_matrix(payload)
    full_size = len(matrix) + quiet_zone * 2
    rows = []
    for y in range(full_size):
        cells = []
        for x in range(full_size):
            in_matrix = quiet_zone <= x < full_size - quiet_zone and quiet_zone <= y < full_size - quiet_zone
            is_dark = matrix[y - quiet_zone][x - quiet_zone] if in_matrix else False
            color = "#111111" if is_dark else "#ffffff"
            cells.append(
                f'<td style="width:{module_size}px;height:{module_size}px;background:{color};padding:0;margin:0;font-size:0;line-height:0;"></td>'
            )
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<table role="presentation" align="center" cellspacing="0" cellpadding="0" '
        'style="margin:0 auto 14px auto;border-collapse:separate;border-spacing:0;background:#ffffff;'
        'border-radius:18px;">'
        '<tr><td style="padding:14px;">'
        '<table role="presentation" align="center" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">'
        f"{''.join(rows)}</table>"
        "</td></tr></table>"
    )


def reservation_details_payload(reservation_row: sqlite3.Row | dict, base_url: str | None = None) -> dict:
    room = reservation_room(reservation_row["room_id"])
    slot = reservation_slot(reservation_row["slot_key"])
    table = reservation_table(room, reservation_row["table_id"]) if room else None
    cancel_token = reservation_row["cancel_token"]
    payload = {
        "id": reservation_row["id"],
        "reservationCode": reservation_row["reservation_code"],
        "date": reservation_row["reservation_date"],
        "slotKey": reservation_row["slot_key"],
        "slotLabel": slot["label"] if slot else reservation_row["slot_key"],
        "roomId": reservation_row["room_id"],
        "roomName": room["name"] if room else reservation_row["room_id"],
        "tableId": reservation_row["table_id"],
        "tableLabel": table["label"] if table else reservation_row["table_id"],
        "guests": reservation_row["guests"],
        "name": reservation_row["guest_name"],
        "email": reservation_row["guest_email"],
        "phone": reservation_row["guest_phone"],
        "occasion": reservation_row["occasion"],
        "notes": reservation_row["notes"],
        "status": reservation_row["status"],
        "cancelledAt": reservation_row["cancelled_at"],
        "createdAt": reservation_row["created_at"],
        "scheduledLabel": format_reservation_datetime(reservation_row["reservation_date"], reservation_row["slot_key"]),
        "cancellationDeadlineLabel": reservation_cancellation_deadline(
            reservation_row["reservation_date"], reservation_row["slot_key"]
        ).strftime("%d.%m.%Y · %H:%M"),
    }
    if base_url:
        payload["qrCodeUrl"] = reservation_qr_page_url(base_url, reservation_row["id"])
        payload["qrImageUrl"] = reservation_qr_image_url(base_url, reservation_row["id"])
        payload["cancelUrl"] = reservation_cancel_url(base_url, reservation_row["id"], cancel_token)
    return payload


def build_reservation_confirmation_email(reservation: dict, base_url: str) -> EmailMessage:
    settings = smtp_settings()
    message = EmailMessage()
    message["Subject"] = f"Deine Reservierung bei Bavarian RoboTaste · {reservation['scheduledLabel']}"
    message["From"] = settings["mail_from"]
    message["To"] = reservation["email"]

    plain_text = (
        f"Hallo {reservation['name']}\n\n"
        "deine Reservierung ist bei uns eingegangen.\n\n"
        f"Raum: {reservation['roomName']}\n"
        f"Tisch: {reservation['tableLabel']}\n"
        f"Zeit: {reservation['scheduledLabel']}\n"
        f"Personen: {reservation['guests']}\n"
        f"Reservierungs-ID: {reservation['id']}\n"
        f"Reservierungscode: {reservation['reservationCode']}\n\n"
        f"QR-Code öffnen: {reservation['qrCodeUrl']}\n"
        f"Reservierung löschen: {reservation['cancelUrl']}\n"
        f"Bitte beachte: Eine Löschung ist nur bis {RESERVATION_CANCELLATION_NOTICE_HOURS} Stunden vor Termin möglich.\n\n"
        "Wir freuen uns auf deinen Besuch.\n"
        "Bavarian RoboTaste\n"
    )
    message.set_content(plain_text)

    qr_link = html.escape(reservation["qrCodeUrl"])
    qr_image = html.escape(reservation["qrImageUrl"])
    cancel_link = html.escape(reservation["cancelUrl"])
    guest_name = html.escape(reservation["name"])
    room_name = html.escape(reservation["roomName"])
    table_label = html.escape(reservation["tableLabel"])
    scheduled_label = html.escape(reservation["scheduledLabel"])
    reservation_id = html.escape(reservation["id"])
    reservation_code = html.escape(reservation["reservationCode"])
    occasion = html.escape(reservation["occasion"] or "Kein besonderer Anlass hinterlegt")
    notes = html.escape(reservation["notes"] or "Keine Zusatznotizen")
    cancellation_deadline = html.escape(reservation["cancellationDeadlineLabel"])

    qr_media_markup = f'<a href="{qr_link}" style="text-decoration:none;color:inherit;">{reservation_qr_email_markup(reservation["id"])}</a>'

    html_body = f"""
<!DOCTYPE html>
<html lang="de">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  </head>
  <body style="margin:0;padding:0;background:#07131c;color:#edf1f3;font-family:Trebuchet MS,Segoe UI,sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;background:#07131c;">
      <tr>
        <td style="padding:12px 8px;background:radial-gradient(circle at top right, rgba(242,106,61,0.22), transparent 34%), #07131c;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%;max-width:560px;margin:0 auto;border-collapse:separate;border-spacing:0;border:1px solid rgba(255,255,255,0.1);border-radius:24px;overflow:hidden;background:rgba(11,24,35,0.92);">
            <tr>
              <td style="padding:20px 16px 10px;">
                <div style="color:#77e5d8;font-size:12px;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:12px;">Reservierung bestätigt</div>
                <div style="margin:0 0 12px;font-family:Georgia,Times New Roman,serif;font-size:28px;line-height:1.08;font-weight:700;">Dein Abend steht.</div>
                <p style="margin:0;color:#a7b4bc;font-size:15px;line-height:1.7;">
                  Hallo {guest_name}, wir freuen uns auf deinen Besuch im <strong style="color:#edf1f3;">{room_name}</strong>.
                  Unten findest du deinen QR-Code für den Check-in, alle Eckdaten und den Storno-Link.
                </p>
              </td>
            </tr>

            <tr>
              <td style="padding:8px 16px 0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:separate;border-spacing:0;">
                  <tr>
                    <td style="padding:16px;border:1px solid rgba(119,229,216,0.18);border-radius:20px;background:linear-gradient(180deg, rgba(119,229,216,0.08), rgba(255,255,255,0.03));text-align:center;">
                      <div style="color:#77e5d8;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:12px;">Check-in QR</div>
                      {qr_media_markup}
                      <p style="margin:0;color:#a7b4bc;line-height:1.6;">
                        Tippe auf den QR-Code, um ihn im Browser groß zu öffnen. Darin steckt deine lange Reservierungs-ID.
                      </p>
                      <p style="margin:12px 0 0;color:#a7b4bc;font-size:13px;line-height:1.6;">
                        Falls dein Mailprogramm eingebettete Bilder blockiert, kannst du den Code auch direkt hier öffnen:<br />
                        <a href="{qr_image}" style="color:#77e5d8;">QR-Code direkt laden</a>
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:14px 16px 0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:separate;border-spacing:0;">
                  <tr>
                    <td style="padding:18px;border:1px solid rgba(255,255,255,0.08);border-radius:20px;background:rgba(255,255,255,0.03);">
                      <div style="color:#77e5d8;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;">Zeitfenster</div>
                      <div style="margin-top:6px;font-size:20px;font-weight:700;line-height:1.35;word-break:break-word;">{scheduled_label}</div>

                      <div style="margin-top:18px;color:#77e5d8;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;">Raum &amp; Tisch</div>
                      <div style="margin-top:6px;font-size:17px;font-weight:700;line-height:1.45;word-break:break-word;">{room_name} · {table_label}</div>

                      <div style="margin-top:18px;color:#77e5d8;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;">Personen</div>
                      <div style="margin-top:6px;font-size:18px;font-weight:700;">{reservation['guests']} Gäste</div>

                      <div style="margin-top:18px;color:#77e5d8;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;">Anlass</div>
                      <div style="margin-top:6px;color:#a7b4bc;line-height:1.6;">{occasion}</div>

                      <div style="margin-top:18px;color:#77e5d8;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;">Notizen</div>
                      <div style="margin-top:6px;color:#a7b4bc;line-height:1.6;">{notes}</div>

                      <div style="margin-top:18px;color:#77e5d8;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;">Code</div>
                      <div style="margin-top:6px;">
                        <span style="display:inline-block;margin:0 8px 8px 0;padding:9px 12px;border-radius:999px;background:rgba(119,229,216,0.12);color:#77e5d8;font-weight:700;">Code {reservation_code}</span>
                      </div>

                      <div style="margin-top:10px;color:#77e5d8;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;">Reservierungs-ID</div>
                      <div style="margin-top:6px;padding:12px 14px;border-radius:16px;background:rgba(242,106,61,0.12);color:#ffd9cd;font-weight:700;line-height:1.55;word-break:break-all;">{reservation_id}</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:14px 16px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:separate;border-spacing:0;">
                  <tr>
                    <td style="padding:18px 18px;border:1px solid rgba(242,106,61,0.24);border-radius:20px;background:rgba(242,106,61,0.08);">
                      <div style="font-weight:700;font-size:18px;margin-bottom:8px;">Reservierung verwalten</div>
                      <p style="margin:0 0 14px;color:#ffd9cd;line-height:1.7;">
                        Falls sich etwas ändert, kannst du deine Reservierung über den Link unten löschen.
                        Bitte beachte: Das geht nur bis <strong>{cancellation_deadline}</strong>, also spätestens {RESERVATION_CANCELLATION_NOTICE_HOURS} Stunden vor Beginn.
                      </p>
                      <a href="{cancel_link}" style="display:inline-block;padding:15px 22px;border-radius:999px;background:linear-gradient(135deg, #f26a3d, #db4d1f);color:#fff5f0;text-decoration:none;font-weight:700;">Reservierung löschen</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    message.add_alternative(html_body, subtype="html")
    return message


def create_reservation(payload: dict, base_url: str) -> tuple[dict, str | None]:
    guest_name = str(payload.get("name", "")).strip()
    guest_email = normalize_email(str(payload.get("email", "")))
    guest_phone = str(payload.get("phone", "")).strip()
    reservation_date = str(payload.get("date", "")).strip()
    slot_key = str(payload.get("slotKey", "")).strip()
    room_id = str(payload.get("roomId", "")).strip()
    table_id = str(payload.get("tableId", "")).strip()
    occasion = str(payload.get("occasion", "")).strip()
    notes = str(payload.get("notes", "")).strip()

    try:
        guests = int(payload.get("guests", 0))
    except (TypeError, ValueError):
        guests = 0

    missing = [
        field
        for field, value in {
            "name": guest_name,
            "email": guest_email,
            "date": reservation_date,
            "slotKey": slot_key,
            "roomId": room_id,
            "tableId": table_id,
            "guests": guests,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"missing_fields:{','.join(missing)}")

    room = reservation_room(room_id)
    if not room:
        raise ValueError("Der ausgewählte Raum wurde nicht gefunden.")
    if room["status"] != "bookable":
        raise ValueError("Dieser Raum ist aktuell nur für Veranstaltungen vorgesehen.")

    table = reservation_table(room, table_id)
    if not table:
        raise ValueError("Der ausgewählte Tisch wurde nicht gefunden.")
    if guests < table["capacityMin"] or guests > table["capacityMax"]:
        raise ValueError("Die Personenzahl passt nicht zur Kapazität des gewählten Tisches.")

    free_tables = available_tables(reservation_date, slot_key, room_id, guests)
    selected_table = next((item for item in free_tables if item["id"] == table_id), None)
    if not selected_table or not selected_table["isAvailable"]:
        raise ValueError("Der ausgewählte Tisch ist in diesem Slot nicht mehr verfügbar.")

    reservation_id = f"reservation_{secrets.token_hex(24)}"
    reservation_code = secrets.token_hex(4).upper()
    cancel_token = secrets.token_urlsafe(24)
    created_at = now_iso()

    with db_connection() as connection:
        connection.execute(
            """
            INSERT INTO reservations (
                id, reservation_code, reservation_date, slot_key, room_id, table_id, guests,
                guest_name, guest_email, guest_phone, occasion, notes, cancel_token, status, cancelled_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reservation_id,
                reservation_code,
                reservation_date,
                slot_key,
                room_id,
                table_id,
                guests,
                guest_name,
                guest_email,
                guest_phone,
                occasion,
                notes,
                cancel_token,
                "requested",
                "",
                created_at,
            ),
        )
    reservation = reservation_details_payload(
        {
            "id": reservation_id,
            "reservation_code": reservation_code,
            "reservation_date": reservation_date,
            "slot_key": slot_key,
            "room_id": room_id,
            "table_id": table_id,
            "guests": guests,
            "guest_name": guest_name,
            "guest_email": guest_email,
            "guest_phone": guest_phone,
            "occasion": occasion,
            "notes": notes,
            "cancel_token": cancel_token,
            "status": "requested",
            "cancelled_at": "",
            "created_at": created_at,
        },
        base_url,
    )

    mail_error = None
    try:
        send_messages([build_reservation_confirmation_email(reservation, base_url)])
    except Exception as exc:
        mail_error = str(exc)

    return reservation, mail_error


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def smtp_settings() -> dict:
    return {
        "host": os.environ["SMTP_HOST"],
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ["SMTP_USER"],
        "password": os.environ["SMTP_PASS"],
        "mail_from": os.environ.get("MAIL_FROM", os.environ["SMTP_USER"]),
        "registration_url": os.environ.get("REGISTRATION_URL", "http://localhost:8080/register.html"),
    }


def send_messages(messages: list[EmailMessage]) -> None:
    settings = smtp_settings()

    with smtplib.SMTP(settings["host"], settings["port"], timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings["user"], settings["password"])
        for message in messages:
            smtp.send_message(message)


def build_thank_you_message(first_name: str, registration_url: str) -> str:
    return (
        f"Hallo {first_name}\n\n"
        "vielen Dank für deine Nachricht an Bavarian RoboTaste.\n\n"
        "Wir haben deine Anfrage erhalten und leiten sie intern weiter. "
        "Unser Team meldet sich so schnell wie möglich bei dir.\n\n"
        "Wenn du dich schon jetzt registrierst, können wir deine künftigen "
        "Besuche besser begleiten. Außerdem wartet bei jedem Restaurantbesuch "
        "eine kleine Überraschung auf dich.\n\n"
        f"Hier kannst du dich registrieren:\n{registration_url}\n\n"
        "Beste Grüße\n"
        "Bavarian RoboTaste\n"
    )


def build_registration_code_message(first_name: str, code: str) -> str:
    return (
        f"Hallo {first_name}\n\n"
        "dein Bestätigungscode für die Registrierung bei Bavarian RoboTaste lautet:\n\n"
        f"{code}\n\n"
        f"Der Code ist {REGISTRATION_CODE_TTL_MINUTES} Minuten gültig.\n\n"
        "Falls du diese Registrierung nicht angefordert hast, kannst du diese E-Mail ignorieren.\n\n"
        "Beste Grüße\n"
        "Bavarian RoboTaste\n"
    )


def build_registration_success_message(first_name: str, registration_url: str) -> str:
    return (
        f"Hallo {first_name}\n\n"
        "deine Registrierung bei Bavarian RoboTaste ist jetzt abgeschlossen.\n\n"
        "Ab sofort können wir deine künftigen Besuche, Reservierungen und besondere Überraschungen "
        "besser auf dich abstimmen.\n\n"
        f"Hier findest du deine Registrierungsseite erneut:\n{registration_url}\n\n"
        "Bis bald bei Bavarian RoboTaste\n"
        "Bavarian RoboTaste\n"
    )


def build_contact_messages(payload: dict) -> list[EmailMessage]:
    settings = smtp_settings()
    name = payload["name"].strip()
    first_name = name.split()[0]
    sender_email = payload["email"].strip()
    topic = payload["topic"].strip()
    message = payload["message"].strip()

    internal_message = EmailMessage()
    internal_message["Subject"] = f"Neue Kontaktanfrage: {topic}"
    internal_message["From"] = settings["mail_from"]
    internal_message["To"] = settings["user"]
    internal_message["Reply-To"] = sender_email
    internal_message.set_content(
        "Neue Nachricht über das Kontaktformular\n\n"
        f"Name: {name}\n"
        f"E-Mail: {sender_email}\n"
        f"Thema: {topic}\n\n"
        f"Nachricht:\n{message}\n"
    )

    thank_you_message = EmailMessage()
    thank_you_message["Subject"] = "Danke für deine Nachricht an Bavarian RoboTaste"
    thank_you_message["From"] = settings["mail_from"]
    thank_you_message["To"] = sender_email
    thank_you_message.set_content(build_thank_you_message(first_name, settings["registration_url"]))

    return [internal_message, thank_you_message]


def build_registration_code_email(first_name: str, email: str, code: str) -> EmailMessage:
    settings = smtp_settings()
    message = EmailMessage()
    message["Subject"] = "Dein Bestätigungscode für Bavarian RoboTaste"
    message["From"] = settings["mail_from"]
    message["To"] = email
    message.set_content(build_registration_code_message(first_name, code))
    return message


def build_registration_success_email(first_name: str, email: str) -> EmailMessage:
    settings = smtp_settings()
    message = EmailMessage()
    message["Subject"] = "Deine Registrierung bei Bavarian RoboTaste ist abgeschlossen"
    message["From"] = settings["mail_from"]
    message["To"] = email
    message.set_content(build_registration_success_message(first_name, settings["registration_url"]))
    return message


def reservation_qr_document(reservation: dict) -> str:
    room_name = html.escape(reservation["roomName"])
    scheduled_label = html.escape(reservation["scheduledLabel"])
    reservation_id = html.escape(reservation["id"])
    qr_svg = reservation_qr_svg(reservation["id"], module_size=12)
    return f"""<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Reservierungs-QR | Bavarian RoboTaste</title>
  </head>
  <body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#07131c;color:#edf1f3;font-family:Trebuchet MS,Segoe UI,sans-serif;">
    <main style="width:min(calc(100% - 24px), 760px);padding:28px;border:1px solid rgba(255,255,255,0.1);border-radius:32px;background:rgba(11,24,35,0.94);text-align:center;">
      <div style="color:#77e5d8;font-size:12px;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:12px;">Check-in QR</div>
      <h1 style="margin:0 0 10px;font-family:Georgia,Times New Roman,serif;font-size:42px;line-height:1.04;">Reservierungs-ID im Vollbild</h1>
      <p style="margin:0 auto 20px;max-width:40ch;color:#a7b4bc;line-height:1.7;">{room_name} · {scheduled_label}<br />{reservation_id}</p>
      <div style="display:inline-block;border-radius:24px;background:#fff;padding:16px;">{qr_svg}</div>
    </main>
  </body>
</html>"""


def cancel_reservation(reservation_id: str, cancel_token: str) -> tuple[dict, str]:
    reservation_row = reservation_by_id(reservation_id)
    if not reservation_row or reservation_row["cancel_token"] != cancel_token:
        raise ValueError("Diese Reservierung konnte nicht gefunden werden.")
    if reservation_row["status"] == "cancelled":
        return reservation_details_payload(reservation_row), "already_cancelled"

    if now_local() > reservation_cancellation_deadline(reservation_row["reservation_date"], reservation_row["slot_key"]):
        raise ValueError(
            f"Eine Löschung ist nur bis {RESERVATION_CANCELLATION_NOTICE_HOURS} Stunden vor dem Termin möglich."
        )

    cancelled_at = now_iso()
    with db_connection() as connection:
        connection.execute(
            """
            UPDATE reservations
            SET status = 'cancelled', cancelled_at = ?
            WHERE id = ?
            """,
            (cancelled_at, reservation_id),
        )

    refreshed_row = reservation_by_id(reservation_id)
    return reservation_details_payload(refreshed_row), "cancelled"


def reservation_cancel_confirmation_document(reservation: dict, confirm_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Reservierung löschen | Bavarian RoboTaste</title>
  </head>
  <body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#07131c;color:#edf1f3;font-family:Trebuchet MS,Segoe UI,sans-serif;">
    <div style="position:fixed;inset:0;background:rgba(4,10,16,0.8);backdrop-filter:blur(10px);"></div>
    <main style="position:relative;z-index:1;width:min(calc(100% - 24px), 760px);padding:28px;border:1px solid rgba(255,255,255,0.1);border-radius:32px;background:rgba(11,24,35,0.94);box-shadow:0 24px 80px rgba(0,0,0,0.28);">
      <div style="color:#f26a3d;font-size:12px;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:12px;">Bestätigung</div>
      <h1 style="margin:0 0 12px;font-family:Georgia,Times New Roman,serif;font-size:42px;line-height:1.04;">Reservierung wirklich löschen?</h1>
      <p style="margin:0 0 22px;color:#a7b4bc;line-height:1.8;">
        Du bist dabei, deine Reservierung für <strong>{html.escape(reservation['scheduledLabel'])}</strong> im
        <strong>{html.escape(reservation['roomName'])}</strong> an <strong>{html.escape(reservation['tableLabel'])}</strong> zu löschen.
      </p>
      <div style="display:grid;gap:12px;padding:18px 20px;border:1px solid rgba(255,255,255,0.08);border-radius:22px;background:rgba(255,255,255,0.03);margin-bottom:18px;">
        <p style="margin:0;"><strong>Reservierungscode</strong><br /><span style="color:#a7b4bc;">{html.escape(reservation['reservationCode'])}</span></p>
        <p style="margin:0;"><strong>Gast</strong><br /><span style="color:#a7b4bc;">{html.escape(reservation['name'])}</span></p>
        <p style="margin:0;"><strong>Frist</strong><br /><span style="color:#a7b4bc;">Löschung nur bis {html.escape(reservation['cancellationDeadlineLabel'])}</span></p>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:12px;">
        <a href="{html.escape(confirm_url)}" style="display:inline-flex;align-items:center;justify-content:center;min-height:54px;padding:0 22px;border-radius:999px;background:linear-gradient(135deg, #f26a3d, #db4d1f);color:#fff5f0;text-decoration:none;font-weight:700;">Ja, Reservierung löschen</a>
        <a href="/" style="display:inline-flex;align-items:center;justify-content:center;min-height:54px;padding:0 22px;border-radius:999px;border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.04);color:#edf1f3;text-decoration:none;font-weight:700;">Abbrechen</a>
      </div>
    </main>
  </body>
</html>"""


def reservation_cancel_document(title: str, body: str, tone: str = "success") -> str:
    accent = "#77e5d8" if tone == "success" else "#f26a3d"
    return f"""<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(title)} | Bavarian RoboTaste</title>
  </head>
  <body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#07131c;color:#edf1f3;font-family:Trebuchet MS,Segoe UI,sans-serif;">
    <main style="width:min(calc(100% - 24px), 720px);padding:28px;border:1px solid rgba(255,255,255,0.1);border-radius:32px;background:rgba(11,24,35,0.94);">
      <div style="color:{accent};font-size:12px;letter-spacing:0.18em;text-transform:uppercase;margin-bottom:12px;">Reservierung</div>
      <h1 style="margin:0 0 12px;font-family:Georgia,Times New Roman,serif;font-size:42px;line-height:1.04;">{html.escape(title)}</h1>
      <p style="margin:0;color:#a7b4bc;line-height:1.8;">{body}</p>
    </main>
  </body>
</html>"""


def create_password_hash(password: str) -> dict:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": PASSWORD_HASH_ITERATIONS,
        "salt": salt.hex(),
        "hash": derived_key.hex(),
    }


def verify_password_hash(password: str, password_state: dict) -> bool:
    if not password_state:
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(password_state["salt"]),
        int(password_state["iterations"]),
    )
    return secrets.compare_digest(derived_key.hex(), password_state["hash"])


def guest_profiles() -> list[dict]:
    profiles = read_json_file(GUEST_PROFILES_FILE, [])
    return profiles if isinstance(profiles, list) else []


def pending_registrations() -> dict:
    registrations = read_json_file(PENDING_REGISTRATIONS_FILE, {})
    return registrations if isinstance(registrations, dict) else {}


def sessions() -> dict:
    auth_sessions = read_json_file(SESSIONS_FILE, {})
    return auth_sessions if isinstance(auth_sessions, dict) else {}


def public_profile(profile: dict) -> dict:
    return {
        "id": profile["id"],
        "firstName": profile["firstName"],
        "email": profile["email"],
        "phone": profile.get("phone", ""),
        "createdAt": profile.get("createdAt", ""),
    }


def find_profile_by_email(email: str) -> dict | None:
    normalized_email = normalize_email(email)
    return next((profile for profile in guest_profiles() if normalize_email(profile["email"]) == normalized_email), None)


def find_profile_by_id(profile_id: str) -> dict | None:
    return next((profile for profile in guest_profiles() if profile["id"] == profile_id), None)


def is_code_expired(expires_at: str) -> bool:
    return datetime.fromisoformat(expires_at) < now_utc()


def create_session(profile_id: str) -> str:
    with DATA_LOCK:
        auth_sessions = sessions()
        token = secrets.token_urlsafe(32)
        auth_sessions[token] = {
            "guestProfileId": profile_id,
            "createdAt": now_iso(),
        }
        write_json_file(SESSIONS_FILE, auth_sessions)
    return token


def delete_session(token: str) -> None:
    with DATA_LOCK:
        auth_sessions = sessions()
        auth_sessions.pop(token, None)
        write_json_file(SESSIONS_FILE, auth_sessions)


def profile_for_token(token: str) -> dict | None:
    auth_sessions = sessions()
    session = auth_sessions.get(token)
    if not session:
        return None
    return find_profile_by_id(session["guestProfileId"])


def request_registration_code(payload: dict) -> None:
    email = normalize_email(payload["email"])

    with DATA_LOCK:
        if find_profile_by_email(email):
            raise ValueError("Für diese E-Mail-Adresse existiert bereits ein Gastprofil.")

        registrations = pending_registrations()
        code = generate_verification_code()
        registrations[email] = {
            "firstName": payload["firstName"].strip(),
            "email": email,
            "phone": payload.get("phone", "").strip(),
            "verificationCode": code,
            "requestedAt": now_iso(),
            "expiresAt": (now_utc() + timedelta(minutes=REGISTRATION_CODE_TTL_MINUTES)).isoformat(),
            "verifiedAt": None,
        }
        write_json_file(PENDING_REGISTRATIONS_FILE, registrations)

    send_messages([build_registration_code_email(payload["firstName"].strip(), email, code)])


def verify_registration_code(payload: dict) -> None:
    email = normalize_email(payload["email"])
    code = str(payload.get("verificationCode", "")).strip()

    with DATA_LOCK:
        registrations = pending_registrations()
        registration = registrations.get(email)
        if not registration:
            raise ValueError("Für diese E-Mail-Adresse gibt es keine offene Registrierung.")
        if is_code_expired(registration["expiresAt"]):
            registrations.pop(email, None)
            write_json_file(PENDING_REGISTRATIONS_FILE, registrations)
            raise ValueError("Der Bestätigungscode ist abgelaufen. Bitte fordere einen neuen Code an.")
        if not code or registration["verificationCode"] != code:
            raise ValueError("Der eingegebene Bestätigungscode ist nicht korrekt.")

        registration["verifiedAt"] = now_iso()
        registrations[email] = registration
        write_json_file(PENDING_REGISTRATIONS_FILE, registrations)


def complete_registration(payload: dict) -> tuple[dict, str]:
    email = normalize_email(payload["email"])
    password = payload["password"]

    with DATA_LOCK:
        registrations = pending_registrations()
        registration = registrations.get(email)
        if not registration:
            raise ValueError("Für diese E-Mail-Adresse gibt es keine offene Registrierung.")
        if is_code_expired(registration["expiresAt"]):
            registrations.pop(email, None)
            write_json_file(PENDING_REGISTRATIONS_FILE, registrations)
            raise ValueError("Der Bestätigungscode ist abgelaufen. Bitte fordere einen neuen Code an.")
        if not registration.get("verifiedAt"):
            raise ValueError("Bitte bestätige zuerst deinen E-Mail-Code.")
        if find_profile_by_email(email):
            raise ValueError("Für diese E-Mail-Adresse existiert bereits ein Gastprofil.")

        guest_profile = {
            "id": f"guest_{secrets.token_hex(8)}",
            "firstName": registration["firstName"],
            "email": registration["email"],
            "phone": registration["phone"],
            "createdAt": now_iso(),
            "registrationSource": "website",
            "password": create_password_hash(password),
        }

        profiles = guest_profiles()
        profiles.append(guest_profile)
        write_json_file(GUEST_PROFILES_FILE, profiles)

        registrations.pop(email, None)
        write_json_file(PENDING_REGISTRATIONS_FILE, registrations)

    send_messages([build_registration_success_email(guest_profile["firstName"], guest_profile["email"])])
    token = create_session(guest_profile["id"])
    return guest_profile, token


def login_user(email: str, password: str) -> tuple[dict, str]:
    profile = find_profile_by_email(email)
    if not profile or not verify_password_hash(password, profile.get("password", {})):
        raise ValueError("E-Mail oder Passwort ist nicht korrekt.")

    token = create_session(profile["id"])
    return profile, token


def update_profile(profile_id: str, payload: dict) -> dict:
    with DATA_LOCK:
        profiles = guest_profiles()
        profile = next((item for item in profiles if item["id"] == profile_id), None)
        if not profile:
            raise ValueError("Das Gastprofil wurde nicht gefunden.")

        first_name = str(payload.get("firstName", "")).strip()
        if not first_name:
            raise ValueError("Bitte gib einen Vornamen an.")

        profile["firstName"] = first_name
        profile["phone"] = str(payload.get("phone", "")).strip()
        write_json_file(GUEST_PROFILES_FILE, profiles)
        return profile


def change_password(profile_id: str, current_password: str, new_password: str) -> None:
    with DATA_LOCK:
        profiles = guest_profiles()
        profile = next((item for item in profiles if item["id"] == profile_id), None)
        if not profile:
            raise ValueError("Das Gastprofil wurde nicht gefunden.")
        if not verify_password_hash(current_password, profile.get("password", {})):
            raise ValueError("Das aktuelle Passwort ist nicht korrekt.")

        profile["password"] = create_password_hash(new_password)
        write_json_file(GUEST_PROFILES_FILE, profiles)


def parse_json_body(handler) -> dict:
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(content_length)
    return json.loads(raw_body.decode("utf-8"))


def bearer_token(handler) -> str | None:
    authorization = handler.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        parsed_url = urlsplit(self.path)

        if parsed_url.path == "/api/auth/me":
            self.handle_auth_me()
            return
        if parsed_url.path == "/api/products":
            self.handle_products(parsed_url.query)
            return
        if parsed_url.path == "/api/reservations/config":
            self.handle_reservations_config()
            return
        if parsed_url.path == "/api/reservations/calendar":
            self.handle_reservations_calendar(parsed_url.query)
            return
        if parsed_url.path == "/api/reservations/availability":
            self.handle_reservations_availability(parsed_url.query)
            return
        if parsed_url.path == "/api/profile/reservations":
            self.handle_profile_reservations()
            return
        if parsed_url.path.startswith("/reservations/qr-image/") and parsed_url.path.endswith(".svg"):
            self.handle_reservation_qr_image(parsed_url.path)
            return
        if parsed_url.path.startswith("/reservations/qr/"):
            self.handle_reservation_qr(parsed_url.path)
            return
        if parsed_url.path == "/reservations/cancel":
            self.handle_reservation_cancel(parsed_url.query)
            return
        if parsed_url.path.startswith("/api/cms/products/"):
            self.handle_cms_product_get(parsed_url.path)
            return
        super().do_GET()

    def do_POST(self):
        routes = {
            "/api/contact": self.handle_contact,
            "/api/reservations": self.handle_reservations_create,
            "/api/register/request-code": self.handle_register_request_code,
            "/api/register/verify-code": self.handle_register_verify_code,
            "/api/register/complete": self.handle_register_complete,
            "/api/auth/login": self.handle_auth_login,
            "/api/auth/logout": self.handle_auth_logout,
            "/api/profile": self.handle_profile_update,
            "/api/profile/change-password": self.handle_profile_change_password,
        }

        handler = routes.get(self.path)
        if not handler:
            self.send_error(404, "Not found")
            return

        try:
            payload = parse_json_body(self)
        except json.JSONDecodeError:
            self.respond_json(400, {"ok": False, "error": "invalid_json"})
            return

        handler(payload)

    def do_PUT(self):
        if self.path.startswith("/api/cms/products/") and self.path.endswith("/price"):
            try:
                payload = parse_json_body(self)
            except json.JSONDecodeError:
                self.respond_json(400, {"ok": False, "error": "invalid_json"})
                return

            self.handle_cms_product_price_update(self.path, payload)
            return

        self.send_error(404, "Not found")

    def authenticated_profile(self) -> tuple[str | None, dict | None]:
        token = bearer_token(self)
        if not token:
            return None, None
        return token, profile_for_token(token)

    def handle_auth_me(self):
        _, profile = self.authenticated_profile()
        if not profile:
            self.respond_json(401, {"ok": False, "error": "unauthorized"})
            return

        self.respond_json(200, {"ok": True, "guestProfile": public_profile(profile)})

    def handle_products(self, query_string: str):
        page = parse_qs(query_string).get("page", [""])[0].strip().lower()
        if page not in {"menu", "drinks"}:
            self.respond_json(400, {"ok": False, "error": "invalid_page"})
            return

        self.respond_json(200, {"ok": True, "page": page, "sections": page_products(page)})

    def handle_reservations_config(self):
        self.respond_json(200, {"ok": True, "config": reservation_config()})

    def handle_reservations_availability(self, query_string: str):
        params = parse_qs(query_string)
        date_value = params.get("date", [""])[0].strip()
        slot_key = params.get("slotKey", [""])[0].strip()
        room_id = params.get("roomId", [""])[0].strip()
        guests_raw = params.get("guests", [""])[0].strip()

        try:
            guests = int(guests_raw) if guests_raw else None
        except ValueError:
            self.respond_json(400, {"ok": False, "error": "invalid_guests"})
            return

        try:
            tables = available_tables(date_value, slot_key, room_id, guests)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        room = reservation_room(room_id)
        self.respond_json(
            200,
            {
                "ok": True,
                "date": date_value,
                "slotKey": slot_key,
                "roomId": room_id,
                "roomStatus": room["status"] if room else "",
                "tables": tables,
            },
        )

    def handle_reservations_calendar(self, query_string: str):
        params = parse_qs(query_string)
        start_date = params.get("start", [""])[0].strip()
        slot_key = params.get("slotKey", [""])[0].strip()
        room_id = params.get("roomId", [""])[0].strip()
        guests_raw = params.get("guests", [""])[0].strip()
        days_raw = params.get("days", ["28"])[0].strip()

        try:
            guests = int(guests_raw) if guests_raw else None
        except ValueError:
            self.respond_json(400, {"ok": False, "error": "invalid_guests"})
            return

        try:
            days = int(days_raw)
        except ValueError:
            self.respond_json(400, {"ok": False, "error": "invalid_days"})
            return

        try:
            calendar_days = reservation_calendar_days(start_date, days, slot_key, room_id, guests)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(
            200,
            {
                "ok": True,
                "start": start_date,
                "days": calendar_days,
                "slotKey": slot_key,
                "roomId": room_id,
            },
        )

    def handle_reservations_create(self, payload: dict):
        try:
            reservation, mail_error = create_reservation(payload, self.public_base_url())
        except ValueError as exc:
            message = str(exc)
            if message.startswith("missing_fields:"):
                fields = [field for field in message.removeprefix("missing_fields:").split(",") if field]
                self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": fields})
                return

            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": message})
            return

        response_payload = {"ok": True, "reservation": reservation, "mailStatus": "sent" if not mail_error else "failed"}
        if mail_error:
            response_payload["mailError"] = mail_error
        self.respond_json(200, response_payload)

    def handle_profile_reservations(self):
        _, profile = self.authenticated_profile()
        if not profile:
            self.respond_json(401, {"ok": False, "error": "unauthorized"})
            return

        self.respond_json(
            200,
            {"ok": True, "reservations": reservations_for_guest_email(profile["email"], self.public_base_url())},
        )

    def cms_product_payload(self, product: sqlite3.Row) -> dict:
        image_path = product["image_path"] or ""
        image_url = self.absolute_url(image_path) if image_path else None
        return {
            "erpId": product["erp_id"],
            "page": product["page"],
            "sectionKey": product["section_key"],
            "category": product["category"],
            "name": product["title"],
            "description": product["teaser"],
            "imageUrl": image_url,
            "price": product["price"],
        }

    def absolute_url(self, path: str) -> str:
        host = self.headers.get("Host", f"{HOST}:{PORT}")
        return f"http://{host}/{path.lstrip('/')}"

    def public_base_url(self) -> str:
        return reservation_public_base_url(self.headers.get("Host"))

    def handle_reservation_qr(self, path: str):
        reservation_id = unquote(path.removeprefix("/reservations/qr/")).strip()
        reservation_row = reservation_by_id(reservation_id)
        if not reservation_row:
            self.respond_html(404, reservation_cancel_document("Nicht gefunden", "Diese Reservierung existiert nicht mehr.", "error"))
            return

        reservation = reservation_details_payload(reservation_row, self.public_base_url())
        self.respond_html(200, reservation_qr_document(reservation))

    def handle_reservation_qr_image(self, path: str):
        reservation_id = unquote(path.removeprefix("/reservations/qr-image/").removesuffix(".svg")).strip()
        reservation_row = reservation_by_id(reservation_id)
        if not reservation_row:
            self.respond_html(404, reservation_cancel_document("Nicht gefunden", "Diese Reservierung existiert nicht mehr.", "error"))
            return

        body = reservation_qr_svg(reservation_id).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_reservation_cancel(self, query_string: str):
        params = parse_qs(query_string)
        reservation_id = params.get("reservationId", [""])[0].strip()
        cancel_token = params.get("token", [""])[0].strip()
        confirm = params.get("confirm", [""])[0].strip() == "1"
        if not reservation_id or not cancel_token:
            self.respond_html(
                400,
                reservation_cancel_document(
                    "Link unvollständig",
                    "Für diese Aktion fehlen Reservierungsdaten. Bitte nutze den vollständigen Link aus deiner E-Mail.",
                    "error",
                ),
            )
            return

        reservation_row = reservation_by_id(reservation_id)
        if not reservation_row or reservation_row["cancel_token"] != cancel_token:
            self.respond_html(400, reservation_cancel_document("Löschen nicht möglich", "Diese Reservierung konnte nicht gefunden werden.", "error"))
            return

        reservation = reservation_details_payload(reservation_row, self.public_base_url())
        if reservation_row["status"] == "cancelled":
            body = (
                f"Die Reservierung für <strong>{html.escape(reservation['scheduledLabel'])}</strong> "
                f"im <strong>{html.escape(reservation['roomName'])}</strong> wurde bereits früher gelöscht."
            )
            self.respond_html(200, reservation_cancel_document("Bereits gelöscht", body, "success"))
            return

        if not confirm:
            confirm_url = (
                f"{self.public_base_url()}/reservations/cancel?"
                f"reservationId={quote(reservation_id, safe='')}&token={quote(cancel_token, safe='')}&confirm=1"
            )
            self.respond_html(200, reservation_cancel_confirmation_document(reservation, confirm_url))
            return

        try:
            reservation, state = cancel_reservation(reservation_id, cancel_token)
        except ValueError as exc:
            self.respond_html(400, reservation_cancel_document("Löschen nicht möglich", html.escape(str(exc)), "error"))
            return

        if state == "already_cancelled":
            body = (
                f"Die Reservierung für <strong>{html.escape(reservation['scheduledLabel'])}</strong> "
                f"im <strong>{html.escape(reservation['roomName'])}</strong> wurde bereits früher gelöscht."
            )
            self.respond_html(200, reservation_cancel_document("Bereits gelöscht", body, "success"))
            return

        body = (
            f"Deine Reservierung für <strong>{html.escape(reservation['scheduledLabel'])}</strong> "
            f"im <strong>{html.escape(reservation['roomName'])}</strong> wurde erfolgreich gelöscht. "
            "Wir hoffen, dich bald wieder bei Bavarian RoboTaste begrüßen zu dürfen."
        )
        self.respond_html(200, reservation_cancel_document("Reservierung gelöscht", body, "success"))

    def handle_cms_product_get(self, path: str):
        erp_id = unquote(path.removeprefix("/api/cms/products/")).strip()
        if not erp_id:
            self.respond_json(400, {"ok": False, "error": "missing_erp_id"})
            return

        product = product_by_erp_id(erp_id)
        if not product:
            self.respond_json(404, {"ok": False, "error": "product_not_found", "erpId": erp_id})
            return

        self.respond_json(200, {"ok": True, "product": self.cms_product_payload(product)})

    def handle_cms_product_price_update(self, path: str, payload: dict):
        erp_id = unquote(path.removeprefix("/api/cms/products/").removesuffix("/price")).strip()
        if not erp_id:
            self.respond_json(400, {"ok": False, "error": "missing_erp_id"})
            return

        price = str(payload.get("price", "")).strip()
        if not price:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": ["price"]})
            return

        product = update_product_price_by_erp_id(erp_id, price)
        if not product:
            self.respond_json(404, {"ok": False, "error": "product_not_found", "erpId": erp_id})
            return

        self.respond_json(200, {"ok": True, "product": self.cms_product_payload(product)})

    def handle_contact(self, payload: dict):
        required_fields = ["name", "email", "topic", "message"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        try:
            send_messages(build_contact_messages(payload))
        except Exception as exc:
            self.respond_json(500, {"ok": False, "error": "mail_send_failed", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True})

    def handle_register_request_code(self, payload: dict):
        required_fields = ["firstName", "email"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        try:
            request_registration_code(payload)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return
        except Exception as exc:
            self.respond_json(500, {"ok": False, "error": "mail_send_failed", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True})

    def handle_register_verify_code(self, payload: dict):
        required_fields = ["email", "verificationCode"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        try:
            verify_registration_code(payload)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True})

    def handle_register_complete(self, payload: dict):
        required_fields = ["email", "password", "passwordConfirm"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        if payload["password"] != payload["passwordConfirm"]:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": "Die Passwörter stimmen nicht überein."})
            return

        if len(payload["password"]) < 8:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": "Das Passwort muss mindestens 8 Zeichen lang sein."})
            return

        try:
            guest_profile, token = complete_registration(payload)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return
        except Exception as exc:
            self.respond_json(500, {"ok": False, "error": "registration_failed", "detail": str(exc)})
            return

        self.respond_json(
            200,
            {
                "ok": True,
                "token": token,
                "guestProfile": public_profile(guest_profile),
            },
        )

    def handle_auth_login(self, payload: dict):
        required_fields = ["email", "password"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        try:
            profile, token = login_user(payload["email"], payload["password"])
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True, "token": token, "guestProfile": public_profile(profile)})

    def handle_auth_logout(self, payload: dict):
        token, _ = self.authenticated_profile()
        if token:
            delete_session(token)
        self.respond_json(200, {"ok": True})

    def handle_profile_update(self, payload: dict):
        _, profile = self.authenticated_profile()
        if not profile:
            self.respond_json(401, {"ok": False, "error": "unauthorized"})
            return

        try:
            updated_profile = update_profile(profile["id"], payload)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True, "guestProfile": public_profile(updated_profile)})

    def handle_profile_change_password(self, payload: dict):
        _, profile = self.authenticated_profile()
        if not profile:
            self.respond_json(401, {"ok": False, "error": "unauthorized"})
            return

        required_fields = ["currentPassword", "newPassword", "newPasswordConfirm"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        if payload["newPassword"] != payload["newPasswordConfirm"]:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": "Die neuen Passwörter stimmen nicht überein."})
            return

        if len(payload["newPassword"]) < 8:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": "Das neue Passwort muss mindestens 8 Zeichen lang sein."})
            return

        try:
            change_password(profile["id"], payload["currentPassword"], payload["newPassword"])
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True})

    def guess_type(self, path):
        if str(path).endswith(".js"):
            return "application/javascript"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"

    def respond_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_html(self, status: int, document: str):
        body = document.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ensure_data_dir()
    ensure_products_db()
    ensure_reservations_db()
    ensure_demo_reservations()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving Bavarian RoboTaste on http://{HOST}:{PORT}")
    server.serve_forever()
