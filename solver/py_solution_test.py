from copy import deepcopy
import logging

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
                logging.error('Cost Error')
                logging.error('Incorrect route cost - Actual: %i \t Specified: %i' %(cost, route_solution['Cost']))
        if route_solution['Deadhead'] != deadhead  and self.deadheading:
            self.costError = True
            self.errorFound = True
            if self.print_output:
                logging.error('Cost Error')
                logging.error('Incorrect route deadheading cost - Actual: %i \t Specified: %i' %(deadhead, route_solution['Deadhead']))
        if route_solution['Service'] != servicecost and self.deadheading:
            self.costError = True
            self.errorFound = True
            if self.print_output:
                logging.error('Cost Error')
                logging.error('Incorrect route service cost - Actual: %i \t Specified: %i' %(servicecost, route_solution['Service']))
        if route_solution['Load'] != load:
            self.costError = True    
            self.errorFound = True
            if self.print_output:  
                logging.error('Cost Error')
                logging.error('Incorrect route load - Actual: %i \t Specified: %i' %(load, route_solution['Load']))
        if route_solution['Load'] > self.info.capacity: 
            self.costError = True      
            self.errorFound = True
            if self.print_output:
                logging.error('Constraint Error')
                logging.error('Load is more than vehicle capacity - Actual: %i \t Limit: %i' %(route_solution['Load'], self.info.capacity)) 
        
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
                    logging.error('Service Error')
                    logging.error('Depot visit in middle of trip')
            elif arc in self.info.IFarcsnewkey:
                self.serviceError = True
                self.errorFound = True
                if self.print_output:
                    logging.error('Service Error')
                    logging.error('IF visit in middle of trip', arc)
            elif arc not in self.info.reqArcList: 
                self.serviceError = True
                self.errorFound = True
                if self.print_output:
                    logging.error('Service Error')
                    logging.error('Arc does not need to be serviced',arc)
            else:
                self.serviceError = True
                self.errorFound = True
                if self.print_output:
                    logging.error('Service Error')
                    logging.error('Arc already serviced',arc)
        
        return(servicedarcs)
    
    def testdepot(self, trip):
        if trip[0] != self.info.depotnewkey:
            self.depotError = True
            self.errorFound = True
            if self.print_output:
                logging.error('Depot Error')
                logging.error('Route does not begin at depot')
        if trip[-1] != self.end_depot:
            self.depotError = True
            self.errorFound = True
            if self.print_output:
                logging.error('Depot Error')
                logging.error('Route does not end at depot')
        
    def testCARPsolution(self):
        nRoutes = self.solution['nVehicles']
        
        if nRoutes != len(self.solution) - 3:
            self.errorFound = True
            if self.print_output:
                logging.error('Vehicle Error')
                logging.error('More vehicles than specified - Actual: %i \t Specified: %i' %(nRoutes, len(self.solution) - 3))
            
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
                logging.error('Service Error')
                logging.error('Arcs not serviced',servicedarcs)
        if total_cost != self.solution['TotalCost']:
            self.costError = True
            self.errorFound = True
            if self.print_output:
                logging.error('Cost Error')
                logging.error('Incorrect solution cost - Actual: %i \t Specified: %i' %(total_cost, self.solution['TotalCost']))
        
    def testMCARP(self):
        self.testCARPsolution()
        return(self.errorFound)

