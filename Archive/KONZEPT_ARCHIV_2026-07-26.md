# DanceCreator – Konzeptpapier

## 1. Projektübersicht

### 1.1 Zielsetzung
**DanceCreator** ist ein Softwaresystem zur digitalen Modellierung, Visualisierung und Verwaltung von Tanzfiguren, insbesondere im Bereich **Scottish Country Dancing**. Das System ermöglicht es:
- Tanzfiguren hierarchisch zu definieren und zu verwalten
- Tanzabläufe zu strukturieren und zu kombinieren
- Die Positionen von Tänzern auf der Tanzfläche zu tracken
- Tänzer-Instruktionen (Cripts) zu generieren
- Eine benutzerfreundliche Weboberfläche zur Visualisierung bereitzustellen

### 1.2 Zielgruppe
- **Tanzlehrer** – zur Vorbereitung und Dokumentation von Tanzabläufen
- **Tänzer** – zum Verständnis komplexer Figuren und Positionen
- **Software-Entwickler** – zur Integration in spezialisierte Tanzsoftware

### 1.3 Kernfunktionalitäten
1. **Figuren-Management** – Modellierung von Tanzfiguren (einfach und komplex)
2. **Tanzflächen-Simulation** – Tracking von Tänzern und deren Positionen
3. **Choreografie-Verwaltung** – Zusammensetzung von Figuren zu kompletten Tänzen
4. **Anleitung & Visualisierung** – Text-basierte und später grafische Darstellung
5. **REST-API** – Zur Abfrage und Verwaltung von Daten
6. **Web-GUI** – Interaktive Benutzeroberfläche zur Visualisierung

---

## 2. Systemarchitektur

### 2.1 Architektur-Übersicht

```
┌─────────────────────────────────────────────────────┐
│         Web-Frontend (Flask/HTML5/JavaScript)       │
│    (templates/index.html + static/app.js)           │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│      API-Layer (Flask - GUI_DanceCreator_App.py)    │
│  Endpunkte: /tree, /get_nodes, /                    │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│         Business Logic Layer                        │
│  ┌──────────────────────────────────────────┐       │
│  │ Figure (ABC - Abstrakte Basisklasse)    │       │
│  │ ├─ SimpleFigure                         │       │
│  │ └─ ComplexFigure                        │       │
│  │                                          │       │
│  │ FigureAddon (Modifikatoren)             │       │
│  └──────────────────────────────────────────┘       │
└────────────────┬──────────────────────────────────┘
                 │
          ┌──────┴──────┐
          ▼             ▼
    ┌─────────────┐  ┌─────────────────────┐
    │ DanceFloor  │  │ Dance (Management)  │
    │ + Dancer    │  │                     │
    └─────────────┘  └─────────────────────┘
          │
          ▼
    ┌──────────────────────────────────┐
    │  Data Layer                      │
    │  ├─ Figures/   (JSON-Dateien)   │
    │  ├─ Dances/    (JSON-Dateien)   │
    │  └─ Static/    (CSS, JS)        │
    └──────────────────────────────────┘
```

### 2.2 Komponenten

#### **2.2.1 Figure (Abstrakte Basisklasse)**
- **Datei:** `Figures.py`
- **Aufgaben:**
  - Definiert die Schnittstelle für alle Figurentypen
  - Verwaltet gemeinsame Eigenschaften: Beschreibung, Takte, Start-/Endpositionen, Ausrichtung
  - Abstract Methods: `DanceMove()`, `getCrips()`, `loadFigure()`
  - **FigureAddon:** Modifiziert Figuren mit zusätzlichen Anweisungen

#### **2.2.2 SimpleFigure**
- **Datei:** `SimpleFigure.py`
- **Aufgaben:**
  - Repräsentiert eine atomare Tanzfigur
  - Lädt Figuren aus JSON-Dateien (Version 2)
  - Verwaltet Tänzer-Positionen und Anweisungen (Cripts)
  - Unterstützt Addons zur Modifikation von Figuren
  - **Key Methods:**
    - `DanceMove(oldDF)` – Aktualisiert die Tanzfläche
    - `getCrips(myDF)` – Generiert Anweisungen für Tänzer

#### **2.2.3 ComplexFigure**
- **Datei:** `ComplexFigure.py`
- **Aufgaben:**
  - Repräsentiert eine zusammengesetzte Tanzfigur (Kombination mehrerer Figuren)
  - Unterstützt sequenzielle (s) und parallele (p) Ausführung
  - Lädt hierarchische Figuren-Strukturen aus JSON (Version 3)
  - **Key Methods:**
    - `DanceMove(oldDF)` – Führt alle Sub-Figuren nacheinander aus
    - `getCrips(oldDF)` – Generiert Anweisungen für komplexe Moves
    - `subDanceMove()` / `subgetCrips()` – Rekursive Hilfsmethoden

