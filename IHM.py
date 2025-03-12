"""Classe IHM qui contient des attributs communs à toutes les fenêtres PyQt"""

from PyQt5 import QtCore

from configparser import ConfigParser
import os
from pathlib import Path
from datetime import datetime

from Phidget22.Phidget import *
from Phidget22.Devices.VoltageInput import *
from Phidget22.Devices.Manager import *

from lib.oceandirect.OceanDirectAPI import Spectrometer as Sp, OceanDirectAPI
from lib.oceandirect.od_logger import od_logger

#Instruments
from subsystems.pHmeter import PHMeter
from subsystems.absorbanceMeasure import AbsorbanceMeasure
from subsystems.dispenser import Dispenser, PhidgetStepperPump
from subsystems.peristalticPump import PeristalticPump
from subsystems.circuit import Circuit

#Windows
from windows.control_panel import ControlPanel
from windows.sequence_config_window import SequenceConfigWindow
from windows.phmeter_calib_window import PhMeterCalibWindow
from windows.custom_sequence_window import CustomSequenceWindow
from windows.classic_sequence_window import ClassicSequenceWindow
from windows.spectrometry_window import SpectrometryWindow
from windows.dispenser_window import DispenserWindow
from windows.settings_window import SettingsWindow

path = Path(__file__)
ROOT_DIR = path.parent.absolute()

