import json
import DanceFloor as DF
import Figures


class ParalelFigure(Figures.SimpleFigure):
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
            if type(FigData['FigureSeries']['List']) == list
                for i in range(len(FigData['FigureSeries']['List'][0])):
                    self.FigureSeries['List'].append(Figures.SimpleFigure(FigData['FigureSeries']['List'][0][i], ''))
                    self.FigureSeries['List'][i].loadFigure(FigData['FigureSeries']['List'][0][i])
                    self.FigureSeries['Anchor'].append(FigData['FigureSeries']['Anchor'][0][i])
                    self.FigureSeries['List'][i].Anchor = \
                        (FigData['FigureSeries']['Anchor'][0][i][0], FigData['FigureSeries']['Anchor'][0][i][1])
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
            FigData['FigureSeries']['List'] = [[]]
            FigData['FigureSeries']['Anchor'] = [[]]
            for i in range(self.FigureSeries['List']):
                FigData['FigureSeries']['List'][0][i] = self.FigureSeries['List'][i].name()
                FigData['FigureSeries']['Anchor'][0][i] = self.FigureSeries['Anchor'][i]

            with open('E:/Git/DanceCreator/Figures/' + self.name + '.json', 'w') as f:
                json.dump(FigData, f, sort_keys=True)
        else:
            # self.FigureSeries['List'][0].writeFigure()

    def DanceMove(self):
        myDanceMove = []
        for i in range(len(self.FigureSeries['List'])):
            myDanceMove.append(self.FigureSeries['List'][i].DanceMove())

        for j in range(len(myDanceMove)):
            myDancers = []
            for i in range(len(myDanceMove[j]['Dancers'])):
                myPos = self.addPositions([self.Anchor,  myDanceMove[j]['Dancers'][i]])
                myDancers.append(myPos)
            myDanceMove[j]['Dancers'] = myDancers
        return myDanceMove

