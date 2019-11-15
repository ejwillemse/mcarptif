'''
Created on 15 May 2016

@author: ejwillemse
'''
from __future__ import division
import os
import numpy as np
from math import ceil

def returnInt(line, strMatch):
    if line.find(strMatch) == 0 and line.find(strMatch) != -1:
        val = int(line[line.find(strMatch) + len(strMatch):])
    else:
        val = None
    return(val)

def returnStr(line, strMatch):
    if line.find(strMatch) == 0 and line.find(strMatch) != -1:
        val = line[line.find(strMatch) + len(strMatch):line.find('.')]
    else:
        val = None
    return(val)

def returnList(line, strMatch):
    if line.find(strMatch) != -1:
        val = line[line.find(strMatch) + len(strMatch):]
        if val.find(',') == -1:
            val = [abs(int(val))]
        else:
            val = [abs(int(i)) for i in val.split(',')]
    else:
        val = None
    return(val)

def returnReqArcEdgesList(line):
    nodes = [abs(int(n)) for n in line[1:line.find(')')].split(',')]
    serv_cost_start = line.find('serv_cost')
    trav_cost_start = line.find('trav_cost')
    if trav_cost_start == -1:
        repTrav = 'trave_cost'
        trav_cost_start = line.find('trave_cost')
    else:
        repTrav = 'trav_cost'
    
    dem_start = line.find('demand')
    
    serv_cost_val = int(line[serv_cost_start + len('serv_cost'):trav_cost_start].replace(' ',''))
    trav_cost_val = int(line[trav_cost_start + len(repTrav):dem_start].replace(' ',''))
    dem_start_val = int(line[dem_start + len('demand'):].replace(' ',''))
    outPutList = nodes + [serv_cost_val, trav_cost_val, dem_start_val]
    return(outPutList)

def returnNonReqArcEdgesList(line):
    nodes = [abs(int(n)) for n in line[1:line.find(')')].split(',')]
    trav_cost_start = line.find('cost')
    
    trav_cost_val = int(line[trav_cost_start + len('cost'):].replace(' ',''))
    outPutList = nodes + [trav_cost_val]
    return(outPutList)

