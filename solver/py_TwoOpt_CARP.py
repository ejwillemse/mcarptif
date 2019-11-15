'''
Created on 29 Jan 2012

@author: elias

Classical neighbourhood search using three different constructors: remove-insert, exchange and two-opt. Operatorors are applied
to one or two routes, and the first or best improving move found is implemented. The efficiency of the algorithm is improved
by only evaluating moves into routes if available vehicle capacity allows. Down-side of the algorithm is that all moves are 
evaluated in each iteration, even though most moves are the same as with previous iterations.

Depots are not included in solution lists, but are accounted for with cost calculations.
'''
from __future__ import division
# Import pyximport used for c modules
import numpy as np
import pyximport
pyximport.install(setup_args={"include_dirs":np.get_include()})

# All
#import c_LS_CARP as cri
import py_solution_builders
import py_route_directions
from py_display_solution import display_solution_stats

from py_remove_insert_operators import remove_insert_CARP
from copy import deepcopy
from py_solution_test  import test_solution
from py_reduce_number_trips import Reduce_Trips 

from time import clock


# Populate the c modules with required input data
# def populate_c_local_searc(info):
#     cri.set_input(info)
# 
# def free_c_local_search():
#     cri.free_input()

class make_neighbourhood_moves(object):
    '''
    Make actual neighbourhood moves to the solution lists. Moves consists
    of arcs, positions, routes, move types, load and cost changes.
    '''
    
    def make_move_RI_other(self, solution_lists, move_data):
        '''
        Arc is removed from a route and inserted into another route.
        '''
        (routes, loads, services,  deadheads, costs) = solution_lists
        (net_remove, net_insert, i, i_arc, j, j_pos, arc) = move_data[1:8]
        
        # Demand and service cost of removed arc
        demand_arc = self.demand[arc]
        service_arc = self.service[arc]
        
        del routes[i][i_arc] # Arc in route i in position i_arc is deleted from route
                
        routes[j].insert(j_pos, arc) # Arc (or possible its inverse) is inserted into position j_pos in route j 
        loads[j] += demand_arc # Load of route j is updated
        services[j] += service_arc # Service cost of route j is updated
        deadheads[j] += net_insert # Deadheading cost of route j is updated (removal + insert cost = net_insert)
        costs[j] += (net_insert + service_arc) # Cost of route j is updated
        
        # If route i serviced a single arc, the route and its associated information is deleted --- depots are not included in solution lists.
        if not routes[i]:
            del routes[i]
            del loads[i]
            del services[i]
            del deadheads[i]
            del costs[i]
        # Else the information of route i is updated by subtracting insertion information
        else:
            loads[i] -= demand_arc
            services[i] -= service_arc
            deadheads[i] += net_remove
            costs[i] += (net_remove - service_arc)
        
        solution_lists = (routes, loads, services,  deadheads, costs)
        return(solution_lists)

    def make_move_RI_same(self, solution_lists, move_data):
        '''
        Arc is removed from a route and reinserted into the route in a different position.
        '''
        (routes, loads, services,  deadheads, costs) = solution_lists
        (net_cost, i, i_pos, j_pos, arc) = move_data[:5]
        
        # Arc is delete from its position, and the arc or its inverse is inserted into a new position. The arc has to be deleted from its original, 
        # hence the delete insert sequence depends on the remove and insert positions relative to each other.
        if i_pos < j_pos:
            routes[i].insert(j_pos, arc)
            del routes[i][i_pos]
        elif i_pos > j_pos:
            del routes[i][i_pos]
            routes[i].insert(j_pos, arc)
        
        # Move applied to the same route so only the costs of the route have to be updated with the net costs.
        deadheads[i] += net_cost
        costs[i] += net_cost
        
        solution_lists = (routes, loads, services,  deadheads, costs)
        return(solution_lists)

    def make_move_E_other(self, solution_lists, move_data):
        '''
        Two arcs are exchanged between two routes.
        '''
        (routes, loads, services,  deadheads, costs) = solution_lists
        (net_replace_i, net_replace_j, i, i_pos, j, j_pos, remove_arc_i, remove_arc_j, demand_change) = move_data[1:10]
        
        # Net costs for routes i and j are updated
        service_change = self.service[remove_arc_i] - self.service[remove_arc_j] # Change in service cost for route j
        
        loads[i] -= demand_change # Demand changes are subtracted for route i since they are specified for route j
        services[i] -= service_change
        deadheads[i] += net_replace_i
        costs[i] += (net_replace_i - service_change)

        loads[j] += demand_change
        services[j] += service_change
        deadheads[j] += net_replace_j
        costs[j] += (net_replace_j + service_change)
        
        routes[i][i_pos] = remove_arc_j # Arc in i_pos is simply changed to route j
        routes[j][j_pos] = remove_arc_i # Arc in j_pos is simply changed to route_i
        
        solution_lists = (routes, loads, services,  deadheads, costs)
        return(solution_lists)

    def make_move_E_same(self, solution_lists, move_data):
        '''
        Two routes are exchanged in the same route.
        '''
        (routes, loads, services,  deadheads, costs) = solution_lists
        (net_cost, i, i_pos, j_pos, remove_arc_i, remove_arc_j) = move_data[:6]
        routes[i][i_pos] = remove_arc_j
        routes[i][j_pos] = remove_arc_i
        costs[i] += net_cost
        deadheads[i] += net_cost
        solution_lists = (routes, loads, services,  deadheads, costs)
        return(solution_lists)

    def adjust_load_servce_lists(self, ls_list_i, i_pos, ls_list_j, j_pos):
        '''
        Cumulative load and service cost is updated with two-opt move.
        '''
        if i_pos == 0: ld_i1 = 0
        else: ld_i1 = ls_list_i[i_pos-1] 
        if j_pos == 0: ld_j1 = 0
        else: ld_j1 =  ls_list_j[j_pos-1]
        
        new_ls_i = ls_list_i[:i_pos] + ls_list_j[j_pos:]
        new_ls_j = ls_list_j[:j_pos] + ls_list_i[i_pos:]
        
        for k in range(i_pos, len(new_ls_i)):
            new_ls_i[k] += (ld_i1 - ld_j1)
        for l in range(j_pos, len(new_ls_j)):
            new_ls_j[l] += (ld_j1 - ld_i1) 
        
        return(new_ls_i, new_ls_j)
    
    def adjust_dead_lists(self, ls_list_i, i_pos, i_link, ls_list_j, j_pos, j_link):
        '''
        Dead-heading cost is updated with two-opt move.
        '''
        new_ls_i = ls_list_i[:i_pos] + ls_list_j[j_pos:]
        new_ls_j = ls_list_j[:j_pos] + ls_list_i[i_pos:]
        
        if i_pos == 0: ld_i1 = 0
        else: ld_i1 = new_ls_i[i_pos-1]   
        if j_pos == 0: ld_j1 = 0
        else: ld_j1 =  new_ls_j[j_pos-1]
        
        new_ls_i[i_pos] = ld_i1 + i_link
        i_change = new_ls_i[i_pos] - ls_list_j[j_pos]
        
        new_ls_j[j_pos] = ld_j1 + j_link
        j_change = new_ls_j[j_pos] - ls_list_i[i_pos]

        if j_pos == len(ls_list_j) - 1: new_ls_i[-1] += self.dumpCost
        if i_pos == len(ls_list_i) - 1: new_ls_j[-1] += self.dumpCost
        
        for k in range(i_pos+1, len(new_ls_i)):
            new_ls_i[k] += i_change
        for l in range(j_pos+1, len(new_ls_j)):
            new_ls_j[l] += j_change
            
        return(new_ls_i, new_ls_j)  

    def make_move_2opt_other(self, solution_lists, solution_cum_lists, solution_cum_lists_inv, move_data):
        '''
        Two routes are split and re-linked by adding the head of one section to the tail of the other.
        '''
        (save, new_cost_i, new_cost_j, i, i_pos, j, j_pos) = move_data[:7]
        
        (routes, loads_cum, service_cum, deadhead_cum) = solution_cum_lists
        inv_routes = solution_cum_lists_inv[0]
        
        (loads, service, deadhead, cost) = solution_lists[1:]
        
        if i >= len(routes):
            i -=  len(routes)
            routes[i] = inv_routes[i]
        if j >= len(routes):
            j -= len(routes)
            routes[j] = inv_routes[j]
        
        new_route_i = routes[i][:i_pos] + routes[j][j_pos:]
        new_route_j = routes[j][:j_pos] + routes[i][i_pos:]         
        
        if not new_route_i: 
            new_route_i = [self.depot]
            del_route_i = True
        else: del_route_i = False
        if not new_route_j: 
            new_route_j = [self.depot]
            del_route_j = True
        else: del_route_j = False
        
        (new_load_i, new_serve_i, new_cum_dead_i) =  self.builder.build_CARP_cum_list_from_route(new_route_i)
        (new_load_j, new_serve_j, new_cum_dead_j) =  self.builder.build_CARP_cum_list_from_route(new_route_j)
        
        if save <> (new_cum_dead_i[-1] + new_cum_dead_j[-1] - deadhead_cum[i][-1] - deadhead_cum[j][-1]): 
            if (del_route_i == False)&(del_route_j == False): print('Error', save, new_cum_dead_i[-1] + new_cum_dead_j[-1] - deadhead_cum[i][-1] - deadhead_cum[j][-1])

        routes[i], routes[j] = deepcopy(new_route_i), deepcopy(new_route_j)

        loads_cum[i], loads_cum[j] = deepcopy(new_load_i), deepcopy(new_load_j)
        loads[i], loads[j] = loads_cum[i][-1], loads_cum[j][-1]
  
        service_cum[i], service_cum[j] = deepcopy(new_serve_i), deepcopy(new_serve_j)
        service[i], service[j] = service_cum[i][-1], service_cum[j][-1]

        deadhead_cum[i], deadhead_cum[j]  = deepcopy(new_cum_dead_i), deepcopy(new_cum_dead_j)
        deadhead[i], deadhead[j] = deadhead_cum[i][-1], deadhead_cum[j][-1]
        
        cost[i] = service[i] + deadhead[i]
        cost[j] = service[j] + deadhead[j]
        
        solution_cum_lists = (routes, loads_cum, service_cum,  deadhead_cum)
        solution_lists = (routes, loads, service, deadhead, cost)

        if del_route_i: 
            for del_i in xrange(len(solution_lists)): 
                del solution_lists[del_i][i]
                
        if del_route_j: 
            for del_i in xrange(len(solution_lists)): 
                del solution_lists[del_i][j]
                
        return(solution_lists, solution_cum_lists)

    def make_move_2opt_same(self, solution_lists, solution_cum_lists, solution_cum_lists_inv, move_data):
        '''
        A section of a route is removed, reversed and re-inserted into a route.
        '''
        (save, i, i_pos, j_pos) = move_data[:4]
        (routes, loads_cum, service_cum, deadhead_cum) = solution_cum_lists
        inv_route = solution_cum_lists_inv[0]
        (loads, service, deadhead, cost) = solution_lists[1:]
        
        if i >= len(routes):
            i -= len(routes)
            k = len(routes[i]) - j_pos - 1
            l = len(routes[i]) - i_pos
            new_route_i = inv_route[i][:i_pos] + routes[i][k:l] + inv_route[i][j_pos+1:]
            routes[i] = deepcopy(new_route_i)
        else:
            k = len(inv_route[i]) - j_pos - 1
            l = len(inv_route[i]) - i_pos
            new_route_i = routes[i][:i_pos] + inv_route[i][k:l] + routes[i][j_pos+1:]
            routes[i] = deepcopy(new_route_i)
        
        (new_load, new_serv, new_dead) =  self.builder.build_CARP_cum_list_from_route(new_route_i)
        
        if save <> (new_dead[-1] - deadhead_cum[i][-1]): print('Error', save, new_dead[-1] + deadhead_cum[i][-1])
        
        loads_cum[i] = deepcopy(new_load)
        loads[i] = loads_cum[i][-1]
        
        service_cum[i] = deepcopy(new_serv)
        service[i] = service_cum[i][-1]

        deadhead_cum[i] = deepcopy(new_dead)
        deadhead[i] = deadhead_cum[i][-1]
        
        cost[i] = deadhead[i] + service[i]
        
        solution_cum_lists = (routes, loads_cum, service_cum,  deadhead_cum)     
        solution_lists = (routes, loads, service,  deadhead, cost)
        
        return(solution_lists, solution_cum_lists)

    def make_move(self, solution_lists, solution_cum_lists, solution_cum_lists_inv, move_data):
        if move_data[-1] == 'remove-insert-same':
            return(self.make_move_RI_same(solution_lists, move_data), solution_cum_lists)
        if move_data[-1] == 'remove-insert-other':
            return(self.make_move_RI_other(solution_lists, move_data), solution_cum_lists)
        if move_data[-1] == 'exchange-same':
            return(self.make_move_E_same(solution_lists, move_data), solution_cum_lists)
        if move_data[-1] == 'exchange-other':
            return(self.make_move_E_other(solution_lists, move_data), solution_cum_lists)    
        if move_data[-1] == '2opt-same': 
            return(self.make_move_2opt_same(solution_lists, solution_cum_lists, solution_cum_lists_inv, move_data))
        if move_data[-1] == '2opt-other': 
            return(self.make_move_2opt_other(solution_lists, solution_cum_lists, solution_cum_lists_inv, move_data))

