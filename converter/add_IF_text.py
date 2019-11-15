'''
Created on 15 Mar 2016

@author: eliaswillemse
'''
sizes = open('ProblemSize.csv','r')

outFile = open('Problem_sizes_MCARPTIF_small.csv','w')

lines = sizes.readlines()

headings = lines[0]
outFile.write('Set,Instance,tau,Problem\n')

for l in lines[1:]:
    print(l)
    linfo = l.split(',')
    if linfo[0] == 'gdb':
        linfo = ['gdb-IF',linfo[1] + '-IF',linfo[4][:-1], 'MCARPTIF\n']
        newL = ','.join(linfo)
        outFile.write(newL)
    if linfo[0] == 'bccm':
        linfo = ['bccm-IF',linfo[1] + '-IF',linfo[4][:-1], 'MCARPTIF\n']
        newL = ','.join(linfo)
        outFile.write(newL)
        
for l in lines[1:]:
    l = l.replace('_','-')
    linfo = l.split(',')
    if linfo[0] == 'gdb':
        linfo = ['gdb-IF-3L',linfo[1] + '-IF',linfo[4][:-1], 'MCARPTIF\n']
        newL = ','.join(linfo)
        outFile.write(newL)
    if linfo[0] == 'bccm':
        linfo = ['bccm-IF-3L',linfo[1] + '-IF',linfo[4][:-1], 'MCARPTIF\n']
        newL = ','.join(linfo)
        outFile.write(newL)
        
outFile.close()
sizes.close()
