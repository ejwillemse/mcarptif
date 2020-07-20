#===============================================================================
# Floyd-Warshall algorithm adapted for Arc to Arc with Turn Penalties
# Creator: Elias Willemse (ejwillemse@gmail.com)

# Derived from the book:
# Cormen, T., Leiserson, C., Rivest, R. (1990). Introduction to algorithms 
# Chapter 26 pages 558-562.
#===============================================================================

import numpy as np
#cimport numpy as np

cimport libc.stdlib
from libc.stdlib cimport malloc, free 

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
#    print('')
#    print('Starting shortest path calculations (3 procedures)')
#    print('')
#
#    cdef int huge
#    
#    huge = 10000000# Infinity
#     
#    cdef int i, j, k, nArcs
#    cdef int **d_new
#    cdef int nSucs   
#    
#    nArcs = len(cL)
#    
#    d_np = np.ndarray(shape=(nArcs, nArcs), dtype=np.int16)
#    d = <int **>malloc(nArcs * sizeof(int *))
#
#    print('    1 of 3: Initialise matrices')
#    
#    for i from 0 <= i < nArcs:
#        d[i] = <int *>malloc(nArcs * sizeof(int *))
#
#    for i from 0 <= i < nArcs:
#        for j from 0 <= j < nArcs:
#            if i == j: d[i][j] = 0# Distance from an arc to itself is zeros    
#            else: d[i][j] == huge  
#        
#    for i from 0 <= i < nArcs:
#        d[i][i] = -1
#
#    for i from 0 <= i < nArcs:
#        sL_i = sL[i]
#        nSucs = len(sL_i)
#        for j in xrange(nSucs):
#            d[i][sL_i[j]] = -1
#            
#    cdef int cL_k, d_i_k
#
#    print('    2 of 3: Calculate shortest paths')
#    print('') 
#    for k from 0 <= k < nArcs:
#        print('        2 of 3: SP calc %i out of %i' %(k+1,nArcs))
#        cL_k = cL[k]
#        for i from 0 <= i < nArcs:
#            d_i_k = d[i][k]
#            for j from 0 <= j < nArcs:
#                if d_i_k + d[k][j] + cL_k < d[i][j]:#If moving from arc i to arc j via arc k is shorter than moving directly from arc i to j:
#                    #Note that we have to add the cost of traversing arc k
#                    d[i][j] = d_i_k + d[k][j] + cL_k#Update distance from arc i to j
#    
#    print('')
#    print('    3 of 3: Populating numpy array')
#    
#    for i from 0 <= i < nArcs:
#        for j from 0 <= j < nArcs:
#            d_np[i,j] = d[i][j]
#    
#    for i from 0 <= i < nArcs:
#        free(d[i])
#        
#    free(d); 
#    
#    print('')
#    print('    Done: shortest path calculations')
#    print('')
#    
#    return(d_np)

