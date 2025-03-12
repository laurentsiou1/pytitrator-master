"classe Spectrometer permettant de piloter l'ensemble Spectromètre et lampe"

from lib.oceandirect.OceanDirectAPI import OceanDirectError, OceanDirectAPI, Spectrometer, FeatureID
from lib.oceandirect.od_logger import od_logger
logger = od_logger()

import numpy as np
import matplotlib.pyplot as plt
import time

from Phidget22.Phidget import *
from Phidget22.Devices.DigitalOutput import *

from configparser import ConfigParser
import os
from pathlib import Path

from PyQt5 import QtCore

import subsystems.processing as sp

path = Path(__file__)
ROOT_DIR = path.parent.parent.absolute() #répertoire pytitrator
app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini")
device_ids = os.path.join(ROOT_DIR, "config/device_id.ini")

class AbsorbanceMeasure(Spectrometer):
    
    parser = ConfigParser()
    parser.read(device_ids)
    board_number = int(parser.get('main board', 'id'))
    VINT_number = int(parser.get('VINT', 'id'))
    ch_shutter=int(parser.get('lamp', 'shutter'))
    ch_deuterium=int(parser.get('lamp', 'deuterium'))
    ch_halogen=int(parser.get('lamp', 'halogen'))

    #Lamp control 
    shutter = DigitalOutput()
    shutter.setDeviceSerialNumber(board_number)
    shutter.setChannel(ch_shutter)
    deuterium = DigitalOutput()
    deuterium.setDeviceSerialNumber(board_number)
    deuterium.setChannel(ch_deuterium)
    halogen = DigitalOutput()
    halogen.setDeviceSerialNumber(board_number)
    halogen.setChannel(ch_halogen)

    def __init__(self): #ihm:IHM est un argument optionnel 
        self.state='closed'
        #Data
        #All spectra are saved with active corrections. It can be nonlinearity and/or electric dark 
        # when activated via methods "set_nonlinearity_correction_usage" and 
        # "set_electric_dark_correction_usage". None of these are corrected from 
        # the background spectrum. 
        self.active_background_spectrum=None  #Background Spectrum
        self.active_ref_spectrum=None   #Reference
        self.reference_absorbance=None  #courbe d'absorbance juste après la prise de réf
        self.current_intensity_spectrum=None    #Sample or whatever is in the cell
        self.current_absorbance_spectrum=None   #Absorbance
        self.absorbance_spectrum1=None
        self.wavelengths=None
        self.model=''
        self.serial_number=''
        
        #timer pour acquisition des spectres
        self.timer = QtCore.QTimer()
        self.timer.setInterval(3000)
        
        self.update_infos()

    def connect(self):
        od = OceanDirectAPI()
        device_count = od.find_usb_devices() #ne pas enlever cette ligne pour détecter le spectro
        #print(device_count)
        device_ids = od.get_device_ids()
        #print(device_ids)
        if device_ids!=[]:
            self.id=device_ids[0]
            try:
                spectro = od.open_device(self.id) #crée une instance de la classe Spectrometer
                adv = Spectrometer.Advanced(spectro)
                det=0
                try:
                    self.shutter.openWaitForAttachment(1000)
                    self.shutter_connected=True
                except:
                    self.shutter_connected=False
                    det+=1
                try:
                    self.deuterium.openWaitForAttachment(1000)
                    self.deuterium_connected=True
                except:
                    self.deuterium_connected=False
                    det+=1
                try:
                    self.halogen.openWaitForAttachment(1000)
                    self.halogen_connected=True
                except:
                    self.halogen_connected=False
                    det+=1
                if det==0:
                    self.state='open'
                else:
                    self.state='closed'
            except:
                print("Can not connect to spectrometer identified : ",self.id)
        else:
            self.state='closed'
        
        if self.state=='open':
            self.wavelengths = [ round(l,1) for l in spectro.wavelengths ]
            self.N_lambda = len(self.wavelengths)
            self.model=spectro.get_model()
            self.serial_number=spectro.get_serial_number()
            self.ocean_manager=od #instance de la classe OceanDirectAPI
            self.device=spectro
            self.adv=Spectrometer.Advanced(spectro) 

            parser = ConfigParser()
            parser.read(app_default_settings)
            former_model=parser.get('spectrometry', 'model')
            self.t_int=int(parser.get('spectrometry', 'tint'))  #ms
            self.averaging=int(parser.get('spectrometry', 'avg'))
            self.acquisition_delay=self.t_int*self.averaging
            
            #Settings specific to models    #Tint and avg
            self.device.set_nonlinearity_correction_usage(True)
            if self.model==former_model:
                self.device.set_integration_time(1000*self.t_int)
                self.device.set_scans_to_average(self.averaging)
            else:
                self.device.set_integration_time(15000) 
                self.device.set_scans_to_average(10)
            
            if self.model=='OceanSR2':  #2k pix pour 700nm
                self.device.set_boxcar_width(1) #moyennage sur 3 points (2n+1)    
            elif self.model=='OceanSR6':    #2k pix pour 700nm à vérifier pour le SR6
                self.device.set_boxcar_width(1) #moyennage sur 3 points (2n+1)
            elif self.model=='OceanST': #2k pix pour 400nm
                self.device.set_boxcar_width(2) #moyennage sur 5 points (2n+1) 
            else:
                print("Spectrometer model not recognized")
            
            try:
                ed=self.device.get_electric_dark_correction_usage()
                self.electric_dark=ed
            except: #feature not available for OceanST or OceanSR spectrometers
                self.electric_dark = False

            #time attributes in milliseconds. SDK methods outputs are in microseconds (us)
            self.t_int=self.device.get_integration_time()//1000 
            self.t_int_max=self.device.get_maximum_integration_time()//1000 
            self.t_int_min=self.device.get_minimum_integration_time()//1000 
            self.averaging=self.device.get_scans_to_average()
            self.boxcar=self.device.get_boxcar_width()
            
            self.timer.start()
            self.timer.timeout.connect(self.updateSpectra)
        
        self.update_infos()
        print(self.infos)
    
    def update_infos(self):
        if self.state=='open':
            self.infos="\nSpectrometer : connected"\
            +"\nModel : "+self.model\
            +"\nIntegration time (ms) : "+str(self.t_int/1000)\
            +"\nAveraging : "+str(self.averaging)\
            +"\nBoxcar : "+str(self.boxcar)\
            +"\nNonlinearity correction usage : "+str(self.device.get_nonlinearity_correction_usage())\
            +"\nElectric dark correction usage : "+str(self.electric_dark)\
            +"\nAbsorbance formula : A = log10[(reference-background)/(sample-background)]"\
            +"\nOutput pins :"\
            +"\nShutter pin : "+str(self.shutter_connected)\
            +"\nDeuterium pin : "+str(self.deuterium_connected)\
            +"\nHalogen pin : "+str(self.halogen_connected)
        else:
            self.infos="\nCan not connect to spectrometer"

    def close(self,id): #fermeture de l'objet absorbanceMeasure
        self.timer.stop()
        self.shutter.setState(False)
        print("shutter closed\n")
        self.device.close_device()
        self.ocean_manager.close_device(id) #close_device(id)
        print("Spectrometer disconnected\n")
        self.state='closed'

    def get_shutter_state(self):
        if self.state=='open':
            self.shutter_state=self.shutter.getState()
        else:
            self.shutter_state=False
        return self.shutter_state

    def open_shutter(self):
        if self.state=='open':
            self.shutter.setState(True)

    #@necessite self.state=='open'
    def close_shutter(self):
        if self.state=='open':
            self.shutter.setState(False)

    def changeShutterState(self):
        state=self.shutter.getState()
        self.shutter.setState(not(state))
    
    def update_acquisition_delay(self):
        self.acquisition_delay=self.t_int*self.averaging #ms

    #Récupère autant de spectres que N_avg sur le spectro
    #Fonction vérifiée qui fonctionne. Plus rapide que de faire le moyennage sur le spectro
    def get_N_spectra(self):
        N=self.device.get_scans_to_average()
        try:
            self.device.set_scans_to_average(1)
            spectra = [0 for k in range(N)]
            for i in range(N):
                spectra[i] = self.device.get_formatted_spectrum() #gets the current spectrum
                # with activated corrections (nonlinearity and/or electric dark) and with
                # NO substraction of the background
            self.device.set_scans_to_average(N)
        except OceanDirectError as e:
            logger.error(e.get_error_details())  
        #☺print("spectra",spectra)
        return spectra
    
    def get_averaged_spectrum(self):
        """Returns a list of float"""
        t0=time.time()
        spectra=self.get_N_spectra()
        t1=time.time()
        avg=sp.average_spectra(spectra)
        t2=time.time()
        self.Irec_time=t1-t0
        self.avg_delay=t2-t1
        self.update_refresh_rate()
        return avg

    def acquire_background_spectrum(self):
        self.shutter.setState(False)
        time.sleep(2)
        bgd=self.get_averaged_spectrum()
        self.active_background_spectrum=bgd

    def acquire_ref_spectrum(self):
        self.shutter.setState(True)
        time.sleep(2)
        ref=self.get_averaged_spectrum()
        ref2=self.get_averaged_spectrum()
        self.active_ref_spectrum=ref
        bgd=self.active_background_spectrum
        if bgd!=None:
            self.reference_absorbance, self.Aproc_delay = sp.intensity2absorbance(ref2,ref,bgd)

    def update_intensity_spectrum(self):    #ontimer
        self.current_intensity_spectrum=self.get_averaged_spectrum()
    
    def update_absorbance_spectrum(self):
        self.current_absorbance_spectrum, self.Aproc_delay = sp.intensity2absorbance(self.current_intensity_spectrum,self.active_ref_spectrum,self.active_background_spectrum)

    def dark_and_ref_stored(self):
        """Returns True if a background and a reference spectrum have been stored"""
        open=(self.state=='open')
        bgd=(self.active_background_spectrum!=None)
        ref=(self.active_ref_spectrum!=None)
        return open*bgd*ref

    def updateSpectra(self):
        self.update_intensity_spectrum()
        if self.dark_and_ref_stored(): #background and ref recorded
            self.update_absorbance_spectrum()

    #@Necessary that background and ref are stored
    def update_refresh_rate(self):   
        self.refresh_rate=int(self.Irec_time*1000+500)   #ms
        self.timer.setInterval(self.refresh_rate)

class Advanced(AbsorbanceMeasure):  ### Fonctions optionelles ###    
    
    def get_optimal_integration_time(self, spectra):
        int_time_us=self.t_int*1000
        Imax=sp.max_intensity(spectra)
        if self.serial_number=='STUV002':
            optimal_int_time_us = 1000*int(int_time_us*15/Imax) #15000 unit count correspond au ST.
            #Le capteur a une résolution de 14bit = 16300... unit count
            #ça doit être un multiple de 1000 pour être entier en millisecondes.
            return optimal_int_time_us  
        elif self.serial_number=='SR200336':
            optimal_int_time_us = 1000*int(int_time_us*50/Imax) #15000 unit count correspond au ST. 
            return optimal_int_time_us
        else:
            print("numéro du spectro: ",self.serial_number)
        return optimal_int_time_us