#### **2.2.4 DanceFloor & Dancer**
- **Datei:** `DanceFloor.py` / `Dancer.py`
- **Aufgaben:**
  - **DanceFloor:** Modelliert die Tanzfläche mit Positionen der Tänzer
    - Verwaltet Tänzer in einem 2D-Gitter
    - Tracked die aktuelle Taktzahl
    - Generiert Positionsnamen (z. B. "1m", "1w", "between 1c")
  - **Dancer:** Repräsentiert einen einzelnen Tänzer (Name, Geschlecht)
  - **combineDanceFloor():** Kombiniert parallele DanceFloors (z. B. für synchrone Moves)

#### **2.2.5 Dance (Verwaltung)**
- **Datei:** `Dance.py`
- **Aufgaben:**
  - `getDance(Filename)` – Lädt einen kompletten Tanz
  - `getFigure(Filename, Anchor, Addons)` – Lädt eine einzelne Figur
  - `showCrips()` / `printCrip()` – Gibt Anweisungen aus

#### **2.2.6 Flask-API**
- **Datei:** `GUI_DanceCreator_App.py`
- **Aufgaben:**
  - Bereitstellung der Web-GUI
  - REST-API für Figurenverwaltung
  - **Endpunkte:**
    - `GET /` – Liefert HTML-Seite
    - `GET /get_nodes/<node_Name>` – Gibt Figurendaten in jsTree-Format
    - Zukünftig: CRUD-Operationen für Figuren/Tänze

#### **2.2.7 Frontend**
- **Datei:** `templates/index.html`, `static/app.js`, `static/style_old.css`
- **Aufgaben:**
  - HTML5-basierte Web-Oberfläche
  - Baumdarstellung von Figuren (mit jstree)
  - Visualisierung der Tanzfläche (Platzhalter)
  - Interaktive Anweisungsanzeige

---

## 3. Datenmodell

### 3.1 JSON-Format für Figuren

#### **SimpleFigure (Version 2)**
```json
{
  "Version": 2,
  "Name": "Reel Across",
  "Desc": "Eine Reel-Figur über die Tanzfläche",
  "Bars": 8,
  "StartPos": [[1, 1], [1, 3]],
  "EndPos": [[3, 3], [3, 1]],
  "CriptDesc": [
    "Reel with partner across the dance",
    "Moving from position {StartPos} to {EndPos}"
  ],
  "Faceing": [[1, 3], [1, 1]],
  "Partner": [[1, 3], [1, 1]],
  "Addons": {}
}
```

#### **ComplexFigure (Version 3)**
```json
{
  "Version": 3,
  "Name": "Marrie's Wedding - Full",
  "Desc": "Vollständiger Tanz",
  "FigureList": [
    [[0, 0], "Reel Across"],
    [[0, 0], ["s", [
      [[0, 0], "Right Hand Turn"],
      [[0, 0], "Change Across"]
    ]]],
    [[0, 0], ["p", [
      [[0, 0], "Reel on the Sides"],
      [[0, 0], "Half Reel"]
    ]]]
  ]
}
```

**FigureList-Struktur:**
- Format: `[Anchor, Figur]`
- **Anchor:** Offset-Position `[row, col]`
- **Figur:** String (Figurenname) oder Array für sequenzielle/parallele Ausführung
  - `["s", [Figuren]]` – Sequenziell (nacheinander)
  - `["p", [Figuren]]` – Parallel (gleichzeitig)

### 3.2 Positionssystem

- **Gitter:** 2D-Koordinaten `(row, col)`
- **row:** Paargruppe (1 = First Couple, 2 = Second Couple, etc.)
- **col:** Position in der Paargruppe (1 = Mann, 2 = zwischen, 3 = Frau)
- **Beispiele:**
  - `(1, 1)` = First Man
  - `(1, 3)` = First Woman
  - `(2, 2)` = Between Second Couple

### 3.3 Anchor-System

- Versetzt die Koordinaten aller Sub-Figuren
- Ermöglicht Wiederverwendung von Figuren an verschiedenen Positionen
- Format: `[row_offset, col_offset]`

---

## 4. Kritische Konzepte

### 4.1 Cripts (Anweisungen)
- Textbasierte Anweisungen für Tänzer
- Format: `"Bar X-Y: Anweisung"`
- Template-Variablen:
  - `{Dancer}` → Name des Tänzers
  - `{StartPos}` → Position-Name (z. B. "1m's position")
  - `{EndPos}` → Zielposition
  - `{Face}` → Zu welchem Tänzer schauen
  - `{Partner}` → Name des Partners

