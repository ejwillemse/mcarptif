'''
Created on 01 Oct 2011

@author: elias
'''
import numpy as np
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
    if full: 
        if_cost_old = info.if_cost_np
        maxTrip_old = info.maxTrip
    else:
        maxTrip_old = 100000
    service_old = info.serveCostL
    
    global d, nArcs, depot, inv_list, demand, capacity, dumpCost, if_cost, maxTrip, service
    
    nArcs = len(d_old)
    d = <int **>malloc(nArcs * sizeof(int *))
    if full: if_cost = <int **>malloc(nArcs * sizeof(int *))
    inv_list = inv_list_old #< int *>malloc(nArcs * sizeof(int *))
    demand = < int *>malloc(nArcs * sizeof(int *)) 
    service = < int *>malloc(nArcs * sizeof(int *))
    depot = depot_old
    capacity = capacity_old
    dumpCost = dumpCostOld
    maxTrip = maxTrip_old
    if full: 
        for i from 0 <= i < nArcs:
            d[i] = <int *>malloc(nArcs * sizeof(int *))
            if_cost[i] = <int *>malloc(nArcs * sizeof(int *))
            demand[i] = demand_old[i]
            service[i] = service_old[i]
            
        for i from 0 <= i < nArcs:
            for j from 0 <= j < nArcs:
                d[i][j] = d_old[i][j]
                if_cost[i][j] = if_cost_old[i][j]
    else:
        for i from 0 <= i < nArcs:
            d[i] = <int *>malloc(nArcs * sizeof(int *))
            demand[i] = demand_old[i]
            service[i] = service_old[i]
            
        for i from 0 <= i < nArcs:
            for j from 0 <= j < nArcs:
                d[i][j] = d_old[i][j]       

def free_input(full):
    if full: 
        for i from 0 <= i < nArcs:
            free(d[i])
            free(if_cost[i])
        free(d)
        free(if_cost)
        free(demand)
        free(service)
    else:
        for i from 0 <= i < nArcs:
            free(d[i])
        free(d)
        free(demand)
        free(service)

def findnearestarcs_sub1(previousarc, unservedarcs):
    '''
    Find nearest arc without taking capacity and maxtrip into consideration. New comments
    '''
    
    cdef int nReqArcs, nextarc, disttoarc, i, j
    cdef double nearest
    
    nearest = huge
    nearestarcs = []
    
    nReqArcs = len(unservedarcs)
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = d[previousarc][nextarc]
        if disttoarc < nearest:
            nearest = disttoarc
            nearestarcs = [nextarc]
        elif disttoarc == nearest:
            nearestarcs.append(nextarc)
    
    return(nearestarcs, nearest)

def testload(arc, tripload):
    '''
    Test if an arc can be added without exceeding vehicle capacity.
    '''
    if (tripload + demand[arc]) <= capacity:
        return(True)
    else: return(False)
    
def testtriplimit(arc, arcdist, routecost):
    '''
    Test if an arc can be added without exceeding max trip length.
    '''
    if (routecost + arcdist + service[arc] + if_cost[arc][depot]) <= maxTrip:
        return(True)
    else: return(False)

def testtriplimit_est(arc, arcdist, routecost, estimate_if_cost):
    '''
    Test if an arc can be added without exceeding max trip length.
    '''
    if (routecost + arcdist + service[arc] + if_cost[arc][depot] + estimate_if_cost) <= maxTrip:
        return(True)
    else: return(False)

def checknearestarcs(nearestarcs, arcdist, tripload, routecost):
    '''
    Check which nearest arcs does not exceed capacity and maxtrip restrictions.
    '''
    cdef int nReqArcs
    nextarcfine = []
    nReqArcs = len(nearestarcs)
    for i from 0 <= i < nReqArcs:
        arc = nearestarcs[i]
        if (testload(arc, tripload) == True) & (testtriplimit(arc, arcdist, routecost) == True): 
            nextarcfine.append(arc)
    return(nextarcfine)