class remove_insert_neighbourhood(remove_insert_CARP):
    '''
    Neighbourhoods are constructed by removing arcs from routes and inserting them into different routes, or different
    positions in the same route. Either the best or first improving move is returned.
    '''
    def __init__(self, info, cri, neighbourlist = []):
        remove_insert_CARP.__init__(self, info)
        self.info = info
        self.capacity = info.capacity
        self.demand = info.demandL
        self.service = info.serveCostL
        self.inv_list = info.reqInvArcList
        
        self.neighbourlist = neighbourlist
        self.reqarcs = info.reqInvArcList
        
        self.c_modules = True  # Use c module procedures (much quicker)
        self.full_1r = True     # Inverse insertion of removed arc is also considered with same route moves.
        self.full_2r = True     # Inverse insertion of removed arc is also considered with two route moves.
        self.find_first = True  # Find and return the first improving move, stop the algorithm.
        self.test = False       # Test move made (NOT USED)
        self.cri = cri
    
    def find_best_remove_insert_same_spec_route(self, solution_lists, route_rem_add, best_remove=1e300000):
        '''
        Remove-insert performed on one route.
        '''
        # Best move data with cost 0 (only improving moves are returned).
        move_available = False
        best_move_data = (best_remove, 0)

        # Route on which operations will be performed.
        i = route_rem_add
        routes = solution_lists[0]
        route_i = routes[i]
        
        for i_pos in xrange(len(route_i)): # Each arc in the route is removed
            remove_arc = route_i[i_pos]
            net_remove = self.remove_from_route(route_i, i_pos)[0] # Cost of removing the arc from the route and closing the route
            
            # If the arc has an inverse, inverse insertion is also checked.
            inverse = False
            if self.full_1r: 
                if self.inv_list[remove_arc]:
                    inverse = True
                    inv_remove_arc = self.inv_list[remove_arc]
            
            # Removed arc is inserted in all possible positions in the route.
            # i_pos and i_pos + 1 positions excluded. First redos the arc remove, and second results in an exchange between routes, which requires a different delta calculation.             
            j_pos_range = range(i_pos) + range(i_pos + 2, len(route_i))
            for j_pos in j_pos_range:
                if j_pos <> i_pos: # Redundant since i_pos is excluded from j_pos_range?
                    net_insert = self.insert_in_route(route_i, j_pos, remove_arc)[0] # Calc insert costs.
                    net_cost = net_insert + net_remove # Cost delta
                    
                    # If inverse route is required, compare straight insert with inversed insert and use the best.
                    inversed_choose = False
                    if inverse:
                        net_rev_insert = self.insert_in_route(route_i, j_pos, inv_remove_arc)[0]
                        net_rev_cost = net_rev_insert + net_remove                                    
                        if net_rev_cost < net_cost:
                            remove_arc = inv_remove_arc
                            net_cost = net_rev_cost
                            inversed_choose = True
                    
                    # Check if net_cost is less than best move (0 for first move).        
                    if net_cost < best_move_data[0]:
                        move_available = True
                        best_inverse = inversed_choose
                        # Remove insert info is the move cost (net_cost), remove route (i), remove position (i_pos), insert position (j_pos), actual arc removed or its inverse (remove_arc), flag indicating if the move involved an inversed arc (best_arc), and move key ('remove-insert-same')
                        best_move_data = (net_cost, i, i_pos, j_pos, remove_arc, best_inverse, 'remove-insert-same')
                        if self.find_first: break # break for loop if first found should be returned.
                        
            if move_available: 
                if self.find_first: break # break for loop if first found should be returned. Unnecessary since return can be included in if net_cost < best_move_data[0].
        
        return(move_available, best_move_data)

    def find_best_remove_insert_other_spec_route(self, solution_lists, route_rem, route_add, best_remove=1e300000):
        '''
        Remove-insert performed on two routes.
        '''
        # Best move data with cost 0 (only improving moves are returned).
        move_available = False
        best_move_data = (best_remove, 0)
        
        # Route i from which arcs will be removed, and route j to which they will be added.
        i = route_rem
        j = route_add
        (routes, loads) = solution_lists[:2]
        route_i = routes[i]
        
        for i_arc in xrange(len(route_i)): # Each arc from route i is removed
            # Load and 
            remove_arc = route_i[i_arc]
            net_remove = self.remove_from_route(route_i, i_arc)[0] # Cost of removing the arc from the route and closing the route.
            
            # If the arc has an inverse, inverse insertion is also checked.
            inverse = False
            if self.full_2r:
                if self.inv_list[remove_arc]:
                    inverse = True
                    inv_remove_arc = self.inv_list[remove_arc]
            
            load_remove_arc = self.demand[remove_arc] # Load of removed arc. Check if insert route has available capacity, otherwise move to the next arc.
            if load_remove_arc + loads[j] <= self.capacity:
                route_j = routes[j]
                # Arc is inserted into all possible positions in route j.
                for j_pos in xrange(len(route_j)+1):
                    net_insert = self.insert_in_route(route_j, j_pos, remove_arc)[0] # insert cost
                    net_cost = net_insert + net_remove
                    
                    # If inverse route is required, compare straight insert with inversed insert and use the best.
                    inversed_choose = False
                    if inverse:
                        net_rev_insert = self.insert_in_route(route_j, j_pos, inv_remove_arc)[0]
                        net_rev_cost = net_rev_insert + net_remove                                    
                        if net_rev_cost < net_cost:
                            remove_arc = inv_remove_arc
                            net_cost = net_rev_cost
                            net_insert = net_rev_insert
                            inversed_choose = True
                    
                    # Check if net_cost is less than best move (0 for first move). 
                    if net_cost < best_move_data[0]:
                        move_available = True
                        best_inverse = inversed_choose
                        # Remove insert info is the move cost (net_cost), removal cost (net_remove), insert cost (net_insert), remove route (i), remove position (i_pos), insert route (j), insert position (j_pos), actual arc removed or its inverse (remove_arc), flag indicating if the move involved an inversed arc (best_arc), and move key ('remove-insert-same')
                        best_move_data = (net_cost, net_remove, net_insert, i, i_arc, j, j_pos, remove_arc, best_inverse, 'remove-insert-other')
                        if self.find_first: break # break for loop if first found should be returned.
                        
            if move_available: 
                if self.find_first: break # break for loop if first found should be returned. Unnecessary since return can be included in if net_cost < best_move_data[0].
        
        return(move_available, best_move_data)

    def find_best_remove_insert_same_py(self, solution_lists, best_remove = 0):
        '''
        Find best same route remove insert move with a net cost less than zero (improving move). 
        '''
        best_remove = 0
        best_move_available = False
        best_move_data = (best_remove, 0)
        for route_rem_add in xrange(len(solution_lists[0])):
            (move_available, move_data) = self.find_best_remove_insert_same_spec_route(solution_lists, 
                                                                                       route_rem_add, 
                                                                                       best_move_data[0])
            if move_available:
                if move_data[0] < best_move_data[0]:
                    best_move_data = move_data
                    best_move_available = True
                    if self.find_first: break
                    
        return(best_move_available, best_move_data)
        
    def find_best_remove_insert_other_py(self, solution_lists, best_remove = 0):
        '''
        Find best two route remove insert move with a net cost less than zero (improving move). 
        '''
        best_move_available = False
        best_move_data = (best_remove, 0)
        for route_rem in xrange(len(solution_lists[0])):
            for route_add in xrange(len(solution_lists[0])):
                if route_rem <> route_add: # Can be omitted by constructing a range list
                    (move_available, move_data) = self.find_best_remove_insert_other_spec_route(solution_lists, 
                                                                                                route_rem, route_add, 
                                                                                                best_move_data[0])
                    if move_available:
                        if move_data[0] < best_move_data[0]:
                            best_move_data = move_data
                            best_move_available = True
                            if self.find_first: break # return can be included here.
                            
            if best_move_available: # Can be omitted.
                if self.find_first: break
                
        return(best_move_available, best_move_data)

    def find_best_remove_insert_other_specified_py(self, solution_lists, routes_remove, routes_add, best_remove = 1e300000):
        '''
        Find best two route remove insert move with a net cost less than zero (improving move). 
        '''
        best_move_available = False
        best_move_data = (best_remove, 0)
        for route_rem in routes_remove:
            for route_add in routes_add:
                if route_rem <> route_add: # Can be omitted by constructing a range list
                    (move_available, move_data) = self.find_best_remove_insert_other_spec_route(solution_lists, route_rem, route_add, best_move_data[0])
                    if move_available:
                        if move_data[0] < best_move_data[0]:
                            best_move_data = move_data
                            best_move_available = True
                            if self.find_first: break # return can be included here.
        return(best_move_available, best_move_data)
        
    def c_find_best_remove_insert_same(self, solution_lists):
        '''
        Same route c implementation. Can be directly included in find_best_remove_insert definition.
        '''
        (move_available, best_move_data) = self.cri.find_best_remove_insert_same(solution_lists, self.full_1r, self.find_first)
        return(move_available, best_move_data)
    
    def c_find_best_remove_insert_other(self, solution_lists):
        '''
        Two route c implementation. Can be directly included in find_best_remove_insert definition.
        '''
        (move_available, best_move_data) = self.cri.find_best_remove_insert_other(solution_lists, self.full_2r, self.find_first)
        return(move_available, best_move_data)

    def find_best_remove_insert_same(self, solution_lists):
        if self.c_modules: return(self.c_find_best_remove_insert_same(solution_lists))
        else: return(self.find_best_remove_insert_same_py(solution_lists))
        
    def find_best_remove_insert_other(self, solution_lists):
        if self.c_modules: return(self.c_find_best_remove_insert_other(solution_lists))
        else: return(self.find_best_remove_insert_other_py(solution_lists))    

