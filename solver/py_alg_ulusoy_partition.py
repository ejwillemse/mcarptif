# Optimally partition an existin route using Ulusoy's heuristic.
# Elias Willemse, CSIR Pretoria, Created 14 October 2009. 
#
#
# Derived from the articles:
# Belenguer, J., Benavent, E., Lacomme, P., Prins, C. (2006). Lower and uper 
# bounds for the mixed capacitated arc routing problem. Computers and Operations
# Research. 33(12) 
# p. 3363-3383.
# Specifically pages 3371-3372.
#
# Ghiani, G., Guerriero, F. Laporte, G., Musmanno, R. (2004). Tabu search 
# heuristics for the Arc Routing Problem with Intermediate Facilities under
# Capacity and Length Restrictions. Journal of Mathematical Modelling and 
# Algorithms. 3()
# p 209-223
# Specifically pages 211-213 
#
# Ghiani, G. Improta, G., Laporte, G. (2001). The Capacitated Arc Routing 
# Problem with Intermediate Facilities. Networks. 37(3)
# p 134-143
# Specifically pages 137-138

import numpy as np
import pyximport
pyximport.install(setup_args={"include_dirs":np.get_include()})

import alg_Ulusoy_part_c as c_alg_Ulusoy_part

from math import ceil

import evaluatesolutions
import py_solution_builders as build_solution
from time import clock
from py_display_solution import display_solution_stats 

huge = 1e30000 

def populate_c(info, full = False):
    c_alg_Ulusoy_part.set_input(info, full)

def free_c(full = False):
    c_alg_Ulusoy_part.free_input(full)

def DagSP(G, verticeS, source):
    '''
    Computes the single source shortest path in a directed acyclic graph.
    G must be in started succesor vertex format,i.e., G = {arc : {succesor arc : arc weight}}
    verticeS refers to a typologically sorted list of the verices.
    '''
    huge = 1e30000# Infinity
    dEst = {}.fromkeys(verticeS)
    piEst = {}.fromkeys(verticeS)
    
    for v in verticeS:
        dEst[v] = huge
        piEst[v] = None
        
    dEst[source] = 0
    
    for u in verticeS:
        for v in G[u].keys():
            if dEst[v] > dEst[u] + G[u][v]:
                dEst[v] = dEst[u] + G[u][v]
                piEst[v] = u
                
    return(dEst, piEst)

def sp1SourceList(piEst, origin, destination):
    '''
    Generate shortest path visitation list based on presidence dictionary, and 
    an origin and destination. 
    '''
    pathList = [destination]
    a = destination
    while True:
        a = piEst[a]
        pathList.append(a)
        if a == origin:break
    pathList.reverse()
    return(pathList)

def spAuxGraph(G, route, source):
    '''
    Determines the shortest path and predecessor dict on the auxiliray
    graph.
    '''
    (spDistance, spPath) = DagSP(G, route, source)
    return(spDistance, spPath)

def spSolution(spDistance, spPath, source, destination):
    '''
    Determines the actual shortest path sequence and distance between
    a start and end point.
    '''
    Path = sp1SourceList(spPath, source, destination)
    return(spDistance[destination], Path)

def spAuxToSolution(finalDistance, Path, originalRoute):
    '''
    Converts the shortest path on the auxiliray graph to the actual
    partitioning of the original route.
    '''
    solution = []
    nVehicles = len(Path) - 1

    for i in range(nVehicles):
        sequence = originalRoute[Path[i]:Path[i + 1]]
        solution.append(sequence)
    return(solution)

class Ulusoys(object):
    '''
    Optimally partition a giant route by including trips back to the depot.
    Only works if there is no maximum vehicle trip length and when there are
    no intermediate facilities, and there is only one depot. Can be converted
    to cater for multiple depots.
    '''    
    def __init__(self, info):
        self.info = info
        self.capacity = info.capacity
        self.dumpCost = info.dumpCost
        self.reqArcs = info.reqArcListActual
        self.depot = info.depotnewkey
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.c_modules = True
    
    def c_genAuxGraphSP(self, routeOrig, min_k = True):
        (dEst_end, Path, G, L) = c_alg_Ulusoy_part.genAuxGraphSP(routeOrig, min_k)
        return(dEst_end, Path, G, L) 
        
    def genAuxGraphSP(self, routeOrig):
        '''
        Generates the auxiliry graph and determines the shortest path through
        the graph - the optimal partition. Original route should not contain the 
        depot visits.
        '''
        depot = self.depot
        capacity = self.capacity
        spD = self.d
        demand = self.demand
        serveCost = self.serveCost
        route = routeOrig[:]
        
        dumpCost = self.dumpCost
        
        spRoute = [0]
        for i in range(1, len(route)): 
        # Determines the shortest path length between two arcs connected 
        # in original route.
            spRoute.append(spD[route[i - 1]][route[i]])
                
        sRoute = route[:]
        huge = 1e30000# Infinity
        dEst = {}
        piEst = {}
        L = {}
        G = {}
        K = {}
        
        auxNodes = range(len(sRoute) + 1)
        for i in auxNodes:
            dEst[i] = huge
            piEst[i] = None
            K[i] = huge
        dEst[0] = 0
        K[0] = 0
        
        for i in range(len(sRoute)):
            L[i] = {}
            G[i] = {}
            load = 0
            serviceC = 0
            spCosts = 0
            for j in range(i + 1, len(sRoute) + 1):
                load = load + demand[sRoute[j - 1]]
                if load > capacity: break
                else:
                    if (j - i) > 1:
                        spCosts = spCosts + spD[sRoute[j - 2]][sRoute[j - 1]]
                    serviceC = serviceC + serveCost[sRoute[j - 1]]
                    dDedge = spD[depot][sRoute[i]] + serviceC + spCosts + \
                             spD[sRoute[j - 1]][depot] + dumpCost 
                    L[i][j] = load
                    G[i][j] = dDedge
                    if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + dDedge)):
                        K[j] = K[i] + 1
                        dEst[j] = dEst[i] + dDedge
                        piEst[j] = i
        
        Path = sp1SourceList(piEst, auxNodes[0], auxNodes[ - 1])
        return(dEst[auxNodes[ - 1]], Path, G, L)
    
    def gen_solution_list(self, bigRoute, min_k = True):
        '''
        Generate a partitioned solution
        '''
        if self.c_modules: (finalDistance, Path, G, L) = self.c_genAuxGraphSP(bigRoute, min_k)       
        else: (finalDistance, Path, G, L) = self.genAuxGraphSP(bigRoute)
        solutionlist = spAuxToSolution(finalDistance, Path, bigRoute)
        return(solutionlist, Path, G, L)
    
    def genSolutionPartial(self, bigRoute, min_k = True):
        depo = self.depot
        (solutionIncomplete, Path, G, L) = self.gen_solution_list(bigRoute, min_k)
        nVehiclesCalc = len(Path) - 1
        
        solution = {}
        Tcost = 0        
        for i in xrange(nVehiclesCalc):
            solution[i] = {}
            solution[i]['Route'] = build_solution.insert_depot(solutionIncomplete[i],depo)
            solution[i]['Load'] = L[Path[i]][Path[i + 1]]
            solution[i]['Cost'] = G[Path[i]][Path[i + 1]]
            Tcost = Tcost + G[Path[i]][Path[i + 1]]
        solution['ProblemType'] = 'CARP'
        solution['TotalCost'] = Tcost
        solution['nVehicles'] = nVehiclesCalc
        return(solution)
    
    def genCompleteSolutionPartial(self, solution):
        nVehiclesCalc = solution['nVehicles']
        for i in xrange(nVehiclesCalc):
            if solution[i].get('Deadhead') != None: break
            (solution[i]['Deadhead'], solution[i]['Service']) = build_solution.generate_trip_info(solution[i]['Route'], 
                                                                                                     self.d, 
                                                                                                     self.serveCost, 
                                                                                                     self.dumpCost, 
                                                                                                     self.demand)[:2]
        return(solution)
    
    def genSolution(self, bigRoute, min_k = True):
        '''
        Generate a partitioned solution in vehicle dictionary standard.
        '''
        depo = self.depot
        (solutionIncomplete, Path, G, L) = self.gen_solution_list(bigRoute, min_k)
        nVehiclesCalc = len(Path) - 1
        
        solution = {}
        Tcost = 0        
        for i in xrange(nVehiclesCalc):
            solution[i] = {}
            solution[i]['Route'] = build_solution.insert_depot(solutionIncomplete[i],depo)
            solution[i]['Load'] = L[Path[i]][Path[i + 1]]
            solution[i]['Cost'] = G[Path[i]][Path[i + 1]]
            (solution[i]['Deadhead'], solution[i]['Service']) = build_solution.generate_trip_info(solution[i]['Route'], 
                                                                                                     self.d, 
                                                                                                     self.serveCost, 
                                                                                                     self.dumpCost, 
                                                                                                     self.demand)[:2]
            Tcost = Tcost + G[Path[i]][Path[i + 1]]
        solution['ProblemType'] = 'CARP'
        solution['TotalCost'] = Tcost
        solution['nVehicles'] = nVehiclesCalc
        return(solution)
            
