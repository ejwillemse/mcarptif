'''
Created on 17 Jan 2012

@author: elias
'''

from copy import deepcopy
from math import ceil

import numpy as np

class build_solutions(object):
    
    def __init__(self, info):
        self.depot = info.depotnewkey
        self.capacity = info.capacity
        self.maxTrip = info.maxTrip
        self.dumpCost = info.dumpCost
        self.inv_arcs = info.reqInvArcList
        self.serveCostL = info.serveCostL
        self.demandL = info.demandL
        self.d = info.d
        self.if_arc = info.if_arc_np
        self.if_cost = info.if_cost_np
        
    def insert_IFs_depot(self, route):
        depot = self.depot
        if_arc = self.if_arc
        for i, trip in enumerate(route):#route[1]:
            if i == 0: route[0].insert(0, depot)
            if i == (len(route) - 1): 
                route[i].append(if_arc[trip[-1]][depot])                
                route[i].append(depot)
            if (i > 0):
                if_arc_add = if_arc[route[i-1][-1]][trip[0]]
                route[i-1].append(if_arc_add)
                route[i].insert(0, if_arc_add)
        return(route)
                
    def insert_depot(self, trip):
        depot = self.depot
        trip.insert(0, depot)
        trip.append(depot)
        return(trip)
    
    def generate_trip_dist_info(self, trip):
        d = self.d
        dumpCost = self.dumpCost
        deadhead = 0
        for i, arc in enumerate(trip[:-1]):
            arc_next = trip[i+1]
            deadhead += d[arc][arc_next]
    
        deadhead += dumpCost
        return(deadhead)
        
    def generate_trip_info(self, trip):
        d = self.d
        serveCostL = self.serveCostL
        dumpCost = self.dumpCost
        demandL = self.demandL
        deadhead = 0
        servicecost = 0
        cost = 0
        load = 0
        for i, arc in enumerate(trip[:-1]):
            arc_next = trip[i+1]
            deadhead += d[arc][arc_next]
            servicecost += serveCostL[arc]
            cost += d[arc][arc_next] + serveCostL[arc]
            load += demandL[arc]
            
        cost += serveCostL[trip[-1]] + dumpCost
        deadhead += dumpCost
        servicecost += serveCostL[trip[-1]]
        load += demandL[trip[-1]]
        return(deadhead, servicecost, cost, load)
    
    def build_single_route_dict(self, route):
        route_dict = {}
        (deadhead, servicecost, cost, load) = self.generate_trip_info(route)
        route_dict['Cost'] = cost
        route_dict['Load'] = load
        route_dict['Deadhead'] = deadhead
        route_dict['Service'] = servicecost
        route_dict['Route'] = deepcopy(route)
        return(route_dict)
    
    def build_MCARP_solution_dict(self, routes):
        '''
        Standard solution encoding.
        '''
        solution = {}
        nRoutes = len(routes)
        totalcost = 0
        for i in range(nRoutes):
            routes[i] = self.insert_depot(routes[i])
            solution[i] = self.build_single_route_dict(routes[i])
            totalcost += solution[i]['Cost']
        solution['ProblemType'] = 'CARP'
        solution['TotalCost'] = totalcost
        solution['nVehicles'] = nRoutes
        return(solution)
    
    def build_CLARPIF_route_dict(self, route): 
        route_dict = {}
        route_dict['TripDeadheads'] = []
        route_dict['TripServices'] = []
        route_dict['TripCosts'] = []
        route_dict['TripLoads'] = []
        route = self.insert_IFs_depot(route)
        
        for trip in route:
            (deadhead, servicecost, cost, load) = self.generate_trip_info(trip)
            route_dict['TripDeadheads'].append(deadhead)
            route_dict['TripServices'].append(servicecost)
            route_dict['TripCosts'].append(cost)
            route_dict['TripLoads'].append(load)
        
        route_dict['Trips'] = deepcopy(route)
        route_dict['nTrips'] = len(route)
        route_dict['Cost'] = sum(route_dict['TripCosts'])
        route_dict['Load'] = sum(route_dict['TripLoads'])
        route_dict['Deadhead'] = sum(route_dict['TripDeadheads'])
        route_dict['Service'] = sum(route_dict['TripServices'])
        return(route_dict)
    
    def build_CLARPIF_dict(self, routes):
        solution = {}
        nRoutes = len(routes)
        totalcost = 0
        for i in range(nRoutes):
            solution[i] = self.build_CLARPIF_route_dict(routes[i])
            totalcost += solution[i]['Cost']
        solution['ProblemType'] = 'CLARPIF'
        solution['TotalCost'] = totalcost
        solution['nVehicles'] = nRoutes
        return(solution)
    
    def build_CARP_list(self, solution):
        nRoutes = solution['nVehicles']
        routes = []
        loads = []
        service = []
        deadhead = []
        cost = []
        for i in range(nRoutes):
            routes.append(solution[i]['Route'][1:-1])
            loads.append(solution[i]['Load'])
            service.append(solution[i]['Service'])
            deadhead.append(solution[i]['Deadhead'])
            cost.append(solution[i]['Cost'])
        return(routes, loads, service,  deadhead, cost)

    def build_CARP_single_route(self, solution_full, i):
        solution = {}
        nRoutes = 1
        solution[0] = {}
        solution[0]['Cost'] = solution_full[i]['Cost']
        solution[0]['Load'] = solution_full[i]['Load']
        solution[0]['Deadhead'] = solution_full[i]['Deadhead']
        solution[0]['Service'] = solution_full[i]['Service']
        solution[0]['Route'] = deepcopy(solution_full[i]['Route'])
        solution['ProblemType'] = 'CARP'
        solution['TotalCost'] = solution_full[i]['Cost']
        solution['nVehicles'] = nRoutes
        return(solution)

    def build_CARP_dict_from_list(self, r, loads, service, deadhead, costs):
        routes = deepcopy(r)
        solution = {}
        nRoutes = len(routes)
        totalcost = 0
        for i in range(nRoutes):
            routes[i] = self.insert_depot(routes[i])
            solution[i] = {}
            totalcost += costs[i]
            solution[i]['Cost'] = costs[i]
            solution[i]['Load'] = loads[i]
            solution[i]['Deadhead'] = deadhead[i]
            solution[i]['Service'] = service[i]
            solution[i]['Route'] = deepcopy(routes[i])
        solution['ProblemType'] = 'CARP'
        solution['TotalCost'] = totalcost
        solution['nVehicles'] = nRoutes
        return(solution)
    
    def build_CLARPIF_list(self, solution):
        nRoutes = solution['nVehicles']
        routes = []
        load = []
        service = []
        deadhead = []
        cost = []
        trip_load = []
        trip_service = []
        trip_deadhead = []
        trip_cost = []
    
        for i in range(nRoutes):
            load.append(solution[i]['Load'])
            service.append(solution[i]['Service'])
            deadhead.append(solution[i]['Deadhead'])
            cost.append(solution[i]['Cost'])
            trip_load.append(solution[i]['TripLoads'])
            trip_service.append(solution[i]['TripServices'])
            trip_deadhead.append(solution[i]['TripDeadheads'])
            trip_cost.append(solution[i]['TripCosts'])
            routes.append([])
            for j in range(solution[i]['nTrips']):
                if j == (solution[i]['nTrips'] - 1):
                    routes[i].append(solution[i]['Trips'][j][1:-2])
                else:
                    routes[i].append(solution[i]['Trips'][j][1:-1])
        return(routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost)

    def build_CLARPIF_list_complete(self, solution):
        nRoutes = solution['nVehicles']
        routes = []
        load = []
        service = []
        deadhead = []
        cost = []
        trip_load = []
        trip_service = []
        trip_deadhead = []
        trip_cost = []
        trip_pre_post = []    
        
        for i in range(nRoutes):
            load.append(solution[i]['Load'])
            service.append(solution[i]['Service'])
            deadhead.append(solution[i]['Deadhead'])
            cost.append(solution[i]['Cost'])
            trip_load.append(solution[i]['TripLoads'])
            trip_service.append(solution[i]['TripServices'])
            trip_deadhead.append(solution[i]['TripDeadheads'])
            trip_cost.append(solution[i]['TripCosts'])
            routes.append([])
            trip_pre_post.append([])
            for j in range(solution[i]['nTrips']):
                if j == 0:
                    pre_arc = self.depot
                else:
                    pre_arc = solution[i]['Trips'][j-1][-2]
                if j == (solution[i]['nTrips'] - 1):
                    routes[i].append(solution[i]['Trips'][j][1:-2])
                    post_arc = self.depot
                else:
                    routes[i].append(solution[i]['Trips'][j][1:-1])
                    post_arc = solution[i]['Trips'][j+1][1]
                trip_pre_post[i].append([pre_arc, post_arc])
        return(routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost, trip_pre_post)

    def build_CARP_cum_list(self, solution):
        demand = self.demandL
        serviceL = self.serveCostL
        depot= self.depot
        d = self.d
        dumpcost = self.dumpCost
        nRoutes = solution['nVehicles']
        routes = []
        loads = []
        service = []
        deadhead = []
        cost = []
        for i in range(nRoutes):
            routes.append(solution[i]['Route'][1:-1])
            temp_list_l = []
            temp_list_s = []
            total_load = 0
            total_serve = 0            
            for arc in routes[-1]:
                total_load += demand[arc]
                total_serve += serviceL[arc]
                temp_list_l.append(total_load)
                temp_list_s.append(total_serve)
            loads.append(temp_list_l)
            service.append(temp_list_s)
            
            temp_list_d = []
            arc = routes[-1][0]
            arc_pre = depot
            total_dead = d[arc_pre][arc]
            temp_list_d.append(total_dead)
            for j in range(1,len(routes[-1])):
                arc = routes[-1][j]
                arc_pre = routes[-1][j-1]
                total_dead += d[arc_pre][arc]
                temp_list_d.append(total_dead)
            arc_pre = routes[-1][-1]
            arc = depot
            total_dead += d[arc_pre][arc] + dumpcost
            temp_list_d.append(total_dead)
            deadhead.append(temp_list_d)
            cost.append(solution[i]['Cost'])
        return(routes, loads, service,  deadhead)   
    
    def build_CARP_cum_list_from_route(self, route):
        demand = self.demandL
        serviceL = self.serveCostL
        depot= self.depot
        d = self.d
        dumpcost = self.dumpCost
        temp_list_l = []
        temp_list_s = []
        total_load = 0
        total_serve = 0            
        for arc in route:
            total_load += demand[arc]
            total_serve += serviceL[arc]
            temp_list_l.append(total_load)
            temp_list_s.append(total_serve)
    
        temp_list_d = []
        arc = route[0]
        arc_pre = depot
        total_dead = d[arc_pre][arc]
        temp_list_d.append(total_dead)
        for j in range(1,len(route)):
            arc = route[j]
            arc_pre = route[j-1]
            total_dead += d[arc_pre][arc]
            temp_list_d.append(total_dead)
        arc_pre = route[-1]
        arc = depot
        total_dead += d[arc_pre][arc] + dumpcost
        temp_list_d.append(total_dead)
        return(temp_list_l, temp_list_s, temp_list_d) 

    
    def build_CARP_cum_list_from_lists(self, solution_lists):
        routes = []
        loads = []
        service = []
        deadhead = []
        for route in solution_lists[0]:
            (temp_list_l, temp_list_s, temp_list_d) = self.build_CARP_cum_list_from_route(route)
            routes.append(route)
            loads.append(temp_list_l)
            service.append(temp_list_s)
            deadhead.append(temp_list_d)
        return(routes, loads, service, deadhead)       
    
    def build_CARP_cum_list_from_routes(self, routes):
        loads = []
        service = []
        deadhead = []
        for route in routes:
            (temp_list_l, temp_list_s, temp_list_d) = self.build_CARP_cum_list_from_route(route)
            loads.append(temp_list_l)
            service.append(temp_list_s)
            deadhead.append(temp_list_d)
        return(routes, loads, service, deadhead)     
        
    def build_CARP_dead_cum_list(self, route,):
        depot= self.depot
        d = self.d
        dumpcost = self.dumpCost

        temp_list_d = []
        arc = route[0]
        arc_pre = depot
        total_dead = d[arc_pre][arc]
        temp_list_d.append(total_dead)
        for j in range(1,len(route)):
            arc = route[j]
            arc_pre = route[j-1]
            total_dead += d[arc_pre][arc]
            temp_list_d.append(total_dead)
        arc_pre = route[-1]
        arc = depot
        total_dead += d[arc_pre][arc] + dumpcost
        temp_list_d.append(total_dead)
        return(temp_list_d)
    
    def build_CARP_dict_from_cum_list(self, routes, loads, service,  deadhead):
        depot = self.depot
        solution = {}
        nRoutes = len(routes)
        totalcost = 0
        for i in range(nRoutes):
            routes[i] = insert_depot(routes[i], depot)
            solution[i] = {}
            solution[i]['Load'] = loads[i][-1]
            solution[i]['Deadhead'] = deadhead[i][-1]
            solution[i]['Service'] = service[i][-1]
            solution[i]['Cost'] = service[i][-1] + deadhead[i][-1]
            solution[i]['Route'] = deepcopy(routes[i])
            totalcost += solution[i]['Cost']
        solution['ProblemType'] = 'CARP'
        solution['TotalCost'] = totalcost
        solution['nVehicles'] = nRoutes
        return(solution)
    
    def build_CLARPIF_dict_from_list(self, routes, load, service,  deadhead, cost, 
                                     trip_load, trip_service, trip_deadhead, trip_cost):
        solution = {}
        nRoutes = len(routes)
        totalcost = 0
        for i in range(nRoutes):
            routes[i] = self.insert_IFs_depot(routes[i])
            nTrips = len(routes[i])
            totalcost += cost[i]
            solution[i] = {}
            solution[i]['Cost'] = cost[i]
            solution[i]['Load'] = load[i]
            solution[i]['Deadhead'] = deadhead[i]
            solution[i]['Service'] = service[i]
            solution[i]['Trips'] = routes[i][:]
            solution[i]['nTrips'] = nTrips
            solution[i]['TripLoads'] = []
            solution[i]['TripLoads'] = trip_load[i][:]
            solution[i]['TripServices'] = trip_service[i][:]
            solution[i]['TripDeadheads'] = []
            solution[i]['TripCosts'] = []
            for j in range(nTrips):
                trip_deadhead = self.generate_trip_dist_info(routes[i][j])
                solution[i]['TripDeadheads'].append(trip_deadhead)
                solution[i]['TripCosts'].append(trip_deadhead + trip_service[i][j])
        solution['ProblemType'] = 'CLARPIF'
        solution['TotalCost'] = totalcost
        solution['nVehicles'] = nRoutes
        return(solution)
    
    def build_CLARPIF_cum_list_from_route(self, route):
        demand = self.demandL
        serviceL = self.serveCostL
        depot= self.depot
        d = self.d
        if_cost = self.if_cost
        temp_list_l_f = []
        temp_list_s_f = []
        
        route_load = []
        route_service = []
        total_load_r = 0
        total_serve_r = 0
        
        for trip in route:
            total_load = 0
            total_serve = 0
            temp_list_l = []
            temp_list_s = []
            route_load_t = []
            route_service_t = []     
            for arc in trip:
                total_load += demand[arc]
                total_serve += serviceL[arc]
                total_load_r += demand[arc]
                total_serve_r += serviceL[arc]
                temp_list_l.append(total_load)
                temp_list_s.append(total_serve)
                route_load_t.append(total_load_r)
                route_service_t.append(total_serve_r)   
            temp_list_l_f.append(temp_list_l)
            temp_list_s_f.append(temp_list_s)
            route_load.append(route_load_t)
            route_service.append(route_service_t)
        
        temp_list_d_f = []
        route_dead = []
        route_cost = []
        total_dead_r = 0
        total_cost_r = 0
        
        for i, trip in enumerate(route):
            temp_list_d = []
            temp_route_dead = []
            temp_route_cost = []
            if i == 0:
                total_dead = d[depot][trip[0]]
                total_dead_r += d[depot][trip[0]]
                total_cost_r += d[depot][trip[0]] + serviceL[trip[0]]
            else:
                total_dead = if_cost[route[i-1][-1]][trip[0]]
                total_dead_r += if_cost[route[i-1][-1]][trip[0]]
                total_cost_r += if_cost[route[i-1][-1]][trip[0]] + serviceL[trip[0]]
            temp_list_d.append(total_dead)
            temp_route_dead.append(total_dead_r)
            temp_route_cost.append(total_cost_r )
            for j in range(1,len(trip)):
                arc = trip[j]
                arc_pre = trip[j-1]
                total_dead += d[arc_pre][arc]
                total_dead_r += d[arc_pre][arc]
                total_cost_r += d[arc_pre][arc] + serviceL[arc]
                temp_list_d.append(total_dead)
                temp_route_dead.append(total_dead_r)
                temp_route_cost.append(total_cost_r )
            if i == len(route) - 1:
                total_dead += if_cost[trip[-1]][depot]
                total_dead_r += if_cost[trip[-1]][depot]
                total_cost_r += if_cost[trip[-1]][depot]
                temp_list_d.append(total_dead)
                temp_route_dead.append(total_dead_r)
                temp_route_cost.append(total_cost_r )
            temp_list_d_f.append(temp_list_d)
            route_dead.append(temp_route_dead)
            route_cost.append(temp_route_cost)
        return(temp_list_l_f, temp_list_s_f, temp_list_d_f, route_load, route_service, route_dead, route_cost) 
    
    def build_CLARPIF_cum_list_from_routes(self, routes):
        loads = []
        service = []
        deadhead = []
        load_route = []
        service_route = []
        deadhead_route = []
        cost_route = []
        for route in routes:
            (temp_list_l, temp_list_s, temp_list_d, 
             route_load, route_service, route_dead, route_cost)  = self.build_CLARPIF_cum_list_from_route(route)
            loads.append(temp_list_l)
            service.append(temp_list_s)
            deadhead.append(temp_list_d)
            load_route.append(route_load)
            service_route.append(route_service)
            deadhead_route.append(route_dead)
            cost_route.append(route_cost)   
        return(routes, loads, service, deadhead, load_route, service_route, deadhead_route, cost_route) 

    def build_CLARPIF_list_from_cum_lists(self, routes, load_c, service_c, deadhead_c, 
                                                load_route, service_route, deadhead_route, cost_route):
        trip_load = []
        trip_service = []
        trip_deadhead = []
        trip_cost = []
        for j in range(len(routes)):
            trip_load.append(load_c[j][-1])
            trip_service.append(service_c[j][-1])
            trip_deadhead.append(deadhead_c[j][-1])
            trip_cost.append(deadhead_c[j][-1] + service_c[j][-1])              
        load = load_route[-1][-1]
        service = service_route[-1][-1]
        deadhead = deadhead_route[-1][-1]
        cost = cost_route[-1][-1]
        return(load, service, deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost)

    def arc_route_positions(self, routes):
        invArcList = self.inv_arcs
        nReqArcs = len(invArcList)
        arc_positions = np.ndarray((nReqArcs, 2), dtype='int32')
        nRoutes = len(routes)
        for i in range(nRoutes):
            for arc_pos, arc in enumerate(routes[i]):
                arc_positions[arc, 0] = i
                arc_positions[arc, 1] = arc_pos
                if invArcList[arc]:
                    arc_positions[invArcList[arc], 0] = -1
                    arc_positions[invArcList[arc], 1] = -1         
        return(arc_positions)
    
    def display_CARP_solution_info(self, solution):
                
        import Table_Output
        labels = (' Route', 'Cost', 'Service cost', 'Dead-head cost', 'Efficiency', 'Load utilisation')
        
        capacity = self.capacity
        dumpCost = self.dumpCost
        
        totalDemand = 0
        loadUtil = []
        for i in range(solution['nVehicles']):
            totalDemand += solution[i]['Load'] 
            util_l = solution[i]['Load']/float(capacity)
            loadUtil.append(util_l)
            
        nReqVehicles = int(ceil(totalDemand/float(capacity)))
        if nReqVehicles == solution['nVehicles']: deadAdjust = dumpCost
        else: deadAdjust = 0
                
        utility = []
        load_util = []
        for i in range(solution['nVehicles']):
            if float(solution[i]['Cost']) != 0: ut = solution[i]['Service']/(float(solution[i]['Cost'])-deadAdjust)
            else: ut = 1e300000
            utility.append(ut)
            util_load = solution[i]['Load']/float(self.capacity)
            load_util.append(util_load)
            
        print('')
        print(solution)
        print('')
        print('========================================================================================')
        print(' PROBLEM INFO')
        print('----------------------------------------------------------------------------------------')
        print(' Type         : %s' %solution['ProblemType'])
        print(' Min vehicles : %i' %nReqVehicles)
        print(' Excess cap   : %i' %(nReqVehicles*capacity-totalDemand))
        print('----------------------------------------------------------------------------------------')
        print('')
        data = ''
        tServe = tDead = tLoad = 0
        for i in range(solution['nVehicles']):
            data += '%i,%i,%i,%i,%.2f,%.2f \n'%(
                     i,   
                     solution[i]['Cost'], 
                     solution[i]['Service'], 
                     solution[i]['Deadhead'], 
                     utility[i], 
                     load_util[i])
            tServe += solution[i]['Service']
            tDead += solution[i]['Deadhead']
            tLoad += solution[i]['Load']
        data += '%s,%s,%s,%s,%s,%s, \n'%('','','','','','',)
        data += '%i,%i,%i,%i,%.2f,%.2f \n'%(
                     solution['nVehicles'],   
                     solution['TotalCost'], 
                     tServe, 
                     tDead, 
                     float(tServe)/solution['TotalCost'], 
                     float(tLoad)/(solution['nVehicles']*self.capacity))
        Table_Output.print_table(' SOLUTION TABLE', labels, data)
        print('----------------------------------------------------------------------------------------')
        print(' SUMMARY')
        print('----------------------------------------------------------------------------------------')
        print(' Total cost   : %i' %solution['TotalCost'])
        print(' # Vehicles   : %i' %solution['nVehicles'] )
        print('========================================================================================')
        print('')

    def display_CLARPIF_solution_info(self, solution):
        import Table_Output
        labels = (' Route', 'Cost', 'Service cost', 'Dead-head cost', 'Efficiency', 'Cost utilisation', 'Load utilisation', '# Trips')
        
        excess = solution['nVehicles']*self.maxTrip - solution['TotalCost']
        
        service_util = []
        utility = []
        load_util = []
        for i in range(solution['nVehicles']):
            if float(solution[i]['Cost']) != 0: ut = solution[i]['Service']/(float(solution[i]['Cost']))
            else: ut = 1e300000
            utility.append(ut)
            util_l = solution[i]['Cost']/float(self.maxTrip)
            util_load = solution[i]['Load']/float(solution[i]['nTrips']*self.capacity)
            service_util.append(util_l)
            load_util.append(util_load)
            
        print('')
        print(solution)
        print('')
        print('===========================================================================================================================')
        print(' PROBLEM INFO')
        print('---------------------------------------------------------------------------------------------------------------------------')
        print(' Type                : %s' %solution['ProblemType'])
        print(' Excess service time : %i' %excess)
        print('---------------------------------------------------------------------------------------------------------------------------')
        print('')
        data = ''
        tServe = tDead = TnTrips = tLoad = 0
        for i in range(solution['nVehicles']):
            data += '%i,%i,%i,%i,%.2f,%.2f,%.2f,%i \n'%(
                     i,   
                     solution[i]['Cost'], 
                     solution[i]['Service'], 
                     solution[i]['Deadhead'], 
                     utility[i], 
                     service_util[i],
                     load_util[i], 
                     solution[i]['nTrips'])
            tServe += solution[i]['Service']
            tDead += solution[i]['Deadhead']
            tLoad += solution[i]['Load']
            TnTrips += solution[i]['nTrips']
        data += '%s,%s,%s,%s,%s,%s,%s,%s \n'%('','','','','','','','',)
        data += '%i,%i,%i,%i,%.2f,%.2f,%.2f,%i \n'%(
                     solution['nVehicles'],   
                     solution['TotalCost'], 
                     tServe, 
                     tDead, 
                     float(tServe)/solution['TotalCost'], 
                     float(solution['TotalCost'])/(solution['nVehicles']*self.maxTrip),
                     float(tLoad)/(TnTrips*self.capacity), 
                     TnTrips)
        Table_Output.print_table(' SOLUTION TABLE', labels, data)
        print('---------------------------------------------------------------------------------------------------------------------------')
        print(' SUMMARY')
        print('---------------------------------------------------------------------------------------------------------------------------')
        print(' Total cost   : %i' %solution['TotalCost'])
        print(' # Vehicles   : %i' %solution['nVehicles'] )
        print('===========================================================================================================================')
        print('')
    
    def display_solution_info(self, solution):
        if solution['ProblemType'] == 'CARP':self.display_CARP_solution_info(solution)
        if solution['ProblemType'] == 'CLARPIF':self.display_CLARPIF_solution_info(solution)