class TestCLARPIFSolution(object):
    
    def __init__(self, info, solution, tollerance=0.1):
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
        self.tollerance = tollerance
        
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
        
        if not cost - self.tollerance <= trip_cost <= cost + self.tollerance:
            self.Error = self.costError = True
            logging.error('Cost Error')
            logging.error('Incorrect trip cost - Actual: %i \t Specified: %i' %(trip_cost, cost))
            raise ValueError
        if not deadhead - self.tollerance <= trip_dead_head_cost <= deadhead + self.tollerance:
            self.Error = self.costError = True
            logging.error('Cost Error')
            logging.error('Incorrect trip deadheading cost - Actual: %i \t Specified: %i' %(trip_dead_head_cost, deadhead))
            raise ValueError
        if not servicecost - self.tollerance <= trip_service_cost <= servicecost + self.tollerance:
            self.Error = self.costError = True
            logging.error('Cost Error')
            logging.error('Incorrect trip service cost - Actual: %i \t Specified: %i' %(trip_service_cost, servicecost))
            raise ValueError
        if not load - self.tollerance <= trip_load <= load + self.tollerance:
            self.Error = self.costError = True      
            logging.error('Cost Error')
            logging.error('Incorrect trip load', trip_load, load)
            raise ValueError
        if trip_load > self.info.capacity + self.tollerance:
            self.Error = self.costError = True      
            logging.error('Constraint Error')
            logging.error('Load is more than vehicle capacity - Actual: %i \t Specified: %i' %(trip_load, self.info.capacity))
            raise ValueError
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
                logging.error('Service Error')
                logging.error('Depot visit in middle of trip')
            elif arc in self.info.IFarcsnewkey:
                self.Error = self.serviceError = True
                logging.error('Service Error')
                logging.error('IF visit in middle of trip', arc)
            elif arc not in self.info.reqArcList: 
                self.Error = self.serviceError = True
                logging.error('Service Error')
                logging.error('Arc does not need to be serviced',arc)
            else:
                self.Error = self.serviceError = True
                logging.error('Service Error')
                logging.error('Arc already serviced',arc)
        return(servicedarcs)
    
    def testIFdepot(self, trip):
        if trip[-2] not in self.info.IFarcsnewkey:
            self.Error = self.ifError = True
            logging.error('IF Error')
            logging.error('Route does not end at IF then depot')
        if trip[-1] != self.end_depot:
            self.Error = self.depotError = True
            logging.error('Depot Error')
            logging.error('Route does not end at depot')
    
    def testDepot(self, trip):
        if trip[0] != self.info.depotnewkey:
            self.Error = self.depotError = True
            logging.error('Depot Error')
            logging.error('Route does not begin at depot')
    
    def testIFs(self, IFvisit, prevIFvisit):
        if IFvisit != prevIFvisit:
            self.Error = self.ifError = True
            logging.error('IF Error')
            logging.error('Trip does begin at same IF as previous trips end IF')
    
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
            
        if not route_cost - self.tollerance <= route_solution['Cost'] <= route_cost + self.tollerance:
            self.Error = self.costError = True
            logging.error('Cost Error')
            logging.error('Incorrect route cost - Actual: %i \t Specified: %i' %(route_cost, route_solution['Cost']))
            raise ValueError
        if not route_deadhead - self.tollerance <= route_solution['Deadhead']\
               <= route_deadhead + \
                self.tollerance:
            self.Error = self.costError = True
            logging.error('Cost Error')
            logging.error('Incorrect route deadhead cost - Actual: %i \t Specified: %i' %(route_deadhead, route_solution['Deadhead']))
            raise ValueError

        if not route_servicecost - self.tollerance <= route_solution[
            'Service'] <= route_servicecost + self.tollerance:
            self.Error = self.costError = True
            logging.error('Cost Error')
            logging.error('Incorrect route service cost - Actual: %i \t Specified: %i' %(route_servicecost, route_solution['Service']))
            raise ValueError
        if not route_load - self.tollerance <= route_solution['Load'] <= \
               route_load + self.tollerance:
            self.Error = self.costError = True
            logging.error('Cost Error') 
            logging.error('Incorrect route load - Actual: %i \t Specified: %i' %(route_load, route_solution['Load']))
            raise ValueError
        if route_cost > self.info.maxTrip + self.tollerance:
            self.Error = self.costError = True      
            logging.error('Constraint Error')
            logging.error('Route cost is more than max route cost - Actual: %i \t Specified: %i' %(route_cost, self.info.maxTrip))
            raise ValueError
        total_cost += route_cost
        return(servicedarcs, total_cost)
    
    def testCLARPIFsolution(self):
        nRoutes = self.solution['nVehicles']
        
        if nRoutes != len(self.solution) - 3:
            logging.error('Vehicle Error')
            logging.error('More vehicles than specified - Actual: %i \t Specified: %i' %(nRoutes, len(self.solution) - 3))
            
        total_cost = 0
        servicedarcs = deepcopy(list(self.info.reqArcListActual))
        for i in range(nRoutes):
            (servicedarcs, total_cost) = self.testroute(self.solution[i], servicedarcs,total_cost)
        if servicedarcs:
            self.Error = self.serviceError = True
            logging.error('Service Error')
            logging.error('Arcs not serviced',servicedarcs)
        if not self.solution['TotalCost'] - self.tollerance <=total_cost <= \
               self.solution['TotalCost'] + self.tollerance:
            self.Error = self.costError = True
            logging.error('Cost Error')
            logging.error('Incorrect solution cost - Actual: %i \t Specified: %i' %(total_cost, self.solution['TotalCost']))
            raise ValueError
         
    def testCLARPIF(self):
        self.testCLARPIFsolution()
        if self.Error: 
            a = 0
            #a = input('Error found : \n')
            logging.error('Error found')
                  
            
def test_solution(info, solution, print_output = True, deadheading = False):
    if solution['ProblemType'] == 'CARP':
        tst = TestCARPSolution(info, solution, print_output)
        tst.deadheading = deadheading
        errors = tst.testMCARP()
        if errors:
            logging.error('Error found :',errors)
            a = input('')
        logging.error('Test errors: %s'%errors)
        return(tst.testMCARP())
    elif solution['ProblemType'] == 'CLARPIF':
        tst2 = TestCLARPIFSolution(info, solution)
        tst2.testCLARPIF() 
    else:
        logging.error('Problem type not specified for test')

            
            
            
            
            
            
            
            
            
            
            
        