def checknearestarcs_noload(nearestarcs, arcdist, tripload, routecost, estimate_if_cost):
    '''
    Check which nearest arcs does not exceed capacity and maxtrip restrictions.
    '''
    cdef int nReqArcs
    nextarcfine = []
    nReqArcs = len(nearestarcs)
    for i from 0 <= i < nReqArcs:
        arc = nearestarcs[i]
        if testtriplimit_est(arc, arcdist, routecost, estimate_if_cost):
            nextarcfine.append(arc)
    return(nextarcfine)

def findnearestarcs(previousarc,  unservedarcs, tripload, routecost):
    '''
    Find the nearest servisable arc, while taking 
    into account load and maxtrip restrictions.
    '''
    cdef int nReqArcs, nextarc, disttoarc, i
    cdef double nearest
    
    nearest = huge
    nearestarcs = []
    
    nReqArcs = len(unservedarcs)
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = d[previousarc][nextarc]
            
        if disttoarc <= nearest:
        
            loadflag = testload(nextarc, tripload)
            triplimitflag = testtriplimit(nextarc, disttoarc, routecost)
            
            if (loadflag == True) & (triplimitflag == True):
                if disttoarc < nearest:
                    nearest = disttoarc
                    nearestarcs = [nextarc]
                elif disttoarc == nearest:
                    nearestarcs.append(nextarc)           
                
    return(nearestarcs, nearest)

def findnearestarcs_elipse(previousarc, unservedarcs, tripload, routecost, _tc, _ned):
    '''
    Find the nearest servisable arc, while taking 
    into account load and maxtrip restrictions.
    '''
    
    cdef int nReqArcs, nextarc, disttoarc, i
    cdef double nearest
    
    nearest = huge
    nearestarcs = []

    disttodepot_direct = if_cost[previousarc][depot]
    k = 0
    
    nReqArcs = len(unservedarcs)
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = d[previousarc][nextarc]
        serveC = service[nextarc]
        disttodepot = if_cost[nextarc][depot]
        if (disttoarc + serveC + disttodepot) <= (_tc/float(_ned) + disttodepot_direct):
            k += 1
            if disttoarc <= nearest:
                loadflag = testload(nextarc, tripload)
                triplimitflag = testtriplimit(nextarc, disttoarc, routecost)
                if (loadflag == True) & (triplimitflag == True):
                    if disttoarc < nearest:
                        nearest = disttoarc
                        nearestarcs = [nextarc]
                    elif disttoarc == nearest:
                        nearestarcs.append(nextarc)
  
    return(nearestarcs, nearest, k)

def findnearestarcs_cap_elipse(previousarc, unservedarcs, tripload, routecost, _tc, _ned, IFarcsnewkey):
    '''
    Find the nearest servisable arc, while taking 
    into account load and maxtrip restrictions.
    '''
    cdef int nReqArcs, nextarc, disttoarc, i
    cdef double nearest
    
    nearest = huge
    nearestarcs = []
    disttodepot_direct = huge
    
    for i in IFarcsnewkey:
        if d[previousarc][i] < disttodepot_direct:
            if_k = i
            disttodepot_direct = d[previousarc][i]
    
    k = 0
    
    nReqArcs = len(unservedarcs)
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = d[previousarc][nextarc]
        serveC = service[nextarc]
        disttodepot = d[nextarc][if_k]
        if (disttoarc + serveC + disttodepot) <= (_tc/float(_ned) + disttodepot_direct):
            k += 1
            if disttoarc <= nearest:
                loadflag = testload(nextarc, tripload)
                triplimitflag = testtriplimit(nextarc, disttoarc, routecost)
                if (loadflag == True) & (triplimitflag == True):
                    if disttoarc < nearest:
                        nearest = disttoarc
                        nearestarcs = [nextarc]
                    elif disttoarc == nearest:
                        nearestarcs.append(nextarc)
  
    return(nearestarcs, nearest, k) 

