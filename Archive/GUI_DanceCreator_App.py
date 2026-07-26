"""
DanceTreeApp - ein kleines Flask-Backend für die HTML5-GUI.

Beschreibung:
 - Liefert die HTML-Seite (templates/index.html)
 - Stellt statische Dateien unter /static bereit (style_old.css, app.js)
 - Bietet einen einfachen API-Endpunkt /tree, der eine JSON-Datei (aus ./Figures)
   einliest und als flache Liste von Knoten mit id/parent_id zurückgibt.

Anleitung:
1. Kopiere diese Ordnerstruktur in dein Projekt oder nutze sie standalone:
    DanceTreeApp/
    ├── GUI_DanceCreator_App.py
    ├── templates/
    │   └── index.html
    ├── static/
    │   ├── style_old.css
    │   └── app.js
    └── Figures/         <-- JSON-Dateien hier ablegen (z. B. HLReelAD.json)

2. Abhängigkeiten installieren:
    pip install flask

3. Starten:
    python GUI_DanceCreator_App.py

4. Öffne im Browser:
    http://127.0.0.1:5000

Hinweis:
 - Die GUI zeigt links die Figurenliste und rechts die Baumstruktur.
 - Die mittlere Tanzfläche ist ein Platzhalter (keine Drag&Drop-Funktionalität).
 - Diese Datei ist ausführlich kommentiert; passe die Parserlogik im Bereich `build_tree_from_json`
   an, falls deine JSON-Struktur stärker von den Beispielen abweicht.
"""

from flask import Flask, jsonify, request, render_template
import json
import os
import uuid

Figure_DB = {}
app = Flask(__name__, template_folder="templates", static_folder="static")

# Ordner, in dem der Benutzer seine JSON-Files ablegen soll
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "Figures")
DANCES_DIR = os.path.join(os.path.dirname(__file__), "Dances")

def load_Figuers():
    """Lädt alle .json Dateien aus FIGURES_DIR in das globale Figure_DB."""
    global Figure_DB
    Figure_DB = {}
    if not os.path.isdir(FIGURES_DIR):
        return
    for fname in os.listdir(FIGURES_DIR):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(FIGURES_DIR, fname)
        try:
            with open(fpath, encoding='utf-8') as f:
                data = json.load(f)
            name = data.get('Name') or data.get('name') or fname[:-5]
            # ensure we keep the original object but mark type if possible
            Figure_DB[name] = data
#            if 'FigureList' in Figure_DB[name]:
#                Figure_DB[name]['type'] = 'complex'
#            elif 'Addons' in Figure_DB[name]:
#                Figure_DB[name]['type'] = 'simple'
#            else:
#                Figure_DB[name].setdefault('type', 'unknown')

        except Exception:
            # ignore files that can't be parsed
            continue
    return


# ***************************************
# ***   Funktionen zum Baumdiagramm   ***
# ***************************************

# unique ID
nid = f"_{uuid.uuid4().hex[:8]}"


def make_node(item_id, Data):
    """Erzeuge einen jsTree-kompatiblen Knoten aus einem Figure-Objekt."""
    name = Data.get('Name') or Data.get('name') or str(item_id)
    ntype = Data.get('type', 'unknown')
    node = {
        "id": f"{name}_{nid}",
        "text": name,
        "type": ntype,
        "meta": Data
    }
    if ntype == 'complex':
        node["children"] = True
    return node


