'''
Created on 08 Apr 2012

@author: elias
'''
from __future__ import division
from math import ceil
import solver.Table_Output as Table_Output
import solver.py_solution_test as py_solution_test

def calc_CARP_stats(solution, info):
    capacity = info.capacity
    tServe = tDead = tLoad = 0
    for i in range(solution['nVehicles']):
        tServe += solution[i]['Service']
        tDead += solution[i]['Deadhead']
        tLoad += solution[i]['Load']
        
    nReqVehicles = int(ceil(tLoad/float(capacity)))    
    efficiency = float(tServe)/(solution['TotalCost'] - nReqVehicles*info.dumpCost)
    load_utilisation = float(tLoad)/(solution['nVehicles']*capacity)
    solution_info = {'cost' : int(solution['TotalCost']),
                     'nRoutes' : solution['nVehicles'],
                     'load' : tLoad,
                     'service_cost' : tServe,
                     'dead_cost' : int(tDead),
                     'efficiency' : efficiency,
                     'cost_utilisation' : 0.00,
                     'load_utilisation' : load_utilisation,
                     'nTrips' : 0}
    
    return(solution_info)

def calc_CLARPIF_stats(solution, info):
    capacity = info.capacity
    tServe = tDead = tLoad = TnTrips = 0
    for i in range(solution['nVehicles']):
        tServe += solution[i]['Service']
        tDead += solution[i]['Deadhead']
        tLoad += solution[i]['Load']
        TnTrips += solution[i]['nTrips']
        
    nReqVehicles = int(ceil(tLoad/float(capacity))) 
    efficiency = float(tServe)/(solution['TotalCost'] - nReqVehicles*info.dumpCost)
    load_utilisation = float(tLoad)/(TnTrips*capacity)
    solution_info = {'cost' : int(solution['TotalCost']),
                     'nRoutes' : solution['nVehicles'],
                     'load' : tLoad,
                     'service_cost' : tServe,
                     'dead_cost' : int(tDead),
                     'efficiency' : efficiency,
                     'cost_utilisation' : float(solution['TotalCost'])/(solution['nVehicles']*info.maxTrip),
                     'load_utilisation' : load_utilisation,
                     'nTrips' : TnTrips}    
    return(solution_info)

