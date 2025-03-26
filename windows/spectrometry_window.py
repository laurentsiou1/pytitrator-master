"Classe de la fenêtre pour gestion spectromètre et lampe"

from lib.oceandirect.OceanDirectAPI import OceanDirectError, OceanDirectAPI, Spectrometer as Sp
from lib.oceandirect.od_logger import od_logger
from subsystems.absorbanceMeasure import AbsorbanceMeasure
import subsystems.processing as proc

from PyQt5 import QtCore, QtGui, QtWidgets
from graphic.windows.spectrometer_win import Ui_spectro_config
from PyQt5.QtWidgets import QDialog
import pyqtgraph as pg # Bibliothèque de graphiques scientifiques en temps réel - pas utilisé ici, askip

_translate = QtCore.QCoreApplication.translate # fonction Qt, pour la traduction des chaines

from configparser import ConfigParser
import os
from pathlib import Path

path = Path(__file__)
ROOT_DIR = path.parent.absolute()
app_default_settings = os.path.join(ROOT_DIR, "../config/app_default_settings.ini") # de la même maniere que d'habitude, on récupère le fichier "app_default_settings"

class SpectrometryWindow(QDialog,Ui_spectro_config): # Classe principale, héride de QDialog et Ui_spectro_config

    def __init__(self, ihm, parent=None):
        super(SpectrometryWindow,self).__init__(parent)
        self.setupUi(self)
        self.spectro_unit=ihm.spectro_unit
        self.ihm=ihm
    
        self.refreshing_rate=1000 #ms

        #spectro connecté       -- Certains spectro ne supporte pas le "Electric Dark Correction"
        if self.spectro_unit.state=='open': # Si le spectro est bien connecté
            self.shutter.setChecked(self.spectro_unit.shutter.getState())   # case Checkbox du shutter, pour l'activer ou non - Affiche l'état du shutter
            self.NLcorr_box.setChecked(self.spectro_unit.device.get_nonlinearity_correction_usage()) # CheckBox Correction non-linéaire activée ?
            self.NLcorr_box.clicked.connect(self.change_NLcorr_state) # CheckBox de la "Non Linearity Correction" --- Change état NL quand on clique
            try:
                ed=self.spectro_unit.device.get_electric_dark_correction_usage() # Essaie de lire état de la non linéarité
                self.EDcorr_box.setChecked(self.spectro_unit.device.get_electric_dark_correction_usage())
                self.EDcorr_box.clicked.connect(self.change_EDcorr_state)
            except: #feature not available for OceanST or OceanSR spectrometers
                self.EDcorr_box.setDisabled(True)    # Certains modèles ne supportent pas ED
            self.lambdas=self.spectro_unit.wavelengths # Récupère les longueurs d'ondes

            #Affichage des paramètres selon valeurs actuelles du spectro
            device = "device model : "+self.spectro_unit.model
            self.label_model.setText(device)
            if self.spectro_unit.model=='OceanSR6':  # Fixe les bornes possibles de Tint en fonction du modèle --- ICI SR6
                self.Tint.setMinimum(self.spectro_unit.device.get_minimum_integration_time()//1000+1) #milliseconds
                self.Tint.setMaximum(self.spectro_unit.device.get_maximum_integration_time()//1000)
            if self.spectro_unit.model=='OceanST':  # Fixe les bornes possibles de Tint en fonction du modèle --- ICI OceanST
                self.Tint.setMinimum(self.spectro_unit.device.get_minimum_integration_time()//1000+1) #milliseconds
                self.Tint.setMaximum(self.spectro_unit.device.get_maximum_integration_time()//1000)
            # Initialise valeurs affichées dans la fenêtre
            self.Tint.setProperty("value", self.spectro_unit.t_int)  
            self.avg.setProperty("value", self.spectro_unit.averaging)
            self.acquisition_delay_display.setText(_translate("Dialog", "acquisition delay : %0.2f seconds"% float(self.spectro_unit.acquisition_delay/1000) ))

            #connexions
            self.Tint.valueChanged.connect(self.update_integration_time) # Définition du bouton Qspinbox pour le tenps d'intégration
            self.avg.valueChanged.connect(self.update_averaging) # Définition du bouton Qspinbox pour le moyennage
            self.shutter.clicked.connect(self.changeShutterState) # Définition du bouton du shutter associé la la fonction "changeShutterState"
            #enregistrement
            self.refresh_background.clicked.connect(self.spectro_unit.acquire_background_spectrum) # Bouton "refresh" pour le spectre backgraound associé à la fonction "acquire_background_spectrum"
            self.refresh_background.clicked.connect(self.refreshShutterState) # ce meme bouton est associté à la fonction de "refreshSuhtterState"
            self.refresh_ref.clicked.connect(self.spectro_unit.acquire_ref_spectrum) # Bouton "refresh" pour le spectre référence
            self.refresh_ref.clicked.connect(self.refreshShutterState) # idem  reassocié à la fonction "refreshShutterState"
            
            #actualisation des spectres périodiquement
            self.spectro_unit.timer.timeout.connect(self.refreshScreen)  # Rafraîchissement périodique (via timer)

            #Clic sur OK
            self.buttonBox.accepted.connect(self.updateDefaultParameters) # Sauvegarde si clic sur "OK"
    
    def refreshScreen(self):  
        bgd=(self.spectro_unit.active_background_spectrum!=None) # Background dispo ?
        ref=(self.spectro_unit.active_ref_spectrum!=None)  # Référence dispo ?
        
        #Actu des graphes
        #Intensity - Affiche intensité
        self.intensity_plot=self.intensity_widget.plot([0],[0],pen="r",clear = True)
        self.intensity_plot.setData(self.lambdas,self.spectro_unit.current_intensity_spectrum)
        if bgd: #background enregistré
            a=self.background_widget.plot([0],[0],clear = True)
            self.dark_plot=a
            self.dark_plot.clear()
            self.dark_plot.setData(self.lambdas,self.spectro_unit.active_background_spectrum) 
        if ref: #réf enregistrée
            self.ref_plot=self.reference_widget.plot([0],[0],pen="g",clear = True)
            self.ref_plot.setData(self.lambdas,self.spectro_unit.active_ref_spectrum)
        if bgd*ref: #absorbance
            self.abs_plot=self.absorbance_widget.plot([0],[0],pen="y",clear = True)
            self.abs_plot.setData(self.lambdas,self.spectro_unit.current_absorbance_spectrum)
            delay_sec=float(self.spectro_unit.Aproc_delay/1000) 
            self.absorbance_processing_delay_display.setText("Absorbance computation delay : %f seconds" %delay_sec)

        #actu des delays
        self.acquisition_delay_display.setText(_translate("Dialog", "acquisition delay : %0.2f seconds"% float(self.spectro_unit.acquisition_delay/1000) ))
        self.recording_delay_display.setText("processing delay : %f seconds" %self.spectro_unit.Irec_time)
        self.averaging_delay_display.setText("averaging delay : %f seconds" %self.spectro_unit.avg_delay)          
        self.refresh_rate_display.setText(_translate("Dialog", "période de rafraîchissement : %0.2f seconds"% float(self.spectro_unit.refresh_rate/1000) ))   

        #shutter
        self.refreshShutterState()

    def changeShutterState(self): # Change Etat shutter 
        self.spectro_unit.changeShutterState()
        self.refreshShutterState()

    def refreshShutterState(self): # Raffraichissement de l'état du shutter
        self.shutter.setChecked(not(self.spectro_unit.get_shutter_state()))
        
    def change_NLcorr_state(self): # Change l'état de la correction de la non linéarité
        state=not(self.spectro_unit.device.get_nonlinearity_correction_usage())
        self.spectro_unit.device.set_nonlinearity_correction_usage(state)
    
    def change_EDcorr_state(self): # Change l'état du Electric Dark 
        state=not(self.spectro_unit.device.get_electric_dark_correction_usage())
        self.spectro_unit.device.set_electric_dark_correction_usage(state)
    
    def update_integration_time(self): # Update du temps d'intégration
        t_ms=self.Tint.value()
        t_us=1000*t_ms #us
        self.spectro_unit.device.set_integration_time(t_us)
        self.spectro_unit.t_int=t_ms
        self.spectro_unit.update_acquisition_delay()

    def update_averaging(self): # update du moyennage - ? ? ? ? ? - différence entre moyenenr les spectre et ca ? ?
        a=self.avg.value()
        self.spectro_unit.device.set_scans_to_average(a)
        self.spectro_unit.averaging=a
        self.spectro_unit.update_acquisition_delay()

    def updateDefaultParameters(self): # update les pparamètres par défauts pour les écrire dans le fichier "app_default_settings"
        parser = ConfigParser()
        parser.read(self.ihm.app_default_settings)
        parser.set('spectrometry', 'model', str(self.spectro_unit.model))
        parser.set('spectrometry', 'tint', str(self.spectro_unit.t_int))
        parser.set('spectrometry', 'avg', str(self.spectro_unit.averaging))
        file = open(self.ihm.app_default_settings,'w')
        parser.write(file)
        file.close()

if __name__ == "__main__":
    logger = od_logger()
    od = OceanDirectAPI()
    device_count = od.find_usb_devices() #nb d'appareils détectés
    device_ids = od.get_device_ids()
    if device_ids!=[]:
        id=device_ids[0]
        try:
            spectro = od.open_device(id) #crée une instance de la classe Spectrometer
            adv = Sp.Advanced(spectro)
            spectroIsConnected=True
            print("Spectro connecté")
        except:
            spectro=None #on crée dans tous les cas un objet Spectrometer
            adv = None
            spectroIsConnected=False
            print("Ne peut pas se connecter au spectro numéro ", id)
            pass
    else:
        spectro=None #on crée dans tous les cas un objet Spectrometer
        adv = None #Sp.Advanced(spectro)
        spectroIsConnected=False
        print("Spectro non connecté")
    #print("Nombre d'appareils OceanDirect détectés : ", device_count)
    #print("ID spectros: ", device_ids)

    spectrometry_unit=AbsorbanceMeasure(od, spectro)

    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = SpectrometryWindow(spectrometry_unit)
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
