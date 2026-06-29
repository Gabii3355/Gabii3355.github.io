import os
from pymolecule import multipoles
kcal=627.5095

ligandfile = 'XXX.out'
files = os.listdir('OUT')
files.remove(ligandfile)
ligand = multipoles.PyMultipoles('./OUT/%s' % ligandfile,'GAMESS')
Etot = 0
for r in files:
    resid = multipoles.PyMultipoles('./OUT/%s' % r,'GAMESS')
    intene = multipoles.energy(ligand, resid, L=4)*kcal
    Etot += intene
    resname = r.split('_')[1].split('.')[0]
    print('%6s%10.3f' % (resname, intene))
#print(16*'-')
#print('%6s%10.3f' % ('total', Etot))
