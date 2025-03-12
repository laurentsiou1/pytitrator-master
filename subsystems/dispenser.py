"Classe SyringePump"

from Phidget22.Phidget import *
from Phidget22.Devices.VoltageInput import *
from Phidget22.Devices.DigitalInput import *
from Phidget22.Devices.DigitalOutput import *
from Phidget22.Devices.Stepper import *
import time
import dispense_data

from configparser import ConfigParser
import os
from pathlib import Path

path = Path(__file__)
ROOT_DIR = path.parent.parent.absolute() #répertoire pytitrator
app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini")
device_ids = os.path.join(ROOT_DIR, "config/device_id.ini")

"""def volumeToAdd_uL(current, target, model='fixed volumes', atmosphere=True): #pH courant et cible, modèle choisi par défaut le 5/05
    if model=='5th order polynomial fit on dommino 23/01/2024':
        vol = dispense_data.get_volume_to_dispense_uL(current,target)
    elif atmosphere==False:
        vol = dispense_data.get_volume_to_dispense_uL(current,target)
        #Compléter avec les données issues des mesures IPGP avec bullage N2.
    return int(vol)"""

def getPhStep(current):
    #fonction donnant le pas de pH à viser en fonction du pH. 
    #fonction affine en deux parties. C'est un triangle. 
    #A pH4 le pas est de 0.3. Il est de 0.5 à pH6.5 et de 0.4 à pH10
    if current<=6.5:
        step=0.08*current-0.02
    else:
        step=-0.028*current+0.68
    return step

def identifier(x):
    if x==0:
        y='A'
    elif x==1:
        y='B'
    elif x==2:
        y='C'
    elif x=='A':
        y=0
    elif x=='B':
        y=1
    elif x=='C':
        y=2
    else:
        y='error'
    return y

def getChannel():
    if 'valve_in':
        ch=0
    elif 'valve_out':
        ch=1
    elif 'valve_A':
        ch=2
    elif 'valve_B':
        ch=3
    elif 'valve_C':
        ch=4
    return ch

def tobool(str):
    if str=='True' or str=='true':
        b=True
    else:
        b=False
    return b

class VolumeCount:

    def __init__(self):
        self.added_total_uL = 0
    
    def add(self, vol):
        self.added_total_uL+=vol

    def reset(self):
        self.added_total_uL = 0

class Dispenser:
    
    def __init__(self):
        self.vol=VolumeCount()
        self.syringe_A=PhidgetStepperPump('A',self.vol)
        self.syringe_B=PhidgetStepperPump('B',self.vol)
        self.syringe_C=PhidgetStepperPump('C',self.vol)
        self.syringes=[self.syringe_A,self.syringe_B,self.syringe_C]
        self.use=[self.syringe_A.use,self.syringe_B.use,self.syringe_C.use]
        self.update_infos()
        self.state='closed'
    
    def update_param_from_file(self):
        self.syringe_A.update_param_from_file()
        self.syringe_B.update_param_from_file()
        self.syringe_C.update_param_from_file()
    
    def update_infos(self):
        self.refresh_state()
        self.infos=self.syringe_A.infos+"\n"+self.syringe_B.infos+"\n"+self.syringe_C.infos

    def refresh_state(self):
        connected=0
        use=0
        for syr in self.syringes:
            if syr.use==True:
                use=1
                if syr.state=='closed':
                    connected=-10
                    break
                else:
                    connected=1
            else:
                pass
        if use==1 and connected==1:
            self.state='open'
        else:
            self.state='closed'
        return self.state

    def connect(self):
        if self.use[0]:
            self.syringe_A.connect()
        if self.use[1]:
            self.syringe_B.connect()
        if self.use[2]:
            self.syringe_C.connect()
        self.refresh_state()
        self.update_infos()
    
    def refill_empty_syringes(self):
        for syr in self.syringes:
            if syr.state=='open' and syr.level_uL<syr.size:   #not empty
                syr.full_refill()

    def stop(self):
        for syr in self.syringes:
            syr.stopSyringe()
        print("Stop dispenser")
    
    def close(self):
        self.syringe_A.close()
        self.syringe_B.close()
        self.syringe_C.close()
        print('Closing dispenser')
        self.state='closed'

