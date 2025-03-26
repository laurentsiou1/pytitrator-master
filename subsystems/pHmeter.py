"Acquisition du pH"

"""https://pythonpyqt.com/pyqt-events/ créer des signaux"""

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject

from Phidget22.Phidget import *
from Phidget22.Devices.Log import *
from Phidget22.Devices.VoltageInput import *
#from Phidget22.Devices.PHSensor import *

import math
import numpy as np
from configparser import ConfigParser
import os
from pathlib import Path
import re

#Récupère le fichier des données de calibration par défaut
path = Path(__file__)
ROOT_DIR = path.parent.parent.absolute()
app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini") # va chercher le fichier de config "app_default_setttings" pour charger chemin de "last_cal.ini" + info [pHmeter]
#latest_cal = "config/latest_cal.ini"
cal_log = os.path.join(ROOT_DIR, "config/CALlog.txt") # infos de la derniere calibration du pH metre ???
device_ids = os.path.join(ROOT_DIR, "config/device_id.ini") # Input / Output carte d'interfacage

def volt2pH(a,b,U): #m: pente, c: ordonnée à l'origine
	#U=a*pH+b
	if a!=0:
		pH=(U-b)/a # Conversion par regression linéaire classique - n'utilise pas la datasheet du phmetre de phidget.
	else:
		pH=1000
	return round(pH,3)  

class CustomSignals(QObject):  # Définition de la classe CustomSignals qui hérite de la classeQObject (classe de base pour gérer les signaux et les évenements)
	stability_reached=pyqtSignal() # On déclares une variable de classe (stability_reached) qui contient un objet pyqtSignal.