### 4.2 Sequenzielle vs. Parallele Ausführung
- **Sequenziell (s):** Figuren werden nacheinander ausgeführt; jede Figur wartet auf die vorherige
- **Parallel (p):** Figuren werden simultan ausgeführt; alle Tänzer führen unterschiedliche Moves gleichzeitig aus
- **Kombiniert:** Hierarchische Strukturen ermöglichen komplexe Choreografien

### 4.3 Add-ons
- Ermöglichen die Modifikation von Figuren ohne Neudef​inition
- Können Start-/Endpositionen, Anweisungen und Ausrichtung überschreiben
- In SimpleFigure unterstützt; ermöglicht Variationen einer Basis-Figur

---

## 5. Workflow & Anwendungsbeispiel

### 5.1 Tanz-Erstellung

```
1. Einzelne Figuren definieren (z. B. "Reel Across", "Right Hand Turn")
   └─ Speichern unter Figures/*.json (SimpleFigure v2)

2. Figuren zu Tanzvariationen kombinieren
   └─ Speichern unter Figures/*.json (SimpleFigure v2 mit Addons)

3. Figuren zu kompletten Tänzen komponieren
   └─ Speichern unter Dances/*.json (ComplexFigure v3)

4. Tanz ausführen (Simulation)
   a) DanceFloor mit Paaranzahl initialisieren
   b) Dance.getDance() laden
   c) DanceMove() aufrufen → neue DanceFloor-Position
   d) getCrips() aufrufen → Anweisungen ausgeben
   e) Schritte 2-4 wiederholen bis Tanz endet
```

### 5.2 Code-Beispiel (DanceCreator.py)

```python
# 1. Tanzfläche erstellen (3 Couples)
Floor = DF.DanceFloor('Marrie\'s Wedding', 3)

# 2. Tanz laden
Marrie = Dance.getDance("Marries Wedding_all")

# 3. Cripts anzeigen
Dance.showCrips(Marrie, Floor)

# 4. Tanz ausführen
Floor = Marrie.DanceMove(Floor)

# 5. Neue Tanzflächenposition anzeigen
print(Floor)
```

---

## 6. Aktuelle Implementierungsphasen

### Phase 1: Kernmodell (ABGESCHLOSSEN)
- ✅ Figure-Klassenstruktur
- ✅ SimpleFigure & ComplexFigure
- ✅ DanceFloor & Dancer
- ✅ JSON-basierte Figurendefinition
- ✅ Cript-Generierung

### Phase 2: Web-GUI (IN PROGRESS)
- ⚠️ Flask-API grundstruktur
- ⚠️ HTML-Template (vorhanden, aber funktionalität begrenzt)
- 🔲 Interaktive Tanzflächen-Visualisierung
- 🔲 Drag-and-Drop für Figurenzusammensetzung
- 🔲 Echtzeit-Cript-Anzeige

### Phase 3: Erweiterte Features (GEPLANT)
- 🔲 Persistente Datenbank für Figuren/Tänze
- 🔲 Benutzer-Authentifizierung & Rollen
- 🔲 Erweiterte Suche & Filterung
- 🔲 Import/Export von Tanznotationen
- 🔲 Grafikdarstellung (SVG/Canvas)

---

## 6. GUI-Architektur und Layout

### 6.1 Bildschirm-Aufteilung

Die GUI ist in **vier Bereiche** aufgeteilt:

```
╔═════════════════════════════════════════════════════════════════════╗
║                        [Header/Toolbar]                             ║
║  (Menü, Import/Export, Einstellungen, etc.)                         ║
╠════════════════════════════════════════════════════════════════════╣
║                          [Canvas/Content Area]                      ║
║                                                                     ║
║  ┌────────────────┐  ┌─────────────────────────┐  ┌──────────────┐ ║
║  │    LINKE       │  │                         │  │   RECHTE     │ ║
║  │   SPALTE       │  │    MITTLERER BEREICH    │  │   SPALTE     │ ║
║  │                │  │      (CANVAS)           │  │              │ ║
║  │  Figuren-      │  │                         │  │  Tanz-Baum   │ ║
║  │  Verzeichnis   │  │ Detaildarstellung &     │  │  (jsTree)    │ ║
║  │  (Katalog)     │  │ Visualisierung          │  │              │ ║
║  │                │  │                         │  │              │ ║
║  │  • Kategorien  │  │ • Figurbeschreibung    │  │ ▼ Tanz Name  │ ║
║  │  • Figuren     │  │ • Cripts               │  │  ├─ Figur 1  │ ║
║  │  • Such/Filter │  │ • Grafische Darst.    │  │  ├─ Figur 2  │ ║
║  │                │  │ • Tanzflächen-Layout  │  │  └─ Figur 3  │ ║
║  │                │  │ • Beteiligte Tänzer   │  │              │ ║
║  └────────────────┘  └─────────────────────────┘  └──────────────┘ ║
║                                                                     ║
╚════════════════════════════════════════════════════════════════════╝
```

