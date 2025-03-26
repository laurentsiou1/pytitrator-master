"fenêtre de calibration du pH mètre"

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QDialog
from graphic.windows.phmeter_calib_win import Ui_calibration_window

from subsystems.pHmeter import *
from datetime import datetime

class PhMeterCalibWindow(QDialog, Ui_calibration_window): # Définition de la classe PhMeterCalibWindiw, hérite de QDialog et le fichier python de l'interface créé sur QtDesigner
    def __init__(self, ihm, parent=None): # Le constructeur attend 3 Arguments (self, ihm, et parent=None)
        #Initialisation de la fenêtre
        self.ihm=ihm    # Attribut de l'instance IHM
        super(PhMeterCalibWindow,self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("pH meter calibration") # ajout laurent - on execute SetupUi avant, pour ne pas qui reecrase le truc. 

        # Initialisation des variables
        self.U4=0
        self.U7=0
        self.U10=0
        self.used_pH_buffers=set()

    def setupUi(self, Dialog): # On rapelle que la fenetre "Ph Meter calibration" a été crée et initialement appelé "Dialog"
        Dialog.setObjectName("Dialog") # Ici on le rapelle Dialog, mais c'est redondant je crois...
        Dialog.resize(440, 290)
        # Création de l'interface graphique /!\ ici on ajoutle bouton ok et cancel !!
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        # self.buttonBox.setWindowTitle("test") # test laurent 17.03.2025
        self.buttonBox.setGeometry(QtCore.QRect(190, 220, 231, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel) # Ajout du bouton Ok et Cancel
        self.buttonBox.setObjectName("buttonBox") # de type "buttonBox"
        #print("passage!")

        # Un affichage LCD qui montre la tension en direct du pH-mètre
        self.direct_voltage_mV = QtWidgets.QLCDNumber(Dialog) 
        self.direct_voltage_mV.setGeometry(QtCore.QRect(210, 80, 211, 131))
        self.direct_voltage_mV.setObjectName("direct_voltage_mV")
        self.direct_voltage_mV.setNumDigits(6)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(260, 40, 131, 41))
        self.label.setObjectName("label")
        self.lcdNumber_pH4 = QtWidgets.QLCDNumber(Dialog)
        self.lcdNumber_pH4.setGeometry(QtCore.QRect(30, 50, 71, 51))
        self.lcdNumber_pH4.setObjectName("lcdNumber_pH4")
        self.lcdNumber_pH4.setNumDigits(6)
        self.lcdNumber_pH7 = QtWidgets.QLCDNumber(Dialog)
        self.lcdNumber_pH7.setGeometry(QtCore.QRect(30, 130, 71, 51))
        self.lcdNumber_pH7.setObjectName("lcdNumber_pH7")
        self.lcdNumber_pH7.setNumDigits(6)
        self.lcdNumber_pH10 = QtWidgets.QLCDNumber(Dialog)
        self.lcdNumber_pH10.setGeometry(QtCore.QRect(30, 210, 71, 51))
        self.lcdNumber_pH10.setObjectName("lcdNumber_pH10")
        self.lcdNumber_pH10.setNumDigits(6)
        self.pushButton_pH4 = QtWidgets.QPushButton(Dialog, clicked = lambda: self.saveAndShowVoltage(self.lcdNumber_pH4))
        self.pushButton_pH4.setGeometry(QtCore.QRect(130, 50, 51, 51))
        self.pushButton_pH4.setObjectName("pushButton_pH4")
        self.pushButton_pH7 = QtWidgets.QPushButton(Dialog, clicked = lambda: self.saveAndShowVoltage(self.lcdNumber_pH7))
        self.pushButton_pH7.setGeometry(QtCore.QRect(130, 130, 51, 51))
        self.pushButton_pH7.setObjectName("pushButton_pH7")
        self.pushButton_pH10 = QtWidgets.QPushButton(Dialog, clicked = lambda: self.saveAndShowVoltage(self.lcdNumber_pH10))
        self.pushButton_pH10.setGeometry(QtCore.QRect(130, 210, 51, 51))
        self.pushButton_pH10.setObjectName("pushButton_pH10")
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setGeometry(QtCore.QRect(30, 10, 151, 31))
        self.label_2.setObjectName("label_2")

        self.retranslateUi(Dialog)

        # Connexion des boutons 
        self.buttonBox.accepted.connect(self.validateCal) #lorsqu'on clique sur valider, la calibration est enregsitrée / validé
        self.buttonBox.accepted.connect(self.ihm.phmeter.onCalibrationChange) # Met à jour le phmetre      
        self.buttonBox.accepted.connect(self.ihm.controlPanel.refreshCalibrationText) # Met à jours l'affichage dans le control panel        
        self.buttonBox.accepted.connect(Dialog.accept) # type: ignore
        self.buttonBox.rejected.connect(Dialog.reject) # type: ignore
        
        #self.buttonBox.clicked.connect(self.motherWindow.setOnDirectPH) 
        #pour retrouver le pH en direct quand on revient sur le control pannel 
        
        if self.ihm.phmeter.state=='open': # Affichage de la tension en temps réel
            #activation de l'actualisation de la tension
            #self.phmeter.U_pH.setOnVoltageChangeHandler(self.setOnDirectVoltage)
            #mise sur timer
            self.ihm.timer_display.timeout.connect(self.setOnDirectVoltage)  #remettre timer1s sinon - Met à jours l'affichage de la tension 
        
        #rajouter une fonction à la fermeture de la fenetre pour desactiver les actions sur le timer

        #affichage de la tension déjà affichée sur le panneau de contrôle
        #if self.phmeter.getIsOpen():
            #U=self.phmeter.U_pH.getVoltage()  #valeur actuelle de tension
            #self.direct_voltage_mV.display(U)
    
    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label.setText(_translate("Dialog", "tension (mV) en direct"))
        self.pushButton_pH10.setText(_translate("Dialog", "pH10"))
        self.pushButton_pH7.setText(_translate("Dialog", "pH7"))
        self.pushButton_pH4.setText(_translate("Dialog", "pH4"))
        self.label_2.setText(_translate("Dialog", "Tensions enregistrées"))

    def setOnDirectVoltage(self): #, ch, voltage): # Met à jours l'affichage de la tensio
        self.direct_voltage_mV.display(1000*self.ihm.phmeter.currentVoltage)

    def saveAndShowVoltage(self, screen): #sreen est un objet QLCDNumber - # Enregistrement des valeurs de calib - Stocke et affiche la tension enregistrée pour chaque pH.
        U=self.ihm.phmeter.currentVoltage
        print("save voltage")
        if screen==self.lcdNumber_pH4:
            self.U4=U
            self.used_pH_buffers.add(4)
        if screen==self.lcdNumber_pH7:
            self.U7=U
            self.used_pH_buffers.add(7)
        if screen==self.lcdNumber_pH10:
            self.U10=U
            self.used_pH_buffers.add(10)
        print("voltage=",U)
        screen.display(U)

    def validateCal(self): #pH_buffers est un tuple contenant les valeurs de pH des tampons   
        pH_buffers=sorted(list(self.used_pH_buffers))
        self.used_pH_buffers = pH_buffers
        #print("pH buffers : ",type(pH_buffers),pH_buffers)
        dt = datetime.now()
        if pH_buffers == [4]:
            u_cal = [self.U4]
        elif pH_buffers == [7]:
            u_cal = [self.U7]
        elif pH_buffers == [4,7]:
            u_cal = [self.U4, self.U7]
            print("calib 2 pts")
        elif pH_buffers == [4,7,10]:
            u_cal = [self.U4, self.U7, self.U10]
            print("calib 3 pts")
        else:
            print("This type of calibration is not suppported")
        (a,b)=PHMeter.computeCalCoefs(self.ihm.phmeter,u_cal,pH_buffers) #calcul des coefficients de calib
        PHMeter.saveCalData(self.ihm.phmeter, dt.strftime("%m/%d/%Y %H:%M:%S"), pH_buffers, u_cal, (a,b)) #enregistrer dans le fichier

"""
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = PhMeterCalibWindow()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
"""

"""
# boucle pour tester ce programme uniquement
if __name__ == "__main__":
    from controlPannel import ControlPannel
    try: #si le pH mètre est connecté
        ch = VoltageInput()
        ch.setDeviceSerialNumber(432846)
        ch.setChannel(0)
        ch.openWaitForAttachment(1000)
        ch.setOnVoltageChangeHandler(PHMeter.doOnVoltageChange)

        phm = PHMeter(ch)
        phm.configure_pHmeter()
        print("pH mètre connecté")
    except: #pH mètre non connecté
        phm = 'pH mètre'
        print("pH mètre non connecté")
    finally:    
        import sys
        app = QtWidgets.QApplication(sys.argv)
        Dialog = QtWidgets.QDialog()
        mwindow = ControlPannel()
        ui = PhMeterCalibWindow(phm, mwindow)
        ui.setupUi(Dialog)
    try:
        #connection de la fenêtre avec le pH-mètre
        ui.phmeter.U_pH.setOnVoltageChangeHandler(ui.setOnDirectPH)
    except:
        pass
    finally:
        Dialog.show()        
        #print("show")
        sys.exit(app.exec_())
"""

if __name__ == "__main__":
    
    #spectro
    od = OceanDirectAPI()
    device_count = od.find_usb_devices() # 1 si appareils détectés
    device_ids = od.get_device_ids()
    #device_count = len(device_ids)
    id=device_ids[0]
    spectro = od.open_device(id) #crée une instance de la classe Spectrometer
    adv = Spectrometer.Advanced(spectro)
    spectro_unit=AbsorbanceMeasure(od,spectro)

    #pHmètre
    U_pH = VoltageInput()
    ph_meter = PHMeter(U_pH)

    #Interface
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    cp = ControlPannel(ph_meter,spectro_unit)
    ui = PhMeterCalibWindow(ph_meter, cp)
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
