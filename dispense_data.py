"""
Module appelé pendant la séquence pour obtenir les bons volumes à dispenser ou les pH à viser.
"""

import numpy as np
import math

#data du 23/01/2024
v_23_01_2024 = np.array([0,100,200,300,400,500,550,600,650,700,750,800,850,900,950,1050,1150,1250,1450,1850])
pH_dommino_23_01_2024=np.array([4.01, 4.15,	4.27, 4.5, 4.82, 5.49, 5.85, 6.15, 6.5,	6.91, 7.33,	7.72, 8.18,	8.54, 8.75,	9.19, 9.4, 9.51, 9.74, 10.03])
pH_HI5221_23_01_2024=np.array([4.09, 4.21, 4.36, 4.56, 4.9,	5.59, 5.98,	6.34, 6.69,	7.09, 7.38,	7.75, 8.29,	8.69, 8.92,	9.32, 9.54,	9.69, 9.91,	10.19])
#fit sur pH-mètre dommino le 23/01/2024, fait sur excel
param_dommino_23_01_2024 = [3.9266, -133.37, 1792.2, -11910., 39276., -51141.] 

#données des mesures IPGP du 6/03/2024 avec lHA 2.5ppm et bullage N2 (sans oxygène)
v_N2_6_03_2024 = np.array([0, 173, 300, 388, 447, 490, 534, 627, 840, 1459])
pH_N2_6_03_2024 = np.array([4.041, 4.236, 4.467, 4.737, 5.061, 5.535, 6.758, 8.846, 9.527, 10.077])
#fit réalisé sur excel avec polynôme de deg. 5.
param_IPGP_N2_6_03_2024 = np.array([4.5281, -155.77, 2119.7, -14265., 47527., -62340.])

def dispense_function_uL(pH, atmosphere=True):
    """Retourn le volume correspondant au pH. 
    Suppose utilisation de soude NaOH concentration 10e-2 mol/L.
    On suppose être au pH4 initialement et un volume d'échantillon de 50mL"""
    if atmosphere==True:
        #données du 23/01/2024
        coefs = np.polyfit(pH_dommino_23_01_2024, v_23_01_2024, 5)
    else:   #atmosphere = False
        #données issues des mesures à l'IPGP en mars 2024 - avec bullage N2.
        coefs = np.polyfit(pH_N2_6_03_2024, v_N2_6_03_2024, 7)
    print(coefs)
    P = np.poly1d(coefs)
    #liste ou valeur simple pour le volume
    if type(pH)!=list and type(pH)!=np.ndarray:
        vol = P(pH)
    else:
        vol = [P(u) for u in pH]
    return vol

def get_volume_to_dispense_uL(current_pH, target_pH, atmosphere=True, C_NaOH=0.01, volume=50):
    """C (mol/L) et V(mL) sont les conditions classiques pour lesquelles les courbes de dispense sont obtenues
    Si on est dans des conditions différentes, on corrige"""
    #volume en conditions standard
    factor = (volume*0.01)/(C_NaOH*50)
    print("correction factor from reference dispense curve =",factor)
    vol_ref = max(0,dispense_function_uL(target_pH, atmosphere=atmosphere)-dispense_function_uL(current_pH, atmosphere=atmosphere))
    vol=factor*vol_ref
    return vol

### Fonctions pour la répartition des points de pH ###

def f_ratio_deprotone(x,m,lK):  #sigmoide modelise f1 f2 dans le traitement 
    return 10**(m*(x-lK))/(1+10**(m*(x-lK)))

def derivee_f(x,m,lK):  #dérivée de f_ratio_deprotonee
    return m*math.log(10)*10**(m*(x-lK))/((1+10**(m*(x-lK)))**2)

