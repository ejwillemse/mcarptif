'''
Created on 19 Sep 2017

@author: eliaswillemse
'''
import py_return_problem_data as rd
import alg_shortest_paths as sp
import cPickle

SOLUTIONFOLDER = '../LS_InputData/FinalSolutions/'

def returnRawProblemInfo(problem_set, filename):

    info = rd.return_problem_data(problem_set, filename)
    sp_info = rd.return_sp_data(problem_set, filename)
    arc_data = rd.return_arc_data(problem_set, filename)

    rawInfo = {}
    for i, index in enumerate(arc_data.reqArcList): 
        rawInfo[arc_data.allIndexD[index]] = {'arc' : arc_data.allIndexD[index], 'arcI' : index, 'reqArcI' : i, 's' : arc_data.serveCostL[i], 't' : arc_data.travelCostL[index], 'd' : arc_data.demandL[i]}
        
    for arcKey in arc_data.allIndexD: 
        if arcKey not in arc_data.reqArcList:
            rawInfo[arc_data.allIndexD[arcKey]] = {'arc' : arc_data.allIndexD[arcKey], 'arcI' : arcKey, 't' : arc_data.travelCostL[arcKey]}
    
    return(rawInfo, arc_data, sp_info, info)

def returnSPrawSequence(rawInfo, arc_data, sp_info, origin, destination):
    arc_1 = rawInfo[origin]['arcI']
    arc_2 = rawInfo[destination]['arcI']
    pathList = [(rawInfo[arc_data.allIndexD[i]]) for i in sp.spSource1List(sp_info.p_full, arc_1, arc_2)]
    return(pathList, sp_info.d_full[arc_1][arc_2])

def decodeMCARPTIF(solFile, arc_data):
    
    with open(SOLUTIONFOLDER + solFile) as solFile:
        
        solutionFile = cPickle.load(solFile)
        solution = solutionFile
        
        for i in range(solution['nVehicles']):
            seq = []
            for j, t in enumerate(solution[i]['Trips']):
                seq.append([])
                for k, arc in enumerate(t):
                    addPureArc = False
                    
                    if k == 0: addPureArc = True
                    if (j == len(solution[i]['Trips']) - 1 and k == len(t) - 2) or  k == len(t) - 1: addPureArc = True
                    
                    if addPureArc: 
                        seq[-1].append(arc_data.allIndexD[arc])
                    else: 
                        seq[-1].append(arc_data.allIndexD[arc_data.reqArcList[arc]])
                    
            solution[i]['FullTripServiceSequence'] = seq[:]
        return(solution)

