# class Position:
#     x = 0
#     y = 0
#
#     def __init__(self, value):
#         self.x = value[0]
#         self.y = value[1]
#
#     def __add__(self, other):
#         return (self.x + other.x, self.y + other.y)

class DanceFloor:
    _DanceFloorMap = dict
    _DanceFloorNames = dict
    _Row = 2
    _Col = 4
    Bar = 0

    def __init__(self, name, NofCouple = 3):
        self.name = name
        self.setupDancefloor(NofCouple)

    def getDanceFloorMap(self):
        return self._DanceFloorMap.copy()
    def setDanceFloorMap(self, myFloorMap):
        self._DanceFloorMap = myFloorMap

    def PosbyName(self, myName):
        if myName in self._DanceFloorMap.values():
            keys = [k for k, v in self._DanceFloorMap.items() if v == myName]
            return keys[0]

    def NamebyPos(self, myPos):
        if myPos in self._DanceFloorMap:
            myName = self._DanceFloorMap[myPos]
        else:
            myName = ''

        return myName

    def PosNamebyPos(self, myPos):
        if myPos in self._DanceFloorNames:
            myName = self._DanceFloorNames[myPos] + ' position'
        else:
            myName = ''

        return myName
    def addDancer(self, myName, myPos):
        if myPos not in self._DanceFloorMap.keys():
            self._DanceFloorMap[myPos] = myName

    def setupDancefloor(self, NofCouples):
        self._DanceFloorMap = {}
        for myi in range(NofCouples):
            myi = myi+1
            self._DanceFloorMap[(myi,1)] = str(myi) + 'm'
            self._DanceFloorMap[(myi,2)] = str(myi) + 'w'
        self._DanceFloorNames = self._DanceFloorMap.copy()

    def teleportDancerbyName(self, myName, AbsPos, newFloor):
        StartPos = newFloor.PosbyName(myName)
        if StartPos != '':
            newFloor.pop(StartPos)
        newFloor[AbsPos] = myName
        return newFloor

    def moveDancerbyPos(self, StartPos, RelPos, newFloor):
        if StartPos in self._DanceFloorMap:
            myName = self._DanceFloorMap[StartPos]
            if newFloor[StartPos] == self._DanceFloorMap[StartPos]:
                newFloor.pop(StartPos)
            myPos =(StartPos[0]+RelPos[0], StartPos[1]+RelPos[1])
            newFloor[myPos] = myName
        return newFloor

    def moveDancerbyName(self,myName,RelPos, newFloor):
        return self.moveDancerbyPos(self.PosbyName(myName),RelPos,newFloor)

    def doDanceMove(self, myDanceMove, FigType = 'Simple'):
        if FigType == 'Simple':
            if type(myDanceMove) == dict:
                newFloorMap = self.getDanceFloorMap()
                for i in range(len(myDanceMove['Move'])):
                    self.moveDancerbyPos(myDanceMove['Dancers'][i], myDanceMove['Move'][i], newFloorMap)
                self.setDanceFloorMap(newFloorMap)
                self.Bar = self.Bar + myDanceMove['Bars']

        if FigType == 'Seriel':
            if type(myDanceMove) != []:
                myDanceMove = [myDanceMove]
            myDanceFloor = DanceFloor('DoDanceMove_' + self.name, 0)
            myDanceFloor.setDanceFloorMap(self.getDanceFloorMap())
            for j in range(len(myDanceMove)):
                myDanceFloor.doDanceMove(myDanceMove[j], 'Simple')
            self.setDanceFloorMap(myDanceFloor.getDanceFloorMap())
            self.Bar = self.Bar + myDanceFloor.Bar

        if FigType == 'Parallel':
            myDanceFloorList = []
            for i in range(len(myDanceMove)):
                myDanceFloorList.append(DanceFloor('DoDanceMove_' + self.name + str(i), 0))
                myDanceFloorList[i].setDanceFloorMap(myDanceFloorMap)
                myDanceFloorList[i].doDanceMove(myDanceMove[i], 'Seriel')

            newFloorMap = self.getDanceFloorMap()
            for i in range(len(myDanceFloorList)):
                for j in range(len(myDanceMove[i]['Dancers'])):
                   self.teleportDancerbyName(myDanceMove[i]['Dancers'][j], myDanceFloorList[i].PosbyName(myDanceMove[i]['Dancers'][j]), newFloorMap)

    def __str__(self):
        maxRow = 0
        maxCol = 0
        for nPos in self._DanceFloorMap.keys():
            if maxRow < nPos[0]:
                maxRow = nPos[0]
            if maxCol < nPos[1]:
                maxCol = nPos[1]
#        print(str(maxRow) + ' / ' + str(maxCol))
        myDesc = '                     Men                 Lady\n'
        for i in range(int(self._Row * maxRow) + 1):
            for j in range(int(self._Col * maxCol) + 1):
                locDesc = '    '
                if (i/self._Row,j/self._Col) in self._DanceFloorMap.keys():
                    locDesc = locDesc + self._DanceFloorMap[(i/self._Row, j/self._Col)]
                myDesc = myDesc + locDesc[-4:] + ' '
            myDesc = myDesc + '\n'

        return myDesc

