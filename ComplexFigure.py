from Figures import Figure
from SimpleFigure import SimpleFigure

class ComplexFigure(Figure):
    def __init__(self, data):
        super().__init__(name=data.get('Name'), version=data.get('Version'), desc=data.get('Desc'))
        self.FigureList = data.get('FigureList', [])

    def DanceMove(self, oldDF):
        floor = oldDF
        for entry in self.FigureList:
            anchor, fig = entry[0], entry[1]
            # fig can be string (name) or nested ["s", [...]] or ["p", [...]]
            if isinstance(fig, str):
                # lazy load via Dance.getFigure to avoid circular import; do dynamic import
                from Dance import getFigure
                fobj = getFigure(fig, anchor)
                floor = fobj.DanceMove(floor)
            elif isinstance(fig, list) and fig[0] == 's':
                # sequential
                for sub in fig[1]:
                    sub_anchor, sub_fig = sub[0], sub[1]
                    from Dance import getFigure
                    fobj = getFigure(sub_fig, sub_anchor)
                    floor = fobj.DanceMove(floor)
            elif isinstance(fig, list) and fig[0] == 'p':
                # parallel: compute floors and merge using combine_dancefloors
                floors = []
                for sub in fig[1]:
                    sub_anchor, sub_fig = sub[0], sub[1]
                    from Dance import getFigure
                    fobj = getFigure(sub_fig, sub_anchor)
                    floors.append(fobj.DanceMove(oldDF.copy()))
                # use DanceFloor.combine_dancefloors to detect conflicts
                from DanceFloor import combine_dancefloors
                floor = combine_dancefloors(floors)
            else:
                # unknown entry
                continue
        return floor

    def getCrips(self, oldDF):
        lines = []
        for entry in self.FigureList:
            anchor, fig = entry[0], entry[1]
            if isinstance(fig, str):
                from Dance import getFigure
                fobj = getFigure(fig, anchor)
                lines.extend(fobj.getCrips(oldDF))
            elif isinstance(fig, list):
                mode = fig[0]
                if mode == 's':
                    for sub in fig[1]:
                        sub_anchor, sub_fig = sub[0], sub[1]
                        from Dance import getFigure
                        fobj = getFigure(sub_fig, sub_anchor)
                        lines.extend(fobj.getCrips(oldDF))
                elif mode == 'p':
                    for sub in fig[1]:
                        sub_anchor, sub_fig = sub[0], sub[1]
                        from Dance import getFigure
                        fobj = getFigure(sub_fig, sub_anchor)
                        lines.extend(fobj.getCrips(oldDF))
        return lines