def fullSolutionCost(rawInfo, arc_data, sp_info, solution, info):
    
    depotKey = arc_data.allIndexD[arc_data.depotnewkey]
    
    arcsServed = set()
    arcsNotServed = set(arc_data.reqArcList)
    arcsNotServed.remove(arc_data.depotnewkey)
    arcsNotServed = arcsNotServed.difference(arc_data.IFarcsnewkey)
    
    for i in range(solution['nVehicles']):
        
        solution[i]['FullSequence'] = []
        solution[i]['Demand'] = []
        solution[i]['DeadheadCost'] = []
        solution[i]['SubRouteCost'] = []
        solution[i]['CapacityMet'] = []
        solution[i]['ExtraArcsServed'] = []
        solution[i]['ServiceCost'] = []
        solution[i]['DumpCost'] = []
        #solution[i]['DepotMet'] = depotStartEnd
        
        for j in range(len(solution[i]['FullTripServiceSequence'])):
        
            extraArcsServed = set()
            arcsServedList = solution[i]['Trips'][j][1:-1]
            arcsServedInRoute = set(arcsServedList)
        
            for indexI in arcsServedList:
                if indexI in arcsServed:
                    extraArcsServed.add(arc_data.allIndexD[indexI])
                else:
                    arcsServed.add(indexI)
                    if arc_data.invArcL[indexI] != None:
                        arcsServed.add(arc_data.invArcL[indexI])
            
            invArcsServedInRoute = set(arc_data.invArcL[x] for x in arcsServedInRoute if arc_data.invArcL[x] != None)
            arcsServedInRoute = arcsServedInRoute.union(invArcsServedInRoute)
            arcsNotServed = arcsNotServed.difference(arcsServedInRoute)
            
            serviceCost = sum([rawInfo[x]['s'] for x in solution[i]['FullTripServiceSequence'][j]])
            demand = sum([rawInfo[x]['d'] for x in solution[i]['FullTripServiceSequence'][j]])
            
            if demand > arc_data.capacity: demandFlag = False
            else: demandFlag = True
        
            ifCost = arc_data.dumpCost
            solution[i]['ServiceCost'].append(serviceCost)
            solution[i]['DumpCost'].append(ifCost)
            
            travCost = 0
            fullSequence = []
            for k in range(len(solution[i]['FullTripServiceSequence'][j]) - 1):
                origin = solution[i]['FullTripServiceSequence'][j][k]
                if j == len(solution[i]['FullTripServiceSequence']) - 1:
                    if k == len(solution[i]['FullTripServiceSequence'][j]) - 2:
                        fullSequence.append(('LastIF', rawInfo[origin]))
                    else:
                        fullSequence.append(('Service', rawInfo[origin]))
                else:
                    fullSequence.append(('Service', rawInfo[origin]))
                destination = solution[i]['FullTripServiceSequence'][j][k + 1]
                (spSeq, dist) = returnSPrawSequence(rawInfo, arc_data, sp_info, origin, destination)
                travCost += sum(x['t'] for x in spSeq)
                for subSeq in spSeq:
                    fullSequence.append(('Travel', subSeq))
                
            fullSequence.append(('Service', rawInfo[destination]))
            
            solution[i]['Demand'].append(demand)
            solution[i]['FullSequence'].append(fullSequence)
            solution[i]['DeadheadCost'].append(travCost)
            solution[i]['SubRouteCost'].append(solution[i]['DeadheadCost'][j] + solution[i]['ServiceCost'][j] + solution[i]['DumpCost'][j])
            solution[i]['CapacityMet'].append(demandFlag)
            solution[i]['ExtraArcsServed'].append(extraArcsServed)
            #solution[i]['DepotMet'] = depotStartEnd
    
        solution[i]['RouteCost'] = sum([x for x in solution[i]['SubRouteCost']])
        if solution[i]['RouteCost'] > arc_data.maxTrip: costFlag = False
        else: costFlag = True
        solution[i]['Duration'] = costFlag
    
    solution['ArcsNotServed'] = set(arc_data.allIndexD[x] for x in arcsNotServed)
    solution['TotalCost'] = sum([solution[x]['RouteCost'] for x in range(solution['nVehicles'])])
        
    return(solution)

def summarizeSolution(solution):
    print('\n======================================')
    print('Final solution values and errors')
    print('======================================')
    print('Total cost: %i'%(solution['TotalCost']))
    print('#Vehicles: %i'%(solution['nVehicles']))
    
    if solution['ArcsNotServed']:
        print('\nAll arcs serviced: False')
        for i in solution['ArcsNotServed']: print(i)
    else: print('\nAll arcs serviced: True')
    
    print('\n======================================')
    print('Route values and errors')
    print('======================================')
    
    for i in range(solution['nVehicles']):
        print('\nRoute %i'%(i))
        print('Number of trips: %i'%len(solution[i]['FullTripServiceSequence']))
        print('Total cost: %i'%solution[i]['RouteCost'])
        print('Time-duration constraint met: %s'%solution[i]['Duration'])
        print('-----------------------------------')
        for j in range(len(solution[i]['FullTripServiceSequence'])):
            print('\nRoute %i Trip %i'%(i, j))
            print('-----------------------------------')
            print('Service cost: %i'%solution[i]['ServiceCost'][j])
            print('Travel cost: %i'%solution[i]['DeadheadCost'][j])
            print('Off-load cost: %i'%solution[i]['DumpCost'][j])
            print('Demand serviced: %i'%solution[i]['Demand'][j])
            print('Capacity constraint met: %s'%solution[i]['CapacityMet'][j])
            if solution[i]['ExtraArcsServed'][j]:
                print('Arcs needlessly serviced: True')
                for arc in solution[i]['ExtraArcsServed'][j]: print(arc)
            else: print('Arcs needlessly serviced: False')

