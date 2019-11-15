#===============================================================================
# Improve existing routes through exact and approximate algorihtms
# EJ Willemse CSIR: Built Environmnet 4 November 2009
#
# Addapted from:
# Grove, GW., Van Vuuren, JH (2005). Efficient heuristics for the Rural Postman 
# Problem, ORiON vol 21 (1), pp-33-51.
# Specifically page 37-39.
#===============================================================================

import py_solution_builders as build
from copy import deepcopy

def sp1SourceList(piEst, origin, destination):
    '''
    Generate shortest path visitation list based on presidence dictionary, and 
    an origin and destination. 
    '''
    pathList = [destination]
    a = destination
    while True:
        a = piEst[a]
        pathList.append(a)
        if a == origin:break
    pathList.reverse()
    return(pathList)

class optArcDirect(object):
    
    def __init__(self, info):
        #self.serviceCostD = info.serveCostL
        self.invArcD = info.reqInvArcList
        self.SP = info.d
        self.dumpCost = info.dumpCost
        self.depot = info.depotnewkey
        self.if_arc = info.if_arc_np
        self.builder = build.build_CLARPIF_solutions(info)
        
    def optRoute(self, route, if_positions = []):
        huge = 1e300000
        routeChange = deepcopy(route)
        #serviceCost = self.serviceCostD
        invArcD = self.invArcD
        SP = self.SP
        nArcs = len(route)
        change = False
        change2 = False
        #print('2',route)
        if route[0] == route[-1]:
            change = True
            dummy = {'s2':route[-1]}
            routeChange[-1] = 's2'
            if invArcD[route[-1]]:
                invArcD[route[-1]] = None
#                invArcD['s2'] = 's3'
#                dummy['s3'] = invArcD[route[-1]]
        if (route[0] == route[-2]) & (len(route)>2):
            change2 = True
            dummy2 = {'s4':route[-2]}
            routeChange[-2] = 's4'
            if invArcD[route[-2]]:
                invArcD[route[-2]] = None
