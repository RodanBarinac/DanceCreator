# Implementierung: GUI (DanceCreator)

Zweck:
Dieses Dokument beschreibt die Umsetzung der Web-GUI, die Anforderungen an die API, sowie die Interaktionen, Visualisierungen und Komponentenschnittstellen.

1) Übersicht der GUI-Architektur
- Dreispalten-Layout: linke Spalte (Katalog), mittlerer Canvas/Content, rechte Spalte (Tanz-Baum, jsTree)
- Responsive Anpassung: Tablet → 2-Spalten, Mobile → 1-Spalte
- Frontend-Technologie: HTML5, JavaScript, jstree, SVG/Canvas; optional D3.js für komplexe Layouts

1.1) Header/Toolbar (oberhalb der Spalten)
- Zweck: Zentrale Steuer- und Managementleiste für Dance-Operationen (Load/Save/Export/Jobs).
- Elemente & Aktionen:
  - Tanz laden: Dropdown mit vorhandenen Tänzen oder Datei-Upload. Aktion: GET /api/dances/<name> (oder POST /api/dances/load). Lädt Tanz in den rechten Baum (jsTree) und aktualisiert Canvas.
  - Tanz speichern (Save / Save As): Öffnet Modal für Metadaten (Name, Version). Aktion: POST /api/dances (create) oder PUT /api/dances/<name> (update). Antwort: Bestätigung + aktualisierte Tree-Node.
  - Vollständige Cripts anfordern: Button "Get Full Cripts" → GET /api/dances/<name>/crips. Ergebnis: Anzeige im Panel und Download-Option (.txt/.md).
  - Video anfordern (Render): Button "Render Video" → POST /api/dances/<name>/render-video (oder POST /api/render-jobs with dance + options). Response: Job-ID. Polling: GET /api/render-status/<jobid>. Fertiges Video: GET /api/dances/<name>/video or direct download URL. UI: Fortschrittsanzeige, Benachrichtigung, eingebetteter Player/Download-Link.
  - Export / Drucken: PDF-Export-Button → GET /api/dances/<name>/export?format=pdf oder clientseitig generieren.
- UI-Elemente: Aktueller Tanz-Name, Breadcrumbs, Status-Indikator (Speicher-/Render-Status), Spinner/Progressbar, Autosave-Toggle.
- Verhalten: Long-running Aktionen (Video-Rendering) sollten asynchron mit Job-Status-API implementiert werden; UI zeigt Status und erlaubt Abbruch.



2) Komponenten & Verhalten
- Linke Spalte (Figures-Katalog): Suche, Filter, Kategoriebaum, Liste mit Thumbnails
  - Datenquelle: GET /api/figures
  - Interaktion:
    - Click → lädt die Figur auf den Canvas (GET /api/figures/<name>)
    - Drag & Drop → In den Tanz-Baum (rechte Spalte, jsTree): Figuren können per Drag&Drop in den Baum eingefügt werden; sie werden an der Position im Baum eingefügt, an der der Cursor losgelassen wird. (Phase 2)

- Mittlerer Bereich (Canvas): 4 Modi
  - Modus A: Figur-Details (Name, Version, Beschreibung, Cripts ungefüllt)
    - render: miniature SVG + Cripts (template lines)
  - Modus B: Figur im Tanz-Kontext
    - benötigt: DanceFloor-State (GET /api/dancefloor/state)
    - Darstellung: Start/End-Positionen, Vektoren
    - Interaktion: Parameter der Figur können verändert werden (z. B. Anchor/Offset, Addons/Varianten, Partner-Zuordnungen, Bars-Offset).
      - UI-Controls: numeric Anchor-Eingaben, Addons Key/Value-Editor, Dropdowns für Partner-/Zielpositionen, Bars-Offset-Feld.
      - Aktionen: "Preview" → zeigt lokal auf dem Canvas die Wirkung der geänderten Parameter; "Apply/Execute" → POST /api/dancefloor/execute mit aktuellen Parametern.
  - Modus C: Mehrere Figuren (Akkordeon/Tabs)
  - Modus D: Ganzer Tanz (komplette Choreografie, Playback controls optional)

- Rechte Spalte (jsTree): Tanz-Baum
  - Datenquelle: GET /api/dances/<name>
  - Node-Format: jsTree kompatible JSON (id, text, children, data{type, bars, name})
  - Click → load node data → render in Canvas

3) Rendering & Visualisierung
- Use SVG for static vectors + labels; Canvas for animation (performance)
- Position-Namen (1m, 1w, between1c) als node IDs
- Farben: per couple, legend component
- Animations: Play/Pause, bar-scrubber; backend liefert positions per bar if available via GET /api/dances/<name>/visualization

4) API-Konnektivität (erwartete Payloads)
- GET /api/figures -> [{"Name":..., "Version":..., "Bars":..., "thumbnail": "/api/figures/<name>/thumbnail"}]
- GET /api/figures/<name> -> full JSON (Simple/Complex)
- GET /api/figures/<name>/crips -> ["Bar 1-8: ..."]
- GET /api/dances/<name> -> {"Name":..., "FigureList": [...], "meta": {...}}
- POST /api/dancefloor/init -> {"couples": 3} -> returns DanceFloor JSON
- POST /api/dancefloor/execute -> {"figure": "Reel Across", "anchor": [1,1]} -> returns {"floor": {...}, "crips": [...]} 

5) UI Data Flows & Event Sequence
- Start: load figures list + dances list
- User selects figure → request figure JSON and crips → render details
- User executes figure in context → POST /api/dancefloor/execute → update Canvas with returned floor

6) Implementierungspraktische Hinweise
- use fetch()/axios with error handling
- cache thumbnails and figures metadata to reduce calls
- keep Canvas rendering decoupled from data model (separate renderer module)
- provide a minimal CSS theme; existing static/style_old.css can be refactored

7) Tests / QA
- E2E: simulate loading a dance, executing a figure and asserting returned floor positions
- Unit: renderer functions (coordinate transforms), jsTree node building

8) Dateien
- templates/index.html (root), static/app.js (main logic), static/style.css

---
Kurzanleitung: Die GUI-Implementierung konsumiert die Backend-API (siehe IMPLEMENTIERUNG_BACKEND.md). Dieses Dokument definiert die erwarteten Endpunkte, Payloads und UI-Flows, sodass Frontend- und Backend-Teams unabhängig implementieren können.
