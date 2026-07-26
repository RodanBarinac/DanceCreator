import os, json
import Dance
import DanceFloor as DF
from DanceFloor import CombineConflictError
from Dancer import Dancer

FIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'Figures')
FIG_DIR = os.path.abspath(FIG_DIR)


def write_fig(name, start, end):
    data = {
        "Version": 2,
        "Name": name,
        "Desc": "test",
        "Bars": 2,
        "StartPos": [start],
        "EndPos": [end],
        "CriptDesc": ["Test"]
    }
    path = os.path.join(FIG_DIR, f"{name}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return path


def test_parallel_conflict_raises():
    # create two figures that both move to same end position '2m'
    os.makedirs(FIG_DIR, exist_ok=True)
    a = write_fig('collA', '1m', '2m')
    b = write_fig('collB', '1w', '2m')

    # create complex figure data for parallel execution
    data = {
        'Version': 3,
        'Name': 'parallel_conflict_test',
        'FigureList': [
            [[0,0], ['p', [ [[0,0], 'collA'], [[0,0], 'collB'] ]]]
        ]
    }
    from ComplexFigure import ComplexFigure
    cf = ComplexFigure(data)
    floor = DF.DanceFloor('test', 2)
    # place dancers in start positions
    # ensure positions have dancers
    floor.set_dancer('1m', Dancer('Alice','F'))
    floor.set_dancer('1w', Dancer('Bob','M'))

    try:
        cf.DanceMove(floor)
        assert False, 'Expected CombineConflictError'
    except CombineConflictError as e:
        assert '2m' in e.conflicts
    finally:
        # cleanup
        try:
            os.remove(a)
            os.remove(b)
        except Exception:
            pass
