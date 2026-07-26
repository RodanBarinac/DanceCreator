import copy

class DanceFloor:
    def __init__(self, name, couples=1):
        self.name = name
        self.couples = couples
        self.tick = 0
        # positions like '1m','1w','2m','2w' etc.
        self.positions = {}
        self.init_positions()

    def init_positions(self):
        self.positions = {}
        for r in range(1, self.couples+1):
            # man at col 1, woman at col 3
            self.positions[f"{r}m"] = {"dancer": None, "coord": [r,1]}
            self.positions[f"{r}w"] = {"dancer": None, "coord": [r,3]}

    def copy(self):
        return copy.deepcopy(self)

    def set_dancer(self, pos_name, dancer):
        if pos_name not in self.positions:
            self.positions[pos_name] = {"dancer": dancer, "coord": None}
        else:
            self.positions[pos_name]["dancer"] = dancer

    def move_by_positions(self, mapping):
        # mapping: pos_name -> dancer (or dancer dict)
        new = self.copy()
        for pos, d in mapping.items():
            new.set_dancer(pos, d)
        return new

    def __str__(self):
        s = f"DanceFloor: {self.name} (couples={self.couples}, tick={self.tick})\n"
        for p in sorted(self.positions.keys()):
            d = self.positions[p]["dancer"]
            dn = d.name if d else "-"
            s += f" {p}: {dn}\n"
        return s

    def to_dict(self):
        return {
            "name": self.name,
            "couples": self.couples,
            "tick": self.tick,
            "positions": self.positions
        }


class CombineConflictError(Exception):
    """Raised when multiple parallel floors write conflicting dancers into the same position."""
    def __init__(self, message, conflicts=None):
        super().__init__(message)
        self.conflicts = conflicts or {}


def combine_dancefloors(floors):
    """Combine multiple DanceFloor instances resulting from parallel execution.
    If a position is written by more than one floor with different dancers, raise CombineConflictError.
    Otherwise, apply non-empty changes to a base floor and return it.
    """
    if not floors:
        raise ValueError('No floors to combine')
    base = floors[0].copy()
    conflicts = {}
    # for each position, collect non-None dancer identities
    positions = set()
    for f in floors:
        positions.update(f.positions.keys())
    for pos in positions:
        dancers = []
        for idx, f in enumerate(floors):
            d = f.positions.get(pos, {}).get('dancer')
            if d is not None:
                dancers.append((idx, d))
        # check for conflict: more than one distinct dancer
        unique_names = set()
        for _, d in dancers:
            name = getattr(d, 'name', None) if d is not None else None
            unique_names.add(name)
        if len(dancers) > 1 and len([n for n in unique_names if n is not None]) > 1:
            # conflict
            conflicts[pos] = [{'floor': idx, 'dancer': getattr(d,'name',d)} for idx, d in dancers]
    if conflicts:
        raise CombineConflictError('Conflict while combining parallel floors', conflicts=conflicts)
    # no conflicts: apply non-None dancer values from floors in order (first non-None wins)
    result = base
    for f in floors:
        for pos, info in f.positions.items():
            if info.get('dancer') is not None:
                result.set_dancer(pos, info.get('dancer'))
    # tick: choose max tick
    result.tick = max(f.tick for f in floors)
    return result

