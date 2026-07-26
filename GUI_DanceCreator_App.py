from flask import Flask, jsonify, request, send_file, render_template
import os
import json
from DanceFloor import DanceFloor
import Dance

app = Flask(__name__, static_folder='static', template_folder='templates')
ROOT = os.path.dirname(__file__)
FIGURES_DIR = os.path.join(ROOT, 'Figures')
DANCES_DIR = os.path.join(ROOT, 'Dances')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/dances')
def list_dances():
    files = []
    for f in os.listdir(DANCES_DIR):
        if f.endswith('.json'):
            data = json.load(open(os.path.join(DANCES_DIR, f), 'r', encoding='utf-8'))
            files.append({'Name': data.get('Name'), 'Version': data.get('Version'), 'file': f})
    return jsonify(files)


@app.route('/api/figures')
def list_figures():
    files = []
    for f in os.listdir(FIGURES_DIR):
        if f.endswith('.json'):
            data = json.load(open(os.path.join(FIGURES_DIR,f),'r',encoding='utf-8'))
            files.append({
                'Name': data.get('Name'),
                'Version': data.get('Version'),
                'Bars': data.get('Bars'),
                'Formation': data.get('Formation'),
                'Desc': data.get('Desc'),
                'file': f
            })
    return jsonify(files)


@app.route('/api/figures/<name>')
def get_figure(name):
    path = os.path.join(FIGURES_DIR, f'{name}.json')
    if os.path.exists(path):
        return jsonify(json.load(open(path,'r',encoding='utf-8')))
    return jsonify({'error':'not found'}), 404


@app.route('/api/dances/<name>')
def get_dance(name):
    path = os.path.join(DANCES_DIR, f'{name}.json')
    if os.path.exists(path):
        data = json.load(open(path,'r',encoding='utf-8'))
        # very small tree representation
        tree = {
            'id':'root',
            'text': data.get('Name'),
            'children': []
        }
        for i, entry in enumerate(data.get('FigureList', [])):
            anchor, fig = entry[0], entry[1]
            node = { 'id': f'node-{i}', 'text': str(fig), 'children': [], 'data': {'original': entry}}
            tree['children'].append(node)
        return jsonify({'dance': data, 'tree': tree})
    return jsonify({'error':'not found'}), 404


@app.route('/api/dances/<name>/tree', methods=['PUT'])
def update_dance_tree(name):
        path = os.path.join(DANCES_DIR, f'{name}.json')
        if not os.path.exists(path):
            return jsonify({'error':'not found'}), 404
        body = request.get_json() or {}
        tree = body.get('tree')
        if not tree:
            return jsonify({'error':'no tree provided'}), 400

        def extract_figurelist(node):
            # node is expected to have 'children'
            res = []
            for child in node.get('children', []):
                data = child.get('data', {})
                if 'original' in data:
                    res.append(data['original'])
                elif child.get('children'):
                    # build sequential group from children
                    sub = []
                    for gc in child.get('children'):
                        gd = gc.get('data', {})
                        if 'original' in gd:
                            sub.append(gd['original'])
                    res.append([[0,0], ['s', sub]])
                else:
                    # skip unknown
                    continue
            return res

        new_figurelist = extract_figurelist(tree)
        # load json file and update
        dance = json.load(open(path,'r',encoding='utf-8'))
        dance['FigureList'] = new_figurelist
        with open(path,'w',encoding='utf-8') as f:
            json.dump(dance, f, indent=2)
        return jsonify({'status':'ok', 'updated': len(new_figurelist)})


@app.route('/api/dancefloor/init', methods=['POST'])
def api_init():
        body = request.get_json() or {}
        couples = int(body.get('couples', 1))
        floor = DanceFloor('init', couples)
        return jsonify(floor.to_dict())


@app.route('/api/dancefloor/execute', methods=['POST'])
def api_execute():
        body = request.get_json() or {}
        figure = body.get('figure')
        anchor = body.get('anchor', [0,0])
        try:
            floor = DanceFloor(body.get('dance_name','exec'), int(body.get('couples',1)))
            fobj = Dance.getFigure(figure, anchor)
            new = fobj.DanceMove(floor)
            crips = fobj.getCrips(floor)
            return jsonify({'floor': new.to_dict(), 'crips': crips})
        except Exception as e:
            # handle combine conflict specially
            try:
                from DanceFloor import CombineConflictError
                if isinstance(e, CombineConflictError):
                    return jsonify({'error': str(e), 'conflicts': e.conflicts}), 409
            except Exception:
                pass
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