class display_solution_stats(object):

    def __init__(self, info):
        self.info = info
        self.capacity = info.capacity
        self.maxTrip = info.maxTrip
        self.dumpCost = info.dumpCost
        self.reqArcsPure = info.reqArcsPure
        self.reqEdgesPure = info.reqEdgesPure
        
    def display_CARP_solution_info(self, solution):
        
        nRequiredArcs = len(self.reqArcsPure)
        nRequiredEdge = len(self.reqEdgesPure)
        
        capacity = self.capacity
        dumpCost = self.dumpCost
        
        totalDemand = 0
        loadUtil = []
        for i in range(solution['nVehicles']):
            totalDemand += solution[i]['Load'] 
            util_l = solution[i]['Load']/float(capacity)
            loadUtil.append(util_l)

        nReqVehicles = int(ceil(totalDemand/float(capacity)))
        if nReqVehicles == solution['nVehicles']: 
            deadAdjust = dumpCost
        else: 
            deadAdjust = dumpCost/(solution['nVehicles'] - nReqVehicles)

        utility = []
        load_util = []
        for i in range(solution['nVehicles']):
            if 'Service' not in solution[i]:
                solution[i]['Service'] = sum([self.info.serveCostL[arc] for arc in solution[i]['Route']])
            if float(solution[i]['Cost']) != deadAdjust: ut = solution[i]['Service']/(float(solution[i]['Cost'] - deadAdjust))
            else: ut = 1e300000
            utility.append(ut)
            util_load = solution[i]['Load']/float(capacity)
            load_util.append(util_load)
            if 'Deadhead' not in solution[i]:
                solution[i]['Deadhead'] = solution[i]['Cost'] - solution[i]['Service'] - deadAdjust
            
        print('')
        print('Solution')
        for i in range(solution['nVehicles']):
            print(solution[i])
        print('')
        print('==================================================================================================')
        print(' PROBLEM INFO')
        print('--------------------------------------------------------------------------------------------------')
        print(' Type                 : %s' %solution['ProblemType'])
        print(' Required arcs        : %i' %nRequiredArcs)
        print(' Required edge        : %i' %nRequiredEdge)
        print('')
        print(' Vehicle cap          : %i' %capacity)
        print(' Min vehicles         : %i' %nReqVehicles)
        print(' Excess cap           : %i' %(nReqVehicles*capacity-totalDemand))
        print(' Solution excess cap  : %i' %(solution['nVehicles']*capacity-totalDemand))
        print('--------------------------------------------------------------------------------------------------')
        print('')
        data = ''
        tServe = tDead = tLoad = 0

        labels = (' Route', 'Cost', 'Service cost', 'Dead-head cost', 'Efficiency', 'Load', 'Load utilisation')
        trip = []
        for i in range(solution['nVehicles']):
            data += '%i,%i,%i,%i,%.2f,%i,%.2f \n'%(
                     i,   
                     solution[i]['Cost'], 
                     solution[i]['Service'], 
                     solution[i]['Deadhead'], 
                     utility[i], 
                     solution[i]['Load'], 
                     load_util[i])
            tServe += solution[i]['Service']
            tDead += solution[i]['Deadhead']
            tLoad += solution[i]['Load']
            trip.append(solution[i]['Route'])
        data += '%s,%s,%s,%s,%s,%s \n'%('','','','','','')
        data += '%i,%i,%i,%i,%.2f,%i,%.2f \n'%(
                     solution['nVehicles'],   
                     solution['TotalCost'], 
                     tServe, 
                     tDead, 
                     float(tServe)/(solution['TotalCost']  - nReqVehicles*dumpCost), 
                     tLoad,
                     float(tLoad)/(solution['nVehicles']*self.capacity))
        Table_Output.print_table(' SOLUTION TABLE', labels, data)
        print('--------------------------------------------------------------------------------------------------')
        print(' SUMMARY')
        print('--------------------------------------------------------------------------------------------------')
        print(' Total cost   : %i' %solution['TotalCost'])
        print(' Total demand : %i' %tLoad)
        print(' # Vehicles   : %i' %solution['nVehicles'] )
        print('==================================================================================================')
        print('')
        print('Routes')
        print('----------------------------------------------------')
        for i, t in enumerate(trip): print(i,t)
        print('')
        py_solution_test.test_solution(self.info, solution)
        
    def display_CLARPIF_solution_info(self, solution):
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
            totalDemand = 0
            totalDemand += solution[i]['Load']

        nReqTrip = int(ceil(totalDemand/float(self.capacity)))
            
        print('')
        print(solution)
        print('')
        print('===========================================================================================================================')
        print(' PROBLEM INFO')
        print('---------------------------------------------------------------------------------------------------------------------------')
        print(' Type                : %s' %solution['ProblemType'])
        print(' Excess service time : %.4f' %excess)
        print('---------------------------------------------------------------------------------------------------------------------------')
        print('')
        data = ''
        tServe = tDead = TnTrips = tLoad = 0
        trip = []
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
            trip.append(solution[i]['Trips'])
        data += '%s,%s,%s,%s,%s,%s,%s,%s \n'%('','','','','','','','',)
        data += '%i,%i,%i,%i,%.2f,%.2f,%.2f,%i \n'%(
                     solution['nVehicles'],   
                     solution['TotalCost'], 
                     tServe, 
                     tDead, 
                     float(tServe)/(solution['TotalCost'] - nReqTrip*self.dumpCost), 
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
        print('Trips')
        print('----------------------------------------------------')
        for t in trip: print(t)
        print('')
    
    def display_solution_info(self, solution):
        if solution['ProblemType'] == 'CARP': self.display_CARP_solution_info(solution)
        if solution['ProblemType'] == 'CLARPIF':self.display_CLARPIF_solution_info(solution)

from converter.alg_shortest_paths import spSource1List

def display_converted_route(solution, arc_info, sp_info, info):
    arc_info.allIndexD
    arc_info.reqArcs_map
    for i in range(solution['nVehicles']):
        for k, trip in enumerate(solution[i]['Trips']):
            print('Route %i Trip %i'%(i,k))
            print('-------------------------------------')
            for l, arc in enumerate(trip[:-1]): 
                arc_actual = arc_info.reqArcs_map[arc]
                arc_actual_next = arc_info.reqArcs_map[trip[l+1]]
                arc_full = arc_info.allIndexD[arc_actual]
                line = 'Service arc:; (%i,%i); demand:; %i; service cost:; %i; dead-head cost to next arc:; %i'%(arc_full[0], arc_full[1], info.demandL[arc], info.serveCostL[arc], info.d[arc][trip[l+1]])
                print(line)
                sp = spSource1List(sp_info.p_full, arc_actual, arc_actual_next)
                for a in sp: 
                    line = 'Dead-head arc:; (%i,%i);;; traversal cost:; %i'%(arc_info.allIndexD[a][0],arc_info.allIndexD[a][1], arc_info.travelCostL[a])
                    print(line)
            arc = trip[-1]
            arc_actual = arc_info.reqArcs_map[arc]
            arc_full = arc_info.allIndexD[arc_actual]
            line = 'Service arc:; (%i,%i); demand:; %i; service cost:; %i'%(arc_full[0], arc_full[1], info.demandL[arc], info.serveCostL[arc])
            print(line)
            print('')
            print('')
        
        
        
        
        
        
        
        
        