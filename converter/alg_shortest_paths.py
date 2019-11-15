#===============================================================================
# Floyd-Warshall algorithm adapted for Arc to Arc with Turn Penalties
# Creator: Elias Willemse (ejwillemse@gmail.com)

# Derived from the book:
# Cormen, T., Leiserson, C., Rivest, R. (1990). Introduction to algorithms 
# Chapter 26 pages 558-562.
#===============================================================================

import numpy as np

huge = 1e300000# Infinity


def SP(cL, sL, penDict=None):
    '''
    Addaptation of the Floyd Warshall algorithm for computing arc to 
    arc shortest paths, instead of node to node.
    
    Required input are cost of each arc, the predecesors of an arc, 
    and the turn penalty from moving from one arc to another. Output 
    are the distance matrix D between all arcs, and the predecesor 
    matrix.
    
    Note that the graph has to be complete and connected, ie. all arcs should
    have at least one predecesor arc and one succesor arc.
    
    Output is an m x m dictionary - representing a matrix -  of distances
    and predecesors. For the predecesor matrix, a predecesor of zero means
    that the edge is the origen node.
    
    Algorithm runs in O(m^3) and uses O(m^2) space.
    '''
    print('')
    print('Starting shortest path calculations (3 procedures)')
    print('')

    nArcs = len(cL)
    
    d = np.ndarray(shape=(nArcs, nArcs))

    print('    1 of 3: Initialise matrices')
        
    for i in xrange(nArcs):
        d[i][i] = -1

    for i in xrange(nArcs):
        sL_i = sL[i]
        nSucs = len(sL_i)
        for j in xrange(nSucs):
            d[i][sL_i[j]] = -1
            
    for i in xrange(nArcs):
        for j in xrange(nArcs):
            if d[i][j] != -1: d[i][j] = huge# Distance from an arc to itself is zeros
            elif d[i][j] == -1: d[i][j] = 0                


    print('    2 of 3: Calculate shortest paths')
    print('') 
    for k in xrange(nArcs):
        print('        2 of 3: SP calc %i out of %i' %(k+1,nArcs))
        cL_k = cL[k]
        for i in xrange(nArcs):
            d_i_k = d[i][k]
            for j in xrange(nArcs):
                if d_i_k + d[k][j] + cL_k < d[i][j]:#If moving from arc i to arc j via arc k is shorter than moving directly from arc i to j:
                    #Note that we have to add the cost of traversing arc k
                    d[i][j] = d_i_k + d[k][j] + cL_k#Update distance from arc i to j
    
    print('')
    print('    3 of 3: Populating numpy array')
        
    print('')
    print('    Done: shortest path calculations')
    print('')
    
    return(d)


