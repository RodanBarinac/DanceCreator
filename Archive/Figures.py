from abc import ABC, abstractmethod
import os
import json

class Figure(ABC):
    _Desc = ''
    _Bars = 0
    _StartPos = []
    _EndPos = []
    _Facing = []
    _Anchor = (0, 0)

    def clear(self):
        self._Desc = ''
        self._Bars = 0
        self._StartPos = []
        self._EndPos = []
        self._Facing = []
        self._Anchor = (0, 0)

    @property
    def Desc(self):
        return self._Desc
    @Desc.setter
    def Desc(self, newDesc):
        self._Desc = newDesc
    @property
    def Bars(self):
        return self._Bars
    @Bars.setter
    def Bars(self, newBars):
        self._Bars = newBars
    @property
    def StartPos(self):
        return self._StartPos
    @StartPos.setter
    def StartPos(self, newStartPos):
        self._StartPos = newStartPos
    @property
    def EndPos(self):
        return self._EndPos
    @EndPos.setter
    def EndPos(self, newEndPos):
        self._EndPos = newEndPos
    @property
    def Facing(self):
        return self._Facing
    @Facing.setter
    def Facing(self, newFacing):
        self._Facing = newFacing
    @property
    def Anchor(self):
        return self._Anchor
    @Anchor.setter
    def Anchor(self, newPos):
        self._Anchor = newPos
    @abstractmethod
    def DanceMove(self, DanceFloor):
        pass
    @abstractmethod
    def getCrips(self, DanceFloor):
        pass
    @abstractmethod
    def loadFigure(self, Filename):
        pass

    def posWithAnchor(self, myPos):
        return (myPos[0] + self.Anchor[0], myPos[1] + self.Anchor[1])


class FigureAddon():
    _ParentFigureName = ''
    _newStartPos = []
    _newEndPos = []
    _newFacing = []
    _newPartner = []
    _newCrips = []
    _replaceCrips = []

    def __init__(self, parFig, FigData):
        self._ParentFigureName = parFig.name
        self.loadAddon(FigData)

    def Desc(self, oldData):
        return oldData

    def StartPos(self, oldData):
        for i in range(len(self._newStartPos)):
            if len(self._newStartPos[i]):
                oldData[i] = self._newStartPos[i]
        return oldData

    def EndPos(self, oldData):
        for i in range(len(self._newEndPos)):
            if len(self._newEndPos[i]):
                oldData[i] = self._newEndPos[i]
        return oldData

    def Facing(self, oldData):
        for i in range(len(self._newFacing)):
            if len(self._newFacing[i]):
                oldData[i] = self._newFacing[i]
        return oldData

    def Partner(self, oldData):
        for i in range(len(self._newPartner)):
            if len(self._newPartner[i]):
                oldData[i] = self._newPartner[i]
        return oldData

    def getCrips(self, oldData):
        for i in range(len(self._newCrips)):
            if len(self._newCrips[i]):
                oldData[i].replace(self._replaceCrips[i], self._newCrips[i])
        return oldData

    def loadAddon(self, FigData):
        #with open(os.getcwd()+'/Figures/' + Filename + '.json', 'r') as f:
        #    FigData = json.load(f)
        myKeys = FigData.keys()

        if 'Version' in myKeys:
            if FigData['Version'] != 1:
                raise Exception("Sorry, not the right file version!")
        else:
            raise Exception("Sorry, no file version!")

        if 'Name' in myKeys:
            self.Name = FigData['Name']

        if 'Desc' in myKeys:
            self.Desc = FigData['Desc']

        if 'StartPos' in myKeys:
            self._newStartPos = FigData['StartPos']

        if 'EndPos' in myKeys:
            self._newEndPos = FigData['EndPos']

        if 'CriptDesc' in myKeys:
            self._newCrips = FigData['CriptDesc']

        if 'CriptReplace' in myKeys:
            self._replaceCrips = FigData['CriptReplace']

        if 'Faceing' in myKeys:
            self._newFacing = FigData['Faceing']

        if 'Partner' in myKeys:
            self._newPartner = FigData['Partner']

