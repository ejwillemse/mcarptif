'''
Created on 03 Jun 2015

@author: eliaswillemse

Class to calculate the cost of different neighbourhood moves within a Local Search framework for the Mixed Capacitated Arc Routing Problems. Moves considered are remove-insert (relocate), 
exchange, and cross (special case of two-opt). Relocate removes an arc from a route and inserts in another position; exchange swaps the location of two routes; and cross swaps the end 
portions of two different routes. Relocate and exchange works on the same or two routes. Traditional Two-Opt moves are not considered as their efficient implementation is not trivial
on mixed networks, specifically as route inversions may result in different costs for the inverted section.

Moves are performed using required arcs as a reference and efficiency frameworks of Beullens et al (2003) are applied, such as candidate arcs and nearest neighbour lists, as
well as their move encoding scheme. Compound moves are also considered within an exhaustive neighbourhood search method, as well as exhaustive neighbourhood descent, first move descent and n
descent. 

The move encoding scheme was inspired by Irnich et al (2006) who use a giant route solution representation with inter route depot visits included, to calculate move costs. This should
allow for easier implementation for the MCARP under route length limit and Intermediate Facilities, as well as other versions of the problem. The general solution encoding scheme 
of Belenguer et al (2006) is used for input variables. The class be used for pure local search, metaheuristics or more complex efficient search frameworks, such as that proposed 
by Zachariadis & Kiranoudis (2010). 

Belenguer, J. M., Benavent, E., Lacomme, P., & Prins, C. (2006). Lower and upper bounds for the mixed capacitated arc routing problem. Computers & Operations Research, 33(12), 3363-3383.
Beullens, P., Muyldermans, L., Cattrysse, D., & Van Oudheusden, D. (2003). A guided local search heuristic for the capacitated arc routing problem. European Journal of Operational Research, 147(3), 629-643.
Irnich, S., Funke, B., & Grunert, T. (2006). Sequential search and its application to vehicle-routing problems. Computers & Operations Research, 33(8), 2405-2429.
Zachariadis, E. E., & Kiranoudis, C. T. (2010). A strategy for reducing the computational complexity of local search-based methods for the vehicle routing problem. Computers & Operations Research, 37(12), 2089-2105.
'''

from __future__ import division

cimport libc.stdlib
from libc.stdlib cimport malloc, free 
from math import ceil

cdef int  _nnListLength, _nArcs
cdef int **_d
cdef int **_nnListC
cdef int *_inv
#cdef int *route
#cdef int *routeMapping,

cdef int **_if_cost

def init_input(d_py, nnList_py, inv_py, dumpCost_py, dummArcs_py):
    
    global _d, _inv, _nnListC, _nnList, _nnListLength, _nArcs, _edgesS, _dumpCost, _dummyArcs
    
    _dummyArcs = dummArcs_py
    _dumpCost = dumpCost_py
    _nArcs = len(d_py)
    _nnListLength = len(nnList_py)
    _d = <int **>malloc(_nArcs * sizeof(int *))
    _nnListC = <int **>malloc(_nnListLength * sizeof(int *))
    _nnList = nnList_py
    
    _inv = <int *>malloc(_nArcs * sizeof(int *))
    inv_py_new = inv_py[:]
    _edgesS = set()
    
    for i, arc in enumerate(inv_py):
        if arc == None:
            inv_py_new[i] = -1
        else:
            _edgesS.add(arc)
    
    if _nArcs == _nnListLength:
        for i from 0 <= i < _nArcs:
            _inv[i] = inv_py_new[i]
            _d[i] = <int *>malloc(_nArcs * sizeof(int *))
            _nnListC[i]  = <int *>malloc(_nArcs * sizeof(int *))

        for i from 0 <= i < _nArcs:
            for j from 0 <= j < _nArcs:
                _d[i][j] = d_py[i][j]
                _nnListC[i][j]  = nnList_py[i][j]

    else:
        for i from 0 <= i < _nArcs:
            _d[i] = <int *>malloc(_nArcs * sizeof(int *))
            
        for i from 0 <= i < _nnListLength:
            _nnListC[i]  = <int *>malloc(_nnListLength * sizeof(int *))
                    
        for i from 0 <= i < _nArcs:
            for j from 0 <= j < _nArcs:
                _d[i][j] = d_py[i][j]          
                     
        for i from 0 <= i < _nnListLength:
            for j from 0 <= j < _nnListLength:
                _nnListC[i][j]  = nnList_py[i][j]    

