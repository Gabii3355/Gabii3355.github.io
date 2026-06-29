#!/usr/bin/env python
"""
Usage:	./gms_CAMM.py fileinp.xyz total_charge
"""
import sys, os

charge = int(sys.argv[2])
mult = 1
mp2=0

gamess=""" $CONTRL SCFTYP=RHF RUNTYP=energy ICHARG=%d MULT=%d UNITS=ANGS maxit=200
         mplevl=%d $END
 $SYSTEM MWORDS=90 $END
 $BASIS  GBASIS=N31 NGAUSS=6 NDFUNC=1 $END
 $GUESS  GUESS=HCORE $END
 $ELMOM WHERE=COMASS iemom=3 iemint=0 iamm=9 cum=.t. ibond=0 $END
 $SCF    DIRSCF=.T. DIIS=.t. SOSCF=.f. ETHRSH=5 $END
"""%(charge,mult,mp2)


symmetry="C1       1\n"


inp_b=sys.argv[1][:-3]

os.system('obabel %s -O %s'%(inp_b+'xyz',inp_b+'gamin'))
gtitle="%s\n"%(inp_b+'xyz')
ginp=open(inp_b+'gamin')
gout=open(inp_b+'inp','w')
gout.write(gamess)
#gout.write(gtitle)
#gout.write(symmetry)
while 1:
	line=ginp.readline()
	if len(line)<2: break
while 1:
	line=ginp.readline()
	if not line: break
	gout.write(line)
ginp.close(); gout.close()
	
#to_be_rm='%s_temp??.xyz %s_temp??.gamin'%(inp_b,inp_b)
to_be_rm=inp_b+'gamin'
os.system('rm %s'%to_be_rm)


