'''
Created on 12 Oct 2011

@author: elias
'''
import numpy as np
from alg_shortest_paths import huge
#cimport numpy as np

cimport libc.stdlib

from libc.stdlib cimport realloc, malloc, free 
#from libcpp.vector cimport vector
from math import ceil

huge = 1e30000# Infinity

from copy import deepcopy
cdef int **d, nArcs, depot, *demand, capacity, dumpCost, **if_cost, maxTrip, *service

def set_input(info, full = False):
    
    d_old = info.d
    depot_old = info.depotnewkey
    inv_list_old = info.reqInvArcList
    demand_old = info.demandL
    capacity_old = info.capacity
    dumpCostOld = info.dumpCost
    if_cost_old = info.if_cost_np
    maxTrip_old = info.maxTrip
    service_old = info.serveCostL
    
    global d, nArcs, depot, inv_list, demand, capacity, dumpCost, if_cost, maxTrip, service
    
    nArcs = len(d_old)
    d = <int **>malloc(nArcs * sizeof(int *))
    if_cost = <int **>malloc(nArcs * sizeof(int *))
    inv_list = inv_list_old #< int *>malloc(nArcs * sizeof(int *))
    demand = < int *>malloc(nArcs * sizeof(int *)) 
    service = < int *>malloc(nArcs * sizeof(int *))
    depot = depot_old
    capacity = capacity_old
    dumpCost = dumpCostOld
    if full: maxTrip = maxTrip_old
    for i from 0 <= i < nArcs:
        d[i] = <int *>malloc(nArcs * sizeof(int *))
        if_cost[i] = <int *>malloc(nArcs * sizeof(int *))
        demand[i] = demand_old[i]
        service[i] = service_old[i]
        
    for i from 0 <= i < nArcs:
        for j from 0 <= j < nArcs:
            d[i][j] = d_old[i][j]
            if full: if_cost[i][j] = if_cost_old[i][j]     

def free_input(full):
    for i from 0 <= i < nArcs:
        free(d[i])
        free(if_cost[i])
    free(d)
    free(if_cost)
    free(demand)
    free(service)

def route_IF_cost_stats(route, d):
    '''
    returns estimate for IF visit costs, based on stats of IF visits between all arcs.
    '''
    costs = np.zeros(len(route)-1, int)
    for i in range(len(route)-1):
        costs[i] = if_cost[route[i]][route[i+1]] - d[route[i]][route[i+1]]
    average = np.average(costs)
    max_s = np.max(costs)
    min_s = np.min(costs)
    std = np.std(costs)
    return(average, max_s, min_s, std)

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

def gen_spRoute(route):
    spRoute = [0]
    for i in range(1, len(route)): 
    # Determines the shortest path length between two arcs connected 
    # in original route.
        spRoute.append(d[route[i - 1]][route[i]])    
    return(spRoute)

def Est(nRoutes):
    dEst = {}
    piEst = {}
    K = {}
    for i in xrange(nRoutes+1):
        dEst[i] = huge
        piEst[i] = None
        K[i] = huge
    dEst[0] = 0
    K[0] = 0
    return(dEst, piEst, K)
    
