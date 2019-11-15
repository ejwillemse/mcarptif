'''
Created on 20 Jan 2015

@author: ejwillemse
'''
import os
pSets = ['Lpr', 'mval', 'Cen-Part', 'Cen', 'Cen-Full', 'eglese', 'egl-large', 'bccm', 'gdb', 'bmcv']
outFile = open('ProblemSize.csv', 'w')
outFile.write('Set,Problem,ReqEdges,ReqArcs,tau\n')

for s in pSets:
    pFiles = os.listdir('Raw_input/' + s)
    for p in pFiles:
        if p[0] == '.': continue
        #print(p)
        f = open('Raw_input/' + s + '/' + p, 'r')
        lines = f.readlines()
        f.close()
        name = p[:p.find('.')]
        for l in lines:
            if l.find('REQ_EDGES : ') != -1 & l.find('NOREQ_EDGES : ') == -1:
                if l[-2] == '\r' or  l[-2] == '\n':
                    endI = -2
                else:
                    endI = -1
                reqEdges = int(l[len('REQ_EDGES : '):endI])
            if l.find('REQ_ARCS : ') != -1 & l.find('NOREQ_ARCS : ') == -1:
                if l[-2] == '\r' or  l[-2] == '\n':
                    endI = -2
                else:
                    endI = -1
                reqArcs = int(l[len('REQ_ARCS : '):endI])
                break
        tau = 2*reqEdges + reqArcs
        l = '%s,%s,%i,%i,%i\n'%(s,name,reqEdges,reqArcs,tau)
        print(l)
        outFile.write(l)
outFile.close()

