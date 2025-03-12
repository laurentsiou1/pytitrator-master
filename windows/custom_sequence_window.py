"""fenêtre de séquence sur mesure"""

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow, QApplication
from graphic.windows.custom_seq_win import Ui_CustomSequenceWindow

import pyqtgraph as pg
from windows.spectrometry_window import SpectrometryWindow
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

import file_manager as fm
from file_manager import Data 
import os

path_internal=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
play_icon_path=os.path.join(path_internal, "graphic/images/play_icon.png")
pause_icon_path=os.path.join(path_internal, "graphic/images/pause_icon.png")

class CustomSequenceWindow(QMainWindow,Ui_CustomSequenceWindow):
    
    absorbance_spectrum1=None

    def __init__(self, ihm, parent=None):   #win:WindowHandler
        super(CustomSequenceWindow,self).__init__(parent)
        self.setupUi(self)
        self.ihm=ihm
        self.seq=self.ihm.seq
        seq=self.seq
        
        #Sizing PlotWidgts inside QTabWidgets
        (w,h)=(self.spectra_tabs.geometry().width(),self.spectra_tabs.geometry().height())
        rect=QtCore.QRect(0,0,w-5,h-32)
        
        #rect=QtCore.QRect(910, 440, 831, 300)
        self.delta_all_abs = pg.PlotWidget(self.tab1)
        self.delta_all_abs.setGeometry(rect) 
        self.delta_all_abs.setObjectName("delta_all_abs")
        #self.delta_all_abs.setXRange(min=240,max=540)
        self.all_abs = pg.PlotWidget(self.tab2)
        self.all_abs.setGeometry(rect)
        self.all_abs.setObjectName("all_abs")
        self.all_intensity = pg.PlotWidget(self.tab3)
        self.all_intensity.setGeometry(rect) 
        self.all_intensity.setObjectName("all_intensity")
        self.spectra_tabs.addTab(self.tab1, "delta") 
        self.spectra_tabs.addTab(self.tab2, "raw abs")
        self.spectra_tabs.addTab(self.tab3, "intensity")

        #superposed N spectra
        self.delta_all_abs_plot=self.delta_all_abs.plot([0],[0])
        self.all_abs_plot=self.all_abs.plot([0],[0])
        #self.current_intensity_plot=self.all_intensity.plot([0],[0])
        self.all_intensity_plot=self.all_intensity.plot([0],[0])
        
        #connexions
        self.spectrometry.clicked.connect(self.ihm.openSpectroWindow)
        self.syringes.clicked.connect(self.ihm.openDispenserWindow)
        self.pause_resume_button.clicked.connect(self.seq.pause_resume)
        #saving
        self.actionsave.triggered.connect(lambda : self.ihm.seq_data.createSequenceFiles(seq)) 
        #la fonction ne s'applique pas sur le self, d'où le lambda ?
        self.pump_speed_volt.valueChanged.connect(self.update_pump_speed)
        
        ##Initialisation en fonction de la config 
        self.N_mes=seq.N_mes
        
        #Paramètres d'expérience
        self.experiment_parameters.setPlainText("\nNom de l'expérience : "+str(seq.experience_name)\
        +"\nDescription : "+str(seq.description)\
        +"\nFibres : "+str(seq.fibers)\
        +"\nFlowcell : "+str(seq.flowcell)\
        +"\nDispense mode : "+str(seq.dispense_mode))

        #Spectro
        if ihm.spectro_unit.state=='open':
            self.lambdas=self.ihm.spectro_unit.wavelengths 
            self.N_lambda=len(self.lambdas)

        #Display current spectra
        self.ihm.spectro_unit.timer.timeout.connect(self.refresh_direct_spectra)

        #display timer
        self.ihm.timer_display.timeout.connect(self.refresh_screen)

        #graphique
        #colormap for plots
        cmap = plt.get_cmap('tab10')
        aa = [cmap(i) for i in np.linspace(0, 1, self.N_mes)]
        self.colors = [(int(r * 255), int(g * 255), int(b * 255)) for r, g, b, _ in aa]

        self.pause_resume_button.setIcon(QtGui.QIcon(pause_icon_path))
        
        #Matrix for instructions
        for j in range(self.N_mes): 
            self.tab_jk = QtWidgets.QLabel(self.gridLayoutWidget_2)
            self.tab_jk.setAlignment(QtCore.Qt.AlignCenter)
            self.grid_instructions.addWidget(self.tab_jk, j+1, 0, 1, 1)
            self.tab_jk.setText(str(j+1))
            for k in range(6):
                self.tab_jk = QtWidgets.QLabel(self.gridLayoutWidget_2)
                self.tab_jk.setAlignment(QtCore.Qt.AlignCenter)
                self.grid_instructions.addWidget(self.tab_jk, j+1, k+1, 1, 1)
                self.tab_jk.setText(str(seq.instruction_table[j][k]))
        
        #matrix for dispensed volume, pH and measure times  #3columns and N_mes lines
        self.table_vol_pH=[[QtWidgets.QLabel(self.gridLayoutWidget),QtWidgets.QLabel(self.gridLayoutWidget),QtWidgets.QLabel(self.gridLayoutWidget)] for k in range(self.N_mes)]
        #Tableau volume dispensé/pH mesuré, temps de mesure
        #Mise en forme. A compléter par la suite
        for j in range(self.N_mes+1):
            for k in range(3):
                self.mes_jk = QtWidgets.QLabel(self.gridLayoutWidget)
                self.mes_jk.setAlignment(QtCore.Qt.AlignCenter)
                self.grid_mes_pH_vol.addWidget(self.mes_jk, j, k, 1, 1)
                self.mes_jk.setText("")

        #peristaltic pump
        if seq.pump.state=='open':
            self.pump_speed_volt.setProperty("value", seq.pump.mean_voltage)           

        #pH meter
        self.stab_time.setProperty("value", seq.phmeter.stab_time)
        self.stab_time.valueChanged.connect(self.update_stab_time)
        self.stab_step.setProperty("value", seq.phmeter.stab_step)
        self.stab_step.valueChanged.connect(self.update_stab_step)

        #self.direct_pH.display(self.ihm.phmeter.currentPH) #pH instantané

    #DIRECT
    def refresh_screen(self):
        #Countdown
        try:
            tm=datetime.now()
            tm=tm.replace(microsecond=0)
            elapsed=tm-self.seq.time_mes_last
            elapsed_sec = elapsed.total_seconds() #convert to seconds
            remaining = int(max(0,self.seq.delay_mes-elapsed_sec))
            #print("remaining time : ", remaining)
            self.countdown.setProperty("value", remaining)
        except:
            pass
        #PhMeter
        if self.ihm.phmeter.state=='open':
            self.direct_pH.display(self.ihm.phmeter.currentPH)
            self.stab_time.setProperty("value", self.ihm.phmeter.stab_time)
            self.stab_step.setProperty("value", self.ihm.phmeter.stab_step)
            self.stabilisation_level.setProperty("value", self.ihm.phmeter.stab_purcent)
            self.label_stability.setText(str(self.ihm.phmeter.stab_purcent)+"%")
        #Peristaltic pump
        if self.ihm.peristaltic_pump.state=='open':
            self.pump_speed_volt.setProperty("value", self.ihm.peristaltic_pump.mean_voltage)

    #Displaying current spectra
    def refresh_direct_spectra(self):
        if self.ihm.spectro_unit.state=='open': #Intensity live
            try:
                self.all_intensity.removeItem(self.intensity_current_plot)
            except:
                pass
            self.intensity_current_plot=self.all_intensity.plot([0],[0],clear=False)
            self.intensity_current_plot.setData(self.lambdas,self.ihm.spectro_unit.current_intensity_spectrum)
        if self.ihm.spectro_unit.current_absorbance_spectrum!=None: #Absorbance live
            try:
                self.all_abs.removeItem(self.abs_current_plot)
            except:
                pass
            self.abs_current_plot=self.all_abs.plot([0],[0])
            self.abs_current_plot.setData(self.lambdas,self.ihm.spectro_unit.current_absorbance_spectrum)
            if self.ihm.spectro_unit.absorbance_spectrum1!=None:    #Delta Abs live
                self.current_delta_abs=[self.ihm.spectro_unit.current_absorbance_spectrum[k]-self.absorbance_spectrum1[k] for k in range(self.N_lambda)] #processing delta abs
                try:
                    self.delta_all_abs.removeItem(self.delta_current_plot)
                except:
                    pass
                self.delta_current_plot=self.delta_all_abs.plot([0],[0],clear = False)
                self.delta_current_plot.setData(self.lambdas,self.current_delta_abs)

    #MODIF SUR LES INSTRUMENTS
    def update_pump_speed(self):
        self.ihm.peristaltic_pump.setSpeed_voltage(self.pump_speed_volt.value())
    def update_stab_time(self):
        self.ihm.phmeter.stab_time=self.stab_time.value()
    def update_stab_step(self):
        self.ihm.phmeter.stab_step=self.stab_step.value()
    
    #ENREGISTREMENT

    #Spectres d'absorbance
    def append_spectra(self,N,absorbance,delta,intensity):
        #delta
        self.delta_all_abs_plot=self.delta_all_abs.plot(self.lambdas,delta,pen=pg.mkPen(color=self.colors[N-1])) #pen='g'
        #self.delta_all_abs_plot.setData(,)
        #abs
        self.all_abs_plot=self.all_abs.plot(self.lambdas,absorbance,pen=pg.mkPen(color=self.colors[N-1]))
        #self.all_abs_plot.setData(self.lambdas,absorbance)
        #intensity
        self.all_intensity_plot=self.all_intensity.plot(self.lambdas,intensity,pen=pg.mkPen(color=self.colors[N-1]))
        #self.all_intensity_plot.setData(self.lambdas,intensity)
    
    #volume, pH and times
    def append_vol_in_table(self,nb,vol): #nb numero de mesure 1 à Nmes
        self.table_vol_pH[nb-1][0].setObjectName("vol"+str(nb))
        self.table_vol_pH[nb-1][0].setAlignment(QtCore.Qt.AlignCenter)
        self.grid_mes_pH_vol.addWidget(self.table_vol_pH[nb-1][0], nb, 0, 1, 1)
        self.table_vol_pH[nb-1][0].clear()
        self.table_vol_pH[nb-1][0].setText(str(vol))
    
    def append_pH_in_table(self,nb:int,pH:str): #nb=numero de la mesure 1 à Nmes
        """adds pH measures in table"""
        self.table_vol_pH[nb-1][1].setObjectName("pH"+str(nb))
        self.table_vol_pH[nb-1][1].setAlignment(QtCore.Qt.AlignCenter)
        self.grid_mes_pH_vol.addWidget(self.table_vol_pH[nb-1][1], nb, 1, 1, 1)
        self.table_vol_pH[nb-1][1].clear()
        self.table_vol_pH[nb-1][1].setText(pH)

    def append_time_in_table(self,nb,dt):
        self.table_vol_pH[nb-1][2].setObjectName("dt"+str(nb))
        self.table_vol_pH[nb-1][2].setAlignment(QtCore.Qt.AlignCenter)
        self.grid_mes_pH_vol.addWidget(self.table_vol_pH[nb-1][2], nb, 2, 1, 1)
        self.table_vol_pH[nb-1][2].clear()
        self.table_vol_pH[nb-1][2].setText(str(dt))

    def pause(self):
        self.pause_resume_button.setIcon(QtGui.QIcon(play_icon_path))

    def resume(self):
        self.pause_resume_button.setIcon(QtGui.QIcon(pause_icon_path))

    def closeEvent(self, event):
        print("User has clicked the red x on the custom sequence window")
        #test : ça ne permet pas de supprimer l'objet 
        event.accept()
        self.seq.stop()
        self.ihm.updateDefaultParam()
        self.close()
        #self.__del__()
    
    """def __del__(self):
        pass"""