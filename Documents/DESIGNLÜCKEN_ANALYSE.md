# Analyse der Designlücken und erforderlichen Präzisierungen

> **Valid from version:** -  
> **End of validity:** -  
> **Status:** LEGACY - Design reference document  
> **Last updated:** 2026-08-23

## Überblick
Diese Analyse identifiziert Punkte in den Designdokumenten, die zu schwachen Implementierungen führten:
1. **Fehlende Card-Visualisierung** für die linke Spalte (Figures-Katalog)
2. **Flache Hierarchie statt tiefe Hierarchie** im jsTree der rechten Spalte

---

## 1. PROBLEM: Linke Spalte - Figures-Katalog nicht als Cards implementiert

### Aktueller Zustand im Dokument (IMPLEMENTIERUNG_GUI.md)
**Linie 33-37:**
```
- Linke Spalte (Figures-Katalog): Suche, Filter, Kategoriebaum, Liste mit Thumbnails
  - Datenquelle: GET /api/figures
  - Interaktion:
    - Click → lädt die Figur auf den Canvas (GET /api/figures/<name>)
    - Drag & Drop → In den Tanz-Baum (rechte Spalte, jsTree): ...
```

### Analyse der Lücken

#### 1.1 Unklare Darstellungsform
**Problem:** Die Formulierung "Liste mit Thumbnails" ist mehrdeutig. Sie könnte bedeuten:
- Eine einfache HTML-Liste (`<li>`)
- Ein Textverzeichnis mit Small-Vorschaubildern
- Eine echte Card-basierte Grid-Darstellung

**Fehlende Spezifikationen:**
- Sollten die Figure-Einträge in einer **Grid-Layout oder Flex-Layout** mit mehreren Spalten angezeigt werden?
- Welche **visuellen Komponenten** macht eine Card aus?
  - Thumbnail-Größe (z.B. 120x120px)?
  - Titel/Name-Anzeige?
  - Beschreibung/Version?
  - Kategorie-Tag?
  - Hover-Effekt?
- Sollte die Liste **scrollbar** oder pageiniert sein?

#### 1.2 Card-Layout-Struktur nicht spezifiziert
**Fehlende Elemente einer Card:**
- Größe und Spacing zwischen Cards
- Responsive Verhalten (Anzahl Spalten bei verschiedenen Breiten)
- Hover-Interaktionen (Vergrößerung, Highlight, Shadow-Effekt)
- Fokus-Zustand für Tastaturnavigation

#### 1.3 Keine Klarheit über Card-Inhalte
**Fragen, die das Dokument nicht beantwortet:**
- Wird nur der Name angezeigt oder auch Bars, Version, Beschreibung?
- Wird die Kategorie/Typ (SimpleFigure vs. ComplexFigure) angezeigt?
- Werden Metadaten wie "Schwierigkeit" oder "Tags" angezeigt?

#### 1.4 Filtering und Suche auf Card-Ebene
**Lücke:** Wie sollten Filter/Suche die Card-Liste verändern?
- Instant-Filtering während des Tippens?
- Animierte Übergänge beim Ausblenden von Cards?
- Sollten keine Treffer angezeigt werden, was passiert?

---

## 2. PROBLEM: Rechte Spalte - jsTree mit flacher statt tiefer Hierarchie

### Aktueller Zustand im Dokument

#### 2.1 IMPLEMENTIERUNG_BACKEND.md - Tree-Format (Linie 70-114)
Das Dokument definiert die jsTree-Node-Struktur sehr detailliert:

**Was beschrieben ist:**
- Node-Felder: id, text, children, type, data
- Rekursive Verarbeitung von Sequenzen ("s") und Parallel ("p")
- Anchor-Preservation in data.anchor
- Beispiel-Nodes (Leaf und Sequence)

**Was NICHT klar beschrieben ist:**

#### 2.2 Tiefe der Hierarchie - Zentrale Lücke
**Problem:** Das Dokument sagt nicht explizit, wie tiefe Hierachien aufgebaut werden sollen!

**Szenarien, die nicht klar beschrieben sind:**

1. **Nested Sequences und Parallels:**
   - Wenn eine FigureList enthält: `[[0,0], ["s", [ [[0,0], ["p", [...]]], [...] ]]]`
   - Sollte jede Ebene einen Container-Node erzeugen?
   - Oder sollten flache Sequenzen "durchsichtig" werden?

2. **Gruppierung nach Logik:**
   - Sollten Figures mit gleichen Anchors gruppiert werden?
   - Sollten "Sub-Sections" (z.B. Introduction, Main, Ending) explizit im Tree sichtbar sein?