### 6.2 Komponenten-Beschreibung

#### **6.2.1 Linke Spalte: Figuren-Katalog**

**Funktion:** Verwaltung und Auswahl von Einzelfiguren

**Inhalte:**
- **Suchfeld:** Text-Suche nach Figurennamen, Beschreibung, Tags
- **Filter:** Nach Figurentyp (Simple, Complex), Anzahl Tänzer, Dauer in Takten
- **Kategorien-Baum:**
  - Gruppen nach Typ (Reels, Turns, Changes, etc.)
  - Hierarchische Struktur ermöglicht schnelle Navigation
- **Figuren-Liste:**
  - Alle Figuren der aktuellen Kategorie
  - Thumbnail/Icon für visuellen Überblick
  - Meta-Informationen: Anzahl Tänzer, Dauer, Typ

**Interaktionen:**
- **Click:** Figur auswählen → Canvas zeigt Figurendetails
- **Drag:** Figur in Canvas-Bereich ziehen (ggf. in Baumstruktur)
- **Context-Menu:** Edit, Delete, Duplicate, Preview

**Datenverwaltung:**
- Lädt aus `Figures/` Verzeichnis
- Cached in `Figure_DB` (global)
- Unterstützt Filterung und Suchindizes

---

#### **6.2.2 Mittlerer Bereich: Canvas/Content**

**Funktion:** Multipurpose-Anzeigebereich für Details, Visualisierung und Cripts

**Darstellungs-Modi:**

##### **Modus A: Figur-Details (Auswahl aus linker Spalte)**

Wenn ein Benutzer eine Figur aus dem linken Katalog auswählt:

```
┌─────────────────────────────────────────────┐
│ Figur: Reel Across                         │
│ Version: 2 (SimpleFigure)                  │
├─────────────────────────────────────────────┤
│                                             │
│ Beschreibung:                               │
│ Eine Reel-Figur über die Tanzfläche        │
│ Dauer: 8 Takte                             │
│ Beteiligte Positionen: 6 Tänzer            │
│                                             │
├─────────────────────────────────────────────┤
│ [Grafische Darstellung]                    │
│                                             │
│  1m        1w         START:                │
│   ●━━━━━━━●    (1,1)→(3,3)  1m            │
│   2m  2w   ●→●→●     (1,3)→(3,1)  1w      │
│      ●─────●    →    EndPos: (3,1), (3,3) │
│                                             │
│ Mit Add-ons: -                              │
│                                             │
├─────────────────────────────────────────────┤
│ Cripts (Anweisungen):                      │
│                                             │
│ Bar 1-8: Reel with partner across...       │
│ Bar 1-8: Move from {StartPos} to {EndPos}  │
│                                             │
└─────────────────────────────────────────────┘
```

**Inhalte:**
- Figur-Name, Typ, Version
- Vollständige Beschreibung
- **Grafische Darstellung:**
  - Start-Positionen (Kreise mit Namen)
  - End-Positionen (Zielmarkierungen)
  - Bewegungsvektoren (Pfeile)
  - Ausrichtung (Facing-Richtungen als kleine Dreiecke)
- **Meta-Informationen:**
  - Anzahl beteiligter Tänzer
  - Dauer in Takten
  - Partner-Beziehungen
  - Add-ons (falls vorhanden)
- **Cripts (Anweisungen):**
  - Template-Variablen noch nicht ersetzt (da keine DanceFloor-Kontext)
  - Zeigt die Struktur der Anweisungen

---

##### **Modus B: Figur im Tanz-Kontext (Auswahl aus rechtem Baum)**

Wenn ein Benutzer eine oder mehrere Figuren im rechten Baum auswählt:

```
┌─────────────────────────────────────────────┐
│ Tanz: Marrie's Wedding - Bar 1-8            │
│ Figur(en): Reel Across (Bar 1-8)           │
├─────────────────────────────────────────────┤
│                                             │
│ AKTUELLE TANZFLÄCHEN-AUFSTELLUNG:           │
│                                             │
│ Start (Bar 0, Ende Bar 0):                 │
│  1m (1,1)    1w (1,3)    Figur: Reel...   │
│  2m (2,1)    2w (2,3)                      │
│  3m (3,1)    3w (3,3)                      │
│                                             │
├─────────────────────────────────────────────┤
│ [GRAFISCHE VISUALIZATION]                  │
│                                             │
│ Tänzer-Position (Start vs. Ende):          │
│                                             │
│  1m●────→   1w                              │
│      ↘    ╱  ↙                              │
│  2m  ●  ●   2w                              │
│      ↗    ╲  ↖                              │
│  3m←────●   3w●                             │
│                                             │
│ Legende: ● = Start, ◉ = Ende, → = Vektor  │
│                                             │
├─────────────────────────────────────────────┤
│ CRIPTS (mit Tänzer-Namen und Positionen):  │
│                                             │
│ Bar 1-8: 1m - Reel with 1w across the...  │
│ Bar 1-8: 1w - Reel with 1m across the...  │
│ Bar 1-8: 2m - Move from 2m's position to..│
│ ...                                         │
│                                             │
└─────────────────────────────────────────────┘
```

