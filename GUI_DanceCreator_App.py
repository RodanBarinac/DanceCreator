from flask import Flask, jsonify, request, send_file
import os
import json
from DanceFloor import DanceFloor
import Dance

app = Flask(__name__)
ROOT = os.path.dirname(__file__)
FIGURES_DIR = os.path.join(ROOT, 'Figures')
DANCES_DIR = os.path.join(ROOT, 'Dances')


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
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