class UlusoysIFs_1vehicle(object):
    '''
    Optimally partition a giant route by including trips to intermediate 
    facilities. Only works if there is one vehicle 
    and when there is one depot. No intermediate facilities but can be converted
    to cater for multiple depots.    
    '''
    
    def __init__(self, info):
        self.capacity = info.capacity
        self.maxTrip = info.maxTrip
        self.dumpCost = info.dumpCost
        self.reqArcs = info.reqArcListActual
        self.depot = info.depotnewkey
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.if_cost = info.if_cost_np
        self.if_arc = info.if_arc_np
        self.c_modules = True
            
    def genAuxGraphSP(self, routeOrig):
        '''
        Generates the auxiliary graph and determines the shortest path through
        the graph - the optimal partition. Original route should not contain the 
        depot visits.
        '''
        depot = self.depot
        capacity = self.capacity
        spD = self.d
        route = routeOrig[:]
        dumpCost = self.dumpCost
        bestIFdistD = self.if_cost
        serviceC = self.serveCost
        demandD = self.demand
        serveCostD = self.serveCost
        
        spRoute = [0]
        for i in range(1, len(route)): # Determines the shortest path length between two arcs connected in original route.
            spRoute.append(spD[route[i - 1]][route[i]])
                
        sRoute = route[:]
              
        huge = 1e30000# Infinity
        dEst = {}
        piEst = {}
        L = {}
        G = {}
        IFbest = {}
        
        auxNodes = range(len(sRoute) + 1)
        for i in auxNodes:
            dEst[i] = huge
            piEst[i] = None
        dEst[0] = 0
        
        for i in range(len(sRoute)):
            L[i] = {}
            G[i] = {}
            IFbest[i] = {}
            load = 0
            serviceC = 0
            for j in range(i + 1, len(sRoute) + 1):
                load = load + demandD[sRoute[j - 1]]
                if load > capacity: break
                else:
                    serviceC = serviceC + serveCostD[sRoute[j - 1]]
                    if j == len(sRoute): 
                        bestIFdist = bestIFdistD[sRoute[j - 1]][depot]
                    else:
                        bestIFdist = bestIFdistD[sRoute[j - 1]][sRoute[j]]
                    if i == 0:
                        dDedge = spD[depot][sRoute[i]] + bestIFdist + serviceC + sum(spRoute[i + 1:j])
                    else:
                        dDedge = bestIFdist + serviceC + sum(spRoute[i + 1:j]) 
                    L[i][j] = load
                    G[i][j] = dDedge
                    if dEst[j] > dEst[i] + dDedge:
                        dEst[j] = dEst[i] + dDedge
                        piEst[j] = i 
        
        Path = sp1SourceList(piEst, auxNodes[0], auxNodes[ - 1])
        return(dEst[auxNodes[ - 1]], Path, G, L)

    def genAuxGraphSP_article(self, routeOrig):
        '''
        Different implementation based on the work of Lancomme et all, and on PhD by Elias Willemse.
        Python implementation is more efficient, but not the cython implementation.
        '''
        depot = self.depot
        capacity = self.capacity
        spD = self.d
        sRoute = routeOrig[:]
        bestIFdistD = self.if_cost
        demandD = self.demand
        serveCostD = self.serveCost
        
        huge = 1e30000# Infinity

        n = len(sRoute)
        spRoute = np.zeros((n - 1))
        ifRoute = np.zeros((n))
        for i in range(n - 1):
            spRoute[i] = spD[sRoute[i]][sRoute[i + 1]]
            ifRoute[i] = bestIFdistD[sRoute[i]][sRoute[i + 1]]
        ifRoute[i + 1] = bestIFdistD[sRoute[n - 1]][depot]
        
        N = np.array([huge]*(n + 1))
        P = np.array([None]*(n + 1))
        N[0] = spD[depot][sRoute[0]]
        P[0] = 0
        
        for i in range(n):
            load = cost = 0
            for j in range(i, n):
                arc_j = sRoute[j]
                load = load + demandD[arc_j]
                if load > capacity: break
                a = serveCostD[arc_j] + ifRoute[j]
                if i == j: cost = a
                else: cost = cost + a - ifRoute[j - 1] + spRoute[j - 1]
                dTemp = N[i] + cost 
                if dTemp < N[j + 1]:
                    N[j + 1] = dTemp
                    P[j + 1] = i
        
        Path = sp1SourceList(P, 0, n)
        G, L = None, None
        return(N[-1], Path, G, L)

    def genAuxGraphSP_efficient(self, routeOrig):
        '''
        Different implementation based on the work of Lancomme et all, and on PhD by Elias Willemse.
        Python implementation is more efficient, but not the cython implementation.
        '''
        capacity = self.capacity
        demandD = self.demand
        Path = [0]
        n = len(routeOrig)
        load = 0
        for i in range(n):
            arc_i = routeOrig[i]
            load += demandD[arc_i]
            if load > capacity:
                load = 0 
                Path.append(i)
                load = demandD[arc_i]
        if Path[-1] <> (n): Path.append(n)
        return(0, Path, [], [])

    def c_genAuxGraphSP(self, routeOrig):
        (dEst_end, Path, G, L) = c_alg_Ulusoy_part.genAux1IFGraphSP(routeOrig)
        return(dEst_end, Path, G, L) 

    def c_genAuxGraphSP_article(self, routeOrig):
        (dEst_end, Path, G, L) = c_alg_Ulusoy_part.genAuxGraphSP_article(routeOrig)
        return(dEst_end, Path, G, L)

    def c_genAuxGraphSP_efficient(self, routeOrig):
        (dEst_end, Path, G, L) = c_alg_Ulusoy_part.genAuxGraphSP_efficient(routeOrig)
        return(dEst_end, Path, G, L)
    
    def gen_solution_list(self, bigRoute):
        '''
        Generate a partioned solution
        '''
        if self.c_modules: (finalDistance, Path, G, L) = self.c_genAuxGraphSP(bigRoute)       
        else: (finalDistance, Path, G, L) = self.genAuxGraphSP(bigRoute)
        solutionlist = spAuxToSolution(finalDistance, Path, bigRoute)
        return(solutionlist, Path, G, L, finalDistance)

    def gen_solution_list_article(self, bigRoute):
        '''
        Generate a partioned solution
        '''
        if self.c_modules: (finalDistance, Path, G, L) = self.c_genAuxGraphSP_article(bigRoute)       
        else: (finalDistance, Path, G, L) = self.genAuxGraphSP_article(bigRoute)
        solutionlist = spAuxToSolution(finalDistance, Path, bigRoute)
        return(solutionlist, Path, G, L, finalDistance)

    def gen_solution_list_efficient(self, bigRoute):
        '''
        Generate a partioned solution
        '''
        if self.c_modules: (finalDistance, Path, G, L) = self.c_genAuxGraphSP_efficient(bigRoute)       
        else: (finalDistance, Path, G, L) = self.genAuxGraphSP_efficient(bigRoute)
        solutionlist = spAuxToSolution(finalDistance, Path, bigRoute)
        return(solutionlist, Path, G, L, finalDistance)

    def genSolution(self, bigRoute):
        '''
        Generate a partioned solution
        '''
        (solutionIncomplete) = [self.gen_solution_list_article(bigRoute)[0]] 
        solution = build_solution.build_CLARPIF_dict(solutionIncomplete, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        return(solution)

    def genSolution_efficient(self, bigRoute):
        '''
        Generate a partitioned solution
        '''
        (solutionIncomplete) = [self.gen_solution_list_efficient(bigRoute)[0]] 
        solution = build_solution.build_CLARPIF_dict(solutionIncomplete, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        return(solution)

    def improve_solution(self, solution, return_flag = False):
        '''
        Take an existing solution, and improve each route by determining the optimal placement of IF partitions.
        '''
        old = solution['TotalCost']
        nRoutes = solution['nVehicles']
        solution_with_ifs = []
        for i in xrange(nRoutes):
            big_routes = solution[i]['Trips']
            combined_route = []
            for route in big_routes:
                combined_route += route[1:-1]
            del combined_route[-1]
            solution_with_ifs.append(self.gen_solution_list(combined_route)[0])
        solution = build_solution.build_CLARPIF_dict(solution_with_ifs, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        if solution['TotalCost'] < old: 
            print('Solution IFs improved by %i'%(solution['TotalCost'] - old))
            improved = True
        else: improved = False
        if return_flag: return(solution, improved)
        else: return(solution)

    def improve_ifs_all_routes(self, solution_list, if_pre_arcs):
        '''
        Do not use. Doesn't return anything! Improve IF visits for all routes in a solution.
        '''
        for i, route_i in enumerate(solution_list):
            combined_route = []
            nIfs = len(if_pre_arcs[i])
            combined_route += route_i[1:if_pre_arcs[i][0]+1]
            #print(combined_route)
            for j in xrange(1,nIfs): combined_route += route_i[if_pre_arcs[i][j-1]+2:if_pre_arcs[i][j]+1] 
            print(self.gen_solution_list(combined_route)[0])
            #print(self.gen_solution_list(combined_route)[0])
    
    def improve_solution_routes(self, routes):
        '''
        Do not use. Doesn't return anything! Improve IF visits for a single route
        '''
        new_routes = []
        for route in routes:
            big_route = []
            for subtrip in route: big_route += subtrip
            
class UlusoysIFs(object):
    '''
    Optimally partition a giant route by including trips to intermediate 
    facilities and by partitioning trips for different vehicles. Only works 
    if there is a maximum vehicle trip length and when there is one 
    depot.
    '''    
    def __init__(self, info):
        self.capacity = info.capacity
        self.maxTrip = info.maxTrip
        self.dumpCost = info.dumpCost
        self.reqArcs = info.reqArcListActual
        self.depot = info.depotnewkey
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.if_cost = info.if_cost_np
        self.if_arc = info.if_arc_np
        self.c_modules = True
        self.output = False
      
    def genAuxGraph1_SP(self, routeOrig):
        '''
        Generates the first auxiliary graph, and determined the shortest paths between all successive auxiliary node. Original route should not contain the 
        depot visits.
        '''
        print('')
        print('Gen Aux graph 1')
        
        depot = self.depot
        capacity = self.capacity
        spD = self.d
        serveCostD = self.serveCost
        demandD = self.demand
        bestIFdistD = self.if_cost
        dumpCost = self.dumpCost
        
        route = routeOrig[:]
        
        spRoute = [0]
        serviceRoute = []
        loadRoute = []
        
        for i in range(1, len(route)): # Determines the shortest path length between two arcs connected in original route.
            spRoute.append(spD[route[i - 1]][route[i]])
            serviceRoute.append(serveCostD[route[i - 1]])
            loadRoute.append(demandD[route[i - 1]])
            
        serviceRoute.append(serveCostD[route[i]])
        loadRoute.append(demandD[route[i]])
                
        sRoute = route[:]     
               
        huge = 1e30000# Infinity
        dEst = {}
        piEst = {}
        
        nReqArcs = len(sRoute)
        #auxNodes = range(nReqArcs + 1)
        
        if self.output: print('Initialise 1')
        for s in xrange(nReqArcs + 1):
            dEst[s] = {}
            piEst[s] = {}
            for v in range(s, nReqArcs + 1):
                dEst[s][v] = huge
                piEst[s][v] = None
            dEst[s][s] = 0
        
        startQ = 0
        if self.output: print('gen 1')
        for i in range(nReqArcs):
            if self.output: print('arc %d of %d' %(i,nReqArcs))
            load = 0
            serv = 0
            for j in range(i + 1, nReqArcs + 1):
                load = load + demandD[sRoute[j - 1]]
                serv = serv + serveCostD[sRoute[j - 1]]

                if load > capacity: break
                else:
                    dDedge = 0
                    if j == len(sRoute): 
                        bestIFdist = bestIFdistD[sRoute[j - 1]][depot]
                    else:
                        bestIFdist = bestIFdistD[sRoute[j - 1]][sRoute[j]]
                    for q in range(startQ, i + 1):
                        dDedge = bestIFdist + sum(serviceRoute[i:j]) + sum(spRoute[i + 1:j]) 
                        if dEst[q][j] > dEst[q][i] + dDedge:
                            dEst[q][j] = dEst[q][i] + dDedge
                            piEst[q][j] = i
        if self.output: print('Finished 1')
        return(dEst, piEst)
    
    def genAuxGraph2_SP(self, dEstIFs, routeOrig):
        '''
        Calculates the optimal vehicle partition using the optimal IF partition from genAuxGraph1_SP. 
        '''
        if self.output: print('')
        if self.output: print('Gen Aux graph 2')
        huge = 1e30000# Infinity
        
        depot = self.depot
        maxTripLength = self.maxTrip
        spD = self.d
        bestIFdistD = self.if_cost
        
        route = routeOrig[:]
        
        dEst = {}
        piEst = {}
        K = {}
        G = {}
        sRoute = route[:]
        
        nReqArcs = len(sRoute)       
        if self.output: print('Initialise 2')
        for i in xrange(nReqArcs + 1):
            dEst[i] = huge
            piEst[i] = None
            K[i] = huge
            
        dEst[0] = 0
        K[0] = 0
        if self.output: print('gen 2')
        for i in xrange(len(sRoute)):
            G[i] = {}
            serviceC = 0
            for j in range(i + 1, len(sRoute) + 1):
                if j == len(sRoute):
                    Edge = spD[depot][sRoute[i]] + dEstIFs[i][j]
                else:
                    Edge = spD[depot][sRoute[i]] + dEstIFs[i][j] - bestIFdistD[sRoute[j - 1]][sRoute[j]] + bestIFdistD[sRoute[j - 1]][depot]
                
                serviceC = serviceC + Edge
                
                if Edge > maxTripLength: 
                    if j == i+1: 
                        G[i][j] = Edge
                        if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + Edge)):
                            K[j] = K[i] + 1
                            dEst[j] = dEst[i] + Edge
                            piEst[j] = i
                    else: break
                else:
                    G[i][j] = Edge
                    if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + Edge)): 
                        K[j] = K[i] + 1
                        dEst[j] = dEst[i] + Edge
                        piEst[j] = i
        Path = sp1SourceList(piEst, 0, nReqArcs)
        if self.output: print('finished 2')
        return(Path)

    def genAuxGraph_SP_article(self, routeOrig):
        '''
        Efficient version generating both auxiliary graphs, and determining the shortest paths between all successive auxiliary node, representing IF partitions, and final
        shortest path representing route partitions.
        '''
        depot = self.depot
        capacity = self.capacity
        spD = self.d
        sRoute = routeOrig[:]
        bestIFdistD = self.if_cost
        demandD = self.demand
        serveCostD = self.serveCost
        maxTripLength = self.maxTrip
        
        huge = 1e30000# Infinity

        n = len(sRoute)
        k_start = 0
        
        spRoute = np.zeros((n - 1))
        ifRoute = np.zeros((n))
        N_array = []
        P_array = []
        for i in range(n - 1):
            N_array.append([huge]*(n + 1))
            P_array.append([None]*(n + 1))
            N_array[i][i] = spD[depot][sRoute[i]]
            P_array[i][i] = i
            spRoute[i] = spD[sRoute[i]][sRoute[i + 1]]
            ifRoute[i] = bestIFdistD[sRoute[i]][sRoute[i + 1]]
        ifRoute[i + 1] = bestIFdistD[sRoute[n - 1]][depot]
        N_array.append([huge]*(n + 1))
        P_array.append([None]*(n + 1))
        N_array[i + 1][i + 1] = spD[depot][sRoute[i + 1]]
        P_array[i + 1][i+ 1] = i + 1        
        
        N = np.array(N_array)
        P = np.array(P_array)

        N2 = np.array([huge]*(n + 1))
        K2 = np.array([huge]*(n + 1))
        P2 = np.array([None]*(n + 1))
        N2[0] = 0
        P2[0] = 0
        K2[0] = 0
        for i in range(1, n + 1):
            load = cost = cost2 = 0
            k_0 = k_start
            for j in range(i, n + 1):
                arc_j = sRoute[j - 1]
                load = load + demandD[arc_j]
                if load > capacity: break
                a = serveCostD[arc_j] + ifRoute[j - 1]
                if i == j: cost = a
                else: cost = cost + a - ifRoute[j - 2] + spRoute[j - 2]
                cost2 = cost + serveCostD[arc_j] - a + bestIFdistD[arc_j][depot]
                if cost2 > maxTripLength: 
                    #print(i,j)
                    break
                for k in range(k_0, i):
                    Ntemp = N[k][i - 1] + cost
                    Ntemp2 = N[k][i - 1] + cost2
                    if Ntemp < N[k][j]:
                        N[k][j] = Ntemp
                        P[k][j] = i - 1
                    if Ntemp2 <= maxTripLength:
                        if ((K2[k] + 1) < K2[j]) or (((K2[k] + 1) == K2[j]) and ((N2[k] + Ntemp2) < N2[j])):
                            N2[j] = N2[k] + Ntemp2
                            P2[j] = k
                            K2[j] = K2[k] + 1
                    #else:
                    #    if (i==j):#&(k == (i - 1)): 
                    #        k_start += 1
                    if (i == j)&(j < n):
                        next_j = sRoute[j]
                        if (N[k][j] - ifRoute[j - 1] + serveCostD[next_j] + bestIFdistD[next_j][depot] + spRoute[j - 1]) > maxTripLength:
                            k_start += 1