def SP_IFs(cL, sL, reqArcList, dumpCost, depotArc, IFarcsnewkey = None):
    '''
    Addaptation of the Floyd Warshall algorithm for computing arc to 
    arc shortest paths, instead of node to node. Combined with calculating
    best IFs to visit.
    '''
    
    print('')
    print('Starting shortest path calculations (3 procedures)')
    print('')

    huge = 1000000# Infinity
     
    cdef int i, j, k, nArcs
    cdef int **d
    cdef int nSucs   
    
    nArcs = len(cL)
    
    #d_np = np.ndarray(shape=(nArcs, nArcs), dtype=np.int16)
    d = <int **>malloc(nArcs * sizeof(int *))

    print('    1 of 3: Initialise matrices')
    
    for i from 0 <= i < nArcs:
        d[i] = <int *>malloc(nArcs * sizeof(int *))

    for i from 0 <= i < nArcs:
        for j from 0 <= j < nArcs:
            if i == j: d[i][j] = 0# Distance from an arc to itself is zero   
            else: d[i][j] = huge
            
    #for i from 0 <= i < nArcs:
    #    d[i][j] = 0 #Distance from all arcs to last arc is zero????
    
    for i from 0 <= i < nArcs:
        sL_i = sL[i]
        nSucs = len(sL_i)
        for j in xrange(nSucs):
            d[i][sL_i[j]] = 0          

    cdef int cL_k, d_i_k

    print('    2 of 3: Calculate shortest paths')
    print('') 
    for k from 0 <= k < nArcs:
        print('        2 of 3: SP calc %i out of %i' %(k+1,nArcs))
        cL_k = cL[k]
        for i from 0 <= i < nArcs:
            d_i_k = d[i][k]
            for j from 0 <= j < nArcs:
                if d_i_k + d[k][j] + cL_k < d[i][j]:#If moving from arc i to arc j via arc k is shorter than moving directly from arc i to j:
                    #Note that we have to add the cost of traversing arc k
                    d[i][j] = d_i_k + d[k][j] + cL_k#Update distance from arc i to j
    
    print('')
    print('    3 of 3: Populating numpy array')

    d_np = []
    for i from 0 <= i < nArcs:
        d_np.append([0]*nArcs)
        for j from 0 <= j < nArcs:
            d_np[i][j] = d[i][j]
 
    print('')
    print('    Done: shortest path calculations')
    print('')
    
    print('')
    print('    Starting best IF calculations (1 procedure)')
    print('')
    
    cdef int nReqArcs, nIFs, k_if, i_req, j_req, d_c, visitCi, visitCj, visitT
    
    nReqArcs = len(reqArcList)
    
    print('    1 of 3: Initialise matrices')

    d_np_req = []
    if_np_req = []
    ifc_np_req = []
    
    d_req = <int **>malloc(nReqArcs * sizeof(int *))
    d_req_ifc = <int **>malloc(nReqArcs * sizeof(int *))
    d_req_if = <int **>malloc(nReqArcs * sizeof(int *))
    
    for i from 0 <= i < nReqArcs:
        d_req[i] = <int *>malloc(nReqArcs * sizeof(int *))
        d_req_ifc[i] = <int *>malloc(nReqArcs * sizeof(int *))
        d_req_if[i] = <int *>malloc(nReqArcs * sizeof(int *))

    for i from 0 <= i < nReqArcs:
        i_req = reqArcList[i]
        d_np_req.append([0]*nReqArcs)
        for j from 0 <= j < nReqArcs:
            j_req = reqArcList[j]
            d_c = d[i_req][j_req]
            d_req[i][j] = d_c
            d_np_req[i][j] = d_c

    print('    1 of 3: Calculate best IF')
    print('') 

    if IFarcsnewkey:
        nIfs = len(IFarcsnewkey)
        for j from 0 <= j < nReqArcs:
            d_req_ifc[0][j] = d_req[0][j]
            d_req_if[0][j] = 0                
        print('')
        for i from 0 <= i < nReqArcs:
            print('        2 of 3: Best IF calc %i out of %i' %(i+1,nReqArcs))
            k_if = IFarcsnewkey[0]
            visitCi = d_req[i][k_if]
            for j from 0 <= j < nReqArcs:
                d_req_ifc[i][j] = huge
                for k from 0 <= k < nIfs:
                    k_if = IFarcsnewkey[k]
                    visitCi = d_req[i][k_if]
                    visitCj = d_req[k_if][j]
                    visitT = visitCi + dumpCost + visitCj               
                    if visitT < d_req_ifc[i][j]:
                        d_req_ifc[i][j] = visitT
                        d_req_if[i][j] = k_if                
        print('')
        print('    3 of 3: Populating numpy array')
    
        for i from 0 <= i < nReqArcs:
            ifc_np_req.append([0]*nReqArcs)
            if_np_req.append([0]*nReqArcs)
            for j from 0 <= j < nReqArcs:
                ifc_np_req[i, j] = d_req_ifc[i][j]
                if_np_req[i, j] = d_req_if[i][j]

    print('')
    print('    Done: shortest path calculations')
    print('')

    
    for i from 0 <= i < nArcs:
        free(d[i])
    free(d)
    
    for i from 0 <= i < nReqArcs:
        free(d_req[i])
        free(d_req_ifc[i])
        free(d_req_if[i])
        
    free(d_req)
    free(d_req_ifc)
    free(d_req_if)
    
    p_np = None
    
    return(d_np, p_np, d_np_req, ifc_np_req, if_np_req)

