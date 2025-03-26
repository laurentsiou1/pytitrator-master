"""Fenêtre Pop up - Demande pour quitter la séquence sur mesure"""

from PyQt5.QtWidgets import QDialog
from graphic.windows.Exit_confirmation_win import Ui_PopUp_Exit_Confirmation

class ExitConfirmationWindow(QDialog, Ui_PopUp_Exit_Confirmation):
    def __init__(self, parent_window):  
        super(ExitConfirmationWindow, self).__init__(parent_window)  # Définit le parent pour garder le lien
        self.setupUi(self) # Charge l'interface graphique de la pop-up
        self.parent_window = parent_window  # Stocke la référence vers la fenêtre principale (CustomSequenceWindow)

        # Connexion des boutons
        self.buttonBox.accepted.connect(self.confirm_exit)  # Si on clique sur "Oui" - Associe la fonction confir_exit
        self.buttonBox.rejected.connect(self.reject)   # Si on clique sur "Non" (ferme juste la pop-up) - fonction reject utilisé a partir de pyQt --> QDialog

    def confirm_exit(self):
        """
        Si l'utilisateur clique sur "Oui" :
        - Arrête la séquence
        - Ferme la fenêtre CustomSequenceWindow
        - Ferme la pop-up de confirmation
        """
        print("Confirmation reçue : arrêt de la séquence et fermeture.")  # DEBUG
        self.parent_window.seq.stop()  # # Arrête la séquence en cours
        self.parent_window.close()  # Ferme la fenêtre de séquence (Custom_sequence_window)
        self.accept()  # Ferme la pop-up de confirmation