class exchange_neighbourhood(remove_insert_CARP):
    '''
    Neighbourhoods are constructed by exchanging arcs between routes, or by exchanging arc positions in the same route. 
    Either the best or first improving move is returned.
    '''
    def __init__(self, info, cri):
        remove_insert_CARP.__init__(self, info)
        self.info = info
        self.capacity = info.capacity
        self.demand = info.demandL
        self.service = info.serveCostL
        self.inv_list = info.reqInvArcList

        self.c_modules = True   # Use c modules (much faster)
        self.full_1r = True     # Inverse of both arcs are evaluated with re-insertion in the same route.
        self.full_2r = True     # Inverse of both arcs are considered with re-insertion between two routes.
        self.find_first = True  # First improving move is returned.
        self.test = False       # Test move made (NOT USED)
        self.cri = cri
        
    def find_best_exchange_other_spec_route(self, solution_lists, route_rem, route_add, best_remove=1e300000):
        '''
        Arc exchange performed on two routes.
        '''
        # Best move data with cost 0 (only improving moves are returned).
        move_available = False
        best_move_data = (best_remove, 0)
        
        # Route i and j information
        (routes, loads) = solution_lists[:2]
        i = route_rem
        route_i = routes[i]
        load_i = loads[i]

        j = route_add
        route_j = routes[j]
        load_j = loads[j]
        
        # Each arc in route i is exchanged with each arc in route j
        for i_pos in xrange(len(route_i)): # Route i arcs
            remove_arc_i = route_i[i_pos]
            for j_pos in xrange(len(route_j)): # Route j arcs
                remove_arc_j = route_j[j_pos]
                demand_change = self.demand[remove_arc_i] - self.demand[remove_arc_j] # demand change for route j
                if (load_i - demand_change <= self.capacity) & (load_j + demand_change <= self.capacity): # check that routes can accommodate capacity change
                    replace_cost_i = self.replace_in_route(route_i, i_pos, remove_arc_j)[0] # Cost of replacing arc i with arc j       
                    replace_cost_j = self.replace_in_route(route_j, j_pos, remove_arc_i)[0] # Cost of replacing arc j with arc i                  
                    
                    # Check inversed replacement of both arcs - same procedure performed twice, so can be replaced.
                    inversed_i = inversed_j = False
                    if self.full_2r:
                        if self.inv_list[remove_arc_i]: # Check inversed arc_i
                            inv_remove_arc_i = self.inv_list[remove_arc_i]
                            replace_cost_j_inv = self.replace_in_route(route_j, j_pos, inv_remove_arc_i)[0]
                            if replace_cost_j_inv < replace_cost_j:
                                replace_cost_j = replace_cost_j_inv
                                remove_arc_i = inv_remove_arc_i
                                inversed_i = True
                        if self.inv_list[remove_arc_j]: # Check inversed of arc_j
                            inv_remove_arc_j = self.inv_list[remove_arc_j]
                            inv_replace_cost_i = self.replace_in_route(route_i, i_pos, inv_remove_arc_j) [0]
                            if inv_replace_cost_i < replace_cost_i:
                                replace_cost_i = inv_replace_cost_i
                                remove_arc_j = inv_remove_arc_j
                                inversed_j = True
                            
                    # Check if net_cost is less than best move (0 for first move). 
                    net_cost = replace_cost_i + replace_cost_j
                    if net_cost < best_move_data[0]:
                        final_inv_i, final_inv_j = inversed_i, inversed_j
                        move_available = True
                        best_move_data = (net_cost, replace_cost_i, replace_cost_j, i, i_pos, j, j_pos, remove_arc_i, remove_arc_j, demand_change, final_inv_i, final_inv_j, 'exchange-other')
                        if self.find_first: break
            
            if move_available: # Can be omitted by including a return in net_cost if loop. 
                if self.find_first: break
        
        return(move_available, best_move_data)

    def find_best_exchange_same_spec_route(self, solution_lists, route_rem_add, best_remove=1e300000):
        '''
        Arc exchange performed on one route.
        '''
        # Best move data with cost 0 (only improving moves are returned).
        move_available = False
        best_move_data = (best_remove, 0)
        
        # Route i information
        i = route_rem_add
        routes = solution_lists[0]
        route_i = routes[i]
        
        for i_pos in xrange(len(route_i)-1): # j_pos > i_pos, thus len(route_i) - 1
            # Arcs in i_pos and j_pos are removed. Exchanging arc in j_pos with i_pos is the same as exchanging arc in i_pos with j_pos, thus j_pos > i_pos
            for j_pos in xrange(i_pos+2,len(route_i)): # j_pos = i_pos + 1 requires a different calculation (omitted with this implementation)
                
                remove_arc_i = route_i[i_pos]
                remove_arc_j = route_i[j_pos]
                replace_cost_i = self.replace_in_route(route_i, i_pos, remove_arc_j)[0] # Cost of replacing arc i with arc j           
                replace_cost_j = self.replace_in_route(route_i, j_pos, remove_arc_i)[0] # Cost of replacing arc j with arc i                  
                
                # Check inversed replacement of both arcs - same procedure performed twice, so can be replaced.
                inversed_i = inversed_j = False
                if self.full_1r:
                    if self.inv_list[remove_arc_i]: # Inversed arc i
                        inv_remove_arc_i = self.inv_list[remove_arc_i]
                        replace_cost_j_inv = self.replace_in_route(route_i, j_pos, inv_remove_arc_i)[0]
                        if replace_cost_j_inv < replace_cost_j:
                            replace_cost_j = replace_cost_j_inv
                            remove_arc_i = inv_remove_arc_i
                            inversed_i = True   
                    if self.inv_list[remove_arc_j]: # Inversed arc j
                        inv_remove_arc_j = self.inv_list[remove_arc_j]
                        inv_replace_cost_i = self.replace_in_route(route_i, i_pos, inv_remove_arc_j) [0]
                        if inv_replace_cost_i < replace_cost_i:
                            replace_cost_i = inv_replace_cost_i
                            remove_arc_j = inv_remove_arc_j
                            inversed_j = True
                
                # Check if net_cost is less than best move (0 for first move). 
                net_cost = replace_cost_i + replace_cost_j
                if net_cost < best_move_data[0]:
                    final_inv_i, final_inv_j = inversed_i, inversed_j
                    move_available = True
                    best_move_data = (net_cost, i, i_pos, j_pos, remove_arc_i, remove_arc_j, final_inv_i, final_inv_j, 'exchange-same')
                    if self.find_first: break
            
            if move_available: # Can be replaced
                if self.find_first: break
        
        return(move_available, best_move_data)

    def find_best_exchange_same_py(self, solution_lists, best_remove = 0):
        '''
        Each route is used for internal exchange.
        '''
        best_move_available = False
        best_move_data = (best_remove, 0)
        for route_rem in xrange(len(solution_lists[0])):
            (move_available, move_data) = self.find_best_exchange_same_spec_route(solution_lists, 
                                                                                        route_rem, 
                                                                                        best_move_data[0])
            if move_available:
                if move_data[0] < best_move_data[0]:
                    best_move_data = move_data
                    best_move_available = True
                    if self.find_first: break
        return(best_move_available, best_move_data)

    def find_best_exchange_other_py(self, solution_lists, best_remove = 0):
        '''
        All routes are used for two route arc exchange. 
        '''
        best_move_available = False
        best_move_data = (best_remove, 0)
        for route_rem in xrange(len(solution_lists[0]) - 1):
            # Evaluating route i and route j is the same as evaluating route j and route i, thus j > i.
            for route_add in xrange(route_rem + 1, len(solution_lists[0])):
                (move_available, move_data) = self.find_best_exchange_other_spec_route(solution_lists, 
                                                                                       route_rem, route_add, 
                                                                                       best_move_data[0])
                if move_available:
                    if move_data[0] < best_move_data[0]:
                        best_move_data = move_data
                        best_move_available = True
                        if self.find_first: break
            if best_move_available: 
                if self.find_first: break
        return(best_move_available, best_move_data)

    def c_find_best_exchange_same(self, solution_lists):
        '''
        Same route c implementation. Can be directly included in find_best_remove_insert definition.
        '''
        (move_available, best_move_data) = self.cri.find_best_exchange_same(solution_lists, self.full_1r, self.find_first)
        return(move_available, best_move_data)   

    def c_find_best_exchange_other(self, solution_lists):
        '''
        Two route c implementation. Can be directly included in find_best_remove_insert definition.
        '''
        (move_available, best_move_data) = self.cri.find_best_exchange_other(solution_lists, self.full_2r, self.find_first)
        return(move_available, best_move_data)    
    
    def find_best_exchange_same(self, solution_lists):
        if self.c_modules: return(self.c_find_best_exchange_same(solution_lists))
        else: return(self.find_best_exchange_same_py(solution_lists))

    def find_best_exchange_other(self, solution_lists):
        if self.c_modules: return(self.c_find_best_exchange_other(solution_lists))
        else: return(self.find_best_exchange_other_py(solution_lists))