class build_CLARPIF_solutions(build_solutions):

    def __init__(self, info):
        if info:
            build_solutions.__init__(self, info)
            self.depot = info.depotnewkey
            self.capacity = info.capacity
            self.maxTrip = info.maxTrip
            self.dumpCost = info.dumpCost
            self.inv_arcs = info.reqInvArcList
            self.serveCostL = info.serveCostL
            self.demandL = info.demandL
            self.d = info.d
            self.if_arc = info.if_arc_np
            self.if_cost = info.if_cost_np
    
    def build_route_lists(self, solution):

        nRoutes = solution['nVehicles']
        routes = []
        trip_index = []
        trip_load = []
        load = []
        service = []
        loads = []
        ifs = []
        load_a = []
        cost = []
        normal_arcs = []
        normal_arcs_jump = []
        if_arcs_pre = []
        if_arcs_post = []
        if_single_arcs_route = []
        if_single_arcs_depot_trip = []
        if_single_arcs_trip = []
        
        for i in range(nRoutes):
            nTrips = solution[i]['nTrips']
            route = [self.depot]
            if_positions = []
            t_index = [0]
            t_load = []
            for t in range(0, nTrips - 1):
                route += solution[i]['Trips'][t][1:]
                if_positions.append(len(route)-1)
                t_index += [t]*len(solution[i]['Trips'][t][1:])
                t_load.append(solution[i]['TripLoads'][t])
                
            route += solution[i]['Trips'][-1][1:]
            if_positions.append(len(route)-2)
            t_index += [nTrips - 1]*len(solution[i]['Trips'][-1][1:])
            t_load.append(solution[i]['TripLoads'][-1])
            
            routes.append(route)
            ifs.append(if_positions)
            load.append(loads)
            trip_index.append(t_index)
            trip_load.append(t_load)
            
            normal_pos = []
            normal_jump = []
            if_single_arc_route = []
            if_single_arc_depot_trip = []
            if_single_arc_trip = []
            if_arc_pos_pre = []
            if_arc_pos_post = []
            
            if if_positions[0] == 2:
                if len(if_positions) == 1:
                    if_single_arc_route.append(if_positions[0]-1)
                else:
                    if_single_arc_depot_trip.append(if_positions[0]-1)
            else:
                normal_pos = range(1, if_positions[0]-1)
                normal_jump = [len(normal_pos)]*len(normal_pos)
                if_arc_pos_pre = [if_positions[0]-1]
            
            for if_pos in range(1, len(if_positions)):
                if (if_positions[if_pos -1] + 1) == (if_positions[if_pos] - 1):
                    if_single_arc_trip.append(if_positions[if_pos -1] + 1)
                else:
                    normal_pos += range(if_positions[if_pos -1] + 2, if_positions[if_pos]-1)
                    normal_jump += [len(normal_pos)]*len(normal_pos)
                    if_arc_pos_post += [if_positions[if_pos -1] + 1]
                    if_arc_pos_pre += [if_positions[if_pos]-1]
            
            normal_arcs.append(normal_pos)
            normal_arcs_jump.append(normal_jump)
            if_arcs_pre.append(if_arc_pos_pre)
            if_arcs_post.append(if_arc_pos_post)
            
            if_single_arcs_route.append(if_single_arc_route)
            if_single_arcs_depot_trip.append(if_single_arc_depot_trip)
            if_single_arcs_trip.append(if_single_arc_trip)
            
            service_arc = []
            load_arc = []
            for arc in route:
                service_arc.append(self.serveCostL[arc])
                load_arc.append(self.demandL[arc])
                
            service.append(service_arc)
            load_a.append(load_arc)
            cost.append(solution[i]['Cost'])
            
        return(routes, trip_index, trip_load, load, ifs, cost, service, load_a, normal_arcs, normal_arcs_jump, 
               if_arcs_pre, if_arcs_post, if_single_arcs_route, if_single_arcs_depot_trip, if_single_arcs_trip)
    
    def buil_cumulitive_lists(self, solution_lists):
        (routes, trip_index, trip_load, loads, ifs_full, cost, service_a_full, load_a_full, normal_arcs,  normal_arcs_jump,
         if_arcs_pre, if_arcs_post, if_single_arcs_route, if_single_arcs_depot_trip, if_single_arcs_trip) = solution_lists
        
        cost_cum = []
        load_cum = []
        for r in range(len(routes)):
            route = routes[r]
            service_a = service_a_full[r]
            load_a = load_a_full[r]
            ifs = ifs_full[r]
            nTrips = len(ifs)
            cost_c = [service_a[0]]
            load_c = [load_a[0]]
            c = 0
            l = 0 
            for j in range(1, ifs[0] + 1):
                c += self.d[route[j - 1]][route[j]] + service_a[j]
                cost_c.append(c)
                l += load_a[j]
                load_c.append(l)
            c += self.dumpCost
            cost_c[-1] += self.dumpCost

            for trip in range(1, nTrips):
                l = 0
                for j in range(ifs[trip - 1] + 1, ifs[trip] + 1):
                    c += self.d[route[j - 1]][route[j]] + service_a[j]
                    cost_c.append(c)
                    l += load_a[j]
                    load_c.append(l)
                c += self.dumpCost
                cost_c[-1] += self.dumpCost
            c += self.d[route[-2]][route[-1]] + service_a[-1]
            cost_c.append(c)
            l += load_a[-1]
            load_c.append(l)
            cost_cum.append(cost_c)
            load_cum.append(load_c)
        return(cost_cum, load_cum)                
                
    def build_CLARPIF_dict_from_full_routes(self, cost, loads, routes, ifs):
        
        new_routes = []
        for i in range(len(routes)):
            route_i = []
            for j in range(len(ifs[i])):
                if j == 0:
                    trip_i = routes[i][1:ifs[i][j]]
                else:
                    trip_i = routes[i][ifs[i][j-1] + 1:ifs[i][j]]
                route_i.append(trip_i)
            new_routes.append(route_i)
            
        solution = self.build_CLARPIF_dict(new_routes)
        for i in range(len(routes)):
            solution[i]['Cost'] = cost[i]
            solution[i]['Load'] = sum(loads[i])
            for j in range(len(loads[i])):
                solution[i]['TripLoads'][j] = loads[i][j]
        
        return(solution)

    def build_route_lists_from_routes(self, routes, ifs):
        new_routes = []
        for i in range(len(routes)):
            route_i = []
            for j in range(len(ifs[i])):
                if j == 0:
                    trip_i = routes[i][1:ifs[i][j]]
                else:
                    trip_i = routes[i][ifs[i][j-1] + 1:ifs[i][j]]
                route_i.append(trip_i)
            new_routes.append(route_i)
            
        solution = self.build_CLARPIF_dict(new_routes)
        return(self.build_route_lists(solution))

