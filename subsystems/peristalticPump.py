"Classe permettant de controller le moteur de pompe péristaltique"

from Phidget22.Phidget import *
from Phidget22.Devices.DCMotor import *
import time

from configparser import ConfigParser
import os # OS 
from pathlib import Path

path = Path(__file__)  # Chargemenet des fichiers de configuration 
ROOT_DIR = path.parent.parent.absolute() # Répertoire pytitrator - répértoire principal du projet
app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini") # réglage général de la pompe : speed_volts = 4 speed_scale = 1
device_ids = os.path.join(ROOT_DIR, "config/device_id.ini") # contient l'information du numéro de serie du VINT et Input/Output pompe où est branché la pompe

"""def require_open(self, method):
        if self.state=='open':
            return method # Return the function unchanged, not decorated.
        return require_open(method)"""

def require_open(func): # Vérifie si la pompe est bien connecté, ou non, avant d'exectuer la méthode - 
    def wrapper(self, *args, **kwargs): # décorateur 
        if self.state=='open': # Vérifie si l'objet est ouvert
            return func(self, *args, **kwargs) # Exectue la fonction d'origine si la fonction est bien ouverte
    return wrapper

class PeristalticPump(DCMotor): # Elle est créée comme une sous classe de DCMotor - récup les méthodes (fonctions) de la classe DCMotor codé par Phidget et les celle créé ici 

    parser = ConfigParser() 
    parser.read(device_ids)
    #board_number = int(parser.get('main board', 'id'))
    VINT_number = int(parser.get('VINT', 'id'))  # Viens récupèrer le numéro de série (id) du Vint utilisé via le fichier 'device_id.ini' + fct Confiparser
    port_motor = int(parser.get('VINT', 'dc_motor')) # récupère le portdu Vint où est connecté le DCMotor

    def __init__(self): # Initialisatin de la pompe ??? need plus d'explications - Constructeur
        DCMotor.__init__(self)
        self.setDeviceSerialNumber(self.VINT_number)  # Indique le numéro de série
        self.setChannel(0)
        self.setHubPort(self.port_motor)
        self.state='closed' # Etat
        self.duty_cycle=0 # Rapport cyclique 
        self.current_speed=0 # vitesse actuelle
        self.direction=1 # +1 or -1 according to the direction
        self.circuit_delay_sec=30 
        self.update_infos() # Charge les informations de la pompe

    def connect(self): # Connexion à la pompe 
        try:                                        # Tente d'ouvrir la connexion à la pompe 
            self.openWaitForAttachment(4000)
            self.setCurrentLimit(1) #1A #security
            self.setAcceleration(0.5) #param
            parser = ConfigParser()
            parser.read(app_default_settings)  # va chercher le chemin du fichier .ini "app-default_settings"
            voltage=parser.get('pump', 'speed_volts') # récupère l'information de "speed_volts" dans la braket [pump] du fichier de config
            self.mean_voltage=float(voltage)
            self.duty_cycle=self.mean_voltage/12
            self.target_speed=self.direction*self.duty_cycle   #  Calculs de vitesse ?
            self.current_speed=self.getTargetVelocity() # Renvoi un duty cycle (valeur entre -1 et 1)
            self.state='open'
        except:
            self.state='closed' # Met à jours "self.state" pour indiquer que la pompe est connectée
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
        """Retourne l'information de la vitesse de pompe"""
        if self.state=='open':
            self.current_speed=self.getTargetVelocity() # Instanciation de la methode methode "getTargetVelocity()" à la variable self.current_speed
        else:
            self.current_speed=0

    def setSpeed_voltage(self,v): # Mis à jours de la vitesse de la pompe
        self.mean_voltage=v
        self.duty_cycle=v/12
        self.target_speed=self.duty_cycle*self.direction # création d'un attribut pour pouvoir changer la vitesse ou la direction; pour ne pas redemarer la pompe...
        if self.state=='open':
            self.current_speed=self.getTargetVelocity()
            #indentation rajoutée
            if self.current_speed!=0:   #pour pouvoir changer la vitesse sans reappuyer sur start
                self.setTargetVelocity(self.target_speed)
                print("speed set to ", self.target_speed)
        self.update_infos()

    def set_speed_scale(self,v): # Convertit le scale en volt et on applique un setspeed avec la valeur en volt
        self.setSpeed_voltage(self.scale2volts(v))

    def scale2volts(self, speed_scale):   #speed scale = 1, 2, 3, 4, 5 correspondant à cf. plus bas 
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
                self.setTargetVelocity(self.target_speed) # Ici, SetTargetVelocity attend un valeur positive ou négative pour démarrer la pompe
            else:
                self.setTargetVelocity(0) 

    @require_open
    def start(self):    # Met la pompe en marche 
        self.setTargetVelocity(self.target_speed)    
            #if self.state=='open':

    #@require_attribute('state', 'open')
    def stop(self):      # Met la pompe à l'arret 
        if self.state=='open':
            self.setTargetVelocity(0) # on regle la valeur sur 0 pour faire un stop

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
    
    def update_in_file(self):  # Sauvegarde la vitesse actuelle de la pompe dans le fichier "app_default_settings" - alors prend la derniere valeurs ??? ou ca reset par default ?
        parser = ConfigParser()
        parser.read(app_default_settings)
        parser.set('pump','speed_volts', str(self.mean_voltage))
        file = open(app_default_settings,'w')
        parser.write(file)
        file.close()
    
    def close_pump(self): # Fermer la pompe. 
        self.stop() # appelle méthode pour stopper la pompe
        self.update_in_file() # apelle la méthode pour sauvegarder la vitesse de la pompe
        self.state='closed' # passe l'état de la pomp à fermer
        print("Peristaltic pump closed") # print sur la console 

if __name__=="__main__":  # Ce bloc du code est executé uniquement si "PeristalticPump.py" est lancé directement - via le run ou console 
    pump = PeristalticPump()
    pump.close() # la on applique une méthode à un objet - .close provient de DC motor certainement
# En Python, ce bloc garantit que le code à l'intérieur ne s'exécute pas si le fichier est importé dans un autre script.
# Ici, il sert à tester la classe PeristalticPump indépendamment du reste du projet.