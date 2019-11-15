'''
Created on 18 Sep 2017

@author: eliaswillemse
'''
import os

def writeMCGRP_format(inputfile, outputFile, outname):
    
    lprHeadingsMap = {
                      'NAME : ' : 'Name:', 
                      'NODES : ' : '#Nodes:',
                      'REQ_EDGES :' : '#Required E:',
                      'NOREQ_EDGES :' : None, 
                      'REQ_ARCS :' : '#Required A:',
                      'NOREQ_ARCS :' : None, 
                      'VEHICLES :' : '#Vehicles:',  
                      'CAPACITY :' : 'Capacity:', 
                      'DUMPING_COST :' : None, 
                      'MAX_TRIP :' : None,
                      'DEPOT :' : 'Depot Node:'
                      }
    
    mcgrpMap = {
                    '#Required N:' : 0,
                    'Optimal value:' : -1
                }
    
    mcgrpStr = {
                 'reqEdge' : 'E%i\t%i\t%i\t%i\t%i\t%i\n',
                 'nonreqEdge' : 'NrE%i\t%i\t%i\t%i\n',
                 'reqArc' : 'A%i\t%i\t%i\t%i\t%i\t%i\n',
                 'nonreqArc' : 'NrA%i\t%i\t%i\t%i\n'
                }
    
    lprInfoMap = {
                  'LIST_REQ_EDGES : ' : '\nReE.    From N.    To N.    T. COST    DEMAND    S. COST\n',
                  'LIST_REQ_ARCS : ' : '\nReA.    FROM N.    TO N.    T. COST    DEMAND    S. COST\n',
                  'LIST_NOREQ_EDGES :' : '\nEDGE    FROM N.    TO N.    T. COST\n',
                  'LIST_NOREQ_ARCS :' : '\nARC    FROM N.    TO N.    T. COST\n',
                }
    
    
    def returnHeadingInfo(line, heading):
        if line.find(heading) == 0:
            line = line.replace('\r','').replace('\n','')
            info = line[line.find(heading) + len(heading):]
        else:
            info = None
        return(info)
    
    def startArcEdgeInfo(line, heading):
        return(line.find(heading) != -1)
    
    def extractReqArcInfo(line):
        l = line.replace('\r\n', '').split(' ')
        (inN, outN) = l[0].replace('(','').replace(')','').split(',')
        (inN, outN) = (int(inN), int(outN))
        serv_cost = int(l[4])
        trav_cost = int(l[8])
        demand = int(l[-1])
        return(inN, outN, trav_cost, demand, serv_cost)
    
    def extractReqEdgeInfo(line):
        l = line.replace('\r\n', '').split(' ')
        (inN, outN) = l[0].replace('(','').replace(')','').split(',')
        (inN, outN) = (int(inN), int(outN))
        serv_cost = int(l[4])
        trav_cost = int(l[9])
        demand = int(l[-1])
        return(inN, outN, trav_cost, demand, serv_cost)
        
    def extractNonReqInfo(line):
        l = line.replace('\r\n', '').split(' ')
        (inN, outN) = l[0].replace('(','').replace(')','').split(',')
        (inN, outN) = (int(inN), int(outN))
        trav_cost = int(l[4])
        return(inN, outN, trav_cost)
    
    headings = True
    reqArcsF = False
    nonReqArcsF = False
    reqEdgesF = False
    nonReqEdgesF = False
    
    reqArcs = []
    nonReqArcs = []
    reqEdges = []
    nonReqEdges = []
    
    with open(inputfile, 'r') as lpr_file:
        with open(outputFile, 'w') as outputFile:
            outputFile.write('Name:\t\t%s\n'%outname)
            outputFile.write('Optimal value:\t-1\n')
            
            for i in lpr_file.readlines():
                
                if startArcEdgeInfo(i, 'LIST_REQ_EDGES :') or startArcEdgeInfo(i, 'LIST_REQ_ARCS : '): headings = False
                
                if headings == True:
                    info = returnHeadingInfo(i, 'NODES : ')
                    if info: nNodes = int(info)
                    info = returnHeadingInfo(i, 'REQ_EDGES : ')
                    if info: nReqEdges = int(info)
                    info = returnHeadingInfo(i, 'NOREQ_EDGES : ')
                    if info: nNonReqEdges = int(info)         
                    info = returnHeadingInfo(i, 'REQ_ARCS : ')
                    if info: nReqArcs = int(info)    
                    info = returnHeadingInfo(i, 'NOREQ_ARCS : ')
                    if info: nNonReqArcs = int(info)      
                    info = returnHeadingInfo(i, 'VEHICLES : ')
                    if info: nVehicles = int(info)
                    info = returnHeadingInfo(i, 'CAPACITY : ')
                    if info: capacity = int(info) 
                    info = returnHeadingInfo(i, 'DUMPING_COST : ')
                    if info: dumpCost = int(info)
                    info = returnHeadingInfo(i, 'MAX_TRIP : ')
                    if info: maxTrip = int(info)
                
                elif startArcEdgeInfo(i, 'DEPOT :'):
                    reqArcsF = False
                    nonReqArcsF = False
                    reqEdgesF = False
                    nonReqEdgesF = False
                    depot = int(returnHeadingInfo(i, 'DEPOT : ')) 
            
                elif startArcEdgeInfo(i, 'LIST_REQ_EDGES'):
                    reqArcsF = False
                    nonReqArcsF = False
                    reqEdgesF = True
                    nonReqEdgesF = False
                    
                elif startArcEdgeInfo(i, 'LIST_REQ_ARCS'):
                    reqArcsF = True
                    nonReqArcsF = False
                    reqEdgesF = False
                    nonReqEdgesF = False
            
                elif startArcEdgeInfo(i, 'LIST_NOREQ_ARCS'):
                    reqArcsF = False
                    nonReqArcsF = True
                    reqEdgesF = False
                    nonReqEdgesF = False
                    
                elif startArcEdgeInfo(i, 'LIST_NOREQ_EDGES'):
                    reqArcsF = False
                    nonReqArcsF = False
                    reqEdgesF = False
                    nonReqEdgesF = True             
                
                elif reqArcsF:
                    reqArcs.append(extractReqArcInfo(i))
                
                elif nonReqArcsF:
                    nonReqArcs.append(extractNonReqInfo(i))
                
                elif reqEdgesF:
                    reqEdges.append(extractReqEdgeInfo(i))
                
                elif nonReqEdgesF:
                    nonReqEdges.append(extractNonReqInfo(i))
            
            outputFile.write('#Vehicles:\t%i\n'%nVehicles)
            outputFile.write('Capacity:\t%i\n'%capacity)
            outputFile.write('Depot Node:\t%i\n'%depot)
            outputFile.write('#Nodes:\t\t%i\n'%nNodes)
            outputFile.write('#Edges:\t\t%i\n'%(nReqEdges + nNonReqEdges))
            outputFile.write('#Arcs:\t\t%i\n'%(nReqArcs + nNonReqArcs))
            outputFile.write('#Required N:\t%i\n'%0)
            outputFile.write('#Required E:\t%i\n'%nReqEdges)
            outputFile.write('#Required A:\t%i\n'%nReqArcs)
            
            outputFile.write('\nReN.\tDEMAND\tS. COST\n')
    #         outputFile.write('N%i\t0\t%i\n'%(depot, dumpCost))
            
            outputFile.write('\nReE.\tFrom N.\tTo N.\tT. COST\tDEMAND\tS. COST\n')
            for i, line in enumerate(reqEdges):
                outputFile.write('E%i\t'%(i + 1 + len(nonReqEdges)) + '%i\t%i\t%i\t%i\t%i\n'%line)
    
            outputFile.write('\nEDGE\tFROM N.\tTO N.\tT. COST\n')
            for i, line in enumerate(nonReqEdges):
                outputFile.write('NrE%i\t'%(i + 1) + '%i\t%i\t%i\n'%line)
            
            outputFile.write('\nReA.\tFROM N.\tTO N.\tT. COST\tDEMAND\tS. COST\n')
            for i, line in enumerate(reqArcs):
                outputFile.write('A%i\t'%(i + 1 + len(nonReqArcs)) + '%i\t%i\t%i\t%i\t%i\n'%line)
                
            outputFile.write('\nARC\tFROM N.\tTO N.\tT. COST\n')
            for i, line in enumerate(nonReqArcs):
                outputFile.write('NrA%i\t'%(i + 1) + '%i\t%i\t%i\n'%line)
                
if __name__ == "__main__":
    
    inputOutputMapping = {'Lpr-a-01.txt' : 'BHW1.dat',
                          'Lpr-a-02.txt' : 'BHW2.dat',
                          'Lpr-a-03.txt' : 'BHW3.dat',
                          'Lpr-a-04.txt' : 'BHW4.dat',
                          'Lpr-a-05.txt' : 'BHW5.dat',
                          'Lpr-b-01.txt' : 'BHW6.dat',
                          'Lpr-b-02.txt' : 'BHW7.dat',
                          'Lpr-b-03.txt' : 'BHW8.dat',
                          'Lpr-b-04.txt' : 'BHW9.dat',
                          'Lpr-b-05.txt' : 'BHW10.dat',
                          'Lpr-c-01.txt' : 'BHW11.dat',
                          'Lpr-c-02.txt' :'BHW12.dat',
                          'Lpr-c-03.txt' :'BHW13.dat',
                          'Lpr-c-04.txt' :'BHW14.dat',
                          'Lpr-c-05.txt' :'BHW15.dat'}
    
    fileName = os.listdir('../data/Lpr/')
    for f in fileName:
        print(f)
        outName = inputOutputMapping[f]
        writeMCGRP_format('../data/Lpr/' + f, outName, f)