**Inhalte:**
- **Tanzkontext:**
  - Tanz-Name
  - Balkenbereich (z. B. "Bar 1-8")
  - Figurenname(n)
- **Tanzflächen-Aufstellung (VORHER):**
  - Alle Tänzer mit aktuellen Namen und Positionen
  - Gelabelt mit Positionen (1m, 1w, etc.)
- **Grafische Darstellung:**
  - Bewegungsvektoren mit Animationspfaden
  - Start- und Endpositionen deutlich gekennzeichnet
  - Farbcodierung für verschiedene Tänzer (optional)
  - Facing-Richtungen als kleine Dreiecke
- **Tanzflächen-Aufstellung (NACHHER):**
  - (Optional) Neue Positionen nach der Figur
- **Cripts mit ersetzen Variablen:**
  - `{Dancer}` → echte Tänzer-Namen (z. B. "1m")
  - `{StartPos}` → Position-Namen (z. B. "1m's position")
  - `{EndPos}` → Zielposition
  - Jede Zeile für jeden beteiligten Tänzer

---

##### **Modus C: Mehrere Figuren im Baum ausgewählt**

Wenn mehrere aufeinanderfolgende oder gruppierte Figuren ausgewählt sind:

```
┌─────────────────────────────────────────────┐
│ Tanz: Marrie's Wedding                      │
│ Auswahl: Figur 1 → Figur 2 → Figur 3       │
│ Bar 1-24 (3 Figuren à 8 Takte)              │
├─────────────────────────────────────────────┤
│                                             │
│ ÜBERSICHT ALLER FIGUREN:                    │
│                                             │
│ ┌─ Figur 1: Reel Across (Bar 1-8) ────┐   │
│ │ Cripts: 1m - Reel with 1w...         │   │
│ │         1w - Reel with 1m...         │   │
│ └──────────────────────────────────────┘   │
│                                             │
│ ┌─ Figur 2: Right Hand Turn (Bar 9-16) ──┐ │
│ │ Cripts: 1m - Turn right hand with 2m..│ │
│ │         2m - Turn right hand with 1m..│ │
│ └──────────────────────────────────────┘   │
│                                             │
│ ┌─ Figur 3: Change Across (Bar 17-24) ───┐ │
│ │ Cripts: 1m - Change across with 1w... │ │
│ │         1w - Change across with 1m... │ │
│ └──────────────────────────────────────┘   │
│                                             │
│ [ANIMATION: Play / Step through Bars]      │
│                                             │
└─────────────────────────────────────────────┘
```

**Inhalte:**
- **Akkordeon/Tabs für jede Figur:**
  - Figurenname und Balkenbereich
  - Cripts für alle Tänzer
  - Optional: Mini-Grafiken
- **Gesamtdarstellung:**
  - Alle Cripts in zeitlicher Reihenfolge
  - Gruppierung nach Figur
  - Synchronisierung mit Tanzflächen-Positionen
- **Playback-Kontrollen (optional für Phase 2+):**
  - Play/Pause-Button
  - Bar-schieber zum Scrubben
  - Speed-Regler

---

##### **Modus D: Ganzer Tanz ausgewählt**

Wenn der Tanz-Root im Baum gewählt wird:

```
┌─────────────────────────────────────────────┐
│ TANZ: Marrie's Wedding (Vollständig)       │
│ Version: 3 (ComplexFigure)                 │
│ Gesamtdauer: 32 Takte                      │
│ Beteiligte: 3 Couples (6 Tänzer)           │
├─────────────────────────────────────────────┤
│                                             │
│ VOLLSTÄNDIGE CHOREOGRAFIE:                  │
│                                             │
│ ┌─ Bar 1-8: Reel Across ──────────────┐   │
│ │ 1m: Reel with 1w across the dance   │   │
│ │ 1w: Reel with 1m across the dance   │   │
│ │ 2m: Move from 2m's position to 2w's │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ ┌─ Bar 9-16: Right Hand Turn ─────────┐   │
│ │ 1m: Turn right hand with 2m (4 bars)│   │
│ │ 2m: Turn right hand with 1m (4 bars)│   │
│ │ [...]                                │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ ┌─ Bar 17-24: Change Across ──────────┐   │
│ │ [...]                                │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ ┌─ Bar 25-32: Half Reel ──────────────┐   │
│ │ [...]                                │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ [ANIMATION: Play / Step through Bars]      │
│ [Export as PDF] [Print] [Share]            │
│                                             │
└─────────────────────────────────────────────┘
```

