"Program to execute for launching application"

from PyQt5 import QtWidgets
from IHM import IHM # parce qu'il y a tout dans IHM pour executer le programme 

#Lancement application
import sys # ici, j'ai l'impression que c'est toujours la meme chose... comme dans les __main__ 
qApp = QtWidgets.QApplication(sys.argv)
app=IHM() # Création de l'interface principale
app.openControlPanel() # Ouvre la fenêtre de contrôle 
sys.exit(qApp.exec_()) # Boucle d'évenement Qt

#Modification de laulau le 12/03