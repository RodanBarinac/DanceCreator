"""
DanceTreeApp - ein kleines Flask-Backend f?r die HTML5-GUI.

Beschreibung:
 - Liefert die HTML-Seite (templates/index.html)
 - Stellt statische Dateien unter /static bereit (style_old.css, app.js)
 - Bietet einen einfachen API-Endpunkt /tree, der eine JSON-Datei (aus ./Figures)
   einliest und als flache Liste von Knoten mit id/parent_id zur?ckgibt.

Anleitung:
1. Kopiere diese Ordnerstruktur in dein Projekt oder nutze sie standalone:
    DanceTreeApp/
    ??? GUI_DanceCreator_App.py
    ??? templates/
    ?   ??? index.html
    ??? static/
    ?   ??? style_old.css
    ?   ??? app.js
    ??? Figures/         <-- JSON-Dateien hier ablegen (z. B. HLReelAD.json)

2. Abh?ngigkeiten installieren:
    pip install flask

3. Starten:
    python GUI_DanceCreator_App.py

4. ?ffne im Browser:
    http://127.0.0.1:5000

Hinweis:
 - Die GUI zeigt links die Figurenliste und rechts die Baumstruktur.
 - Die mittlere Tanzfl?che ist ein Platzhalter (keine Drag&Drop-Funktionalit?t).
 - Diese Datei ist ausf?hrlich kommentiert; passe die Parserlogik im Bereich `build_tree_from_json`
   an, falls deine JSON-Struktur st?rker von den Beispielen abweicht.
"""

from flask import Flask, jsonify, request, render_template
import json
import os
import uuid
from SimpleFigure import SimpleFigure

Figure_DB = {}
Figure_File_DB = {}
app = Flask(__name__, template_folder="templates", static_folder="static")

# Ordner, in dem der Benutzer seine JSON-Files ablegen soll
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "Figures")
DANCES_DIR = os.path.join(os.path.dirname(__file__), "Dances")


def iter_json_files(root_dir):
    for base, _, files in os.walk(root_dir):
        for fname in files:
            if fname.lower().endswith('.json') and not fname.lower().endswith('.schema.json'):
                yield os.path.join(base, fname)


def load_Figuers():
    """L?dt alle .json Dateien aus FIGURES_DIR in das globale Figure_DB."""
    global Figure_DB, Figure_File_DB
    Figure_DB = {}
    Figure_File_DB = {}
    if not os.path.isdir(FIGURES_DIR):
        return
    for fpath in iter_json_files(FIGURES_DIR):
        try:
            data = _load_json_file(fpath)
            key = data.get('Name') or data.get('name') or os.path.splitext(os.path.basename(fpath))[0]
            Figure_DB[key] = data
            Figure_File_DB[key] = os.path.relpath(fpath, FIGURES_DIR)
        except Exception:
            continue
    return


def figure_summary(key, data):
    return {
        'file': Figure_File_DB.get(key, key + '.json'),
        'key': key,
        'Name': data.get('Name') or data.get('name') or key,
        'Desc': data.get('Desc'),
        'Bars': data.get('Bars'),
        'Version': data.get('Version')
    }


def dance_summary(path, data):
    rel_path = os.path.relpath(path, DANCES_DIR)
    return {
        'file': rel_path,
        'Name': data.get('Name') or os.path.splitext(os.path.basename(path))[0],
        'Desc': data.get('Desc'),
        'shape': data.get('shape') or data.get('Shape'),
        'Version': data.get('Version')
    }


