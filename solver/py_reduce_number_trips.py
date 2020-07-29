'''
Created on 28 Jan 2012

@author: elias
'''
from math import ceil
from copy import deepcopy
import numpy as np

from solver.py_solution_builders import build_CARP_list
from solver.py_solution_builders import build_CLARPIF_list
from solver.py_solution_builders import build_CARP_dict_from_list
from solver.py_solution_builders import build_CLARPIF_dict_from_list
from solver.py_display_solution import display_solution_stats
from solver.py_route_modifier import insert_multiple_arcs

from solver.py_solution_test  import test_solution # From Dev_SolutionOperators

class Reduce_Trips(object):
    
    def __init__(self, info):
        self.info = info
        self.capacity = info.capacity
        self.insert_multiple_arcs = insert_multiple_arcs(info)
        self.serviceL = info.serveCostL
        self.demandL = info.demandL
        self.depot = info.depotnewkey
        self.maxTrip = info.maxTrip
        self.if_arc = info.if_arc_np
        self.test = False
        self.d = info.d
        self.dumpCost = info.dumpCost
        self.disp = display_solution_stats(info)
        
    def reduce_carp_routes(self, solution_lists, insert_depots=True):
        (routes, loads, service, deadhead, costs) = solution_lists
        nRoutes = len(routes)
        nRequiredRoutes = int(ceil(float(sum(loads))/float(self.capacity)))
        reduction = nRoutes - nRequiredRoutes
        change = False
        while reduction:
            loads_index = np.argsort(loads)
            remove = []
            for i in range(reduction):
                remove += routes[loads_index[i]]
            arc_loads = [] 
            for i, arc in enumerate(remove):
                arc_loads.append([-self.demandL[arc], arc])
            arc_loads.sort()
            arc_np = np.array(arc_loads)
            arcs_insert = arc_np[:,1]
            new_routes = []
            new_loads = []
            new_service = []
            new_deadhead = []
            new_costs = []
            for j in range(reduction, nRoutes):
                index_j = loads_index[j]
                new_routes.append(deepcopy(routes[index_j]))
                new_loads.append(loads[index_j])
                new_service.append(service[index_j])
                new_deadhead.append(deadhead[index_j])
                new_costs.append(costs[index_j])
            solution_lists_new = (new_routes, new_loads, new_service, new_deadhead, new_costs)
            if insert_depots:
                for k in range(len(solution_lists_new[0])):
                    solution_lists_new[0][k].insert(0, self.depot)
                    solution_lists_new[0][k].append(self.depot)
            (change, solution_lists_new) = self.insert_multiple_arcs.insert_multiple_arcs_carp(solution_lists_new, arcs_insert)                  
            for k in range(len(solution_lists_new[0])):
                del solution_lists_new[0][k][0]
                del solution_lists_new[0][k][-1]
            if change: return(change, solution_lists_new)
            else: reduction -= 1#return(change, solution_lists)
        return(change, solution_lists)

    def reduce_clarpif_routes(self, solution_lists, nRemove=1):
        (routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost) = solution_lists
        cost_index = np.argsort(cost)
        cost2 = cost[:]
        cost2.sort()
        excess_cap = (len(routes)-nRemove)*self.maxTrip - sum(cost2[nRemove:])
        nRoutes = len(routes)
        remove = []
        t_service = 0
        for i in range(nRemove):
            for trip in routes[cost_index[i]]:
                remove += trip
            t_service += service[cost_index[i]]
        change = False
        if (t_service < excess_cap) and (nRemove<nRoutes):
            change = True
            new_routes = []
            new_load = []
            new_service = []
            new_deadhead = []
            new_cost = []
            new_trip_load = []
            new_trip_service = []
            new_trip_deadhead = []
            new_trip_cost = []
            
            for j in range(nRemove, nRoutes):
                index_j = cost_index[j]
                new_routes.append(deepcopy(routes[index_j]))
                new_cost.append(cost[index_j])
                new_load.append(load[index_j])
                new_service.append(service[index_j])
                new_deadhead.append(deadhead[index_j])
                new_trip_load.append(trip_load[index_j][:])
                new_trip_service.append(deepcopy(trip_service[index_j]))
                new_trip_deadhead.append(deepcopy(trip_deadhead[index_j]))
                new_trip_cost.append(deepcopy(trip_cost[index_j]))
            solution_lists_new = (new_routes, new_load, new_service, new_deadhead, new_cost,  
                                  new_trip_load, new_trip_service, new_trip_deadhead, new_trip_cost)
            arc_loads = [] 
            for i, arc in enumerate(remove):
                arc_loads.append([-self.demandL[arc], arc])
            arc_loads.sort()
            arc_np = np.array(arc_loads)
            arcs_insert = arc_np[:,1].astype(int)
            (change, solution_lists_new) = self.insert_multiple_arcs.insert_multiple_arcs_clarpif(solution_lists_new, arcs_insert) 
            if change: return(change, solution_lists_new)
            else: return(change, solution_lists)
        return(change, solution_lists)

    def reduce_clarpif_routes_v2(self, solution_lists, nRemove=1):
        (routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost) = solution_lists
        cost_index = range(len(cost))
        cost2 = cost[:]
        excess_cap = (len(routes)-nRemove)*self.maxTrip - sum(cost2[nRemove:])
        nRoutes = len(routes)
        k = 0
        while k < nRoutes:
            remove = []
            t_service = 0
            for trip in routes[cost_index[k]]:
                remove += trip
            t_service += service[cost_index[k]]
            change = False
            if (t_service < excess_cap) and (nRemove<nRoutes):
                change = True
                new_routes = []
                new_load = []
                new_service = []
                new_deadhead = []
                new_cost = []
                new_trip_load = []
                new_trip_service = []
                new_trip_deadhead = []
                new_trip_cost = []
                
                for j in range(nRoutes):
                    if j != cost_index[k]:
                        index_j = cost_index[j]
                        new_routes.append(deepcopy(routes[index_j]))
                        new_cost.append(cost[index_j])
                        new_load.append(load[index_j])
                        new_service.append(service[index_j])
                        new_deadhead.append(deadhead[index_j])
                        new_trip_load.append(trip_load[index_j][:])
                        new_trip_service.append(deepcopy(trip_service[index_j]))
                        new_trip_deadhead.append(deepcopy(trip_deadhead[index_j]))
                        new_trip_cost.append(deepcopy(trip_cost[index_j]))
                solution_lists_new = (new_routes, new_load, new_service, new_deadhead, new_cost,  
                                      new_trip_load, new_trip_service, new_trip_deadhead, new_trip_cost)
                arc_loads = [] 
                for i, arc in enumerate(remove):
                    arc_loads.append([-self.demandL[arc], arc])
                arc_loads.sort()
                arc_np = np.array(arc_loads)
                arcs_insert = arc_np[:,1].astype(int)
                (change, solution_lists_new) = self.insert_multiple_arcs.insert_multiple_arcs_clarpif(solution_lists_new, arcs_insert)
                if change: return(change, solution_lists_new)
                else: k += 1
            else: k += 1
        return(change, solution_lists)

    def reduce_clarpif_routes_v3(self, solution_lists, nRemove=1):
        (routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost) = solution_lists
        cost_index = np.argsort(cost)
        cost2 = cost[:]
        cost2.sort()
        excess_cap = (len(routes)-nRemove)*self.maxTrip - sum(cost2[nRemove:])
        nRoutes = len(routes)
        k = 0
        l = 0
        for k in range(0, nRoutes - 1):
            for l in range(k + 1, nRoutes):
                #print(k,l)
                remove = []
                t_service = 0
    
                for trip in routes[cost_index[k]]:
                    remove += trip
                t_service += service[cost_index[k]]
                
                if nRemove > 1:
                    for trip in routes[cost_index[l]]:
                        remove += trip
                    t_service += service[cost_index[l]]                
                
                change = False
                
                if (t_service < excess_cap) and (nRemove<nRoutes):
                    change = True
                    new_routes = []
                    new_load = []
                    new_service = []
                    new_deadhead = []
                    new_cost = []
                    new_trip_load = []
                    new_trip_service = []
                    new_trip_deadhead = []
                    new_trip_cost = []
                    
                    for j in range(nRemove, nRoutes):
                        if (j != cost_index[k]) and (j != cost_index[l]):
                            index_j = cost_index[j]
                            new_routes.append(deepcopy(routes[index_j]))
                            new_cost.append(cost[index_j])
                            new_load.append(load[index_j])
                            new_service.append(service[index_j])
                            new_deadhead.append(deadhead[index_j])
                            new_trip_load.append(trip_load[index_j][:])
                            new_trip_service.append(deepcopy(trip_service[index_j]))
                            new_trip_deadhead.append(deepcopy(trip_deadhead[index_j]))
                            new_trip_cost.append(deepcopy(trip_cost[index_j]))
                    solution_lists_new = (new_routes, new_load, new_service, new_deadhead, new_cost,  
                                          new_trip_load, new_trip_service, new_trip_deadhead, new_trip_cost)
                    arc_loads = [] 
                    for i, arc in enumerate(remove):
                        arc_loads.append([-self.demandL[arc], arc])
                    arc_loads.sort()
                    arc_np = np.array(arc_loads)
                    arcs_insert = arc_np[:,1]
                    (change, solution_lists_new) = self.insert_multiple_arcs.insert_multiple_arcs_clarpif(solution_lists_new, arcs_insert) 
                    if change: return(change, solution_lists_new)
                    if nRemove == 1: break
        return(change, solution_lists)

    def reduce_CARP_solution(self, solution):
        solution_lists = build_CARP_list(solution)
        (change, solution_lists) = self.reduce_carp_routes(solution_lists)
        if change:
            (new_routes, new_loads, new_service, new_deadhead, new_costs) = solution_lists
            solution = build_CARP_dict_from_list(new_routes, new_loads, new_service, new_deadhead, new_costs, self.depot)
        return(change, solution)

    def reduce_CLARPIF_solution(self, solution):
        solution_list = build_CLARPIF_list(solution)
        n = 0
        reduced = False
        while True:
            n += 1
            (change, solution_list_best) = self.reduce_clarpif_routes(deepcopy(solution_list), n)
            if change:
                solution_list_final = deepcopy(solution_list_best)
                reduced = True
            else: break
        if reduced:
            (routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost) = solution_list_final
            solution = build_CLARPIF_dict_from_list(routes, load, service,  deadhead, cost, trip_load, 
                                                    trip_service, trip_deadhead, trip_cost,
                                                    self.if_arc, self.depot, self.d, self.dumpCost)
        return(reduced, solution)

    def reduce_CLARPIF_solution_v2(self, solution):
        #print('v2')
        solution_list = build_CLARPIF_list(solution)
        n = 0
        reduced = False
        while True:
            n = 1
            (change, solution_list_best) = self.reduce_clarpif_routes_v2(deepcopy(solution_list), n)
            if change:
                solution_list = deepcopy(solution_list_best)
                reduced = True
                break
            else: break
        if reduced:
            (routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost) = solution_list
            solution = build_CLARPIF_dict_from_list(routes, load, service,  deadhead, cost, trip_load, 
                                                    trip_service, trip_deadhead, trip_cost,
                                                    self.if_arc, self.depot, self.d, self.dumpCost)
        return(reduced, solution)

    def reduce_CLARPIF_solution_v3(self, solution):
        print('v3')
        solution_list = build_CLARPIF_list(solution)
        n = 0
        reduced = False
        while n < 2:
            n += 1
            (change, solution_list_best) = self.reduce_clarpif_routes_v3(deepcopy(solution_list), n)
            if change:
                solution_list_final = deepcopy(solution_list_best)
                reduced = True
            else: break
        if reduced:
            (routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost) = solution_list_final
            solution = build_CLARPIF_dict_from_list(routes, load, service,  deadhead, cost, trip_load, 
                                                    trip_service, trip_deadhead, trip_cost,
                                                    self.if_arc, self.depot, self.d, self.dumpCost)
        return(reduced, solution)


    def reduce_trip(self, solution, v2 = True, v3 = False):
        nBefore = solution['nVehicles']
        if solution['ProblemType'] == 'CARP':
            (reduced, solution) = self.reduce_CARP_solution(solution)
        elif solution['ProblemType'] == 'CLARPIF':
            if v2: (reduced, solution) = self.reduce_CLARPIF_solution_v2(solution)
            elif v3: (reduced, solution) = self.reduce_CLARPIF_solution_v3(solution)
            else: (reduced, solution) = self.reduce_CLARPIF_solution(solution)
        if reduced:
            #print('ROUTES REDUCED: nRoutes before: %i nRoutes after: %i'% (nBefore, solution['nVehicles']))
            if self.test: test_solution(self.info, solution)
        #else: print('ROUTES NOT REDUCED')
        return(solution, reduced)
    
if __name__ == ('__main__'):
    print('Use profiler')