from SimpleFigure import SimpleFigure
from KomplexFigure import KomplexFigure
import json

def getFigure(Filename, Anchor = [0,0]):

    with open('E:/Git/DanceCreator/Figures/' + Filename + '.json', 'r') as f:
        FigData = json.load(f)

    if 'FigureList' in FigData.keys():
        myFig = KomplexFigure(Filename, Anchor)
    else:
        myFig = SimpleFigure(Filename, Anchor)

    return myFig