def init_input_MCARPTIF(if_cost_py, ifs_py):

    global _if_cost, _ifs
    
    _if_cost = <int **>malloc(_nArcs * sizeof(int *))
    _ifs = ifs_py

    for i from 0 <= i < _nArcs:
        _if_cost[i] = <int *>malloc(_nArcs * sizeof(int *))
        
    for i from 0 <= i < _nArcs:
        for j from 0 <= j < _nArcs:
            _if_cost[i][j] = if_cost_py[i][j]

def init_route(route_py):
    
    global route, routeMapping
    
    route = route_py
    nRoute = len(route_py)
    routeMapping = [0]*_nArcs
     
    for i in range(nRoute):
          
        arc = route_py[i]
        route[i] = arc
        routeMapping[arc] = i
          
        arcInv = _inv[arc]
        if arcInv != -1: 
            routeMapping[arcInv] = i


#     nRoute = len(route_py)
#     route = <int *>malloc(nRoute * sizeof(int *))
#      
#     routeMapping = <int *>malloc(_nArcs * sizeof(int *))
#  
#     for i from 0 <= i < nRoute:
#          
#         arc = route_py[i]
#         route[i] = arc
#         routeMapping[arc] = i
#          
#         arcInv = _inv[arc]
#         if arcInv != -1: 
#             routeMapping[arcInv] = i

def free_input():
    
    global _d, _nnListC
    
    if _nArcs == _nnListLength:
        for i from 0 <= i < _nArcs:
            free(_d[i])
            free(_nnListC[i])
    else:
        for i from 0 <= i < _nArcs:
            free(_d[i])
        for i from 0 <= i < _nnListLength:
            free(_nnListC[i])
        
    free(_d)
    free(_nnListC)
    free(_inv)

def free_input_MCARPTIF():

    for i from 0 <= i < _nArcs:
        free(_if_cost[i])   

    free(_if_cost)

def free_route():
    pass
    #free(route)
    #free(routeMapping)
        
def _twoArcCost(preArc, arc):
    '''
    Calculate the cost between two arcs.
    '''
    cost = _d[preArc][arc]
    return(cost)
    
def _twoSeqCost(arcPosition):
    '''
    Calculate the cost of two consecutive arcs in a route.
    '''
    preArc = route[arcPosition - 1]
    arc = route[arcPosition]
    cost = _twoArcCost(preArc, arc)
    return(cost, preArc, arc)

def _threeArcCost(preArc, arc, postArc):
    '''
    Calculate the cost between three arcs.
    '''
    cost = _d[preArc][arc] + _d[arc][postArc]
    return(cost)

def _threeSeqCost(arcPosition):
    '''
    Calculate the cost of three consecutive arcs in a route.
    '''
    preArc = route[arcPosition - 1]
    arc = route[arcPosition]
    postArc = route[arcPosition + 1]
    cost = _threeArcCost(preArc, arc, postArc)
    return(cost, preArc, arc, postArc)
    
def _calcRemoveCost(arcPosition):
    '''
    Calculate the cost of removing an arc.
    '''
    (currentCost, preArc, currentArc, postArc) = _threeSeqCost(arcPosition)
    newCost = _twoArcCost(preArc, postArc)
    netCost = newCost - currentCost
    return(netCost, preArc, postArc)

def _calcInsertCost(arcPosition, arc):
    '''
    Calculate the cost of inserting an arc in a position.
    '''
    (currentCost, preArc, postArc) = _twoSeqCost(arcPosition)
    newCost = _threeArcCost(preArc, arc, postArc)
    netCost = newCost - currentCost
    return(netCost, preArc)
    
def _calcReplaceCost(arcP, arc):
    '''
    Calculate the cost of replacing an arc in a position.
    '''
    preArc = route[arcP - 1]
    currentArc = route[arcP]
    postArc = route[arcP + 1]
    currentCost = _d[preArc][currentArc] + _d[currentArc][postArc]
    newCost = _d[preArc][arc] +  _d[arc][postArc]
    netCost = newCost - currentCost
    return(netCost, currentCost, newCost)

def _initiateMoveCostCalculations(moveCandidates, threshold = None):
    moveCandidates = set(moveCandidates)
    if threshold == None: threshold = 1e300000
    return(moveCandidates, threshold)

def _findNearestNeighboursCandidates(arc, nNearest, candidates):
    if nNearest: 
        if nNearest <= 1:
            nIndex = int(ceil(_nnListLength*nNearest))
        else:
            nIndex = nNearest
        nearestArcSet = set(_nnList[arc][:nIndex])#set(nnList[arc][:nNearest])
        arcNearestCandidates = candidates.intersection(nearestArcSet)
    else: 
        arcNearestCandidates = candidates
    return(arcNearestCandidates)