class IHM:

    app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini")
    device_ids = os.path.join(ROOT_DIR, "config/device_id.ini")
    #calibration_file = os.path.join(ROOT_DIR, "config/latest_cal.ini")

    parser = ConfigParser()
    parser.read(device_ids)
    id01 = int(parser.get('main board id', 'dommino01'))
    id02 = int(parser.get('main board id', 'dommino02'))

    #affiche les chemins
    #print("app_default_settings ihm : ", app_default_settings, "\ndevice_ids : ", device_ids)
    
    #Sous sytèmes 
    #On créée les instances de chaque sous système ici. L'état est 'closed' par défaut
    spectro_unit=AbsorbanceMeasure()
    phmeter=PHMeter()
    dispenser=Dispenser()
    peristaltic_pump=PeristalticPump()
    circuit=Circuit(peristaltic_pump)

    manager=Manager()

    instrument_id=''    #SN unknown at opening

    def __init__(self):
        
        #Config for savings
        parser = ConfigParser()
        parser.read(self.app_default_settings)
        self.saving_folder=parser.get('saving parameters', 'folder')       
  
        #Configs for Automatic sequence
        self.experience_name=None
        self.description=None
        self.fibers=parser.get('setup', 'fibers')
        self.flowcell=parser.get('setup', 'flowcell')
        self.N_mes=None #number of pH/spectra measures
        self.dispense_mode=parser.get('sequence', 'dispense_mode')

        #classic
        self.fixed_delay_sec=int(parser.get('classic titration sequence', 'fixed_delay_sec'))
        self.mixing_delay_sec=int(parser.get('classic titration sequence', 'mixing_delay_sec'))
        self.initial_pH=None
        self.final_pH=None
        self.added_total_uL = 0
        self.added_A_uL = 0
        self.added_B_uL = 0
        self.added_C_uL = 0

        #custom
        self.sequence_config_file=parser.get('custom sequence', 'sequence_file') 

        #display timer
        self.timer_display = QtCore.QTimer()
        self.timer_display.setInterval(1000)    #timeout every 1s
        self.timer_display.start()

        #Gestion des connexions/déconnexions
        self.manager.setOnAttachHandler(self.AttachHandler)
        self.manager.setOnDetachHandler(self.DetachHandler)
        self.manager.open()

    def AttachHandler(self, man, channel):
        serialNumber = channel.getDeviceSerialNumber()
        deviceName = channel.getDeviceName()
        channelName = channel.getChannelName()
        ch_num=channel.getChannel()
        hubPort=channel.getHubPort()
        isChannel=channel.getIsChannel()
        #print("Connected : ",serialNumber,deviceName,"port : ",hubPort,isChannel,channelName,"channel : ",ch_num)

        #execution du code ci dessous une seule fois lors du branchement de la carte
        if deviceName=='6-Port USB VINT Hub Phidget':
            self.loadBoardsSerialNumbers('VINT',serialNumber)
        elif deviceName=='PhidgetInterfaceKit 8/8/8' and channelName=='Digital Output' and ch_num==7:
            self.loadBoardsSerialNumbers('interface board',serialNumber)

    def loadBoardsSerialNumbers(self, board, nb):
        parser = ConfigParser()
        parser.read(self.device_ids)
        if board=='VINT':
            self.VINT_number = nb   #S/N as attribute of IHM
            print("VINT S/N = ", nb)
            parser.set('VINT', 'id', str(nb))   #S/N written in file device_id
            file = open(self.device_ids,'w')
            parser.write(file)
            file.close()
        elif board=='interface board':
            self.board_number = nb
            print('Interfacing board S/N = ', nb)
            parser.set('main board', 'id', str(nb))
            file = open(self.device_ids,'w')
            parser.write(file)
            file.close()
            self.getInstrumentSerialNumber()

    def getInstrumentSerialNumber(self):
        parser = ConfigParser()
        parser.read(self.device_ids)
        if self.board_number == self.id01:
            self.instrument_id='DOMMINO01'
        elif self.board_number == self.id02:
            self.instrument_id='DOMMINO02'
        else:
            self.instrument_id='unknown'
        print("instrument S/N =", self.instrument_id)
        try:
            self.controlPanel.label_instrument_SN.setText("instrument S/N : "+self.instrument_id)
        except:
            #no attribute control Panel yet
            pass

    def DetachHandler(self, man, channel):
        serialNumber = channel.getDeviceSerialNumber()
        deviceName = channel.getDeviceName()
        channelName = channel.getChannelName()
        ch_num=channel.getChannel()
        hubPort=channel.getHubPort()
        isChannel=channel.getIsChannel()
        #print("Disconnected : ",serialNumber,"--",deviceName,"--","port : ",hubPort,isChannel,"--",channelName,"--","channel : ",ch_num)

        #pH meter
        if deviceName=='PhidgetInterfaceKit 8/8/8' and channelName=='Voltage Input' and ch_num==0:
            self.phmeter.state='closed'
            print("pH meter disconnected")
            self.controlPanel.led_phmeter.setPixmap(self.controlPanel.pixmap_red)
        #Lamp control

        #Dispenser
        if deviceName=='PhidgetInterfaceKit 8/8/8' and channelName=='Digital Input' and ch_num==0:
            self.dispenser.state='closed'
            print("Syringe pump disconnected due to switchs unaccessible")
            self.controlPanel.led_disp.setPixmap(self.controlPanel.pixmap_red)
        if deviceName=='4A Stepper Phidget' and hubPort==0:
            #stepper A de pousse seringue débranché
            self.dispenser.syringe_A.state='closed'
            print("Stepper A disconnected")
        if deviceName=='4A Stepper Phidget' and hubPort==1:
            #stepper B de pousse seringue débranché
            self.dispenser.syringe_B.state='closed'
            print("Stepper B disconnected")
        if deviceName=='4A Stepper Phidget' and hubPort==2:
            #stepper C de pousse seringue débranché
            self.dispenser.syringe_C.state='closed'
            print("Stepper C disconnected")
        
        self.dispenser.refresh_state()
        
        if self.dispenser.state=='closed':
            self.controlPanel.led_disp.setPixmap(self.controlPanel.pixmap_red)
        
        if deviceName=='4A DC Motor Phidget' and hubPort==3:
            self.peristaltic_pump.state='closed'
            print("Peristaltic pump disconnected")
            self.controlPanel.led_pump.setPixmap(self.controlPanel.pixmap_red)
        
        #Lamp control unaccessible
        if deviceName=='PhidgetInterfaceKit 8/8/8' and channelName=='Digital Output' and ch_num==5:
            self.spectro_unit.state='closed'
            print("Unable to control lamp")
            self.controlPanel.led_spectro.setPixmap(self.controlPanel.pixmap_red)

    def close_all_devices(self):
        print("Closing all device")
        self.updateDefaultParam()
        if self.spectro_unit.state=='open':
            self.spectro_unit.close(self.spectro_unit.id)
        if self.phmeter.state=='open':
            self.phmeter.close()
        if self.dispenser.state=='open':
            self.dispenser.close()
        if self.circuit.state=='open':
            self.circuit.close()
        elif self.peristaltic_pump.state=='open':
            self.peristaltic_pump.close()
              
    def updateDefaultParam(self):
        """Updates current parameters as default in file 'config/app_default_settings'"""
        parser = ConfigParser()
        parser.read(self.app_default_settings)
        parser.set('saving parameters','folder',str(self.saving_folder))
        parser.set('custom sequence', 'sequence_file', self.sequence_config_file)
        if self.peristaltic_pump.state=='open':
            parser.set('pump', 'speed_volts', str(self.peristaltic_pump.mean_voltage))
        if self.phmeter.state=='open':
            parser.set('phmeter', 'epsilon', str(self.phmeter.stab_step))
            parser.set('phmeter', 'delta', str(self.phmeter.stab_time))
            parser.set('calibration', 'file', str(self.phmeter.relative_calib_path))
            parser.set('phmeter', 'default', str(self.phmeter.model))
            parser.set('electrode', 'default', str(self.phmeter.electrode))
        if self.dispenser.state=='open':
            parser.set(self.dispenser.syringe_A.id, 'level', str(self.dispenser.syringe_A.level_uL))
            parser.set(self.dispenser.syringe_B.id, 'level', str(self.dispenser.syringe_B.level_uL))
            parser.set(self.dispenser.syringe_C.id, 'level', str(self.dispenser.syringe_C.level_uL))
        file = open(self.app_default_settings,'w')
        parser.write(file) 
        file.close()
        print("updates current parameters in default file")

    def createDirectMeasureFile(self):
        dt = datetime.now()
        date_text=dt.strftime("%m/%d/%Y %H:%M:%S")
        date_time=dt.strftime("%m-%d-%Y_%Hh%Mmin%Ss")
        name = "mes_"
        header = "Instant measure on Dommino titrator\n"+"date and time : "+str(date_text)+"\n"+"Device : "+self.instrument_id+"\n\n"
        data = ""
        print("saving instant measure - ")
        #saving pH measure
        if self.phmeter.state=='open':
            name+="pH-"
            header+=("current calibration data\n"+"date and time: "+self.phmeter.CALdate+"\nnumber of points: "+str(self.phmeter.CALtype)+"\n"+
            "recorded voltages : U4 = "+str(self.phmeter.U1)+"V; U7="+str(self.phmeter.U2)+"V; U10="+str(self.phmeter.U3)+"V\n"+
            "calibration coefficients : a="+str(self.phmeter.a)+ "; b="+str(self.phmeter.b)+"\n\n"
            )
            pH = self.phmeter.currentPH
            V = self.phmeter.currentVoltage
            data+="pH = "+str(pH)+"; U = "+str(V)+"V\n\n"
        else:
            header+="pH meter not connected\n\n"

        #saving dispensed volumes
        if self.dispenser.state=='open':
            name+="titr-"
            header+=("Syringe Pump : \n"+str("500uL Trajan gas tight syringe\n")
            +str(self.dispenser.infos)+"\n")
            data+=("added syringe A : "+str(self.dispenser.syringe_A.added_vol_uL)+"uL\n"
            +"added syringe B : "+str(self.dispenser.syringe_B.added_vol_uL)+"uL\n"
            +"added syringe C : "+str(self.dispenser.syringe_C.added_vol_uL)+"uL\n"
            +"total added : "+str(self.dispenser.vol.added_total_uL)+"uL\n\n")
        else:
            header+="Syringe pump not connected\n"

        if self.spectro_unit.state=='open':
            name+="Abs_"
            header+=("\nSpectrometer : "+str(self.spectro_unit.model)
            +"\nSerial number : "+str(self.spectro_unit.serial_number)
            +"\nIntegration time (ms) : "+str(self.spectro_unit.t_int/1000)
            +"\nAveraging : "+str(self.spectro_unit.averaging)
            +"\nBoxcar : "+str(self.spectro_unit.boxcar)
            +"\nNonlinearity correction usage : "+str(self.spectro_unit.device.get_nonlinearity_correction_usage())
            +"\nElectric dark correction usage : "+str(self.spectro_unit.electric_dark)
            +"\nAbsorbance formula : A = log10[(reference-background)/(sample-background)]\n")

            background = self.spectro_unit.active_background_spectrum
            ref = self.spectro_unit.active_ref_spectrum
            sample = self.spectro_unit.current_intensity_spectrum
            absorbance = self.spectro_unit.current_absorbance_spectrum
            wl = self.spectro_unit.wavelengths
            spectra=[wl,background,ref,sample,absorbance]
            Nc=len(spectra)-1
            if background==None or ref==None: #pas de calcul d'absorbance possible
                data+="lambda(nm)\tsample (unit count)\n"
                for l in range(self.spectro_unit.N_lambda):
                    data+=str(spectra[0][l])+'\t'
                    data+=str(spectra[3][l])+'\n'
            else:
                data+="lambda(nm)\tbackground (unit count)\treference ('')\tsample ('')\tabsorbance (abs unit)\n"
                for l in range(self.spectro_unit.N_lambda):
                    for c in range(Nc):
                        data+=str(spectra[c][l])+'\t'
                    data+=str(spectra[Nc][l])+'\n'
        else:
            header+="Spectrometer closed\n"

        name+=str(date_time)
        output=header+"\n\n"+data
        f_out = open(self.saving_folder+'/'+name+'.txt','w') #création d'un fichier dans le répertoire
        f_out.write(output)
        f_out.close()    
    
    """def close_sequence(self):
        del self.seq"""

    ### Gestionnaire des fenêtres ###

    def openControlPanel(self):
        self.controlPanel=ControlPanel(self)
        self.controlPanel.show()

    def openConfigWindow(self):
        self.seqConfig = SequenceConfigWindow(self)
        self.seqConfig.show()

    def openSpectroWindow(self):
        self.spectroWindow = SpectrometryWindow(self)
        self.spectroWindow.show()

    def openDispenserWindow(self):
        self.syringePanel = DispenserWindow(self)
        self.syringePanel.show()

    def openCalibWindow(self):
        self.calib_window = PhMeterCalibWindow(self)
        self.calib_window.show()

    def openSettingsWindow(self):
        self.settings_win = SettingsWindow(self)
        self.settings_win.show()

    def openSequenceWindow(self,type):
        if type=="classic":
            self.sequenceWindow = ClassicSequenceWindow(self)
            self.sequenceWindow.show()
        elif type=="custom":
            self.sequenceWindow = CustomSequenceWindow(self)
            self.sequenceWindow.show()

if __name__=="main":
    interface = IHM()
    print(interface.saving_folder)
