"Acquisition du pH"

"""https://pythonpyqt.com/pyqt-events/ créer des signaux"""

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject

from Phidget22.Phidget import *
from Phidget22.Devices.Log import *
from Phidget22.Devices.VoltageInput import *
from Phidget22.Devices.PHSensor import *

import math
import numpy as np
from configparser import ConfigParser
import os
from pathlib import Path
import re

#Récupère le fichier des données de calibration par défaut
path = Path(__file__)
ROOT_DIR = path.parent.parent.absolute()
app_default_settings = os.path.join(ROOT_DIR, "config/app_default_settings.ini")
#latest_cal = "config/latest_cal.ini"
cal_log = os.path.join(ROOT_DIR, "config/CALlog.txt")
device_ids = os.path.join(ROOT_DIR, "config/device_id.ini")

def volt2pH(a,b,U): #m: pente, c: ordonnée à l'origine
	#U=a*pH+b
	if a!=0:
		pH=(U-b)/a
	else:
		pH=1000
	return round(pH,3)

class CustomSignals(QObject):
	stability_reached=pyqtSignal()

class PHMeter:

	parser = ConfigParser()
	parser.read(device_ids)
	board_number = int(parser.get('main board', 'id'))
	VINT_number = int(parser.get('VINT', 'id'))
	ch_phmeter = int(parser.get('ph meter', 'electrode'))

	def __init__(self):
		self.U_pH = VoltageInput() #pH-mètre
		self.state='closed'

		self.stab_timer = QtCore.QTimer()
		self.stab_timer.setInterval(1000)
		self.stable=False
		self.stab_level=0 #pourcentage de stabilité
		parser = ConfigParser()
		parser.read(app_default_settings)
		self.stab_time = int(parser.get('phmeter', 'delta'))
		self.stab_step = float(parser.get('phmeter', 'epsilon'))
		self.stab_purcent = 0
		
		#Création d'un signal PyQt pour informer une fois lorsque l'electrode devient stable
		self.signals=CustomSignals()
	
		print("default settings file:", app_default_settings)
		parser = ConfigParser()
		parser.read(app_default_settings)
		self.relative_calib_path=parser.get('calibration', 'file')
		self.model=parser.get('phmeter', 'default')
		self.electrode=parser.get('electrode', 'default')

		self.update_infos()

	def connect(self):
		
		#Ph mètre Phidget 1130_0 plugged in Voltage Input of main board
		self.U_pH.setDeviceSerialNumber(self.board_number)
		self.U_pH.setChannel(self.ch_phmeter)
		try:
			self.U_pH.openWaitForAttachment(3000)	#beug lors de l'ouverture si pas sous tension
			self.U_pH.setDataRate(3)
			self.U_pH.setVoltageChangeTrigger(0.00001) #seuil de déclenchement (Volt)
			self.getCalData()
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
	
	def getCalData(self):
		parser = ConfigParser()
		parser.read(self.relative_calib_path)
		self.CALmodel=parser.get('data', 'phmeter')
		self.CALelectrode=parser.get('data', 'electrode')
		self.CALdate=parser.get('data', 'date')
		self.CALtype=parser.get('data', 'calib_type')
		self.U1=float(parser.get('data', 'U1'))
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
	
	def saveCalData(self,date,caltype,u_cal,coeffs):
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
		if pH_buffers == [4,7,10]:
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
			self.stab_timer.disconnect() #important pour ne pas executer la fonction plusieurs fois à chaque appel
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