def insert_IFs_depot(route, if_arc, depot):
    for i, trip in enumerate(route):#route[1]:
        if i == 0: route[0].insert(0, depot)
        if i == (len(route) - 1): 
            route[i].append(if_arc[trip[-1]][depot])                
            route[i].append(depot)
        if (i > 0):
            if_arc_add = if_arc[route[i-1][-1]][trip[0]]
            route[i-1].append(if_arc_add)
            route[i].insert(0, if_arc_add)
    return(route)
            
def insert_depot(trip, depot):
    trip.insert(0, depot)
    trip.append(depot)
    return(trip)

def generate_trip_dist_info(trip, d, dumpCost):
    deadhead = 0
    for i, arc in enumerate(trip[:-1]):
        arc_next = trip[i+1]
        deadhead += d[arc][arc_next]

    deadhead += dumpCost
    return(deadhead)
    
def generate_trip_info(trip, d, serveCostL, dumpCost, demandL):
    deadhead = 0
    servicecost = 0
    cost = 0
    load = 0
    for i, arc in enumerate(trip[:-1]):
        arc_next = trip[i+1]
        deadhead += d[arc][arc_next]
        servicecost += serveCostL[arc]
        cost += d[arc][arc_next] + serveCostL[arc]
        load += demandL[arc]
        
    cost += serveCostL[trip[-1]] + dumpCost
    deadhead += dumpCost
    servicecost += serveCostL[trip[-1]]
    load += demandL[trip[-1]]
    return(deadhead, servicecost, cost, load)

