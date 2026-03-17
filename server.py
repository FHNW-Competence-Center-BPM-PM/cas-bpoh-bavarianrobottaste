import hashlib
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
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PENDING_REGISTRATIONS_FILE = DATA_DIR / "pending_registrations.json"
GUEST_PROFILES_FILE = DATA_DIR / "guest_profiles.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
PRODUCTS_DB_FILE = DATA_DIR / "products.db"
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))
REGISTRATION_CODE_TTL_MINUTES = int(os.environ.get("REGISTRATION_CODE_TTL_MINUTES", "15"))
PASSWORD_HASH_ITERATIONS = 200_000
DATA_LOCK = threading.Lock()

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
                    page, section_key, sort_order, category, title, teaser, ingredients, price,
                    image_path, quote_text, quote_author, special_heading_1, special_content_1,
                    special_heading_2, special_content_2, featured
                ) VALUES (
                    :page, :section_key, :sort_order, :category, :title, :teaser, :ingredients, :price,
                    :image_path, :quote_text, :quote_author, :special_heading_1, :special_content_1,
                    :special_heading_2, :special_content_2, :featured
                )
                """,
                PRODUCT_SEED,
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
            SELECT page, section_key, sort_order, category, title, teaser, ingredients, price, image_path,
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
        super().do_GET()

    def do_POST(self):
        routes = {
            "/api/contact": self.handle_contact,
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


if __name__ == "__main__":
    ensure_data_dir()
    ensure_products_db()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving Bavarian RoboTaste on http://{HOST}:{PORT}")
    server.serve_forever()