def genAuxGraphSP(routeOrig, min_k = True):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CARP, thus no IFs.
    '''
    route = routeOrig[:]
    
    spRoute = gen_spRoute(route)
            
    sRoute = route[:]

    L = {}
    G = {}

    (dEst, piEst, K) = Est(len(sRoute))
    
    for i in xrange(len(sRoute)):
        L[i] = {}
        G[i] = {}
        load = 0
        serviceC = 0
        spCosts = 0
        for j in xrange(i + 1, len(sRoute) + 1):
            load = load + demand[sRoute[j - 1]]
            if load > capacity: break
            else:
                if (j - i) > 1:
                    spCosts = spCosts + d[sRoute[j - 2]][sRoute[j - 1]]
                serviceC = serviceC + service[sRoute[j - 1]]
                dDedge = d[depot][sRoute[i]] + serviceC + spCosts + \
                         d[sRoute[j - 1]][depot] + dumpCost 
                L[i][j] = load
                G[i][j] = dDedge
                if min_k:
                    if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + dDedge)):
                        dEst[j] = dEst[i] + dDedge
                        piEst[j] = i
                        K[j] = K[i] + 1
                else:
                    if (dEst[j] > dEst[i] + dDedge) or ((dEst[j] == dEst[i] + dDedge) and (K[i] + 1) < K[j]):
                        dEst[j] = dEst[i] + dDedge
                        piEst[j] = i
                        K[j] = K[i] + 1    
    Path = sp1SourceList(piEst, 0, len(sRoute))
    return(dEst[len(sRoute)], Path, G, L)

def genAux1IFGraphSP(routeOrig):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CARPIF, thus IFs for one vehicle
    without max trip length. Both load and service cost per partition is returned.
    '''
    route = routeOrig[:]
    spRoute = gen_spRoute(route)
    sRoute = route[:]

    L = {}
    G = {}

    (dEst, piEst, K) = Est(len(sRoute))

    for i in range(len(sRoute)):
        L[i] = {}
        G[i] = {}
        load = 0
        serviceC = 0
        for j in range(i + 1, len(sRoute) + 1):
            load = load + demand[sRoute[j - 1]]
            if load > capacity: break
            else:
                serviceC = serviceC + service[sRoute[j - 1]]
                if j == len(sRoute): 
                    bestIFdist = if_cost[sRoute[j - 1]][depot]
                else:
                    bestIFdist = if_cost[sRoute[j - 1]][sRoute[j]]
                if i == 0:
                    dDedge = d[depot][sRoute[i]] + bestIFdist + serviceC + sum(spRoute[i + 1:j]) # + dumpCost
                else:
                    dDedge = bestIFdist + serviceC + sum(spRoute[i + 1:j]) # + dumpCost 
                L[i][j] = load
                G[i][j] = dDedge
                if dEst[j] > dEst[i] + dDedge:
                    dEst[j] = dEst[i] + dDedge
                    piEst[j] = i 
    
    Path = sp1SourceList(piEst, 0, len(sRoute))
    return(dEst[len(sRoute)], Path, G, L)


def genAux1IFGraphSP2(routeOrig):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CARPIF, thus IFs for one vehicle
    without max trip length. Only load for last partition is returned.
    '''
    route = routeOrig[:]
    spRoute = gen_spRoute(route)
    sRoute = route[:]

    L = {}

    (dEst, piEst, K) = Est(len(sRoute))
    
    for i in range(len(sRoute)):
        L[i] = {}
        load = 0
        for j in range(i + 1, len(sRoute) + 1):
            load = load + demand[sRoute[j - 1]]
            if load > capacity: break
            else:
                if j == len(sRoute): 
                    bestIFdist = 0
                else:
                    bestIFdist = if_cost[sRoute[j - 1]][sRoute[j]]
                dDedge = bestIFdist + sum(spRoute[i + 1:j])
                L[i][j] = load
                if dEst[j] > dEst[i] + dDedge:
                    dEst[j] = dEst[i] + dDedge
                    piEst[j] = i 
    
    Path = sp1SourceList(piEst, 0, len(sRoute))
    return(dEst[len(sRoute)], L[Path[-2]][Path[-1]], Path)

def genAuxGraphSP_efficient(routeOrig):
    '''
    Different implementation based on the work of Lancomme et all, and on PhD by Elias Willemse.
    Python implementation is more efficient, but not the cython implementation.
    '''
    Path = [0]
    n = len(routeOrig)
    load = 0
    for i in range(n):
        arc_i = routeOrig[i]
        load += demand[arc_i]
        if load > capacity:
            load = 0 
            Path.append(i)
            load = demand[arc_i]
    if Path[-1] <> (n): Path.append(n)
    return(0, Path, [], [])

def genAuxGraphSP_article(routeOrig):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CARPIF, thus IFs for one vehicle
    without max trip length. First version, with extensive initializations.
    ''' 
    n = len(routeOrig)
    huge = 1e30000# Infinity
    sRoute = routeOrig[:]

    cdef double *cN 
    cdef int *cRoute, *spRoute, *ifRoute
    
    cN = < double *>malloc((n + 1) * sizeof(double *)) 
    cRoute = < int *>malloc(n * sizeof(int *)) 
    spRoute = < int *>malloc((n - 1) * sizeof(int *)) 
    ifRoute = < int *>malloc(n * sizeof(int *)) 
    
    for i in xrange(n):
        cRoute[i] = routeOrig[i]
    
    P = [None]*(n + 1)
    P[0] = 0    

    for i in xrange(n + 1):
        cN[i] = huge
    cN[0] = d[depot][sRoute[0]]
        
    for i in xrange(n - 1):
        spRoute[i] = d[sRoute[i]][sRoute[i + 1]]
        ifRoute[i] = if_cost[sRoute[i]][sRoute[i + 1]]
    ifRoute[i + 1] = if_cost[sRoute[n - 1]][depot]

    for i in xrange(n):
        load = cost = 0
        for j in xrange(i, n):
            arc_j = cRoute[j]
            load = load + demand[arc_j]
            if load > capacity: break
            a = service[arc_j] + ifRoute[j]
            if i == j: cost = a
            else: cost = cost + a - ifRoute[j - 1] + spRoute[j - 1]
            dTemp = cN[i] + cost 
            if dTemp < cN[j + 1]:
                cN[j + 1] = dTemp
                P[j + 1] = i
    
    Path = sp1SourceList(P, 0, n)
    G, L = None, None

    fCost = int(cN[n])
    
    free(cN)
    free(cRoute)
    free(spRoute)
    free(ifRoute)
 
    return(fCost, Path, G, L)

