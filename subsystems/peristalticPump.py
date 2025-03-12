"Classe permettant de controller le moteur de pompe péristaltique"

from Phidget22.Phidget import *
from Phidget22.Devices.DCMotor import *
import time

from configparser import ConfigParser
import os
from pathlib import Path

path = Path(__file__)
ROOT_DIR = path.parent.parent.absolute() #répertoire pytitrator
app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini")
device_ids = os.path.join(ROOT_DIR, "config/device_id.ini")

"""def require_open(self, method):
        if self.state=='open':
            return method # Return the function unchanged, not decorated.
        return require_open(method)"""

def require_open(func):
    def wrapper(self, *args, **kwargs):
        if self.state=='open':
            return func(self, *args, **kwargs)
    return wrapper

class PeristalticPump(DCMotor): #Elle est créée comme une sous classe de DCMotor

    parser = ConfigParser()
    parser.read(device_ids)
    #board_number = int(parser.get('main board', 'id'))
    VINT_number = int(parser.get('VINT', 'id'))
    port_motor = int(parser.get('VINT', 'dc_motor'))

    def __init__(self):
        DCMotor.__init__(self)
        self.setDeviceSerialNumber(self.VINT_number)  #683442
        self.setChannel(0)
        self.setHubPort(self.port_motor)
        self.state='closed'
        self.duty_cycle=0
        self.current_speed=0
        self.direction=1 # +1 or -1 according to the direction
        self.circuit_delay_sec=30
        self.update_infos()

    def connect(self):
        try:
            self.openWaitForAttachment(4000)
            self.setCurrentLimit(1) #1A #security
            self.setAcceleration(0.5) #param
            parser = ConfigParser()
            parser.read(app_default_settings)
            voltage=parser.get('pump', 'speed_volts')
            self.mean_voltage=float(voltage)
            self.duty_cycle=self.mean_voltage/12
            self.target_speed=self.direction*self.duty_cycle
            self.current_speed=self.getTargetVelocity()
            self.state='open'
        except:
            self.state='closed'
        self.update_infos()
        #print(self.infos)

    def update_infos(self):
        if self.state=='open':
            self.infos=("\nPump model : Thomas Pumps SR25 DC Performance 12V - tubing Novoprene - 7ml/min"
            +"\nPeristaltic Pump : Connected"
            +"\nCurrent limit (A) : "+str(self.getCurrentLimit())
            +"\nAcceleration : "+str(self.getAcceleration())
            +"\nCircuit delay : "+str(self.circuit_delay_sec)+" seconds"
            +"\nCurrent speed (Volts) : "+str(self.mean_voltage)
            +"\nCurrent speed (1 to 5 scale) : "+str(self.volts2scale(self.mean_voltage))
            +"\nDirection : "+str(self.direction))
        else:
            self.infos="Peristaltic pump not connected"

    def get_current_speed(self):
        if self.state=='open':
            self.current_speed=self.getTargetVelocity()
        else:
            self.current_speed=0

    def setSpeed_voltage(self,v):
        self.mean_voltage=v
        self.duty_cycle=v/12
        self.target_speed=self.duty_cycle*self.direction
        if self.state=='open':
            self.current_speed=self.getTargetVelocity()
            #indentation rajoutée
            if self.current_speed!=0:   #pour pouvoir changer la vitesse sans reappuyer sur start
                self.setTargetVelocity(self.target_speed)
                print("speed set to ", self.target_speed)
        self.update_infos()

    def set_speed_scale(self,v):
        self.setSpeed_voltage(self.scale2volts(v))

    def scale2volts(self, speed_scale):   #speed scale = 1, 2, 3, 4, 5
        speed_volts = 2+2*speed_scale
        #print("speed volts = ", speed_volts)
        return speed_volts

    def volts2scale(self, speed_volts):   #speed volts = 4V, 6V, 8V, 10V, 12V
        speed_scale=int(0.5*(speed_volts-2))
        return speed_scale

    def start_stop(self):
        self.get_current_speed()
        if self.state=='open':
            if self.current_speed==0:
                self.setTargetVelocity(self.target_speed)
            else:
                self.setTargetVelocity(0) 

    @require_open
    def start(self):
        self.setTargetVelocity(self.target_speed)    
            #if self.state=='open':

    #@require_attribute('state', 'open')
    def stop(self):
        if self.state=='open':
            self.setTargetVelocity(0)

    #@require_attribute('state', 'open')
    def change_direction(self):
        self.stop()
        time.sleep(1)
        self.direction*=-1
        #self.start()

    def text(self):
        self.get_current_speed()
        if self.current_speed==0:
            text='Start'
        else:
            text='Stop'
        return text   
    
    def update_in_file(self):
        parser = ConfigParser()
        parser.read(app_default_settings)
        parser.set('pump','speed_volts', str(self.mean_voltage))
        file = open(app_default_settings,'w')
        parser.write(file)
        file.close()
    
    def close_pump(self):
        self.stop()
        self.update_in_file()
        self.state='closed'
        print("Peristaltic pump closed")

if __name__=="__main__":
    pump = PeristalticPump()
    pump.close()