3. **Naming von nicht-Figur-Nodes:**
   - Linie 109-113 zeigt nur ein generisches "Sequence" label
   - Keine Regeln für aussagekräftige Labels für parallele/sequenzielle Container
   - Sollten sie Bars-Bereiche anzeigen? (z.B. "Sequence [Bar 1-16]")

#### 2.3 Fehlende Regeln für Tree-Aufbau
**Unklarheiten im Backend-Dokument:**

1. **Anchor-Offsets in Labels:**
   - Linie 95: Beispiel zeigt `"text": "Reel Across [Bar 1-8]"`
   - Wo kommen [Bar 1-8] her? Aus figure.Bars oder aus Kontext-Berechnung?
   - Sollte der Anchor auch im Text angezeigt werden? z.B. "Reel Across [Bar 1-8] @[0,1]"?

2. **Darstellung von Addons/Varianten:**
   - Wenn eine Figure Addons hat, sollten diese im Tree-Label sichtbar sein?
   - Beispiel: "Reel Across (mit Facing)"?

3. **Determinismus beim Node-ID-Vergabe:**
   - Linie 121: "Ensure all nodes have unique IDs"
   - Linie 72: "use deterministic IDs when possible, e.g., 'root', 'fig-1', or path-like '0.1.2'"
   - Aber: Keine Regel, wie die path-like IDs aufgebaut werden!
   - Sollte "0.1.2" bedeuten: FigureList[0], Sub[1], Sub[2]? Oder etwas anderes?

#### 2.4 Keine Visualisierungs-Regeln für verschiedene Node-Typen
**Lücke:** Unterscheiden sich "seq", "par", "figure", "dance" Nodes visuell?
- Sollten parallele Nodes anders aussehen als sequenzielle? (Icon, Farbe, etc.)
- Sollten leaf-Nodes (Figuren) anders gestaltet werden als Container?

#### 2.5 Interaction-Regeln für Hierarchie-Manipulation
**Dokument sagt (Linie 117):**
- "When a node is moved in the tree, emit a backend call"
- "PUT /api/dances/<name>/tree to accept updates"

**Aber nicht beschrieben:**
- Wie wird Move/Drag im Tree begrenzt? (z.B. darf man einen "seq"-Node unter "par" verschieben?)
- Kann man Nodes neu ordnen innerhalb einer Sequenz? (ja, wahrscheinlich)
- Kann man Nodes in/aus Parallels ziehen? (unklar)
- Was passiert mit Anchors wenn eine Figure in eine tiefere Ebene verschoben wird?

---

## 3. Spezifische fehlende Beschreibungen

### 3.1 IMPLEMENTIERUNG_GUI.md - Fehlerhafte oder unvollständige Punkte

| Zeile | Bereich | Problem | Fehlende Information |
|-------|---------|---------|----------------------|
| 33 | Figures-Katalog | "Liste mit Thumbnails" | Card-Format, Größen, Layout, Responsive |
| 34 | Datenquelle | GET /api/figures | Welche Felder? (Name, Desc, Version, Tags?) |
| 36-37 | Drag & Drop | "können eingefügt werden" | In welche Position? Anchor-Berechnung? |
| 57-60 | jsTree | Node-Format vage | Tree-Depth, Labeling-Regeln, ID-Schema |
| 60 | Click-Verhalten | "load node data" | Welche Daten? Wie wird Canvas aktualisiert? |

### 3.2 IMPLEMENTIERUNG_BACKEND.md - Präzisierungs-Notwendigkeiten

| Zeile | Bereich | Problem | Fehlende Information |
|-------|---------|---------|----------------------|
| 72-88 | Tree Format | Rekursive Struktur vage | Exakte Regeln für Tiefe, Splitting von langen Listen |
| 84-88 | Representation rules | "create parent node recursively" | Wann neue Nodes, wann durchsichtig machen? |
| 95-104 | Example nodes | Nur generische Beispiele | Komplexe nested Beispiele fehlen |
| 121-124 | Backend responsibilities | Update-Logik unklar | Wie wird PUT /api/dances/<name>/tree validiert? |

---

## 4. Empfohlene Präzisierungen und Ergänzungen

### 4.1 Für die Figures-Katalog (linke Spalte)

**Zu ergänzen in IMPLEMENTIERUNG_GUI.md - nach Linie 37:**

