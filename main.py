"Program to execute for launching application"

from PyQt5 import QtWidgets
from IHM import IHM

#Lancement application
import sys
qApp = QtWidgets.QApplication(sys.argv)
app=IHM() # Création de l'interface principale
app.openControlPanel() # Ouvre la fenêtre de contrôle 
sys.exit(qApp.exec_()) # Boucle d'évenement Qt