'''
Created on 19 Sep 2017

@author: eliaswillemse
'''
import py_return_problem_data as rd
import alg_shortest_paths as sp

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

def decodeMCGRP(solFile):
    
    with open(solFile) as solFile:
        
        solution = {}
        nVehicles = -1
        for l in solFile.readlines()[4:]:
            nVehicles += 1
            info = l.replace('\n','').replace(')','').split('(')
            solutionInfo = info[0].strip().split(' ')
            demand = int(solutionInfo[3])
            cost = int(solutionInfo[4])
            routeSeq = [x.strip().split(',')[1:] for x in info[1:]]
            routeSeq = [(int(x[0]), int(x[1])) for x in routeSeq]
            solution[nVehicles] = {'Cost' : cost, 'Demand' : demand, 'RouteSequence' : routeSeq}
        nVehicles += 1
        
        solution['nVehicles'] = nVehicles
        solution['TotalCostEtimate'] = sum([solution[x]['Cost'] for x in range(nVehicles)])
        solution['TotalDemand'] = sum([solution[x]['Demand'] for x in range(nVehicles)])
        
        return(solution)

def fullSolutionCost(rawInfo, arc_data, sp_info, solution, info):
    
    depotKey = arc_data.allIndexD[arc_data.depotnewkey]
    
    arcsServed = set()
    arcsNotServed = set(arc_data.reqArcList)
    arcsNotServed.remove(arc_data.depotnewkey)
    
    for i in range(solution['nVehicles']):
        
        extraArcsServed = set()
        arcsServedList = [rawInfo[x]['arcI'] for x in solution[i]['RouteSequence'][1:-1]]
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
        
        serviceCost = sum([rawInfo[x]['s'] for x in solution[i]['RouteSequence']])
        demand = sum([rawInfo[x]['d'] for x in solution[i]['RouteSequence']])
        
        if demand > arc_data.capacity: demandFlag = False
        else: demandFlag = True
        
        if solution[i]['RouteSequence'][0] != depotKey or solution[i]['RouteSequence'][-1] != depotKey: depotStartEnd = False
        else: depotStartEnd = True
        
        ifCost = arc_data.dumpCost
        solution[i]['ServiceCost'] = serviceCost
        solution[i]['DumpCost'] = ifCost
        travCost = 0
        fullSequence = []
        for j in range(len(solution[i]['RouteSequence']) - 1):
            origin = solution[i]['RouteSequence'][j]
            fullSequence.append(('Service',rawInfo[origin]))
            destination = solution[i]['RouteSequence'][j + 1]
            (spSeq, dist) = returnSPrawSequence(rawInfo, arc_data, sp_info, origin, destination)
            travCost += sum(x['t'] for x in spSeq)
            for subSeq in spSeq:
                fullSequence.append(('Traverse', subSeq))
                
        fullSequence.append(('Service', rawInfo[destination]))
        solution[i]['Demand'] = demand
        solution[i]['FullSequence'] = fullSequence
        solution[i]['DeadheadCost'] = travCost
        solution[i]['RouteCost'] = solution[i]['DeadheadCost'] + solution[i]['ServiceCost'] + solution[i]['DumpCost'] 
        solution[i]['CapacityMet'] = demandFlag
        solution[i]['DepotMet'] = depotStartEnd
        solution[i]['ExtraArcsServed'] = extraArcsServed

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
        print('\nRoute %i'%i)
        print('-----------------------------------')
        print('Total cost: %i'%solution[i]['RouteCost'])
        print('Service cost: %i'%solution[i]['ServiceCost'])
        print('Travel cost: %i'%solution[i]['DeadheadCost'])
        print('Off-load cost: %i'%solution[i]['DumpCost'])
        print('Demand serviced: %i'%solution[i]['Demand'])
        print('Capacity constraint met: %s'%solution[i]['CapacityMet'])
        print('Starts and ends at depot: %s'%solution[i]['DepotMet'])
        if solution[i]['ExtraArcsServed']:
            print('Arcs needlessly serviced: True')
            for i in solution[i]['ExtraArcsServed']: print(i)
        else: print('Arcs needlessly serviced: False')



if __name__ == "__main__":
    
    solAnalysis = 'Lpr-c-05'
    
    problem_set = 'Lpr'
    filename = solAnalysis + '_problem_info.dat'
    
    (rawInfo, arc_data, sp_info, info) = returnRawProblemInfo(problem_set, filename)

    solution = decodeMCGRP(solAnalysis + '.sol')
    solution = fullSolutionCost(rawInfo, arc_data, sp_info, solution, info)
    summarizeSolution(solution)