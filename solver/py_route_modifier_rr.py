'''
Created on 22 Jan 2012

@author: elias
'''

huge = 1e30000
import numpy as np

class insert_arc_in_route(object):
    
    def __init__(self, info):
        self.d = info.d
        self.inv_arcs = info.reqInvArcList
        self.capacity = info.capacity
        self.demand = info.demandL
        self.service = info.serveCostL
        self.max_trip = info.maxTrip
    
    def test_load_cap(self, arc, route_load):
        if (self.demand[arc] + route_load) <= self.capacity: return(True)
        else: return(False)

    def test_cost_cap(self, route_cost, insert_cost, arc):
        if (self.service[arc] + insert_cost + route_cost) <= self.max_trip: return(True)
        else: return(False)
        
    def calc_split_cost(self, route, position):
        split_cost = self.d[route[position-1]][route[position]]
        return(split_cost)
        
    def calc_insert_cost(self, insert_arc, route, position):
        a = route[position-1]
        b = route[position]
        insert_cost = self.d[route[position-1]][insert_arc] + self.d[insert_arc][route[position]]
        return(insert_cost)
    
    def calc_net_insert_cost(self, insert_arc, route, i):
        net_cost = self.calc_insert_cost(insert_arc, route, i) - self.calc_split_cost(route, i)
        return(net_cost)
    
    def check_best(self, best_cost, best_position, candidate_cost, candidate_position):
        if candidate_cost < best_cost:
            best_cost = candidate_cost
            best_position = candidate_position
            new_best = True
        else:new_best = False
        return(best_cost, best_position, new_best)
        
    def best_single_arc_route_insert(self, insert_arc, route):
        nArcsInRoute = len(route)
        best_insert_cost = self.calc_net_insert_cost(insert_arc, route, 1)
        best_insert_position = 1
        for i in xrange(2, nArcsInRoute-1):
            insert_cost = self.calc_net_insert_cost(insert_arc, route, i)
            (best_insert_cost, best_insert_position) = self.check_best(best_insert_cost, 
                                                                       best_insert_position, 
                                                                       insert_cost, 
                                                                       i)[:2]
        return(best_insert_cost, best_insert_position)
    
    def best_single_arc_insertion_multiple_routes(self, routes, insert_arc):
        best_insert_cost_global, best_insert_position_global, best_insert_route = huge, None, 0
        for i, route in enumerate(routes):
            (best_insert_cost, best_insert_position) = self.best_single_arc_route_insert(insert_arc, 
                                                                                         route)
            (best_insert_cost_global, best_insert_position_global, new_best) = self.check_best(best_insert_cost_global,
                                                                                               best_insert_position_global,
                                                                                               best_insert_cost, 
                                                                                               best_insert_position)
            if new_best: best_insert_route = i
        return(best_insert_cost_global, best_insert_position_global, best_insert_route)

    def best_single_arc_insertion_multiple_routes_cap(self, routes, loads, insert_arc):
        best_insert_cost_global, best_insert_position_global, best_insert_route = huge, None, 0
        for i, route in enumerate(routes):
            if self.test_load_cap(insert_arc, loads[i]):
                (best_insert_cost, best_insert_position) = self.best_single_arc_route_insert(insert_arc, route)
                (best_insert_cost_global, best_insert_position_global, new_best) = self.check_best(best_insert_cost_global,
                                                                                                   best_insert_position_global,
                                                                                                   best_insert_cost, 
                                                                                                   best_insert_position)
            else: new_best = False
            if new_best: best_insert_route = i
        return(best_insert_cost_global, best_insert_position_global, best_insert_route)