def _load_json_file(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def _identifier_variants(identifier):
    raw = str(identifier).strip()
    if raw.lower().endswith('.json'):
        raw = raw[:-5]
    return {raw.lower(), (raw + '.json').lower()}


def _find_json_file(identifier, roots, skip_rel_prefixes=None):
    skip_rel_prefixes = skip_rel_prefixes or []
    wanted = _identifier_variants(identifier)

    for root in roots:
        root_dir = os.path.join(os.getcwd(), root)
        if not os.path.isdir(root_dir):
            continue
        for fpath in iter_json_files(root_dir):
            rel = os.path.relpath(fpath, root_dir)
            if any(rel.startswith(prefix) for prefix in skip_rel_prefixes):
                continue
            basename = os.path.basename(fpath).lower()
            stem = os.path.splitext(basename)[0]
            if basename in wanted or stem in wanted:
                return fpath
            try:
                data = _load_json_file(fpath)
            except Exception:
                continue
            for key in ('Name', 'name', 'key'):
                value = data.get(key)
                if isinstance(value, str) and value.strip().lower() in wanted:
                    return fpath
    return None


def _figure_detail_path(identifier):
    return _find_json_file(identifier, ['Figures', 'Dances'])


def _dance_detail_path(identifier):
    return _find_json_file(identifier, ['Dances'])


def _figure_node_name(entry):
    if isinstance(entry, list):
        if len(entry) > 1 and isinstance(entry[1], list):
            if len(entry[1]) > 0 and isinstance(entry[1][0], str) and entry[1][0] not in ('s', 'p'):
                return entry[1][0]
            return 'Group'
        if len(entry) > 1:
            return str(entry[1])
    if isinstance(entry, dict):
        return entry.get('Name') or entry.get('name') or 'Figure'
    return str(entry)


def _build_dance_tree(entry, node_id):
    if not isinstance(entry, list) or len(entry) < 2:
        return {
            'id': str(node_id),
            'text': str(entry),
            'children': [],
            'data': {'original': entry}
        }

    anchor = entry[0] if isinstance(entry[0], list) and len(entry[0]) == 2 else [0, 0]
    fig = entry[1]

    if isinstance(fig, list) and len(fig) == 2 and fig[0] in ('s', 'p'):
        children = []
        for index, child in enumerate(fig[1]):
            children.append(_build_dance_tree(child, f"{node_id}-{index}"))
        return {
            'id': str(node_id),
            'text': 'Sequential Group' if fig[0] == 's' else 'Parallel Group',
            'children': children,
            'type': 'group',
            'data': {'mode': fig[0], 'anchor': anchor, 'original': entry}
        }

    node_name = _figure_node_name(fig)
    data = {'figureName': node_name, 'anchor': anchor, 'original': entry}
    if isinstance(fig, list) and len(fig) > 1 and isinstance(fig[1], list) and len(fig[1]) == 2:
        data['addons'] = fig[1][1]
    return {
        'id': str(node_id),
        'text': node_name,
        'children': [],
        'type': 'figure',
        'data': data
    }


def build_dance_tree(data, name='Dance'):
    children = []
    figure_list = data.get('FigureList') if isinstance(data, dict) else []
    if isinstance(figure_list, list):
        for index, entry in enumerate(figure_list):
            children.append(_build_dance_tree(entry, f"node-{index}"))
    return {
        'id': 'root',
        'text': name,
        'children': children,
        'data': {
            'figureName': name,
            'version': data.get('Version') if isinstance(data, dict) else None,
            'original': figure_list if isinstance(figure_list, list) else []
        }
    }


def _serialize_dancer(dancer):
    gender = getattr(dancer, 'gender', '')
    if isinstance(gender, str):
        gender_lower = gender.lower()
        if gender_lower.startswith('m'):
            gender = 'M'
        elif gender_lower.startswith('f'):
            gender = 'F'
        elif gender_upper := gender.upper():
            gender = gender_upper[0]
    return {
        'name': getattr(dancer, 'name', ''),
        'gender': gender
    }


def _serialize_floor(floor):
    positions = {}
    dance_map = getattr(floor, 'DanceFloorMap', {})
    for pos, (dancer, facing) in dance_map.items():
        row = int(pos[0])
        col = int(pos[1])
        if col == 1:
            key = f'{row}m'
        elif col == 3:
            key = f'{row}w'
        else:
            key = f'{row}:{col}'
        positions[key] = {
            'dancer': _serialize_dancer(dancer),
            'coord': [row, col],
            'facing': list(facing) if isinstance(facing, (list, tuple)) else facing
        }
    return {
        'name': getattr(floor, 'name', ''),
        'couples': int(getattr(floor, 'maxRow', 0) or 0),
        'tick': int(getattr(floor, 'AktBar', 0) or 0),
        'positions': positions
    }


def _api_error(message, code=404, error='not_found'):
    return jsonify({
        'status': 'error',
        'error': error,
        'message': message,
        'code': code
    }), code


def _resolve_json_path(filename, roots):
    if not filename.lower().endswith('.json'):
        filename = filename + '.json'

    basename = os.path.basename(filename)
    candidates = []
    for root in roots:
        candidates.append(os.path.join(os.getcwd(), root, filename))
        candidates.append(os.path.join(os.getcwd(), root, basename))

    for root in roots:
        root_dir = os.path.join(os.getcwd(), root)
        if not os.path.isdir(root_dir):
            continue
        for base, _, files in os.walk(root_dir):
            for found in files:
                if found.lower() == basename.lower():
                    candidates.append(os.path.join(base, found))

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    raise FileNotFoundError(filename)


def _resolve_dance_path(filename):
    return _resolve_json_path(filename, ['Dances'])


def getDance(Filename):
    from ComplexFigure import ComplexFigure  # Lazy Import, um zirkul?ren Import zu vermeiden

    myDance = ComplexFigure(_resolve_dance_path(Filename), [0,0])
    myDance.loadFigure()

    return myDance


def getFigure(Filename, Anchor = [0,0], Addons = []):
    from ComplexFigure import ComplexFigure  # Lazy Import, um zirkul?ren Import zu vermeiden

    figure_path = _resolve_json_path(Filename, ['Figures', 'Dances'])
    FigData = _load_json_file(figure_path)

    if 'FigureList' in FigData.keys():
        myFig = ComplexFigure(figure_path, Anchor)
        myFig.loadFigure()
    else:
        myFig = SimpleFigure(Filename, Anchor, Addons)

    return myFig


def printCrip(myCrips):
    if type(myCrips) != type([]):
        print(myCrips)
    else:
        if len(myCrips) == 0:
            pass
        elif type(myCrips[0]) != type([]):
            print(myCrips[0])
            if len(myCrips) > 1:
                printCrip(myCrips[1:])
        else:
            for myCrip in myCrips:
                printCrip(myCrip)


def showCrips(myFig, myDF):
    printCrip(myFig.getCrips(myDF))


load_Figuers()

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
    """Kleine Fallback-Funktion, die g?ngige JSON-Formate in eine flache Knotenliste umwandelt.

    Das reicht f?r die GUI, die im Moment nur eine flache Liste/Root ben?tigt.
    """
    nodes = []
    if isinstance(data, dict):
        if 'FigureList' in data and isinstance(data['FigureList'], list):
            for i, item in enumerate(data['FigureList']):
                name = item.get('Name') or item.get('name') or f"Figure {i+1}"
                nodes.append({'id': i+1, 'parent_id': None, 'name': name, 'type': item.get('type', 'unknown'), 'meta': item})
        elif 'Name' in data or 'name' in data:
            name = data.get('Name') or data.get('name')
            nodes.append({'id': 1, 'parent_id': None, 'name': name, 'type': data.get('type', 'unknown'), 'meta': data})
        else:
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


def _load_tree_source(fname):
    candidates = [
        fname,
        os.path.join(FIGURES_DIR, fname),
        os.path.join(DANCES_DIR, fname),
        os.path.join(os.path.dirname(__file__), fname)
    ]
    if not os.path.splitext(fname)[1]:
        candidates.append(fname + ".json")

    for root_dir in (FIGURES_DIR, DANCES_DIR):
        if os.path.isdir(root_dir):
            for fpath in iter_json_files(root_dir):
                base = os.path.basename(fpath).lower()
                if base == os.path.basename(fname).lower() or base == os.path.basename(fname + ".json").lower():
                    candidates.append(fpath)

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


@app.route('/get_nodes/<node_Name>')
def get_nodes(node_Name):
    if node_Name in Figure_DB:
        data = Figure_DB[node_Name]
        return jsonify(make_node(node_Name, data))
    else:
        node = {
            "id": "Dance (leer)",
            "parent_id": None,
            "name": "Dance (leer)",
            "meta": {}
        }
    return jsonify(node)


@app.route('/api/get_nodes/<node_Name>')
def api_get_nodes(node_Name):
    return get_nodes(node_Name)


@app.route("/")
def index():
    """
    Liefert die Hauptseite (templates/index.html).
    """
    return render_template("index.html")


@app.route("/tree")
def tree():
    fname = request.args.get("file") or "HLReelAD.json"
    path = _load_tree_source(fname)
    if path is None:
        nodes = [{
            "id": 1,
            "parent_id": None,
            "name": "Dance (leer)",
            "meta": {}
        }]
        return jsonify(nodes)

    data = _load_json_file(path)
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


@app.route('/api/tree')
def api_tree():
    return tree()


@app.route('/figures')
def figures():
    """Gibt normalisierte Figuren-Summaries zur?ck."""
    load_Figuers()
    result = [figure_summary(key, obj) for key, obj in Figure_DB.items() if isinstance(obj, dict)]
    result.sort(key=lambda x: str(x.get('Name', '')).lower())
    return jsonify(result)


@app.route('/api/figures')
def api_figures():
    return figures()


@app.route('/api/figures/<path:identifier>')
def api_figure_detail(identifier):
    figure_path = _figure_detail_path(identifier)
    if figure_path is None:
        return _api_error(f'Figure not found: {identifier}', 404, 'not_found')
    return jsonify(_load_json_file(figure_path))


@app.route('/dances')
def list_dances():
    """Gibt normalisierte Dance-Summaries f?r vollst?ndige Dances zur?ck."""
    try:
        if not os.path.isdir(DANCES_DIR):
            return jsonify({'error': 'Dances directory not found'}), 404
        files = []
        for fpath in iter_json_files(DANCES_DIR):
            rel = os.path.relpath(fpath, DANCES_DIR)
            if rel.startswith('subDances' + os.sep):
                continue
            data = _load_json_file(fpath)
            files.append(dance_summary(fpath, data))
        files.sort(key=lambda x: str(x.get('Name', '')).lower())
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dances')
def api_dances():
    return list_dances()


@app.route('/api/dances/<path:identifier>')
def api_dance_detail(identifier):
    dance_path = _dance_detail_path(identifier)
    if dance_path is None:
        return _api_error(f'Dance not found: {identifier}', 404, 'not_found')
    dance_data = _load_json_file(dance_path)
    return jsonify({
        'file': os.path.relpath(dance_path, DANCES_DIR),
        'dance': dance_data,
        'tree': build_dance_tree(dance_data, dance_data.get('Name') or os.path.splitext(os.path.basename(dance_path))[0])
    })


@app.route('/api/dances/<path:identifier>/tree')
def api_dance_tree(identifier):
    response = api_dance_detail(identifier)
    if isinstance(response, tuple):
        return response
    payload = response.get_json()
    return jsonify(payload.get('tree', {}))


@app.route('/api/dancefloor/init', methods=['POST'])
def api_dancefloor_init():
    body = request.get_json(silent=True) or {}
    couples = int(body.get('couples', 1))
    name = body.get('name') or 'init'
    from DanceFloor import DanceFloor
    floor = DanceFloor(name, couples)
    return jsonify(_serialize_floor(floor))


@app.route('/api/dancefloor/execute', methods=['POST'])
def api_dancefloor_execute():
    body = request.get_json(silent=True) or {}
    figure_name = body.get('figure')
    if not figure_name:
        return _api_error('Missing figure', 400, 'bad_request')

    couples = int(body.get('couples', 1))
    anchor = body.get('anchor') or [0, 0]
    addons = body.get('addons') or []
    floor_name = body.get('dance_name') or 'execute'

    from DanceFloor import DanceFloor
    floor = DanceFloor(floor_name, couples)
    figure = getFigure(figure_name, anchor, addons)

    try:
        new_floor = figure.DanceMove(floor)
        crips = figure.getCrips(floor)
    except Exception as exc:
        return jsonify({
            'status': 'error',
            'error': 'execution_failed',
            'message': str(exc)
        }), 500

    return jsonify({
        'status': 'ok',
        'floor': _serialize_floor(new_floor),
        'crips': crips
    })


if __name__ == "__main__":
    os.makedirs(FIGURES_DIR, exist_ok=True)
    load_Figuers()
    print("\nStarte DanceTreeApp (Flask). Lege JSON-Dateien in das Verzeichnis 'Figures'.")
    app.run(debug=True)
