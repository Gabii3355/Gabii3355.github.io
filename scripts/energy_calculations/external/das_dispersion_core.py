#!/usr/bin/python
'''
Das version (2017)
Written by W. Giedroyc-Piasecka and W. "Gadget" Beker
'''

from math import sqrt, exp, factorial
from numpy import dot, array
from os.path import dirname,realpath

ang2bohr=1.889725989
ht2kc=627.5095469
pth=dirname(realpath(__file__)) # w ten sposob zawsze wie gdzie jest i jak znalezc plik z parametrami

#========== read parameters ========================

plik=open(pth+'/params.txt',"r")
coeff={}
line=plik.readline()
while(line):
	if '#' not in line:
		line=line.split()
		at=line[0]
		c6=float(line[1])*10884.3209320438/ht2kc
		c8=float(line[2])*3886861.00398035/ht2kc
		b=float(line[3])
		coeff[at]={'C6':c6,'C8':c8,'B':b}
	line=plik.readline()
plik.close() 

#=========== useful functions ========================
def fact(n):return float(factorial(n))

def calcRab(a,b):
    d=a-b
    return (sqrt(dot(d,d)))

def calcf6(R):
    suma = 0
    for n in range(7):
        suma += ((R**n)/fact(n))
    return 1 - exp(-R)*suma

def calcf8(R):
    suma = 0
    for n in range(9):
        suma += ((R**n)/fact(n))
    return 1 - exp(-R)*suma

#============ energy =========================================

def EDas(mol_a,mol_b):
	das=0
	for a in range(len(mol_a.coor)):
		for b in range(len(mol_b.coor)):
			[C6a,C8a,Ba]=[coeff[mol_a.elements[a]][x] for x in ['C6','C8','B']]
			[C6b,C8b,Bb]=[coeff[mol_b.elements[b]][x] for x in ['C6','C8','B']]
			r=calcRab(mol_a.coor[a],mol_b.coor[b])
			rr=sqrt(Ba*Bb)*r
			f6=calcf6(rr)
			f8=calcf8(rr)
			Dab = -(sqrt(C6a*C6b))/(r**6)*f6 - (sqrt(C8a*C8b)/(r**8))*f8 
			das+=Dab
	return das			
		
#==================== molecule class ===============================
class molecule():
	def __init__(self,name='',iftop=True):
		if name: 
			extension = name.split('.')[-1]
			if extension == 'xyz':
				self.load_xyz(name)
			elif extension == 'mol2':
				self.load_mol2(name)
			else:
				raise TypeError('Unknown extension: %s'%extension)
		else:
			self.elements=['he']
			self.coor=[array([0.0,0.0,0.0])]
		
		
	def load_xyz(self, filename):
		plik=open(name,'r')
		data=plik.readlines()[2:] # pominac liczbe at. i komentarz
		plik.close()
		self.elements=[]
		self.coor=[]
		
		for x in data:
			x=x.split()
			if x!=[]:
				self.elements.append(x[0].lower())
				coor=map(float, x[1:])
				self.coor.append(array(coor)*ang2bohr)
		if iftop: self.top()        

        #defines 'topology' of hydrogens
	def _exclude_digits(self, string):
		return ''.join([x for x in string if not x.isdigit()])
	
	def load_mol2(self, filename):
		self.elements=[]
		self.coor=[]
		line=''
		with open(filename, 'r') as f:
			#skip first two lines
			[f.readline() for _ in range(2)]
			#read number of atoms and bonds
			N_atoms, N_bonds = [int(x) for x in f.readline().split()[:2]]
			self.atom_bonds=[[] for _ in range(N_atoms)] 
			#skip everything before ATOM section
			while('ATOM' not in line):
			    line=f.readline()
			#read atom data
			for _ in range(N_atoms):
				line=f.readline()
				_, symbol, x,y,z = line.split()[:5]
				symbol = self._exclude_digits(symbol)
				self.elements.append(symbol.lower())
				self.coor.append(array([x,y,z]).astype(float)*ang2bohr)
				
			#proceed and check whether BOND section starts
			line = f.readline()
			assert 'BOND' in line
			#read bond data
			for _ in range(N_bonds):
				line=f.readline()
				idx1, idx2 = [int(x)-1 for x in line.split()[1:3]]
				self.atom_bonds[idx1].append(idx2)
				self.atom_bonds[idx2].append(idx1)
				
		#assign hybridizations to carbons and neirest neighbors to Hs
		for idx, element in enumerate(self.elements):
			nei=self.atom_bonds[idx]
			num_nei=len(nei)
			if element=='c':
				assert num_nei<=4
				element = 'csp%i'%(num_nei-1)
			elif element=='h':
				assert num_nei==1
				nei_symbol = self.elements[nei[0]]
				if 'sp' in nei_symbol:
					nei_symbol = nei_symbol.split('sp')[0]
				element = 'h-%s'%nei_symbol
			else:
				continue
			self.elements[idx]=element
			                        
			    
	def top(self,ifhyb=True):
		n=len(self.elements)
		self.elements=map(lambda x: x.lower(),self.elements)
		carbons=[]
		carbons_neighbors_nums=[]
		for i in range(n):
				ni=self.elements[i]
				if ni=='c' and i not in carbons: 
					carbons.append(i)
					carbons_neighbors_nums.append(0)
				for j in range(i+1,n):
					nj=self.elements[j]
					if nj=='c' and j not in carbons:
						carbons.append(j)
						carbons_neighbors_nums.append(0)
					
					d=self.coor[i]-self.coor[j]
					d=sqrt(dot(d,d))
					if d<3:
						if 'h' in [ni,nj]:
							if ni=='h':
								self.elements[i]=self.elements[i]+'-'+self.elements[j]
							else:
								self.elements[j]=self.elements[j]+'-'+self.elements[i]
						if ni=='c':
							carbons_neighbors_nums[carbons.index(i)]+=1
						if nj=='c':
							carbons_neighbors_nums[carbons.index(j)]+=1
				if ni=='c' and ifhyb:
					self.elements[i]+='sp%i'%(carbons_neighbors_nums[carbons.index(i)]-1)