def findnearestIFarcs_elipse(previousarc, unservedarcs, tripload, routecost, _tc, _ned, inc_frac):
    '''
    Find the nearest servisable arc, while taking 
    into account load and maxtrip restrictions.
    '''
    
    cdef int nReqArcs, nextarc, disttoarc, i
    cdef double nearest
    
    nearest = huge
    nearestarcs = []

    disttodepot_direct = if_cost[previousarc][depot]
    k = 0
    
    nReqArcs = len(unservedarcs)
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = if_cost[previousarc][nextarc]
        serveC = service[nextarc]
        disttodepot = if_cost[nextarc][depot]
        if (disttoarc + serveC + disttodepot) <= inc_frac*(_tc/float(_ned) + disttodepot_direct):
            k += 1
            if disttoarc <= nearest:
                triplimitflag = testtriplimit(nextarc, disttoarc, routecost)
                if triplimitflag == True:
                    if disttoarc < nearest:
                        nearest = disttoarc
                        nearestarcs = [nextarc]
                    elif disttoarc == nearest:
                        nearestarcs.append(nextarc)
  
    return(nearestarcs, nearest, k)

def findnearestarcs_noload(previousarc,  unservedarcs, tripload, routecost, estimate_if_cost):
    '''
    Find the nearest servisable arc, while taking 
    into account load and maxtrip restrictions.
    '''
    cdef int nReqArcs, nextarc, disttoarc, i
    cdef double nearest
    
    nearest = huge
    nearestarcs = []
    
    nReqArcs = len(unservedarcs)
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = d[previousarc][nextarc]
            
        if disttoarc <= nearest:
            triplimitflag = testtriplimit_est(nextarc, disttoarc, routecost, estimate_if_cost)
            if (triplimitflag == True):
                if disttoarc < nearest:
                    nearest = disttoarc
                    nearestarcs = [nextarc]
                elif disttoarc == nearest:
                    nearestarcs.append(nextarc)           
    return(nearestarcs, nearest)

def findnearestarcs_nolimit(previousarc, unservedarcs, tripload):
    '''
    Find nearest servisable arc while only taking capacity into consideration.
    Used with classical CARP.
    '''
    cdef int nReqArcs, nextarc, disttoarc, i
    cdef double nearest
    
    nearest = huge
    nearestarcs = []
    
    nReqArcs = len(unservedarcs)
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = d[previousarc][nextarc]
        
        if disttoarc <= nearest:
            
            loadflag = testload(nextarc, tripload)
            if loadflag:
                if disttoarc < nearest:
                    nearest = disttoarc
                    nearestarcs = [nextarc]
                else:nearestarcs.append(nextarc)
    return(nearestarcs, nearest)

def findnearestarcs_nolimit_elipse(previousarc, unservedarcs, tripload, _tc, _ned):
    '''
    Find nearest servisable arc while only taking capacity and elipse rule into consideration.
    Used with classical CARP.
    '''
    cdef int nReqArcs, nextarc, disttoarc, i, disttodepot, disttodepot_direct, serveC
    cdef double nearest
    
    nearest = huge
    nearestarcs = []
    disttodepot_direct = d[previousarc][depot]
    nReqArcs = len(unservedarcs)
    k = 0
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = d[previousarc][nextarc]
        disttodepot = d[nextarc][depot]
        serveC = service[nextarc]
        if (disttoarc + serveC + disttodepot) <= (_tc/float(_ned) + disttodepot_direct):
            k += 1
            if disttoarc <= nearest:
                loadflag = testload(nextarc, tripload)
                if (loadflag == True):
                    if disttoarc < nearest:
                        nearest = disttoarc
                        nearestarcs = [nextarc]
                    else:
                        nearestarcs.append(nextarc)           
            
    return(nearestarcs, nearest, k)


def findnearestIFarcs(previousarc, unservedarcs, tripload, routecost):
    '''
    Find the nearest servisable arc that can be serviced after 
    visiting a dumpsite while taking maxtrip restriction into account
    '''
    cdef int nReqArcs, nextarc, disttoarc, i
    cdef double nearest
    
    nearest = huge
    nearestarcs = []
    
    nReqArcs = len(unservedarcs)
    for i from 0 <= i < nReqArcs:
        nextarc = unservedarcs[i]
        disttoarc = if_cost[previousarc][nextarc]
        if disttoarc <= nearest:
        
            triplimitflag = testtriplimit(nextarc, disttoarc, routecost)    
            if triplimitflag:
                if disttoarc < nearest:
                    nearest = disttoarc
                    nearestarcs = [nextarc]
                elif disttoarc == nearest:
                    nearestarcs.append(nextarc)           
            
    return(nearestarcs, nearest)


    