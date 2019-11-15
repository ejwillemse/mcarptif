from copy import deepcopy

class TestCARPSolution(object):
    
    def __init__(self, info, solution, print_output):
        self.info = info
        self.solution = solution
        self.errorReport = {}
        self.TeversalReport = []
        self.additionalTraversalReport = []
        self.outPutLines = []
        self.errorFound = False
        self.costError = False
        self.serviceError = False
        self.depotError = False
        self.vehicleError = False
        self.end_depot = self.info.depotnewkey
        self.print_output = print_output
        self.deadheading = True
        
    def testroutecosts(self, route_solution, total_cost):
        trip = route_solution['Route']
        cost = 0
        deadhead = 0
        servicecost = 0
        load = 0
        for i, arc in enumerate(trip[:-1]):
            arc_next = trip[i+1]
            deadhead += self.info.d[arc][arc_next]
            servicecost += self.info.serveCostL[arc]
            cost += self.info.d[arc][arc_next] + self.info.serveCostL[arc]
            load += self.info.demandL[arc]
            
        cost += self.info.serveCostL[trip[-1]] + self.info.dumpCost
        deadhead += self.info.dumpCost
        servicecost += self.info.serveCostL[trip[-1]]
        load += self.info.demandL[trip[-1]]
        total_cost += cost
        
        if route_solution['Cost'] != cost:
            self.costError = True
            self.errorFound = True
            if self.print_output:
                print('Cost Error')
                print('Incorrect route cost - Actual: %i \t Specified: %i' %(cost, route_solution['Cost']))
        if route_solution['Deadhead'] != deadhead  and self.deadheading:
            self.costError = True
            self.errorFound = True
            if self.print_output:
                print('Cost Error')
                print('Incorrect route deadheading cost - Actual: %i \t Specified: %i' %(deadhead, route_solution['Deadhead']))
        if route_solution['Service'] != servicecost and self.deadheading:
            self.costError = True
            self.errorFound = True
            if self.print_output:
                print('Cost Error')
                print('Incorrect route service cost - Actual: %i \t Specified: %i' %(servicecost, route_solution['Service']))
        if route_solution['Load'] != load:
            self.costError = True    
            self.errorFound = True
            if self.print_output:  
                print('Cost Error')
                print('Incorrect route load - Actual: %i \t Specified: %i' %(load, route_solution['Load']))
        if route_solution['Load'] > self.info.capacity: 
            self.costError = True      
            self.errorFound = True
            if self.print_output:
                print('Constraint Error')
                print('Load is more than vehicle capacity - Actual: %i \t Limit: %i' %(route_solution['Load'], self.info.capacity)) 
        
        return(total_cost)
        
    def testservice(self, trip, servicedarcs):
        for arc in trip[1:-1]:
            if arc in servicedarcs:
                arc1 = servicedarcs.index(arc)
                if self.info.reqInvArcList[arc]:
                    arc2 = servicedarcs.index(self.info.reqInvArcList[arc])
                    del servicedarcs[max(arc1, arc2)]
                    del servicedarcs[min(arc1, arc2)]
                else: 
                    del servicedarcs[arc1]
            elif arc == self.info.depotnewkey:
                self.serviceError = True
                self.errorFound = True
                if self.print_output:
                    print('Service Error')
                    print('Depot visit in middle of trip')
            elif arc in self.info.IFarcsnewkey:
                self.serviceError = True
                self.errorFound = True
                if self.print_output:
                    print('Service Error')
                    print('IF visit in middle of trip', arc)
            elif arc not in self.info.reqArcList: 
                self.serviceError = True
                self.errorFound = True
                if self.print_output:
                    print('Service Error')
                    print('Arc does not need to be serviced',arc)
            else:
                self.serviceError = True
                self.errorFound = True
                if self.print_output:
                    print('Service Error')
                    print('Arc already serviced',arc)
        
        return(servicedarcs)
    
    def testdepot(self, trip):
        if trip[0] != self.info.depotnewkey:
            self.depotError = True
            self.errorFound = True
            if self.print_output:
                print('Depot Error')
                print('Route does not begin at depot')
        if trip[-1] != self.end_depot:
            self.depotError = True
            self.errorFound = True
            if self.print_output:
                print('Depot Error')
                print('Route does not end at depot')
        
    def testCARPsolution(self):
        nRoutes = self.solution['nVehicles']
        
        if nRoutes != len(self.solution) - 3:
            self.errorFound = True
            if self.print_output:
                print('Vehicle Error')
                print('More vehicles than specified - Actual: %i \t Specified: %i' %(nRoutes, len(self.solution) - 3))
            
        servicedarcs = deepcopy(self.info.reqArcListActual)
        total_cost = 0
        for i in range(nRoutes):
            self.testdepot(self.solution[i]['Route'])
            (servicedarcs) = self.testservice(self.solution[i]['Route'], servicedarcs)
            total_cost = self.testroutecosts(self.solution[i], total_cost)
        if servicedarcs:
            self.serviceError = True
            self.errorFound = True
            if self.print_output:
                print('Service Error')
                print('Arcs not serviced',servicedarcs)
        if total_cost != self.solution['TotalCost']:
            self.costError = True
            self.errorFound = True
            if self.print_output:
                print('Cost Error')
                print('Incorrect solution cost - Actual: %i \t Specified: %i' %(total_cost, self.solution['TotalCost']))
        
    def testMCARP(self):
        self.testCARPsolution()
        return(self.errorFound)