def SP_IFs_complete(cL, sL, reqArcList, dumpCost, depotArc, IFarcsnewkey = None):
    '''
    Addaptation of the Floyd Warshall algorithm for computing arc to 
    arc shortest paths, instead of node to node. Combined with calculating
    best IFs to visit.
    '''
    
    print('')
    print('Starting shortest path calculations (3 procedures)')
    print('')

    huge = 1000000# Infinity
     
    cdef int i, j, k, nArcs
    cdef int **d, **p
    cdef int nSucs   
    
    nArcs = len(cL)
    
    d_np = []
    p_np = []
    d = <int **>malloc(nArcs * sizeof(int *))
    p = <int **>malloc(nArcs * sizeof(int *))

    print('    1 of 3: Initialise matrices')
    
    for i from 0 <= i < nArcs:
        d[i] = <int *>malloc(nArcs * sizeof(int *))
        p[i] = <int *>malloc(nArcs * sizeof(int *))

    for i from 0 <= i < nArcs:
        for j from 0 <= j < nArcs:
            if i == j: 
                d[i][j] = 0# Distance from an arc to itself is zero   
                p[i][j] = 0
            else: 
                d[i][j] = huge
                p[i][j] = -1
            
#    for i from 0 <= i < nArcs:
#        d[i][j] = 0
    
    for i from 0 <= i < nArcs:
        sL_i = sL[i]
        nSucs = len(sL_i)
        for j in xrange(nSucs):
            d[i][sL_i[j]] = 0
            p[i][sL_i[j]] = i          

    cdef int cL_k, d_i_k

    print('    2 of 3: Calculate shortest paths')
    print('') 
    for k from 0 <= k < nArcs:
        print('        2 of 3: SP calc %i out of %i' %(k+1,nArcs))
        cL_k = cL[k]
        for i from 0 <= i < nArcs:
            d_i_k = d[i][k]
            for j from 0 <= j < nArcs:
                if d_i_k + d[k][j] + cL_k < d[i][j]:#If moving from arc i to arc j via arc k is shorter than moving directly from arc i to j:
                    #Note that we have to add the cost of traversing arc k
                    d[i][j] = d_i_k + d[k][j] + cL_k#Update distance from arc i to j
                    p[i][j] = p[k][j]
    
    print('')
    print('    3 of 3: Populating numpy array')

    for i from 0 <= i < nArcs:
        d_np.append([0]*nArcs)
        p_np.append([0]*nArcs)
        for j from 0 <= j < nArcs:
            d_np[i][j] = d[i][j]
            p_np[i][j] = p[i][j]
            if d[i][j] < 0: 
                print('ERROR')
                a = input('')
            if d_np[i][j] < 0:
                print('ERROR', i,j, d[i][j], d_np[i,j])
                a = input('')               
 
    print('')
    print('    Done: shortest path calculations')
    print('')
    
    print('')
    print('    Starting best IF calculations (1 procedure)')
    print('')
    
    cdef int nReqArcs, nIFs, k_if, i_req, j_req, d_c, visitCi, visitCj, visitT
    
    nReqArcs = len(reqArcList)
    
    print('    1 of 3: Initialise matrices')

    d_np_req = []
    if_np_req = []
    ifc_np_req = []
    
    d_req = <int **>malloc(nReqArcs * sizeof(int *))
    d_req_ifc = <int **>malloc(nReqArcs * sizeof(int *))
    d_req_if = <int **>malloc(nReqArcs * sizeof(int *))
    
    for i from 0 <= i < nReqArcs:
        d_req[i] = <int *>malloc(nReqArcs * sizeof(int *))
        d_req_ifc[i] = <int *>malloc(nReqArcs * sizeof(int *))
        d_req_if[i] = <int *>malloc(nReqArcs * sizeof(int *))

    for i from 0 <= i < nReqArcs:
        i_req = reqArcList[i]
        d_np_req.append([0]*nReqArcs)
        for j from 0 <= j < nReqArcs:
            j_req = reqArcList[j]
            d_c = d[i_req][j_req]
            d_req[i][j] = d_c
            d_np_req[i][j] = d_c


    print('    1 of 3: Calculate best IF')
    print('') 

    if IFarcsnewkey:
        nIfs = len(IFarcsnewkey)
        for j from 0 <= j < nReqArcs:
            d_req_ifc[0][j] = d_req[0][j]
            d_req_if[0][j] = 0                
        print('')
        for i from 0 <= i < nReqArcs:
            print('        2 of 3: Best IF calc %i out of %i' %(i+1,nReqArcs))
            k_if = IFarcsnewkey[0]
            visitCi = d_req[i][k_if]
            for j from 0 <= j < nReqArcs:
                d_req_ifc[i][j] = huge
                for k from 0 <= k < nIfs:
                    k_if = IFarcsnewkey[k]
                    visitCi = d_req[i][k_if]
                    visitCj = d_req[k_if][j]
                    visitT = visitCi + dumpCost + visitCj               
                    if visitT < d_req_ifc[i][j]:
                        d_req_ifc[i][j] = visitT
                        d_req_if[i][j] = k_if                
        print('')
        print('    3 of 3: Populating numpy array')
    
        for i from 0 <= i < nReqArcs:
            ifc_np_req.append([0]*nReqArcs)
            if_np_req.append([0]*nReqArcs)
            for j from 0 <= j < nReqArcs:
                ifc_np_req[i][j] = d_req_ifc[i][j]
                if_np_req[i][j] = d_req_if[i][j]

    print('')
    print('    Done: shortest path calculations')
    print('')
 
    for i from 0 <= i < nArcs:
        free(d[i])
        free(p[i])
    free(d)
    free(p)
    
    for i from 0 <= i < nReqArcs:
        free(d_req[i])
        free(d_req_ifc[i])
        free(d_req_if[i])
        
    free(d_req)
    free(d_req_ifc)
    free(d_req_if)
    
    return(d_np, p_np, d_np_req, ifc_np_req, if_np_req)

