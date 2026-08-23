import os
import json
import Figures
import DanceFloor as DF

class SimpleFigure(Figures.Figure):
    _Partner = []
    _CriptDesc = []
    _Addons = []

    def __init__(self, loadFile, Anchor = [0,0], Addons = []):
        self.clear()
        self.name = loadFile
        self.Anchor = Anchor
        self.loadFigure(loadFile, Addons)

    def clear(self):
        super().clear()
        self._Partner = []
        self._CriptDesc = []
        self._Addons = []

    @property
    def Desc(self):
        addDesc = ''
        for Addon in self._Addons:
            tmpDesc = Addon.Desc
            if len(tmpDesc) > 0:
                addDesc = addDesc + '\n' + tmpDesc

        if len(addDesc) > 0:
            return super().Desc + '\n' + addDesc
        else:
            return  super().Desc
    @Desc.setter
    def Desc(self, newDesc):
        self._Desc = newDesc

    @property
    def StartPos(self):
        tmpPos = super().StartPos
        for Addon in self._Addons:
            tmpPos = Addon.StartPos(tmpPos)
        return tmpPos
    @StartPos.setter
    def StartPos(self, newStartPos):
        self._StartPos = newStartPos

    @property
    def EndPos(self):
        tmpPos = super().EndPos
        for Addon in self._Addons:
            tmpPos = Addon.EndPos(tmpPos)
        return tmpPos
    @EndPos.setter
    def EndPos(self, newEndPos):
        self._EndPos = newEndPos

    @property
    def Facing(self):
        tmpPos = super().Facing
        for Addon in self._Addons:
            tmpPos = Addon.Facing(tmpPos)
        return tmpPos
    @EndPos.setter
    def Facing(self, newFacing):
        self._Facing = newFacing

    @property
    def Partner(self):
        tmpPos = super().Partner
        for Addon in self._Addons:
            tmpPos = Addon.Partner(tmpPos)
        return tmpPos
    @EndPos.setter
    def Partner(self, newPartner):
        self._Partner = newPartner

    def DanceMove(self, oldDF):
        newDF = DF.DanceFloor('dummy')
        newDF.AktBar = oldDF.AktBar + self.Bars

        for i in range(len(self.StartPos)):
            tmpStartPos = self.posWithAnchor(self.StartPos[i])
            tmpEndPos = self.posWithAnchor(self.EndPos[i])
            if len(self.Facing) > i:
                tmpFacing = self.posWithAnchor(self.Facing[i])
            else:
                tmpFacing = []
            newDF.addDancer(oldDF.DancerbyPos(tmpStartPos), tmpEndPos, tmpFacing)

        return newDF

    def getCrips(self, myDF):
        myCrips = []

        if not isinstance(myDF, DF.DanceFloor):
            raise Exception("Sorry, no Dance Floor")

        aktCrips = self._CriptDesc
        for Addon in self._Addons:
            aktCrips = Addon.getCrips(aktCrips)

        if len(self.StartPos) != len(aktCrips):
            raise Exception("Sorry, no Cripts for everyone")

        for i in range(len(aktCrips)):
            myCript = str(aktCrips[i])
            if '{Dancer}' in myCript:
                myCript = myCript.replace('{Dancer}', myDF.DancerbyPos(self.posWithAnchor(self.StartPos[i])).name)

            if '{StartPos}' in myCript:
                myCript = myCript.replace('{StartPos}', myDF.PosNamebyPos(self.posWithAnchor(self.StartPos[i])))

            if '{EndPos}' in myCript:
                myCript = myCript.replace('{EndPos}', myDF.PosNamebyPos(self.posWithAnchor(self.EndPos[i])))

            if '{Face}' in myCript:
                if self._FacingPos[i] != '':
                    myCript = myCript.replace('{Face}', myDF.PosNamebyPos(self.posWithAnchor(self._FacingPos[i])))
                else:
                    raise Exception("Sorry, noone to face!")

            if '{Partner}' in myCript:
                if self._PartnerPos[i] != '':
                    myCript = myCript.replace('{Partner}', myDF.DancerbyPos(self.posWithAnchor(self._PartnerPos[i])).name)
                else:
                    raise Exception("Sorry, no partner!")
            if len(myCript) > 0:
                myCrips.append(str(myDF.AktBar) + ' - ' + str(myDF.AktBar+self.Bars-1) + ': ' + myCript)

        return myCrips

    def loadFigure(self, Filename, Addons):
        with open(os.getcwd()+'/Figures/' + Filename + '.json', 'r') as f:
            FigData = json.load(f)
        myKeys = FigData.keys()
        if 'Version' in myKeys:
            if FigData['Version'] != 2:
                raise Exception("Sorry, not the right file version")

        if 'Name' in myKeys:
            self.Name = FigData['Name']
        if 'Desc' in myKeys:
            self.Desc = FigData['Desc']
        if 'Bars' in myKeys:
            self.Bars = FigData['Bars']


        if 'StartPos' in myKeys:
            tmpList = []
            for i in range(len(FigData['StartPos'])):
                tmpList.append((FigData['StartPos'][i][0], FigData['StartPos'][i][1]))
            self.StartPos = tmpList
        if 'EndPos' in myKeys:
            tmpList = []
            for i in range(len(FigData['EndPos'])):
                tmpList.append((FigData['EndPos'][i][0], FigData['EndPos'][i][1]))
            self.EndPos = tmpList
        if 'CriptDesc' in myKeys:
            tmpList = []
            for i in range(len(FigData['CriptDesc'])):
                tmpList.append(FigData['CriptDesc'][i])
            self._CriptDesc = tmpList
        if 'Faceing' in myKeys:
            tmpList = []
            for i in range(len(FigData['Faceing'])):
                if len(FigData['Faceing'][i]) == 2:
                    tmpList.append((FigData['Faceing'][i][0], FigData['Faceing'][i][1]))
                else:
                    tmpList.append('')
            self._FacingPos = tmpList
        if 'Partner' in myKeys:
            tmpList = []
            for i in range(len(FigData['Partner'])):
                if len(FigData['Partner'][i]) == 2:
                    tmpList.append((FigData['Partner'][i][0], FigData['Partner'][i][1]))
                else:
                    tmpList.append('')
            self._PartnerPos = tmpList

        if len(Addons) > 0:
            myAKeys = FigData['Addons'].keys()
            for i in range(len(Addons)):
                if Addons[i] in myAKeys:
                    self._Addons.append(Figures.FigureAddon(self, FigData['Addons'][Addons[i]]))
                else:
                    raise Exception('Sorry, no such addon!')
