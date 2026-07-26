from Figures import Figure
from Dancer import Dancer

class SimpleFigure(Figure):
    def __init__(self, data):
        super().__init__(name=data.get('Name'), version=data.get('Version'), desc=data.get('Desc'), bars=data.get('Bars'))
        self.StartPos = data.get('StartPos', [])
        self.EndPos = data.get('EndPos', [])
        self.CriptDesc = data.get('CriptDesc', [])
        self.Faceing = data.get('Faceing', [])
        self.Partner = data.get('Partner', [])
        self.Addons = data.get('Addons', {})

    def DanceMove(self, oldDF):
        # naive implementation: map StartPos -> EndPos by index
        new = oldDF.copy()
        for i, sp in enumerate(self.StartPos):
            try:
                ep = self.EndPos[i]
            except IndexError:
                continue
            # position names expected as strings (e.g., '1m') in higher-level code
            # if input contains coords, try to map by inferred names
            # simple approach: if keys matching exist, move dancer from first matching start to end
            # find dancer at any position matching coords
            start_name = None
            end_name = None
            # if entries are strings, use directly
            if isinstance(sp, str):
                start_name = sp
            elif isinstance(sp, (list, tuple)):
                # try to find position with same coord
                for pname, pinfo in oldDF.positions.items():
                    if pinfo.get('coord') == sp:
                        start_name = pname
                        break
            if isinstance(ep, str):
                end_name = ep
            elif isinstance(ep, (list, tuple)):
                # find matching position by coord
                for pname, pinfo in new.positions.items():
                    if pinfo.get('coord') == ep:
                        end_name = pname
                        break
            if not start_name or not end_name:
                continue
            dancer = oldDF.positions.get(start_name, {}).get('dancer')
            if dancer:
                new.set_dancer(end_name, dancer)
                # clear old position
                new.set_dancer(start_name, None)
        new.tick += getattr(self, 'Bars', 0)
        return new

    def getCrips(self, oldDF):
        # expand templates minimally
        lines = []
        for t in self.CriptDesc:
            line = t
            # naive placeholder replacement
            line = line.replace('{Bars}', str(self.Bars))
            lines.append(line)
        return lines
