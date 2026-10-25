from ..figures.SimpleFigure import SimpleFigure
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
    return _resolve_json_path(filename, ['data/Dances'])


def getDance(Filename):
    from ..figures.ComplexFigure import ComplexFigure  # Lazy Import, um zirkul?ren Import zu vermeiden

    myDance = ComplexFigure(_resolve_dance_path(Filename), [0,0])
    myDance.loadFigure()

    return myDance

def getFigure(Filename, Anchor = [0,0], Addons = []):
    from ..figures.ComplexFigure import ComplexFigure  # Lazy Import, um zirkul?ren Import zu vermeiden

    figure_path = _resolve_json_path(Filename, ['data/Figures', 'data/Dances'])
    with open(figure_path, 'r') as f:
        FigData = json.load(f)

    if 'FigureList' in FigData.keys():
        myFig = ComplexFigure(figure_path, Anchor)
        myFig.loadFigure()
    else:
        myFig = SimpleFigure(Filename, Anchor, Addons)

    return myFig

def _simple_crip_lines(figure, incoming_floor, bar_start):
    descriptions = list(figure._CriptDesc)
    for addon in figure._Addons:
        descriptions = addon.getCrips(descriptions)
    if not descriptions:
        return []
    floor = incoming_floor.copy()
    floor._DanceFloorNames = dict(incoming_floor._DanceFloorNames)
    floor.AktBar = bar_start
    rendered = figure.getCrips(floor)
    active_indices = [index for index, text in enumerate(descriptions) if str(text)]
    start = bar_start
    bar_range = [start, start + figure.Bars - 1]
    lines = []
    for index, rendered_line in zip(active_indices, rendered):
        position = figure.posWithAnchor(figure.StartPos[index])
        dancer = incoming_floor.DancerbyPos(position).name
        _, separator, text = rendered_line.partition(': ')
        if not separator:
            text = rendered_line
        if text.startswith(f"{dancer} "):
            text = text[len(dancer) + 1:]
        lines.append({
            "figureRef": str(getattr(figure, "name", figure.Name)),
            "dancer": str(dancer),
            "barRange": list(bar_range),
            "text": text,
        })
    return lines


def getCripsData(myFig, myDF, *, bar_start=None):
    """Return structured crips without printing, preserving getCrips line text."""
    from ..figures.ComplexFigure import ComplexFigure
    from ..models import Figures as Fig
    from ..domain.dance_model import FigureOccurrence
    from ..models import DanceFloor as DF

    if not isinstance(myDF, DF.DanceFloor):
        raise ValueError("Sorry, no Dance Floor")
    first_bar = myDF.AktBar if bar_start is None else bar_start
    if isinstance(myFig, FigureOccurrence):
        myFig = getFigure(myFig.figure_ref, list(myFig.anchor), list(myFig.addons))

    def collect(node, current_floor, node_bar):
        if isinstance(node, ComplexFigure):
            return collect(node._FigureObjs, current_floor, node_bar)
        if isinstance(node, Fig.Figure):
            return _simple_crip_lines(node, current_floor, node_bar)
        if not isinstance(node, (list, tuple)) or not node:
            raise ValueError("Sorry, no valid figure found!")
        if node[0] in ("s", "p") and len(node) == 2:
            group_type, children = node
        else:
            group_type, children = "s", node
        if group_type == "p":
            lines = []
            for child in children:
                lines.extend(collect(child, current_floor, node_bar))
            return lines
        lines = []
        cursor = node_bar
        sequential_floor = current_floor
        for child in children:
            lines.extend(collect(child, sequential_floor, cursor))
            duration = child.Bars if isinstance(child, Fig.Figure) else _sub_bars(child)
            cursor += duration
            sequential_floor = _advance(child, sequential_floor)
        return lines

    return collect(myFig, myDF, first_bar)


def _advance(node, floor):
    from ..figures.ComplexFigure import ComplexFigure
    from ..models import Figures as Fig
    from ..models import DanceFloor as DF

    if isinstance(node, ComplexFigure):
        return node.DanceMove(floor)
    if isinstance(node, Fig.Figure):
        return node.DanceMove(floor)
    if not isinstance(node, (list, tuple)) or not node:
        return floor
    if node[0] in ("s", "p") and len(node) == 2:
        kind, children = node
    else:
        kind, children = "s", node
    if kind == "s":
        current = floor
        for child in children:
            current = _advance(child, current)
        return current
    return DF.combineDanceFloor([_advance(child, floor) for child in children])


def _sub_bars(node):
    from ..figures.ComplexFigure import ComplexFigure
    from ..models import Figures as Fig

    if isinstance(node, ComplexFigure):
        return node.Bars
    if isinstance(node, Fig.Figure):
        return node.Bars
    if isinstance(node, (list, tuple)) and node:
        if node[0] in ("s", "p") and len(node) == 2:
            kind, children = node
        else:
            kind, children = "s", node
        bars = [_sub_bars(child) for child in children]
        if kind == "p" and bars and any(value != bars[0] for value in bars[1:]):
            raise ValueError("Sorry, not all the Bars are allocated")
        return sum(bars) if kind == "s" else (bars[0] if bars else 0)
    return 0


def showCrips(myFig, myDF):
    """Compatibility entry point returning crips data instead of printing it."""
    return getCripsData(myFig, myDF)
