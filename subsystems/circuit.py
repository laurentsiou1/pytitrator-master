"Class for controlling pump motor along with electrovalves of measure circuit"

#from Phidget22.Devices.DigitalOutput import *

from subsystems.peristalticPump import PeristalticPump
from subsystems.electrovalve import Electrovalve

from configparser import ConfigParser
import os
from pathlib import Path

path = Path(__file__)
ROOT_DIR = path.parent.parent.absolute() #répertoire pytitrator
app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini")
device_ids = os.path.join(ROOT_DIR, "config/device_id.ini")

def require_pump_and_valves_connected(func):
    def wrapper(self, *args, **kwargs):
        if self.pump.state=='closed':
            raise Exception("Pump not connected")
        elif self.ev_state=='closed':
            raise Exception("Electrovalve not connected")
        return func(self, *args, **kwargs)
    return wrapper

class Circuit(): #la classe hérite des méthodes de la pompe

    def __init__(self, pump : PeristalticPump):   #pump est un objet de la classe pump, passé en argument
        
        self.pump=pump
        self.ev0 = Electrovalve('circuit entrance')
        self.ev1 = Electrovalve('circuit exit')
        self.state='closed'

    def connect(self):
        self.pump.connect()
        self.ev0.connect()
        self.ev1.connect()
        self.updateState()
        self.update_infos()
        print(self.infos)

    def updateState(self):
        if self.pump.state=='open' and self.ev0.channel_state=='open' and self.ev1.channel_state=='open':
            self.state='open'
        else:
            self.state='closed'
    
    def update_infos(self):
        self.pump.update_infos()
        self.infos=self.pump.infos
        if self.state=='open':
            self.infos+=("\nElectrovalves : Connected"
            +"\nEntrance valve ev0 : "+str(self.ev0.state)
            +"\nExit valve ev1 : "+str(self.ev1.state))
        else:
            self.infos+="\nElectrovalves not connected"
    
    def close(self):
        if self.pump.state=='open':
            self.pump.close_pump()
        self.ev0.close()
        self.ev1.close()
        self.state='closed'

    def ev0_changeState(self):
        self.ev0.changeState()

    def ev1_changeState(self):
        self.ev1.changeState()

    def ev0_display(self):
        pass
    
    """@require_pump_and_valves_connected
    def fillWater(self):
    
    @require_pump_and_valves_connected
    def cleanAndEmpty(self):"""