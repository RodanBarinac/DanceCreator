from configparser import ConfigParser

                
class Step:
    pass


class SimpleFigure:
    _Bars = 0
    _Dancers = ['1m', '1l', '2m', '2l']
    _StartPos = []
    _TransferCode = []
    desc = ""

    _PosMap = [
        ['1m', '1bm', '1center', '1bl' ,'1l'],
        ['b1&2m', 'b1&2bm', 'b1&2center', 'b1&2bl' ,'b1&2l'],
        ['2m', '2bm', '2center', '2bl' ,'2l'],
        ['b2&3m', 'b2&3bm', 'b2&3center', 'b2&3bl' ,'b2&3l'],
        ['3m', '3bm', '3center', '3bl' ,'3l'],
        ['b3&4m', 'b3&4bm', 'b3&4center', 'b3&4bl' ,'b3&4l'],
        ['4m', '4bm', '4center', '4bl' ,'4l'],
        ['b4&5m', 'b4&5bm', 'b4&5center', 'b4&5bl' ,'b4&5l'],
        ['5m', '5bm', '5center', '5bl' ,'5l'],
    ]

    def __init__(self, name, desc):
        self.name = name
        self.desc = desc

    def __str__(self):
        return self.name

    def __len__(self):
        return self._Bars

    @property
    def Bars(self):
        return self._Bars
    @Bars.setter
    def Bars(self, newBars):
        self._Bars = newBars

    @property
    def Dancers(self):
        return self._Dancers

    @Dancers.setter
    def Dancers(self, newDancers):
        if len(newDancers) == len(self.StartPos):
            self._Dancers = newDancers

    @property
    def StartPos(self):
        return self._StartPos

    @StartPos.setter
    def StartPos(self, newPos):
        self._StartPos = newPos

    @property
    def TransferCode(self):
        return self._TransferCode

    @TransferCode.setter
    def TransferCode(self, newPos):
        self._TransferCode = newPos


    @property
    def EndPos(self):
        myEndPos = []
        for i in range(len(self.StartPos)):
            myEndPos.append(self.transferPosition(self.StartPos[i], self.TransferCode[i]))

        return myEndPos

    def short_desc(self):
        return self.desc
    @property
    def long_desc(self):
        myStr = ""
        for i in range(len(self.StartPos)):
           myStr = myStr + f"{self.desc} for {self.Dancers[i]} from {self.StartPos[i]} to {self.EndPos[i]}\n"

        return myStr

    # def writeFigure(self):
    #     config = ConfigParser()
    #
    #     config['SimpleFigure']= {}
    #     config['SimpleFigure']['Name'] = self.name
    #     config['SimpleFigure']['Desc'] = self.desc
    #     config['SimpleFigure']['Bars'] = '%s' % self.Bars
    #     config['Dancers']= {}
    #     config['StartPos']= {}
    #     config['TransferCode']= {}
    #     config['Dancers']['Anzahl'] = '%s' % len(self.Dancers)
    #     for i in range(len(self.StartPos)):
    #         config['StartPos']['%s' % i] = self.StartPos[i]
    #         config['TransferCode']['%s' % i] = self.TransferCode[i]
    #
    #     with open(self.name + '.ini', 'w') as configfile:
    #         config.write(configfile)

    def loadFigure(self, Filename):
        config = ConfigParser()
        config.read_file(open(Filename + '.ini', 'r'))

        self.name = config['SimpleFigure']['Name']
        self.desc = config['SimpleFigure']['Desc']
        self.Bars =config['SimpleFigure']['Bars']

        # myDancers = []
        myStartPos = []
        myTransferCode = []
        for i in range(int(config['Dancers']['Anzahl'])):
           # myDancers.append(config['Dancers']['%s' % i])
           myStartPos.append(config['StartPos']['%s' % i])
           myTransferCode.append(config['TransferCode']['%s' % i])
          
        self.StartPos = myStartPos
        self.TransferCode = myTransferCode

    def transferPosition(self, StartPos, TransCode):        
        mypos = [0, 0]
        mytrco = ['', '']
    
        if StartPos == '1m':
            mypos = [0,0]
        elif StartPos == '1l':
            mypos = [0,1]
        elif StartPos == '3m':
            mypos = [2,0]
        elif StartPos == '3l':
            mypos = [2,1]
        elif StartPos == 'b1&2bm':
            mypos = [0.5,0.25]
        elif StartPos == 'b2&3bl':
            mypos = [1.5,0.75]
    
    #   TransCode z.B. [Row][Colum]
        mytrco = TransCode.split('][', 2)
        for i in range(len(mytrco)):
            mytrco[i] = mytrco[i].strip('[]')
    
        for i in range(len(mytrco)):
            if mytrco[i] == '0':
                mypos[i] = mypos[i]
            elif mytrco[i] == '1':
                mypos[i] = mypos[i] + 1
            elif mytrco[i] == '-1':
                mypos[i] = mypos[i] - 1
            elif mytrco[i] == '2':
                mypos[i] = mypos[i] + 2
            elif mytrco[i] == '-2':
                mypos[i] = mypos[i] - 2
            elif mytrco[i] == '1/2':
                mypos[i] = mypos[i] + 0.5
            elif mytrco[i] == '-1/2':
                mypos[i] = mypos[i] - 0.5
            elif mytrco[i] == '1/4':
                mypos[i] = mypos[i] + 0.25
            elif mytrco[i] == '-1/4':
                mypos[i] = mypos[i] - 0.25
    
        return self._PosMap[int(mypos[0]*2)][int(mypos[1]*4)]