def genAuxGraphSP_article2(routeOrig):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CARPIF, thus IFs for one vehicle
    without max trip length. Second version, without extensive initializations.
    ''' 
    sRoute = routeOrig[:]
    
    huge = 1e30000# Infinity

    n = len(sRoute)

    N = np.array([huge]*(n + 1))
    P = np.array([None]*(n + 1))
    N[0] = d[depot][sRoute[0]]
    P[0] = 0
    
    for i in range(n):
        load = cost = 0
        for j in range(i, n):
            arc_j = sRoute[j]
            load = load + demand[arc_j]
            if load > capacity: break
            if j < (n - 1): a = service[arc_j] + if_cost[sRoute[j]][sRoute[j + 1]]
            else:  a = service[arc_j] + if_cost[sRoute[j]][depot]
            if i == j: cost = a
            else: cost = cost + a - if_cost[sRoute[j - 1]][sRoute[j]] + d[sRoute[j - 1]][sRoute[j]]
            dTemp = N[i] + cost 
            if dTemp < N[j + 1]:
                N[j + 1] = dTemp
                P[j + 1] = i
    
    Path = sp1SourceList(P, 0, n)
    G, L = None, None
    return(N[-1], Path, G, L)


def genAuxGraph1_SP_IF(routeOrig, output = False):
    '''
    Generates the first auxiliary graph, and determined the shortest paths between all successive auxiliary node. 
    Original route should not contain the depot visits. First step in solving CLARPIF.
    '''
    if output: print('')
    if output: print('Gen Aux graph 1')
    
    route = routeOrig[:]
    
    spRoute = [0]
    serviceRoute = []
    loadRoute = []
    
    for i in xrange(1, len(route)): # Determines the shortest path length between two arcs connected in original route.
        spRoute.append(d[route[i - 1]][route[i]])
        serviceRoute.append(service[route[i - 1]])
        loadRoute.append(demand[route[i - 1]])
        
    serviceRoute.append(service[route[i]])
    loadRoute.append(demand[route[i]])
            
    sRoute = route[:]     
           
    huge = 1e30000# Infinity
    dEst = {}
    piEst = {}
    
    nReqArcs = len(sRoute)
    #auxNodes = range(nReqArcs + 1)
    
    if output: print('Initialise 1')
    for s in xrange(nReqArcs + 1):
        dEst[s] = {}
        piEst[s] = {}
        for v in xrange(s, nReqArcs + 1):
            dEst[s][v] = huge
            piEst[s][v] = None
        dEst[s][s] = 0
    
    startQ = 0
    if output: print('gen 1')
    for i in xrange(nReqArcs):
        if output: print('arc %d of %d' %(i,nReqArcs))
        load = 0
        serv = 0
        for j in xrange(i + 1, nReqArcs + 1):
            load = load + demand[sRoute[j - 1]]
            serv = serv + service[sRoute[j - 1]]
 
            if load > capacity: break
            else:
                dDedge = 0
                if j == len(sRoute): 
                    bestIFdist = if_cost[sRoute[j - 1]][depot]
                else:
                    bestIFdist = if_cost[sRoute[j - 1]][sRoute[j]]
                for q in range(startQ, i + 1):
                    dDedge = bestIFdist + sum(serviceRoute[i:j]) + sum(spRoute[i + 1:j]) # + dumpCost 
                    if dEst[q][j] > dEst[q][i] + dDedge:
                        dEst[q][j] = dEst[q][i] + dDedge
                        piEst[q][j] = i
    if output: print('Finished 1')
    return(dEst, piEst)


def genAuxGraph2_SP_IF(dEstIFs, routeOrig, output = False):
    '''
    Calculates the optimal vehicle partition using the optimal IF partition from genAuxGraph1_SP_IF.
    Second step in solving CLARPIF.
    '''
    if output: print('')
    if output: print('Gen Aux graph 2')
    huge = 1e30000# Infinity
    
    route = routeOrig[:]
    
    dEst = {}
    piEst = {}
    G = {}
    K = {}

    sRoute = route[:]
    nReqArcs = len(sRoute)       
    if output: print('Initialise 2')
    for i in xrange(nReqArcs + 1):
        dEst[i] = huge
        piEst[i] = None
        K[i] = huge
    K[0] = 0
    dEst[0] = 0
    if output: print('gen 2')
    for i in xrange(len(sRoute)):
        G[i] = {}
        serviceC = 0
        for j in range(i + 1, len(sRoute) + 1):
            if j == len(sRoute):
                Edge = d[depot][sRoute[i]] + dEstIFs[i][j]
            else:
                Edge = d[depot][sRoute[i]] + dEstIFs[i][j] - if_cost[sRoute[j - 1]][sRoute[j]] + if_cost[sRoute[j - 1]][depot]
            
            serviceC = serviceC + Edge
            
            if Edge > maxTrip: 
                if j == i + 1:
                    G[i][j] = Edge
                    if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + Edge)):
                        dEst[j] = dEst[i] + Edge
                        piEst[j] = i
                        K[j] = K[i] + 1
                else: break
            else:
                G[i][j] = Edge
                if ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + Edge)):
                    dEst[j] = dEst[i] + Edge
                    piEst[j] = i
                    K[j] = K[i] + 1
    Path = sp1SourceList(piEst, 0, nReqArcs)
    if output: print('finished 2')
    return(Path)

def genAuxGraph_SP_IF_article(routeOrig, orig = False):
    '''
    Efficient version generating both auxiliary graphs, and determining the shortest paths between all successive auxiliary node, representing IF partitions, and final
    shortest path representing route partitions. Combined steps for solving the CLARPIF.
    '''

    n = len(routeOrig)
    huge = 1e30000# Infinity

    spD = d
    bestIFdistD = if_cost
    demandD = demand
    serveCostD = service
    maxTripLength = maxTrip
    
    k_start = 0

    cdef double *N2, *K2, **N 
    cdef int *sRoute, *spRoute, *ifRoute

    N = <double **>malloc(n * sizeof(double *))     
    N2 = < double *>malloc((n + 1) * sizeof(double *))
    K2 = < double *>malloc((n + 1) * sizeof(double *)) 
    sRoute = < int *>malloc(n * sizeof(int *)) 
    spRoute = < int *>malloc((n - 1) * sizeof(int *)) 
    ifRoute = < int *>malloc(n * sizeof(int *)) 
#     
    for i in xrange(n):
        sRoute[i] = routeOrig[i]
        N[i] = <double *>malloc((n + 1) * sizeof(double *))  
# 
    for i in xrange(n + 1):
        N2[i] = huge
        K2[i] = huge
    N2[0] = 0
    K2[0] = 0

    P = []
    
    for i in range(n - 1):
        for j in range(n + 1):
            N[i][j] = huge
        P.append([None]*(n + 1))
        N[i][i] = spD[depot][sRoute[i]]
        P[i][i] = i
        spRoute[i] = spD[sRoute[i]][sRoute[i + 1]]
        ifRoute[i] = bestIFdistD[sRoute[i]][sRoute[i + 1]]
        
    ifRoute[i + 1] = bestIFdistD[sRoute[n - 1]][depot]
    
    for j in range(n + 1): N[i + 1][j] = huge
    P.append([None]*(n + 1))
    N[i + 1][i + 1] = spD[depot][sRoute[i + 1]]
    P[i + 1][i + 1] = i + 1        
  
    P2 = [None]*(n + 1)
    P2[0] = 0
    
    
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
            if cost2 > maxTripLength: break
            for k in range(k_0, i):
                Ntemp = N[k][i - 1] + cost
                Ntemp2 = N[k][i - 1] + cost2
                if Ntemp < N[k][j]:
                    N[k][j] = Ntemp
                    P[k][j] = i - 1
                if Ntemp2 <= maxTripLength:
#                     if ((N2[k] + Ntemp2) < N2[j]) or (((N2[k] + Ntemp2) == N2[j]) and ((K2[k] + 1) < K2[j])):
#                         N2[j] = N2[k] + Ntemp2
#                         P2[j] = k
#                         K2[j] = K2[k] + 1
                    if ((K2[k] + 1) < K2[j]):
                        N2[j] = N2[k] + Ntemp2
                        P2[j] = k
                        K2[j] = K2[k] + 1
                    elif ((N2[k] + Ntemp2) < N2[j]):
                        if ((K2[k] + 1) == K2[j]):
                            N2[j] = N2[k] + Ntemp2
                            P2[j] = k
                            K2[j] = K2[k] + 1
                elif (i == j):
                    if orig == True:
                        k_start += 1
                if i==j:
                    if not orig:
                        if j < n: 
                            next_j = sRoute[j]
                            if (N[k][j] - ifRoute[j - 1] + serveCostD[next_j] + bestIFdistD[next_j][depot] + spRoute[j - 1]) > maxTripLength:
                                k_start += 1
    
    free(sRoute)
    free(spRoute)
    free(ifRoute)
    free(N2)
    free(K2)
    for i in range(n): free(N[i])
    free(N)
 
    Path = sp1SourceList(P2, 0, n)
    return(Path, P)

def genAuxGraph_SP_IF_article2(routeOrig):
    '''
    Efficient version generating both auxiliary graphs, and determining the shortest paths between all successive auxiliary node, representing IF partitions, and final
    shortest path representing route partitions. Combined steps for solving the CLARPIF.
    '''
    spD = d
    sRoute = routeOrig[:]
    bestIFdistD = if_cost
    demandD = demand
    serveCostD = service
    maxTripLength = maxTrip
    
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
            if cost2 > maxTripLength: break
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
                else:
                    if i==j: k_start += 1
                    
    Path = sp1SourceList(P2, 0, n)
    return(Path, N, P)

def if_cost_function(nDumps, stats, adjust_estimate, adjust_up):
    '''
    Estimates IF costs in a route. Can be adjusted if estimate is too low.
    '''
    route_average = stats[0]*(1 - adjust_estimate) + adjust_up #- 2*stats[3]
    temp_cost = int(nDumps*route_average)
    return(temp_cost)
    
def estimate_if_cost(load, stats, adjust_estimate, adjust_up):
    '''
    Determines the minimum number of offloads required in a route.
    '''
    nDumps = int(ceil(float(load)/float(capacity)) - 1)
    return(if_cost_function(nDumps, stats, adjust_estimate, adjust_up))
     
def genAuxGraphSP_Est(routeOrig, stats, adjust_estimate, adjust_up):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CLARPIF by estimating the
    IF visit costs in a route. First step in solving the CLARPIF.
    '''
    
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
            if_cost_est = estimate_if_cost(load, stats, adjust_estimate, adjust_up)
            if (j - i) > 1:
                spCosts = spCosts + d[sRoute[j - 2]][sRoute[j - 1]]
            serviceC = serviceC + service[sRoute[j - 1]]
            dDedge = d[depot][sRoute[i]] + serviceC + spCosts + \
                     if_cost[sRoute[j - 1]][depot] + if_cost_est
            if dDedge > maxTrip: break
            else:
                if dEst[j] > dEst[i] + dDedge:
                    dEst[j] = dEst[i] + dDedge
                    piEst[j] = i
    
    Path = sp1SourceList(piEst, 0, len(sRoute))
    return(dEst[len(sRoute)], Path)

