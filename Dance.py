import json
import os
from SimpleFigure import SimpleFigure
from ComplexFigure import ComplexFigure

ROOT = os.path.dirname(__file__)
FIGURES_DIR = os.path.join(ROOT, 'Figures')
DANCES_DIR = os.path.join(ROOT, 'Dances')


def load_json_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def getFigure(name, anchor=[0,0], addons=None):
    # try Figures/<name>.json
    candidates = [os.path.join(FIGURES_DIR, f'{name}.json'), os.path.join(FIGURES_DIR, name)]
    for p in candidates:
        if os.path.exists(p):
            data = load_json_file(p)
            if data.get('Version', 0) >= 3 and 'FigureList' in data:
                return ComplexFigure(data)
            else:
                return SimpleFigure(data)
    # fallback: if name not found, create a trivial SimpleFigure
    return SimpleFigure({'Name': name, 'Version':2, 'Bars':4, 'StartPos':[], 'EndPos':[], 'CriptDesc':[]})


def getDance(name):
    path = os.path.join(DANCES_DIR, f'{name}.json')
    if os.path.exists(path):
        data = load_json_file(path)
        if data.get('Version',0) >= 3:
            return ComplexFigure(data)
        else:
            return SimpleFigure(data)
    raise FileNotFoundError(f'Dance not found: {name}')


def showCrips(figure_or_dance, floor):
    lines = figure_or_dance.getCrips(floor)
    for l in lines:
        print(l)
    return lines