#                invArcD['s4'] = 's5'
#                dummy2['s5'] = invArcD[route[-2]]
            
        D = {}
        PI = {}
        
        D[routeChange[0]] = 0 #serviceCost[route[0]]
        PI[routeChange[0]] = 's'
        if invArcD[route[0]]:
            D[invArcD[routeChange[0]]] = 0 #serviceCost[routeChange[0]]
            PI[invArcD[routeChange[0]]] = 's'
        for i in range(1,nArcs):
            edge1 = D[route[i-1]] +  SP[route[i-1]][route[i]] # + serviceCost[route[i]]
            edge2 = huge
            edge4 = huge
            if invArcD[route[i-1]]:
                edge2 =  D[invArcD[route[i-1]]] +  SP[invArcD[route[i-1]]][route[i]] # + serviceCost[route[i]]
                if invArcD[route[i]]:
                    edge4 = D[invArcD[route[i-1]]] +  SP[invArcD[route[i-1]]][invArcD[route[i]]] # + serviceCost[route[i]]               
            if edge1 < edge2:
                D[routeChange[i]] = edge1
                PI[routeChange[i]] = routeChange[i-1]
            else:
                D[routeChange[i]] = edge2
                PI[routeChange[i]] = invArcD[routeChange[i-1]]
            if invArcD[route[i]]:
                edge3 = D[route[i-1]] + SP[route[i-1]][invArcD[route[i]]] #+ serviceCost[route[i]]
                if edge3 < edge4:
                    D[invArcD[routeChange[i]]] = edge3
                    PI[invArcD[routeChange[i]]] = routeChange[i-1]
                else:
                    D[invArcD[routeChange[i]]] = edge4
                    PI[invArcD[routeChange[i]]] = invArcD[routeChange[i-1]]
                    
        if invArcD[route[i]]:
            if D[route[i]] < D[invArcD[route[i]]]:
                D['t'] = D[routeChange[i]]
                PI['t'] = routeChange[i]                
            else:
                D['t'] = D[invArcD[routeChange[i]]]
                PI['t'] = invArcD[routeChange[i]]  
        else:
            D['t'] = D[routeChange[i]]
            PI['t'] = routeChange[i]
        cost = D['t']
        optimalRoute = sp1SourceList(PI, 's', 't')
        if change:
            optimalRoute[-2] = dummy[optimalRoute[-2]]
        if change2:
            optimalRoute[-3] = dummy2[optimalRoute[-3]]
        impRoute = optimalRoute[1:-1]
        return(impRoute, cost)
                            
    def reverse_route(self, route):
        new_route = deepcopy(route)
        new_route.reverse()
        new_route.insert(0, self.depot)
        new_route.append(self.depot)
        (new_route, deadcost) = self.optRoute(new_route)
        deadcost += self.dumpCost
        return(new_route[1:-1], deadcost)
    
    def reverse_all_routes(self, routes):
        all_routes = []
        all_dead = []
        for route in routes:
            (new_route, deadcost) = self.reverse_route(route)
            all_routes.append(new_route)
            all_dead.append(deadcost)
        return(all_routes, deadcost)
    
    def opt_routes(self, routes):
        all_routes = []
        all_dead = []
        for route in routes:
            (new_route, deadcost) = self.optRoute(route)
            all_routes.append(new_route)
            all_dead.append(deadcost)
        return(all_routes, all_dead)

    def opt_routes2(self, routes):
        all_routes = []
        all_dead = []
        for route in routes:
            route2 = [self.depot] + route + [self.depot] 
            (new_route, deadcost) = self.optRoute(route2)
            all_routes.append(new_route[1:-1])
            all_dead.append(deadcost + self.dumpCost)
        return(all_routes, all_dead)
            
    def reverse_clarpif_routes(self, routes):
        rev_routes = []
        for route in routes:
            rev_routes.append([])
            for trip in route:
                rev_trip = deepcopy(trip)
                rev_trip.reverse()
                rev_routes[-1].insert(0, rev_trip)
        return(rev_routes)
    
    def reverse_if_route(self, route, ifs):
        opt_rev_route = []
        if len(ifs) == 1:
            trip_rev = deepcopy(route)
            trip_rev.reverse()
            del trip_rev[1]
            trip_rev.insert(-1, self.if_arc[trip_rev[-2]][self.depot])
            (opt_trip, deadcost) = self.optRoute(trip_rev)
            opt_rev_route = trip_rev
        else:
            trip = route[1:ifs[0]+1]
            trip_rev = deepcopy(trip)
            trip_rev.reverse()
            trip_rev.append(self.if_arc[trip[-1]][self.depot])
            trip_rev.append(self.depot)
            (opt_trip, deadcost) = self.optRoute(trip_rev)
            opt_rev_route += trip_rev
            i = 0
            for i in xrange(1, len(ifs)-1):
                trip = route[ifs[i-1]:ifs[i]+1]
                trip_rev = deepcopy(trip)
                trip_rev.reverse()
                (opt_trip, deadcost) = self.optRoute(trip_rev)
                opt_rev_route = opt_trip[:-1] + opt_rev_route
            trip = route[ifs[i]:ifs[i+1]]
            trip_rev = deepcopy(trip)
            trip_rev.reverse()
            trip_rev.insert(0, self.depot)
            (opt_trip, deadcost) = self.optRoute(trip_rev)
            opt_rev_route = opt_trip[:-1] + opt_rev_route
        return(opt_rev_route)
    
    def reverse_if_route_complete(self, route, ifs_i):
        ifs_new = []
        n_ifs = range(len(ifs_i) - 1)
        n_ifs.reverse()
        for k in n_ifs:
            ifs_new.append(ifs_i[-1] - ifs_i[k])
        ifs_new.append(ifs_i[-1])
        return(self.reverse_if_route(route, ifs_i), ifs_new)

    def reverse_al_if_routes(self, solution_lists):
        (routes, trip_index, trip_load, loads, ifs, cost, service_a_full, load_a_full, normal_arcs,  normal_arcs_jump,
         if_arcs_pre, if_arcs_post, if_single_arcs_route, if_single_arcs_depot_trip, if_single_arcs_trip) = solution_lists
        all_routes = []
        ifs_n = []
        for i in xrange(len(routes)):
            opt_rev_route = self.reverse_if_route(routes[i], ifs[i])
            all_routes.append(opt_rev_route)
            ifs_new = []
            n_ifs = range(len(ifs[i]) - 1)
            n_ifs.reverse()
            for k in n_ifs:
                ifs_new.append(ifs[i][-1] - ifs[i][k])
            ifs_new.append(ifs[i][-1])
            ifs_n.append(ifs_new)
        return(self.builder.build_route_lists_from_routes(all_routes, ifs_n))
    
    def opt_IF_routes(self, routes):
        all_routes = []
        for route in routes:
            route_complete = []
            for i, trip in enumerate(route):
                new_trip = deepcopy(trip)
                if i == 0:
                    new_trip.insert(0, self.depot)
                else:
                    prev_arc = route[i-1][-1]
                    new_trip.insert(0, self.if_arc[prev_arc][trip[0]])
                if i == len(route)-1:
                    new_trip.append(self.if_arc[trip[-1]][self.depot])
                    new_trip.append(self.depot)
                    (opt_trip, deadcost) = self.optRoute(new_trip)
                    route_complete.append(opt_trip[1:-2])
                else:
                    next_arc = route[i+1][0]
                    new_trip.append(self.if_arc[trip[-1]][next_arc])
                    (opt_trip, deadcost) = self.optRoute(new_trip)
                    route_complete.append(opt_trip[1:-1])
            all_routes.append(route_complete)
        return(all_routes)
    
    def opt_if_reverse_routes(self, routes):
        rev_routes = self.reverse_clarpif_routes(routes)
        opt_rev_routes = self.opt_IF_routes(rev_routes)
        return(opt_rev_routes)
        
                    