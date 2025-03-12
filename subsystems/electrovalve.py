"Class for electrovalves. It includes those of measure circuit and Syringe Pump circuits"

from Phidget22.Devices.DigitalOutput import *

from configparser import ConfigParser
import os
from pathlib import Path

path = Path(__file__)
ROOT_DIR = path.parent.parent.absolute() #répertoire pytitrator
app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini")
device_ids = os.path.join(ROOT_DIR, "config/device_id.ini")

class Electrovalve: 

    parser = ConfigParser()
    parser.read(device_ids)
    VINT_number = int(parser.get('VINT', 'id'))
    port_relay = int(parser.get('VINT', 'relay'))
    num_a = int(parser.get('relay', 'valve_a'))
    num_b = int(parser.get('relay', 'valve_b'))
    num_c = int(parser.get('relay', 'valve_c'))
    num_entrance = int(parser.get('relay', 'valve_in'))
    num_exit = int(parser.get('relay', 'valve_out'))

    def __init__(self,type):

        self.type=type
        self.channel=DigitalOutput()    #electrovalves
        self.channel.setDeviceSerialNumber(self.VINT_number)
        self.channel.setHubPort(self.port_relay)
        
        if type == 'syringe pump A':
            self.channel.setChannel(self.num_a)
        elif type=='syringe pump B':
            self.channel.setChannel(self.num_b)
        elif type=='syringe pump C':
            self.channel.setChannel(self.num_c)        
        elif type=='circuit entrance':
            self.channel.setChannel(self.num_entrance)        
        elif type=='circuit exit':
            self.channel.setChannel(self.num_exit)        
        
        #state of connexion of valve channel : 'open' or 'closed'
        #Physical state on solenoid : 'True' (means 12V or NC) or 'False' (means 0V or NO)
        self.channel_state='closed' 
        self.state=False    

    def connect(self):
        try:
            self.channel.openWaitForAttachment(1000)
            self.channel_state='open'
        except:
            self.channel_state='closed'
    
    def close(self):
        self.setState(False)
        self.channel.close()
        self.channel_state='closed'
    
    def getState(self):
        if self.channel_state=='open':
            if self.channel.getState()==True:
                self.state=True
            else:
                self.state=False
        else:
            self.state=False
        return self.state
    
    def setState(self,state):
        "state is a boolean"
        if self.channel_state=='open':
            self.channel.setState(state)
            self.state=state
    
    def changeState(self):
        if self.channel_state=='open':
            state=self.channel.getState()   #phidget function
            self.channel.setState(not(state))

    def state2Text(self,state):
        type=self.type
        #print(state,type)
        if state==True: 
            if type=='circuit entrance':
                text='WATER'
            elif type=='circuit exit':
                text='BIN'
            else:       #dispenser
                text='ON'
        else:
            if type=='circuit entrance':
                text='IN'
            elif type=='circuit exit':
                text='OUT'
            else:   #syringe pumps
                text='OFF'
        #print(text)
        return text