class PHMeter:

	parser = ConfigParser()
	parser.read(device_ids)  # récupération des informations issue du fichier "device_ids"
	board_number = int(parser.get('main board', 'id'))   # numéro de série de la carte d'interfacage (int parce qu'on attend un nombre entier)
	#VINT_number = int(parser.get('VINT', 'id')) # numéro de série du Vint 
	ch_phmeter = int(parser.get('ph meter', 'electrode')) # entrée logique de l'électrode sur la carte d'interfacage 
	# print(ch_phmeter) - modif laulau 18.03.2025 pour savoir la valeur de ch_phmeter

	def __init__(self):
		self.U_pH = VoltageInput() #pH-mètre - récupère la tension issu du pHmetre
		self.state='closed' # pourquoi ? - définition d'une variable pour suivre l'état du capteur - #Etat initial : capteur non connecté

		self.stab_timer = QtCore.QTimer() # Timer pour surveiller la stabilité du pH
		self.stab_timer.setInterval(1000) # Vérification chaque seconde 
		self.stable=False # Variable pour savoir si le pH est stable
		self.stab_level=0 #pourcentage de stabilité
		parser = ConfigParser() # on utilise ConfigParser pour aller chercher les information dans le fichier "app_default_settings" et les récupérer
		parser.read(app_default_settings)
		self.stab_time = int(parser.get('phmeter', 'delta')) # int delta
		self.stab_step = float(parser.get('phmeter', 'epsilon')) # float epsilon
		self.stab_purcent = 0
		
		#Création d'un signal PyQt pour informer une fois lorsque l'electrode devient stable
		self.signals=CustomSignals()   
	
		print("default settings file:", app_default_settings)  # que fait exactement ce bout de code ?? pourquoi afficher ca ?
		parser = ConfigParser()
		parser.read(app_default_settings) # on vient lire le fichier "app_default_steeings" pour :
		self.relative_calib_path=parser.get('calibration', 'file') # récupérer les valeurs de la calibration - ces valeurs sont enregistré dans un fichier sauvé a chaque calibration faites.
		self.model=parser.get('phmeter', 'default')  # Ref du phmetre utilisé
		self.electrode=parser.get('electrode', 'default') # Ref de electrode utilisé

		self.update_infos()

	def connect(self):  # Définition d'une méthode, intitulé connect, utilisant self --> connexion du phmetre...
		
		#Ph mètre Phidget 1130_0 plugged in Voltage Input of main board
		"""Connexion du PhMetre Phidget 1130"""
		# Ici la boucle try sous python permet de d'executer un morceau de code et d'attraper les erreurs qui pourrait se produire (ici la non connexion du ph metre)
		# empechant le programme de s'areter brutalemen. En gros, ca "try" de se connecter et si ca marche pas, ca plante pas, mais execute la boucle "except" (= sauf, a l'expetion de...). 
		self.U_pH.setDeviceSerialNumber(self.board_number) # 
		self.U_pH.setChannel(self.ch_phmeter)
		try:
			self.U_pH.openWaitForAttachment(3000)	#beug lors de l'ouverture si pas sous tension (-> fait appel à la méthode de phiodget pour placer un delai)
			self.U_pH.setDataRate(3) # Pourquoi 3 ? --> Fait appel à la methode : "setDataRate" de Voltage Input pour fixer la fréquence d'échantillonage - fréquence à laquelle sont pris les mesures
			self.U_pH.setVoltageChangeTrigger(0.00001) #seuil de déclenchement (Volt) - change la valeur du pH quand il y a une variation de 5.10-5 V- ca change tt le temps vu les µV
			self.getCalData() # Fait appel à la methode défini ICI de "GetCalData" pour fixer les valeurs de calibrations 
			self.currentVoltage=self.U_pH.getVoltage()
			self.currentPH=volt2pH(self.a,self.b,self.currentVoltage)
			self.state='open'
			print("pH meter connected")	
		except:
			self.state='closed'
			print("pH meter disconnected")
		self.update_infos()

	def update_infos(self):
		if self.state=='open':
			self.infos=("Ph meter : "+self.state+"\nModel : phidget 1130"+"\nElectrode : "
			+self.electrode+"\nCurrent calibration data\ndate and time: "+self.CALdate
			+"\nNumber of points: "+str(self.CALtype)+"\nRecorded voltages: U4="+str(self.U1)
			+"V; U7="+str(self.U2)+"V; U10="+str(self.U3)+"V\nCurrent calibration coefficients: a="
			+str(self.a)+ "V; b="+str(self.b)+"V")
		else:
			self.infos="Ph meter : closed"

	"""def load_calibration(self,path):
		self.relative_calib_path=os.path.relpath(path, ROOT_DIR)
		#a faire récupérer le chemin relatif du fichier de calib
		#Changement dans le fichier contenant le chemin du fichier de calibration par defaut
		parser = ConfigParser()
		parser.read(app_default_settings)
		parser.set('calibration', 'file', str(self.relative_calib_path))
		#écriture du nouveau chemin de cal par défaut
		cal_path_file = open(app_default_settings,'w')
		parser.write(cal_path_file) 
		cal_path_file.close()"""
	
	def getCalData(self): # Récupères les dernieres valeurs de calibrations
		parser = ConfigParser()
		parser.read(self.relative_calib_path) # li les valeurs de calibrationd du fichier de calib (Cf. Ligne 67) - les valeurs sont stocké dans "relative_calib_path"
		self.CALmodel=parser.get('data', 'phmeter')
		self.CALelectrode=parser.get('data', 'electrode')
		self.CALdate=parser.get('data', 'date')
		self.CALtype=parser.get('data', 'calib_type')
		self.U1=float(parser.get('data', 'U1')) # on rentre les valeurs comme attribut de la classe PHMETER
		self.U2=float(parser.get('data', 'U2'))
		self.U3=float(parser.get('data', 'U3'))
		self.a = float(parser.get('data', 'a'))
		self.b = float(parser.get('data', 'b'))

	def doOnVoltageChange(self,ch,voltage): 
		#les arguments de cette fonctions ne peuvent pas être changés
		#self:PHMeter,ch:VoltageInput,voltage:float 
		self.currentVoltage=voltage 
		self.currentPH=volt2pH(self.a,self.b,self.currentVoltage)  
		#print(self.currentPH)
	
	def activatePHmeter(self):
		#si le voltagechangetrigger est à zéro, l'évènement se produit périodiquement
		self.U_pH.setOnVoltageChangeHandler(self.doOnVoltageChange)
	
	def onCalibrationChange(self):
		parser = ConfigParser()
		parser.read("config/latest_cal.ini")
		self.CALmodel=parser.get('data', 'phmeter')
		self.CALelectrode=parser.get('data', 'electrode')
		self.CALdate=parser.get('data', 'date')
		#c'est un string : à convertir en set puis à ordonner
		l=re.findall(r'\d+',parser.get('data', 'calib_type'))
		ll=[int(x) for x in l]
		self.CALtype=sorted(ll)
		self.U1=float(parser.get('data', 'U1'))
		self.U2=float(parser.get('data', 'U2'))
		self.U3=float(parser.get('data', 'U3'))
		self.a = float(parser.get('data', 'a'))
		self.b = float(parser.get('data', 'b'))
		print(self.CALdate, "calibration change on ph meter")
		self.update_infos()
	
	def saveCalData(self,date,caltype,u_cal,coeffs): # metehode permettant de sauvegarder les fichiers de calibrations ?? ou initilation pour sauvegarde ?
		parser = ConfigParser()
		parser.read("config/latest_cal.ini")
		parser.set('data', 'phmeter', str(self.model))
		parser.set('data', 'electrode', str(self.electrode))
		parser.set('data', 'date', str(date)) 
		parser.set('data', 'calib_type', str(caltype))
		try:
			parser.set('data', 'U1', str(float(u_cal[0])))
			parser.set('data', 'U2', str(float(u_cal[1])))
			parser.set('data', 'U3', str(float(u_cal[2])))
		except:
			pass
		parser.set('data', 'a', str(float(coeffs[0])))
		parser.set('data', 'b', str(float(coeffs[1])))
		
		file = open("config/latest_cal.ini",'w')	#qu'est-ce qu'apporte r+ ou lieu de w
		parser.write(file) 
		file.close()

		#sauvegarde de toutes les calibration
		oldCal = open(cal_log, "a")
		oldCal.write("pH meter : "+str(self.CALmodel)+"\npH probe : "+str(self.CALelectrode)+"\n"
			   +str(date)+"\n"+"\nType de calibration: "+str(caltype)+"\nVoltages calib:\n"
			   +str(u_cal)+"\nCoefficients U=a*pH+b\n(a,b)="+str(coeffs)+"\n\n")
		oldCal.close()

	def computeCalCoefs(self,u_cal,pH_buffers):
		if pH_buffers == [4]:
			b=u_cal[0]-4*self.a	#dernière calibration
		if pH_buffers == [4,7]:
			pH = np.array([4,7])
			u = np.array([u_cal[0:2]]).T #seulement pH4 et 7
			#print("pH : ",pH," tensions de calib: ", u)
			a=(u_cal[1]-u_cal[0])/3;b=u_cal[0]-4*a
		if pH_buffers == [4,7,10]: # cas le plus courant
			pH = np.array([4,7,10])
			u = np.array([u_cal[0:3]]).T #pH 4, 7 et 10
			#print("pH : ",pH," tensions de calib: ", u)
			A = np.vstack([pH.T, np.ones(len(pH)).T]).T
			x = np.linalg.lstsq(A, u, rcond=None)[0]		#a: pente, b: ord à l'origine
			a=float(x[0].item());b=float(x[1].item())	#U=a*pH+b
		self.a=a
		self.b=b
		return a, b
	
	def activateStabilityLevel(self): 
		self.ph0=self.currentPH
		self.stab_timer.start()
		try:
			self.stab_timer.disconnect() # important pour ne pas executer la fonction plusieurs fois à chaque appel
		except:
			pass
			#print("ne peut pas deconnecter les signaux sur le timer")
		self.stab_timer.timeout.connect(self.refreshStabilityLevel)
		self.time_counter=0
	
	def refreshStabilityLevel(self):
		self.time_counter+=1
		ts=self.stab_time
		if (abs(self.currentPH-self.ph0)<self.stab_step):	#le pH bouge pas, le stab_level progresse
			if self.stab_level<ts: 					#en attente
				self.stable=False
				self.stab_level+=1 
			else:	#self.stab_level>=ts	#elif self.stab_level==ts: 				#stable
				self.stab_level=ts
				if self.stable==False:
					self.stable=True
					self.signals.stability_reached.emit()
				if self.stable==False or self.time_counter>=ts:
					self.ph0=self.currentPH #on reprend une valeur de référence pour le pH
					self.time_counter=0 #reset du compteur		
		else: 	#si ça bouge, on reset tout
			self.ph0=self.currentPH
			self.time_counter=0
			self.stab_level=0
			self.stable=False
		self.stab_purcent = round((self.stab_level/ts)*100,2)

	def close(self):
		self.U_pH.close()
		self.stab_timer.disconnect()
		self.stab_timer.stop()
		self.state='closed'
		print("pH meter closed")

	def onError(self, code, description):
		print("Code: " + ErrorEventCode.getName(code))
		print("Description: " + str(description))
		print("----------")