def SP_IFs_complete2(cL, sL, reqArcList, dumpCost, depotArc, IFarcsnewkey = None):
    '''
    Addaptation of the Floyd Warshall algorithm for computing arc to 
    arc shortest paths, instead of node to node. Combined with calculating
    best IFs to visit.
    '''
    
    print('')
    print('Starting shortest path calculations (3 procedures)')
    print('')
   
    huge = 10000000# Infinity
     
    cdef int i, j, k, nArcs
    cdef int **d, **p
    cdef int nSucs   
    
    nArcs = len(cL)
    
    d_np = np.ndarray(shape=(nArcs, nArcs), dtype=np.int16)
    p_np = np.ndarray(shape=(nArcs, nArcs), dtype=np.int16)
    d = <int **>malloc(nArcs * sizeof(int *))
    p = <int **>malloc(nArcs * sizeof(int *))
    
    print('    1 of 3: Initialise matrices')
    
    for i from 0 <= i < nArcs:
        d[i] = <int *>malloc(nArcs * sizeof(int *))
        p[i] = <int *>malloc(nArcs * sizeof(int *))
        
    for i from 0 <= i < nArcs:
        for j from 0 <= j < nArcs:
            if i == j: 
                d[i][j] = 0# Distance from an arc to itself is zeros    
                p[i][j] = 0
            else: d[i][j] == huge  
        
    for i from 0 <= i < nArcs:
        d[i][i] = -1

    for i from 0 <= i < nArcs:
        sL_i = sL[i]
        nSucs = len(sL_i)
        for j in xrange(nSucs):
            d[i][sL_i[j]] = -1
            p[i][sL_i[j]] = i
                  
    cdef int cL_k, d_i_k

    print('    2 of 3: Calculate shortest paths')
    print('') 
    for k from 0 <= k < nArcs:
        print('        2 of 3: SP calc %i out of %i' %(k+1,nArcs))
        cL_k = cL[k]
        for i from 0 <= i < nArcs:
            d_i_k = d[i][k]
            for j from 0 <= j < nArcs:
                if d_i_k + d[k][j] + cL_k < d[i][j]:#If moving from arc i to arc j via arc k is shorter than moving directly from arc i to j:
                    #Note that we have to add the cost of traversing arc k
                    d[i][j] = d_i_k + d[k][j] + cL_k#Update distance from arc i to j
                    p[i][j] = p[k][j]
    
    print('')
    print('    3 of 3: Populating numpy array')
    
    for i from 0 <= i < nArcs:
        for j from 0 <= j < nArcs:
            d_np[i,j] = d[i][j]
            p_np[i,j] = p[i][j]
        
    print('')
    print('    Starting best IF calculations (1 procedure)')
    print('')
    
    cdef int nReqArcs, nIFs, k_if, i_req, j_req, d_c, visitCi, visitCj, visitT
    
    nReqArcs = len(reqArcList)
    
    print('    1 of 3: Initialise matrices')

    d_np_req = np.ndarray(shape=(nReqArcs, nReqArcs), dtype=np.int16)
    if_np_req = np.ndarray(shape=(nReqArcs, nReqArcs), dtype=np.int16)
    ifc_np_req = np.ndarray(shape=(nReqArcs, nReqArcs), dtype=np.int16)
    
    d_req = <int **>malloc(nReqArcs * sizeof(int *))
    d_req_ifc = <int **>malloc(nReqArcs * sizeof(int *))
    d_req_if = <int **>malloc(nReqArcs * sizeof(int *))
    
    for i from 0 <= i < nReqArcs:
        d_req[i] = <int *>malloc(nReqArcs * sizeof(int *))
        d_req_ifc[i] = <int *>malloc(nReqArcs * sizeof(int *))
        d_req_if[i] = <int *>malloc(nReqArcs * sizeof(int *))

    for i from 0 <= i < nReqArcs:
        i_req = reqArcList[i]
        for j from 0 <= j < nReqArcs:
            j_req = reqArcList[j]
            d_c = d[i_req][j_req]
            d_req[i][j] = d_c
            d_np_req[i, j] = d_c


    print('    1 of 3: Calculate best IF')
    print('') 

    if IFarcsnewkey:
        nIfs = len(IFarcsnewkey)
        for j from 0 <= j < nReqArcs:
            d_req_ifc[0][j] = d_req[0][j]
            d_req_if[0][j] = 0                
        print('')
        for i from 1 <= i < nReqArcs:
            print('        2 of 3: Best IF calc %i out of %i' %(i+1,nReqArcs))
            k_if = IFarcsnewkey[0]
            visitCi = d_req[i][k_if]
            for j from 0 <= j < nReqArcs:
                d_req_ifc[i][j] = huge
                for k from 0 <= k < nIfs:
                    k_if = IFarcsnewkey[k]
                    visitCi = d_req[i][k_if]
                    visitCj = d_req[k_if][j]
                    visitT = visitCi + dumpCost + visitCj               
                    if visitT < d_req_ifc[i][j]:
                        d_req_ifc[i][j] = visitT
                        d_req_if[i][j] = k_if                
        print('')
        print('    3 of 3: Populating numpy array')
    
        for i from 0 <= i < nReqArcs:
            for j from 0 <= j < nReqArcs:
                ifc_np_req[i, j] = d_req_ifc[i][j]
                if_np_req[i, j] = d_req_if[i][j]

    print('')
    print('    Done: shortest path calculations')
    print('')

    
    for i from 0 <= i < nArcs:
        free(d[i])
        free(p[i])
    free(d)
    free(p)
    
    for i from 0 <= i < nReqArcs:
        free(d_req[i])
        free(d_req_ifc[i])
        free(d_req_if[i])
        
    free(d_req)
    free(d_req_ifc)
    free(d_req_if)
    
    return(d_np, p_np, d_np_req, ifc_np_req, if_np_req)

