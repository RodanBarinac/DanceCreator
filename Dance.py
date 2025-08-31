from SimpleFigure import SimpleFigure
from ComplexFigure import ComplexFigure
import json
import os

def getFigure(Filename, Anchor = [0,0]):

    with open(os.getcwd()+'/Figures/' + Filename + '.json', 'r') as f:
        FigData = json.load(f)

    if 'FigureList' in FigData.keys():
        myFig = ComplexFigure(Filename, Anchor)
    else:
        myFig = SimpleFigure(Filename, Anchor)

    return myFig
