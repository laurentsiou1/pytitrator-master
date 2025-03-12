# main_window.py

from configparser import ConfigParser
import os
from pathlib import Path

from PyQt5.QtWidgets import QMainWindow, QApplication #, QWidget, QLabel, QLineEdit, QPushButton
from graphic.windows.control_panel_win import Ui_ControlPanel
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRect, QPoint
#from PyQt5.QtGui import QPixmap
from graphic import display

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

from subsystems.pHmeter import *
from subsystems.absorbanceMeasure import AbsorbanceMeasure
from subsystems.dispenser import *
from subsystems.peristalticPump import *

from Phidget22.Devices.VoltageInput import VoltageInput
from Phidget22.Devices.DigitalInput import DigitalInput
from Phidget22.Devices.DigitalOutput import DigitalOutput
from Phidget22.Devices.Stepper import Stepper
from lib.oceandirect.OceanDirectAPI import Spectrometer as Sp, OceanDirectAPI
from lib.oceandirect.od_logger import od_logger

#chemin du repertoire _internal lors du lancement de l'exe
path_internal=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
green_led_path=os.path.join(path_internal, "graphic/images/green-led-on.png")
red_led_path=os.path.join(path_internal, "graphic/images/red-led-on.png")

class ControlPanel(QMainWindow, Ui_ControlPanel):
    def __init__(self, ihm, parent=None):
        
        #appareils
        self.ihm=ihm
        self.phmeter=ihm.phmeter
        self.spectro_unit=ihm.spectro_unit
        self.dispenser=ihm.dispenser
        self.peristaltic_pump=ihm.peristaltic_pump
        self.circuit=ihm.circuit
        
        #graphique
        super(ControlPanel,self).__init__(parent)
        self.setupUi(self)
        
        if os.path.exists(green_led_path):  #lors d'un lancement avec le dossier d'executable
            self.pixmap_green=QtGui.QPixmap(green_led_path)
            self.pixmap_red=QtGui.QPixmap(red_led_path)
        else:
            self.pixmap_green=QtGui.QPixmap("graphic/images/green-led-on.png")
            self.pixmap_red=QtGui.QPixmap("graphic/images/red-led-on.png")
        
        #Paramètres affichés
        self.label_instrument_SN.setText("instrument S/N : "+self.ihm.instrument_id)
        parser = ConfigParser()
        parser.read(ihm.app_default_settings)
        #menus déroulants
        self.electrode_box.appendPlainText(str(parser.get('electrode', 'default')))
        self.stab_step.setValue(float(parser.get('phmeter', 'epsilon')))
        self.stab_time.setValue(int(parser.get('phmeter', 'delta')))
        #Spectromètre
        self.shutter.setChecked(True)   #shutter is closed before connecting spectrometer
        #Peristaltic pump
        self.connect_disconnect_circuit.setText("Connect")
        self.start_stop_pump_button.setText("Start")
        self.pump_speed.setTickPosition(int(parser.get('pump', 'speed_scale')))
        
        #Pousse seringues
        self.reagentA.setText(self.dispenser.syringe_A.reagent)   #string
        self.reagentB.setText(self.dispenser.syringe_B.reagent)
        self.reagentC.setText(self.dispenser.syringe_C.reagent)
        self.Ca.setText(str(self.dispenser.syringe_A.concentration))   #float
        self.Cb.setText(str(self.dispenser.syringe_B.concentration))
        self.Cc.setText(str(self.dispenser.syringe_C.concentration))
        self.levelbarA.setProperty("value",str(self.dispenser.syringe_A.level_uL))   #int
        self.levelbarB.setProperty("value",str(self.dispenser.syringe_B.level_uL))
        self.levelbarC.setProperty("value",str(self.dispenser.syringe_C.level_uL))
        self.levelA_uL.setText(str(self.dispenser.syringe_A.level_uL))  
        self.levelB_uL.setText(str(self.dispenser.syringe_B.level_uL))
        self.levelC_uL.setText(str(self.dispenser.syringe_C.level_uL))

        if self.dispenser.syringe_A.use==False:
            self.syringeA.setDisabled(True)   #bool
            self.reagentA.setDisabled(True)
            self.Ca.setDisabled(True)
            self.levelbarA.setDisabled(True)
            self.levelA_uL.setDisabled(True)
            self.added_A_uL.setDisabled(True)
        if self.dispenser.syringe_B.use==False:
            self.syringeB.setDisabled(True)   #bool
            self.reagentB.setDisabled(True)
            self.Cb.setDisabled(True)
            self.levelbarB.setDisabled(True)
            self.levelB_uL.setDisabled(True)
            self.added_B_uL.setDisabled(True)
        if self.dispenser.syringe_C.use==False:
            self.syringeC.setDisabled(True)   #bool
            self.reagentC.setDisabled(True)
            self.Cc.setDisabled(True)
            self.levelbarC.setDisabled(True)
            self.levelC_uL.setDisabled(True)
            self.added_C_uL.setDisabled(True)
        
        self.update_lights()
        self.led_spectro.setScaledContents(True)
        self.led_phmeter.setScaledContents(True)
        self.led_disp.setScaledContents(True)
        self.led_pump.setScaledContents(True)
        self.led_ev_circuit.setScaledContents(True)

        #self.led_spectro.resize(pixmap.width(),pixmap.height())
        #self.setCentralWidget(self.led_spectro)
        #self.resize(pixmap.width(), pixmap.height())

        #ajout
        (w,h)=(self.graphic_tabs.geometry().width(),self.graphic_tabs.geometry().height())
        rect=QRect(0,0,w-5,h-32)
        self.Abs_direct = pg.PlotWidget(self.tab1)
        self.Abs_direct.setGeometry(rect)
        self.Abs_direct.setObjectName("Abs_direct")
        self.Spectrum_direct = pg.PlotWidget(self.tab_2)
        self.Spectrum_direct.setGeometry(rect)
        self.Spectrum_direct.setObjectName("Spectrum_direct")

        #connexions
        self.electrode_box.textChanged.connect(self.update_electrode_model)
        self.connect_phmeter.clicked.connect(self.link_pHmeter2IHM)
        self.cal_button.clicked.connect(self.ihm.openCalibWindow)

        self.connect_disconnect_spectro_button.clicked.connect(self.connect_disconnect_spectrometer)
        self.spectro_settings.clicked.connect(self.OnClick_spectro_settings)
        
        self.connect_syringe_pump.clicked.connect(self.connectSyringePump)
        self.open_syringe_panel.clicked.connect(self.ihm.openDispenserWindow)
        
        self.connect_disconnect_circuit.clicked.connect(self.connexionChange_circuit)
        self.pump_speed.valueChanged.connect(self.update_pump_speed)
        self.ev0_state.clicked.connect(self.ev0_changeState)
        self.ev1_state.clicked.connect(self.ev1_changeState)
        #self.fill_water.clicked.connect(self.fillWater)
        #self.clean_empty.clicked.connect(self.cleanAndEmpty)
        
        self.connect_all_devices.clicked.connect(self.connectAllDevices)
        self.ihm.timer_display.timeout.connect(self.refresh_screen)
        
        self.configure_sequence.clicked.connect(self.ihm.openConfigWindow)
        self.action_edit_folder.triggered.connect(self.ihm.openSettingsWindow)    #choix dossier
        self.save_button.clicked.connect(self.ihm.createDirectMeasureFile)  #deux façons de sauver les données
        self.action_save.triggered.connect(self.ihm.createDirectMeasureFile) 
        self.action_open_settings.triggered.connect(self.ihm.openSettingsWindow) #config des seringues

        self.close_all.clicked.connect(self.ihm.close_all_devices)
        self.close_all.clicked.connect(self.update_lights)
        self.close_all.clicked.connect(self.clear_IHM)

    def select_pixmap(self, state):
        if state=='open':
            px=self.pixmap_green
        elif state=='closed':
            px=self.pixmap_red
        elif state==['closed','closed','closed']:
            px=self.pixmap_red
        else:
            px=self.pixmap_green
        return px

    def update_lights(self):
        self.led_spectro.setPixmap(self.select_pixmap(self.ihm.spectro_unit.state))
        self.led_phmeter.setPixmap(self.select_pixmap(self.ihm.phmeter.state))
        self.led_disp.setPixmap(self.select_pixmap(self.ihm.dispenser.state))
        self.led_pump.setPixmap(self.select_pixmap(self.ihm.peristaltic_pump.state))
        self.led_ev_circuit.setPixmap(self.select_pixmap(self.ihm.circuit.ev0.channel_state))

    def refresh_screen(self):
        if self.ihm.phmeter.state=='open':
            self.stab_time.setProperty("value", self.ihm.phmeter.stab_time)
            self.stab_step.setProperty("value", self.ihm.phmeter.stab_step)
        if self.ihm.spectro_unit.state=='open':
            self.refreshShutterState()
        #if self.ihm.peristaltic_pump.state=='open':
            #self.pump_speed.setProperty("value", self.ihm.peristaltic_pump.mean_voltage)
            #self.pump_speed.setValue()

    ##Méthodes multi instruments
    def connectAllDevices(self):
        self.connectCircuit()
        self.link_pHmeter2IHM()
        self.connectSyringePump()
        self.spectro_unit.connect()
        if self.spectro_unit.state=='open':
            self.led_spectro.setPixmap(self.pixmap_green)
            self.link_spectro2IHM()
            self.spectro_unit.acquire_background_spectrum()
            self.spectro_unit.acquire_ref_spectrum()

                                
                                ### Méthodes pour le pH mètre
    
    def link_pHmeter2IHM(self):
        if self.phmeter.state=='closed':
            self.phmeter.connect()
        if self.phmeter.state=='open':
            #affichage des données de calibration
            self.refreshCalibrationText()
            self.led_phmeter.setPixmap(self.pixmap_green)
            #pH en direct
            self.direct_pH.display(self.phmeter.currentPH) #pH instantané
            self.phmeter.U_pH.setOnVoltageChangeHandler(self.displayDirectPH) #à chaque changement
            self.phmeter.activateStabilityLevel()
            self.phmeter.stab_timer.timeout.connect(self.refresh_stability_level)
            self.update_stab_time()
            self.stab_time.valueChanged.connect(self.update_stab_time)
            self.update_stab_step()
            self.stab_step.valueChanged.connect(self.update_stab_step)
            #self.load_calibration_button.clicked.connect(self.load_calibration)
    
    def update_electrode_model(self):
        self.phmeter.electrode=self.electrode_box.toPlainText()

    def update_stab_time(self):
        self.phmeter.stab_time=self.stab_time.value()
    
    def update_stab_step(self):
        self.phmeter.stab_step=self.stab_step.value()

    def clear_IHM(self):
        #pH meter
        self.direct_pH.display(None)
        self.calib_text_box.clear()
        self.stabilisation_level.setProperty("value", 0)
        #Spectro

    def displayDirectPH(self,ch,voltage): #arguments immuables
        self.phmeter.currentVoltage=voltage        
        pH = volt2pH(self.phmeter.a,self.phmeter.b,voltage)
        self.phmeter.currentPH=pH #actualisation de l'attribut de la classe pHmeter
        self.direct_pH.display(pH)
    
    def refresh_stability_level(self):
        self.stabilisation_level.setProperty("value", self.phmeter.stab_purcent)
        self.stability_label.setText(str(self.phmeter.stab_purcent)+"%")

    """def load_calibration(self):
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select File', "config")
        #print(filepath)
        self.phmeter.load_calibration(filepath)
        self.phmeter.getCalData()
        self.refreshCalibrationText()"""
    
    def refreshCalibrationText(self):
        self.calib_text = ("Current calibration data:\npH meter : "+str(self.phmeter.CALmodel)
        +"\nelectrode : "+str(self.phmeter.CALelectrode)+"\ndate: "+str(self.phmeter.CALdate)
        +"\npH buffers: "+str(self.phmeter.CALtype)+"\nRecorded voltages:\nU4="+str(self.phmeter.U1)
        +"V\nU7="+str(self.phmeter.U2)+"V\nU10="+str(self.phmeter.U3)+"V\ncoefficients U=a*pH+b\na="
        +str(self.phmeter.a)+"\nb="+str(self.phmeter.b))
        self.calib_text_box.clear()
        self.calib_text_box.appendPlainText(self.calib_text)


                                        ### Methods for Spectrometer
    def connect_disconnect_spectrometer(self):
        if self.spectro_unit.state=='closed':
            self.spectro_unit.connect()
        elif self.spectro_unit.state=='open':
            self.spectro_unit.close(self.spectro_unit.id)
        self.update_connexion_state()
        
    def update_connexion_state(self):
        """Updates light indicator and Connexion button"""
        if self.spectro_unit.state=='closed':
            self.led_spectro.setPixmap(self.pixmap_red)
            self.connect_disconnect_spectro_button.setText("Connect")
        elif self.spectro_unit.state=='open':
            self.led_spectro.setPixmap(self.pixmap_green)
            self.connect_disconnect_spectro_button.setText("Disconnect")

    def OnClick_spectro_settings(self):
        if self.spectro_unit.state=='closed':
            self.connect_spectrometer()
        self.ihm.openSpectroWindow()

    def connect_spectrometer(self):
        self.spectro_unit.connect()
        if self.spectro_unit.state=='open':
            self.link_spectro2IHM()
        self.update_connexion_state()
    
    def changeShutterState(self):
        self.spectro_unit.changeShutterState()
        self.refreshShutterState()
    
    def refreshShutterState(self):
        self.shutter.setChecked(not(self.spectro_unit.get_shutter_state()))

    def updateSpectrum(self):
        if self.spectro_unit.state == 'open' and self.spectro_unit.current_intensity_spectrum!=None:   #intensité direct
            self.intensity_direct_plot=self.Spectrum_direct.plot([0],[0],clear = True)
            self.intensity_direct_plot.setData(self.lambdas,self.spectro_unit.current_intensity_spectrum)
        if self.spectro_unit.active_ref_spectrum!=None:
            self.reference_plot=self.Spectrum_direct.plot([0],[0],pen='g')
            self.reference_plot.setData(self.lambdas,self.spectro_unit.active_ref_spectrum)
        if self.spectro_unit.active_background_spectrum!=None:      
            self.background_plot=self.Spectrum_direct.plot([0],[0],pen='r')
            self.background_plot.setData(self.lambdas,self.spectro_unit.active_background_spectrum)
        if self.spectro_unit.current_absorbance_spectrum!=None: #abs direct
            self.abs_direct_plot=self.Abs_direct.plot([0],[0],clear = True)
            self.abs_direct_plot.setData(self.lambdas,self.spectro_unit.current_absorbance_spectrum)
        if self.spectro_unit.reference_absorbance!=None:    #abs ref
            self.reference_abs_plot=self.Abs_direct.plot([0],[0],pen='y')
            self.reference_abs_plot.setData(self.lambdas,self.spectro_unit.reference_absorbance)  

    def link_spectro2IHM(self):
        #informations
        self.label_model.setText("model : "+self.spectro_unit.model)
        self.label_spectro_SN.setText("S/N : "+self.spectro_unit.serial_number)
        #config de l'affichage du spectre courant
        self.lambdas=self.spectro_unit.wavelengths      
        self.abs_direct_plot=self.Abs_direct.plot([0],[0])
        self.intensity_direct_plot=self.Spectrum_direct.plot([0],[0])
        #mise sur timer
        self.spectro_unit.timer.timeout.connect(self.updateSpectrum)            
        #état réel du shutter
        self.shutter.setChecked(not(self.spectro_unit.shutter.getState()))
        self.shutter.clicked.connect(self.spectro_unit.changeShutterState)


                                    ### Methods for Syringe pumps
    def connectSyringePump(self):
        self.dispenser.connect()
        if self.dispenser.state=='open':
            self.led_disp.setPixmap(self.pixmap_green)
    
    def refresh_volumes(self):
        self.levelbarA.setProperty("value",str(self.dispenser.syringe_A.level_uL))   #int
        self.levelbarB.setProperty("value",str(self.dispenser.syringe_B.level_uL))
        self.levelbarC.setProperty("value",str(self.dispenser.syringe_C.level_uL))
        self.levelA_uL.setText(str(self.dispenser.syringe_A.level_uL))  
        self.levelB_uL.setText(str(self.dispenser.syringe_B.level_uL))
        self.levelC_uL.setText(str(self.dispenser.syringe_C.level_uL))
        # volume counts
        self.added_A_uL.setText("%d" %self.dispenser.syringe_A.added_vol_uL)
        self.added_B_uL.setText("%d" %self.dispenser.syringe_B.added_vol_uL)
        self.added_C_uL.setText("%d" %self.dispenser.syringe_C.added_vol_uL)
        self.added_total.setText("%d" %self.dispenser.vol.added_total_uL)
    
    def reset_volume_count(self):
        self.syringe_pump.added_acid_uL=0
        self.syringe_pump.added_base_uL=0
        self.syringe_pump.added_total_uL=0
        self.syringe_pump.acid_dispense_log=[]
        self.syringe_pump.base_dispense_log=[]
        self.added_acid.setValue(0)
        self.added_base.setText("0")
        self.added_total.setText("0" )

    ### Peristaltic pump and circuit
    def connexionChange_circuit(self):
        if self.circuit.state=='closed':
            self.connectCircuit()
        elif self.circuit.state=='open':
            self.disconnectCircuit()

    def connectCircuit(self):
        self.circuit.connect()
        if self.peristaltic_pump.state=='open':
            self.led_pump.setPixmap(self.pixmap_green)
            self.pump_speed.setValue(self.peristaltic_pump.volts2scale(self.peristaltic_pump.mean_voltage))
            self.link_pump2IHM()
        if self.circuit.state=='open':
            self.led_ev_circuit.setPixmap(self.pixmap_green)
            self.connect_disconnect_circuit.setText("Disconnect")
    
    def disconnectCircuit(self):
        self.circuit.close()
        self.led_pump.setPixmap(self.pixmap_red)
        self.led_ev_circuit.setPixmap(self.pixmap_red)
        self.connect_disconnect_circuit.setText("Connect")
    
    def link_pump2IHM(self):
        #print("fonction link pump execute")
        self.start_stop_pump_button.clicked.connect(self.start_stop_pump)
        self.change_dir.clicked.connect(self.peristaltic_pump.change_direction)
        self.pump_speed.valueChanged.connect(self.update_pump_speed)

    def start_stop_pump(self):
        """Start or stop Peristaltic pump and displays on button"""
        self.peristaltic_pump.start_stop()
        self.start_stop_pump_button.setText(self.peristaltic_pump.text())

    def update_pump_speed(self):
        self.peristaltic_pump.setSpeed_voltage(self.peristaltic_pump.scale2volts(self.pump_speed.value()))

    def ev0_changeState(self):
        """Changes state display on entrance valve"""
        self.circuit.ev0.changeState()
        self.ev0_state.setText(self.circuit.ev0.state2Text(self.circuit.ev0.getState()))

    def ev1_changeState(self):
        """Changes state dispaly on exit valve"""
        self.circuit.ev1.changeState()
        self.ev1_state.setText(self.circuit.ev1.state2Text(self.circuit.ev1.getState()))

    def closeEvent(self, event):
        print("Closing main window")
        self.ihm.updateDefaultParam()