#global
GAIN_ON_PH_STEP = 0.5

class SyringePump(Dispenser): #Nouvelle classe SyringePump globale : classe mère

    mode = 'manual' #peut être 'titration'

    #niveau courant
    level_uL=0

    #monitoring de la dispense sur le titrage
    added_vol_uL = 0
    
    acid_dispense_log = []
    base_dispense_log = []
    
    def __init__(self, model):
        if model=='Phidget':
            self.model='Stepper Phidget'
            PhidgetStepperPump.__init__(self)
        elif model=='Legato':
            self.model='KDSLegato100'
            KDS_Legato100.__init__(self)
        else:
            self.model='unknown'

class PhidgetStepperPump(SyringePump): #remplace l'ancienne classe SyringePump
    
    parser = ConfigParser()
    parser.read(device_ids)
    board_number = int(parser.get('main board', 'id'))
    VINT_number = int(parser.get('VINT', 'id'))
    port_a = int(parser.get('VINT', 'stepper_a'))
    port_b = int(parser.get('VINT', 'stepper_b'))
    port_c = int(parser.get('VINT', 'stepper_c'))

    def __init__(self,id,vol,syringe_type='Trajan SGE 500uL'): #par défaut une Trajan SGE 500uL
        
        self.vol=vol
        self.added_vol_uL=0

        self.stepper = Stepper() #contrôle du stepper
        self.security_switch = DigitalInput() #interrupteur bout de course seringue   
        self.reference_switch = DigitalInput() #interrupteur pour positionnement de référence
        self.electrovalve = DigitalOutput() #contrôle électrovannes

        parser2 = ConfigParser()
        parser2.read(device_ids)
        #print("device_ids : ", device_ids)
        
        self.stepper.setDeviceSerialNumber(self.VINT_number)  #683442
        
        self.syringe_type=syringe_type
        if syringe_type=='Trajan SGE 500uL':
            self.size = 400 #uL : useful volume on syringe
            #uL use only 400 on a 500uL syringe
            #Pour ne pas toucher le bout de la seringue
        else:
            pass

        self.model='Phidget Stepper STC1005_0'
        self.id=id
        
        if id=='A':
            self.stepper.setHubPort(self.port_a)
            self.stepper.setChannel(0)
            self.ch_full=int(parser2.get('switchs','full_A'))
            self.ch_empty=int(parser2.get('switchs','empty_A'))
            self.ch_valve=int(parser2.get('relay','valve_A'))
            self.id='Syringe A'
            #print(id,'interrupteurs sur DigitalInputs ',self.ch_full,self.ch_empty,'electrovalve sur sortie relai ',self.ch_valve)
        elif id=='B':
            self.stepper.setHubPort(self.port_b)
            self.stepper.setChannel(0)
            self.ch_full=int(parser2.get('switchs','full_B'))
            self.ch_empty=int(parser2.get('switchs','empty_B'))
            self.ch_valve=int(parser2.get('relay','valve_B'))
            self.id='Syringe B'
            #print(id,self.ch_full,self.ch_empty,self.ch_valve)
        elif id=='C':
            self.stepper.setHubPort(self.port_c)
            self.stepper.setChannel(0)
            self.ch_full=int(parser2.get('switchs','full_C'))
            self.ch_empty=int(parser2.get('switchs','empty_C'))
            self.ch_valve=int(parser2.get('relay','valve_C'))
            self.id='Syringe C'
            #print(id,self.ch_full,self.ch_empty,self.ch_valve)
        #print("Syringe", id,': switchs full/empty on DigitalInputs ',self.ch_full,"/",self.ch_empty,'\nelectrovalve on relay pin',self.ch_valve)
        self.state='closed'
        self.infos=self.id+" : "+self.state

        self.update_param_from_file()
        #print("syringe",id,self.use,self.reagent,self.concentration, self.level_uL)

    def update_param_from_file(self):
        parser = ConfigParser()
        parser.read(app_default_settings)
        self.rescale_factor=float(parser.get(self.id, 'rescale_factor'))
        self.offset_ref=int(parser.get(self.id, 'offset_ref'))
        self.use=tobool(parser.get(self.id, 'use'))
        self.reagent=parser.get(self.id, 'reagent') #string
        self.concentration=float(parser.get(self.id, 'concentration'))
        self.level_uL=round(float(parser.get(self.id, 'level')))

    def connect(self):
        print("connecting syringe",self.stepper,self.id,self.ch_full,self.ch_empty,self.ch_valve,\
            self.stepper.getHubPort(),self.stepper.getChannel(),self.stepper.getDeviceSerialNumber())
        #Stepper
        try:
            self.stepper.openWaitForAttachment(4000)
            print("stepper "+self.id+" connected")
            print("limite de courant actuelle : ", self.stepper.getCurrentLimit())
            self.stepper.setCurrentLimit(0.4) #0.1A
            print("limite de courant après réglage : ", self.stepper.getCurrentLimit())
            self.stepper.setVelocityLimit(20)
            print("limite de vittesse stepper : ", self.stepper.getVelocityLimit())
            self.stepper.setAcceleration(3)
            print("acceleration stepper : ", self.stepper.getAcceleration())
            
            #rescale factor calculé le 25/01/2024
            print("le syringe type est bon")
            self.stepper.setRescaleFactor(self.rescale_factor) 
            #rescale factor = -0.013115 avant 25/01/2024
            #rescale factor = -0.01298 le 30/08/2024 pour le pas B
            #baisser le rescale factor augmente la course
            #450uL dispensés sur une échelle de 30500 positions avec scale factor=1
            #soit 76,25 microsteps pour 1 uL.     
            print("rescale factor = ", self.stepper.getRescaleFactor())
        except:
            print("stepper "+self.id+": not connected")
        
        #Interrupteurs, electrovalve
        self.security_switch.setDeviceSerialNumber(self.board_number)  #452846
        self.security_switch.setChannel(self.ch_empty)
        disp="security switch : "
        try:
            self.security_switch.openWaitForAttachment(1000)
            disp+="on"
        except:
            disp+="off"
        print(disp)
        self.reference_switch.setDeviceSerialNumber(self.board_number)
        self.reference_switch.setChannel(self.ch_full)
        disp="reference switch : "
        try:
            self.reference_switch.openWaitForAttachment(1000)
            disp+="on"
        except:
            disp+="off"
        print(disp)
        self.electrovalve.setDeviceSerialNumber(self.VINT_number)
        self.electrovalve.setHubPort(4)     #modifier pour mettre la valeur du fichier de cablage
        self.electrovalve.setChannel(self.ch_valve)
        disp="electrovalve : "
        try:
            self.electrovalve.openWaitForAttachment(1000)
            disp+="on"
        except:
            disp+="off"
        print(disp)
        if (self.stepper.getIsOpen() and self.security_switch.getIsOpen() and \
        self.reference_switch.getIsOpen() and self.electrovalve.getIsOpen()):
            self.state='open'
            self.infos=self.id+" : "+self.state+"\nSyringe : "+self.syringe_type\
                +"\nReagent : "+self.reagent+"\nConcentration : "+str(self.concentration)+" mol/L"
        else:
            self.state='closed'
        #L'attribut state ne garantit pas que tous les appareils passifs sont branchés
        #Il s'agit seulement des Phidgets
        #Cela permet de ne pas avoir d'erreurs lors de l'exécution mais ne garantit pas 
        #qu'un interrupteur de sécurité ne soit mal branché. 

        if self.state=='open':
            self.reference_switch.setOnStateChangeHandler(self.stop_syringe_full)
            self.security_switch.setOnStateChangeHandler(self.stop_syringe_empty)   
            self.mode='normal'         
            self.purging=False

    def set_valve_state(self, bool):
        self.electrovalve.setState(bool)
    
    def get_valve_state(self):
        try:
            state=self.electrovalve.getState()
        except:
            state=False
        return state

    def stop_syringe_full(self, reference_switch, state):
        print("state change on full syringe switch :", state)
        if state == False:
            self.stepper.setEngaged(False)
            print("reference switch hit - motor stop")
            time.sleep(1) #stabilisation du moteur
            if self.mode=='normal':
                print("going to zero position")
                self.go_to_ref_position()
            elif self.mode=='purge':
                print("full dispensing")
                self.full_dispense()
        else:
            print("switch closes again")

    def stop_syringe_empty(self, security_switch, state):
        print("state change on empty syringe switch :", state)
        if state == False: #switch has just opened
            #print("security stop \nself:",self,"security_switch:",security_switch,"state",state)
            self.stepper.setEngaged(False)
            print("empty switch hit - motor stop")
            if self.mode=='normal':
                print("go to zero position")
                self.go_to_zero_position()
            elif self.mode=='purge':
                print("full refilling")
                self.full_refill()
        else:
            print("switch closes again")

    def go_to_ref_position(self):
        self.configForDispense(ev=0)
        #offset_ref depends on each syringe pump. Its value in uL is set in app_default_settings.
        self.stepper.setTargetPosition(self.stepper.getPosition()+self.offset_ref) 
        self.stepper.setEngaged(True)
        while(self.stepper.getIsMoving()==True):
            pass
        self.stepper.setEngaged(False)
        time.sleep(1) #stabilisation méca du stepper
        self.setReference()
        print("Plunger back in reference position - ready for dispense")
    
    def go_to_zero_position(self):
        self.simple_refill(54) #54uL ajusté à l'oeil
        self.level_uL=0
    
    def validity_code(self):
        target=self.stepper.getTargetPosition()-self.stepper.getPosition()
        time.sleep(1)   #time for reading on switches
        state0=self.reference_switch.getState()
        state1=self.security_switch.getState()
        #print("state1, state0 :", state1, ",", state0)
        #cas général : aucun interrupteur enfoncé, tout mouvement est possible
        if state1==True and state0==True: #les sécurités sont fonctionnelles
            #print("motor in the middle at start")
            code=0
            if abs(target)>=1:
                valid=True
            else:
                valid=False
        #interrupteur de référence enfoncé
        elif state1==True and state0==False:    
            print("reference switch is pushed")
            code=1
            if target>=1:
                valid=True
            else: 
                print("wrong direction - end of pitch")
                valid=False
        #interrupteur de sécurité enfoncé 
        elif state1==False and state0==True:
            print("security switch is pushed")
            code=2
            if target<=-1:
                valid=True
            else: 
                print("wrong direction - end of pitch")
                valid=False
        else:
            code=3
            valid=False
            print("Switches not connected - No dispense")   
        return code, valid
    
    def configForDispense(self,ev=1): #ev=1 electrovalve en position de dispense
        #paramètres stepper
        self.stepper.setCurrentLimit(0.4)
        self.stepper.setAcceleration(2)
        self.stepper.setVelocityLimit(15)
        #print("config pour dispense : \n\
        #    vitesse limite = ",self.stepper.getVelocityLimit(),"\n\
        #    limite en courant (A) : ", self.stepper.getCurrentLimit() )
        if ev==1:#electrovalve sur le mode dispense
            time.sleep(1)
            self.electrovalve.setState(True)
            print("electrovalve state : ",self.electrovalve.getState())
            time.sleep(1)

    def configForRefill(self): #ev=0 electrovalve en position de recharge
        #paramètres stepper
        self.stepper.setCurrentLimit(0.4)
        self.stepper.setAcceleration(3)
        self.stepper.setVelocityLimit(20)
        #print("config pour recharge : \n\
        #    vitesse limite = ",self.stepper.getVelocityLimit(),"\n\
        #    limite en courant (A) : ", self.stepper.getCurrentLimit() )
        if self.electrovalve.getState()==True: #toujours mettre l'electrovalve off pour recharger
            time.sleep(1)
            self.electrovalve.setState(False)
            time.sleep(1)

    #def configForPurge(self):


    def simple_dispense(self,vol,ev=1):
        pos0 = self.stepper.getPosition()
        #print("position avant dispense : ",pos0)
        if ev==1:
            pass
            #print("syringe level before dispense = ",self.level_uL)
        else:
            pass
            #print("syringe level before unfill = ", self.level_uL)
        disp=False #par défaut, avant dispense : pas encore de dispense effectuée
        if vol >= 0:     #and vol <= self.size-pos0+10:   
            #+10 est une marge pour pouvoir dépasser légèrement le niveau complet     
            self.configForDispense(ev)
            self.stepper.setTargetPosition(pos0+vol)
            #lancement
            code,valid=self.validity_code()
            if valid:
                self.stepper.setEngaged(True)
                while(self.stepper.getIsMoving()==True):
                    pass
                time.sleep(1) #stabilisation méca du steper
                self.stepper.setEngaged(False)
                self.electrovalve.setState(False) #On repasse en mode recharge (electrovalve hors tension)
                time.sleep(1)
                #affichage de la position atteinte
                position = self.stepper.getPosition()
                delta=round(position-pos0)
                self.level_uL-=delta
                print("Niveau courant :", delta)
                #print("Position atteinte après dispense: ", position)
                #print("syringe level = ",self.level_uL)
                if ev==1 and self.mode=='normal':
                    self.added_vol_uL+=delta
                    self.vol.add(delta)
                    self.base_dispense_log.append(delta)
                    disp=True #seulement si toutes les conditions sont réunies, la dispense\
                    #aura eu lieu
        elif vol<0:
            print("Unable to dispense : negative volume")
        else:   #volume trop grand
            print("Dispense with mulitple stages")
        return disp #bool about dispense was achived or not 
    
    def dispense(self, vol):
        #prévoir le cas où le piston touche le bout (car mauvaise valeur de position initiale)
        # 
        # il faut savoir compter la quantité lors de l'arrêt. 
        # Puis recharger
        # Puis reprendre la dispense là où elle s'est arrêtée. 

        print("starting dispense %f uL" %vol)
        capacity=self.size
        level=self.level_uL
        q=int(vol//capacity)
        r=vol%capacity
        print(q,"x",self.size,"+",r,"uL")
        if vol<=level: #cas classique de simple dispense
            self.simple_dispense(vol)
        else:   #vol>level #dispense with multiple stages
            r2=r-level
            #print("r2=",r2)
            if r2<=0: #r<=level     #On peut dispenser le reste sans recharger
                #donc on commence par dispenser le reste
                self.simple_dispense(r)
                self.full_refill()
                #puis les dispenses entières
                for i in range(q):
                    self.simple_dispense(capacity)
                    self.full_refill()
            else: #r>level:     #Le reste est supérieur au niveau de la seringue
                #print("recharge pour dispense du reste")
                self.full_refill()
                self.simple_dispense(r)
                self.full_refill()
                for i in range(q):
                    self.simple_dispense(capacity)
                    self.full_refill()
        #self.vol.add(vol)   #update in volume tracking
        print("end of dispense\n")

    def standard_dispense_for_calib(self):
        print("400uL target dispense for calibration")
        self.dispense(400)  #visée 400uL
    
    def compute_rescale_factor(self,reached_uL):
        current_factor=self.rescale_factor
        new_factor=(reached_uL/400)*current_factor  #new rescale_factor
        self.rescale_factor=new_factor
        print("Syringe",self.id,":\nRescale factor has been ajusted from %f to %f \n \
              Now you can ajust the reference offset" % (current_factor,new_factor))

    def simple_refill(self,vol):   
        pos0=self.stepper.getPosition()
        self.configForRefill()
        self.stepper.setTargetPosition(pos0-vol) #recharge donc target supérieur à position courante
        #lancement
        code,valid=self.validity_code()
        if valid:
            self.stepper.setEngaged(True)
            #print("start of movement")
            while(self.stepper.getIsMoving()==True): #getEngaged
                pass
            #print("end of movement")
            time.sleep(1)
            self.stepper.setEngaged(False)
            #affichage de la position atteinte
            position = self.stepper.getPosition()
            #print("Position atteinte après recharge: ", position)
            delta=round(position-pos0)
            self.level_uL-=delta #delta est negatif
            print("Niveau courant :",self.level_uL)
    
    def full_refill(self):
        pos0=self.stepper.getPosition()
        self.configForRefill()
        self.stepper.setTargetPosition(pos0-2*self.size) #recharge donc target supérieur à position courante
        #lancement
        code,valid=self.validity_code()
        if valid:
            self.stepper.setEngaged(True)
            while(self.stepper.getIsMoving()==True):
                pass
            #time.sleep(20) #attente que le moteur se remette sur la référence
        
    def full_dispense(self):
        self.simple_dispense(2*self.size)   #dispense jusqu'à la position d'arrêt avec l'interrupteur
    
    def setReference(self): #permet de remettre à zéro la position mesurée par le stepper
        pos=self.stepper.getPosition()
        #print("position du moteur avant remise à zéro : ",pos)
        self.stepper.addPositionOffset(-pos)
        pos1=self.stepper.getPosition()
        self.level_uL=self.size
    
    def purge(self):
        if self.mode=='normal': #not currently purging
            self.mode='purge'
            print("Start purge")  
            self.full_refill()
        elif self.mode=='purge':
            self.mode='normal'
            print("last movement before end of purge")

    def close(self):
        self.stopSyringe()
        self.stepper.close()
        self.security_switch.close()
        self.reference_switch.close()
        self.electrovalve.close()
        print('Closing syringe pump ',self.id)
        self.state='closed'
    
    def stopSyringe(self):
        if self.state=='open':
            self.stepper.setEngaged(False)

if __name__=="__main__":
    sp=PhidgetStepperPump()
    sp.connect()
    sp.full_refill()
    sp.dispense(100)
    #sp.setZeroPosition()
    #sp.simple_refill(50)
    #sp.simple_dispense(100,0)


class KDS_Legato100(SyringePump):
    #Le pousse seringue doit être configuré en amont avec la bonne seringue

    def __init__(self):
        self.ser=serial.Serial('COM3', timeout = 2, stopbits=2)  #COM3 peut changer, à vérifier
        print(self.ser)
        self.dir = DigitalInput() #direction courante
        self.dir.setDeviceSerialNumber(self.board_number)
        self.dir.setChannel(7)
        self.movement = DigitalInput() #mouvement en cours ou pas
        self.movement.setDeviceSerialNumber(self.board_number)
        self.movement.setChannel(5)
        self.electrovalve=DigitalOutput() #contrôle electrovalve
        self.electrovalve.setDeviceSerialNumber(self.board_number)
        self.electrovalve.setChannel(0)
        try:
            self.dir.openWaitForAttachment(1000)
            self.movement.openWaitForAttachment(1000)    
            self.electrovalve.openWaitForAttachment(1000) 
        except:
            pass
        
        self.size=300    #définition de la courser complète (en mL)
    
    def setValveOnRefill(self):
        time.sleep(1)
        self.electrovalve.setState(False)
        time.sleep(1)
    
    def setValveOnDispense(self):
        time.sleep(1)
        self.electrovalve.setState(True)
        time.sleep(1)

    def send(self,cmd): #envoyer une commande en RS232
        command=cmd+"\r"
        command_ascii=[]
        for ch in command:
            ch3=ord(ch) #code ascii
            #print(ch, ch3)
            command_ascii.append(ch3)
        #print(command_ascii)
        bytes_command=bytearray(command_ascii) #conversion en bytes
        #print(bytes_command)
        self.ser.write(bytes_command) #renvoie le byte string given 
        y=0
        x=self.ser.in_waiting
        while(y==0 or x!=0):
            if x > 0:
                #print("ser.in_waiting=",x)
                out = self.ser.read(100)
                answer=out.decode()
                y=1
            else:
                y=0
                pass
            x=self.ser.in_waiting
        print(answer)
        #print(out)
    
    def waitForStop(self):
        #attendre le signal de la seringue annonçant le moteur s'arrete
        mv=self.movement.getState()
        #print("mv=",mv)
        if mv==True:
            print("start of movement")
            while(self.movement.getState()==True):
                pass
            print("end of movement")
        else:
            print("no movement")

    def simple_dispense(self,vol,pos):
        self.setValveOnDispense()
        stroke=self.size-pos
        if vol>stroke:
            print("erreur : ne peut pas faire une simple dispense")
        else: #vol<=stroke
            if vol!=0:
                self.send("cvolume") #impératif pour pas avoir le message erreur
                print("simple dispense of %d uL"%vol)
                self.send("tvolume %d u" %vol)
                self.send("irun")
                self.waitForStop()
            else: #volume nul 
                pass   
            ending_position=pos+vol    
            return ending_position
            
    def dispense(self,vol,pos): 
        # vol: volume (uL) 
        # pos: position avant dispense (uL)  /!\ impératif /!\
        stroke=self.size-pos #le type de dispense en dépend
        
        #dispense simple
        if vol<=stroke: 
            ending_position=self.simple_dispense(vol,pos)
        
        #dispense en plusieures parties
        else: 
            #Calcul des quatités
            vol2=vol-stroke #reste à dispenser après un aller en bout de course
            q=vol2//self.size;r=vol2%self.size
            print("Déroulé de la dispense :\nvolume=%duL (bout de course) \n+%d*%duL (nombre de courses)\
                   \n+%duL (dernière dispense)" % (stroke, q, self.size ,r))
            
            #Première dispense jusqu'en bout de course
            self.simple_dispense(stroke, pos)
            print("première dispense de %d uL effectuée"%stroke)
            #input("Tapez entrée pour recharger")
            self.refill(self.size)
            #input("Taper entrée pour dispenser")
            
            #dispenses course complète
            for n in range(q):
                self.simple_dispense(self.size,0)
                print(" %d dispense(s) sur course complète effectuée(s) sur %d"%(n+1,q))
                #input("taper entrée pour recharger") #les input seront 
                #à remplacer par des commandes sur l'électrovanne pour security_switcher (dispense/recharge)
                self.refill(self.size)
                #input("taper entrée pour dispenser")

            #dernière dispense avec le reste
            self.simple_dispense(r,0)   
            print("dernière dispense de %d uL effectuée"%r)
            ending_position=r #remainder of euclidian division 
        
        print("ending position : %d"%ending_position)
        return ending_position

    def refill(self,pos):
        self.setValveOnRefill()
        if (self.electrovalve.getState()==False): #Attention à ne pas recharger la seringue avec
            #l'électrovanne en position dispense. La valve anti-retour va bloquer et la seringue 
            #soit va caler, soit va prendre de l'air où elle peut (donc bulles) soit va endommanger la
            #valve anti retour. 
            self.send("cvolume")
            self.send("tvolume %d u" %pos)
            self.send("wrun")
            self.waitForStop()



    """def run_sequence(self,seq):
    # seq est une liste de volumes en microlitres [50, 30, 20, 10, 15, 30, 80, 200] par exemple
        a=input("Voulez-vous recharger la seringue ? 'y' for YES, any key otherwise : ")
        #Recharge optionnelle au début
        if a=='y':
            self.refill(self.size)
        else:
            pass
        pos=0 #position courante de la seringue
        #séquence de dispenses
        for vol in seq:
            #("taper entrée pour dispenser la séquence suivante")
            #if volume_count<=self.size:
            end_pos=self.dispense(vol,pos) 
            pos=end_pos
            print("position courante: ", pos)
        #input("Taper entrée pour remettre la seringue en position initiale")
        self.refill(pos) #remet en position initiale"""


