import Dance
import DanceFloor as DF


Floor = DF.DanceFloor('Marrie\'s Wedding',3)
print(Floor)
#print('### First 8 Bars ###')
Marrie = Dance.getDance( "Marries Wedding_all")
Dance.showCrips(Marrie, Floor)
Floor = Marrie.DanceMove(Floor)
print(Floor)