#    def best_single_arc_insertion_multiple_IF_routes(self, routes, insert_arc):
#        best_insert_cost_global, best_insert_position_global = huge, None 
#        best_insert_route, best_insert_trip = 0, 0
#        for i, route in enumerate(routes):
#            for j, trip in enumerate(route):
#                if j == len(route) - 1: temp_trip = trip[:-1]
#                else: temp_trip = deepcopy(trip)
#                (best_insert_cost, best_insert_position) = self.best_single_arc_route_insert(insert_arc, 
#                                                                                             temp_trip)
#                (best_insert_cost_global, best_insert_position_global, new_best) = self.check_best(best_insert_cost_global,
#                                                                                                   best_insert_position_global,
#                                                                                                   best_insert_cost, 
#                                                                                                   best_insert_position)
#                if new_best: 
#                    best_insert_route = i
#                    best_insert_trip = j
#        return(best_insert_cost_global, best_insert_position_global, best_insert_route, best_insert_trip)
#    
#    def best_single_arc_insertion_multiple_IF_routes_cap(self, routes, costs, loads, insert_arc):
#        best_insert_cost_global, best_insert_position_global = huge, None 
#        best_insert_route, best_insert_trip = 0, 0
#        for i, route in enumerate(routes):
#            if self.test_cost_cap(costs[i], 0, insert_arc):
#                for j, trip in enumerate(route):
#                    if self.test_load_cap(insert_arc, loads[i][j]):
#                        if j == len(route) - 1: temp_trip = trip[:-1]
#                        else: temp_trip = deepcopy(trip)
#                        (best_insert_cost, best_insert_position) = self.best_single_arc_route_insert(insert_arc, 
#                                                                                                     temp_trip)
#                        if self.test_cost_cap(costs[i], best_insert_cost, insert_arc):
#                            (best_insert_cost_global, best_insert_position_global, new_best) = self.check_best(best_insert_cost_global,
#                                                                                                               best_insert_position_global,
#                                                                                                               best_insert_cost, 
#                                                                                                               best_insert_position)
#                            if new_best: 
#                                best_insert_route = i
#                                best_insert_trip = j
#        return(best_insert_cost_global, best_insert_position_global, best_insert_route, best_insert_trip)

