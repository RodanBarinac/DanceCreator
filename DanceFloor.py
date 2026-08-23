import Dancer

def combineDanceFloor(oldDFs = []):
    newDF = DanceFloor('dummy')
    newBars = []

    for DF in oldDFs:
        newBars.append(DF.AktBar)

    if not newBars[:-1] == newBars[1:]:
        raise Exception("Sorry, not all the Bars are equal")
    else:
        newDF.AktBar = newBars[0]

    for i in range(len(oldDFs)):
#        print('????\n', i, oldDFs[i])
        for myPos in oldDFs[i].DanceFloorMap.keys():
            newDF.addDancer(oldDFs[i].DanceFloorMap[myPos][0], myPos, oldDFs[i].DanceFloorMap[myPos][1])
    return newDF


class DanceFloor:
    _DanceFloorMap = {}           # Karte der beteidigten Tänzer
    _DanceFloorNames = {}         # Karte der Positionen der beteidigten Tänzer
    _MaxRow = 0
    _Row = 2
    _Col = 2
    AktBar = 0

    def __init__(self, name, NofCouple = 0):
        self._DanceFloorMap = {}  # Karte der beteidigten Tänzer
        self._DanceFloorNames = {}  # Karte der Positionen der beteidigten Tänzer

        self.name = name
        self.AktBar = 1
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
            raise Exception("Sorry, spott already taken. " + str(myPos) + ' ' + myDancer.name + self.__str__())

    def setupDanceFloorNames(self, NofCouples):
        for myi in range(NofCouples):
            myi += 1
            self._DanceFloorNames[(myi ,1)] = str(myi) + 'm'
            self._DanceFloorNames[(myi ,2)] = 'between ' + str(myi) + 'c'
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
        newDF.AktBar = self.AktBar
        return newDF

    def _short_name(self, myName):
        if myName is None:
            return ''
        myName = str(myName).strip()
        if len(myName) <= 3:
            return myName
        return myName[-3:]

    def _cell_label(self, row, col):
        pos = (row, col)
        if pos not in self._DanceFloorMap:
            return '   '

        dancer = self._DanceFloorMap[pos][0]
        name = self._short_name(getattr(dancer, 'name', ''))
        gender = str(getattr(dancer, 'gender', '')).lower()
        if gender.startswith('m'):
            return '○' + name
        if gender.startswith('f'):
            return '□' + name
        return '·' + name

    def __str__(self):
        maxRow = 0
        maxCol = 0
        for nPos in self._DanceFloorMap.keys():
            if maxRow < nPos[0]:
                maxRow = nPos[0]
            if maxCol < nPos[1]:
                maxCol = nPos[1]
        if maxRow == 0:
            maxRow = self.maxRow

        myDesc = '\nEnd of Bar: ' + str(self.AktBar - 1) + '\n'
        myDesc = myDesc + '    Row |   Men   | Between |   Lady  \n'
        myDesc = myDesc + '   ------+---------+---------+---------\n'

        for row in range(1, int(maxRow) + 1):
            men = self._cell_label(row, 1)
            middle = self._cell_label(row, 2)
            lady = self._cell_label(row, 3)
            myDesc = myDesc + '    {0:>3} | {1:^7} | {2:^7} | {3:^7}\n'.format(row, men, middle, lady)

        return myDesc