#                     if j < n:
#                     #if (j <= 5)&(k==0):
#                         next_j = sRoute[j]
#                         print('k:%i i:%i j:%i k_0:%i k_start:%i N_temp2:%i L:%i'%(k, i, j, k_0, k_start, Ntemp2, maxTripLength))
#                         print(N[k][:6])
#                         print(P[k][:6])
#                         print(N2[:6])
#                         print(P2[:6])
#                         print(N[k][j] - ifRoute[j - 1] + bestIFdistD[arc_j][depot])
#                         print(N[k][j] + serveCostD[next_j] + bestIFdistD[next_j][depot])
#                         print(N[k][j] - ifRoute[j - 1] + serveCostD[next_j] + bestIFdistD[next_j][depot]) + spRoute[j - 1]#spD[arc_j][next_j]
                        
        Path = sp1SourceList(P2, 0, n)
#         print(N2)
#         print(Path)
#         print(P2)
        return(Path, P)

    def c_genAuxGraph1_SP(self, routeOrig):
        '''
        cython implementation of genAuxGraph1_SP
        '''
        (dEst, piEst) = c_alg_Ulusoy_part.genAuxGraph1_SP_IF(routeOrig)
        return(dEst, piEst)
    
    def c_genAuxGraph2_SP(self, dEstIFs, routeOrig):
        '''
        cython implementation of genAuxGraph2_SP
        '''
        Path = c_alg_Ulusoy_part.genAuxGraph2_SP_IF(dEstIFs, routeOrig)
        return(Path)
    
    def c_genAuxGraph_SP_article(self, routeOrig):
        '''
        cython implementation of genAuxGraph_SP_article
        '''
        (Path, piEst) = c_alg_Ulusoy_part.genAuxGraph_SP_IF_article(routeOrig)
        return(Path, piEst)
    
    def partition(self, routeOrig, Path, piEst):
        '''
        Partition original giant route using the SP through two auxiliary graphs.
        Inserts depots and the intermediate facilities, and records the vehicle
        load and route costs.
        '''
        nVehicles = len(Path) - 1
        solution_list = [None]*nVehicles
        for i in xrange(nVehicles):
            start = Path[i]
            stop = Path[i + 1]
            piEstTemp = piEst[Path[i]]
            IFPath = sp1SourceList(piEstTemp, start, stop)
            nIFs = len(IFPath) - 1
            solution_list[i] = []
            for j in range(nIFs):
                startIF = IFPath[j]
                stopIF = IFPath[j + 1]
                routeIF = routeOrig[startIF:stopIF]
                solution_list[i].append(routeIF)
        return(solution_list)
    
    def gen_solution_list(self, routeOrig):
        '''
        Generate a partitioned solution using two auxiliary graphs. One from all to 
        all optimal optimal IF partitions, and one from optimal vehicle route
        partition.
        '''
        if self.c_modules:
            (dEst, piEst) = self.c_genAuxGraph1_SP(routeOrig)
            Path = self.c_genAuxGraph2_SP(dEst, routeOrig)
        else:
            (dEst, piEst) = self.genAuxGraph1_SP(routeOrig)
            Path = self.genAuxGraph2_SP(dEst, routeOrig)
        solution_list = self.partition(routeOrig, Path, piEst)
        return(solution_list)

    def gen_solution_list_article(self, routeOrig):
        '''
        Generate a partitioned solution by simultaneously generating two auxiliary graphs. One from all to 
        all optimal optimal IF partitions, and one from optimal vehicle route
        partition.
        '''
        if self.c_modules:
            (Path, piEst) = self.c_genAuxGraph_SP_article(routeOrig)
        else:
            (Path, piEst) = self.genAuxGraph_SP_article(routeOrig)
        solution_list = self.partition(routeOrig, Path, piEst)
        return(solution_list)

    def genSolution(self, bigRoute):
        '''
        Generate a partitioned solution using standard approach
        '''
        solutionIncomplete = self.gen_solution_list(bigRoute)
        if self.output: print('')
        if self.output: print(solutionIncomplete)     
        solution = build_solution.build_CLARPIF_dict(solutionIncomplete, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        #print(solution)
        return(solution)

    def genSolution_article(self, bigRoute):
        '''
        Generate a partitioned solution using efficient article approach
        '''
        solutionIncomplete = self.gen_solution_list_article(bigRoute)
        if self.output: print('')
        if self.output: print(solutionIncomplete)     
        solution = build_solution.build_CLARPIF_dict(solutionIncomplete, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        return(solution)


class UlusoysIFs_efficient(object):
    '''
    Optimally partition a giant route by including trips to intermediate 
    facilities and by partitioning trips for different vehicles. Only works 
    if there is a maximum vehicle trip length and when there is one 
    depot. First efficient version, using IFs calculated afterwards.
    '''  
    
    def __init__(self, info):
        self.info = info
        self.capacity = info.capacity
        self.maxTrip = info.maxTrip
        self.dumpCost = info.dumpCost
        self.reqArcs = info.reqArcListActual
        self.depot = info.depotnewkey
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.if_cost = info.if_cost_np
        self.if_arc = info.if_arc_np
        self.c_modules = True
        self.opt_ifs = False
        
        self.stats = 0
        self.adjust_estimate = 1
        self.adjust_up = 0
        
    def gen_route_stats(self, route):
        self.stats = py_solution_stats.c_route_IF_cost_stats(route, 
                                                            self.d, 
                                                            self.if_cost)

    def if_cost_function(self, nDumps):
        route_average = self.stats[0]*(1 - self.adjust_estimate) + self.adjust_up
        temp_cost = int(nDumps*route_average)
        return(temp_cost)
        
    def estimate_if_cost(self, load):
        nDumps = int(ceil(float(load)/float(self.capacity)) - 1)
        return(self.if_cost_function(nDumps))
    
    def genAuxGraphSP(self, routeOrig):
        '''
        Generates the auxiliary graph and determines the shortest path through
        the graph, representing optimal route partition. Estimate of IF costs is used to 
        to determine feasible routes based on maxtrip length. Does not compute IF placements.
        '''
        
        depot = self.depot
        spD = self.d
        demand = self.demand
        serveCost = self.serveCost
        if_cost  = self.if_cost
        maxTripLength = self.maxTrip
        
        route = routeOrig[:]
        
        spRoute = [0]
        for i in xrange(1, len(route)): 
            # Determines the shortest path length between two arcs connected 
            # in original route.
            spRoute.append(spD[route[i - 1]][route[i]])
                
        sRoute = route[:]
        huge = 1e30000# Infinity
        dEst = {}
        piEst = {}

        for i in xrange(len(sRoute) + 1):
            dEst[i] = huge
            piEst[i] = None
        dEst[0] = 0
        
        for i in range(len(sRoute)):
            load = 0
            serviceC = 0
            spCosts = 0
            for j in range(i + 1, len(sRoute) + 1):
                load = load + demand[sRoute[j - 1]]
                if_cost_est = self.estimate_if_cost(load)
                if (j - i) > 1:
                    spCosts = spCosts + spD[sRoute[j - 2]][sRoute[j - 1]]
                serviceC = serviceC + serveCost[sRoute[j - 1]]
                dDedge = spD[depot][sRoute[i]] + serviceC + spCosts + \
                         if_cost[sRoute[j - 1]][depot] + if_cost_est
                if dDedge > maxTripLength: 
                    if j == i + 1:
                        if dEst[j] > dEst[i] + dDedge:
                            dEst[j] = dEst[i] + dDedge
                            piEst[j] = i
                    else: break
                else:
                    if dEst[j] > dEst[i] + dDedge:
                        dEst[j] = dEst[i] + dDedge
                        piEst[j] = i
        Path = sp1SourceList(piEst, 0, len(sRoute))
        return(dEst[len(sRoute)], Path)

    def genAuxGraphSP_Est_Advance(self, routeOrig, est = True):
        '''
        Generates the auxiliary graph and determines the shortest path through
        the graph - the optimal partition. Original route should not contain the 
        depot visits. Used to partition route for the CLARPIF. IF visits are accounted, 
        when partitioning the routes, but not optimally.
        '''
        
        d = self.d
        depot = self.depot
        demand = self.demand
        capacity = self.capacity
        if_cost = self.if_cost
        service = self.serveCost
        maxTrip = self.maxTrip
                
        sRoute = {}
        huge = 1e30000# Infinity
        dEst = {}
        piEst = {}
        K = {}
        
        for i in xrange(len(routeOrig)):
            sRoute[i] = routeOrig[i]
        
        for i in xrange(len(sRoute) + 1):
            dEst[i] = huge
            piEst[i] = None
            K[i] = huge
        dEst[0] = 0
        K[0] = 0
        if_visits = {}
        if_visits_opt = {}
        
        for i in range(len(sRoute)):
            if_visits[i] = []
            load = 0
            serviceC = 0
            spCosts = 0
            depot_c = d[depot][sRoute[i]]
            for j in range(i + 1, len(sRoute) + 1):
                load = load + demand[sRoute[j - 1]]
                if load > capacity:
                    if_cost_est = if_cost[sRoute[j - 2]][sRoute[j - 1]]
                    load = demand[sRoute[j - 1]]
                    if_visits[i].append(j - 1)
                else:
                    #print(j-2,j-1)
                    if j == 1: if_cost_est = 0
                    else: if_cost_est = d[sRoute[j - 2]][sRoute[j - 1]]
                if (j - i) > 1:
                    spCosts = spCosts + if_cost_est
                serviceC = serviceC + service[sRoute[j - 1]]
                dDedge = depot_c + serviceC + spCosts + if_cost[sRoute[j - 1]][depot]
                if dDedge > maxTrip: 
                    if j == i + 1:
                        if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + dDedge)):
                            dEst[j] = dEst[i] + dDedge
                            piEst[j] = i
                            K[j] = K[i] + 1
                            if_visits_opt[j] = if_visits[i][:] 
                    else: break
                else:
                    if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + dDedge)):
                        dEst[j] = dEst[i] + dDedge
                        piEst[j] = i
                        K[j] = K[i] + 1
                        if_visits_opt[j] = if_visits[i][:] 
        
        Path = sp1SourceList(piEst, 0, len(sRoute))
        return(dEst[len(sRoute)], Path, if_visits, if_visits_opt)

    def genAuxGraphSP_Est_Supper_Advance(self, routeOrig):
        '''
        Generates the auxiliary graph and determines the shortest path through
        the graph - the optimal partition. Original route should not contain the 
        depot visits. Used to partition route for the CLARPIF. IF visits are accounted, 
        when partitioning the routes, but not optimally.
        '''
        
        d = self.d
        depot = self.depot
        demand = self.demand
        capacity = self.capacity
        if_cost = self.if_cost
        service = self.serveCost
        maxTrip = self.maxTrip
                
        if_visits = {0 : []}
        routes_visits = [0]
        
        n = len(routeOrig)
        nRoutes = 0
        load = 0
        cost = d[depot][routeOrig[0]]
        for i in range(n):
            load += demand[routeOrig[i]]
            if load > capacity:     
                cost_temp = cost + if_cost[routeOrig[i - 1]][routeOrig[i]] + service[routeOrig[i]]
                if (cost_temp + if_cost[routeOrig[i]][depot]) > maxTrip:
                    routes_visits.append(i)
                    nRoutes += 1
                    if_visits[nRoutes] = []
                    cost = d[depot][routeOrig[i]] + service[routeOrig[i]]
                    load = demand[routeOrig[i]]
                else:
                    load = demand[routeOrig[i]]
                    if_visits[nRoutes].append(i)
                    cost = cost_temp
            else:
                cost_temp = cost + d[routeOrig[i - 1]][routeOrig[i]] + service[routeOrig[i]]
                if (cost_temp + if_cost[routeOrig[i]][depot]) > maxTrip:
                    routes_visits.append(i)
                    nRoutes += 1
                    if_visits[nRoutes] = []
                    cost = d[depot][routeOrig[i]] + service[routeOrig[i]]
                    load = demand[routeOrig[i]]
                else:
                    cost = cost_temp
        routes_visits.append(n)
        return(routes_visits, if_visits)

    def c_genAuxGraphSP_old(self, routeOrig):
        '''
        Old cython version is not used anymore.
        '''
