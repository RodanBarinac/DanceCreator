from abc import ABC, abstractmethod
import os
import json

class Figure(ABC):
    _Desc = ''
    _Bars = 0
    _StartPos = []
    _EndPos = []
    _EndFacing = []
    _StartFacing = []
    _StartDancers = []
    _Partner = []
    _Anchor = (0, 0)

    def clear(self):
        self._Desc = ''
        self._Bars = 0
        self._StartPos = []
        self._EndPos = []
        self._EndFacing = []
        self._StartFacing = []
        self._StartDancers = []
        self._Partner = []
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
    def EndFacing(self):
        return self._EndFacing
    @EndFacing.setter
    def EndFacing(self, newFacing):
        self._EndFacing = newFacing
    @property
    def StartFacing(self):
        return self._StartFacing
    @StartFacing.setter
    def StartFacing(self, newFacing):
        self._StartFacing = newFacing
    @property
    def StartDancers(self):
        return self._StartDancers
    @StartDancers.setter
    def StartDancers(self, newDancers):
        self._StartDancers = newDancers
    @property
    def Partner(self):
        return self._Partner
    @Partner.setter
    def Partner(self, newPartner):
        self._Partner = newPartner
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


class FigureAddon:
    """A selected, data-defined addon applied to one simple figure."""

    def __init__(self, parFig, fig_data):
        self._ParentFigureName = parFig.name
        self._newBars = None
        self._newStartPos = []
        self._newEndPos = []
        self._newEndFacing = []
        self._newPartner = []
        self._newCrips = []
        self._replaceCrips = []
        self.Name = ""
        self.loadAddon(fig_data)

    def Desc(self, oldData):
        return oldData

    @staticmethod
    def _replace_entries(old_data, replacements):
        result = list(old_data)
        for index, replacement in enumerate(replacements):
            if replacement:
                while len(result) <= index:
                    result.append([])
                result[index] = replacement
        return result

    def Bars(self, oldData):
        return oldData if self._newBars is None else self._newBars

    def StartPos(self, oldData):
        return self._replace_entries(oldData, self._newStartPos)

    def EndPos(self, oldData):
        return self._replace_entries(oldData, self._newEndPos)

    def EndFacing(self, oldData):
        return self._replace_entries(oldData, self._newEndFacing)

    def Partner(self, oldData):
        return self._replace_entries(oldData, self._newPartner)

    def getCrips(self, oldData):
        result = list(oldData)
        for i in range(min(len(self._newCrips), len(result), len(self._replaceCrips))):
            replacement = self._newCrips[i]
            target = self._replaceCrips[i]
            if replacement and target:
                result[i] = result[i].replace(target, replacement)
        return result

    def loadAddon(self, fig_data):
        from src.engine.figures.addon_utils import duration_addon_bars

        keys = fig_data.keys()
        if 'Faceing' in keys:
            raise ValueError("Unsupported legacy addon key 'Faceing'; use 'EndFacing'.")
        self.Name = fig_data.get('Name', self.Name)
        if 'Bars' in keys:
            self._newBars = fig_data['Bars']
        elif duration_addon_bars(self.Name) is not None:
            self._newBars = duration_addon_bars(self.Name)
        self._newStartPos = fig_data.get('StartPos', [])
        self._newEndPos = fig_data.get('EndPos', [])
        self._newEndFacing = fig_data.get('EndFacing', [])
        self._newPartner = fig_data.get('Partner', [])
        self._newCrips = fig_data.get('CriptDesc', [])
        self._replaceCrips = fig_data.get('CriptReplace', [])
