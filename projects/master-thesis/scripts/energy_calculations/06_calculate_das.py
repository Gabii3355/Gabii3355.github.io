import os
from Das2a import EDas
from Das2a import molecule
kcal=627.5095

ligandfile = 'XXX.mol2'
files = os.listdir('MOL2')
files.remove(ligandfile)
ligand = molecule('./MOL2/%s' % ligandfile)
Etot = 0
for r in files:
    resid = molecule('./MOL2/%s' % r)
    dispene = EDas(ligand, resid) * kcal
    Etot += dispene
    resname = r.split('_')[1].split('.')[0]
    print('%6s%10.3f' % (resname, dispene))
#print('%6s%10.3f' % ('total', Etot))
