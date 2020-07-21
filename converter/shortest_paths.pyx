#cython: language_level=3
#cython: boundscheck=False
#cython: cython.wraparound=False

#===============================================================================
# Floyd-Warshall algorithm adapted for Arc to Arc with Turn Penalties
# Creator: Elias Willemse (ejwillemse@gmail.com)

# Two options, a C version, straight out of the box, and a pytables option,
# for very large distance matrices.

# Derived from the book:
# Cormen, T., Leiserson, C., Rivest, R. (1990). Introduction to algorithms
# Chapter 26 pages 558-562.
#===============================================================================
cimport cython
import numpy as np
cimport numpy as np
from numpy import int32
from numpy cimport int32_t

from libc.stdlib cimport malloc, free
import logging

ctypedef np.int_t DTYPE_t


def SP(cL, sL, huge=None):
    '''
    Adaptation of the Floyd Warshall algorithm for computing arc to
    arc shortest paths, instead of node to node. Combined with calculating
    best IFs to visit.
    '''

    logging.info('Starting shortest path calculations (3 procedures)')

    if huge is None:
        huge = 1000000# Infinity

    cdef int i, j, k, nArcs
    cdef int **d, **p
    cdef int nSucs

    nArcs = len(cL)

    d = <int **>malloc(nArcs * sizeof(int *))
    p = <int **>malloc(nArcs * sizeof(int *))

    d_np = np.ndarray(shape=(nArcs, nArcs), dtype=np.int32)
    p_np = np.ndarray(shape=(nArcs, nArcs), dtype=np.int32)

    logging.info('1 of 3: Initialise matrices')

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
        # push


#    for i from 0 <= i < nArcs:
#        d[i][j] = 0

    for i from 0 <= i < nArcs:
        sL_i = sL[i]
        nSucs = len(sL_i)
        for j in xrange(nSucs):
            d[i][sL_i[j]] = 0
            p[i][sL_i[j]] = i

    cdef int cL_k, d_i_k

    logging.info('2 of 3: Calculate shortest paths')
    
    for k from 0 <= k < nArcs:
        logging.debug('2 of 3: SP calc %i out of %i' %(k+1,nArcs))
        cL_k = cL[k]
        for i from 0 <= i < nArcs:
            d_i_k = d[i][k]
            for j from 0 <= j < nArcs:
                if d_i_k + d[k][j] + cL_k < d[i][j]:#If moving from arc i to arc j via arc k is shorter than moving directly from arc i to j:
                    #Note that we have to add the cost of traversing arc k
                    d[i][j] = d_i_k + d[k][j] + cL_k#Update distance from arc i to j
                    p[i][j] = p[k][j]
            # can update distance array here and store i, j, k values,
            # if it crashes above this point, it's fine since it will
            # restart this calc in any case.

    logging.info('3 of 3: Populating numpy array')

    for i from 0 <= i < nArcs:
        for j from 0 <= j < nArcs:
            d_np[i][j] = d[i][j]
            p_np[i][j] = p[i][j]
            if d[i][j] < 0:
                logging.info('ERROR')
                a = input('')
            if p[i][j] < 0:
                raise ValueError('Not all paths calculated: i {} j {} d {}'.format(i,j, d[i][j]))

    logging.info('    Done: shortest path calculations')

    for i from 0 <= i < nArcs:
        free(d[i])
        free(p[i])
    free(d)
    free(p)

    return d_np, p_np


def SP_pytable(arc_cost,
               arc_successor_index_list,
               cost_matrix,
               predecessor_matrix,
               huge=None):
    '''
    Adaptation of the Floyd Warshall algorithm for computing arc to
    arc shortest paths, instead of node to node. Combined with calculating
    best IFs to visit.

    Arg:
        arc_cost (list int): cost of traversing arc
        arc_successor_index_list (array <array>): multi-dimensional array
            of successor arc index of arc i
        cost_matrix (pytable.carray): carray to which the cost matrix info
            will be written.
        predecessor_matrix (pytable.carray): carray to which the predecessor
            into will be written.
    '''

    logging.info('Starting shortest path calculations (3 procedures)')

    if huge is None:
        huge = 1000000# Infinity

    cdef int i, j, k, nArcs
    cdef int **d, **p
    cdef int nSucs

    nArcs = len(arc_cost)

    d = <int **>malloc(nArcs * sizeof(int *))
    p = <int **>malloc(nArcs * sizeof(int *))

    arc_cost = list(arc_cost)
    arc_successor_index_list = list(arc_successor_index_list)

    logging.info('1 of 3: Initialise matrices')

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

    for i from 0 <= i < nArcs:
        sL_i = arc_successor_index_list[i]
        nSucs = len(sL_i)
        for j in xrange(nSucs):
            d[i][sL_i[j]] = 0
            p[i][sL_i[j]] = i

    cdef int cL_k, d_i_k

    logging.info('2 of 3: Calculate shortest paths')

    for k from 0 <= k < nArcs:
        logging.debug('2 of 3: SP calc %i out of %i' %(k+1,nArcs))
        cL_k = arc_cost[k]
        for i from 0 <= i < nArcs:
            d_i_k = d[i][k]
            for j from 0 <= j < nArcs:
                if d_i_k + d[k][j] + cL_k < d[i][j]:#If moving from arc i to arc j via arc k is shorter than moving directly from arc i to j:
                    #Note that we have to add the cost of traversing arc k
                    d[i][j] = d_i_k + d[k][j] + cL_k#Update distance from arc i to j
                    p[i][j] = p[k][j]
            # can update distance array here and store i, j, k values,
            # if it crashes above this point, it's fine since it will
            # restart this calc in any case.

    logging.info('3 of 3: Writing outputs to pytable')

    d_np = np.ndarray(shape=(nArcs, nArcs), dtype=np.int32)
    p_np = np.ndarray(shape=(nArcs, nArcs), dtype=np.int32)

    for i from 0 <= i < nArcs:
        for j from 0 <= j < nArcs:
            d_np[i, j] = d[i][j]
            p_np[i, j] = p[i][j]
            if d[i][j] < 0:
                logging.warning('Not all paths calculated: i {} j '
                                          '{} d {}'.format(i,j, d[i][j]))
            if p[i][j] < 0:
                logging.warning('Not all paths calculated: i {} j {} d {}'.format(i,j, d[i][j]))
        cost_matrix[i, :] = d_np[i, :]
        predecessor_matrix[i, :] = p_np[i, :]

    logging.info('Done: shortest path calculations')

    for i from 0 <= i < nArcs:
        free(d[i])
        free(p[i])
    free(d)
    free(p)