class insert_arc_in_if_route(insert_arc_in_route):
    
    def __init__(self, info):
        insert_arc_in_route.__init__(self, info)
        self.depot = info.depotnewkey
        self.dumpCost = info.dumpCost
        self.if_cost = info.if_cost_np

    def calc_split_pre_if_depot(self, route):
        cost_split_pre_if = self.d[self.depot][route[0]]
        return(cost_split_pre_if)
     
    def calc_split_pre_if(self, route, pre_arc):
        cost_split_pre_if = self.if_cost[pre_arc][route[0]]
        return(cost_split_pre_if)
    
    def calc_split_post_if(self, route, post_arc):
        calc_split_post_if = self.if_cost[route[-1]][post_arc]
        return(calc_split_post_if)

    def calc_insert_pre_if(self, route, pre_arc, insert_arc):
        cost_insert_pre_if = self.if_cost[pre_arc][insert_arc] + self.d[insert_arc][route[0]]
        return(cost_insert_pre_if)
   
    def calc_insert_pre_if_depot(self, route, insert_arc):
        cost_insert_pre_if = self.d[self.depot][insert_arc] + self.d[insert_arc][route[0]]
        return(cost_insert_pre_if)
   
    def calc_insert_post_if(self, route, post_arc, insert_arc):
        cost_insert_post_if = self.d[route[-1]][insert_arc] + self.if_cost[insert_arc][post_arc]
        return(cost_insert_post_if)
    
    def calc_net_pre_if_insert(self, route, pre_arc, insert_arc):
        net_cost = self.calc_insert_pre_if(route, pre_arc, insert_arc) - self.calc_split_pre_if(route, pre_arc)
        return(net_cost)

    def calc_net_pre_if_insert_depot(self, route, insert_arc):
        net_cost = self.calc_insert_pre_if_depot(route, insert_arc) - self.calc_split_pre_if_depot(route)
        return(net_cost)

    def calc_net_post_if_insert(self, route, post_arc, insert_arc):
        net_cost = self.calc_insert_post_if(route, post_arc, insert_arc) - self.calc_split_post_if(route, post_arc)
        return(net_cost)
    
    def best_single_arc_route_IF_insert(self, insert_arc, route, pre_arc, post_arc):
        nArcsInRoute = len(route)
        
        best_insert_position = 0
        if pre_arc == self.depot:
            best_insert_cost = self.calc_net_pre_if_insert_depot(route, insert_arc)
        else:
            best_insert_cost = self.calc_net_pre_if_insert(route, pre_arc, insert_arc)
        
        insert_cost = self.calc_net_post_if_insert(route, post_arc, insert_arc)
        insert_position = len(route)
        (best_insert_cost, best_insert_position) = self.check_best(best_insert_cost, 
                                                                   best_insert_position, 
                                                                   insert_cost, 
                                                                   insert_position)[:2]
        for i in xrange(1, nArcsInRoute-1):
            insert_cost = self.calc_net_insert_cost(insert_arc, route, i)
            (best_insert_cost, best_insert_position) = self.check_best(best_insert_cost, 
                                                                       best_insert_position, 
                                                                       insert_cost, 
                                                                       i)[:2]
        return(best_insert_cost, best_insert_position)
    
    def best_single_arc_insertion_multiple_IF_routes(self, routes, insert_arc):
        best_insert_cost_global, best_insert_position_global = huge, None 
        best_insert_route, best_insert_trip = 0, 0
        for i, route in enumerate(routes):
            for j, trip in enumerate(route):
                if j == 0: pre_arc = self.depot
                else: pre_arc = route[j-1][-1]
                if j == len(route) - 1: post_arc = self.depot
                else: post_arc = route[j+1][0]
                (best_insert_cost, best_insert_position) = self.best_single_arc_route_IF_insert(insert_arc, 
                                                                                                trip,pre_arc,
                                                                                                post_arc)
                (best_insert_cost_global, best_insert_position_global, new_best) = self.check_best(best_insert_cost_global,
                                                                                                   best_insert_position_global,
                                                                                                   best_insert_cost, 
                                                                                                   best_insert_position)
                if new_best: 
                    best_insert_route = i
                    best_insert_trip = j
        return(best_insert_cost_global, best_insert_position_global, best_insert_route, best_insert_trip)

    def best_single_arc_insertion_multiple_IF_routes_cap(self, routes, costs, loads, insert_arc):
        best_insert_cost_global, best_insert_position_global = huge, None 
        best_insert_route, best_insert_trip = 0, 0
        for i, route in enumerate(routes):
            if self.test_cost_cap(costs[i], 0, insert_arc):
                for j, trip in enumerate(route):
                    if self.test_load_cap(insert_arc, loads[i][j]):
                        if j == 0: pre_arc = self.depot
                        else: pre_arc = route[j-1][-1]
                        if j == len(route) - 1: post_arc = self.depot
                        else: post_arc = route[j+1][0]
                        (best_insert_cost, best_insert_position) = self.best_single_arc_route_IF_insert(insert_arc, 
                                                                                                        trip,pre_arc,
                                                                                                        post_arc)
                        if self.test_cost_cap(costs[i], best_insert_cost, insert_arc): 
                            (best_insert_cost_global, best_insert_position_global, new_best) = self.check_best(best_insert_cost_global,
                                                                                                               best_insert_position_global,
                                                                                                               best_insert_cost, 
                                                                                                               best_insert_position)
                            if new_best: 
                                best_insert_route = i
                                best_insert_trip = j
        return(best_insert_cost_global, best_insert_position_global, best_insert_route, best_insert_trip)
    
    def calc_insert_pre_trip(self, route, pre_arc, insert_arc):
        cost_insert_pre_trip = self.if_cost[pre_arc][insert_arc] + self.if_cost[insert_arc][route[0]]
        return(cost_insert_pre_trip)

    def calc_insert_pre_trip_depot(self, route, insert_arc):
        cost_insert_pre_trip = self.d[self.depot][insert_arc] + self.if_cost[insert_arc][route[0]]
        return(cost_insert_pre_trip)

    def calc_net_pre_trip_insert(self, route, pre_arc, insert_arc):
        net_cost = self.calc_insert_pre_trip(route, pre_arc, insert_arc) - self.calc_split_pre_if(route, pre_arc)
        return(net_cost)

    def calc_net_pre_trip_insert_depot(self, route, insert_arc):
        net_cost = self.calc_insert_pre_trip_depot(route, insert_arc) - self.calc_split_pre_if_depot(route)
        return(net_cost)
   
    def calc_insert_post_trip(self, route, post_arc, insert_arc):
        cost_insert_post_trip = self.if_cost[route[-1]][insert_arc] + self.if_cost[insert_arc][post_arc]
        return(cost_insert_post_trip)

    def calc_net_post_trip_insert(self, route, post_arc, insert_arc):
        net_cost = self.calc_insert_post_trip(route, post_arc, insert_arc) - self.calc_split_post_if(route, post_arc)
        return(net_cost)
    
    def best_singlearc_trip_insert_cap(self, routes, costs, loads, insert_arc):
        best_cost = huge
        best_position = best_route = None
        for i, route in enumerate(routes):
            if self.test_cost_cap(costs[i], self.dumpCost, insert_arc):
                for j, trip in enumerate(route):
                    if j == 0: 
                        net_cost = self.calc_net_pre_trip_insert_depot(trip, insert_arc)
                    else: 
                        pre_arc = route[j-1][-1]
                        net_cost = self.calc_net_pre_trip_insert(trip, pre_arc, insert_arc)
                    if self.test_cost_cap(costs[i], net_cost, insert_arc): 
                        (best_cost, 
                         best_position, 
                         new_best) = self.check_best(best_cost, 
                                                     best_position, 
                                                     net_cost,
                                                     j)
                        if new_best: best_route = i
                if self.test_cost_cap(costs[i], net_cost, insert_arc):
                    net_cost = self.calc_net_post_trip_insert(trip, self.depot, insert_arc)  
                    (best_cost, 
                     best_position, 
                     new_best) = self.check_best(best_cost, 
                                                 best_position, 
                                                 net_cost, 
                                                 j+1)
                    if new_best: best_route = i
        return(best_cost, best_position, best_route)   