def build_single_route_dict(route, d, serveCostL, dumpCost, demandL):
    route = {}
    (deadhead, servicecost, cost, load) = generate_trip_info(route, d, serveCostL, dumpCost, demandL)
    route['Cost'] = cost
    route['Load'] = load
    route['Deadhead'] = deadhead
    route['Service'] = servicecost
    route['Route'] = deepcopy(route)
    return(route)

def build_MCARP_solution_dict(routes, d, serveCostL, dumpCost, demandL, depot):
    '''
    Standard solution encoding.
    '''
    solution = {}
    nRoutes = len(routes)
    totalcost = 0
    for i in range(nRoutes):
        routes[i] = insert_depot(routes[i], depot)
        solution[i] = build_single_route_dict(routes[i], d, serveCostL, dumpCost, demandL)
        totalcost += solution[i]['Cost']
    solution['ProblemType'] = 'CARP'
    solution['TotalCost'] = totalcost
    solution['nVehicles'] = nRoutes
    return(solution)

def build_CLARPIF_route_dict(route, if_arc, depot, d, serveCostL, dumpCost, demandL): 
    route_dict = {}
    route_dict['TripDeadheads'] = []
    route_dict['TripServices'] = []
    route_dict['TripCosts'] = []
    route_dict['TripLoads'] = []
    route = insert_IFs_depot(route, if_arc, depot)
    
    for trip in route:
        (deadhead, servicecost, cost, load) = generate_trip_info(trip, d, serveCostL, dumpCost, demandL)
        route_dict['TripDeadheads'].append(deadhead)
        route_dict['TripServices'].append(servicecost)
        route_dict['TripCosts'].append(cost)
        route_dict['TripLoads'].append(load)
    
    route_dict['Trips'] = deepcopy(route)
    route_dict['nTrips'] = len(route)
    route_dict['Cost'] = sum(route_dict['TripCosts'])
    route_dict['Load'] = sum(route_dict['TripLoads'])
    route_dict['Deadhead'] = sum(route_dict['TripDeadheads'])
    route_dict['Service'] = sum(route_dict['TripServices'])
    return(route_dict)