def _relocateToPositions(arcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold):
    '''
    Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    for arcToRelocateBefore in arcToInsertAt:
        arcPositionInsert = routeMapping[arcToRelocateBefore] # Relocate position
        (netCostInsert, arcToRelocateBeforePreArc) = _calcInsertCost(arcPositionInsert, arcRelocate) # Calculate cost of inserting an arc.
        relocateCost = netCostRemove + netCostInsert
        if relocateCost < threshold:
            relocateAccurate = arcPositionInsert < arcPositionRemove or arcPositionInsert > arcPositionRemove + 1
            if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
            savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, arcToRelocateBefore, arcToRelocateBeforePreArc, None), 'relocate', (netCostRemove, netCostInsert)))
    return(savings)
            
def relocateMoves(relocateCandidates, arcToRelocateBeforeCandidates, 
                   threshold = None, nNearest = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (arcToRelocateBeforeCandidates, thresholds) = _initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
    
    for arcRelocate in relocateCandidates:
        arcPositionRemove = routeMapping[arcRelocate]
        (netCostRemove, removePreArc, removePostArc) = _calcRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
        arcToInsertAt = _findNearestNeighboursCandidates(arcRelocate, nNearest, arcToRelocateBeforeCandidates)
        savings += _relocateToPositions(arcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)

    return(savings)

def relocateMovesWithInv(relocateCandidates, arcToRelocateBeforeCandidates, 
                   threshold = None, nNearest = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (arcToRelocateBeforeCandidates, thresholds) = _initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
    
    for arcRelocate in relocateCandidates:
        arcPositionRemove = routeMapping[arcRelocate]
        (netCostRemove, removePreArc, removePostArc) = _calcRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
        arcToInsertAt = _findNearestNeighboursCandidates(arcRelocate, nNearest, arcToRelocateBeforeCandidates)
        savings += _relocateToPositions(arcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)

        if arcRelocate in _edgesS:
            invArcRelocate = _inv[arcRelocate]
            savings += _relocateToPositions(invArcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)
            
    return(savings)

def _exchangeWithPosition(arcsToExchange, arcExhangePosition1, preArc1, arcExchange1, postArc1, currenCost1, threshold):
    '''
    Calculate the move cost of exchanging a specified arc with other arcs.
    '''
    savings = []
    for arcExchange2 in arcsToExchange:
        arcExhangePosition2 = routeMapping[arcExchange2]
        exchangeArcs = arcExhangePosition2 > arcExhangePosition1 + 1 # Prevents re-evaluation of exchanges (B with A is the same as A with B), and for two consecutive arcs to be exchanged (1,2,3(A),4(B),5,6).
        if not exchangeArcs: continue

        (currenCost2, preArc2, arc2, postArc2) = _threeSeqCost(arcExhangePosition2) # Calculate cost of inserting an arc. 
        newCost1 = _threeArcCost(preArc1, arcExchange2, postArc1) # Cost of new sequences with middle arcs replaced.
        newCost2 = _threeArcCost(preArc2, arcExchange1, postArc2)
        netCostRoute1 = newCost1 - currenCost1
        netCostRoute2 = newCost2 - currenCost2
        exchangeCost = netCostRoute1 + netCostRoute2
        if exchangeCost < threshold: # If it's below (better than) a threshold the move is added to the savings list.
            savings.append((exchangeCost, (arcExchange1, preArc1, postArc1, arcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1, netCostRoute2)))
    return(savings)
                
def exchangeMoves(exchangeCandidatesI, exchangeCandidatesJ, 
                   threshold = None, nNearest = None):
    '''
    Calculate the move cost of exchanging two arcs. To enable the nearest-neighbour list, the preceding arc of an
    exchange is determined, and its neighbours are used, which may include the depot arc.
    '''
    
    savings = []
    (exchangeCandidatesI, threshold) = _initiateMoveCostCalculations(exchangeCandidatesI, threshold)
    exchangeCandidatesJ = set(exchangeCandidatesJ)
    
    for arcExchange1 in exchangeCandidatesI:
        arcExhangePosition1 = routeMapping[arcExchange1]
        (currenCost1, preArc1, arc1, postArc1) = _threeSeqCost(arcExhangePosition1)
        arcsToExchange = _findNearestNeighboursCandidates(preArc1, nNearest, exchangeCandidatesJ) # Select nearest neighbours of arcRelocate 
        savings += _exchangeWithPosition(arcsToExchange, arcExhangePosition1, 
                                              preArc1, arcExchange1, postArc1, currenCost1, threshold)
    return(savings)

def _crossWithPositions(nearestCandidatesJ, arcIPosition, preArcI, arcI, currenCostI, threshold):
    
    '''
    Calculate the move costs with a specified arc and all others.
    '''
    savings = []
    for arcJ in nearestCandidatesJ:
        arcJPosition = routeMapping[arcJ]
        moveFeasible = arcJPosition > arcIPosition + 1 # Prevents re-evaluation of exchanges (B with A is the same as A with B), and for two consecutive arcs to be exchanged (1,2,3(A),4(B),5,6).
        if not moveFeasible: continue

        (currenCostJ, preArcJ, currentArcJ) = _twoSeqCost(arcJPosition) # Calculate cost of inserting an arc. 
        newCostI = _twoArcCost(preArcI, arcJ) # Cost of new sequences with middle arcs replaced.
        newCostJ = _twoArcCost(preArcJ, arcI)
        moveCost = (newCostI - currenCostI) +  (newCostJ - currenCostJ)
        if moveCost < threshold: # If it's below (better than) a threshold the move is added to the savings list.
            savings.append((moveCost, (arcI, preArcI, None, arcJ, preArcJ, None), 'cross', (newCostI - currenCostI, newCostJ - currenCostJ)))
    return(savings)
    
def crossMoves(candidatesI, candidatesJ, threshold = None, nNearest = None):
    '''
    Calculate the move cost of crossing two end sections in a route. Same principles applies as exchange.
    '''
    savings = []
    (candidatesI, threshold) = _initiateMoveCostCalculations(candidatesI, threshold)
    candidatesJ = set(candidatesJ)
    
    for arcI in candidatesI:
        arcIPosition = routeMapping[arcI]
        (currenCostI, preArcI, currentArcI) = _twoSeqCost(arcIPosition)
        nearestCandidatesJ = _findNearestNeighboursCandidates(arcI, nNearest, candidatesJ) # Select nearest neighbours of arcRelocate 
        savings += _crossWithPositions(nearestCandidatesJ, arcIPosition, preArcI, arcI, currenCostI, threshold)
    return(savings)

def flipMoves(flipCandidates, threshold = None):
    '''
    Calculate the move cost of inverting an edge arc task.
    '''
    savings = []
    (flipCandidates, threshold) = _initiateMoveCostCalculations(flipCandidates, threshold)
    flipEdges = flipCandidates.intersection(_edgesS)
    for arc in flipEdges:
        arcPosition = routeMapping[arc]
        invArc = _inv[arc]
        (currenCost, preArc, arc, postArc) = _threeSeqCost(arcPosition)
        newCost = _threeArcCost(preArc, invArc, postArc)
        flipCost = newCost - currenCost
        if flipCost < threshold:
            savings.append((flipCost, (invArc, preArc, postArc, None, None, None), 'flip', (arcPosition, None)))
    return(savings)

def relocateEndRouteMoves(relocateCandidates, routeDummyArcs, threshold = None, nNearest = None):
    '''
    Calculate the move cost of exception relocating an arc from current position before a dummy arc:
        - End of a route before the depot.
    First dummy arc(s) in the giant route should thus NOT be in dummyArcs set.
    '''
    savings = []
    for dummyArcPosition in routeDummyArcs: # Arc will be inserted before the last dummy arc of a route, thus end of a route.
        if dummyArcPosition == 0: continue # Arc cannot be inserted before the giant route.
        (relocateCandidates, threshold) = _initiateMoveCostCalculations(relocateCandidates, threshold)
        (currentDepotCost, preArc, dummyArc) = _twoSeqCost(dummyArcPosition)
        arcToInsertAfter = _findNearestNeighboursCandidates(preArc, nNearest, relocateCandidates)
        for arcRelocate in arcToInsertAfter:
            arcPositionRemove = routeMapping[arcRelocate]
            (netCostRemove, removePreArc, removePostArc) = _calcRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
            netCostInsert = _threeArcCost(preArc, arcRelocate, dummyArc)
            relocateCost = netCostRemove + netCostInsert - currentDepotCost
            if relocateCost < threshold:
                relocateAccurate = dummyArcPosition < arcPositionRemove or dummyArcPosition > arcPositionRemove + 1
                if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
                savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, dummyArc, preArc, None), 'relocateBeforeDummy', (netCostRemove, netCostInsert - currentDepotCost)))
                
    return(savings)

def relocateEndRouteMovesWithInv(relocateCandidates, routeDummyArcs, threshold = None, nNearest = None):
    '''
    Calculate the move cost of exception relocating an arc from current position before a dummy arc:
        - End of a route before the depot.
    First dummy arc(s) in the giant route should thus NOT be in dummyArcs set.
    '''
    savings = []
    for dummyArcPosition in routeDummyArcs: # Arc will be inserted before the last dummy arc of a route, thus end of a route.
        if dummyArcPosition == 0: continue # Arc cannot be inserted before the giant route.
        (relocateCandidates, threshold) = _initiateMoveCostCalculations(relocateCandidates, threshold)
        (currentDepotCost, preArc, dummyArc) = _twoSeqCost(dummyArcPosition)
        arcToInsertAfter = _findNearestNeighboursCandidates(preArc, nNearest, relocateCandidates)
        for arcRelocate in arcToInsertAfter:
            arcPositionRemove = routeMapping[arcRelocate]
            (netCostRemove, removePreArc, removePostArc) = _calcRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
            netCostInsert = _threeArcCost(preArc, arcRelocate, dummyArc)
            relocateCost = netCostRemove + netCostInsert - currentDepotCost
            if relocateCost < threshold:
                relocateAccurate = dummyArcPosition < arcPositionRemove or dummyArcPosition > arcPositionRemove + 1
                if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
                savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, dummyArc, preArc, None), 'relocateBeforeDummy', (netCostRemove, netCostInsert - currentDepotCost)))

            if arcRelocate in _edgesS:
                arcRelocateInv = _inv[arcRelocate]
                
                netCostInsert = _threeArcCost(preArc, arcRelocateInv, dummyArc)
                relocateCost = netCostRemove + netCostInsert - currentDepotCost
                if relocateCost < threshold:
                    relocateAccurate = dummyArcPosition < arcPositionRemove or dummyArcPosition > arcPositionRemove + 1
                    if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
                    savings.append((relocateCost, (arcRelocateInv, removePreArc, removePostArc, dummyArc, preArc, None), 'relocateBeforeDummy', (netCostRemove, netCostInsert - currentDepotCost)))
                
    return(savings)

def crossEndRouteMoves(crossCandidates, routeDummyArcs, threshold = None, nNearest = None):
    '''
    Calculate the move cost of crossing two end sections in a route. Same principles applies as exchange.
    '''
    savings = []
    for dummyArcPosition in routeDummyArcs: # Arc will be inserted before the last dummy arc of a route, thus end of a route.
        if dummyArcPosition == 0: continue # Arc cannot be inserted before the giant route.
        (crossCandidates, threshold) = _initiateMoveCostCalculations(crossCandidates, threshold)
        (currenCost1, preArc1, dummyArc) = _twoSeqCost(dummyArcPosition)
        arcToCrossAfter = _findNearestNeighboursCandidates(preArc1, nNearest, crossCandidates)
        for arcExchange2 in arcToCrossAfter:
            arcExhangePosition2 = routeMapping[arcExchange2]
            exchangeArcs = dummyArcPosition > arcExhangePosition2 + 1 or dummyArcPosition < arcExhangePosition2 # Prevents re-evaluation of exchanges (B with A is the same as A with B), and for two consecutive arcs to be exchanged (1,2,3(A),4(B),5,6).
            if not exchangeArcs: continue
            (currenCost2, preArc2, arc2) = _twoSeqCost(arcExhangePosition2) # Calculate cost of inserting an arc. 
            newCost1 = _twoArcCost(preArc1, arcExchange2) # Cost of new sequences with middle arcs replaced.
            newCost2 = _twoArcCost(preArc2, dummyArc)
            if preArc2 in _dummyArcs: dumpSave = -_dumpCost
            else: dumpSave = 0
            exchangeCost = (newCost1 - currenCost1) +  (newCost2 - currenCost2) + dumpSave
            if exchangeCost < threshold: # If it's below (better than) a threshold the move is added to the savings list.
                savings.append((exchangeCost, (arcExchange2, preArc2, None, dummyArc, preArc1, None), 'crossAtDummy', (newCost2 - currenCost2 + dumpSave, newCost1 - currenCost1)))
    return(savings)

def _exchangeWithPositionWithInv(arcsToExchange, arcExhangePosition1, preArc1, arcExchange1, postArc1, currenCost1, threshold):
    '''
    Calculate the move cost of exchanging a specified arc with other arcs.
    '''
    savings = []
    for arcExchange2 in arcsToExchange:
        arcExhangePosition2 = routeMapping[arcExchange2]
        exchangeArcs = arcExhangePosition2 > arcExhangePosition1 + 1 # Prevents re-evaluation of exchanges (B with A is the same as A with B), and for two consecutive arcs to be exchanged (1,2,3(A),4(B),5,6).
        if not exchangeArcs: continue

        (currenCost2, preArc2, arc2, postArc2) = _threeSeqCost(arcExhangePosition2) # Calculate cost of inserting an arc. 
        newCost1 = _threeArcCost(preArc1, arcExchange2, postArc1) # Cost of new sequences with middle arcs replaced.
        newCost2 = _threeArcCost(preArc2, arcExchange1, postArc2)
        netCostRoute1 = newCost1 - currenCost1
        netCostRoute2 = newCost2 - currenCost2
        exchangeCost = netCostRoute1 + netCostRoute2
        if exchangeCost < threshold: # If it's below (better than) a threshold the move is added to the savings list.
            savings.append((exchangeCost, (arcExchange1, preArc1, postArc1, arcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1, netCostRoute2)))
            
        bothExchange = True
        
        if arcExchange2 in _edgesS:
            invArcExchange2 = _inv[arcExchange2]
            newCost1inv = _threeArcCost(preArc1, invArcExchange2, postArc1)
            netCostRoute1inv = newCost1inv - currenCost1
            exchangeCostinv = netCostRoute1inv + netCostRoute2
            if exchangeCostinv < threshold: # If it's below (better than) a threshold the move is added to the savings list.
                savings.append((exchangeCostinv, (arcExchange1, preArc1, postArc1, invArcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1inv, netCostRoute2)))
        else:
            bothExchange = False
            
        if arcExchange1 in _edgesS:
            invArcExchange1 = _inv[arcExchange1]
            newCost2inv = _threeArcCost(preArc2, invArcExchange1, postArc2)
            netCostRoute2inv = newCost2inv - currenCost2
            exchangeCostinv = netCostRoute1 + netCostRoute2inv
            if exchangeCostinv < threshold: # If it's below (better than) a threshold the move is added to the savings list.
                savings.append((exchangeCostinv, (invArcExchange1, preArc1, postArc1, arcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1, netCostRoute2inv)))
        else:
            bothExchange = False
            
        if bothExchange:
            exchangeCostinv = netCostRoute1inv + netCostRoute2inv
            if exchangeCostinv < threshold: # If it's below (better than) a threshold the move is added to the savings list.
                savings.append((exchangeCostinv, (invArcExchange1, preArc1, postArc1, invArcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1inv, netCostRoute2inv)))   
            
    return(savings)
                
def exchangeMovesWithInv(exchangeCandidatesI, exchangeCandidatesJ, 
                   threshold = None, nNearest = None):
    '''
    Calculate the move cost of exchanging two arcs. To enable the nearest-neighbour list, the preceding arc of an
    exchange is determined, and its neighbours are used, which may include the depot arc.
    '''
    
    savings = []
    (exchangeCandidatesI, threshold) = _initiateMoveCostCalculations(exchangeCandidatesI, threshold)
    exchangeCandidatesJ = set(exchangeCandidatesJ)
    
    for arcExchange1 in exchangeCandidatesI:
        arcExhangePosition1 = routeMapping[arcExchange1]
        (currenCost1, preArc1, arc1, postArc1) = _threeSeqCost(arcExhangePosition1)
        arcsToExchange = _findNearestNeighboursCandidates(preArc1, nNearest, exchangeCandidatesJ) # Select nearest neighbours of arcRelocate 
        savings += _exchangeWithPositionWithInv(arcsToExchange, arcExhangePosition1, 
                                              preArc1, arcExchange1, postArc1, currenCost1, threshold)
    return(savings)

def _threeArcDoubleCost(preArc, arc1, arc2, postArc):
    '''
    Calculate the cost between three arcs.
    '''
    cost = _d[preArc][arc1] + _d[arc2][postArc]
    return(cost)

def _calcDoubleInsertCost(arcPosition, arc1, arc2):
    '''
    Calculate the cost of inserting an arc in a position.
    '''
    (currentCost, preArc, postArc) = _twoSeqCost(arcPosition)
    newCost = _threeArcDoubleCost(preArc, arc1, arc2, postArc)
    netCost = newCost - currentCost
    return(netCost, preArc)

def _doubleRelocateToPositions(arcRelocate1, arcRelocate2, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold):
    '''
    Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    for arcToRelocateBefore in arcToInsertAt:
        arcPositionInsert = routeMapping[arcToRelocateBefore] # Relocate position
        (netCostInsert, arcToRelocateBeforePreArc) = _calcDoubleInsertCost(arcPositionInsert, arcRelocate1, arcRelocate2) # Calculate cost of inserting an arc.
        relocateCost = netCostRemove + netCostInsert
        if relocateCost < threshold:
            relocateAccurate = arcPositionInsert < arcPositionRemove or arcPositionInsert > arcPositionRemove + 2
            if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
            savings.append((relocateCost, (arcRelocate1, removePreArc, removePostArc, arcToRelocateBefore, arcToRelocateBeforePreArc, arcRelocate2), 'doubleRelocate', (netCostRemove, netCostInsert)))
    return(savings)

