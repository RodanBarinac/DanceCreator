"""
DanceTreeApp - ein kleines Flask-Backend f?r die HTML5-GUI.

Beschreibung:
 - Liefert die HTML-Seite (templates/index.html)
 - Stellt statische Dateien unter /static bereit (style_old.css, app.js)
 - Bietet einen einfachen API-Endpunkt /tree, der eine JSON-Datei (aus ./data/Figures)
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
    ??? data/Figures/    <-- JSON-Dateien hier ablegen (z. B. HLReelAD.json)

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
import re
import shutil
import uuid
import sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from engine.figures.SimpleFigure import SimpleFigure
from src.engine.converters.TreeConverter import TreeConverter, TreeConversionError
from src.engine.persistence.FileManager import FileManager, FileManagerError
from engine.validators.ApiRequestValidator import ApiRequestValidator, ApiValidationError
from engine.validators.ApiResponseValidator import get_validator

Figure_DB = {}
Figure_File_DB = {}
app = Flask(__name__, template_folder="templates", static_folder="static")

# Ordner, in dem der Benutzer seine JSON-Files ablegen soll
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "data", "Figures")
DANCES_DIR = os.path.join(os.path.dirname(__file__), "data", "Dances")


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
    """Create a figure summary with all required fields for API response."""
    summary = {
        'file': Figure_File_DB.get(key, key + '.json'),
        'key': key,
        'Name': data.get('Name') or data.get('name') or key,
        'Version': data.get('Version', 1)  # Required field with default
    }
    
    # Optional fields
    if 'Desc' in data:
        summary['Desc'] = data['Desc']
    if 'Bars' in data:
        summary['Bars'] = data['Bars']
    if 'Formation' in data:
        summary['Formation'] = data['Formation']
    if 'StartPos' in data:
        summary['StartPos'] = data['StartPos']
    if 'EndPos' in data:
        summary['EndPos'] = data['EndPos']
    if 'HasFacing' in data:
        summary['HasFacing'] = data['HasFacing']
    
    # Transform Addons from dict to array of addon names
    if 'Addons' in data:
        addons = data['Addons']
        if isinstance(addons, dict):
            summary['Addons'] = list(addons.keys())
        elif isinstance(addons, list):
            summary['Addons'] = addons
        else:
            summary['Addons'] = []
    
    return summary


def dance_summary(path, data):
    """Create a dance summary with all required fields and calculated metadata."""
    rel_path = os.path.relpath(path, DANCES_DIR)
    shape = data.get('shape') or data.get('Shape', '1/1')
    
    summary = {
        'file': rel_path,
        'Name': data.get('Name') or os.path.splitext(os.path.basename(path))[0],
        'shape': shape,
        'Version': data.get('Version', 1)  # Required with default
    }
    
    # Optional description
    if 'Desc' in data:
        summary['Desc'] = data['Desc']
    
    # Extract couples from shape (e.g., "3/32" -> 3 couples)
    try:
        couples_str = shape.split('/')[0]
        summary['Couples'] = int(couples_str) if couples_str.isdigit() else couples_str
    except:
        summary['Couples'] = 1
    
    # Calculate EstimatedBars from FigureList
    estimated_bars = _calculate_dance_bars(data)
    if estimated_bars > 0:
        summary['EstimatedBars'] = estimated_bars
    
    # Optional formation
    if 'Formation' in data:
        summary['Formation'] = data['Formation']
    
    return summary


def _calculate_dance_bars(dance_data):
    """Calculate estimated bars for a dance from its FigureList."""
    # This is a simplified calculation - actual implementation would need
    # to load each figure and sum bars, handling series/parallel groups correctly
    figure_list = dance_data.get('FigureList', [])
    if not figure_list:
        return 0
    
    # For now, return bar count from shape or a simple estimate
    shape = dance_data.get('shape') or dance_data.get('Shape', '')
    try:
        parts = shape.split('/')
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])  # e.g., "3/32" -> 32 bars
    except:
        pass
    
    return 0


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
        if root == 'Figures':
            root_dir = FIGURES_DIR
        elif root == 'Dances':
            root_dir = DANCES_DIR
        else:
            continue
        root_dir = os.path.abspath(root_dir)
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


def _dance_write_summary(data):
    summary = {
        "Name": data.get("Name"),
        "Version": data.get("Version"),
    }

    shape = data.get("shape")
    if shape is None and "Shape" in data:
        shape = data.get("Shape")
    if shape is not None:
        summary["shape"] = shape

    return summary


def _sanitize_dance_filename(name):
    safe_name = str(name).strip().replace('/', ' ').replace('\\', ' ')
    safe_name = safe_name.replace('..', ' ')
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', ' ', safe_name)
    safe_name = re.sub(r'\s+', ' ', safe_name).strip().strip('.')
    if not safe_name:
        safe_name = 'dance'
    if not safe_name.lower().endswith('.json'):
        safe_name = safe_name + '.json'
    return safe_name


def _is_group_entry(entry):
    return isinstance(entry, list) and len(entry) == 2 and entry[0] in ('s', 'p') and isinstance(entry[1], list)


def _is_figure_call(entry):
    return (
        isinstance(entry, list)
        and len(entry) == 2
        and isinstance(entry[0], list)
        and len(entry[0]) == 2
        and isinstance(entry[1], list)
        and len(entry[1]) >= 1
    )


def _build_dance_tree(entry, node_id, seen=None, depth=0, max_depth=50):
    """Build dance tree with recursion protection."""
    seen = seen or set()
    
    # Prevent infinite recursion
    if depth > max_depth:
        return {
            'id': str(node_id),
            'text': '[Max depth reached]',
            'children': [],
            'type': 'figure',
            'data': {'error': 'max_depth_exceeded'}
        }

    if _is_group_entry(entry):
        mode = entry[0]
        children = []
        for index, child in enumerate(entry[1]):
            children.append(_build_dance_tree(child, f"{node_id}-{index}", seen, depth + 1, max_depth))
        return {
            'id': str(node_id),
            'text': 'Sequential Group' if mode == 's' else 'Parallel Group',
            'children': children,
            'type': 'group',
            'data': {
                'groupType': mode,
                'groupIndex': depth,
                'original': entry
            }
        }

    if _is_figure_call(entry):
        anchor = entry[0]
        fig_spec = entry[1]
        figure_name = fig_spec[0] if len(fig_spec) > 0 else 'Figure'
        addons = fig_spec[1:] if len(fig_spec) > 1 else []
        node = {
            'id': str(node_id),
            'text': figure_name,
            'children': [],
            'type': 'figure',
            'data': {
                'figureName': figure_name,
                'anchor': anchor,
                'addons': addons,
                'original': entry
            }
        }
        figure_path = _figure_detail_path(figure_name)
        if figure_path and figure_path not in seen:
            try:
                figure_data = _load_json_file(figure_path)
            except Exception:
                figure_data = None
            if isinstance(figure_data, dict) and isinstance(figure_data.get('FigureList'), list):
                nested_seen = set(seen)
                nested_seen.add(figure_path)
                child_entries = figure_data.get('FigureList')
                child_nodes = []
                if _is_group_entry(child_entries):
                    child_nodes.append(_build_dance_tree(child_entries, f"{node_id}-0", nested_seen, depth + 1, max_depth))
                else:
                    for index, child in enumerate(child_entries):
                        child_nodes.append(_build_dance_tree(child, f"{node_id}-{index}", nested_seen, depth + 1, max_depth))
                if child_nodes:
                    node['type'] = 'group'
                    node['text'] = figure_name
                    node['children'] = child_nodes
                    node['data']['expanded'] = True
        return node

    if isinstance(entry, list):
        children = []
        for index, child in enumerate(entry):
            children.append(_build_dance_tree(child, f"{node_id}-{index}", seen, depth + 1, max_depth))
        return {
            'id': str(node_id),
            'text': 'Group',
            'children': children,
            'type': 'group',
            'data': {'original': entry}
        }

    return {
        'id': str(node_id),
        'text': str(entry),
        'children': [],
        'type': 'figure',
        'data': {'figureName': str(entry), 'original': entry}
    }


def build_dance_tree(data, name='Dance'):
    children = []
    figure_list = data.get('FigureList') if isinstance(data, dict) else []
    if _is_group_entry(figure_list):
        children.append(_build_dance_tree(figure_list, 'node-0', set()))
    elif isinstance(figure_list, list):
        for index, entry in enumerate(figure_list):
            children.append(_build_dance_tree(entry, f"node-{index}", set()))
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
        row = pos[0]
        col = pos[1]
        key = _dance_position_key((row, col))
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


def _format_floor_coordinate(value):
    try:
        integer = int(value)
        if value == integer:
            return str(integer)
    except (TypeError, ValueError, OverflowError):
        pass
    return str(value)


def _dance_position_key(position):
    row, col = position[0], position[1]
    row_text = _format_floor_coordinate(row)
    col_text = _format_floor_coordinate(col)
    if col_text == '-1':
        return f'{row_text}m'
    if col_text == '1':
        return f'{row_text}w'
    return f'{row_text}:{col_text}'


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
        if root == 'Figures':
            root_dir = FIGURES_DIR
        elif root == 'Dances':
            root_dir = DANCES_DIR
        else:
            continue
        candidates.extend((os.path.join(root_dir, filename), os.path.join(root_dir, basename)))

    for root in roots:
        if root == 'Figures':
            root_dir = FIGURES_DIR
        elif root == 'Dances':
            root_dir = DANCES_DIR
        else:
            continue
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
    from engine.figures.ComplexFigure import ComplexFigure

    myDance = ComplexFigure(_resolve_dance_path(Filename), [0,0])
    myDance.loadFigure()

    return myDance


def getFigure(Filename, Anchor = [0,0], Addons = []):
    from engine.figures.ComplexFigure import ComplexFigure

    figure_path = _resolve_json_path(Filename, ['Figures', 'Dances'])
    FigData = _load_json_file(figure_path)

    if 'FigureList' in FigData.keys():
        myFig = ComplexFigure(figure_path, Anchor)
        myFig.loadFigure()
    else:
        myFig = SimpleFigure(Filename, Anchor, Addons)

    return myFig


def showCrips(myFig, myDF):
    """Return structured crips data without printing to the console."""
    from engine.models.Dance import getCripsData
    return getCripsData(myFig, myDF)


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


def api_tree():
    return tree()


@app.route('/figures')
def figures():
    """Gibt normalisierte Figuren-Summaries zur?ck."""
    load_Figuers()
    result = [figure_summary(key, obj) for key, obj in Figure_DB.items() if isinstance(obj, dict)]
    result.sort(key=lambda x: str(x.get('Name', '')).lower())
    return jsonify(result)


def api_figures():
    """
    GET /api/figures - List figures with filtering, pagination, and sorting.
    
    Query Parameters:
        - version: Filter by schema version
        - formation: Filter by formation type
        - minBars, maxBars: Filter by bar count
        - search: Search by name or description
        - limit, offset: Pagination
        - sort, order: Sorting
    """
    try:
        # Validate query parameters
        validated_params = ApiRequestValidator.validate_figure_list_params(request.args.to_dict())
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400
    
    # Load all figures
    load_Figuers()
    all_figures = [
        figure_summary(key, obj) 
        for key, obj in Figure_DB.items() 
        if isinstance(obj, dict)
    ]
    
    # Apply filters
    filtered = all_figures
    filters_applied = {}
    
    if 'version' in validated_params:
        version = validated_params['version']
        filtered = [f for f in filtered if f.get('Version') == version]
        filters_applied['version'] = version
    
    if 'formation' in validated_params:
        formation = validated_params['formation']
        filtered = [f for f in filtered if f.get('Formation', '').lower() == formation]
        filters_applied['formation'] = formation
    
    if 'minBars' in validated_params:
        min_bars = validated_params['minBars']
        filtered = [f for f in filtered if _get_bar_count(f.get('Bars')) >= min_bars]
        filters_applied['minBars'] = min_bars
    
    if 'maxBars' in validated_params:
        max_bars = validated_params['maxBars']
        filtered = [f for f in filtered if _get_bar_count(f.get('Bars')) <= max_bars]
        filters_applied['maxBars'] = max_bars
    
    if 'search' in validated_params:
        search_term = validated_params['search'].lower()
        filtered = [
            f for f in filtered
            if search_term in f.get('Name', '').lower() 
            or search_term in f.get('Desc', '').lower()
        ]
        filters_applied['search'] = validated_params['search']
    
    # Total count after filtering
    total = len(filtered)
    
    # Sort
    sort_field = validated_params.get('sort', 'name')
    reverse = validated_params.get('order', 'ASC') == 'DESC'
    
    if sort_field == 'name':
        filtered.sort(key=lambda x: x.get('Name', '').lower(), reverse=reverse)
    elif sort_field == 'bars':
        filtered.sort(key=lambda x: _get_bar_count(x.get('Bars')), reverse=reverse)
    elif sort_field == 'version':
        filtered.sort(key=lambda x: x.get('Version', 0), reverse=reverse)
    
    # Pagination
    offset = validated_params['offset']
    limit = validated_params['limit']
    paginated = filtered[offset:offset + limit]
    
    # Build response
    response = {
        "status": "ok",
        "version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(paginated),
        "total": total,
        "offset": offset,
        "limit": limit,
        "filters_applied": filters_applied,
        "figures": paginated
    }
    
    # Validate response against schema (in development mode)
    try:
        validator = get_validator()
        validator.validate_figure_list_response(response)
    except Exception as validation_error:
        # Log validation error but don't fail the request in production
        print(f"Warning: Response validation failed: {validation_error}")
    
    return jsonify(response)


def _get_bar_count(bars):
    """Extract numeric bar count from Bars field (handles int or array)."""
    if isinstance(bars, int):
        return bars
    if isinstance(bars, list) and len(bars) > 0:
        return bars[0]  # Use first value if array
    return 0


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



def api_dances():
    """
    GET /api/dances - List dances with filtering, pagination, and sorting.
    
    Query Parameters:
        - version: Filter by schema version
        - minCouples, maxCouples: Filter by couple count
        - search: Search by name or description
        - limit, offset: Pagination
        - sort, order: Sorting
    """
    try:
        # Validate query parameters
        validated_params = ApiRequestValidator.validate_dance_list_params(request.args.to_dict())
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400
    
    # Load all dances
    try:
        if not os.path.isdir(DANCES_DIR):
            return jsonify({
                "status": "error",
                "error": "dances_directory_not_found",
                "message": "Dances directory not found"
            }), 404
        
        all_dances = []
        for fpath in iter_json_files(DANCES_DIR):
            rel = os.path.relpath(fpath, DANCES_DIR)
            # Skip subdances directory
            if rel.startswith('subDances' + os.sep):
                continue
            try:
                data = _load_json_file(fpath)
                all_dances.append(dance_summary(fpath, data))
            except Exception:
                continue  # Skip malformed files
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": "internal_error",
            "message": str(e)
        }), 500
    
    # Apply filters
    filtered = all_dances
    filters_applied = {}
    
    if 'version' in validated_params:
        version = validated_params['version']
        filtered = [d for d in filtered if d.get('Version') == version]
        filters_applied['version'] = version
    
    if 'minCouples' in validated_params:
        min_couples = validated_params['minCouples']
        filtered = [d for d in filtered if _get_couple_count(d.get('Couples')) >= min_couples]
        filters_applied['minCouples'] = min_couples
    
    if 'maxCouples' in validated_params:
        max_couples = validated_params['maxCouples']
        filtered = [d for d in filtered if _get_couple_count(d.get('Couples')) <= max_couples]
        filters_applied['maxCouples'] = max_couples
    
    if 'search' in validated_params:
        search_term = validated_params['search'].lower()
        filtered = [
            d for d in filtered
            if search_term in d.get('Name', '').lower() 
            or search_term in d.get('Desc', '').lower()
        ]
        filters_applied['search'] = validated_params['search']
    
    # Total count after filtering
    total = len(filtered)
    
    # Sort
    sort_field = validated_params.get('sort', 'name')
    reverse = validated_params.get('order', 'ASC') == 'DESC'
    
    if sort_field == 'name':
        filtered.sort(key=lambda x: x.get('Name', '').lower(), reverse=reverse)
    elif sort_field == 'couples':
        filtered.sort(key=lambda x: _get_couple_count(x.get('Couples')), reverse=reverse)
    elif sort_field == 'version':
        filtered.sort(key=lambda x: x.get('Version', 0), reverse=reverse)
    elif sort_field == 'bars':
        filtered.sort(key=lambda x: x.get('EstimatedBars', 0), reverse=reverse)
    
    # Pagination
    offset = validated_params['offset']
    limit = validated_params['limit']
    paginated = filtered[offset:offset + limit]
    
    # Build response
    response = {
        "status": "ok",
        "version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(paginated),
        "total": total,
        "offset": offset,
        "limit": limit,
        "filters_applied": filters_applied,
        "dances": paginated
    }
    
    # Validate response against schema (in development mode)
    try:
        validator = get_validator()
        validator.validate(response, 'api_dances_list.schema.json')
    except Exception as validation_error:
        # Log validation error but don't fail the request in production
        print(f"Warning: Response validation failed: {validation_error}")
    
    return jsonify(response)


def api_dance_create():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": "body",
            "message": "Request body must be a JSON object"
        }), 400

    try:
        validated_data = ApiRequestValidator.validate_dance_create_request(body)
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400

    filename = _sanitize_dance_filename(validated_data.get("Name", "dance"))
    dance_path = os.path.join(DANCES_DIR, filename)
    if os.path.exists(dance_path):
        return jsonify({
            "status": "error",
            "error": "conflict",
            "message": "A dance with this name already exists"
        }), 409

    try:
        FileManager.write_json_safe(dance_path, validated_data, create_backup=False)
    except FileManagerError as e:
        return jsonify({
            "status": "error",
            "error": "write_failed",
            "message": str(e)
        }), 500

    response = {
        "status": "ok",
        "version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Dance created",
        "file": os.path.relpath(dance_path, DANCES_DIR),
        "dance": _dance_write_summary(validated_data)
    }

    return jsonify(response), 201


def _get_couple_count(couples):
    """Extract numeric couple count from Couples field (handles int or string)."""
    if isinstance(couples, int):
        return couples
    if isinstance(couples, str) and couples.isdigit():
        return int(couples)
    return 1  # Default


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


def api_dance_update(identifier):
    try:
        identifier = ApiRequestValidator.validate_dance_tree_identifier(identifier)
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400

    dance_path = _dance_detail_path(identifier)
    if dance_path is None:
        return jsonify({
            "status": "error",
            "error": "not_found",
            "message": f"Dance not found: {identifier}"
        }), 404

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": "body",
            "message": "Request body must be a JSON object"
        }), 400

    try:
        validated_data = ApiRequestValidator.validate_dance_update_request(body)
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400

    expected_hash = body.get("_expected_hash")
    if "_expected_hash" in body and FileManager.detect_conflict(dance_path, expected_hash):
        return jsonify({
            "status": "error",
            "error": "conflict",
            "message": "File was modified since last read"
        }), 409

    write_data = dict(validated_data)
    write_data.pop("_expected_hash", None)

    try:
        FileManager.write_json_safe(dance_path, write_data, create_backup=True)
    except FileManagerError as e:
        return jsonify({
            "status": "error",
            "error": "write_failed",
            "message": str(e)
        }), 500

    response = {
        "status": "ok",
        "version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Dance updated",
        "file": os.path.relpath(dance_path, DANCES_DIR),
        "dance": _dance_write_summary(write_data)
    }

    return jsonify(response)


def api_dance_delete(identifier):
    try:
        identifier = ApiRequestValidator.validate_dance_tree_identifier(identifier)
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400

    dance_path = _dance_detail_path(identifier)
    if dance_path is None:
        return jsonify({
            "status": "error",
            "error": "not_found",
            "message": f"Dance not found: {identifier}"
        }), 404

    try:
        FileManager.backup_file(dance_path)
        deleted_dir = os.path.join(DANCES_DIR, ".deleted")
        os.makedirs(deleted_dir, exist_ok=True)

        original_name = os.path.basename(dance_path)
        deleted_path = os.path.join(deleted_dir, original_name)
        if os.path.exists(deleted_path):
            stem, ext = os.path.splitext(original_name)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            deleted_path = os.path.join(deleted_dir, f"{stem}-{timestamp}{ext}")

        shutil.move(dance_path, deleted_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": "delete_failed",
            "message": str(e)
        }), 500

    response = {
        "status": "ok",
        "version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Dance deleted",
        "file": os.path.relpath(dance_path, DANCES_DIR)
    }

    return jsonify(response)


def api_dance_tree(identifier):
    """
    GET /api/dances/<identifier>/tree - Get dance tree structure.
    
    Returns jsTree-compatible tree with metadata envelope.
    """
    try:
        # Validate identifier
        identifier = ApiRequestValidator.validate_dance_tree_identifier(identifier)
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400
    
    # Find dance file
    dance_path = _dance_detail_path(identifier)
    if dance_path is None:
        return jsonify({
            "status": "error",
            "error": "not_found",
            "message": f"Dance not found: {identifier}"
        }), 404
    
    # Load dance data
    try:
        dance_data = _load_json_file(dance_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": "load_error",
            "message": f"Failed to load dance: {str(e)}"
        }), 500
    
    # Build tree
    dance_name = dance_data.get('Name') or os.path.splitext(os.path.basename(dance_path))[0]
    tree = build_dance_tree(dance_data, dance_name)
    
    # Build response with metadata envelope
    response = {
        "status": "ok",
        "version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "format": "jstree",
        "dance": {
            "file": os.path.relpath(dance_path, DANCES_DIR),
            "Name": dance_name,
            "shape": dance_data.get('shape') or dance_data.get('Shape', '1/1'),
            "Version": dance_data.get('Version', 1)
        },
        "tree": tree
    }
    
    # Add optional dance fields
    if 'Desc' in dance_data:
        response['dance']['Desc'] = dance_data['Desc']
    
    # Validate response against schema
    try:
        validator = get_validator()
        validator.validate_dance_tree_response(response)
    except Exception as validation_error:
        # Log validation error but don't fail the request in production
        print(f"Warning: Dance tree response validation failed: {validation_error}")
    
    return jsonify(response)


def api_dance_tree_update(identifier):
    try:
        identifier = ApiRequestValidator.validate_dance_tree_identifier(identifier)
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400

    dance_path = _dance_detail_path(identifier)
    if dance_path is None:
        return jsonify({
            "status": "error",
            "error": "not_found",
            "message": f"Dance not found: {identifier}"
        }), 404

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": "body",
            "message": "Request body must be a JSON object"
        }), 400

    try:
        validated_data = ApiRequestValidator.validate_tree_update_request(body)
    except ApiValidationError as e:
        return jsonify({
            "status": "error",
            "error": "validation_error",
            "field": e.field,
            "message": e.message
        }), 400

    try:
        dance_data = _load_json_file(dance_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": "load_error",
            "message": f"Failed to load dance: {str(e)}"
        }), 500

    try:
        converted_figure_list = TreeConverter.jstree_to_figure_list(validated_data["tree"])
    except TreeConversionError as e:
        return jsonify({
            "status": "error",
            "error": "conversion_error",
            "message": str(e),
            "node_id": getattr(e, "node_id", None)
        }), 400

    updated_dance = dict(dance_data)
    updated_dance["FigureList"] = converted_figure_list

    try:
        FileManager.write_json_safe(dance_path, updated_dance, create_backup=True)
    except FileManagerError as e:
        return jsonify({
            "status": "error",
            "error": "write_failed",
            "message": str(e)
        }), 500

    response = {
        "status": "ok",
        "version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Dance tree updated",
        "file": os.path.relpath(dance_path, DANCES_DIR)
    }

    return jsonify(response)


@app.route('/api/dancefloor/init', methods=['POST'])
def api_dancefloor_init():
    """Initialize dancefloor with given couples."""
    body = request.get_json(silent=True) or {}
    couples = int(body.get('couples', 1))
    name = body.get('name') or 'init'
    from engine.models.DanceFloor import DanceFloor
    floor = DanceFloor(name, couples)
    serialized = _serialize_floor(floor)
    
    # Validate response
    try:
        validator = get_validator()
        validator.validate_dancefloor_response(serialized)
    except Exception as validation_error:
        print(f"Warning: Dancefloor init response validation failed: {validation_error}")
    
    return jsonify(serialized)


@app.route('/api/dancefloor/execute', methods=['POST'])
def api_dancefloor_execute():
    """Execute a figure on the dancefloor."""
    body = request.get_json(silent=True) or {}
    figure_name = body.get('figure')
    if not figure_name:
        return _api_error('Missing figure', 400, 'bad_request')

    couples = int(body.get('couples', 1))
    anchor = body.get('anchor') or [0, 0]
    addons = body.get('addons') or []
    floor_name = body.get('dance_name') or 'execute'

    from engine.models.DanceFloor import DanceFloor
    floor = DanceFloor(floor_name, couples)
    figure = getFigure(figure_name, anchor, addons)

    try:
        new_floor = figure.DanceMove(floor)
        crips = showCrips(figure, floor)
    except Exception as exc:
        return jsonify({
            'status': 'error',
            'error': 'execution_failed',
            'message': str(exc)
        }), 500

    serialized_floor = _serialize_floor(new_floor)
    
    # Validate floor response
    try:
        validator = get_validator()
        validator.validate_dancefloor_response(serialized_floor)
    except Exception as validation_error:
        print(f"Warning: Dancefloor execute response validation failed: {validation_error}")
    
    return jsonify({
        'status': 'ok',
        'floor': serialized_floor,
        'crips': crips
    })


@app.route('/dancefloor_mockup.html')
def dancefloor_mockup():
    """Serve the dancefloor mockup page with H1DR demonstration."""
    return render_template('dancefloor_mockup.html')


@app.route('/dancefloor_test.html')
def dancefloor_test():
    """Serve the dancefloor test page."""
    return render_template('dancefloor_test.html')


@app.route('/svg_test.html')
def svg_test():
    """Serve the SVG test page."""
    return render_template('svg_test.html')


@app.route('/schema/<path:filename>')
def serve_schema(filename):
    """Serve schema files from the schema directory."""
    from flask import send_from_directory
    schema_dir = os.path.join(os.path.dirname(__file__), 'schema')
    return send_from_directory(schema_dir, filename, mimetype='application/json')


# Replace legacy dance/figure/jsTree API rules with canonical contracts.
from src.api.canonical import register_canonical_api

register_canonical_api(app, sys.modules[__name__])


if __name__ == "__main__":
    os.makedirs(FIGURES_DIR, exist_ok=True)
    load_Figuers()
    print("\nStarte DanceTreeApp (Flask). Lege JSON-Dateien in das Verzeichnis 'data/Figures'.")
    app.run(debug=True)
