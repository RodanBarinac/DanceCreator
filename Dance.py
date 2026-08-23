from SimpleFigure import SimpleFigure
import json
import os

def _resolve_json_path(filename, roots):
    if not filename.lower().endswith('.json'):
        filename = filename + '.json'

    candidates = []
    basename = os.path.basename(filename)
    for root in roots:
        candidates.append(os.path.join(os.getcwd(), root, filename))
        candidates.append(os.path.join(os.getcwd(), root, basename))

    for root in roots:
        root_dir = os.path.join(os.getcwd(), root)
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
    with open(figure_path, 'r') as f:
        FigData = json.load(f)

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