if __name__ == "__main__":
	
	phm=PHMeter()
	phm.connect()
	
	
	"""Log.enable(LogLevel.PHIDGET_LOG_INFO, "phidgetlog.log")
	U_pH = VoltageInput()
	U_pH.setOnErrorHandler(PHMeter.onError)
	
	U_pH.setDeviceSerialNumber(683442)	#pH mètre ADP1000_0
	U_pH.setHubPort(3)
	U_pH.openWaitForAttachment(2000)
	if U_pH.getIsOpen():
		print("connectéé")
		#print(U_pH.getDataRate())
		#print(U_pH.getMinDataRate(),U_pH.getMaxDataRate())
		#print(U_pH.getMinDataInterval(),U_pH.getMaxDataInterval())
		currentVoltage=U_pH.getVoltage()
		print(currentVoltage)
		
		#U_pH.setDataInterval(int(1000))	#ms
		print("aa")
		#U_pH.setVoltageChangeTrigger(0.00001) #seuil de déclenchement (Volt)
		print("aaa")
		
	else:
		print("non détecté")
	#except:
	#	pass"""
	
		#fonction de détection ne fonctionne pas encore
	"""def getPhmeterModel(self):
		#Ph mètre Phidget 1130_0 branché sur le voltageInput0 de la carte
		U_1130=VoltageInput()
		U_1130.setDeviceSerialNumber(432846)	
		U_1130.setChannel(0)	

		#pH mètre ADP_1000 branché sur la broche 3 du VINT
		U_ADP1000 = VoltageInput() 
		U_ADP1000.setDeviceSerialNumber(683442)
		U_ADP1000.setChannel(3)		

		try:
			U_ADP1000.openWaitForAttachment(1000)
			if U_pH.getIsOpen():
				self.model='Phidget ADP1000_0'
				V=ADP1000.getVoltage()	
				if abs(V-0.25)<=0.01:
					self.electrode_state='unplugged'
				else:
					self.electrode_state='unplugged'
		try:
			U_1130.openWaitForAttachment(1000)
			if U_1130.getIsOpen():
				self.model='Phidget pH adapter 1130_0'
				V=U_1130.getVoltage()	
				if abs(V)<=0.01:
					self.electrode_state='unplugged'
				else:
					self.electrode_state='plugged'"""