**Inhalte:**
- **Tanz-Header:**
  - Tanz-Name, Typ, Version
  - Gesamtdauer, Anzahl Couples
  - Musik-Info (zukünftig)
- **Vollständige Cript-Liste:**
  - Alle Figuren in Bar-Reihenfolge
  - Cripts für alle Tänzer
  - Farbcodierung nach Figuren (optional)
- **Tanzflächen-Simulation:**
  - Start-Position (vor Tanz)
  - End-Position (nach Tanz)
  - Optional: Step-by-Step Animation
- **Export/Share-Optionen:**
  - PDF-Export (Cripts + Grafiken)
  - Druck-Version
  - Teilen (zukünftig)

---

#### **6.2.3 Rechte Spalte: Tanz-Baum (jsTree)**

**Funktion:** Hierarchische Navigation durch Tanz-Struktur

**Inhalte:**
- **Root-Knoten:** Tanz-Name
  - Icon: 🎭 (Tanz)
  - Click: Zeigt gesamten Tanz im Canvas
  - Farbe: Hervorgehoben
- **Figur-Knoten:** Hierarchisch
  - Icons:
    - 📦 SimpleFigure (Blatt-Knoten)
    - 🎯 ComplexFigure (Ordner-Knoten mit Kindern)
  - Labels: Figurenname + Bar-Bereich (z. B. "Reel Across [Bar 1-8]")
  - Farben: Optional nach Figurentyp
- **Gruppierungs-Knoten (falls komplexe Struktur):**
  - 📂 Sequenziell (s)
  - ⚡ Parallel (p)

**Interaktionen:**
- **Single-Click:** Figur auswählen → Canvas zeigt Details
- **Multi-Select (Shift+Click/Ctrl+Click):**
  - Mehrere Figuren wählen → Canvas zeigt Übersicht aller
  - Bereich auswählen (z. B. Bar 9-24) → zeigt nur diesen Teil
- **Expand/Collapse:** Unterfiguren anzeigen/verbergen
- **Context-Menu:** Edit, Delete, Duplicate, Insert New Figure
- **Drag-and-Drop (Phase 2+):** Figuren verschieben, neu anordnen

**Datenquelle:**
- Laden aus `Dances/` und `Figures/` JSON-Dateien
- Dynamisch aufgebaut aus ComplexFigure FigureList
- Real-time Update bei Änderungen

---

### 6.3 Interaktions-Flussdiagramm

```
┌──────────────────────────────────────────────────────────┐
│                     USER STARTS APP                      │
└──────────────────────┬───────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ Linke    │  │ Canvas   │  │ Rechte   │
    │ Spalte   │  │ (Leer)   │  │ Spalte   │
    │ zeigt    │  │          │  │ zeigt    │
    │Kategorien│  │          │  │ Tanz-    │
    └────┬─────┘  └──────────┘  │ Baum     │
         │                       └────┬────┘
         │ Clicks Figur
         ▼
    ┌──────────────────────────────────┐
    │ Canvas: Figur-Details anzeigen   │  ← MODUS A
    │ (Beschreibung, Grafik, Cripts)   │
    └──────────────────────────────────┘
         ▲                    │
         │                    │ Oder:
         │                    │ Baum-Click
         │                    ▼
         │            ┌──────────────────────────────┐
         │            │ Canvas: Figur in Tanz-Kontext│  ← MODUS B
         │            │ (Tanzfläche, Cripts)         │
         └────────────┤ mit Namen & Positionen       │
                      └──────────────────────────────┘
                                 ▲
                                 │
                                 │ Multi-Select
                                 ▼
                      ┌──────────────────────────────┐
                      │ Canvas: Mehrere Figuren      │  ← MODUS C
                      │ (Übersicht, Akkordeon)       │
                      └──────────────────────────────┘
                                 ▲
                                 │
                                 │ Baum-Root-Click
                                 ▼
                      ┌──────────────────────────────┐
                      │ Canvas: Ganzer Tanz          │  ← MODUS D
                      │ (Vollständige Choreografie)  │
                      └──────────────────────────────┘
```

---

### 6.4 Grafische Visualisierung

#### **6.4.1 Tanzflächen-Layout**

Die Tanzfläche wird als **2D-Gitter** dargestellt:

```
        Col 1           Col 2           Col 3
Row 1   ●(1m)    ────→  ×(between1c)    ←──── ●(1w)
        │               │               │
Row 2   │       ●(2m)   ▼      ←───────+       ●(2w)
        │       │       │               │       │
Row 3   ●←──────+       ×(between3c)    ▼       ●
```