#====================== to ues in pymolecule ===================================================
def top(pmol,ifhyb=True):
		n=len(pmol.elements)
		pmol.elements=map(lambda x: x.lower(),pmol.elements)
		carbons=[]
		carbons_neighbors_nums=[]
		for i in range(n):
				ni=pmol.elements[i]
				if ni=='c' and i not in carbons: 
					carbons.append(i)
					carbons_neighbors_nums.append(0)
				for j in range(i+1,n):
					nj=pmol.elements[j]
					if nj=='c' and j not in carbons:
						carbons.append(j)
						carbons_neighbors_nums.append(0)
					
					d=pmol.coor[i]-pmol.coor[j]
					d=sqrt(dot(d,d))
					if d<3:
						if 'h' in [ni,nj]:
							if ni=='h':
								pmol.elements[i]=pmol.elements[i]+'-'+pmol.elements[j]
							else:
								pmol.elements[j]=pmol.elements[j]+'-'+pmol.elements[i]
						if ni=='c':
							carbons_neighbors_nums[carbons.index(i)]+=1
						if nj=='c':
							carbons_neighbors_nums[carbons.index(j)]+=1
				if ni=='c' and ifhyb:
					pmol.elements[i]+='sp%i'%(carbons_neighbors_nums[carbons.index(i)]-1)
#=======================  TEST   =========================================================	


if __name__ == '__main__':
	from sys import argv
	mol=molecule(argv[1])
	print( mol.elements)
	#plik=open(pth+'/tests/ref_data.txt','r')
	#data=plik.readlines()[1:]
	#plik.close()
	#print '\n\n'+20*'='+' TEST '+20*'='+'\n\n'
	#print '%5s  %25s  %10s  %10s'%('No','Name','delta[mH]','delta[kcal/mol]')
	#print 60*'-'

	#succ=0
	#ntest=0

	#for line in data:
		#[no,name,mH,kc]=line.split()
		#mH,kc=float(mH),float(kc)
		#mola=molecule('tests/%s_a.xyz'%no)
		#molb=molecule('tests/%s_b.xyz'%no)
		#e=EDas(mola,molb)

		#ntest+=1
		#dmH=mH-e*1000
		#dkc=kc-e*ht2kc

		#test1= round(dmH,4)==0
		#test2= round(dkc,6)==0

		#if test1 and test2: 
			#message='OK'
			#succ+=1
		#elif not (test1 and test2): message='FAILED'
		#elif not test1: message='Hartree FAILED'
		#else: message='kcal/mol FAILED'

		#print '%5s  %25s  %10f  %10f  %s'%(no,name,dmH,dkc,message)

	#print '\nDone %i test, %i failures'%(ntest,ntest-succ)


