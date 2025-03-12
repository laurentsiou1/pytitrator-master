"""nouvelle version de titrationWindow"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QApplication
from graphic.windows.classic_seq_win import Ui_titrationWindow

import pyqtgraph as pg
from windows.spectrometry_window import SpectrometryWindow
import numpy as np
import matplotlib.pyplot as plt

import datetime
from file_manager import Data

class ClassicSequenceWindow(QMainWindow,Ui_titrationWindow):
    
    absorbance_spectrum1=None
    
    #renouvellement affichage
    timer_display = QtCore.QTimer()
    timer_display.setInterval(1000)
    
    def __init__(self, ihm, parent=None):
        super(ClassicSequenceWindow,self).__init__(parent)
        self.setupUi(self)
        self.ihm=ihm
        self.spectro_unit=ihm.spectro_unit
        self.phmeter=ihm.phmeter
        self.peristaltic_pump=ihm.peristaltic_pump

        ## Mise en forme de base
        #ajouts
        size=self.absorbance_tabs.size()
        rect=QtCore.QRect(QtCore.QPoint(0,0),size)
        self.delta_all_abs = pg.PlotWidget(self.tab1)
        self.delta_all_abs.setGeometry(rect)  #.geometry() #meme dimension que le contenant
        #mais position sur l'origine car le repère est relatif
        self.delta_all_abs.setObjectName("delta_all_abs")
        self.all_abs = pg.PlotWidget(self.tab2)
        self.all_abs.setGeometry(rect)
        self.all_abs.setObjectName("all_abs")
        self.absorbance_tabs.addTab(self.tab1, "delta") 
        self.absorbance_tabs.addTab(self.tab2, "raw abs")

        #spectre en direct
        self.direct_intensity = pg.PlotWidget(self.widget_direct)
        self.direct_intensity.setGeometry(QtCore.QRect(QtCore.QPoint(0,0),self.widget_direct.size())) #self.widget_direct.geometry())
        self.direct_intensity.setObjectName("all_abs")
        self.direct_intensity_plot=self.direct_intensity.plot([0],[0])

        self.timer_display.start()

        #Affichage dépendant de la configuration
        self.seq=self.ihm.seq
        self.N_mes=self.seq.N_mes
        #Paramètres d'expérience
        self.experiment_parameters.setPlainText("\nNom de l'expérience : "+str(self.seq.experience_name)\
        +"\nDescription : "+str(self.seq.description)\
        +"\nFibres : "+str(self.seq.fibers)\
        +"\nFlowcell : "+str(self.seq.flowcell)\
        +"\nDispense mode : "+str(self.seq.dispense_mode)\
        +"\nNombre de mesures : "+str(self.seq.N_mes)\
        +"\npH initial : "+str(self.seq.pH_start)\
        +"\npH final : "+str(self.seq.pH_end)\
        +"\nFixed delay for chemical stability: "+str(self.seq.fixed_delay_sec//60)+"minutes, "+str(self.seq.fixed_delay_sec%60)+"secondes\n"\
        "Agitation delay (pump stopped) : "+str(self.seq.mixing_delay_sec//60)+"minutes, "+str(self.seq.mixing_delay_sec%60)+"secondes\n\n")

        #Spectro
        if ihm.spectro_unit.state=='open':
            self.lambdas=self.spectro_unit.wavelengths 
            self.N_lambda=len(self.lambdas) 
        
        #refresh screen
        self.timer_display.timeout.connect(self.refreshScreen)
        
        #graphique
        cmap = plt.get_cmap('tab10')  # You can choose a different colormap
        aa = [cmap(i) for i in np.linspace(0, 1, self.N_mes)]
        self.colors = [(int(r * 255), int(g * 255), int(b * 255)) for r, g, b, _ in aa]

        #tableau pH,volume
        self.grid_all_pH_vol.addWidget(self.label_total_volume, 0, self.N_mes+1, 1, 1)
        self.grid_all_pH_vol.addWidget(self.total_volume, 1, self.N_mes+1, 1, 1)  
        
        #tableau de données QLabels à compléter au fil de l'expérience
        self.table_vol_pH=[[QtWidgets.QLabel(self.gridLayoutWidget_2) for k in range(self.N_mes+1)], \
                         [QtWidgets.QLabel(self.gridLayoutWidget_2) for k in range(self.N_mes)]]
        
        for j in range(1,self.N_mes+1): #1ère ligne : numeros de mesures
            #mes_j="mes"+str(j)
            self.mes_j = QtWidgets.QLabel(self.gridLayoutWidget_2)
            #self.mes_j.setObjectName(mes_j)
            self.grid_all_pH_vol.addWidget(self.mes_j, 0, j, 1, 1)
            self.mes_j.setText(str(j))

        #pompe
        if self.peristaltic_pump.state=='open':
            self.pump_speed_volt.setProperty("value", self.peristaltic_pump.current_speed)

        #pH meter
        self.stab_time.setProperty("value", self.phmeter.stab_time)
        self.stab_time.valueChanged.connect(self.seq.update_stab_time)
        self.stab_step.setProperty("value", self.phmeter.stab_step)
        self.stab_step.valueChanged.connect(self.seq.update_stab_step)

        #saving
        self.actionsave.triggered.connect(lambda : self.ihm.seq_data.createSequenceFiles(self.seq))

    #DIRECT
    def refresh_stability_level(self):
        self.stabilisation_level.setProperty("value", self.phmeter.stab_purcent)
        self.label_stability.setText(str(self.phmeter.stab_purcent)+"%")

    def refreshScreen(self):
        #Countdown
        try:
            tm=datetime.now()
            tm=tm.replace(microsecond=0)
            elapsed=tm-self.seq.time_mes_last
            elapsed_sec = elapsed.total_seconds() #convert to seconds
            remaining = int(max(0,self.seq.delay_mes-elapsed_sec))
            self.countdown.setProperty("value", remaining)
        except:
            pass
        #spectrometer
        if self.spectro_unit.state=='open':
            self.direct_intensity_plot.setData(self.lambdas,self.spectro_unit.current_intensity_spectrum)
        #PhMeter
        if self.ihm.phmeter.state=='open':
            self.direct_pH.display(self.ihm.phmeter.currentPH)
            self.stab_time.setProperty("value", self.ihm.phmeter.stab_time)
            self.stab_step.setProperty("value", self.ihm.phmeter.stab_step)
            self.stabilisation_level.setProperty("value", self.ihm.phmeter.stab_purcent)
            self.label_stability.setText(str(self.ihm.phmeter.stab_purcent)+"%")

    #spectre courant sur le graphe en delta 
    def update_spectra(self): #il y a déjà un spectre enregistré
        if self.spectro_unit.current_absorbance_spectrum!=None:
            self.current_abs_curve.setData(self.lambdas,self.spectro_unit.current_absorbance_spectrum)
            if self.absorbance_spectrum1!=None:
                #le spectre en delta est une donnée graphique, pas une donnée fondamentale
                self.current_absorbance_spectrum_delta=[self.spectro_unit.current_absorbance_spectrum[k]-self.absorbance_spectrum1[k] for k in range(self.N_lambda)]
                self.current_delta_abs_curve.setData(self.lambdas,self.current_absorbance_spectrum_delta)

    #ENREGISTREMENT

    #Spectres en delta
    def append_abs_spectra(self,N,spec,delta):
        print(spec[300:310],delta[300:310])
        #delta
        a=self.delta_all_abs.plot([0],[0],pen=pg.mkPen(color=self.colors[N-1])) #pen='g'
        a.setData(self.lambdas,delta)
        #abs
        b=self.all_abs.plot([0],[0],pen=pg.mkPen(color=self.colors[N-1]))
        b.setData(self.lambdas,spec)
    
    def append_vol_in_table(self,nb,vol): #nb numero de mesure 1 à Nmes
        self.table_vol_pH[0][nb-1].setObjectName("vol"+str(nb))
        self.grid_all_pH_vol.addWidget(self.table_vol_pH[0][nb-1], 1, nb, 1, 1)
        self.table_vol_pH[0][nb-1].clear()
        self.table_vol_pH[0][nb-1].setText(str(vol))
    
    #pH et volume
    def append_pH_in_table(self,nb,pH): #nb=numero de la mesure 1 à Nmes
        self.table_vol_pH[1][nb-1].setObjectName("pH"+str(nb))
        self.grid_all_pH_vol.addWidget(self.table_vol_pH[1][nb-1], 2, nb, 1, 1)
        self.table_vol_pH[1][nb-1].clear()
        self.table_vol_pH[1][nb-1].setText(str(pH))

    def append_total_vol_in_table(self,tot):
        #self.total_volume.
        self.grid_all_pH_vol.addWidget(self.table_vol_pH[0][self.N_mes], 1, self.N_mes+1, 1, 1)
        self.total_volume.clear()
        self.total_volume.setText(str(tot))