def evolution_absorbance(A1,m1,lK1,A2,m2,lK2,pH):  #fonction
    #return max(A1*derivee_f(pH,m1,lK1),A2*derivee_f(pH,m2,lK2))
    return max(A1[0]*derivee_f(pH,m1,lK1)+A2[0]*derivee_f(pH,m2,lK2),A1[1]*derivee_f(pH,m1,lK1)+A2[1]*derivee_f(pH,m2,lK2))

def delta_pH(A1,m1,lK1,A2,m2,lK2,pH,pH0,max_delta):
    return max_delta*evolution_absorbance(A1,m1,lK1,A2,m2,lK2,pH0)/evolution_absorbance(A1,m1,lK1,A2,m2,lK2,pH)


#données issues de l'optim sur les donnees du 26/01/2024
#A1=[0.1317,0.0419],m1=0.416,lK1=3.90,A2=[0.0727,0.1392],m2=0.197,lK2=9.94,pH0=6.486
absorbance_model_26_01_2024 = [[0.1317,0.0419],0.416,3.90,[0.0727,0.1392],0.197,9.94,6.486]

"""def dispense_function(pH,coefs,x0):
    [y0, ba, ca, bb, cb] = coefs
    if type(pH)!=list:
        if pH<=y0:
            x=x0-ba*(10**((y0-pH)/ca)-1)
        else:
            x=x0+bb*(10**((pH-y0)/cb)-1)
    else:
        x=[]
        for y in pH:
            if y<=y0:
                x.append(x0-ba*(10**((y0-y)/ca)-1))
            else:
                x.append(x0+bb*(10**((y-y0)/cb)-1))
    return x"""

#à développer pour plus tard
"""elif self.dispense_mode=='variable step with feedback': #à développer
    ph0=self.pH_mes[N-2]
    target=ph0+getPhStep(ph0)
    vol1=GAIN_ON_PH_STEP*volumeToAdd_uL(ph0, target, model='5th order polynomial fit on dommino 23/01/2024')
    self.syringe.dispense(vol1) #lancement du stepper 
    #boucle de correction
    ph1=self.phmeter.currentPH
    reached_ratio=(ph1-ph0)/(target-ph0)    #how much the target pH is reached
    if reached_ratio>0.8:
        #la dispense est validée
        pass
    else:
        new_gain=old_gain*old_gain/reached_ratio"""

