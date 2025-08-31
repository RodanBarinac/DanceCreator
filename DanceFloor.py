import Dancer

def combineDanceFloor(oldDFs = []):
    newDF = DanceFloor('dummy')

    for i in range(len(oldDFs)):
        for myPos in oldDFs[i].DanceFloorMap.keys():
            newDF.addDancer(oldDFs[i].DanceFloorMap[myPos][0], myPos, oldDFs[i].DanceFloorMap[myPos][1])
    return newDF


class DanceFloor:
    _DanceFloorMap = {}           # Karte der beteidigten Tänzer
    _DanceFloorNames = {}         # Karte der Positionen der beteidigten Tänzer
    _MaxRow = 0
    _Row = 2
    _Col = 2

    def __init__(self, name, NofCouple = 0):
        self._DanceFloorMap = {}  # Karte der beteidigten Tänzer
        self._DanceFloorNames = {}  # Karte der Positionen der beteidigten Tänzer

        self.name = name
        self.maxRow = NofCouple
        if NofCouple > 0:
            self.setupDancefloor(int(NofCouple))

    @property
    def maxRow(self):
        return self._MaxRow
    @maxRow.setter
    def maxRow(self, newMaxRow):
        if newMaxRow > self.maxRow:
            self._MaxRow = newMaxRow
            self.setupDanceFloorNames(int(newMaxRow))

    @property
    def DanceFloorMap(self):
        return self._DanceFloorMap

    def DancerbyPos(self, myPos):
        if type(myPos) == type([]):
            myPos = (myPos[0], myPos[1])

        if myPos in self._DanceFloorMap:
            myDancer = self._DanceFloorMap[myPos][0]
        else:
            raise Exception("Sorry, no dancer here! " + str(myPos) + "\n" + str(self))

        return myDancer

    def PosNamebyPos(self, myPos):
        if type(myPos) == type([]):
            myPos = (myPos[0], myPos[1])

        if myPos in self._DanceFloorNames:
            myName = self._DanceFloorNames[myPos] + 's position'
        else:
            myName = ''

        return myName

    def addDancer(self, myDancer, myPos, myFacing):
        if type(myPos) == type([]):
            myPos = (myPos[0], myPos[1])

        self.maxRow = myPos[0]
        if myPos not in self._DanceFloorMap.keys():
            self._DanceFloorMap[myPos] = [myDancer, myFacing]
        else:
            raise Exception("Sorry, spott already taken. " + str(myPos))

    def setupDanceFloorNames(self, NofCouples):
        for myi in range(NofCouples):
            myi += 1
            self._DanceFloorNames[(myi ,1)] = str(myi) + 'm'
            self._DanceFloorNames[(myi ,3)] = str(myi) + 'w'

    def setupDancefloor(self, NofCouples):
        for myi in range(NofCouples):
            myi += 1
            myMan = Dancer.Dancer(str(myi) + 'm', 'male')
            myLady = Dancer.Dancer(str(myi) + 'w', 'female')

            self.addDancer(myMan, (myi, 1), [myi, 3])
            self.addDancer(myLady, (myi, 3),[myi, 1])
    def copy(self):
        newDF = DanceFloor('dummy')

        for myPos in self._DanceFloorMap.keys():
             newDF.addDancer( self._DanceFloorMap[myPos][0], myPos,  self._DanceFloorMap[myPos][1])
        return newDF

    def __str__(self):
        maxRow = 0
        maxCol = 0
        for nPos in self._DanceFloorMap.keys():
            if maxRow < nPos[0]:
                maxRow = nPos[0]
            if maxCol < nPos[1]:
                maxCol = nPos[1]
#        print(str(maxRow) + ' / ' + str(maxCol))
        myDesc = '            Men                 Lady'
        for i in range(int(self._Row * maxRow) + 1):
            for j in range(int(self._Col * maxCol) + 1):
                locDesc = '    '
                if (i/self._Row,j/self._Col) in self._DanceFloorMap.keys():
                    locDesc = locDesc + self._DanceFloorMap[(i/self._Row, j/self._Col)][0].name
                myDesc = myDesc + locDesc[-4:] + ' '
            myDesc = myDesc + '\n'

        return myDesc

