b'''
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

def init_input(d_py, nnList_py, inv_py, dumpCost_py, dummArcs_py, if_cost_py, ifs_py):
    
    global _d, _inv, _nnListC, _nnList, _nnListLength, _nArcs, _edgesS, _dumpCost, _dummyArcs, _if_cost, _ifs
    
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

    for i from 0 <= i < _nArcs:
        free(_if_cost[i])   

    free(_if_cost)

def free_route():
    pass
    #free(route)
    #free(routeMapping)
        
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

def _threeSeqCost(arcPosition, n):
    '''
    Calculate the cost of three consecutive arcs in a route.
    '''         
    preArc = route[arcPosition - 1]
    arc = route[arcPosition]
    postArc = route[arcPosition + 1]
    
    if preArc in _ifs: 
        exchangePos = n + 'excPostIF'
        preArc = route[arcPosition - 2]
        cost = _if_cost[preArc][arc] + _d[arc][postArc]
    elif postArc in _ifs: 
        exchangePos = n + 'excPreIF'
        postArc = route[arcPosition + 2]
        cost = _d[preArc][arc] + _if_cost[arc][postArc]
    else: 
        exchangePos = ''
        cost = _d[preArc][arc] + _d[arc][postArc]
    return(cost, preArc, arc, postArc, exchangePos)

def _replaceCost(preArc, postArc, replaceArc, exchangePos):
    '''
    Calculate the cost of three consecutive arcs in a route.
    '''                  
    if exchangePos.find('excPostIF') != -1: 
        cost = _if_cost[preArc][replaceArc] + _d[replaceArc][postArc]
    elif exchangePos.find('excPreIF') != -1:
        cost = _d[preArc][replaceArc] + _if_cost[replaceArc][postArc]
    else: 
        cost = _d[preArc][replaceArc] + _d[replaceArc][postArc]
    return(cost)

def exchangeMovesMCARPTIF(exchangeCandidates1, exchangeCandidates2, threshold = None, nNearest = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (exchangeCandidates1, threshold) = _initiateMoveCostCalculations(exchangeCandidates1, threshold)
    for arcExchange1 in exchangeCandidates1:
        arcPositionExc1 = routeMapping[arcExchange1]
        (cost1, preArc1, arc1, postArc1, exchangePos1) = _threeSeqCost(arcPositionExc1, n= '_1')
        exchangeCandidates2 = _findNearestNeighboursCandidates(preArc1, nNearest, exchangeCandidates2) 
        for arcExchange2 in exchangeCandidates2:
            arcPositionExc2 = routeMapping[arcExchange2]
            (cost2, preArc2, arc2, postArc2, exchangePos2) = _threeSeqCost(arcPositionExc2, n = '_2')
            if exchangePos1 == '_1excPreIF' and exchangePos2 == '_2excPostIF':
                exchangeArcs = arcPositionExc2 > arcPositionExc1 + 2
            else: 
                exchangeArcs = arcPositionExc2 > arcPositionExc1 + 1
            if not exchangeArcs: continue
            cost1new = _replaceCost(preArc1, postArc1, arcExchange2, exchangePos1)
            cost2new = _replaceCost(preArc2, postArc2, arcExchange1, exchangePos2)
            netExc1 = cost1new - cost1
            netExc2 = cost2new - cost2
            netExc = netExc1 + netExc2
            if netExc1 + netExc2 < threshold:
                savings.append((netExc, (arcExchange1, preArc1, postArc1, arcExchange2, preArc2, postArc2), 'exchange' + exchangePos1 + exchangePos2, (netExc1, netExc2)))
    return(savings)

def _twoSeqCost(arcPosition, n):
    '''
    Calculate the cost of three consecutive arcs in a route.
    '''       
    preArc = route[arcPosition - 1]
    arc = route[arcPosition]
    
    if preArc in _ifs: 
        crossPos = n + 'crossPostIF'
        preArc = route[arcPosition - 2]
        cost = _if_cost[preArc][arc]
    else: 
        crossPos = ''
        cost = _d[preArc][arc]
    return(cost, preArc, arc, crossPos)

def _relinkCost(preArc, relinkArc, crossPos):
    '''
    Calculate the cost of three consecutive arcs in a route.
    '''                  
    if crossPos.find('crossPostIF') != -1: 
        cost = _if_cost[preArc][relinkArc]
    else: 
        cost = _d[preArc][relinkArc]
    return(cost)

def crossMovesMCARPTIF(relinkCandidates1, relinkCandidates2, threshold = None, nNearest = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (relinkCandidates1, threshold) = _initiateMoveCostCalculations(relinkCandidates1, threshold)
    for arcRelink1 in relinkCandidates1:
        arcPositionRelink1 = routeMapping[arcRelink1]
        (cost1, preArc1, arc1, relinkPos1) = _twoSeqCost(arcPositionRelink1, n= '_1')
        relinkCandidates2 = _findNearestNeighboursCandidates(preArc1, nNearest, relinkCandidates2) 
        for arcRelink2 in relinkCandidates2:
            arcPositionRelink2 = routeMapping[arcRelink2]
            (cost2, preArc2, arc2, relinkPos2) = _twoSeqCost(arcPositionRelink2, n = '_2')
            if relinkPos1 == '_1crossPreIF' and relinkPos2 == '_2crossPostIF':
                exchangeArcs = arcPositionRelink2 > arcPositionRelink1 + 2
            else: 
                exchangeArcs = arcPositionRelink2 > arcPositionRelink1 + 1
            if not exchangeArcs: continue
            cost1new = _relinkCost(preArc1, arcRelink2, relinkPos1)
            cost2new = _relinkCost(preArc2, arcRelink1, relinkPos2)
            netLink1 = cost1new - cost1
            netLink2 = cost2new - cost2
            netLinkNew = netLink1 + netLink2
            if netLinkNew < threshold:
                savings.append((netLinkNew, (arcRelink1, preArc1, None, arcRelink2, preArc2, None), 'cross' + relinkPos1 + relinkPos2, (netLink1, netLink2)))
    return(savings)

def flipMovesMCARPTIF(exchangeCandidates1, threshold = None):
    '''
    Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
    an arc to the end of a route and replacing an arc with its inverse 
    '''
    savings = []
    (exchangeCandidates1, threshold) = _initiateMoveCostCalculations(exchangeCandidates1, threshold)
    for arcExchange1 in exchangeCandidates1:
        invExchange = _inv[arcExchange1]
        arcPositionExc1 = routeMapping[arcExchange1]
        (cost1, preArc1, arc1, postArc1, exchangePos1) = _threeSeqCost(arcPositionExc1, n= '_')
        cost1new = _replaceCost(preArc1, postArc1, invExchange, exchangePos1)
        netFlip = cost1new - cost1
        if netFlip < threshold:
            savings.append((netFlip, (arcExchange1, preArc1, postArc1, invExchange, None, None), 'flip' + exchangePos1, (netFlip, 0)))
    return(savings)