class ReferenceData:
    #Cette classe modélise un titrage qui peut servir de référence à plusieurs niveaux

    def __init__(self,A1,m1,lK1,A2,m2,lK2):  #initialisation par les fonctions de référence
        self.A1=A1#maximum de la fonction A1
        self.m1=m1
        self.lK1=lK1
        self.A2=A2#maximum de la fonction A2
        self.m2=m2
        self.lK2=lK2

    ### Calcul d'espacement des courbes en pH
    #donnees de référence : 26/01/2024

    def evolution_absorbance(self,pH):   #représente le maximum d'évolution avec le pH\
        # entre les deux absorbance A(lambda1) et A(lambda2) qui correspondent aux longueurs d'onde\
        # d'intérêt pour les COOH et PhOH
        #max(A1(lambda1)*f1',A2(lambda2)*f2')
        return max(self.A1[0]*derivee_f(pH,self.m1,self.lK1)+self.A2[0]*derivee_f(pH,self.m2,self.lK2),self.A1[1]*derivee_f(pH,self.m1,self.lK1)+self.A2[1]*derivee_f(pH,self.m2,self.lK2))

    def min_abs_variation(self):
        """La fonction doit se lancer depuis un environnement virtuel contenant scipy"""
        import scipy.optimize 
        self.pH0 = scipy.optimize.fmin(lambda x: self.evolution_absorbance(x), 6)   #minimum de variation d'absorbance
        return self.pH0

    def delta_pH(self,pH,max_delta):
        """renvoie le pas de pH en fonction du pH courant pour satisfaire le critère d'écart maximum\
        entre deux valeurs de pH.""" 
        return max_delta*self.evolution_absorbance(self.pH0)/self.evolution_absorbance(pH)
    
    def plot_functions(self,max_delta=0.5):
        import matplotlib.pyplot as plt
        n=100
        x=np.linspace(3.5,10.5,100)
        F1=np.zeros_like(x)
        F2=np.zeros_like(x)
        G1=np.zeros_like(x)
        G2=np.zeros_like(x)
        y=np.zeros_like(x)
        z=np.zeros_like(x)
        for k in range(n):
            F1[k], F2[k] = self.A1[0]*f_ratio_deprotone(x[k],self.m1,self.lK1)+self.A2[0]*f_ratio_deprotone(x[k],self.m2,self.lK2), self.A1[1]*f_ratio_deprotone(x[k],self.m1,self.lK1)+self.A2[1]*f_ratio_deprotone(x[k],self.m2,self.lK2)
            G1[k], G2[k] = self.A1[0]*derivee_f(x[k],self.m1,self.lK1)+self.A2[0]*derivee_f(x[k],self.m2,self.lK2), self.A1[1]*derivee_f(x[k],self.m1,self.lK1)+self.A2[1]*derivee_f(x[k],self.m2,self.lK2)
            y[k]=self.evolution_absorbance(x[k])
            z[k]=self.delta_pH(x[k],max_delta)
        fig, ((ax1, ax2),(ax3,ax4)) = plt.subplots(2,2)
        fig.suptitle('courbe delta pH sur données du 26/01/2024')
        ax1.plot(x, F1, x, F2)
        ax1.set_title("modélisation max(A1)*f1, max(A2)*f2")
        ax2.plot(x, G1, x, G2)
        ax2.set_title("variation d'absorbance")
        ax3.plot(x, y)
        ax3.set_title("max d'augmentation sur l'absorbance")
        ax3.set(xlabel="pH")
        ax4.plot(x, z)
        ax4.set_title("pas de pH à viser avec maximum fixé à %f" %max_delta)
        ax4.set(xlabel="pH")
        plt.show()

if __name__=="__main__":
    #obtention de la courbe de référence
    """dataSet = ReferenceData(A1=[0.1317,0.0419],m1=0.416,lK1=3.90,A2=[0.0727,0.1392],m2=0.197,lK2=9.94)    #26/01/2024
    #d'après le fichier matlab
    pH0 = dataSet.min_abs_variation()
    print(pH0)
    dataSet.plot_functions(0.8)    #max_delta"""

    ### Tracé des courbes de dispense volume(pH)
    """import matplotlib.pyplot as plt
    x=np.linspace(3.5,10.5,100)
    y_O2=dispense_function_uL(x)
    y_N2=dispense_function_uL(x,atmosphere=False)
    plt.xlabel('pH')
    plt.ylabel('volume (uL)')
    fig, axes = plt.subplots(1,2, sharex=True, sharey=True)
    fig.suptitle('Dispense curves\nInitial pH=4, volume : 50mL\nAddition of NaOH with concentration 0.01mol/L')
    axes[0].scatter(pH_dommino_23_01_2024, v_23_01_2024, label='23/01 normal conditions', color='black')
    axes[0].plot(x,y_O2,label='5th degree polynome',color='red')
    axes[0].legend()
    axes[0].set_title('standard conditions (with O2)')
    axes[1].scatter(pH_N2_6_03_2024, v_N2_6_03_2024, label='6/03 IPGP with N2 bubling (no atmosphere)', color='black')
    axes[1].plot(x,y_N2,label='7th degree polynome',color='blue')
    axes[1].legend()
    axes[1].set_title('N2 bubling (without O2)')
    plt.show()"""

    #Test de la fonction get_volume_to_dispense_uL
    while(True):
        ph0, ph1 = input("ph courant, ph cible: ").split()
        x0=float(ph0);x1=float(ph1)
        print("current: ", ph0)
        print("target: ", ph1)
        print("volume à ajouter : ", get_volume_to_dispense_uL(x0,x1,C_NaOH=0.005,volume=55))