class two_opt_neighourhood(remove_insert_CARP,  make_neighbourhood_moves):
    '''
    Neighbourhoods are constructed by exchanging complete sections between routes, or by removing a section of a route,
    reversing it, and reinserting it in the same route. Cumulative costs are used.
    '''
    def __init__(self, info, cri):
        self.opdirect = py_route_directions.optArcDirect(info) # Finds the optimal direction of all edge tasks in a route - NOT USED here, but in the main problem structure. NOT GOOD!
        remove_insert_CARP.__init__(self, info)
        
        self.info = info
        self.capacity = info.capacity
        self.demand = info.demandL
        self.service = info.serveCostL        
        self.dumpCost = info.dumpCost
        self.depot = info.depotnewkey

        self.c_modules = True  # Use c module implementations (much quicker)
        self.cp_modules = False # Old implementation - NOT USED.       
        self.full_1r = True    # Inversed route sections are checked for 1 route: a = [1,2,3,4,5], m1 = [1,4',3',2',5], m1_inv = [5',2,3,4,1']
        self.full_2r = True    # Inversed route sections are checked for 2 routes.
        self.find_first = True  # Return the first improving move found.
        self.test = True        # Test move - NOT USED.
        self.cri = cri
        
        
    def c_calc_remaining_caps(self, cum_route_load, pos):
        '''
        C implementation of remaining cap calculation - NOT USED.
        '''
        (sec_1, sec_2) = self.cri.calc_capacity(cum_route_load, pos)
        return(sec_1, sec_2)

    def calc_remaining_caps(self, cum_route_load, pos):
        '''
        Calculate the total capacity from position pos in a route.
        '''
        if pos > 0: sec_1 = cum_route_load[pos-1]
        else: sec_1 = 0 
        sec_2 = cum_route_load[-1] - sec_1
        return(sec_1, sec_2)
    
    def calc_link_cost(self, i_pos, j_pos, j_end, pre_arc, post_arc):
        '''
        Cost of linking route i with route j
        '''
        if (i_pos == 0) & (j_pos == j_end): return(-self.dumpCost) # Complete route is added to the end of another route, thus a route is removed.
        else: return(self.d[pre_arc][post_arc]) # Deadheading cost of link.

    def find_best_two_opt_same_spec_route(self, solution_cum_lists, solution_cum_lists_inv, rem_route, best_remove=1e300000):
        '''
        Route section is removed, inversed and replaced in original route.
        '''
        # Best move data with cost 0 (only improving moves are returned).
        move_available = False
        best_move_data = (best_remove, 0)

        # Route i information, including cumulative deadheading cost .
        i = rem_route
        routes_normal = solution_cum_lists[0]
        cum_dead_normal = solution_cum_lists[3]
        # Inversed information of route i - required since move is reversed. Information is pre-calculated for the full route.
        routes_inv_normal = solution_cum_lists_inv[0] 
        routes_inv_dead_normal = solution_cum_lists_inv[3]         
        
        # Inversed routes are checked in the full version.
        if self.full_1r:
            inv_routes = solution_cum_lists_inv[0]
            inv_cum_dead = solution_cum_lists_inv[3]
            inv_routes_inv = solution_cum_lists[0]
            inv_cum_dead_inv = solution_cum_lists[3]
        else:
            inv_routes = []
            inv_cum_dead = []
            inv_routes_inv = []
            inv_cum_dead_inv = []
        
        # Inversed route information is combined with normal route information.
        routes = routes_normal + inv_routes
        cum_dead = cum_dead_normal + inv_cum_dead
        routes_inv = routes_inv_normal + inv_routes_inv
        routes_inv_dead = routes_inv_dead_normal + inv_cum_dead_inv        
        
        nNormal_routes = len(routes_normal)
        if i >= nNormal_routes: # Represents an reversed route
            inv_penalty = routes_inv_dead_normal[i - nNormal_routes][-1] - cum_dead_normal[i - nNormal_routes][-1] # Penalty associated with reversing complete route.
        else:
            inv_penalty = 0
        
        # Final route i information - not very efficient.
        route_i = routes[i]
        cum_dead_i = cum_dead[i]
        route_i_inv = routes_inv[i]
        cum_dead_i_inv = routes_inv_dead[i]
        nPos_i = len(route_i)
        
        # Route between (including) section i_pos and j_pos is removed and inversed. 
        for i_pos in xrange(0, nPos_i - 1):
            (split_i_cost, pre_arc_i) = self.split_route_cost(route_i, i_pos)[:2] # Cost of splitting between i_pos - 1 and i_pos
            for j_pos in xrange(i_pos + 1, nPos_i):
                split_route_info = self.split_route_cost(route_i, j_pos + 1) # Cost of splitting between j_pos and j_pos + 1
                split_j_cost, post_arc_j = split_route_info[0], split_route_info[2]
                   
                dead_seg_old = cum_dead_i[j_pos] - cum_dead_i[i_pos] # Deadheading cost of removed section 
                dead_seg_new = cum_dead_i_inv[nPos_i - i_pos - 1] - cum_dead_i_inv[nPos_i - j_pos - 1] # Inversed deadheading cost of removed section.
                
                post_inv_arc_i = route_i_inv[nPos_i - j_pos - 1] #  inverse arc of new start of route section. Can be simplified using split route information, but then an inverse check has to be performed.
                pre_inv_arc_j = route_i_inv[nPos_i - i_pos - 1] # inverse arc of new end of route section. Can be simplified using split route information, but then an inverse check has to be performed.
                
                delta_i = self.d[pre_arc_i][post_inv_arc_i] - split_i_cost # Net cost of relinking route with new beginning of the route section.
                delta_j = self.d[pre_inv_arc_j][post_arc_j] - split_j_cost # Net cost of relinking route with new ending of the route section.
                
                # Net cost of move: new deadheading cost if reversed section - old deadheading cost, plus new link costs, plus route reversed penalty.
                net_cost = dead_seg_new - dead_seg_old + delta_i + delta_j + inv_penalty
                if net_cost < best_move_data[0]:
                    move_available = True
                    if i >= nNormal_routes: inv_i = True
                    else: inv_i = False
                    best_move_data = (net_cost, i, i_pos, j_pos, inv_i, '2opt-same')
                    if self.find_first: break
            
            if move_available: 
                if self.find_first: break
                                                        
        return(move_available, best_move_data)

    def find_best_two_opt_other_spec_route(self, solution_cum_lists, inv_solution_cum_lists, route_rem, route_add, best_remove=1e300000):
        '''
        End section of routes are exchanged. Allows for a complete route to be added to the end of another route.
        '''
        # Best move data with cost 0 (only improving moves are returned).
        move_available = False
        best_move_data = (best_remove, 0)
        
        # Route i information.
        i = route_rem
        j = route_add
        normal_routes = solution_cum_lists[0]
        normal_cum_loads = solution_cum_lists[1]
        
        # Reversed route information.
        if self.full_2r:
            inv_routes = inv_solution_cum_lists[0]
            inv_cum_loads = inv_solution_cum_lists[1]
        else:
            inv_routes = []
            inv_cum_loads = []
        
        routes = normal_routes + inv_routes
        cum_loads = normal_cum_loads + inv_cum_loads
        
        n_normal_routes = len(normal_routes)
        
        route_i = routes[i]
        cum_load_i = cum_loads[i]
        nPos_i = len(route_i) 

        route_j = routes[j] # SHOULD BE CALCULATED OUTSIDE THE MAIN FOR LOOP!
        cum_load_j = cum_loads[j] # SHOULD BE CALCULATED OUTSIDE THE MAIN FOR LOOP!
        nPos_j = len(route_j) # SHOULD BE CALCULATED OUTSIDE THE MAIN FOR LOOP!

        if i >= n_normal_routes: # Represent a reversed route i. Route j is accounted for in for loop.
            inv_cost_i = inv_solution_cum_lists[3][i-n_normal_routes][-1] - solution_cum_lists[3][i-n_normal_routes][-1]
        else:
            inv_cost_i = 0
        
        if j >= n_normal_routes: # SHOULD BE CALCULATED OUTSIDE THE MAIN FOR LOOP!
            inv_cost_j = inv_solution_cum_lists[3][j-n_normal_routes][-1] - solution_cum_lists[3][j-n_normal_routes][-1]
        else:
            inv_cost_j = 0
        
        # Sections starting at i_pos is removed and exchanged with section starting at route j_pos - with last positions
        # only one section is removed and added to the end of the other route.
        for i_pos in xrange(nPos_i+1):
            (split_i_cost, pre_arc_i, post_arc_i) = self.split_route_cost(route_i, i_pos) # Cost of removing the end of route i
            (sec_i1, sec_i2) = self.calc_remaining_caps(cum_load_i, i_pos) # Calculate the load of the beginning and end sections.
    
            #if j <> (i + n_normal_routes): continue # WHOLE PROCEDURE SHOULD BE SKIPPED IF THIS IS THE CASE!
                
            for j_pos in xrange(nPos_j+1):
                (sec_j1, sec_j2) = self.calc_remaining_caps(cum_load_j, j_pos) # Calculate the load of the beginning and end sections.
                if sec_i2 + sec_j1 > self.capacity: break # load of section j1 will only become more, so move to next sec_i2. 
                elif  sec_i1 + sec_j2 <= self.capacity:
                    (split_j_cost, pre_arc_j, post_arc_j) =  self.split_route_cost(route_j, j_pos) # Cost of removing the end of route j
                    new_cost_i = self.calc_link_cost(i_pos, j_pos, nPos_j, pre_arc_i, post_arc_j) # Adding end of j to beginning of i 
                    new_cost_j = self.calc_link_cost(j_pos, i_pos, nPos_i, pre_arc_j, post_arc_i) # Adding end of i to beginning of j
                    
                    # Net cost of move
                    delta_i = new_cost_i - split_i_cost
                    delta_j = new_cost_j - split_j_cost
                    net_cost = delta_i + delta_j + inv_cost_i + inv_cost_j # Reversed route penalty.
                    if net_cost < best_move_data[0]:
                        move_available = True
                        if i >= n_normal_routes:inv_i = True
                        else: inv_i = False
                        if j >= n_normal_routes:inv_j = True
                        else: inv_j = False
                        best_move_data = (net_cost, new_cost_i, new_cost_j, i, i_pos, j, j_pos, inv_i, inv_j, '2opt-other')                            
                        if self.find_first: break
        
            if move_available: 
                if self.find_first: break 
                      
        return(move_available, best_move_data)

    def find_best_two_opt_same_py(self, solution_cum_lists, solution_cum_lists_inv, best_remove = 0):
        '''
        Perform internal two-opt move on all routes, including reversed route. Can be simplified by first doing two-opt on normal route,
        and then doing two-opt on reversed routes.
        '''
        best_move_available = False
        best_move_data = (best_remove, 0)
        if self.full_1r: nRoutes = 2*len(solution_cum_lists[0]) # Dirty!
        else: nRoutes = len(solution_cum_lists[0])
        for route_rem in xrange(nRoutes):
            (move_available, move_data) = self.find_best_two_opt_same_spec_route(solution_cum_lists, solution_cum_lists_inv, route_rem, best_move_data[0])
            if move_available:
                if move_data[0] < best_move_data[0]:
                    best_move_data = move_data
                    best_move_available = True
                    if self.find_first: break
        return(best_move_available, best_move_data)

    def find_best_two_opt_other_py(self, solution_cum_lists, solution_cum_lists_inv, best_remove = 0):
        '''
        Perform two-opt moves between two routes, including reversed routes. Can be simplified by first doing two-opt on normal routes,
        and then doing two-opt on reversed routes.
        '''
        best_move_available = False
        best_move_data = (best_remove, 0)
        n_normal_routes = len(solution_cum_lists[0])
        if self.full_2r: nRoutes = 2*len(solution_cum_lists[0])
        else: nRoutes = len(solution_cum_lists[0]) # Dirty!
        for route_rem in xrange(nRoutes - 1):
            for route_add in xrange(route_rem + 1, nRoutes):
                # CHECK THAT ROUTE i IS NOT THE INVERSED OF ROUTE j! (Simple continue statement).
                if route_add == (route_rem + n_normal_routes): continue
                (move_available, move_data) = self.find_best_two_opt_other_spec_route(solution_cum_lists, solution_cum_lists_inv, 
                                                                                      route_rem, route_add, best_move_data[0])
                if move_available:
                    if move_data[0] < best_move_data[0]:
                        best_move_data = move_data
                        best_move_available = True
                        if self.find_first: break
            if best_move_available: 
                if self.find_first: break
        return(best_move_available, best_move_data)    

    def c_find_best_two_opt_other(self, solution_cum_lists, solution_cum_lists_inv):
        (move_available, best_move_data) = self.cri.find_best_two_opt_other(solution_cum_lists, solution_cum_lists_inv, 
                                                                       self.full_2r, self.find_first)
        return(move_available, best_move_data)        

    def c_find_best_two_opt_same(self, solution_cum_lists, solution_cum_lists_inv):
        (move_available, best_move_data) = self.cri.find_best_two_opt_same(solution_cum_lists, solution_cum_lists_inv, 
                                                                      self.full_1r, self.find_first)
        return(move_available, best_move_data)      
    
    def find_best_two_opt_other(self, solution_cum_lists, solution_cum_lists_inv):
        if self.c_modules: return(self.c_find_best_two_opt_other(solution_cum_lists, solution_cum_lists_inv))
        else: return(self.find_best_two_opt_other_py(solution_cum_lists, solution_cum_lists_inv))

    def find_best_two_opt_same(self, solution_cum_lists, solution_cum_lists_inv):
        if self.c_modules: return(self.c_find_best_two_opt_same(solution_cum_lists, solution_cum_lists_inv))
        else: return(self.find_best_two_opt_same_py(solution_cum_lists, solution_cum_lists_inv))