class insert_multiple_arcs(insert_arc_in_if_route):
    
    def __init__(self, info):
        insert_arc_in_if_route.__init__(self, info)
        
    def update_carp_lists(self, solution_lists, route, position, arc, cost):
        (routes, loads, service, deadhead, costs) = solution_lists
        routes[route].insert(position, arc)
        loads[route] += self.demand[arc]
        service[route] += self.service[arc]
        costs[route] += cost + self.service[arc]
        deadhead[route] += cost
        solution_lists = (routes, loads, service,  deadhead, costs) 
        return(solution_lists)      
    
    def find_insert_arc_carp(self, solution_lists, arc):
        inv_insert_cost = huge
        (insert_cost, 
        insert_position, 
        insert_route) = self.best_single_arc_insertion_multiple_routes_cap(solution_lists[0], 
                                                                           solution_lists[1], arc)
        inv_insert_position = None
        if self.inv_arcs[arc]:
            inv_arc = self.inv_arcs[arc]
            (inv_insert_cost, 
             inv_insert_position, 
             inv_insert_route) = self.best_single_arc_insertion_multiple_routes_cap(solution_lists[0], 
                                                                                    solution_lists[1], inv_arc)
        if (insert_position == None)&(inv_insert_position == None):
            insert = False 
        elif (insert_cost < inv_insert_cost):
            insert = True
            solution_lists = self.update_carp_lists(solution_lists, insert_route, insert_position, arc, insert_cost)
        else:
            insert = True
            solution_lists = self.update_carp_lists(solution_lists, inv_insert_route, inv_insert_position, inv_arc, inv_insert_cost)            
        return(insert, solution_lists)
    
    def update_clarpif_lists(self, solution_lists, route, trip, position, arc, cost):
        (routes, loads, service, deadhead, costs, trip_loads, trip_service, trip_deadhead, trip_cost) = solution_lists
        routes[route][trip].insert(position, arc)
        costs[route] += cost + self.service[arc]
        loads[route] += self.demand[arc]
        service[route] += self.service[arc]
        deadhead[route] += cost
        trip_loads[route][trip] += self.demand[arc]
        trip_service[route][trip] += self.service[arc]
        trip_deadhead[route][trip] += cost
        trip_cost[route][trip] += cost + self.service[arc]
        solution_lists = (routes, loads, service, deadhead, costs, trip_loads, trip_service, trip_deadhead, trip_cost)
        return(solution_lists)
    
    def update_clarpif_lists_trip(self, solution_lists, route, trip, arc, cost):
        (routes, loads, service, deadhead, costs, trip_loads, trip_service, trip_deadhead, trip_cost) = solution_lists
        routes[route].insert(trip, [arc])
        costs[route] += cost + self.service[arc]
        loads[route] += self.demand[arc]
        service[route] += self.service[arc]
        deadhead[route] += cost
        trip_loads[route].insert(trip, self.demand[arc])
        trip_service[route].insert(trip, self.service[arc])
        trip_deadhead[route].insert(trip, cost)
        trip_cost[route].insert(trip, cost + self.service[arc])
        solution_lists = (routes, loads, service, deadhead, costs, trip_loads, trip_service, trip_deadhead, trip_cost)
        return(solution_lists)
            
    def find_insert_arc_clarpif(self, solution_lists, arc):
        inv_insert_cost = inv_insert_cost2 = huge
        (insert_cost, 
        insert_position, 
        insert_route,
        insert_trip) = self.best_single_arc_insertion_multiple_IF_routes_cap(solution_lists[0], 
                                                                            solution_lists[4], 
                                                                            solution_lists[5],
                                                                            arc)
        (insert_cost2,
         insert_trip2,  
         insert_route2) = self.best_singlearc_trip_insert_cap(solution_lists[0], 
                                                              solution_lists[4], 
                                                              solution_lists[5], 
                                                              arc)
        if self.inv_arcs[arc]:
            inv_arc = self.inv_arcs[arc]
            (inv_insert_cost, 
            inv_insert_position, 
            inv_insert_route,
            inv_insert_trip) = self.best_single_arc_insertion_multiple_IF_routes_cap(solution_lists[0], 
                                                                                     solution_lists[4], 
                                                                                     solution_lists[5],
                                                                                     inv_arc)
            (inv_insert_cost2,
             inv_insert_trip2,  
             inv_insert_route2) = self.best_singlearc_trip_insert_cap(solution_lists[0], 
                                                                      solution_lists[4], 
                                                                      solution_lists[5], 
                                                                      inv_arc)
             
        if min([insert_cost, insert_cost2, inv_insert_cost, inv_insert_cost2]) != huge:
            insert = True
            i = np.argmin([insert_cost, insert_cost2, inv_insert_cost, inv_insert_cost2])
            if i==0:            
                solution_lists = self.update_clarpif_lists(solution_lists, insert_route, insert_trip, 
                                                           insert_position, arc, insert_cost)
            if i==1:
                solution_lists = self.update_clarpif_lists_trip(solution_lists, insert_route2, 
                                                                insert_trip2, arc, insert_cost2)
            if i==2:
                solution_lists = self.update_clarpif_lists(solution_lists, inv_insert_route, inv_insert_trip, 
                                                           inv_insert_position, inv_arc, inv_insert_cost)
            if i==3:
                solution_lists = self.update_clarpif_lists_trip(solution_lists, inv_insert_route2, inv_insert_trip2, 
                                                                inv_arc, inv_insert_cost2)
            #print(arc, solution_lists[0][0])
            #print(arc, solution_lists[0][3])
        else:    
            insert = False
        return(insert, solution_lists)
    
    def insert_multiple_arcs_carp(self, solution_lists, insert_arcs):
        for arc in insert_arcs:
            (insert, solution_lists) = self.find_insert_arc_carp(solution_lists, arc)
            if insert == False: 
                break
        return(insert, solution_lists)
    
    def insert_multiple_arcs_clarpif(self, solution_lists, insert_arcs):
        #print('insert_arcs', insert_arcs)
        for arc in insert_arcs:
            (insert, solution_lists) = self.find_insert_arc_clarpif(solution_lists, arc)
            if insert == False: 
                break
        return(insert, solution_lists)
   
