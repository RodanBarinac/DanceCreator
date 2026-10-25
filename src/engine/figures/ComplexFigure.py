import os
import json
from ..models import Figures as Fig
from ..models import DanceFloor as DF
from ..models import Dance

class ComplexFigure(Fig.Figure):
    _FigureList = [[]]
    _FigureObjs = []

    def __init__(self, loadFile, Anchor = [0,0]):
        self.name = loadFile
        self.Anchor = Anchor
#        self.loadFigure(loadFile)

    def clear(self):
        super().clear()
        self._FigureList = [[]]
        self._FigureObjs = []

    def SubBars(self, FigObjs):
        if isinstance(FigObjs, Fig.Figure):
            return FigObjs.Bars
        if not isinstance(FigObjs, (list, tuple)) or not FigObjs:
            return 0

        if FigObjs[0] in ('s', 'p') and len(FigObjs) == 2:
            group_type, children = FigObjs
            child_bars = [self.SubBars(child) for child in children]
            if not child_bars:
                return 0
            if group_type == 's':
                return sum(child_bars)
            if any(bars != child_bars[0] for bars in child_bars[1:]):
                raise Exception("Sorry, not all the Bars are allocated")
            return child_bars[0]

        child_bars = [self.SubBars(child) for child in FigObjs]
        if all(isinstance(child, Fig.Figure) for child in FigObjs):
            return sum(child_bars)
        if any(bars != child_bars[0] for bars in child_bars[1:]):
            raise Exception("Sorry, not all the Bars are allocated")
        return child_bars[0]
    @property
    def Bars(self):
        return self.SubBars(self._FigureObjs)

    def subDanceMove(self, FigObjs, newDF):
        if isinstance(FigObjs, Fig.Figure):
            return FigObjs.DanceMove(newDF)
        else:
            if FigObjs[0] == "s":
                for FigObj in FigObjs[1]:
                    newDF = self.subDanceMove(FigObj, newDF)
                return newDF
            elif FigObjs[0] == "p":
                newDFs = []
                for FigObj in FigObjs[1]:
                    newDFs.append(self.subDanceMove(FigObj, newDF))
                return DF.combineDanceFloor(newDFs)

    def DanceMove(self, oldDF):
        return self.subDanceMove(self._FigureObjs, oldDF)

    def subgetCrips(self, FigObjs, newDF):
        if isinstance(FigObjs, Fig.Figure):
            return FigObjs.getCrips(newDF)
        else:
            if FigObjs[0] == "s":
                newCrips = []
                tmpDF = newDF.copy()
                for FigObj in FigObjs[1]:
                    newCrips.append(self.subgetCrips(FigObj, tmpDF))
                    tmpDF = self.subDanceMove(FigObj, tmpDF)
                return newCrips
            elif FigObjs[0] == "p":
                newCrips = [] #  ['While:']
                for FigObj in FigObjs[1]:
                    newCrips.append(self.subgetCrips(FigObj, newDF))
                return newCrips
            else:
                raise Exception("Sorry, no valid figure found!")

    def getCrips(self, oldDF):
        return self.subgetCrips(self._FigureObjs, oldDF)

    def loadSubFigure(self, myFigList, myAnchor):
        if len(myFigList) >> 1:
            if type(myFigList[1]) != type([]):
                return Dance.getFigure(myFigList[1], (myFigList[0][0] + myAnchor[0], myFigList[0][1] + myAnchor[1]),[]) # no Addons
            elif type(myFigList[1][0]) == type('') and myFigList[1][0] != 's' and myFigList[1][0] != 'p':
                return Dance.getFigure( myFigList[1][0], (myFigList[0][0]+myAnchor[0],myFigList[0][1]+myAnchor[1]), myFigList[1][1])
            else:
                retList = [myFigList[0],[]]
                for FigList in myFigList[1]:
                    retList[1].append(self.loadSubFigure(FigList, myAnchor))
                return retList

    def loadFigure(self, Filename = ''):
        if Filename == '':
            Filename = self.name

        # Determine the actual file path.
        # If an absolute path or a path containing separators is provided, use it (ensure .json suffix).
        # Otherwise, assume the file is in the project's data/Figures directory and append .json.
        if os.path.isabs(Filename) or (os.path.sep in Filename) or ('/' in Filename):
            filepath = Filename if Filename.lower().endswith('.json') else Filename + '.json'
        else:
            filepath = os.path.join(os.getcwd(), 'data', 'Figures', Filename + '.json')

        # Check if the file exists before attempting to open it.
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Figure file not found: {filepath}")

        with open(filepath, 'r') as f:
            FigData = json.load(f)
        if 'Faceing' in FigData:
            raise ValueError("Unsupported legacy figure key 'Faceing'; use 'EndFacing'.")
        myKeys = FigData.keys()
        if 'Version' in myKeys:
            if FigData['Version'] != 3:
                raise Exception("Sorry, not the right version")

        if 'Name' in myKeys:
            self.name = FigData['Name']
        if 'Desc' in myKeys:
            self.desc = FigData['Desc']

        if 'FigureList' in myKeys:
            self._FigureList = FigData['FigureList']

        self._FigureObjs = self.loadSubFigure(self._FigureList, self.Anchor)