def instanceInfo(fPath, newPath):
    
    fOpen = open(fPath, 'r')
    l = fOpen.readlines()
    fOpen.close()
    l2 = []
    maxL = -1
    heading = True
    
    reqEdges = False
    nonReqEdges = False
    reqArcs = False
    nonReqArcs = False
    
    reqEdgesL = []
    nonReqEdgesL = []
    reqArcsL = []
    nonReqArcsL = []
    
    depotsL = []
    ifsL = []
    
    nodesS = set()
    
    for line in l:
        
        if line.find('LIST_') != -1:
            heading = False
        
        if heading:
            val = returnStr(line, 'NAME : ')
            if val != None: 
                nName = val
                newF = open(newPath + '/' + val + '.txt', 'w')
            val = returnInt(line, 'NODES : ')
            if val != None: nNodes = val
            val = returnInt(line, 'REQ_EDGES : ')
            if val != None: nReqEdges = val
            val = returnInt(line, 'NOREQ_EDGES : ')
            if val != None: nNonReqEdges = val
            val = returnInt(line, 'REQ_ARCS : ')
            if val != None: nReqArcs = val
            val = returnInt(line, 'NOREQ_ARCS : ')
            if val != None: nNonReqArcs = val
            val = returnInt(line, 'CAPACITY : ')
            if val != None: cap = val
            val = returnInt(line, 'DUMPING_COST : ')
            if val != None: dump = val
            val = returnInt(line, 'MAX_TRIP : ')
            if val != None: maxL = val
        
        if line.find('LIST_REQ_EDGES') != -1:
            reqEdges = True
            nonReqEdges = False
            reqArcs = False
            nonReqArcs = False

        elif line.find('LIST_NOREQ_EDGES') != -1:
            reqEdges = False
            nonReqEdges = True
            reqArcs = False
            nonReqArcs = False  

        elif line.find('LIST_REQ_ARCS') != -1:
            reqEdges = False
            nonReqEdges = False
            reqArcs = True
            nonReqArcs = False

        elif line.find('LIST_NOREQ_ARCS') != -1:
            reqEdges = False
            nonReqEdges = False
            reqArcs = False
            nonReqArcs = True         

        elif line.find('DEPOT : ') != -1:
            reqEdges = False
            nonReqEdges = False
            reqArcs = False
            nonReqArcs = False
            depotsL = returnList(line, 'DEPOT : ')

        elif line.find('DUMPING_SITES : ') != -1:
            reqEdges = False
            nonReqEdges = False
            reqArcs = False
            nonReqArcs = False
            ifsL = returnList(line, 'DUMPING_SITES : ')

        else:
            
            if reqEdges:
                outLine = returnReqArcEdgesList(line)
                reqEdgesL.append(outLine)
                nodesS = nodesS.union(outLine[:2])
            if reqArcs:
                outLine = returnReqArcEdgesList(line)
                reqArcsL.append(outLine)
                nodesS = nodesS.union(outLine[:2])
            if nonReqEdges:
                outLine = returnNonReqArcEdgesList(line)
                nonReqEdgesL.append(outLine)
                nodesS = nodesS.union(outLine[:2])
            if nonReqArcs:
                outLine = returnNonReqArcEdgesList(line)
                nonReqArcsL.append(outLine)
                nodesS = nodesS.union(outLine[:2])
                
    if not ifsL: ifsL = depotsL
    
    demand = sum([d[4] for d in reqEdgesL]) + sum([d[4] for d in reqArcsL])
    service = sum([d[2] for d in reqEdgesL]) + sum([d[2] for d in reqArcsL])
    
    nSubtripLB = int(ceil(demand/cap))
    
    #print('Nodes', len(nodesS), nNodes)
    #print('nReqEdges', len(reqEdgesL), nReqEdges)
    #print('nNoReqEdges', len(nonReqEdgesL), nNonReqEdges)
    #print('nReqArcs', len(reqArcsL), nReqArcs)
    #print('nNoReqArcs', len(nonReqArcsL), nNonReqArcs)
    #print('Demand service', demand, service)
    #print(nNonReqEdges, nReqArcs, nNonReqArcs, cap, dump, maxL)
    #print(depotsL, ifsL)
    nReqArcsEdges = len(reqEdgesL) + len(reqArcsL)
    nNonReqArcsEdges = len(nonReqEdgesL) + len(nonReqArcsL)
    instanceSize = 2*len(reqEdgesL) + len(reqArcsL)
    
    nAcrsSubtrip = '%.2f'%(nReqArcsEdges/nSubtripLB)
    
    if maxL == -1:
        nVehiclesLB = 0
        nAcrsRoute = 0
        maxL = 0
    else:
        nVehiclesLB = int(ceil((service+nSubtripLB*dump)/maxL))
        nAcrsRoute = '%.2f'%(nReqArcsEdges/nVehiclesLB)
    
    newF.write('NAME : %s\n'%nName)
    newF.write('NODES : %i\n'%nNodes)
    newF.write('REQ_EDGES : %i\n'%nReqEdges)
    newF.write('NOREQ_EDGES : %i\n'%nNonReqEdges)
    newF.write('REQ_ARCS : %i\n'%nReqArcs)
    newF.write('NOREQ_ARCS : %i\n'%nNonReqArcs)
    newF.write('CAPACITY : %i\n'%cap)
    newF.write('DUMPING_COST : %i\n'%dump)
    newF.write('MAX_DURATION : %i\n'%maxL)
    depoLs1 = [str(iDepot) for iDepot in depotsL]
    depoLs = ','.join(depoLs1)
    depoIFs1 = [str(iDepot) for iDepot in ifsL]
    depoIFs = ','.join(depoIFs1)
    newF.write('DEPOT : ' + depoLs + '\n')
    newF.write('DUMPING_SITES : ' + depoIFs + '\n')
    newF.write('LIST_REQ_EDGES :\n')
    for s in reqEdgesL:
        newF.write('start_node %i,end_node %i,serv_cost %i,trav_cost %i,demand %i\n'%tuple(s))
    newF.write('LIST_NOREQ_EDGES :\n')
    for s in nonReqEdgesL:
        newF.write('start_node %i,end_node %i,serv_cost 0,trav_cost %i,demand 0\n'%tuple(s))
    newF.write('LIST_REQ_ARCS :\n')
    for s in reqArcsL:
        newF.write('start_node %i,end_node %i,serv_cost %i,trav_cost %i,demand %i\n'%tuple(s))
    newF.write('LIST_NOREQ_ARCS :\n')
    for s in nonReqArcsL:
        newF.write('start_node %i,end_node %i,serv_cost 0,trav_cost %i,demand 0\n'%tuple(s))
    newF.close()
    return([len(nodesS), len(reqEdgesL), len(nonReqEdgesL), len(reqArcsL), len(nonReqArcsL), nReqArcsEdges, nNonReqArcsEdges, instanceSize, len(depotsL), len(ifsL), cap, dump, maxL, demand, service, nSubtripLB, nAcrsSubtrip, nVehiclesLB, nAcrsRoute, nName])

