'''
Created on 10 Aug 2012

@author: elias
'''

import numpy as np
from math import floor

def calc_neighbourhood_list(info):
    nArcs = len(info.d)
    nArcsFrac = 0.25
    nCutOff = int(floor(nArcs*nArcsFrac))
    d2 = np.empty((nArcs,nArcs),dtype='int32')
    neighbour_list_2 = np.ones((nArcs,nArcs),dtype='int32')*-1
    for i in xrange(nArcs):
        d2[i,:] = np.argsort(info.d[i,:])
        for j in xrange(nCutOff):
            neighbour_list_2[i,d2[i][j]] = 1
    return(neighbour_list_2)

def calc_neighbourhood_list2(info):
    nArcs = len(info.d)
    nArcsFrac = 1
    nCutOff = int(floor(nArcs*nArcsFrac))
    d2 = np.empty((nArcs,nArcs),dtype='int32')
    neighbour_list_2 = np.empty((nArcs,nCutOff),dtype='int32')
    for i in xrange(nArcs):
        d2[i,:] = np.argsort(info.d[i,:])
        neighbour_list_2[i,:] = d2[i,:nCutOff]
    return(neighbour_list_2)

def update_position(route_n, position_n, arc, i, j):
    route_n[arc] = i
    position_n[arc] = j
    return(route_n, position_n)  

def calc_arc_positions(info, solution):
    nArcs = len(info.d)
    route_n = [-1]*nArcs #np.ones((nArcs,1),dtype='int32')*-1
    position_n = [-1]*nArcs #np.ones((nArcs,1),dtype='int32')*-1
    for i in xrange(solution['nVehicles']):
        for j, arc in enumerate(solution[i]['Route'][1:-1]):
            (route_n, position_n) = update_position(route_n, position_n, arc, i, j)
            if info.reqInvArcList[arc]:
                (route_n, position_n) = update_position(route_n, position_n, info.reqInvArcList[arc], i, j)               
    return(route_n, position_n)

def calc_orient_list(info, routes):
    nArcsOrig = len(info.d)
    nArcs = nArcsOrig + len(routes)    
    orientation_list = [0]*nArcs
    for i, route in enumerate(routes):
        for j, arc in enumerate(route):
            orientation_list[arc] = 1
        orientation_list[nArcsOrig + i] = 1        
    return(orientation_list)

def calc_orient_list_changed(info, routes, routes_old):
    changed = []
    nArcsOrig = len(info.d)
    nArcs = nArcsOrig + len(routes)    
    orientation_list = [0]*nArcs
    for i, route in enumerate(routes):
        for j, arc in enumerate(route):
            orientation_list[arc] = 1
            if arc <> routes_old[i][j]: changed.append((arc, i, j))
        orientation_list[nArcsOrig + i] = 1        
    return(orientation_list, changed)

def calc_arc_positions2(info, solution):
    nArcsOrig = len(info.d)
    nArcs = nArcsOrig + len(solution[0])
    route_n = [-1]*nArcs
    position_n = [-1]*nArcs
    orientation_list = [0]*nArcs
    for i, route in enumerate(solution[0]):
        for j, arc in enumerate(route):
            (route_n, position_n) = update_position(route_n, position_n, arc, i, j)
            orientation_list[arc] = 1
            if info.reqInvArcList[arc]:
                (route_n, position_n) = update_position(route_n, position_n, info.reqInvArcList[arc], i, j)
        (route_n, position_n) = update_position(route_n, position_n, nArcsOrig + i, i, j + 1)
        orientation_list[nArcsOrig + i] = 1        
    return(route_n, position_n, orientation_list)

def calc_arc_positions3(info, solution, depot_dict):
    nArcsOrig = info.d.shape[0]
    nArcs = nArcsOrig + len(solution[0])
    route_n = [-1]*nArcs
    position_n = [-1]*nArcs
    orientation_list = [0]*nArcs
    for i, route in enumerate(solution[0]):
        for j, arc in enumerate(route):
            (route_n, position_n) = update_position(route_n, position_n, arc, i, j)
            orientation_list[arc] = 1
            if info.reqInvArcList[arc]:
                (route_n, position_n) = update_position(route_n, position_n, info.reqInvArcList[arc], i, j)
        route_i_end_arc = depot_dict[i]
        (route_n, position_n) = update_position(route_n, position_n, route_i_end_arc, i, j + 1)
        orientation_list[route_i_end_arc] = 1        
    return(route_n, position_n, orientation_list)

def calc_arc_positions_route_i(info, solution, route_i, route_n, position_n, orientation_list, depot_arc = None):
    nArcs = len(info.d)
    nArcs_in_route = len(solution[0][route_i])
    for j in xrange(nArcs_in_route):
        arc = solution[0][route_i][j]
        (route_n, position_n) = update_position(route_n, position_n, arc, route_i, j)
        orientation_list[arc] = 1
        inv_arc = info.reqInvArcList[arc]
        if inv_arc:
            (route_n, position_n) = update_position(route_n, position_n, inv_arc, route_i, j)
            orientation_list[inv_arc] = 0
    if not depot_arc:
        (route_n, position_n) = update_position(route_n, position_n, nArcs + route_i, route_i, j + 1)
        orientation_list[nArcs + route_i] = 1
    else: 
        (route_n, position_n) = update_position(route_n, position_n, depot_arc, route_i, j + 1)
        orientation_list[depot_arc] = 1
    #orientation_list[nArcs + route_i] = 1    
    return(route_n, position_n, orientation_list)