def build_CLARPIF_correct_route_dict(solution, routeI,  d, serveCostL, dumpCost, demandL): 

    route = solution[routeI]['Trips']

    solution[routeI]['TripDeadheads'] = []
    solution[routeI]['TripServices'] = []
    solution[routeI]['TripCosts'] = []
    solution[routeI]['TripLoads'] = []
    
    for trip in route:
        (deadhead, servicecost, cost, load) = generate_trip_info(trip, d, serveCostL, dumpCost, demandL)
        solution[routeI]['TripDeadheads'].append(deadhead)
        solution[routeI]['TripServices'].append(servicecost)
        solution[routeI]['TripCosts'].append(cost)
        solution[routeI]['TripLoads'].append(load)
    
    solution[routeI]['nTrips'] = len(route)
    solution[routeI]['Cost'] = sum(solution[routeI]['TripCosts'])
    solution[routeI]['Load'] = sum(solution[routeI]['TripLoads'])
    solution[routeI]['Deadhead'] = sum(solution[routeI]['TripDeadheads'])
    solution[routeI]['Service'] = sum(solution[routeI]['TripServices'])
    return(solution)

def build_CLARPIF_dict_correct(solution, info):#d, serveCostL, dumpCost, demandL):
    d = info.d
    serveCostL = info.serveCostL
    dumpCost = info.dumpCost
    demandL = info.demandL
    nRoutes = solution['nVehicles']
    for i in range(nRoutes):
        solution = build_CLARPIF_correct_route_dict(solution, i, d, serveCostL, dumpCost, demandL)
    return(solution)