**Elemente:**
- **Knoten (●):** Tänzer an Position
  - Label: Position-Name (1m, 1w, etc.)
  - Farbe: Optional nach Paar (1st, 2nd, 3rd, ...)
  - Size: Konstant oder animiert
- **Vektoren (→, ←, ↑, ↓, ↘, ↙, etc.):** Bewegungsrichtungen
  - Pfeile zeigen Endposition
  - Optional: Animierte Bewegung
  - Farbe: Nach Tänzer/Paar
- **Linien:** Verbindungen
  - Partner-Linien (gestrichelt)
  - Facing-Richtungen (kleine Dreiecke)
- **Bounding-Box:** Tanzflächen-Grenzen

**Rendering-Technologien (Phase 2+):**
- SVG für Vektor-Grafiken (einfach, scalebar)
- Canvas für Animation (schneller)
- D3.js für komplexe Layouts (optional)

---

#### **6.4.2 Farbcodierung**

| Element | Farbe | Bedeutung |
|---------|-------|-----------|
| 1st Couple | Blau | First Couple / First Dancers |
| 2nd Couple | Grün | Second Couple |
| 3rd Couple | Rot | Third Couple |
| Männer | Dunkelblau | Männliche Tänzer |
| Frauen | Pink/Hellrot | Weibliche Tänzer |
| Start-Position | Grün | Anfangsposition |
| End-Position | Orange | Zielposition |
| Bewegungsvektor | Pfeil-grau | Bewegungsrichtung |
| Facing | Dreieck-blau | Blickrichtung |

---

### 6.5 Responsive Design

Die GUI sollte auf verschiedenen Bildschirmgrößen funktionieren:

| Breakpoint | Layout |
|-----------|--------|
| Desktop (>1200px) | 3-spalten (L, C, R) wie beschrieben |
| Tablet (768-1200px) | 2-spalten (Tabs zum Wechsel) oder Accordion |
| Mobile (<768px) | 1-spalten mit Tabs/Dropdown-Navigation |

---

### 6.6 API-Endpunkte für GUI

Die Flask-API muss folgende Endpunkte unterstützen:

#### **Figur-Verwaltung**
- `GET /api/figures` – Alle Figuren mit Metadaten
- `GET /api/figures/<name>` – Einzelne Figur-Details
- `GET /api/figures/<name>/crips` – Cripts (ungefüllt)
- `GET /api/figures/<name>/thumbnail` – SVG-Miniatur
- `POST /api/figures` – Neue Figur erstellen (Phase 2+)
- `PUT /api/figures/<name>` – Figur aktualisieren (Phase 2+)
- `DELETE /api/figures/<name>` – Figur löschen (Phase 2+)

#### **Tanz-Verwaltung**
- `GET /api/dances` – Alle Tänze
- `GET /api/dances/<name>` – Tanz-Details + Baum
- `GET /api/dances/<name>/crips` – Vollständige Cripts
- `GET /api/dances/<name>/visualization` – SVG mit Tanzfläche
- `POST /api/dances` – Neuer Tanz (Phase 2+)
- `PUT /api/dances/<name>` – Tanz aktualisieren (Phase 2+)

#### **Tanzflächen-Simulation**
- `POST /api/dancefloor/init` – DanceFloor mit N Couples
- `POST /api/dancefloor/execute` – Figur ausführen + neue Positionen
- `GET /api/dancefloor/state` – Aktuelle Tanzflächen-Position

#### **Such & Filter**
- `GET /api/search` – Figuren-Suche (Query: `q`, `type`, `dancers`)
- `GET /api/figures/bytype/<type>` – Figuren nach Typ filtern

---

## 7. Technologie-Stack

| Layer | Technologie | Rolle |
|-------|------------|-------|
| **Frontend** | HTML5, JavaScript, jstree | Benutzeroberfläche |
| **Backend** | Python 3.x, Flask | API & Business Logic |
| **Data Storage** | JSON (Dateisystem) | Figur-Definitionen |
| **Datenmodell** | Python Classes + JSON | Objekt-Persistierung |
| **Version Control** | Git | Zusammenarbeit |

---

## 8. Dateien & Verzeichnisstruktur

```
DanceCreator/
├── DanceCreator.py                  # Haupteinstiegspunkt (Simulation)
├── Dance.py                         # Verwaltung von Tänzen & Figuren
├── SimpleFigure.py                  # Atomare Tanzfiguren
├── ComplexFigure.py                 # Zusammengesetzte Figuren
├── Figures.py                       # Abstrakte Basis + FigureAddon
├── DanceFloor.py                    # Tanzflächen-Simulation
├── Dancer.py                        # Tänzer-Datenklasse
├── GUI_DanceCreator_App.py          # Flask-API
├── check_figures_api.py             # Test/Debug-Script
├── KONZEPT.md                       # Dieses Dokument
├── Readme.md                        # Basisdokumentation
│
├── Figures/                         # SimpleFigure JSON-Dateien
│   └── *.json                       # Figur-Definitionen (v2)
│
├── Dances/                          # ComplexFigure JSON-Dateien
│   └── *.json                       # Tanz-Definitionen (v3)
│
├── templates/                       # HTML-Templates
│   └── index.html                   # Hauptseite
│
├── static/                          # Statische Ressourcen
│   ├── app.js                       # Frontend-Logik
│   └── style_old.css                # Styling
│
├── ChatGPT/                         # ChatGPT-Prompts/Dokumentation
├── .git/                            # Git-Repository
└── __pycache__/                     # Python Cache
```