class multiple_neighbourhood_search(make_neighbourhood_moves):
    
    def __init__(self, info, cri):
        '''
        Move operators are chosen and the best move is implemented. Terminates when no-more improving moves
        can be found. Options of performing moves on one or two routes, reducing number of routes, and finding
        the optimal orientation of all edge tasks in a route.
        '''
        self.Reduce_Trips = Reduce_Trips(info) # Reduce trips
        self.RI = remove_insert_neighbourhood(info, cri)
        self.SE = exchange_neighbourhood(info, cri)
        self.TwoOpt = two_opt_neighourhood(info, cri)
        
        self.info = info
        self.builder = py_solution_builders.build_solutions(info)
        self.displaySolution = display_solution_stats(info)
        self.d = info.d
        self.capacity = info.capacity
        self.demand = info.demandL
        self.service = info.serveCostL
        self.dumpCost = info.dumpCost
        self.depot = info.depotnewkey
        
        self.RI_1r_flag = True # Perform remove insert on a single route
        self.RI_2r_flag = True # Perform remove insert between two routes
        self.SE_1r_flag = True # Perform exchange on a single route
        self.SE_2r_flag = True # Perform exchange on two routes.
        self.TwoOpt_1r_flag = True # Perform two opt on one route
        self.TwoOpt_2r_flag = True # Perform two opt between two routes
        
        self.RI.c_modules = True # Use remove insert c modules
        self.SE.c_modules = True # Use exchange c modules
        self.TwoOpt.c_modules = True # Use TwoOpt c modules

        self.find_first_full = True # Return the first improving move found
        self.reduce_routes = False # Try to Reduce routes after each iteration.
        self.opt_direct = False# Determine optimal service direction of edge tasks in all routes after each iteration. 
        
        self.test = False # Test final solution
        
        # Return move information
        self.return_move_data = False
        self.move_data = []
        self.print_execution = False
        
        self.vd1_seq = False
        self.vd2_seq = False

    def setTwOptSearch(self):
        
        self.RI_1r_flag = False # Perform remove insert on a single route
        self.RI_2r_flag = False # Perform remove insert between two routes
        self.RI.find_first = False
        self.SE_1r_flag = False # Perform exchange on a single route
        self.SE_2r_flag = False # Perform exchange on two routes.
        self.SE.find_first = False
        
        self.find_first_full = True
        self.TwoOpt_1r_flag = True # Perform two opt on one route
        self.TwoOpt_2r_flag = True # Perform two opt between two routes
        self.TwoOpt.find_first = True
        
    def setFullSearch(self):
        
        self.RI_1r_flag = True # Perform remove insert on a single route
        self.RI_2r_flag = True # Perform remove insert between two routes
        self.SE_1r_flag = True # Perform exchange on a single route
        self.SE_2r_flag = True # Perform exchange on two routes.
        self.TwoOpt_1r_flag = True # Perform two opt on one route
        self.TwoOpt_2r_flag = True # Perform two opt between two routes
        
        self.find_first_full = False
        self.RI.find_first = False
        self.SE.find_first = False
        self.TwoOpt.find_first = False

    def setFullPartialSearch(self):
        
        self.RI_1r_flag = True # Perform remove insert on a single route
        self.RI_2r_flag = True # Perform remove insert between two routes
        self.SE_1r_flag = True # Perform exchange on a single route
        self.SE_2r_flag = True # Perform exchange on two routes.
        self.TwoOpt_1r_flag = False # Perform two opt on one route
        self.TwoOpt_2r_flag = True # Perform two opt between two routes
        self.TwoOpt.full_2r = False
        
        self.find_first_full = False
        self.RI.find_first = False
        self.SE.find_first = False
        self.TwoOpt.find_first = False

    def setFullFindFirst(self):
        
        self.RI_1r_flag = True # Perform remove insert on a single route
        self.RI_2r_flag = True # Perform remove insert between two routes
        self.SE_1r_flag = True # Perform exchange on a single route
        self.SE_2r_flag = True # Perform exchange on two routes.
        
        self.find_first_full = True
        self.RI.find_first = True
        self.SE.find_first = True
        self.TwoOpt.find_first = True

    def set_VND_first_seq1(self):
        
        self.RI_1r_flag = True # Perform remove insert on a single route
        self.RI_2r_flag = True # Perform remove insert between two routes
        self.SE_1r_flag = True # Perform exchange on a single route
        self.SE_2r_flag = True # Perform exchange on two routes.
        
        self.find_first_full = True
        self.RI.find_first = True
        self.SE.find_first = True
        self.TwoOpt.find_first = True
        
        self.vd1_seq = True

    def set_VND_first_seq2(self):
        
        self.RI_1r_flag = True # Perform remove insert on a single route
        self.RI_2r_flag = True # Perform remove insert between two routes
        self.SE_1r_flag = True # Perform exchange on a single route
        self.SE_2r_flag = True # Perform exchange on two routes.
        
        self.find_first_full = True
        self.RI.find_first = True
        self.SE.find_first = True
        self.TwoOpt.find_first = True
        
        self.vd2_seq = True
      
    def set_VND_best_seq1(self):
        '''
        Best performing first
        '''
        self.RI_1r_flag = True # Perform remove insert on a single route
        self.RI_2r_flag = True # Perform remove insert between two routes
        self.SE_1r_flag = True # Perform exchange on a single route
        self.SE_2r_flag = True # Perform exchange on two routes.
        
        self.find_first_full = True
        self.RI.find_first = False
        self.SE.find_first = False
        self.TwoOpt.find_first = False
        
        self.vd1_seq = True

    def set_VND_best_seq2(self):
        '''
        Simplest first
        '''        
        self.RI_1r_flag = True # Perform remove insert on a single route
        self.RI_2r_flag = True # Perform remove insert between two routes
        self.SE_1r_flag = True # Perform exchange on a single route
        self.SE_2r_flag = True # Perform exchange on two routes.
        
        self.find_first_full = True
        self.RI.find_first = False
        self.SE.find_first = False
        self.TwoOpt.find_first = False
        
        self.vd2_seq = True
        
        
    def find_best_move(self, solution_lists, solution_cum_lists, solution_cum_lists_inv):
        '''
        Find the best improving move from all the neighbourhoods.
        '''
        savings = [1e300000]*6
        moves = [0]*6
        move_available = [0]*6
        if self.RI_1r_flag:
            (move_available[0], moves[0]) = self.RI.find_best_remove_insert_same(solution_lists)
            savings[0] = moves[0][0]
        if self.RI_2r_flag: 
            (move_available[1], moves[1])  = self.RI.find_best_remove_insert_other(solution_lists)
            savings[1] = moves[1][0]
        if self.SE_1r_flag:
            (move_available[2], moves[2])  = self.SE.find_best_exchange_same(solution_lists)
            savings[2] = moves[2][0]
        if self.SE_2r_flag:
            (move_available[3], moves[3])  = self.SE.find_best_exchange_other(solution_lists)
            savings[3] = moves[3][0]
        if self.TwoOpt_1r_flag:
            (move_available[4], moves[4])  = self.TwoOpt.find_best_two_opt_same(solution_cum_lists, solution_cum_lists_inv)
            savings[4] = moves[4][0]            
        if self.TwoOpt_2r_flag:
            (move_available[5], moves[5])  = self.TwoOpt.find_best_two_opt_other(solution_cum_lists, solution_cum_lists_inv)
            savings[5] = moves[5][0]             
        best_move_i = np.argmin(savings)
        return(move_available[best_move_i], moves[best_move_i])
    
    def find_first_best_move(self, solution_lists, solution_cum_lists, solution_cum_lists_inv):
        '''
        Find the first improving move from all the neighbourhoods. SHOULDN'T BE SEPERATE.
        '''
        if self.RI_1r_flag:
            (move_available, moves) = self.RI.find_best_remove_insert_same(solution_lists)
            if move_available:return(move_available, moves)
        if self.RI_2r_flag: 
            (move_available, moves)  = self.RI.find_best_remove_insert_other(solution_lists)
            if move_available:return(move_available, moves)
        if self.SE_1r_flag:
            (move_available, moves)  = self.SE.find_best_exchange_same(solution_lists)
            if move_available:return(move_available, moves)
        if self.SE_2r_flag:
            (move_available, moves)  = self.SE.find_best_exchange_other(solution_lists)
            if move_available:return(move_available, moves)
        if self.TwoOpt_1r_flag:
            (move_available, moves)  = self.TwoOpt.find_best_two_opt_same(solution_cum_lists, solution_cum_lists_inv)         
            if move_available:return(move_available, moves)
        if self.TwoOpt_2r_flag:
            (move_available, moves)  = self.TwoOpt.find_best_two_opt_other(solution_cum_lists, solution_cum_lists_inv)            
            if move_available:return(move_available, moves)
        return(False, (1e300000, 0))

    def VND_seq1(self, solution_lists, solution_cum_lists, solution_cum_lists_inv):
        '''
        Find the first improving move from all the neighbourhoods. SHOULDN'T BE SEPERATE.
        '''
        if self.RI_2r_flag: 
            (move_available, moves)  = self.RI.find_best_remove_insert_other(solution_lists)
            if move_available:return(move_available, moves)
        if self.RI_1r_flag:
            (move_available, moves) = self.RI.find_best_remove_insert_same(solution_lists)
            if move_available:return(move_available, moves)
        if self.TwoOpt_1r_flag:
            (move_available, moves)  = self.TwoOpt.find_best_two_opt_same(solution_cum_lists, solution_cum_lists_inv)         
            if move_available:return(move_available, moves)
        if self.TwoOpt_2r_flag:
            (move_available, moves)  = self.TwoOpt.find_best_two_opt_other(solution_cum_lists, solution_cum_lists_inv)            
            if move_available:return(move_available, moves)
        if self.SE_2r_flag:
            (move_available, moves)  = self.SE.find_best_exchange_other(solution_lists)
            if move_available:return(move_available, moves)
        if self.SE_1r_flag:
            (move_available, moves)  = self.SE.find_best_exchange_same(solution_lists)
            if move_available:return(move_available, moves)
        return(False, (1e300000, 0))

    def VND_seq2(self, solution_lists, solution_cum_lists, solution_cum_lists_inv):
        '''
        Find the first improving move from all the neighbourhoods. SHOULDN'T BE SEPERATE.
        '''
        if self.SE_1r_flag:
            (move_available, moves)  = self.SE.find_best_exchange_same(solution_lists)
            if move_available:return(move_available, moves)
        if self.RI_1r_flag:
            (move_available, moves) = self.RI.find_best_remove_insert_same(solution_lists)
            if move_available:return(move_available, moves)
        if self.SE_2r_flag:
            (move_available, moves)  = self.SE.find_best_exchange_other(solution_lists)
            if move_available:return(move_available, moves)
        if self.RI_2r_flag: 
            (move_available, moves)  = self.RI.find_best_remove_insert_other(solution_lists)
            if move_available:return(move_available, moves)
        if self.TwoOpt_1r_flag:
            (move_available, moves)  = self.TwoOpt.find_best_two_opt_same(solution_cum_lists, solution_cum_lists_inv)         
            if move_available:return(move_available, moves)
        if self.TwoOpt_2r_flag:
            (move_available, moves)  = self.TwoOpt.find_best_two_opt_other(solution_cum_lists, solution_cum_lists_inv)            
            if move_available:return(move_available, moves)
        return(False, (1e300000, 0))
            
    def local_search(self, solution_lists, itter = 0, outputPureList = [], break_first = False):
        improved = False
        i = 0
        total_Savings = 0 
        outputList = []
        
        if self.print_execution:
            print('=======================================================')
            print(' Local search')
            print('-------------------------------------------------------')
        while True:
            iterStart = clock()
            i += 1       
            itter += 1
            if self.reduce_routes: # Try to reduce the number of routes.
                orig = len(solution_lists[0])
                (change, solution_lists) = self.Reduce_Trips.reduce_carp_routes(solution_lists)
                if change: 
                    new_orig = len(solution_lists[0]) 
                    if self.print_execution: print('Routes reduced by %i'%(orig - new_orig))
            if self.opt_direct: # Find the optimal service directions for edge tasks
                (routes, deadheads) = self.TwoOpt.opdirect.opt_routes2(solution_lists[0])
                diff_total = sum(deadheads) - sum(solution_lists[3])
                if diff_total < 0: # If improved, update the deadheading costs
                    total_Savings += diff_total
                    if self.print_execution: print(diff_total, 'OptDirect saving')
                    for i in xrange(len(deadheads)):
                        diff = deadheads[i] - solution_lists[3][i]
                        solution_lists[0][i] = routes[i]
                        solution_lists[3][i] += diff
                        solution_lists[4][i] += diff
            
            # Calculate reversed routes if TwoOpt will be used.
            if (self.TwoOpt_1r_flag == True)|(self.TwoOpt_2r_flag == True):
                solution_cum_lists = self.builder.build_CARP_cum_list_from_routes(solution_lists[0]) 
                inv_routes = self.TwoOpt.opdirect.reverse_all_routes(solution_lists[0])[0]
                solution_cum_lists_inv = self.builder.build_CARP_cum_list_from_routes(inv_routes) 
            else:
                solution_cum_lists_inv = []
                solution_cum_lists = []
            
            # Find first or best improving move
            if self.find_first_full: 
                if self.vd1_seq:
                    (move_available, best_move_data) = self.VND_seq1(solution_lists, solution_cum_lists, solution_cum_lists_inv)
                elif self.vd2_seq:
                    (move_available, best_move_data) = self.VND_seq2(solution_lists, solution_cum_lists, solution_cum_lists_inv)
                else:
                    (move_available, best_move_data) = self.find_first_best_move(solution_lists, solution_cum_lists, solution_cum_lists_inv)
            else: 
                (move_available, best_move_data) = self.find_best_move(solution_lists, solution_cum_lists, solution_cum_lists_inv)
            
            # If an improving move has been found, make the move and go to next iteration
            if move_available:
                if best_move_data[-1] in {'exchange-same', 'exchange-other', '2opt-other'}:
                    inv_flag = best_move_data[-3] or best_move_data[-2]
                else:
                    inv_flag = best_move_data[-2]
                if inv_flag: inv_text = 'inv'
                else: inv_text = ''
                #print("T %i \t Saving: %i \t Type: %s %s" %(itter,best_move_data[0], best_move_data[-1], inv_text))
                #self.move_data.append(''%best_move_data[-1],)
                #if self.print_execution: print(best_move_data)
                total_Savings += best_move_data[0]
                improved = True
                (solution_lists, solution_cum_lists) =  self.make_move(solution_lists, solution_cum_lists, solution_cum_lists_inv, best_move_data)
                if self.return_move_data:self.move_data.append(best_move_data)
                iterStop = clock() - iterStart
                infotuple = (i, best_move_data[-1],inv_flag,best_move_data[0],iterStop)
                output = '%i,%s,%s,%i,%.4f\n'%infotuple
                outputList.append(output)
                outputPureList.append(infotuple)
                if break_first: 
                    #saving_pers = (-total_Savings)/float(original_cost)
                    break
            else:
                #print("T %i \t Saving: %i \t Type: %s %s" %(itter,0,'',''))
                #saving_pers = (-total_Savings)/float(original_cost)
                if self.print_execution:
                    print('-------------------------------------------------------')
                    #print(' Total saving: %i (%.4f)' %(total_Savings,saving_pers))
                    print('=======================================================')
                break
        saving_pers = 0
        return(solution_lists, itter, saving_pers, improved, outputList, outputPureList, total_Savings)
    
    def improve_local_search(self, solution, break_first = False):
        '''
        Perform local search.
        '''
        self.output = []
        solution_lists = self.builder.build_CARP_list(solution) # Solution list used to construct neighbourhoods. Does not include depots but includes depot costs.
        (solution_lists, i, saving_pers, improved, outputList, outputPureList, total_Savings) = self.local_search(solution_lists, solution, break_first) # Perform local seach and returns the savings, if any.
        (routes, loads, service, deadhead, costs) = solution_lists # Rebuild solution into standard dictionary.
        solution = self.builder.build_CARP_dict_from_list(routes, loads, service, deadhead, costs)
        if self.print_execution: self.displaySolution.display_CARP_solution_info(solution) # Display final solution information.
        if self.test: test_solution(self.info, solution) # Test final solution.
        return(solution, i, saving_pers, improved, outputList, outputPureList, total_Savings)

    def local_search_one_route(self, solution_lists, itter = 0, break_first = False):
        '''
        Perform local search.
        '''
        outputPureList = []
        nRoutes = len(solution_lists[0])
        (routes, loads, service, deadhead, costs) = deepcopy(solution_lists) # Rebuild solution into standard dictionary.
        total_saving = 0
        RI_flag_store, SE_flag_store, TowOpt_flag_store = self.RI_2r_flag, self.SE_2r_flag, self.TwoOpt_2r_flag
        self.RI_2r_flag = self.SE_2r_flag = self.TwoOpt_2r_flag = False # Perform remove inse
        for iRoute in range(nRoutes):
            solution_lists_iRoute = [[routes[iRoute]], [loads[iRoute]], [service[iRoute]], [deadhead[iRoute]], [costs[iRoute]]]
            (solution_lists_iRoute, itter, saving_pers, improved, outputList, outputPureList, total_SavingsR) = self.local_search(solution_lists_iRoute, itter, outputPureList) # Perform local seach and returns the savings, if any.
            solution_lists[0][iRoute] = solution_lists_iRoute[0][0] 
            solution_lists[1][iRoute] = solution_lists_iRoute[1][0]
            solution_lists[2][iRoute] = solution_lists_iRoute[2][0]
            solution_lists[3][iRoute] = solution_lists_iRoute[3][0]
            solution_lists[4][iRoute] = solution_lists_iRoute[4][0]
            total_saving += total_SavingsR
        if total_saving < 0: improved = True
        self.RI_2r_flag, self.SE_2r_flag, self.TwoOpt_2r_flag = RI_flag_store, SE_flag_store, TowOpt_flag_store
        return(solution_lists, itter, saving_pers, improved, outputList, outputPureList, total_saving)
        
    def improve_single_route_local_search(self, solution, break_first = False):
        '''
        Perform local search.
        '''
        print_exec_save = self.print_execution
        self.print_execution = False
        solution_lists = self.builder.build_CARP_list(solution) # Solution list used to construct neighbourhoods. Does not include depots but includes depot costs.
        nRoutes = len(solution_lists[0])
        (routes, loads, service, deadhead, costs) = solution_lists # Rebuild solution into standard dictionary.
        total_saving = 0
        original_cost = solution['TotalCost']
        RI_flag_store, SE_flag_store, TowOpt_flag_store = self.RI_2r_flag, self.SE_2r_flag, self.TwoOpt_2r_flag
        self.RI_2r_flag = self.SE_2r_flag = self.TwoOpt_2r_flag = False # Perform remove inse
        for iRoute in range(nRoutes):
            route_cost = costs[iRoute]
            solution_single = self.builder.build_CARP_single_route(solution, iRoute)
            solution_lists_iRoute = [[routes[iRoute]], [loads[iRoute]], [service[iRoute]], [deadhead[iRoute]], [costs[iRoute]]]
            (solution_lists_iRoute, i, saving_pers, improved) = self.local_search(solution_lists_iRoute, solution_single, break_first) # Perform local seach and returns the savings, if any.
            solution_lists[0][iRoute] = solution_lists_iRoute[0][0] 
            solution_lists[1][iRoute] = solution_lists_iRoute[1][0]
            solution_lists[2][iRoute] = solution_lists_iRoute[2][0]
            solution_lists[3][iRoute] = solution_lists_iRoute[3][0]
            solution_lists[4][iRoute] = solution_lists_iRoute[4][0]
            route_saving = solution_lists_iRoute[4][0] - route_cost
            if (print_exec_save == True)&(route_saving < 0):
                total_saving += route_saving
                print("Route %i Total Saving: %i" %(iRoute, route_saving))
                print('')
        self.print_execution = print_exec_save 
        self.RI_2r_flag, self.SE_2r_flag, self.TwoOpt_2r_flag = RI_flag_store, SE_flag_store, TowOpt_flag_store
        (routes, loads, service, deadhead, costs) = solution_lists # Rebuild solution into standard dictionary.
        solution = self.builder.build_CARP_dict_from_list(routes, loads, service, deadhead, costs)
        if self.print_execution:
            print('-------------------------------------------------------')
            print(' Total saving: %i (%.4f)' %(-total_saving,total_saving/original_cost))
            print('=======================================================')
        if self.print_execution: self.builder.display_solution_info(solution) # Display final solution information.
        if self.test: test_solution(self.info, solution) # Test final solution.
        return(solution, i, saving_pers, improved)

if __name__ == "__main__":
    problemset = 'Lpr'
    problem = 'info'
    
    
    
    
    
    