import json
import DanceFloor as DF
import Figures

class SerialFigure(Figures.SimpleFigure):
    FigureSeries = {}
    desc = ''

    def __init__(self, name, desc):
        super().__init__(name, desc)
        self.FigureSeries['List'] = []
        self.FigureSeries['Anchor'] = []

    def loadFigure(self, Filename):
        with open('E:/Git/DanceCreator/Figures/' + Filename + '.json', 'r') as f:
            FigData = json.load(f)

        self.name = FigData['Name']
        self.desc = FigData['Desc']

        self.FigureSeries['List'] = []
        self.FigureSeries['Anchor'] = []

        if 'FigureSeries' in FigData:
            for i in range(len(FigData['FigureSeries']['List'])):
                self.FigureSeries['List'].append(Figures.SimpleFigure(FigData['FigureSeries']['List'][i], ''))
                self.FigureSeries['List'][i].loadFigure(FigData['FigureSeries']['List'][i])
                self.FigureSeries['Anchor'].append(FigData['FigureSeries']['Anchor'][i])
                self.FigureSeries['List'][i].Anchor = \
                    (FigData['FigureSeries']['Anchor'][i][0], FigData['FigureSeries']['Anchor'][i][1])
        else:
            # print(FigData)
            # self.FigureSeries['List'].append(Figures.SimpleFigure(self.name, ''))
            # self.FigureSeries['List'][0].loadFigure()
            # self.FigureSeries['Anchor'].append((0, 0))

    def writeFigure(self):

        if len(self.FigureSeries['List']) > 1:
            FigData = {
                'Name': self.name,
                'Desc': self.desc,
                }
            FigData['FigureSeries'] = {}
            FigData['FigureSeries']['List'] = []
            FigData['FigureSeries']['Anchor'] = []
            for i in range(self.FigureSeries['List']):
                FigData['FigureSeries']['List'][i] = self.FigureSeries['List'][i].name()
                FigData['FigureSeries']['Anchor'][i] = self.FigureSeries['Anchor'][i]

            with open('E:/Git/DanceCreator/Figures/' + self.name + '.json', 'w') as f:
                json.dump(FigData, f, sort_keys=True)
        else:
            # self.FigureSeries['List'][0].writeFigure()

    # def testFigureSeries(self):
    #     myStartPos = self.FigureSeries['List'][0].StartPos
    #     myDF = DF.DanceFloor(self.name)
    #     for i in range(len(myStartPos)):
    #         myDF.addDancer(i, myStartPos[i])
    #
    #     for i in range(len(self.FigureSeries['List'])):
    #         myDF.doDanceMove(self.FigureSeries['List'][i].DanceMove())
    #
    #     myFlag = True
    #     myEndPos = myDF.getDanceFloorMap().values()
    #     for i in range(len(myStartPos)):
    #         if not (myStartPos[i] in myEndPos):
    #             myFlag = False
    #
    #     return myFlag

    def DanceMove(self):
        myDanceMove = []
        for i in range(len(self.FigureSeries['List'])):
            myDanceMove.append(self.FigureSeries['List'][i].DanceMove())

        for j in range(len(myDanceMove)):
            myDancers = []
            for i in range(len(myDanceMove[j]['Dancers'])):
                myPos = self.addPositions([self.Anchor,myDanceMove[j]['Dancers'][i]])
                myDancers.append(myPos)
            myDanceMove[j]['Dancers'] = myDancers
        return myDanceMove

    def getCrips(self, myDanceFloorMap, globAnchor = (0,0)):
        myCrips = []
        finalCript= []

        myDanceFloor = DF.DanceFloor('getCrips_' + self.name, int(len(myDanceFloorMap)/2))
        myDanceFloor.setDanceFloorMap(myDanceFloorMap)

        for i in range(len(self.FigureSeries['List'])):
            myPos = self.addPositions([globAnchor,self.Anchor])
            myCrips.append(self.FigureSeries['List'][i].getCrips(myDanceFloor.getDanceFloorMap(), myPos))
            myDanceMove = self.FigureSeries['List'][i].DanceMove()
            myDancers = []
            for j in range(len(myDanceMove['Dancers'])):
                myPos = self.addPositions([globAnchor, self.Anchor, myDanceMove['Dancers'][j]])
                myDancers.append(myPos)
            myDanceMove['Dancers'] = myDancers

            myDanceFloor.doDanceMove(myDanceMove, 'Seriel')

        for i in range(len(myCrips)):
            if len(myCrips[i]):
                for j in range(len(myCrips[i])):
                    finalCript.append(myCrips[i][j])
            else:
                finalCript.append(myCrips[i])
        return finalCript