class TestCLARPIFSolution(object):
    
    def __init__(self, info, solution):
        self.info = info
        self.solution = solution
        self.errorReport = {}
        self.TeversalReport = []
        self.additionalTraversalReport = []
        self.outPutLines = []
        self.costError = False
        self.serviceError = False
        self.depotError = False
        self.ifError = False
        self.Error = False
        self.end_depot = self.info.depotnewkey
        
    def testtripcosts(self, trip, route_cost_info):
        (trip_cost,
        trip_dead_head_cost,
        trip_service_cost,
        trip_load) = route_cost_info
        cost = 0
        deadhead = 0
        servicecost = 0
        load = 0
        for i, arc in enumerate(trip[:-1]):
            arc_next = trip[i+1]
            deadhead += self.info.d[arc][arc_next]
            servicecost += self.info.serveCostL[arc]
            cost += self.info.d[arc][arc_next] + self.info.serveCostL[arc]
            load += self.info.demandL[arc]
            
        cost += self.info.serveCostL[trip[-1]] + self.info.dumpCost
        deadhead += self.info.dumpCost
        servicecost += self.info.serveCostL[trip[-1]]
        load += self.info.demandL[trip[-1]]
        
        if trip_cost != cost:
            self.Error = self.costError = True
            print('Cost Error')
            print('Incorrect trip cost - Actual: %i \t Specified: %i' %(trip_cost, cost))
        if trip_dead_head_cost != deadhead:
            self.Error = self.costError = True
            print('Cost Error')
            print('Incorrect trip deadheading cost - Actual: %i \t Specified: %i' %(trip_dead_head_cost, deadhead))
        if trip_service_cost != servicecost:
            self.Error = self.costError = True
            print('Cost Error')
            print('Incorrect trip service cost - Actual: %i \t Specified: %i' %(trip_service_cost, servicecost))
        if trip_load != load:
            self.Error = self.costError = True      
            print('Cost Error')
            print('Incorrect trip load', trip_load, load)
        if trip_load > self.info.capacity: 
            self.Error = self.costError = True      
            print('Constraint Error')
            print('Load is more than vehicle capacity - Actual: %i \t Specified: %i' %(trip_load, self.info.capacity))
        return(cost, deadhead, servicecost, load)
  
    def testservice(self, trip, servicedarcs):
        for arc in trip[1:-1]:
            if arc in servicedarcs:
                arc1 = servicedarcs.index(arc)
                if self.info.reqInvArcList[arc]:
                    arc2 = servicedarcs.index(self.info.reqInvArcList[arc])
                    del servicedarcs[max(arc1, arc2)]
                    del servicedarcs[min(arc1, arc2)]
                else: 
                    del servicedarcs[arc1]
            elif (arc == self.info.depotnewkey)|(arc == self.end_depot):
                self.Error = self.serviceError = True
                print('Service Error')
                print('Depot visit in middle of trip')
            elif arc in self.info.IFarcsnewkey:
                self.Error = self.serviceError = True
                print('Service Error')
                print('IF visit in middle of trip', arc)
            elif arc not in self.info.reqArcList: 
                self.Error = self.serviceError = True
                print('Service Error')
                print('Arc does not need to be serviced',arc)
            else:
                self.Error = self.serviceError = True
                print('Service Error')
                print('Arc already serviced',arc)
        return(servicedarcs)
    
    def testIFdepot(self, trip):
        if trip[-2] not in self.info.IFarcsnewkey:
            self.Error = self.ifError = True
            print('IF Error')
            print('Route does not end at IF then depot')
        if trip[-1] != self.end_depot:
            self.Error = self.depotError = True
            print('Depot Error')
            print('Route does not end at depot')
    
    def testDepot(self, trip):
        if trip[0] != self.info.depotnewkey:
            self.Error = self.depotError = True
            print('Depot Error')
            print('Route does not begin at depot')
    
    def testIFs(self, IFvisit, prevIFvisit):
        if IFvisit != prevIFvisit:
            self.Error = self.ifError = True
            print('IF Error')
            print('Trip does begin at same IF as previous trips end IF')
    
    def testroute(self, route_solution, servicedarcs, total_cost):
        nTrips = route_solution['nTrips']
        route_cost = 0
        route_deadhead = 0
        route_servicecost = 0
        route_load = 0
        for i in range(nTrips):
            if (i == 0) & (i == (nTrips - 1)):
                self.testDepot(route_solution['Trips'][i])
                (servicedarcs) = self.testservice(route_solution['Trips'][i][:-1], servicedarcs)
                self.testIFdepot(route_solution['Trips'][i])
            elif i == 0:
                self.testDepot(route_solution['Trips'][i])
                (servicedarcs) = self.testservice(route_solution['Trips'][i], servicedarcs)
            elif i == (nTrips - 1):
                (servicedarcs) = self.testservice(route_solution['Trips'][i][:-1], servicedarcs)
                self.testIFdepot(route_solution['Trips'][i])
                self.testIFs(route_solution['Trips'][i][0], route_solution['Trips'][i-1][-1])
            else:
                (servicedarcs) = self.testservice(route_solution['Trips'][i], servicedarcs)
                self.testIFs(route_solution['Trips'][i][0], route_solution['Trips'][i-1][-1])
            route_cost_info = (route_solution['TripCosts'][i],
                               route_solution['TripDeadheads'][i],
                               route_solution['TripServices'][i],
                               route_solution['TripLoads'][i])
            (cost, deadhead, servicecost, load) = self.testtripcosts(route_solution['Trips'][i], route_cost_info)
            route_cost += cost
            route_deadhead += deadhead
            route_servicecost += servicecost
            route_load += load
            
        if route_cost != route_solution['Cost']:
            self.Error = self.costError = True
            print('Cost Error')
            print('Incorrect route cost - Actual: %i \t Specified: %i' %(route_cost, route_solution['Cost']))
        if route_deadhead != route_solution['Deadhead']:
            self.Error = self.costError = True
            print('Cost Error')
            print('Incorrect route deadhead cost - Actual: %i \t Specified: %i' %(route_deadhead, route_solution['Deadhead']))
        if route_servicecost != route_solution['Service']:
            self.Error = self.costError = True
            print('Cost Error')
            print('Incorrect route service cost - Actual: %i \t Specified: %i' %(route_servicecost, route_solution['Service']))
        if route_load != route_solution['Load']:
            self.Error = self.costError = True
            print('Cost Error') 
            print('Incorrect route load - Actual: %i \t Specified: %i' %(route_load, route_solution['Load']))
        if route_cost > self.info.maxTrip: 
            self.Error = self.costError = True      
            print('Constraint Error')
            print('Route cost is more than max route cost - Actual: %i \t Specified: %i' %(route_cost, self.info.maxTrip))
        total_cost += route_cost
        return(servicedarcs, total_cost)
    
    def testCLARPIFsolution(self):
        nRoutes = self.solution['nVehicles']
        
        if nRoutes != len(self.solution) - 3:
            print('Vehicle Error')
            print('More vehicles than specified - Actual: %i \t Specified: %i' %(nRoutes, len(self.solution) - 3))
            
        total_cost = 0
        servicedarcs = deepcopy(self.info.reqArcListActual)
        for i in range(nRoutes):
            (servicedarcs, total_cost) = self.testroute(self.solution[i], servicedarcs,total_cost)
        if servicedarcs:
            self.Error = self.serviceError = True
            print('Service Error')
            print('Arcs not serviced',servicedarcs)
        if total_cost != self.solution['TotalCost']:
            self.Error = self.costError = True
            print('Cost Error')
            print('Incorrect solution cost - Actual: %i \t Specified: %i' %(total_cost, self.solution['TotalCost']))
         
    def testCLARPIF(self):
        self.testCLARPIFsolution()
        if self.Error: 
            a = 0
            #a = input('Error found : \n')
            print('Error found')
            a = input('')       
            
def test_solution(info, solution, print_output = True, deadheading = False):
    if solution['ProblemType'] == 'CARP':
        tst = TestCARPSolution(info, solution, print_output)
        tst.deadheading = deadheading
        errors = tst.testMCARP()
        if errors:
            print('Error found :',errors)
            a = input('')
        print('Test errors: %s'%errors)
        return(tst.testMCARP())
    elif solution['ProblemType'] == 'CLARPIF':
        tst2 = TestCLARPIFSolution(info, solution)
        tst2.testCLARPIF() 
    else:
        print('Problem type not specified for test')

            
            
            
            
            
            
            
            
            
            
            
        