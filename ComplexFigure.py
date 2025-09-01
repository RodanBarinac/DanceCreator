import os
import json
import Figures as Fig
import DanceFloor as DF
import Dance

class ComplexFigure(Fig.Figure):
    _FigureList = [[]]
    _FigureObjs = []
    def __init__(self, loadFile, Anchor = [0,0]):
        self.name = loadFile
        self.Anchor = Anchor
        self.loadFigure(loadFile)

    def SubBars(self, FigObjs):
        if isinstance(FigObjs, Fig.Figure):
            return FigObjs.Bars
        else:
            if isinstance(FigObjs[0], Fig.Figure):
                newBars = 0
                for FigObj in FigObjs:
                    newBars += self.SubBars(FigObj)
                return newBars
            else:
                newBars = []
                for FigObj in FigObjs:
                    newBars.append(self.SubBars(FigObj))

                if not newBars[:-1] == newBars[1:]:
                    raise Exception("Sorry, not all the Bars are allocated")

                return newBars[0]
    @property
    def Bars(self):
        return self.SubBars(self._FigureObjs)

    def subDanceMove(self, FigObjs, newDF):
        if isinstance(FigObjs, Fig.Figure):
            return FigObjs.DanceMove(newDF)
        else:
            if FigObjs[0] == "s":
                for FigObj in FigObjs[1:]:
                    newDF = self.subDanceMove(FigObj, newDF)
                return newDF
            elif FigObjs[0] == "p":
                newDFs = []
                for FigObj in FigObjs[1:]:
                    newDFs.append(self.subDanceMove(FigObj, newDF))
                return DF.combineDanceFloor(newDFs)

    def DanceMove(self, oldDF):
        return self.subDanceMove(self._FigureObjs, oldDF)

    def getCrips(self, myDanceFloorMap, globAnchor=(0, 0)):
        return 'Test'

    def loadSubFigure(self, myFigList, myAnchor):
        if len(myFigList) >> 1:
            if type(myFigList[1]) != type([]):
                return Dance.getFigure( myFigList[1], (myFigList[0][0]+myAnchor[0],myFigList[0][1]+myAnchor[1]))
            else:
                retList = [myFigList[0]]
                for FigList in myFigList[1:]:
                    retList.append(self.loadSubFigure(FigList, myAnchor))
                return retList

    def loadFigure(self, Filename):
        with open(os.getcwd()+'/Figures/' + Filename + '.json', 'r') as f:
            FigData = json.load(f)
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