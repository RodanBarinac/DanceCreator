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