def build_CLARPIF_dict(routes, if_arc, depot, d, serveCostL, dumpCost, demandL):
    solution = {}
    nRoutes = len(routes)
    totalcost = 0
    for i in range(nRoutes):
        solution[i] = build_CLARPIF_route_dict(routes[i], if_arc, depot, d, serveCostL, dumpCost, demandL)
        totalcost += solution[i]['Cost']
    solution['ProblemType'] = 'CLARPIF'
    solution['TotalCost'] = totalcost
    solution['nVehicles'] = nRoutes
    return(solution)

def build_CARP_list(solution):
    nRoutes = solution['nVehicles']
    routes = []
    loads = []
    service = []
    deadhead = []
    cost = []
    for i in range(nRoutes):
        routes.append(solution[i]['Route'][1:-1])
        loads.append(solution[i]['Load'])
        service.append(solution[i]['Service'])
        deadhead.append(solution[i]['Deadhead'])
        cost.append(solution[i]['Cost'])
    return(routes, loads, service,  deadhead, cost)

def build_CARP_dict_from_list(routes, loads, service, deadhead, costs, depot):
    solution = {}
    nRoutes = len(routes)
    totalcost = 0
    for i in range(nRoutes):
        routes[i] = insert_depot(routes[i], depot)
        solution[i] = {}
        totalcost += costs[i]
        solution[i]['Cost'] = costs[i]
        solution[i]['Load'] = loads[i]
        solution[i]['Deadhead'] = deadhead[i]
        solution[i]['Service'] = service[i]
        solution[i]['Route'] = deepcopy(routes[i])
    solution['ProblemType'] = 'CARP'
    solution['TotalCost'] = totalcost
    solution['nVehicles'] = nRoutes
    return(solution)