def SP_IFs(cL, sL, reqArcList, dumpCost, IFarcsnewkey = None):
    '''
    Addaptation of the Floyd Warshall algorithm for computing arc to 
    arc shortest paths, instead of node to node. Combined with calculating
    best IFs to visit.
    '''
    
    print('')
    print('Starting shortest path calculations (3 procedures)')
    print('')
    
    nArcs = len(cL)
    
    d = np.ndarray(shape=(nArcs, nArcs))
    print('    1 of 3: Initialise matrices')
    
        
    for i in range(nArcs):
        d[i][i] = -1

    for i in range(nArcs):
        sL_i = sL[i]
        nSucs = len(sL_i)
        for j in range(nSucs):
            d[i][sL_i[j]] = -1
            
    for i in range(nArcs):
        for j in range(nArcs):
            if d[i][j] != -1: d[i][j] = huge# Distance from an arc to itself is zeros
            elif d[i][j] == -1: d[i][j] = 0                
    
    print('    2 of 3: Calculate shortest paths')
    print('') 
    for k in range(nArcs):
        print('        2 of 3: SP calc %i out of %i' %(k+1,nArcs))
        cL_k = cL[k]
        for i in range(nArcs):
            d_i_k = d[i][k]
            for j in range(nArcs):
                if d_i_k + d[k][j] + cL_k < d[i][j]:#If moving from arc i to arc j via arc k is shorter than moving directly from arc i to j:
                    #Note that we have to add the cost of traversing arc k
                    d[i][j] = d_i_k + d[k][j] + cL_k#Update distance from arc i to j
    
    print('')
    print('    3 of 3: Populating numpy array')
        
    print('')
    print('    Done: shortest path calculations')
    print('')
    
    print('')
    print('    Starting best IF calculations (1 procedure)')
    print('')
        
    nReqArcs = len(reqArcList)
    
    print('    1 of 3: Initialise matrices')

    d_c = np.ndarray(shape=(nReqArcs, nReqArcs), dtype=np.int16)
    d_req = np.ndarray(shape=(nReqArcs, nReqArcs), dtype=np.int16)
    d_req_ifc = np.ndarray(shape=(nReqArcs, nReqArcs), dtype=np.int16)
    d_req_if = np.ndarray(shape=(nReqArcs, nReqArcs), dtype=np.int16)
    
    for i in range(nReqArcs):
        i_req = reqArcList[i]
        for j in range(nReqArcs):
            j_req = reqArcList[j]
            d_c = d[i_req][j_req]
            d_req[i][j] = d_c

    print('    1 of 3: Calculate best IF')
    print('') 

    if IFarcsnewkey:
        nIfs = len(IFarcsnewkey)
        for i in range(nReqArcs):
            print('        2 of 3: Best IF calc %i out of %i' %(i+1,nReqArcs))
            k_if = IFarcsnewkey[0]
            visitCi = d_req[i][k_if]
            for j in range(nReqArcs):
                visitCj = d[k_if][j]
                d_req_ifc[i][j] = visitCi + dumpCost + visitCj
                d_req_if[i][j] = k_if
            
            for k in range(nIfs):
                k_if = IFarcsnewkey[k]
                visitCi = d_req[i][k_if]
                for j in range(nReqArcs):
                    visitCj = d[k_if][j]
                    visitT = visitCi + dumpCost + visitCj
                    if visitT < d_req_ifc[i][j]:
                        d_req_ifc[i][j] = visitT
                        d_req_if[i][j] = k_if
    
        print('')
        print('    3 of 3: Populating numpy array')
        
    print('')
    print('    Done: shortest path calculations')
    print('')
    print(nArcs, d[0, nArcs-1])
    return(d, d_req, d_req_ifc, d_req_if)


def spSource1List(piEst, origin, destination):
    '''
    Generate shortest path visitation list based on presidence dictionary, and 
    an origin and destination. 
    '''
    piEst = piEst[origin][:]
    pathList = [destination]
    a = destination
    while True:
        a = piEst[a]
        pathList.append(a)
        if a == origin: break
    pathList.reverse()
    return(pathList[1:-1])


def sp_full(p_full, origin, destination, full=False):
    """Returns the full shortest path between two vertices.

    Arg:
        info.p_full (n*n matrix): predecessor arc before v on the shortest path
            between arcs u and v.

        origin (int): origin arc from where the shortest path starts
        destination (int): destination arc where the shortest path ends.

    Kwarg:
        full (bool): whether the origin and destination arcs should be included
            in the shortest path

    Raises:
        AttributeError: when the destination arc cannot be reaced from the
            origin.

    Return:
        path (list): arc visitation sequence for the shortest path from the
            origin to destination arc. This means there is something wrong with
            the input data.
    """
    path = []
    p_origin = p_full[origin]
    n_arcs = len(p_origin)
    v = destination
    while True:
        v = p_origin[v]
        if v == origin: break
        path.insert(0, v)
        if len(path) == n_arcs:
            raise AttributeError('Destination `{0}` could not be reached from'
                                 '{1}'.format(destination, origin))

    return path