#        (dEst_end, Path) = c_alg_Ulusoy_part.genAuxGraphSP_Est(routeOrig,
#                                                                self.stats,
#                                                                self.adjust_estimate,
#                                                                self.adjust_up)
        (dEst_end, Path) = c_alg_Ulusoy_part.genAuxGraphSP_Est_Advance(routeOrig)
        return(dEst_end, Path) 

    def c_genAuxGraphSP(self, routeOrig, min_k = True):
        '''
        Advanced cython version used anymore. Unclear what the difference is.
        '''
        (dEst_end, Path, if_visits, if_visits_opt) = c_alg_Ulusoy_part.genAuxGraphSP_Est_Advance(routeOrig, min_k)
        return(dEst_end, Path, if_visits, if_visits_opt) 

    def c_genAuxGraphSP_Supper_Advance(self, routeOrig):
        '''
        Advanced cython version used anymore. Unclear what the difference is.
        '''
        (Path, if_visits) = c_alg_Ulusoy_part.genAuxGraphSP_Est_Supper_Advance(routeOrig)
        return(Path, if_visits) 

    def partition_pure_V0(self, routeOrig, piEst, Path):
        '''
        Partition original giant route using the SP through two auxiliary graphs.
        Inserts depots and the intermediate facilities, and records the vehicle
        load and route costs.
        '''
        nVehicles = len(Path) - 1
        solution_list = [None]*nVehicles
        for i in xrange(nVehicles):
            start = Path[i]
            stop = Path[i + 1]
            IFPath = piEst[start]
            print(start, stop, IFPath)
            solution_list[i] = []
            s = start
            for e in IFPath:
                if e >= stop: break 
                routeIF = routeOrig[s:e]
                solution_list[i].append(routeIF)
                s = e
            routeIF = routeOrig[s:stop]
            solution_list[i].append(routeIF)
        return(solution_list)

    def partition_pure_V1(self, routeOrig, piEst, Path):
        '''
        Partition original giant route using the SP through two auxiliary graphs.
        Inserts depots and the intermediate facilities, and records the vehicle
        load and route costs.
        '''
        nVehicles = len(Path) - 1
        solution_list = [None]*nVehicles
        for i in xrange(nVehicles):
            start = Path[i]
            stop = Path[i + 1]
            IFPath = piEst[i]
            solution_list[i] = []
            s = start
            for e in IFPath:
                routeIF = routeOrig[s:e]
                solution_list[i].append(routeIF)
                s = e
            routeIF = routeOrig[s:stop]
            solution_list[i].append(routeIF)
        return(solution_list)

    def partition_pure(self, routeOrig, piEst, Path):
        '''
        Partition original giant route using the SP through two auxiliary graphs.
        Inserts depots and the intermediate facilities, and records the vehicle
        load and route costs.
        '''
        nVehicles = len(Path) - 1
        solution_list = [None]*nVehicles
        for i in xrange(nVehicles):
            start = Path[i]
            stop = Path[i + 1]
            IFPath = piEst[stop]
            solution_list[i] = []
            s = start
            for e in IFPath:
                routeIF = routeOrig[s:e]
                solution_list[i].append(routeIF)
                s = e
            routeIF = routeOrig[s:stop]
            solution_list[i].append(routeIF)
        return(solution_list)

    def gen_solution_list(self, bigRoute, min_k = True):
        '''
        Generate a partitioned solution
        '''        
        #self.gen_route_stats(bigRoute)
        if self.c_modules: (finalDistance, Path, if_visits, if_visits_opt) = self.c_genAuxGraphSP(bigRoute, min_k)       
        else: (finalDistance, Path, if_visits, if_visits_opt) = self.genAuxGraphSP_Est_Advance(bigRoute)
        solutionlist = spAuxToSolution(finalDistance, Path, bigRoute)
        return(solutionlist, if_visits, if_visits_opt, Path)

    def gen_solution_list_efficient(self, bigRoute):
        '''
        Generate a partitioned solution
        '''        
        if self.c_modules: (Path, if_visits) = self.c_genAuxGraphSP_Supper_Advance(bigRoute)       
        else: (Path, if_visits) = self.genAuxGraphSP_Est_Supper_Advance(bigRoute)
        solutionlist = self.partition_pure_V1(bigRoute, if_visits, Path)
        return(solutionlist)

    def gen_solution_list_ifs_old(self, solutionlist):
        '''
        Routes are partitioned, and then each is partitioned into subroutes (old version).
        '''
        UL1IF = UlusoysIFs_1vehicle(self.info)
        complete_route = []
        feasible = True
        for route in solutionlist:
            route_with_ifs_info = UL1IF.gen_solution_list(route)
            if route_with_ifs_info[-1] > self.maxTrip: 
                feasible = False