def printSolution(solution, arcinfo, solutionFile):
    
    output = open(solutionFile, 'w')
    headings = 'RouteID,TripID,ServiceSeqID,ArcNodeIn,ArcNodeOut,TraversalType,TraversalTime,AmountWaterSprayed,RemainingWater,CummulativeWorkTime,RemainingWorkTime'
    print(headings)
    output.write(headings + '\n')
    for i in range(solution['nVehicles']):
        CummulativeWorkTime = 0
        RemainingWater = arcinfo.capacity
        RemainingWorkTime = arcinfo.maxTrip
        for j in range(len(solution[i]['FullSequence'])):
            RouteID = i + 1
            TripID = j + 1
            ServiceSeqID = -1
            for k in range(len(solution[i]['FullSequence'][j])):
                #print(solution[i]['FullSequence'][j][k])
                Depot = False
                Reload = False
                if j == 0:
                    if k == 0: Depot = True
                if j == len(solution[i]['FullSequence']) - 1:
                    if solution[i]['FullSequence'][j][k][0] == 'LastIF': Reload = True
                    if k == len(solution[i]['FullSequence'][j]) - 1: Depot = True  
                elif len(solution[i]['FullSequence']) > 1:
                    if k == 0 and j != 0: continue
                    if k == len(solution[i]['FullSequence'][j]) - 1: Reload = True
                
                ServiceSeqID += 1
                arcInfo = solution[i]['FullSequence'][j][k]
                ArcNodeIn = arcInfo[1]['arc'][0]
                ArcNodeOut = arcInfo[1]['arc'][1]
                
                if Depot:
                    TraversalType = 'DepotVist'
                    TraversalTime = 0
                    AmountWaterSprayed = 0
                elif Reload:
                    TraversalType = 'WaterReload'
                    TraversalTime = solution[i]['DumpCost'][j]
                    AmountWaterSprayed = RemainingWater-arcinfo.capacity               
                else:
                    TraversalType = arcInfo[0]
                    if TraversalType == 'Travel':
                        TraversalTime = arcInfo[1]['t']
                        AmountWaterSprayed = 0
                    if TraversalType == 'Service':
                        TraversalTime = arcInfo[1]['s']
                        AmountWaterSprayed = arcInfo[1]['d']
                
                RemainingWater -= AmountWaterSprayed
                CummulativeWorkTime += TraversalTime
                RemainingWorkTime -= TraversalTime
                outline = ','.join(map(str, [RouteID, TripID, ServiceSeqID, ArcNodeIn, ArcNodeOut, TraversalType, TraversalTime, AmountWaterSprayed, RemainingWater, CummulativeWorkTime, RemainingWorkTime])) 
                print(outline)
                output.write(outline + '\n')
    output.close()

if __name__ == "__main__":
    
    solAnalysis = 'WaterTrucU_5R_bestNATS_NN1_tau5.dat'
    
    problem_set = 'WaterTruck'
    problem_name = 'WaterTruc'
    solutionFile = 'WaterTruckU_5R_bestNATS_NN1_tau5.csv'
    filename = problem_name + '_problem_info.dat'
    
    print(solutionFile)
    (rawInfo, arc_data, sp_info, info) = returnRawProblemInfo(problem_set, filename)

    solution = decodeMCARPTIF(solAnalysis, arc_data)
    solution = fullSolutionCost(rawInfo, arc_data, sp_info, solution, info)
    #print(solution)
    summarizeSolution(solution)
    printSolution(solution, arc_data, solutionFile)