```markdown
### 2.0.1) Figures-Katalog - Card-basierte Darstellung

**Card-Komponente Struktur:**
- Größe: 200x250px (Card), Thumbnail: 180x120px, responsiv auf Tablet: 150x200px
- Layout: CSS Grid mit min-width: 200px (auto-wrap bei Viewport-Größe)
- Elemente pro Card:
  1. Thumbnail (SVG oder Bild)
  2. Figure-Name (fettgedruckt, max 20 Zeichen mit Ellipsis)
  3. Version & Bars (grau, klein)
  4. Kategorie-Badge (Tag, z.B. "Simple", "Complex", "Parallel")
  5. Hover-Effekt: Shadow + leichte Vergrößerung (transform: scale(1.02))

**Card-Inhalte (von GET /api/figures):**
- name: string
- version: int
- bars: int
- type: string ("simple" | "complex")
- thumbnail: URI (API-Pfad oder SVG inline)
- description: string (optional, tooltip on hover)

**Filter & Suche:**
- Echtzeit-Filter während Eingabe (z.B. Lodash debounce, 300ms)
- Cards mit Transition fade-out/fade-in animieren (200ms)
- "Keine Ergebnisse"-Meldung bei 0 Treffern

**Pagination/Scrolling:**
- Virtuelle Scroll-Liste für Performance (bei >100 Figures)
- oder: Lazy Loading bei Scroll zum Ende

**Drag-Quelle für jsTree:**
- dataTransfer.setData("figure", figureName) beim Drag-Start
- Visual Feedback: Cursor + Drag-Image mit Figure-Icon
```

### 4.2 Für den jsTree (rechte Spalte)

**Zu ergänzen in IMPLEMENTIERUNG_BACKEND.md - nach Linie 89:**