---

## 8. Erweiterungspotenziale

### 8.1 Kurzfristig (Nächste Iteration)
- [ ] GUI-Funktionalität vollständig implementieren
- [ ] Drag-and-Drop für Figurenzusammensetzung
- [ ] Grafische Tanzflächen-Visualisierung
- [ ] RESTful API erweitern (CRUD für Figuren)

### 8.2 Mittelfristig
- [ ] Datenbank-Backend (statt JSON-Dateien)
- [ ] Multi-User-Support mit Authentifizierung
- [ ] Import/Export-Formate (z. B. SCD-Notation, LillyPond)
- [ ] Validation & Error-Handling verbessern

### 8.3 Langfristig
- [ ] Mobile-App (React Native/Flutter)
- [ ] Community-Features (Figuren-Sharing, Rating)
- [ ] Musik-Integration (Synchronisierung mit Audio)
- [ ] AI-gestützte Choreografie-Suggestions
- [ ] VR/AR-Visualisierung

---

## 9. Design-Richtlinien

### 9.1 Code-Struktur
- **Separation of Concerns:** Jede Klasse hat eine klare Verantwortung
- **Abstraktion:** Figure-Basisklasse definiert Schnittstelle
- **Rekursion:** ComplexFigure nutzt rekursive Struktur für hierarchische Figuren
- **Lazy Import:** Dance.py nutzt Lazy-Imports um zirkuläre Abhängigkeiten zu vermeiden

### 10.2 Naming-Konventionen
- **Klassen:** PascalCase (SimpleFigure, DanceFloor)
- **Methoden/Funktionen:** camelCase oder lowercase (DanceMove, getCrips)
- **Private Attribute:** Führender Unterstrich (_DanceFloorMap)
- **Konstanten:** UPPER_CASE (FIGURES_DIR)

### 10.3 Fehlerbehandlung
- Aussagekräftige Exception-Messages
- Validierung von JSON-Versions
- Type-Checking für Positionen (list ↔ tuple)

---

## 11. Offene Fragen & Diskussionspunkte

1. **Datenbank-Migration:** Sollte das JSON-Dateisystem durch eine Datenbank ersetzt werden?
2. **Versionierung:** Wie sollten Figuren-Versionen verwaltet werden?
3. **Musik-Integration:** Wie sollen Figuren mit Musik synchronisiert werden?
4. **Benutzerverwaltung:** Ist Multi-User-Support geplant?
5. **Grafik-Engine:** Welche Technologie für 2D/3D-Visualisierung?

---

## 12. Glossar

| Begriff | Definition |
|---------|-----------|
| **Cript** | Textanweisung für einen Tänzer |
| **SimpleFigure** | Atomare, nicht-zerlegbare Tanzfigur |
| **ComplexFigure** | Zusammengesetzte Figur aus mehreren Figuren |
| **DanceFloor** | Die Modellierung der Tanzfläche mit Positionen |
| **Anchor** | Offset-Vektor für Positionsversatz |
| **FigureAddon** | Modifikator für Figuren-Variationen |
| **Bar** | Musikalischer Takt (8 Beats) |
| **Couple** | Tanzpaar (Mann + Frau) |
| **Move** | Eine Bewegung oder Tanzfigur |
| **Facing** | Richtung, zu der ein Tänzer schaut |

---

## 13. Nächste Schritte zur Implementierung

**Nach Genehmigung dieses Konzepts sollte folgende Reihenfolge eingehalten werden:**

1. ✅ **Konzept-Review:** Stakeholder-Feedback einholen
2. 🔲 **Phase 2 - GUI-Entwicklung:** 
   - Frontend-Komponenten erweitern
   - API-Endpunkte implementieren
3. 🔲 **Phase 3 - Datenbank-Migration:**
   - Schema-Design
   - ORM-Integration (SQLAlchemy)
4. 🔲 **Phase 4 - Testing & QA:**
   - Unit-Tests
   - Integrationstests
   - Performance-Tests

---

**Versionskontrolle:**
- Version: 1.0
- Datum: 2026-07-25
- Autor: Copilot
- Status: Entwurf zur Genehmigung
