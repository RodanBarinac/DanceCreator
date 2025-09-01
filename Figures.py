from abc import ABC, abstractmethod
# import DanceFloor as DF

class Figure(ABC):
    _Desc = ''
    _Bars = 0
    _StartPos = []
    _EndPos = []
    _Facing = []
    _Anchor = (0, 0)

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
    def getCrips(self):
        pass
    @abstractmethod
    def loadFigure(self, Filename):
        pass

    def posWithAnchor(self, myPos):
        return (myPos[0] + self.Anchor[0], myPos[1] + self.Anchor[1])
''