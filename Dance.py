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

def printCrip(myCrips):
    if type(myCrips) != type([]):
        print(myCrips)
    else:
        if len(myCrips) == 0:
            pass
        elif type(myCrips[0]) != type([]):
            print(myCrips[0])
            if len(myCrips) > 1:
                printCrip(myCrips[1:])
        else:
            for myCrip in myCrips:
                printCrip(myCrip)
def showCrips(myFig, myDF):
    printCrip(myFig.getCrips(myDF))