def build_CLARPIF_list(solution):
    nRoutes = solution['nVehicles']
    routes = []
    load = []
    service = []
    deadhead = []
    cost = []
    trip_load = []
    trip_service = []
    trip_deadhead = []
    trip_cost = []
    
    
    
    for i in range(nRoutes):
        load.append(solution[i]['Load'])
        service.append(solution[i]['Service'])
        deadhead.append(solution[i]['Deadhead'])
        cost.append(solution[i]['Cost'])
        trip_load.append(solution[i]['TripLoads'])
        trip_service.append(solution[i]['TripServices'])
        trip_deadhead.append(solution[i]['TripDeadheads'])
        trip_cost.append(solution[i]['TripCosts'])
        routes.append([])
        #print('')
        #print(solution[i]['Trips'])
        for j in range(len(solution[i]['Trips'])):
            #print(solution[i]['Trips'][j])
            if j == (solution[i]['nTrips'] - 1):
                routes[i].append(solution[i]['Trips'][j][1:-2])
            else:
                routes[i].append(solution[i]['Trips'][j][1:-1])
    #raise NameError('Check routes')
    return(routes, load, service,  deadhead, cost, trip_load, trip_service, trip_deadhead, trip_cost)

def build_CARP_cum_list(solution, demand, serviceL, d, depot, dumpcost):
    nRoutes = solution['nVehicles']
    routes = []
    loads = []
    service = []
    deadhead = []
    cost = []
    for i in range(nRoutes):
        routes.append(solution[i]['Route'][1:-1])
        temp_list_l = []
        temp_list_s = []
        total_load = 0
        total_serve = 0            
        for arc in routes[-1]:
            total_load += demand[arc]
            total_serve += serviceL[arc]
            temp_list_l.append(total_load)
            temp_list_s.append(total_serve)
        loads.append(temp_list_l)
        service.append(temp_list_s)
        
        temp_list_d = []
        arc = routes[-1][0]
        arc_pre = depot
        total_dead = d[arc_pre][arc]
        temp_list_d.append(total_dead)
        for j in range(1,len(routes[-1])):
            arc = routes[-1][j]
            arc_pre = routes[-1][j-1]
            total_dead += d[arc_pre][arc]
            temp_list_d.append(total_dead)
        arc_pre = routes[-1][-1]
        arc = depot
        total_dead += d[arc_pre][arc] + dumpcost
        temp_list_d.append(total_dead)
        deadhead.append(temp_list_d)
        cost.append(solution[i]['Cost'])
    return(routes, loads, service,  deadhead)   

def build_CARP_cum_list_from_route(route, demand, serviceL, d, depot, dumpcost):

    temp_list_l = []
    temp_list_s = []
    total_load = 0
    total_serve = 0            
    for arc in route:
        total_load += demand[arc]
        total_serve += serviceL[arc]
        temp_list_l.append(total_load)
        temp_list_s.append(total_serve)

    temp_list_d = []
    arc = route[0]
    arc_pre = depot
    total_dead = d[arc_pre][arc]
    temp_list_d.append(total_dead)
    for j in range(1,len(route)):
        arc = route[j]
        arc_pre = route[j-1]
        total_dead += d[arc_pre][arc]
        temp_list_d.append(total_dead)
    arc_pre = route[-1]
    arc = depot
    total_dead += d[arc_pre][arc] + dumpcost
    temp_list_d.append(total_dead)
    return(temp_list_l, temp_list_s, temp_list_d) 

def build_CARP_cum_list_from_lists(solution_lists, demand, serviceL, d, depot, dumpcost):
    routes = []
    loads = []
    service = []
    deadhead = []
    for route in solution_lists[0]:
        (temp_list_l, temp_list_s, temp_list_d) = build_CARP_cum_list_from_route(route, demand, serviceL, d, depot, dumpcost)
        routes.append(route)
        loads.append(temp_list_l)
        service.append(temp_list_s)
        deadhead.append(temp_list_d)
    return(routes, loads, service, deadhead)       

def build_CARP_cum_list_from_routes(routes, demand, serviceL, d, depot, dumpcost):
    loads = []
    service = []
    deadhead = []
    for route in routes:
        (temp_list_l, temp_list_s, temp_list_d) = build_CARP_cum_list_from_route(route, demand, serviceL, d, depot, dumpcost)
        loads.append(temp_list_l)
        service.append(temp_list_s)
        deadhead.append(temp_list_d)
    return(routes, loads, service, deadhead)     
    
def build_CARP_dead_cum_list(route, d, depot, dumpcost):

    temp_list_d = []
    arc = route[0]
    arc_pre = depot
    total_dead = d[arc_pre][arc]
    temp_list_d.append(total_dead)
    for j in range(1,len(route)):
        arc = route[j]
        arc_pre = route[j-1]
        total_dead += d[arc_pre][arc]
        temp_list_d.append(total_dead)
    arc_pre = route[-1]
    arc = depot
    total_dead += d[arc_pre][arc] + dumpcost
    temp_list_d.append(total_dead)
    return(temp_list_d)