def genAuxGraphSP_Est_Advance(routeOrig, min_k):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CLARPIF. IF visits are accounted, 
    when partitioning the routes, but not optimally.
    '''
    
    huge = 1e30000# Infinity
    piEst = {}
    n = len(routeOrig)

#     K = {}
#     dEst = {}
#     sRoute = {}
    cdef double *dEst, *K 
    cdef int *sRoute
    
    dEst = < double *>malloc((n + 1) * sizeof(double *)) 
    K = < double *>malloc((n + 1) * sizeof(double *)) 
    sRoute = < int *>malloc(n * sizeof(int *)) 

    for i in xrange(n):
        sRoute[i] = routeOrig[i]

    for i in xrange(n + 1):
        dEst[i] = huge
        piEst[i] = None
        K[i] = huge
    
    dEst[0] = 0
    K[0] = 0
    if_visits = {}
    if_visits_opt = {}
    
    for i in range(n):
        if_visits[i] = []
        load = 0
        serviceC = 0
        spCosts = 0
        depot_c = d[depot][sRoute[i]]
        for j in range(i + 1, n + 1):
            load = load + demand[sRoute[j - 1]]
            if load > capacity:
                if_cost_est = if_cost[sRoute[j - 2]][sRoute[j - 1]]
                load = demand[sRoute[j - 1]]
                if_visits[i].append(j - 1)
            else:
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
                if min_k == True:
                    newSP = ((K[i] + 1) < K[j]) or ((K[i] + 1 == K[j]) and (dEst[j] > dEst[i] + dDedge))
                else:
                    newSP = ((dEst[i] + dDedge) < dEst[j]) or (((dEst[i] + dDedge) == dEst[j] and ((K[i] + 1) < K[j])))
                
                if newSP == True:
                    dEst[j] = dEst[i] + dDedge
                    piEst[j] = i
                    K[j] = K[i] + 1
                    if_visits_opt[j] = if_visits[i][:]

    dFinal = int(dEst[n])
    
    free(dEst)
    free(K)
    free(sRoute)
    
    Path = sp1SourceList(piEst, 0, n)
    return(dFinal, Path, if_visits, if_visits_opt)

def genAuxGraphSP_Est_Supper_Advance(routeOrig):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CLARPIF. IF visits are accounted, 
    when partitioning the routes, but not optimally.
    '''
                
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

def genAuxGraphSP_Est_Advance2(routeOrig):
    '''
    Generates the auxiliary graph and determines the shortest path through
    the graph - the optimal partition. Original route should not contain the 
    depot visits. Used to partition route for the CLARPIF. IF visits are accounted, 
    when partitioning the routes, and optimally by solving the CARPIF.
    '''
    
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
    
    for i in range(len(sRoute)):
        load = 0
        serviceC = 0
        spCosts = 0
        depot_c = d[depot][sRoute[i]]
        if_visits[i] = []
        for j in range(i + 1, len(sRoute) + 1):
            load = load + demand[sRoute[j - 1]]
            if load > capacity:
                #print('calc IFs', load)
                (if_cost_est, load, path) = genAux1IFGraphSP2(sRoute[i:j]) 
                spCosts = if_cost_est
                if_visits[i] = path[:]
            else:
                if j == 1: if_cost_est = 0
                else: if_cost_est = d[sRoute[j - 2]][sRoute[j - 1]]
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
                    if_visits_opt[j] = if_visits[i][1:-1]
                    
    Path = sp1SourceList(piEst, 0, len(sRoute))
    return(dEst[len(sRoute)], Path, if_visits_opt)