#                if route_with_ifs_info[-1] - self.maxTrip > self.adjust_up: 
#                    self.adjust_up = route_with_ifs_info[-1] - self.maxTrip
#                else:
#                    self.adjust_up += route_with_ifs_info[-1] - self.maxTrip
                print('Not feasible: %i    Adjust %i' %(route_with_ifs_info[-1], self.adjust_up))
                self.adjust_estimate -= 0.1
                break
            else:
                complete_route.append(route_with_ifs_info[0])
        return(complete_route, feasible)

    def gen_solution_list_ifs_optimal(self, solutionlist):
        '''
        Routes are partitioned, and then each is partitioned into subroutes.
        '''
        UL1IF = UlusoysIFs_1vehicle(self.info)
        complete_route = []
        for route in solutionlist:
            route_with_ifs_info = UL1IF.gen_solution_list_article(route)
            complete_route.append(route_with_ifs_info[0])
        return(complete_route)

    def gen_solution(self, bigRoute):
        '''
        Generate a partitioned solution
        '''
        (solutionIncomplete, if_visits, if_visits_opt, Path) = self.gen_solution_list(bigRoute)
        if self.opt_ifs: solution_with_ifs = self.gen_solution_list_ifs_optimal(solutionIncomplete)
        else: 
            solution_with_ifs = self.partition_pure(bigRoute, if_visits_opt, Path)
            #solution_with_ifs = self.partition_pure_V0(bigRoute, if_visits, Path)
        solution = build_solution.build_CLARPIF_dict(solution_with_ifs, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        return(solution)

    def gen_solution_efficient(self, bigRoute, min_k = True):
        '''
        Generate a partitioned solution
        '''
        (solutionIncomplete, if_visits, if_visits_opt, Path) = self.gen_solution_list(bigRoute)
        solution_with_ifs = self.gen_solution_list_ifs_optimal(solutionIncomplete)
        solution = build_solution.build_CLARPIF_dict(solution_with_ifs, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        return(solution)

    def gen_solution_super_efficient(self, bigRoute):
        '''
        Generate a partitioned solution
        '''
        solution_with_ifs = self.gen_solution_list_efficient(bigRoute)
        solution = build_solution.build_CLARPIF_dict(solution_with_ifs, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        return(solution)

class UlusoysIFs_efficient2(object):
    '''
    Optimally partition a giant route by including trips to intermediate 
    facilities and by partitioning trips for different vehicles. Only works 
    if there is a maximum vehicle trip length and when there is one 
    depot. Second efficient version.
    '''  
    
    def __init__(self, info):
        self.Part_1_route = UlusoysIFs_efficient(info)
        self.info = info
        self.capacity = info.capacity
        self.maxTrip = info.maxTrip
        self.dumpCost = info.dumpCost
        self.reqArcs = info.reqArcListActual
        self.depot = info.depotnewkey
        self.invArcList = info.reqInvArcList
        self.serveCost = info.serveCostL
        self.demand = info.demandL
        self.d = info.d
        self.if_cost = info.if_cost_np
        self.if_arc = info.if_arc_np
        self.c_modules = True
        self.opt_ifs = False
        
        self.stats = 0
        self.adjust_estimate = 0.9
        self.adjust_up = 0
    
    def genAuxGraphSP(self, routeOrig):
        '''
        Generates the auxiliary graph and determines the shortest path through
        the graph, representing optimal route partition. Once vehicle load is exceeded, Ulusoy-IF for
        one vehicle is used to determine optimal IF placements. The cost of the partition is used to
        check for vehicle capacity. Not very efficient as optimal IF visits are recalculated.
        '''
        depot = self.depot
        d = self.d
        demand = self.demand
        service = self.serveCost
        if_cost  = self.if_cost
        maxTrip = self.maxTrip
                
        route = routeOrig[:]
        
        spRoute = [0]
        for i in xrange(1, len(route)): 
            # Determines the shortest path length between two arcs connected 
            # in original route.
            spRoute.append(d[route[i - 1]][route[i]])
                
        sRoute = route[:]
        huge = 1e30000# Infinity
        dEst = {}
        piEst = {}
        K = {}
        if_visits = {}
        if_visits_opt = {}
        
        for i in xrange(len(sRoute) + 1):
            dEst[i] = huge
            piEst[i] = None
            K[i] = huge
        dEst[0] = 0
        K[0] = 0
        sp_if_cals = 0
        sp_if_cals_temp = []
        for i in range(len(sRoute)):
            load = 0
            serviceC = 0
            spCosts = 0
            if_visits[i] = []
            for j in range(i + 1, len(sRoute) + 1):
                load = load + demand[sRoute[j - 1]]
                serviceC = serviceC + service[sRoute[j - 1]]
                load_cost = (ceil(load/self.capacity) - 1)*self.dumpCost
                dDedge_temp = d[depot][sRoute[i]] + serviceC + if_cost[sRoute[j - 1]][depot] + spCosts + d[sRoute[j - 2]][sRoute[j - 1]] + load_cost
                load_exc = False
                if (load > self.capacity) and (dDedge_temp >= self.adjust_estimate*maxTrip):
                    #print('calc IFs', load)
                    sp_if_cals += 1
                    (if_cost_est, load, path) = c_alg_Ulusoy_part.genAux1IFGraphSP2(sRoute[i:j]) 
                    spCosts = if_cost_est
                    if_visits[i] = path[:]
                    load_exc = True
                else:
                    if_cost_est = d[sRoute[j - 2]][sRoute[j - 1]]
                #if (j - i) > 1:
                    spCosts = spCosts + if_cost_est
                dDedge = d[depot][sRoute[i]] + serviceC + spCosts + if_cost[sRoute[j - 1]][depot]
                if load_exc: sp_if_cals_temp.append([i, j, if_cost_est, dDedge, dDedge_temp, dDedge_temp/(dDedge)])
                if dDedge > maxTrip: 
                    if j == i + 1:
                        if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + dDedge)):
                            dEst[j] = dEst[i] + dDedge
                            piEst[j] = i
                            K[j] = K[i] + 1
                            if_visits_opt[j] = if_visits[i][:]
                    else: break
                else:
                    if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + dDedge)):
                        dEst[j] = dEst[i] + dDedge
                        piEst[j] = i
                        K[j] = K[i] + 1
                        if_visits_opt[j] = if_visits[i][1:-1]
                        
        Path = sp1SourceList(piEst, 0, len(sRoute))
        print('')
        print('-------------------- sp_if_cals = %i ---------------------'%sp_if_cals)
        #print(sp_if_cals_temp)
        print('')
        return(dEst[len(sRoute)], Path, if_visits_opt)

    def c_genAuxGraphSP(self, routeOrig):
        '''
        cython implementation for genAuxGraphSP.
        '''
        (dEst_end, Path, if_visits_opt) = c_alg_Ulusoy_part.genAuxGraphSP_Est_Advance2(routeOrig)
        return(dEst_end, Path, if_visits_opt) 

    def gen_solution_list(self, bigRoute):
        '''
        Generate a partitioned solution list. Does not contain IFs.
        '''        
        if self.c_modules: (finalDistance, Path, if_visits_opt) = self.c_genAuxGraphSP(bigRoute)       
        else: (finalDistance, Path, if_visits_opt) = self.genAuxGraphSP(bigRoute)
        solutionlist = spAuxToSolution(finalDistance, Path, bigRoute)
        return(solutionlist, Path, if_visits_opt)
    
    def gen_solution_list_ifs_opt(self, solutionlist):
        '''
        Generate route with IF visits. Each route is (again) optimally partitioned. 
        '''        
        UL1IF = UlusoysIFs_1vehicle(self.info)
        complete_route = []
        for route in solutionlist:
            route_with_ifs_info = UL1IF.gen_solution_list_article(route)
            complete_route.append(route_with_ifs_info[0])
        return(complete_route)

    def gen_solution_list_ifs_heuristic(self, routeOrig, Path, piEst):
        '''
        Generate route with IF visits. Each route is (again) optimally partitioned. 
        '''        
        nVehicles = len(Path) - 1
        solution_list = [None]*nVehicles
        for i in xrange(nVehicles):
            start = Path[i]
            stop = Path[i + 1]
            IFPath = [k + start for k in piEst[stop]]
            solution_list[i] = []
            s = start
            for e in IFPath:
                routeIF = routeOrig[s:e]
                solution_list[i].append(routeIF)
                s = e
            routeIF = routeOrig[s:stop]
            solution_list[i].append(routeIF)
        return(solution_list)

    def gen_solution(self, bigRoute):
        '''
        Generate a partitioned solution by first determining route partitions, and secondly by 
        determining optimal IF partitions. Not very efficient!
        '''
        (solutionIncomplete, Path, if_visits_opt) = self.gen_solution_list(bigRoute)
        if self.opt_ifs: 
            solution_with_ifs = self.gen_solution_list_ifs_opt(solutionIncomplete)
        else: 
            solution_with_ifs = self.gen_solution_list_ifs_heuristic(bigRoute, Path, if_visits_opt)
            #solution_with_ifs = self.gen_solution_list_ifs_opt(solutionIncomplete)
        solution = build_solution.build_CLARPIF_dict(solution_with_ifs, 
                                                     self.if_arc, 
                                                     self.depot, 
                                                     self.d, 
                                                     self.serveCost, 
                                                     self.dumpCost, 
                                                     self.demand)
        return(solution)

if __name__ == "__main__":
    print('Use profile module')
    

    