def build_CARP_dict_from_cum_list(routes, loads, service,  deadhead, depot):
    solution = {}
    nRoutes = len(routes)
    totalcost = 0
    for i in range(nRoutes):
        routes[i] = insert_depot(routes[i], depot)
        solution[i] = {}
        solution[i]['Load'] = loads[i][-1]
        solution[i]['Deadhead'] = deadhead[i][-1]
        solution[i]['Service'] = service[i][-1]
        solution[i]['Cost'] = service[i][-1] + deadhead[i][-1]
        solution[i]['Route'] = deepcopy(routes[i])
        totalcost += solution[i]['Cost']
    solution['ProblemType'] = 'CARP'
    solution['TotalCost'] = totalcost
    solution['nVehicles'] = nRoutes
    return(solution)

def build_CLARPIF_dict_from_list(routes, load, service,  deadhead, cost, 
                                 trip_load, trip_service, trip_deadhead, trip_cost,
                                 if_arc, depot, d, dumpcost):
    #for r in routes: print(r)
    solution = {}
    nRoutes = len(routes)
    totalcost = 0
    for i in range(nRoutes):
        routes[i] = insert_IFs_depot(routes[i], if_arc, depot)
        nTrips = len(routes[i])
        totalcost += cost[i]
        solution[i] = {}
        solution[i]['Cost'] = cost[i]
        solution[i]['Load'] = load[i]
        solution[i]['Deadhead'] = deadhead[i]
        solution[i]['Service'] = service[i]
        solution[i]['Trips'] = routes[i][:]
        solution[i]['nTrips'] = nTrips
        solution[i]['TripLoads'] = []
        solution[i]['TripLoads'] = trip_load[i][:]
        solution[i]['TripServices'] = trip_service[i][:]
        solution[i]['TripDeadheads'] = []
        solution[i]['TripCosts'] = []
        #if len(trip_service[i]) < nTrips: trip_service[i].append(0)
        #print(routes[i])
        #print(i, nTrips, trip_service[i])
        for j in range(nTrips):
            trip_deadhead = generate_trip_dist_info(routes[i][j], d, dumpcost)
            solution[i]['TripDeadheads'].append(trip_deadhead)
            solution[i]['TripCosts'].append(trip_deadhead + trip_service[i][j])
    solution['ProblemType'] = 'CLARPIF'
    solution['TotalCost'] = totalcost
    solution['nVehicles'] = nRoutes
    return(solution)

def arc_route_positions(routes, invArcList):
    nReqArcs = len(invArcList)
    arc_positions = np.ndarray((nReqArcs, 2), dtype='int32')
    nRoutes = len(routes)
    for i in range(nRoutes):
        for arc_pos, arc in enumerate(routes[i]):
            arc_positions[arc, 0] = i
            arc_positions[arc, 1] = arc_pos
            if invArcList[arc]:
                arc_positions[invArcList[arc], 0] = -1
                arc_positions[invArcList[arc], 1] = -1         
    return(arc_positions)

    
def display_CARP_solution_info(solution, capacity=10000, dumpCost = 300):
    totalDemand = 0
    loadUtil = []
    for i in range(solution['nVehicles']):
        totalDemand += solution[i]['Load'] 
        util_l = solution[i]['Load']/float(capacity)
        loadUtil.append(util_l)
        
    nReqVehicles = int(ceil(totalDemand/float(capacity)))
    if nReqVehicles == solution['nVehicles']: deadAdjust = 300
    else: deadAdjust = 0
    
    utility = []
    
    for i in range(solution['nVehicles']):
        ut = solution[i]['Service']/(float(solution[i]['Cost'])-deadAdjust)
        utility.append(ut)

    print('')
    print(solution)
    print('')
    print('================================================================================================')
    print(' PROBLEM INFO')
    print('------------------------------------------------------------------------------------------------')
    print(' Type         : %s' %solution['ProblemType'])
    print(' Min vehicles : %i' %nReqVehicles)
    print(' Excess cap   : %i' %(nReqVehicles*capacity-totalDemand))
    print('------------------------------------------------------------------------------------------------')
    print(' SOLUTION')
    print('------------------------------------------------------------------------------------------------')
    for i in range(solution['nVehicles']):
        print(' Routes %i \t Cost: %i \t Load: %i \t Dead: %i \t Util: %.2f \t Load Util: %.2f' 
              %(i, solution[i]['Cost'], solution[i]['Load'], solution[i]['Deadhead']-deadAdjust, utility[i], loadUtil[i]))
    print('------------------------------------------------------------------------------------------------')
    print(' SUMMARY')
    print('------------------------------------------------------------------------------------------------')
    print(' Total cost   : %i' %solution['TotalCost'])
    print(' # Vehicles   : %i' %solution['nVehicles'] )
    print('================================================================================================')
    print('')

def display_CLARPIF_solution_info(solution, maxTrip=28800):
    
    
    excess = solution['nVehicles']*maxTrip - solution['TotalCost']
    
    service_util = []
    utility = []
    for i in range(solution['nVehicles']):
        if float(solution[i]['Cost']) != 0: ut = solution[i]['Service']/(float(solution[i]['Cost']))
        else: ut = 1e300000
        utility.append(ut)
        util_l = solution[i]['Cost']/float(maxTrip)
        service_util.append(util_l)
        
    print('')
    print(solution)
    print('')
    print('===========================================================================================================================')
    print(' PROBLEM INFO')
    print('---------------------------------------------------------------------------------------------------------------------------')
    print(' Type         : %s' %solution['ProblemType'])
    print(' Excess cap   : %i' %excess)
    print('---------------------------------------------------------------------------------------------------------------------------')
    print(' SOLUTION')
    print('---------------------------------------------------------------------------------------------------------------------------')
    for i in range(solution['nVehicles']):
        print(' Routes %i \t Cost: %i \t Service: %i \t Dead: %i \t Util: %.2f \t Day Util: %.2f \t # Trips: %i' 
              %(i, solution[i]['Cost'], solution[i]['Service'], solution[i]['Deadhead'], utility[i], service_util[i], solution[i]['nTrips']))
        #print(solution[i]['TripLoads'])
    print('---------------------------------------------------------------------------------------------------------------------------')
    print(' SUMMARY')
    print('---------------------------------------------------------------------------------------------------------------------------')
    print(' Total cost   : %i' %solution['TotalCost'])
    print(' # Vehicles   : %i' %solution['nVehicles'] )
    print('===========================================================================================================================')
    print('')

def display_solution_info(solution):

    if solution['ProblemType'] == 'CARP':display_CARP_solution_info(solution)
    if solution['ProblemType'] == 'CLARPIF':display_CLARPIF_solution_info(solution)
    