def build_tree_from_json(data):
    """Kleine Fallback-Funktion, die gängige JSON-Formate in eine flache Knotenliste umwandelt.

    Das reicht für die GUI, die im Moment nur eine flache Liste/Root benötigt.
    """
    nodes = []
    if isinstance(data, dict):
        # direkte FigureList
        if 'FigureList' in data and isinstance(data['FigureList'], list):
            for i, item in enumerate(data['FigureList']):
                name = item.get('Name') or item.get('name') or f"Figure {i+1}"
                nodes.append({'id': i+1, 'parent_id': None, 'name': name, 'type': item.get('type', 'unknown'), 'meta': item})
        # einzelnes Objekt
        elif 'Name' in data or 'name' in data:
            name = data.get('Name') or data.get('name')
            nodes.append({'id': 1, 'parent_id': None, 'name': name, 'type': data.get('type', 'unknown'), 'meta': data})
        else:
            # suche Listen in Feldern
            for k, v in data.items():
                if isinstance(v, list):
                    for i, item in enumerate(v):
                        name = item.get('Name') or item.get('name') or f"{k}_{i+1}"
                        nodes.append({'id': len(nodes)+1, 'parent_id': None, 'name': name, 'type': item.get('type', 'unknown'), 'meta': item})
    elif isinstance(data, list):
        for i, item in enumerate(data):
            name = item.get('Name') or item.get('name') or str(i+1)
            nodes.append({'id': i+1, 'parent_id': None, 'name': name, 'type': item.get('type', 'unknown'), 'meta': item})
    return nodes


@app.route('/get_nodes/<node_Name>')
def get_nodes(node_Name):
    if node_Name in Figure_DB:
        data = Figure_DB[node_Name]
        return make_node(node_Name, data)
    else:
        node = {
            "id": "Dance (leer)",
            "parent_id": None,
            "name": "Dance (leer)",
            "meta": {}
        }
    return node


@app.route("/")
def index():
    """
    Liefert die Hauptseite (templates/index.html).
    """
    return render_template("index.html")


@app.route("/tree")
def tree():
    fname = request.args.get("file") or "HLReelAD.json"
    candidates = [
        fname,
        os.path.join(FIGURES_DIR, fname),
        os.path.join(DANCES_DIR, fname),
        os.path.join(os.path.dirname(__file__), fname)
    ]
    data = None
    for c in candidates:
        if os.path.isfile(c):
            with open(c, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = None
            break

    if data is None:
        nodes = [{
            "id": 1,
            "parent_id": None,
            "name": "Dance (leer)",
            "meta": {}
        }]
        return jsonify(nodes)

    try:
        nodes = build_tree_from_json(data)
    except Exception:
        nodes = []
        if isinstance(data, list):
            for i, item in enumerate(data):
                nodes.append({
                    "id": i + 1,
                    "parent_id": None,
                    "name": item.get('Name') or item.get('name') or str(i + 1),
                    "meta": item
                })

    if not nodes:
        nodes = [{
            "id": 1,
            "parent_id": None,
            "name": "Dance (leer)",
            "meta": {}
        }]
    return jsonify(nodes)


@app.route('/figures')
def figures():
    """Gibt alle Figuren (vollständige Objekte) aus Figure_DB zurück.

    Jede Figur wird als JSON-Objekt geliefert. Zusätzlich wird ein einheitliches
    Feld 'name' gesetzt (falls nicht vorhanden) für die GUI.
    """
    result = []
    for key, obj in Figure_DB.items():
        # Wir wollen das Original-Objekt nicht verändern. Erstelle eine flache Kopie
        if isinstance(obj, dict):
            item = dict(obj)
        else:
            # falls der Eintrag kein dict ist, packe ihn unter 'data'
            item = {'data': obj}

        # Einheitliche Zusatzfelder, die die GUI erwarten kann
        item.setdefault('name', item.get('Name') or item.get('name') or key)
        # Entferne das Feld 'type', es wird nicht mehr benötigt
        if 'type' in item:
            item.pop('type', None)
        # key ist der Schlüssel in Figure_DB (kann z.B. vom Dateinamen abgeleitet worden sein)
        item['key'] = key

        result.append(item)

    # sortiere stabil nach name
    result.sort(key=lambda x: str(x.get('name', '')).lower())
    return jsonify(result)


@app.route('/dances')
def list_dances():
    """Gibt eine alphabetisch sortierte Liste der .json Dateien im DANCES_DIR zurück."""
    try:
        if not os.path.isdir(DANCES_DIR):
            return jsonify({'error': 'Dances directory not found'}), 404
        files = [f for f in os.listdir(DANCES_DIR) if f.lower().endswith('.json')]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    os.makedirs(FIGURES_DIR, exist_ok=True)
    load_Figuers()
    print("\nStarte DanceTreeApp (Flask). Lege JSON-Dateien in das Verzeichnis 'Figures'.")
    app.run(debug=True)
