from SimpleFigure import SimpleFigure
import json
import os

def getDance(Filename):
    from ComplexFigure import ComplexFigure  # Lazy Import, um zirkulären Import zu vermeiden

    myDance = ComplexFigure(os.path.join(os.getcwd(), 'Dances', Filename + '.json'), [0,0])
    myDance.loadFigure()

    return myDance

def getFigure(Filename, Anchor = [0,0], Addons = []):
    from ComplexFigure import ComplexFigure  # Lazy Import, um zirkulären Import zu vermeiden

    with open(os.path.join(os.getcwd(), 'Figures', Filename + '.json'), 'r') as f:
        FigData = json.load(f)

    if 'FigureList' in FigData.keys():
        myFig = ComplexFigure(Filename, Anchor)
        myFig.loadFigure()
    else:
        myFig = SimpleFigure(Filename, Anchor, Addons)

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
