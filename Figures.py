import json
import DanceFloor as DF

class SimpleFigure:
    _Bars = 0
    _StartPos = []
    _Anchor = (0, 0)
    _TransferCode = []
    _FacingPos = []
    _PartnerPos = []
    _CriptDesc = []
    desc = ''

    def __init__(self, name, desc):
        self.name = name
        self.desc = desc

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
    def Anchor(self):
        return self._Anchor

    @Anchor.setter
    def Anchor(self, newPos):
        self._Anchor = newPos

    @property
    def TransferCode(self):
        return self._TransferCode

    @TransferCode.setter
    def TransferCode(self, newPos):
        self._TransferCode = newPos

    def addPositions(self, *PositionsList):
        myPos = [0, 0]
        Positions = PositionsList[0]
        for i in range(len(Positions)):
            myPos[0] = myPos[0] + Positions[i][0]
            myPos[1] = myPos[1] + Positions[i][1]
        return (myPos[0], myPos[1])

    def getCrips(self, myDanceFloorMap, globAnchor = (0,0)):
        myCrips = []
        myDancers = []
        myEndPos = []
        myFacing = []
        myPartner = []

        myDanceFloor = DF.DanceFloor('getCrips_' + self.name, 10)
        myDanceFloor.setDanceFloorMap(myDanceFloorMap)

        for i in range(len(self.StartPos)):
            myDancers.append(myDanceFloor.NamebyPos((globAnchor[0] + self.Anchor[0]+self.StartPos[i][0], globAnchor[1] + self.Anchor[1]+self.StartPos[i][1])))
        if len(self._PartnerPos) == len(self.StartPos):
            for i in range(len(self.StartPos)):
                if len(self._PartnerPos[i]) == 2:
                    myPartner.append(myDanceFloor.NamebyPos((globAnchor[0] + self.Anchor[0]+self._PartnerPos[i][0], globAnchor[1] + self.Anchor[1]+self._PartnerPos[i][1])))
                else:
                    myFacing.append('')
        myDanceMove = self.DanceMove()
        for i in range(len(myDanceMove['Dancers'])):
            myDanceMove['Dancers'][i] = self.addPositions([tuple(myDanceMove['Dancers'][i]), globAnchor, tuple(self.Anchor)])
        myDanceFloor.doDanceMove(myDanceMove, 'Simple')
        for i in range(len(self.StartPos)):
            myEndPos.append(myDanceFloor.PosNamebyPos(myDanceFloor.PosbyName(myDancers[i])))
        if len(self._FacingPos) == len(self.StartPos):
            for i in range(len(self.StartPos)):
                if len(self._FacingPos[i]) == 2:
                    myFacing.append(myDanceFloor.PosNamebyPos((globAnchor[0] + self.Anchor[0]+self._FacingPos[i][0], globAnchor[1] + self.Anchor[1]+self._FacingPos[i][1])))
                else:
                    myFacing.append('')

        for i in range(len(self.StartPos)):
            n = 1
            Texts = []
            myCript = str(self._CriptDesc[i])
            if '{Dancer}' in myCript:
                myCript = myCript.replace('{Dancer}', '{Text' + str(n) + '}')
                Texts.append(myDancers)
                n = n + 1
            if '{StartPos}' in myCript:
                myCript = myCript.replace('{StartPos}', '{Text' + str(n) + '}')
                Texts.append(self.StartPos)
                n = n + 1
            if '{EndPos}' in myCript:
                myCript = myCript.replace('{EndPos}', '{Text' + str(n) + '}')
                Texts.append(myEndPos)
                n = n  + 1
            if '{Face}' in myCript:
                myCript = myCript.replace('{Face}', '{Text' + str(n) + '}')
                Texts.append(myFacing)
                n = n + 1
            if '{Partner}' in myCript:
                myCript = myCript.replace('{Partner}', '{Text' + str(n) + '}')
                Texts.append(myPartner)
                n = n + 1

            match  n-1:
                case 1:
                    myCript = myCript.format(Text1 = Texts[0][i])
                case 2:
                    myCript = myCript.format(Text1 = Texts[0][i], Text2 = Texts[1][i])
                case 3:
                    myCript = myCript.format(Text1 = Texts[0][i], Text2 = Texts[1][i], Text3 = Texts[2][i])
                case 4:
                    myCript = myCript.format(Text1 = Texts[0][i], Text2 = Texts[1][i], Text3 = Texts[2][i], Text4 = Texts[3][i])
                case 5:
                    myCript = myCript.format(Text1 = Texts[0][i], Text2 = Texts[1][i], Text3 = Texts[2][i], Text4 = Texts[3][i], Text5 = Texts[4][i])
            myCrips.append(myCript)
        return myCrips

    def DanceMove(self):
        myDancers = []
        for i in range(len(self.StartPos)):
            myPos = (self.Anchor[0]+self.StartPos[i][0], self.Anchor[1]+self.StartPos[i][1])
            myDancers.append(myPos)
        return {'Dancers': myDancers, 'Move': self.TransferCode, 'Bars': self.Bars}

    def loadFigure(self, Filename):
        with open('E:/Git/DanceCreator/Figures/' + Filename + '.json', 'r') as f:
            FigData = json.load(f)
        myKeys = FigData.keys()

        if 'Name' in myKeys:
            self.name = FigData['Name']
        if 'Desc' in myKeys:
            self.desc = FigData['Desc']
        if 'Bars' in myKeys:
            self.Bars = FigData['Bars']


        if 'StartPos' in myKeys:
            tmpList = []
            for i in range(len(FigData['StartPos'])):
                tmpList.append((FigData['StartPos'][i][0], FigData['StartPos'][i][1]))
            self.StartPos = tmpList
        if 'TransferCode' in myKeys:
            tmpList = []
            for i in range(len(FigData['TransferCode'])):
                tmpList.append((FigData['TransferCode'][i][0], FigData['TransferCode'][i][1]))
            self.TransferCode = tmpList
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

    def writeFigure(self):
        FigData = {
            'Name': self.name,
            'Desc': self.desc,
            'Bars': self.Bars,
            'StartPos': self.StartPos,
            'TransferCode': self.TransferCode,
            'CriptDesc' : self._CriptDesc,
            'Faceing' :self._FacingPos,
            'Partner' : self._PartnerPos
            }

        with open('E:/Git/DanceCreator/Figures/' + self.name + '.json', 'w') as f:
            json.dump(FigData, f, sort_keys=True)




class Dance(SimpleFigure):
    pass