benchMarkSets = {'Act-IF'       : ['Act-IF', 'Act-IF-', '', 'CARPTIF', 2016],
                 'bccm'         : ['bccm', 'val', '', 'CARPTIF', 1992],
                 'bccm_IF'      : ['bccm-IF', 'val', '_IF', 'CARPTIF', 1992],
                 'bccm_IF_3L'   : ['bccm-IF-3L', 'val', '_IF', 'CARPTIF', 1992],
                 'Cen-IF'       : ['Cen-IF', 'Cen-IF-', '', 'MCARPTIF', 2016],
                 'Cen-Full-IF'  : ['Cen-Full-IF', 'Cen-Full-IF-', '', 'MCARPTIF', 2016],
                 'Cen-Part-IF'  : ['Cen-Part-IF', 'Cen-Part-IF-', '', 'MCARPTIF', 2016],
                 'bmcv'         : ['bmcv', '', '_IF', 'CARP', 2003],
                 'eglese'       : ['egl', 'egl-', '', 'CARP', 1996],
                 'egl-large'    : ['egl-large', 'egl-', '_IF', 'CARP', 2008],
                 'kshs'         : ['kshs', 'kshs', '', 'CARP', 1995],
                 'gdb'          : ['gdb', 'gdb', '', 'CARP', 1983],
                 'gdb_IF'       : ['gdb-IF', 'gdb-', '_IF', 'CARPTIF', 1983],
                 'gdb_IF_3L'    : ['gdb-IF-3L', 'gdb-', '_IF', 'CARPTIF', 1983],
                 'Lpr'          : ['Lpr', 'Lpr-', '', 'MCARP', 2006],
                 'Lpr_IF'       : ['Lpr-IF', 'Lpr_IF-', '', 'MCARPTIF', 2006],
                 'mval'         : ['mval', 'mval', '', 'MCARP', 1992],
                 'mval_IF_3L'   : ['mval-IF-3L', 'mval-', '_IF', 'MCARPTIF', 1992]}

headings = 'ProblemType,BenchmarkSet,Year,InstanceName,nNodes,nReqEdges,nNonReqEdges,nReqArcs,nNonReqArcs,nReqArcsEdges,nNonReqArcsEdges,instanceSize,nDepots,nIFs,Capacity,OffloadTime,maxRouteDuration,Demand,Service,nSubtripLB,nArcsSubtrip,nVehiclesLB,nArcsRoute\n'

fout = open('benchmarkSetFeaturesRaw.csv', 'w')
fout.write(headings)

for setName in benchMarkSets:
    #print(setName)
    newSetName = benchMarkSets[setName][0]
    inPath = 'Raw_input/' + setName + '/'
    outPath = 'Raw_input_conv/' + newSetName
    if not os.path.isdir(outPath): os.mkdir(outPath)
    instances = os.listdir(inPath)
    fromString = benchMarkSets[setName][1]
    toString = benchMarkSets[setName][2]
    maxSetString = 0
    instanceName = []
    instanceNameStringL = []
    lineInfoAll = []
    for f in instances:
        
        insOut = instanceInfo(inPath + f, outPath)
        lineInfo = [benchMarkSets[setName][3],newSetName,benchMarkSets[setName][4],''] + insOut[:-1]
        
        lineInfoS = [str(s) for s in lineInfo]
        lineInfoAll.append(lineInfoS)
        s = ','.join(lineInfoS)# + '\n'
        
        f = f[:f.find('.')]
        name1 = f
        if fromString:
            name1 = name1[name1.find(fromString) + len(fromString):]
        if toString:
            name1 = name1[:name1.find(toString)]
        
        i = []
        for k, s in enumerate(name1):
            try: 
                int(s)
                i += [k]
            except:
                True
        
        if len(i) > maxSetString:
            maxSetString = len(i)
        
        instanceName.append([name1, insOut[-1]])
        instanceNameStringL.append(i)
    
    for k, f2L in enumerate(instanceName):
        f2 = f2L[0]
        if len(instanceNameStringL[k]) < maxSetString:
            f2 = f2[:instanceNameStringL[k][0]] + '0' + f2[instanceNameStringL[k][0]:] 
        lineInfoAll[k][3] = newSetName + '-' + f2
        s = ','.join(lineInfoAll[k]) + '\n'
        print(newSetName + '-' + f2)
        fout.write(s)        
        fNew = open(outPath + '/' + f2L[-1] + '.txt')
        linesf2 = fNew.readlines()
        fNew.close()
        os.remove(outPath + '/' + f2L[-1] + '.txt')
        linesf2[0] = 'NAME : ' + newSetName + '-' + f2 + '\n'
        f3 = open(outPath + '/' + newSetName + '-' + f2 + '.txt', 'w')
        for s in linesf2: f3.write(s)
        f3.close()
        
fout.close()
        
        
    
        