def _threeSeqDoubleCost(arcPosition):
    '''
    Calculate the cost of three consecutive arcs in a route.
    '''      
    preArc = route[arcPosition - 1]
    arc1 = route[arcPosition]
    arc2  = route[arcPosition + 1]
    postArc = route[arcPosition + 2]
    cost = _threeArcDoubleCost(preArc, arc1, arc2, postArc)
    return(cost, preArc, arc1, arc2, postArc)
    
def _calcDoubleRemoveCost(arcPosition):
    '''
    Calculate the cost of removing an arc.
    '''
    (currentCost, preArc, currentArc1, currentArc2, postArc) = _threeSeqDoubleCost(arcPosition)
    newCost = _twoArcCost(preArc, postArc)
    netCost = newCost - currentCost
    return(netCost, preArc, currentArc2, postArc)

def doubleRelocateMoves(relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (arcToRelocateBeforeCandidates, threshold) = _initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
    
    for arcRelocate1 in relocateCandidates:
        arcPositionRemove = routeMapping[arcRelocate1]
        (netCostRemove, removePreArc, arcRelocate2, removePostArc) = _calcDoubleRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
        arcToInsertAt = _findNearestNeighboursCandidates(arcRelocate2, nNearest, arcToRelocateBeforeCandidates)
        savings += _doubleRelocateToPositions(arcRelocate1, arcRelocate2, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)
    return(savings)

# ====================================== #
# MCARPTIF move costs

def _calcRemoveCostMCARPTIF(arcPosition):
    '''
    Calculate the cost of removing an arc.
    '''  
    preArc = route[arcPosition - 1]
    arc = route[arcPosition]
    postArc = route[arcPosition + 1]
    currentCost = _d[preArc][arc] + _d[arc][postArc]
    newCost = _d[preArc][postArc]
    netCost = newCost - currentCost
    return(netCost, preArc, postArc)
    
def _calcRemoveCostPostIF(arcPosition):
    '''
    Calculate the cost of removing an arc.
    '''  
    preArc = route[arcPosition - 2]
    arc = route[arcPosition]
    postArc = route[arcPosition + 1]
    currentCost = _if_cost[preArc][arc] + _d[arc][postArc]
    newCost = _if_cost[preArc][postArc]
    netCost = newCost - currentCost
    return(netCost, preArc, postArc)

def _calcRemoveCostPreIF(arcPosition):
    '''
    Calculate the cost of removing an arc.
    '''
    preArc = route[arcPosition - 1]
    arc = route[arcPosition]
    postArc = route[arcPosition + 2]
    currentCost = _d[preArc][arc] + _if_cost[arc][postArc]
    newCost = _if_cost[preArc][postArc]
    netCost = newCost - currentCost
    return(netCost, preArc, postArc)

def _calcInsertCostPostIF(arcPosition, insertArc):
    '''
    Calculate the cost of removing an arc.
    '''
    preArc = route[arcPosition - 2]
    arc = route[arcPosition]
    currentCost = _if_cost[preArc][arc]
    newCost = _if_cost[preArc][insertArc] + _d[insertArc][arc]
    netCost = newCost - currentCost
    return(netCost, preArc)

def _calcInsertCostPreIF(arcPosition, insertArc):
    '''
    Calculate the cost of removing an arc.
    '''    
    arc = route[arcPosition]
    postArc = route[arcPosition + 2]
    currentCost = _if_cost[arc][postArc]
    newCost = _d[arc][insertArc] + _if_cost[insertArc][postArc]
    netCost = newCost - currentCost
    return(netCost, postArc)

def _calcInsertCostMCARPTIF(arcPosition, insertArc):
    '''
    Calculate the cost of removing an arc.
    '''  
    preArc = route[arcPosition - 1]
    arc = route[arcPosition]
    currentCost = _d[preArc][arc]
    newCost = _d[preArc][insertArc] + _d[insertArc][arc]
    netCost = newCost - currentCost
    return(netCost, preArc)

def _relocateToPreIF(arcsToRelocate, arcRelocateAfter, threshold):
    '''
    Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    arcPositionInsert = routeMapping[arcRelocateAfter]
    for arcToRelocate in arcsToRelocate:
        arcPositionRemove = routeMapping[arcToRelocate]
        relocateAccurate = arcPositionRemove < arcPositionInsert or arcPositionInsert + 2 < arcPositionRemove
        if not relocateAccurate: continue
        preArc = route[arcPositionRemove - 1]
        postArc = route[arcPositionRemove + 1]
        if preArc in _ifs: 
            specialIF = 'PostIF'
            (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostPostIF(arcPositionRemove)
        elif postArc in _ifs: 
            specialIF = 'PreIF'
            (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostPreIF(arcPositionRemove)
        else:
            specialIF = ''
            (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostMCARPTIF(arcPositionRemove)
        (netCostInsert, arcToRelocateAfterPost) = _calcInsertCostPreIF(arcPositionInsert, arcToRelocate)
        relocateCost = netCostRemove + netCostInsert
        if relocateCost < threshold:
            savings.append((relocateCost, (arcToRelocate, removePreArc, removePostArc, arcRelocateAfter, None, arcToRelocateAfterPost), 'relocate' + specialIF + '_PreIF', (netCostRemove, netCostInsert)))
    return(savings)

def relocateMovesPreIF(relocateCandidates, arcToRelocateAfterCandidates, threshold = None, nNearest = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (relocateCandidates, threshold) = _initiateMoveCostCalculations(relocateCandidates, threshold)
    for arcRelocateAfter in arcToRelocateAfterCandidates:
        arcsToRelocate = _findNearestNeighboursCandidates(arcRelocateAfter, nNearest, relocateCandidates)      
        savings += _relocateToPreIF(arcsToRelocate, arcRelocateAfter, threshold)
    return(savings)

def _relocateToPostIF(arcRelocate, arcToRelocateBeforeCandidates, threshold):
    '''
    Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    arcPositionRemove = routeMapping[arcRelocate]
    preArc = route[arcPositionRemove - 1]
    postArc = route[arcPositionRemove + 1]            

    if preArc in _ifs: 
        specialIF = 'PostIF'
        (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostPostIF(arcPositionRemove)
    elif postArc in _ifs: 
        specialIF = 'PreIF'
        (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostPreIF(arcPositionRemove)
    else:
        specialIF = ''
        (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostMCARPTIF(arcPositionRemove)
    
    for arcToRelocateBefore in arcToRelocateBeforeCandidates:
        arcPositionInsert = routeMapping[arcToRelocateBefore]
        relocateAccurate = arcPositionRemove > arcPositionInsert or arcPositionInsert > arcPositionRemove + 2
        if not relocateAccurate: continue
        (netCostInsert, arcToRelocateBeforePre) = _calcInsertCostPostIF(arcPositionInsert, arcRelocate)
        relocateCost = netCostRemove + netCostInsert
        if relocateCost < threshold:
            savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, arcToRelocateBefore, arcToRelocateBeforePre, None), 'relocate' + specialIF + '_PostIF', (netCostRemove, netCostInsert)))
    return(savings)

def relocateMovesPostIF(relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (arcToRelocateBeforeCandidates, threshold) = _initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
    for arcRelocate in relocateCandidates:
        arcToRelocateBeforeCandidates = _findNearestNeighboursCandidates(arcRelocate, nNearest, arcToRelocateBeforeCandidates)      
        savings += _relocateToPostIF(arcRelocate, arcToRelocateBeforeCandidates, threshold)
    return(savings)

def _relocateBeforeArc(arcRelocate, arcToRelocateBeforeCandidates, threshold):
    '''
    Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    arcPositionRemove = routeMapping[arcRelocate]
    preArc = route[arcPositionRemove - 1]
    postArc = route[arcPositionRemove + 1]            

    if preArc in _ifs: 
        specialIF = 'PostArcIF'
        (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostPostIF(arcPositionRemove)
        arcPositionRemoveAdd = + 1
    elif postArc in _ifs: 
        specialIF = 'PreArcIF'
        (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostPreIF(arcPositionRemove)
        arcPositionRemoveAdd = + 2
    else:
        specialIF = ''
        (netCostRemove, removePreArc, removePostArc) = _calcRemoveCostMCARPTIF(arcPositionRemove)
        arcPositionRemoveAdd = + 1
        
    for arcToRelocateBefore in arcToRelocateBeforeCandidates:
        arcPositionInsert = routeMapping[arcToRelocateBefore]
        relocateAccurate = arcPositionRemove > arcPositionInsert or arcPositionInsert > arcPositionRemove + arcPositionRemoveAdd
        if not relocateAccurate: continue
        (netCostInsert, arcToRelocateBeforePre) = _calcInsertCostMCARPTIF(arcPositionInsert, arcRelocate)
        relocateCost = netCostRemove + netCostInsert
        if relocateCost < threshold:
            savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, arcToRelocateBefore, arcToRelocateBeforePre, None), 'relocate' + specialIF, (netCostRemove, netCostInsert)))
    return(savings)
    
def relocateMovesMCARPTIF(relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (arcToRelocateBeforeCandidates, threshold) = _initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
    for arcRelocate in relocateCandidates:
        arcToRelocateBeforeCandidates = _findNearestNeighboursCandidates(arcRelocate, nNearest, arcToRelocateBeforeCandidates)      
        savings += _relocateBeforeArc(arcRelocate, arcToRelocateBeforeCandidates, threshold)
    return(savings)