```markdown
### 5.0.1) jsTree-Hierarchie: Tiefe und Struktur-Regeln

**Aufbau-Prinzipien:**
1. **Root-Node:** Die ComplexFigure selbst wird zum Root-Node (type: "dance")
   - id: "root"
   - text: "{DanceName} [Bar 1-{totalBars}]"
   - children: rekursiv aus FigureList

2. **FigureList-Verarbeitung:**
   - Jedes Entry erzeugt 1-n Child-Nodes
   - String-Entry ("FigureName") → 1 leaf node (type: "figure")
   - Sequenz-Entry (["s", [...]]) → 1 container node (type: "seq") + recursive children
   - Parallel-Entry (["p", [...]]) → 1 container node (type: "par") + recursive children

3. **ID-Schema (deterministische, path-artige IDs):**
   - Root: "root"
   - FigureList Level: "fig-{index}" (z.B. "fig-0", "fig-1")
   - Sequenz-Container: "seq-{parent-id}-{index}" (z.B. "seq-fig-0-0")
   - Parallel-Container: "par-{parent-id}-{index}" (z.B. "par-fig-1-2")
   - Leaf-Figures: "leaf-{path}" (z.B. "leaf-fig-0-0-1")

4. **Label-Generierung:**
   - Leaf-Nodes (figures):
     ```
     "{figureName} [Bar {startBar}-{endBar}]"
     if anchor != [0,0]:
       append " @[{anchor[0]},{anchor[1]}]"
     if addons:
       append " (Addons: {addon_keys})"
     ```
   - Container-Nodes (seq/par):
     ```
     if type == "seq":
       label = "Sequence [Bar {startBar}-{endBar}]"
     else if type == "par":
       label = "Parallel [Bar {startBar}-{endBar}]"
       (optional: num_sub-figures anzeigen)
     ```

5. **Bars-Berechnung:** Jeder Node muss startBar/endBar kennen (akkumuliert von Figuren)
   - Speichern in data.bars: [startBar, endBar]
   - Bei sequenziellen: Summation
   - Bei parallelen: Max (alle Parallel-Figuren zusammen dauern so lange wie die längste)

6. **Preservation von Struktur-Info:**
   - data.anchor: immer vorhanden (auch [0,0] wenn nicht gesetzt)
   - data.addons: immer vorhanden (auch {} wenn leer)
   - data.original: speichert das originale FigureList-Entry als Rekonstruktions-Schlüssel
   - data.type: "figure" | "seq" | "par" | "dance" (redundant mit top-level type, aber hilfreich)

**Beispiel: Komplexe verschachtelte Struktur**

Input FigureList:
```
[
  [0,0], "Reel Across",
  [0,0], ["s", [
    [[0,0], "Right Hand Turn"],
    [[1,0], ["p", [
      [[0,0], "1st Corners Pass"],
      [[0,0], "2nd Corners Pass"]
    ]]]
  ]]
]
```

Resulting Tree:
```
{
  "id": "root",
  "text": "My Dance [Bar 1-48]",
  "type": "dance",
  "children": [
    {
      "id": "fig-0",
      "text": "Reel Across [Bar 1-8]",
      "type": "figure",
      "data": {
        "figureName": "Reel Across",
        "bars": [1, 8],
        "anchor": [0, 0],
        "addons": {},
        "original": [[0,0], "Reel Across"]
      },
      "children": []
    },
    {
      "id": "fig-1",
      "text": "Sequence [Bar 9-48]",
      "type": "seq",
      "data": {
        "bars": [9, 48],
        "original": [[0,0], ["s", [...]]]
      },
      "children": [
        {
          "id": "seq-fig-1-0",
          "text": "Right Hand Turn [Bar 9-16]",
          "type": "figure",
          "data": {
            "figureName": "Right Hand Turn",
            "bars": [9, 16],
            "anchor": [0, 0],
            "addons": {},
            "original": [[0,0], "Right Hand Turn"]
          },
          "children": []
        },
        {
          "id": "seq-fig-1-1",
          "text": "Parallel [Bar 17-48]",
          "type": "par",
          "data": {
            "bars": [17, 48],
            "anchor": [1, 0],
            "original": [[1,0], ["p", [...]]]
          },
          "children": [
            {
              "id": "par-seq-fig-1-1-0",
              "text": "1st Corners Pass [Bar 17-24]",
              "type": "figure",
              "data": {
                "figureName": "1st Corners Pass",
                "bars": [17, 24],
                "anchor": [0, 0],
                "addons": {},
                "original": [[0,0], "1st Corners Pass"]
              },
              "children": []
            },
            {
              "id": "par-seq-fig-1-1-1",
              "text": "2nd Corners Pass [Bar 17-24]",
              "type": "figure",
              "data": {
                "figureName": "2nd Corners Pass",
                "bars": [17, 24],
                "anchor": [0, 0],
                "addons": {},
                "original": [[0,0], "2nd Corners Pass"]
              },
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

**Frontend-Anforderungen zur Darstellung:**
- Icons für node types: 🎯 figure, ➡️ sequence, ⏸️ parallel, 💃 dance
- Container-Nodes (type: seq/par) sollten expandierbar/kollabierbar sein (jsTree default)
- Leaf-Nodes sollten auf Doppelklick in Canvas laden
- Visuelle Unterscheidung: parallele Nodes in anderer Farbe/Icon

**Interaction & Tree-Manipulation:**
- Drag & Drop innerhalb des Trees:
  - Figur in sequence: reordern OK (ändert FigureList-Order)
  - Figur aus par in seq verschieben: Anchor-Anpassung notwendig (Backend-Logik)
  - Hinzufügen neuer Figuren aus Katalog: 
    - Drag figure → release auf Tree
    - Backend: Berechnet Anchor basierend auf Drop-Position, fügt zu FigureList hinzu
- Node-Deletion: Backend muss FigureList entsprechend aktualisieren
- Persistence: PUT /api/dances/<name>/tree mit rekonstruierter FigureList
```

---

## 5. Zusammenfassung: Priorität der Verbesserungen

### Kritisch (Must-Have für nächste Implementierung)
1. ✅ **Card-Layout-Spezifikation** für Figures-Katalog (Größen, Spacing, Responsive)
2. ✅ **jsTree-Hierarchie-Tiefe-Regeln** (wann container nodes, ID-Schema)
3. ✅ **Label-Generierung-Algorithmen** (Bars-Berechnung, Anchor-Anzeige)
4. ✅ **Komplexe verschachtelte Beispiele** im Backend-Dokument

### Wichtig (Sollte klar sein)
5. ✅ **Drag & Drop Regeln** für Tree-Manipulation (was erlaubt, Anchor-Behandlung)
6. ✅ **Filter/Suche-Verhalten** auf Card-Liste (Echtzeit, Animation)
7. ✅ **Node-Typ Visualisierung** (Icons, Farben, unterschiedliche Darstellung)

### Schön-zu-haben (Phase 2+)
8. Virtuelles Scrolling für große Figure-Listen
9. Advanced Tree-Editing (Node-Einfügen nach, duplizieren, löschen)
10. Undo/Redo für Tree-Änderungen

---

## 6. Implementierungsleitfaden für nächsten Versuch

**Vor der Implementierung:**
1. Aktualisiere IMPLEMENTIERUNG_GUI.md mit Card-Spezifikation (Abschnitt 2.0.1)
2. Aktualisiere IMPLEMENTIERUNG_BACKEND.md mit Tree-Hierarchie-Regeln (Abschnitt 5.0.1)
3. Erstelle ein Testdokument mit konkreten Beispielen (simple, complex, parallel-nested)
4. Definiere Akzeptanzkriterien für Cards und Tree-Darstellung

**Während der Implementierung:**
- Entwickle zuerst die Card-Komponente mit Unit-Tests
- Implementiere jsTree-Builder mit Test-Fixtures für verschiedene Hierarchie-Tiefen
- Teste Drag & Drop und Persist-Logik mit echten Tanz-Daten

**After Launch:**
- QA: Visuelle Vergleiche mit dieser Spezifikation durchführen
- User-Feedback: Hat die tiefe Hierarchie die gewünschte Klarheit gebracht?