def test_CLARPIF():
    from py_return_problem_data  import return_problem_data # From Dev_TestData
    import py_alg_extended_path_scanning as EPS
    problem_set = 'Lpr_IF'
    filename = 'Lpr_IF-a-03_problem_info.dat'
    info = return_problem_data(problem_set, filename)
    eps = EPS.EPS_IF(info)
    solution = eps.buildMultipleIFRoutes()
    print(solution)
    print('')
    routes = [[solution[0]['Trips'][0][1:-1],solution[0]['Trips'][1][1:-1],solution[0]['Trips'][2][1:-2]]]
    print(routes)
    loads = [solution[0]['TripLoads']]
    costs = [solution[0]['Cost']]
    arc_i = solution[1]['Trips'][0][2]
    mod_route_ifs = insert_arc_in_if_route(info)
    print(mod_route_ifs.best_singlearc_trip_insert_cap(routes, costs, loads, arc_i))
    
def test_CARP():
    from py_return_problem_data  import return_problem_data # From Dev_TestData
    import py_alg_extended_path_scanning as EPS
    problem_set = 'Lpr'
    filename = 'Lpr-a-02_problem_info.dat'
    info = return_problem_data(problem_set, filename)
    eps = EPS.EPS(info)
    solution = eps.buildMultipleRoutes()
    print(solution)
    print('')
    arc_i = solution[2]['Route'][1]
    mod_route = insert_arc_in_route(info)
    routes = [solution[0]['Route'], solution[1]['Route'], solution[2]['Route']]
    loads = [solution[0]['Load'], solution[1]['Load'], solution[2]['Load']]
    print(mod_route.best_single_arc_insertion_multiple_routes_cap(routes, loads, arc_i))

if  __name__ == "__main__":
    test_CLARPIF()
    #test_CARP()
    
    
    
       
    