class Figure(SimpleFigure):
    FigureSeries = []
    desc = ''
    _Dancers = ['1m', '1l', '2m', '2l']

    def __init__(self, name, desc):
        self.name = name
        self.desc = desc

    @property
    def Bars(self):
        my_Bars = 0
        if len(self.FigureSeries) > 0:
            for myFigure in self.FigureSeries:
                my_Bars = my_Bars + myFigure.Bars
        return my_Bars

    @property
    def Dancers(self):
        return self._Dancers

    @Dancers.setter
    def Dancers(self, newDancers):
        if len(newDancers) == len(self.StartPos):
            self._Dancers = newDancers

    @property
    def StartPos(self):
        return self._StartPos

    @StartPos.setter
    def StartPos(self, newPos):
        self._StartPos = newPos

    @property
    def EndPos(self):
        myAktPos = self.StartPos
        if len(self.FigureSeries) > 0:
            for myFigure in self.FigureSeries:
                myFigure.StartPos = myAktPos
                myAktPos = myFigure.EndPos

        return myAktPos

    def short_desc(self):
        return self.desc

    @property
    def long_desc(self):
        myStr = ""
        myAktPos = self.StartPos
        if len(self.FigureSeries) > 0:
            for myFigure in self.FigureSeries:
                myFigure.Dancers = self.Dancers
                myFigure.StartPos = myAktPos
                myStr = myStr + myFigure.long_desc
                myAktPos = myFigure.EndPos
        return myStr

    def testFigure(self):
        myDance = Dance(self.name)
        if myDance.TestDance(self):
            return 'Pass'
        else:
            return 'Fail'
        del myDance

    def writeFigure(self):
        config = ConfigParser()

        config['Figure']= {}
        config['Figure']['Name'] = self.name
        config['Figure']['Desc'] = self.desc
        config['Series']= {}
        config['Series']['Anzahl'] = '%s' % len(self.FigureSeries)
        for i in range(len(self.FigureSeries)):
            config['Series']['%s' % i] = self.FigureSeries[i].name

        with open(self.name + '.ini', 'w') as configfile:
            config.write(configfile)

    def loadFigure(self, Filename):
        config = ConfigParser()
        config.read_file(open(Filename + '.ini', 'r'))

        self.name = config['Figure']['Name']
        self.desc = config['Figure']['Desc']

        mySeries =[]
        for i in range(int(config['Series']['Anzahl'])):
            mySeries.append(SimpleFigure(config['Series']['%s' % i], 'empty'))
            mySeries[i].loadFigure(mySeries[i].name)
        self.FigureSeries = mySeries

class Dance(Figure):
    def __init__(self, name):
        self.name = name
        self.desc = name

    # def TestDance(self, myDance = ''):
    #     if myDance == '':
    #         myDance = self
    #
    #     if myDance.Dancers != 0:
    #         myDancers = myDance.Dancers
    #         myBars = myDance.Bars
    #         myAktPositions = myDance.StartPos
    #         myFigureSeries = myDance.FigureSeries
    #         myTime = [0 for j in range(len(myDancers))]
    #
    #         for myFigure in myFigureSeries:
    #             myFlags = [True for j in range(len(myDancers))]
    #             myEndPositions = ['' for j in range(len(myDancers))]
    #             for aktDancer in myFigure.Dancers:
    #                 if myAktPositions[myDancers.index(aktDancer)] == myFigure.StartPos[myFigure.Dancers.index(aktDancer)]:
    #                     myEndPositions[myDancers.index(aktDancer)] = myFigure.EndPos[myFigure.Dancers.index(aktDancer)]
    #                     myTime[myDancers.index(aktDancer)] = myTime[myDancers.index(aktDancer)] + myFigure.Bars
    #                 else:
    #                     myFlags[myDancers.index(aktDancer)] = False
    #             myAktPositions = myEndPositions
    #
    #         for i in range(len(myDancers)):
    #             if myTime[i] != myBars:
    #                 myFlags[i] = False
    #
    #     return all(myFlags)

print ("...................................\n")

# SA = SimpleFigure("Set Advancing","Set Advancing")
# SA._Bars = 2
# SA._Dancers = ["1m"]
# SA._StartPos = ["1m"]
# SA._EndPos = ["Between 2c"]
#
# DR = SimpleFigure("1HDR", "Half Diagonal Reel on the first diagonal")
# DR._Bars = 4
# DR._Dancers = ["2m", "1l", "1m", "3l"]
# DR._EndPos = ["1m", "ifo3l", "ifo1m", "3l"]
# DR._StartPos = ["3l", "ifo1m", "ifo3l", "1m"]
# DR.writeFigure()
#
# DR2 = SimpleFigure("2HDR", "Half Diagonal Reel back on the first diagonal")
# DR2._Bars = 4
# DR2._Dancers = ["3l", "1m", "1l", "2m"]
# DR2._EndPos = ["1m", "ifo3l", "ifo1m", "3l"]
# DR2._StartPos = ["3l", "ifo1m", "ifo3l", "1m"]
# DR2.writeFigure()
#
# DiaReel = Figure("Diagone_Reel", 'Full Diagonal Reel')
# DiaReel.FigureSeries = [DR, DR2]
# DiaReel.writeFigure()
#
# print('%s' % len(DiaReel))
# print(DiaReel.testFigure())
# print(DiaReel.long_desc)

Reel = Figure('dummy','empty')
Reel.loadFigure('Diagone_Reel')
Reel.StartPos = ['1m', 'b1&2bm', 'b2&3bl', '3l']
Reel.Dancers = ['2m', '1l', '1m', '3l']

print(Reel.long_desc)