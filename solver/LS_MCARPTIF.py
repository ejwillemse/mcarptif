'''
Created on 11 Jun 2015

@author: eliaswillemse

Class to implement Local Search for the Mixed Capacitated Arc Routing Problem.
'''

from __future__ import division

import os
import solver.sysPath as sysPath
import sys
sys = sysPath.addInputPaths(sys)
mainPath = sysPath.returnPath()

import random
import solver.calcMoveCost as calcMoveCost
import solver.py_display_solution as py_display_solution
from copy import deepcopy
import pickle
from time import clock
from solver.py_reduce_number_trips import Reduce_Trips as ReduceRoutes
from solver.py_solution_builders import build_CLARPIF_dict_correct

class TestLocalSeach(object):
    '''
    Class to check if solution and locals search moves are calculated correctly
    '''
    def __init__(self, info):
        '''
        Class initialization values.
        '''
        # Problem info
        self._info = info
        self._d = info.d
        self._depot = info.depotnewkey
        self._dumpCost = info.dumpCost
        self._demand = info.demandL
        self._maxTrip = info.maxTrip
        self._service = info.serveCostL
        self._capacity = info.capacity
        self._ifs = info.IFarcsnewkey
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._nReqArcs = len(self._reqArcs)
        self._nEliments = len(self._d)
        self._reqArcsSet = set(self._reqArcs)
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self._arcsL = [arc for arc in self._reqArcs if arc not in self._edgesS]
        self._arcsS = set(self._arcsL)
        self._prevSolution = None  
        self._if_cost = info.if_cost_np
        self._if_arc = info.if_arc_np

    def _testSolution(self, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        totalCost = 0
        errorsFound = False
        arcsNotService = self._reqArcsSet.copy()
        for i in range(solution['nVehicles']):
            routeI = solution[i]['Trips']
            nTrips = len(routeI)
            routeCost = 0
            for tripIndex, trip in enumerate(routeI):
                demand = sum([self._demand[arc] for arc in trip])
                serviceCost = sum([self._service[arc] for arc in trip])
                deadheadCost = sum([self._d[trip[j]][trip[j+1]] for j in range(len(trip)-1)]) + self._dumpCost
                routeCost += serviceCost + deadheadCost
                if demand != solution[i]['TripLoads'][tripIndex]:
                    errorsFound = True
                    print('ERROR: Incorrect route load specified for route %i trip %i: actual %i vs %i'%(i, tripIndex, demand, solution[i]['TripLoads'][tripIndex]))
                if demand > self._capacity:
                    errorsFound = True 
                    print('ERROR: Trip demand exceeds capacity for route %i trip %i: actual %i vs %i'%(i, tripIndex, demand, self._capacity))
                if tripIndex == 0 and routeI[tripIndex][0] != self._depot:
                    errorsFound = True
                    print('ERROR: First arc not the depot in route %i: %i'%(i, routeI[tripIndex][0]))
                lastArcI = -1
                if tripIndex == nTrips - 1:
                    lastArcI = -2
                    if routeI[tripIndex][-1] != self._depot:
                        errorsFound = True
                        print('ERROR: Last arc not the depot in route %i: %i'%(i, routeI[tripIndex][-1]))
                    if routeI[tripIndex][-2] not in self._ifs:
                        errorsFound = True
                        print('ERROR: Second last arc not IF in route %i: %i'%(i, routeI[tripIndex][-2]))
                elif routeI[tripIndex][-1] not in self._ifs:
                        errorsFound = True
                        print('ERROR: last arc not IF in route %i trip %i: %i'%(i, tripIndex, routeI[tripIndex][-1]))
                for arc in routeI[tripIndex][1:lastArcI]:
                    if arc not in arcsNotService:
                        errorsFound = True
                        print('ERROR: Arc does not have to be serviced in route %i trip %i: %i'%(i, tripIndex, arc))
                    else:
                        arcsNotService.remove(arc)
                        if arc in self._edgesS:
                            arcsNotService.remove(self._inv[arc])
                if tripIndex < len(routeI) - 1:
                    bestIF = self._if_arc[routeI[tripIndex][-2]][solution[i]['Trips'][tripIndex + 1][1]]
                    if routeI[tripIndex][-1] != bestIF:
                        errorsFound = True
                        print('ERROR: Suboptimal IF visit at the end of trip %i: %i instead of %i'%(i, routeI[tripIndex][-1], bestIF))
                    if routeI[tripIndex][-1] != solution[i]['Trips'][tripIndex + 1][0]:
                        errorsFound = True
                        print('ERROR: Last IF visit at the end of trip %i not the same as next trip: %i and %i'%(i, routeI[tripIndex][-1], solution[i]['Trips'][tripIndex + 1][0]))
                                                    
            if routeCost != solution[i]['Cost']:
                errorsFound = True
                print('ERROR: Incorrect route cost specified for route %i: actual %i vs %i'%(i, routeCost, solution[i]['Cost']))
                #totalCost += serviceCost + deadheadCost
            if routeCost > self._maxTrip:
                errorsFound = True 
                print('ERROR: Route cost exceeds max cost limit for route %i: actual %i vs %i'%(i, routeCost, self._maxTrip))
            totalCost += routeCost
            
        if  totalCost != solution['TotalCost']:
            errorsFound = True
            print('ERROR: Incorrect total cost specified: actual %i vs %i'%(totalCost, solution['TotalCost']))   
        for arc in arcsNotService:
            errorsFound = True
            if arc in self._edgesS:
                print('ERROR: Not all required arcs serviced: %i or %i'%(arc, self._inv[arc]))
            else:
                print('ERROR: Not all required arcs serviced: %i'%arc)
             
        if errorsFound:
            #print('Previous solution',self._prevSolution)
            #print('Current solution ',solution)
            #(routeI, tripI) = (0, 2)
            #(routeJ, tripJ) = (5, 2)
            #print(routeI, self._prevSolution[routeI]['Trips'][tripI])#, self._prevSolution[routeI]['Trips'][tripI+1])
            #print(routeJ, self._prevSolution[routeJ]['Trips'][tripJ])
#            print(solution[2]['Trips'][0], solution[2]['Trips'][-1])
            #print(routeI, solution[routeI]['Trips'][tripI])#, solution[routeI]['Trips'][tripI+1])
            #print(routeJ, solution[routeJ]['Trips'][tripJ])
#             print(self._d[114][2] + self._d[2][solution[7]['Trips'][1][1]])
#             print(self._d[114][1] + self._d[1][solution[7]['Trips'][1][1]])
            raise NameError('Errors found with solution above, please see comments above solution.')            
        
        self._prevSolution = deepcopy(solution)
        
    def _testRelocateMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        
        if moveType.find('relocate') == -1: 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (relocate).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, tripI, removePos) = solutionMapping[arcI]
        if moveType.find('relocatePreArcIF') != -1:   
            preArc = solution[routeI]['Trips'][tripI][removePos - 1]
            arc = solution[routeI]['Trips'][tripI][removePos]
            if tripI == len(solution[routeI]['Trips']) - 1:
                postArc = solution[routeI]['Trips'][tripI][removePos + 2]
            else:
                postArc = solution[routeI]['Trips'][tripI + 1][1]
            actualMoveCostsI = self._if_cost[preArc][postArc] - (self._d[preArc][arc] + self._if_cost[arc][postArc])        
        elif moveType.find('relocatePostArcIF') != -1:
            preArc = solution[routeI]['Trips'][tripI - 1][-2]
            arc = solution[routeI]['Trips'][tripI][removePos]
            postArc = solution[routeI]['Trips'][tripI][removePos + 1]
            actualMoveCostsI = self._if_cost[preArc][postArc] - (self._if_cost[preArc][arc] + self._d[arc][postArc])                
        else: 
            preArc = solution[routeI]['Trips'][tripI][removePos - 1]
            arc = solution[routeI]['Trips'][tripI][removePos]
            postArc = solution[routeI]['Trips'][tripI][removePos + 1]
            actualMoveCostsI = self._d[preArc][postArc] - (self._d[preArc][arc] + self._d[arc][postArc])
        
        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to remove not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print(solution[routeI]['Trips'][tripI])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Trips'][tripI])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Trips'])
                    
        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated remove move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Trips'][tripI])
            
        (routeJ, tripJ, insertPos) = solutionMapping[arcJ]
        preArc = solution[routeJ]['Trips'][tripJ][insertPos - 1]
        arc = solution[routeJ]['Trips'][tripJ][insertPos]
        actuaMoveCostsJ = self._d[preArc][arcI] + self._d[arcI][arc]- self._d[preArc][arc]

        if arcJ != arc:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print(solution[routeJ]['Trips'][tripJ])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print(solution[routeJ]['Trips'][tripJ])
        
        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated insert move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Trips'][tripJ])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Trips'][tripI])
            print(solution[routeJ]['Trips'][tripJ])
                   
        if errorsFound:
            print(solution)
            print(moveInfo)
            raise NameError('Errors found with move to solution above, please see comments above solution.')   

    def _testRelocateIFMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        
        if moveType.find('relocate') == -1: 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (relocate).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, tripI, removePos) = solutionMapping[arcI]
        
        if moveType.find('relocatePreIF') != -1:   
            preArc = solution[routeI]['Trips'][tripI][removePos - 1]
            arc = solution[routeI]['Trips'][tripI][removePos]
            if tripI == len(solution[routeI]['Trips']) - 1:
                postArc = solution[routeI]['Trips'][tripI][removePos + 2]
            else:
                postArc = solution[routeI]['Trips'][tripI + 1][1]
            actualMoveCostsI = self._if_cost[preArc][postArc] - (self._d[preArc][arc] + self._if_cost[arc][postArc])        
        elif moveType.find('relocatePostIF') != -1:
            preArc = solution[routeI]['Trips'][tripI - 1][-2]
            arc = solution[routeI]['Trips'][tripI][removePos]
            postArc = solution[routeI]['Trips'][tripI][removePos + 1]
            actualMoveCostsI = self._if_cost[preArc][postArc] - (self._if_cost[preArc][arc] + self._d[arc][postArc])                
        else: 
            preArc = solution[routeI]['Trips'][tripI][removePos - 1]
            arc = solution[routeI]['Trips'][tripI][removePos]
            postArc = solution[routeI]['Trips'][tripI][removePos + 1]
            actualMoveCostsI = self._d[preArc][postArc] - (self._d[preArc][arc] + self._d[arc][postArc])
        
        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to remove not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print('Remove arc route trip (%i, %i)'%(routeI, tripI))
            print(solution[routeI]['Trips'][tripI])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print('Remove arc route trip (%i, %i)'%(routeI, tripI))
            print(solution[routeI]['Trips'][tripI])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print('Remove arc route trip (%i, %i)'%(routeI, tripI))
            print(solution[routeI]['Trips'])
                    
        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated remove move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Trips'][tripI])
            
        (routeJ, tripJ, insertPos) = solutionMapping[arcJ]
        
        if moveType.find('_PreIF') != -1:  
            preArc = solution[routeJ]['Trips'][tripJ][insertPos]
            if tripJ == len(solution[routeJ]['Trips']) - 1:
                arc = solution[routeJ]['Trips'][tripJ][insertPos + 2]
            else:
                #print(solution[routeJ]['Trips'][tripJ], solution[routeJ]['Trips'][tripJ + 1]) 
                arc = solution[routeJ]['Trips'][tripJ + 1][1]
            actuaMoveCostsJ = self._d[preArc][arcI] + self._if_cost[arcI][arc]- self._if_cost[preArc][arc]
            preArcJ = arcJ
            arcJ = postArcJ
            
        elif moveType.find('_PostIF') != -1:
            preArc = solution[routeJ]['Trips'][tripJ - 1][-2]
            arc = solution[routeJ]['Trips'][tripJ][insertPos]
            actuaMoveCostsJ = self._if_cost[preArc][arcI] + self._d[arcI][arc] - self._if_cost[preArc][arc]
            
        if arcJ != arc:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print('Insert arc route trip (%i, %i)'%(routeJ, tripJ))
            print(solution[routeJ]['Trips'][tripJ])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print('Insert arc route trip (%i, %i)'%(routeJ, tripJ))
            print(solution[routeJ]['Trips'][tripJ])
        
        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated insert move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print('Insert arc route trip (%i, %i)'%(routeJ, tripJ))
            print(solution[routeJ]['Trips'][tripJ])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print('Insert arc route trip (%i, %i)'%(routeJ, tripJ))
            print(solution[routeI]['Trips'][tripI])
            print(solution[routeJ]['Trips'][tripJ])
                   
        if errorsFound:
            print(moveInfo)
            raise NameError('Errors found with move to solution above, please see comments above solution.')  

    def _testDoubleRelocateMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI1, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        arcI2 = postArcJ
        if moveType != 'doubleRelocate': 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (relocate).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, tripI, removePos) = solutionMapping[arcI1]
        preArc = solution[routeI]['Trips'][tripI][removePos - 1]
        arc1 = solution[routeI]['Trips'][tripI][removePos]
        arc2 = solution[routeI]['Trips'][tripI][removePos + 1]
        postArc = solution[routeI]['Trips'][tripI][removePos + 2]
        actualMoveCostsI = self._d[preArc][postArc] - (self._d[preArc][arc1] + self._d[arc2][postArc])
        
        if arcI1 != arc1 or arcI2 != arc2:
            errorsFound = True
            print('ERROR: Arc to remove not the same as the one currently in the route position %i: actual %i, %i vs %i, %i'%(routeI, arc1, arcI1, arc2, arcI2))
            print(solution[routeI][tripI]['Route'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI][tripI]['Route'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI][tripI]['Route'])
                    
        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated remove move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI][tripI]['Route'])
            
        (routeJ, tripJ, insertPos) = solutionMapping[arcJ]
        preArc = solution[routeJ]['Trips'][tripJ][insertPos - 1]
        arc = solution[routeJ]['Trips'][tripJ][insertPos]
        actuaMoveCostsJ = self._d[preArc][arcI1] + self._d[arcI2][arc]- self._d[preArc][arc]

        if arcJ != arc:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print(solution[routeJ]['Trips'])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print(solution[routeJ]['Trips'])
        
        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated insert move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Trips'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Trips'])
            print(solution[routeJ]['Trips'])
                   
        if errorsFound:
            print(solution)
            print(moveInfo)
            raise NameError('Errors found with move to solution above, please see comments above solution.')  

    def _testExchangeMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        
        if moveType.find('exchange') == -1: 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (relocate).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, tripI, removePos) = solutionMapping[arcI]
        
        
        if moveType.find('1excPostIF') != -1:
            preArc = solution[routeI]['Trips'][tripI - 1][-2]
            arc = solution[routeI]['Trips'][tripI][removePos]
            postArc = solution[routeI]['Trips'][tripI][removePos + 1]
            actualMoveCostsI = self._if_cost[preArc][arcJ] + self._d[arcJ][postArc]  - (self._if_cost[preArc][arc] + self._d[arc][postArc])
        elif moveType.find('1excPreIF') != -1:
            preArc = solution[routeI]['Trips'][tripI][removePos - 1]
            arc = solution[routeI]['Trips'][tripI][removePos]
            if tripI == len(solution[routeI]['Trips']) - 1:
                postArc = solution[routeI]['Trips'][tripI][removePos + 2]
            else:
                postArc = solution[routeI]['Trips'][tripI + 1][1]    
            actualMoveCostsI = self._d[preArc][arcJ] + self._if_cost[arcJ][postArc]  - (self._d[preArc][arc] + self._if_cost[arc][postArc])
        else:
            preArc = solution[routeI]['Trips'][tripI][removePos - 1]
            arc = solution[routeI]['Trips'][tripI][removePos]
            postArc = solution[routeI]['Trips'][tripI][removePos + 1]
            actualMoveCostsI = self._d[preArc][arcJ] + self._d[arcJ][postArc]  - (self._d[preArc][arc] + self._d[arc][postArc])        
        
        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to exchange not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print(solution[routeI]['Trips'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before exchange arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Trips'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after exchange arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Trips'])

        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated exchange move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Trips'])
            
        (routeJ, tripJ, removePos) = solutionMapping[arcJ]
        
        if moveType.find('2excPostIF') != -1:
            preArc = solution[routeJ]['Trips'][tripJ - 1][-2]
            arc = solution[routeJ]['Trips'][tripJ][removePos]
            postArc = solution[routeJ]['Trips'][tripJ][removePos + 1]
            actuaMoveCostsJ = self._if_cost[preArc][arcI] + self._d[arcI][postArc]  - (self._if_cost[preArc][arc] + self._d[arc][postArc])
        elif moveType.find('2excPreIF') != -1:
            preArc = solution[routeJ]['Trips'][tripJ][removePos - 1]
            arc = solution[routeJ]['Trips'][tripJ][removePos]
            if tripJ == len(solution[routeJ]['Trips']) - 1:
                postArc = solution[routeJ]['Trips'][tripJ][removePos + 2]
            else:
                postArc = solution[routeJ]['Trips'][tripJ + 1][1] 
            actuaMoveCostsJ = self._d[preArc][arcI] + self._if_cost[arcI][postArc]  - (self._d[preArc][arc] + self._if_cost[arc][postArc])
         
        else:
            preArc = solution[routeJ]['Trips'][tripJ][removePos - 1]
            arc = solution[routeJ]['Trips'][tripJ][removePos]
            postArc = solution[routeJ]['Trips'][tripJ][removePos + 1]
            actuaMoveCostsJ = self._d[preArc][arcI] + self._d[arcI][postArc]  - (self._d[preArc][arc] + self._d[arc][postArc])
            
        if arcJ != arc and self._inv[arcJ] != arc:
            errorsFound = True
            print('ERROR: Arc to exchange not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print(solution[routeJ]['Trips'])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before exchange not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print(solution[routeJ]['Trips'])
            
        if postArc != postArcJ:
            errorsFound = True
            print('ERROR: Arc now after exchange not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, postArc, postArcJ))
            print(solution[routeJ]['Trips'])

        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated exchange move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Trips'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Trips'])
            print(solution[routeJ]['Trips'])
                        
        if errorsFound:
            print(solution)
            print(moveInfo)
            raise NameError('Errors found with move to solution above, please see comments above solution.')   

    def _testFlipMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        
        if moveType.find('flip') == -1: 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (relocate).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, tripI, removePos) = solutionMapping[arcI]

        if moveType.find('excPostIF') != -1:
            preArc = solution[routeI]['Trips'][tripI - 1][-2]
            arc = solution[routeI]['Trips'][tripI][removePos]
            postArc = solution[routeI]['Trips'][tripI][removePos + 1]
            actualMoveCostsI = self._if_cost[preArc][arcJ] + self._d[arcJ][postArc]  - (self._if_cost[preArc][arc] + self._d[arc][postArc])
        elif moveType.find('excPreIF') != -1:
            preArc = solution[routeI]['Trips'][tripI][removePos - 1]
            arc = solution[routeI]['Trips'][tripI][removePos]
            if tripI == len(solution[routeI]['Trips']) - 1:
                postArc = solution[routeI]['Trips'][tripI][removePos + 2]
            else:
                postArc = solution[routeI]['Trips'][tripI + 1][1]    
            actualMoveCostsI = self._d[preArc][arcJ] + self._if_cost[arcJ][postArc]  - (self._d[preArc][arc] + self._if_cost[arc][postArc])
        else:
            preArc = solution[routeI]['Trips'][tripI][removePos - 1]
            arc = solution[routeI]['Trips'][tripI][removePos]
            postArc = solution[routeI]['Trips'][tripI][removePos + 1]
            actualMoveCostsI = self._d[preArc][arcJ] + self._d[arcJ][postArc]  - (self._d[preArc][arc] + self._d[arc][postArc])        
        
        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to exchange not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print(solution[routeI]['Trips'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before exchange arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Trips'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after exchange arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Trips'])

        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated exchange move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Trips'])
            
        if actualMoveCostsI != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, 0, relocateCost))
            print(solution[routeI]['Trips'])
                        
        if errorsFound:
            print(solution)
            print(moveInfo)
            raise NameError('Errors found with move to solution above, please see comments above solution.')   

    def _testRelocateMoveEndRoute(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        
        if moveType != 'relocateBeforeDummy': 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (relocateBeforeDummy).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, tripI, removePos) = solutionMapping[arcI]

        preArc = solution[routeI]['Trips'][tripI][removePos - 1]
        arc = solution[routeI]['Trips'][tripI][removePos]
        postArc = solution[routeI]['Trips'][tripI][removePos + 1]
        actualMoveCostsI = self._d[preArc][postArc] - (self._d[preArc][arc] + self._d[arc][postArc])

        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to remove not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print(solution[routeI]['Trips'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Trips'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Trips'])

        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated remove move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Trips'])
            
        (routeJ, tripJ, insertPos) = solutionMapping[preArcJ]
        preArc = solution[routeJ]['Trips'][tripJ][insertPos]
        arc = solution[routeJ]['Trips'][tripJ][insertPos + 1]
        actuaMoveCostsJ = self._d[preArc][arcI] + self._d[arcI][arc] - self._d[preArc][arc]

        if arcJ != arc:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print(solution[routeJ]['Trips'])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print(solution[routeJ]['Trips'])

        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated insert move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Trips'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Trips'])
            print(solution[routeJ]['Trips'])
             
        if errorsFound:
            print(solution)
            print(moveInfo)
            raise NameError('Errors found with move to solution above, please see comments above solution.')   

    def _testCrossMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        
        if moveType.find('cross') == -1: 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (cross).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, tripI, removePos1) = solutionMapping[arcI]
        (routeJ, tripJ, removePos2) = solutionMapping[arcJ]
        
        if moveType.find('_1crossPostIF') != -1:
            preArc1 = solution[routeI]['Trips'][tripI - 1][-2]
        else:
            preArc1 = solution[routeI]['Trips'][tripI][removePos1 - 1]
        arc1 = solution[routeI]['Trips'][tripI][removePos1]
 
        if arcI != arc1 and self._inv[arcI] != arc1:
            errorsFound = True
            print('ERROR: Arc to cross not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc1, arcI))
            print(solution[routeI]['Trips'])            
        
        if preArc1 != preArcI:
            errorsFound = True
            print('ERROR: Arc now before cross arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc1, preArcI))
            print(solution[routeI]['Trips'])
        
        if moveType.find('_2crossPostIF') != -1:
            preArc2 = solution[routeJ]['Trips'][tripJ - 1][-2]
        else:
            preArc2 = solution[routeJ]['Trips'][tripJ][removePos2 - 1]
        arc2 = solution[routeJ]['Trips'][tripJ][removePos2]

        if arcJ != arc2:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc2, arcJ))
            print(solution[routeI]['Trips'])  
 
        if preArc2 != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc2, preArcJ))
            print(solution[routeJ]['Trips'])
        
        if moveType.find('_1crossPostIF') != -1:
            actualMoveCostsI = self._if_cost[preArc1][arc2] - self._if_cost[preArc1][arc1]
        else:
            actualMoveCostsI = self._d[preArc1][arc2] - self._d[preArc1][arc1]
        
        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated cross move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Trips'])
        
        if moveType.find('_2crossPostIF') != -1:
            actuaMoveCostsJ = self._if_cost[preArc2][arc1] - self._if_cost[preArc2][arc2]
        else:
            actuaMoveCostsJ = self._d[preArc2][arc1] - self._d[preArc2][arc2]
      
        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated cross move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Trips'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Trips'])
            print(solution[routeJ]['Trips'])
            
        if errorsFound:
            print(solution)
            print(moveInfo, routeI, tripI, removePos1, routeJ, tripJ, removePos2)
            print(solution[routeI]['Trips'][tripI])
            print(solution[routeJ]['Trips'][tripJ])
            raise NameError('Errors found with move to solution above, please see comments above solution.') 
        
    def _testCrossAtDummyMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        
        if moveType != 'crossAtDummy': 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (crossAtDummy).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, removePos1) = solutionMapping[arcI]
        (routeJ, removePos2) = solutionMapping[preArcJ]
        removePos2 += 1

        preArc1 = solution[routeI]['Route'][removePos1 - 1]
        arc1 = solution[routeI]['Route'][removePos1]
 
        if arcI != arc1 and self._inv[arcI] != arc1:
            errorsFound = True
            print('ERROR: Arc to cross not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc1, arcI))
            print(solution[routeI]['Route'])            
        
        if preArc1 != preArcI:
            errorsFound = True
            print('ERROR: Arc now before cross arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc1, preArcI))
            print(solution[routeI]['Route'])
 
        preArc2 = solution[routeJ]['Route'][removePos2 - 1]
        arc2 = solution[routeJ]['Route'][removePos2]

        if arcJ != arc2:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc2, arcJ))
            print(solution[routeI]['Route'])  
 
        if preArc2 != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc2, preArcJ))
            print(solution[routeJ]['Route'])
            
        actualMoveCostsI = self._d[preArc1][arc2] - self._d[preArc1][arc1]
        
        if removePos1 == 1:
            actualMoveCostsI -= self._info.dumpCost
 
        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated dummy cross move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Route'])
            
        actuaMoveCostsJ = self._d[preArc2][arc1] - self._d[preArc2][arc2]
      
        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated dummy cross move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Route'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Route'])
            print(solution[routeJ]['Route'])
            
        if errorsFound:
            print(solution)
            print(moveInfo, routeI, removePos1, routeJ, removePos2)
            raise NameError('Errors found with move to solution above, please see comments above solution.') 

def genMCARPTIFcumulativeRoute(info, route):
    _demand = info.demandL
    _servCost = info.serveCostL
    _d = info.d
    _dumpCost = info.dumpCost
    loadsD = [[_demand[arc] for arc in trip] for trip in route]
    costsD = [[_servCost[arc] for arc in trip] for trip in route]
    cumLoad = []
    cumServe = []
    for k, loads in enumerate(loadsD):
        cumLoad.append([loads[0]])
        costs = costsD[k]
        cumServe.append([costs[0]])
        trip = route[k]
        for i in range(1, len(loads)):
            lValue = cumLoad[k][i - 1] + loads[i]
            cumLoad[k].append(lValue)
            sValue = cumServe[k][i - 1] + _d[trip[i - 1]][trip[i]] + costs[i]
            cumServe[k].append(sValue)
        cumServe[k][-1] += _dumpCost
    #cumServe[-1] += _dumpCost
    return(cumLoad, cumServe)

def updateMCARPcumulitiveSolution(info, solution, routeI):
    (solution[routeI]['CumLoad'], solution[routeI]['CumServe']) = genMCARPTIFcumulativeRoute(info, solution[routeI]['Trips'])
    solution[routeI]['CumUpdate'] = True
    return(solution)

def addMCARPcumulativeSolution(info, solution):
    '''
    Generates the cumulative load and cost at an arc position in a route.
    '''
    for i in range(solution['nVehicles']):
        #print(solution[i])
        route = solution[i]['Trips']
        (solution[i]['CumLoad'], solution[i]['CumServe']) = genMCARPTIFcumulativeRoute(info, route)
        solution[i]['CumUpdate'] = True
    return(solution)

def printMove(moveInfo, routeI, tripI, posI, routeJ, tripJ, posJ, tCost, _searchPhase = 'Unknown', extraInfo = ''):
    '''
    Print basic info of relocate move
    '''
    if moveInfo[2].find('relocate') != -1:
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Relocate arc %i (R %i, T %i, P %i) before arc %i (R %i, T %i, P %i) \t %s \t %s'%(tCost, relocateCost, arcI, routeI, tripI, posI, arcJ, routeJ, tripJ, posJ, moveType, _searchPhase))
    
    if moveInfo[2].find('exchange') != -1:
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Exchange arc %i (R %i, T %i, P %i) with arc %i (R %i, T %i, P %i) \t %s \t %s'%(tCost, relocateCost, arcI, routeI, tripI, posI, arcJ, routeJ, tripJ, posJ, moveType, _searchPhase))
    
    if moveInfo[2] == 'doubleRelocate':
        (relocateCost, (arcIa, preArcI, postArcI, arcJ, preArcJ, arcIb), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Double relocate arcs %i and %i (R %i, T %i, P %i) before arc %i (R %i, T %i, P %i) \t %s'%(tCost, relocateCost, arcIa, arcIb, routeI, tripI, posI, arcJ, routeJ, tripJ, posJ, _searchPhase))
    
    if moveInfo[2].find('flip') != -1:
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI)) = moveInfo
        print('Z: %i \t Savings: %i \t Flip arc %i (R %i, T %i, P %i) \t %s \t %s'%(tCost, relocateCost, arcI, routeI, tripI, posI, moveType, _searchPhase))
    
    if moveInfo[2].find('cross') != -1:
        if routeI == routeJ:
            (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
            print('Z: %i \t Savings: %i \t Trip cross arc %i (R %i, T %i, P %i) to end with arc %i (R %i, T %i, P %i) to end \t %s %s \t %s'%(tCost, relocateCost, arcI, routeI, tripI, posI, arcJ, routeJ, tripJ, posJ, moveType, extraInfo, _searchPhase))
        else:
            (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
            print('Z: %i \t Savings: %i \t Route cross arc %i (R %i, T %i, P %i) to end with arc %i (R %i, T %i, P %i) to end \t %s %s \t %s'%(tCost, relocateCost, arcI, routeI, tripI, posI, arcJ, routeJ, tripJ, posJ, moveType, extraInfo, _searchPhase))

class CalcMoveCosts(object):
    '''
    '''
    def __init__(self, info, nnList, cModules = True, autoInvCosts = False):
        self._info = info
        self._MoveCosts = calcMoveCost.CalcMoveCosts(info, cModules = cModules, nnList = nnList)
        self._MoveCosts_MCARPTIF = calcMoveCost.CalcMoveCostsMCARPTIFspecial(info, cModules = cModules, nnList = nnList)
        self._MoveCosts.autoInvCosts = autoInvCosts
        self.autoInvCosts = autoInvCosts
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        #self._info._edgesS = set(self._edgesL)
        
        self._relocateCandidates = set(self._reqArcs)
        self._nArcs = len(info.d)
        self._depot = info.depotnewkey
        self._reqArcs = info.reqArcListActual
        
        self.setInputDefaults()
        
        self.nonAdjacentRestrictionInsert = False
        self.nonAdjacentRestrictionExchange = False
        self.nonAdjacentRestrictionCross = False
        self.nonAdjacentInsertArcs = set()
        self.nonAdjacentExchangeArcs = set()
        
        self.movesToUse = ['flip', 
                           'cross', 
                           'exchange', 
                           'relocate', 
                           'relocatePreIF', 
                           'relocatePostIF']
        
    def setMovesToUse(self, movesToUse = None):
        
        if movesToUse == None:
            movesToUse = ['flip', 
                          'cross', 
                          'exchange', 
                          'relocate', 
                          'relocatePreIF', 
                          'relocatePostIF']
            
        self.movesToUse = movesToUse
        
    def setInputDefaults(self, threshold = None, nnFrac = None):
        if threshold: self.threshold = threshold
        else: self.threshold = 0
        if nnFrac: self.nnFrac = nnFrac
        else:self.nnFrac = None
        self.thresholdUse = self.threshold
        self.nnFracUse = self.nnFrac
        #self._MoveCosts.initiateCmodules()
        self._MoveCosts_MCARPTIF.initiateCmodules_MCARPTIF()
    
    def setInputValues(self, threshold = None, nnFrac = None):
        if threshold: self.thresholdUse = threshold
        else: self.thresholdUse = self.threshold
        if nnFrac: self.nnFracUse = nnFrac
        else:self.nnFracUse = self.nnFrac
    
    def freeInputValues(self):
        #self._MoveCosts.freeCmodules()
        self._MoveCosts_MCARPTIF.freeCmodules_MCARPTIF()
    
    def setSolution(self, solution):
        self._solution = solution
        (giantRoute, 
         self._solutionArcs, 
         self._specialArcs, 
         self._normalArcs, 
         self._normalArcsF, 
         self._dummyDepotArcPositions, 
         self._dummyIFArcPositions) = self._genMCARPTIFgiantRouteMapping(solution)
        (self._beginRouteArcs, 
         self._beginRouteArcsF, 
         self._beginTripArcs, 
         self._beginTripArcsF, 
         self._endRouteArcs, 
         self._endRouteArcsF, 
         self._endTripArcs, 
         self._endTripArcsF,
         self.singleRouteArcs, 
         self.singleRouteArcsF, 
         self.singleTripArcs, 
         self.singleTripArcsF, 
         self.verySpecialArcs) = self._specialArcs
        self._MoveCosts_MCARPTIF.setRoute_MCARPTIF(giantRoute)
        self._setNonAdjacentArcs()
        
    def freeSolution(self):
        self._MoveCosts_MCARPTIF.freeRoute_MCARPTIF()
        
    def terminateSearch(self):
        self.freeInputValues()
        self.freeSolution
        
    def _genMCARPTIFgiantRouteMapping(self, solution):
        '''
        Takes an initial solution and generates a giant route with the necessary giant route arc position mapping. 
        '''
        solutionArcs = set()
        giantRoute = [self._depot] # Giant route starts with depot.        
        dummyDepotArcPositions = [0]
        dummyIFArcPositions = []
        
        endTripArcs = set()
        endRouteArcs = set()
        beginTripArcs = set()
        beginRouteArcs = set()
        
        endTripArcsF = set()
        endRouteArcsF = set()
        beginTripArcsF = set()
        beginRouteArcsF = set()
        
        normalArcs = set()
        normalArcsF = set()
        
        k = 0
        for i in range(solution['nVehicles']):
            nSubtrips = len(solution[i]['Trips'])
            for j in range(nSubtrips):
                subtrip = solution[i]['Trips'][j]
                nArcs = len(subtrip)
                for n, arc in enumerate(subtrip): # Each route consists of a start and end depot visit, with only one needed in the giant route.
                    
                    if n == 0: continue
                    
                    k += 1
                    
                    normalPosition = True
                    if j == 0 and n == 1:
                        beginRouteArcs.add(arc)
                        beginRouteArcsF.add(arc)
                        if arc in self._edgesS: beginRouteArcsF.add(self._inv[arc])
                        normalPosition = False
                    if j > 0 and n == 1:
                        beginTripArcs.add(arc)
                        beginTripArcsF.add(arc)
                        if arc in self._edgesS: beginTripArcsF.add(self._inv[arc])
                        normalPosition = False   
                    if j == nSubtrips - 1 and n >= len(subtrip) - 3: 
                        normalPosition = False 
                        if n == len(subtrip) - 3:
                            endRouteArcs.add(arc)
                            endRouteArcsF.add(arc)
                            if arc in self._edgesS: endRouteArcsF.add(self._inv[arc])
                    if j < nSubtrips - 1 and n >= len(subtrip) - 2:
                        normalPosition = False 
                        if n == len(subtrip) - 2:
                            endTripArcs.add(arc)
                            endTripArcsF.add(arc)
                            if arc in self._edgesS: endTripArcsF.add(self._inv[arc])
                                          
                    giantRoute.append(arc)

                    if j == nSubtrips - 1 and n == nArcs - 2:
                        dummyIFArcPositions.append(k)
                    elif j == nSubtrips - 1 and n == nArcs - 1:
                        dummyDepotArcPositions.append(k)
                    elif n == nArcs - 1:
                        dummyIFArcPositions.append(k)
                    else:
                        solutionArcs.add(arc)
                        if normalPosition == True:
                            normalArcs.add(arc)
                            normalArcsF.add(arc)
                            if arc in self._edgesS: normalArcsF.add(self._inv[arc])
                            
        singleRouteArcs = beginRouteArcs.intersection(endRouteArcs)
        singleTripArcs = (beginRouteArcs.union(beginTripArcs)).intersection(endRouteArcs.union(endTripArcs))
        singleTripArcs = singleTripArcs.difference(singleRouteArcs)
        
        singleRouteArcsF = singleRouteArcs.copy()
        for arc in singleRouteArcs:
            if arc in self._edgesS:
                singleRouteArcsF.add(self._inv[arc])
        
        singleTripArcsF = singleTripArcs.copy()
        for arc in singleTripArcs:
            if arc in self._edgesS:
                singleTripArcsF.add(self._inv[arc])
        
        verySpecialArcs = singleRouteArcsF.union(singleTripArcsF).union(singleRouteArcsF)
        
        specialArcs = (beginRouteArcs, beginRouteArcsF, beginTripArcs, beginTripArcsF, endRouteArcs, endRouteArcsF, endTripArcs, endTripArcsF, 
                       singleRouteArcs, singleRouteArcsF, 
                       singleTripArcs, singleTripArcsF, verySpecialArcs)
        return(giantRoute, solutionArcs, specialArcs, normalArcs, normalArcsF, dummyDepotArcPositions, dummyIFArcPositions)

    def calcRelocatePreIFMoves(self, relocateCandidates = None, insertCandidates = None, dummyArcPositions = None):

        savings = []
        if 'relocatePreIF' in self.movesToUse:

            if relocateCandidates == None:
                relocateCandidates = self._relocateCandidates.difference(self.verySpecialArcs)
            
            if insertCandidates == None: 
                insertCandidates = self._endRouteArcs.union(self._endTripArcs).union(self.singleTripArcs).union(self.singleRouteArcs)
                
            if self.nonAdjacentRestrictionInsert:
                insertCandidates = insertCandidates.intersection(self.nonAdjacentInsertArcs)
            
            savings += self._MoveCosts_MCARPTIF.relocateMovesPreIF(relocateCandidates, insertCandidates, threshold = self.thresholdUse, nNearest = self.nnFracUse)

        return(savings) 

    def calcRelocatePostIFMoves(self, relocateCandidates = None, insertCandidates = None, dummyArcPositions = None):

        savings = []
        if 'relocatePostIF' in self.movesToUse:

            if relocateCandidates == None:
                relocateCandidates = self._relocateCandidates.difference(self.verySpecialArcs)
            
            if insertCandidates == None: 
                insertCandidates = self._beginTripArcs
                
            if self.nonAdjacentRestrictionInsert:
                insertCandidates = insertCandidates.intersection(self.nonAdjacentInsertArcs.difference(self.verySpecialArcs))
            
            savings += self._MoveCosts_MCARPTIF.relocateMovesPostIF(relocateCandidates, insertCandidates, threshold = self.thresholdUse, nNearest = self.nnFracUse)

        return(savings) 
    
    def calcRelocateMoves(self, relocateCandidates = None, insertCandidates = None, dummyArcPositions = None):

        savings = []
        if 'relocate' in self.movesToUse:

            if relocateCandidates == None:
                relocateCandidates = self._relocateCandidates.difference(self.verySpecialArcs)
            
            if insertCandidates == None: 
                insertCandidates = self._normalArcs.union(self._endRouteArcs).union(self._endTripArcs).union(self._beginRouteArcs).difference(self.verySpecialArcs)
                
            if self.nonAdjacentRestrictionInsert:
                insertCandidates = insertCandidates.intersection(self.nonAdjacentInsertArcs)
            
            savings += self._MoveCosts_MCARPTIF.relocateMovesMCARPTIF(relocateCandidates, insertCandidates, threshold = self.thresholdUse, nNearest = self.nnFracUse)

        return(savings)  

    def calcDoubleRelocateMoves(self, relocateCandidates = None, insertCandidates = None, dummyArcPositions = None):
        
        savings = []
        if 'doubleRelocate' in self.movesToUse:
            
            if relocateCandidates == None:
                #if not self.autoInvCosts: 
                #    relocateCandidates = self._relocateCandidates
                #else:
                relocateCandidates = self._solutionArcs.difference(self._endTripArcs).difference(self._endRouteArcs)
            
            if insertCandidates == None: 
                insertCandidates = self._solutionArcs
    
            if self.nonAdjacentRestrictionInsert:
                insertCandidates = insertCandidates.intersection(self.nonAdjacentInsertArcs)
                
            savings += self._MoveCosts.doubleRelocateMoves(relocateCandidates, insertCandidates, threshold = self.thresholdUse, nNearest = self.nnFracUse)

        return(savings) 

    def calcExchangeMoves(self, exchangeCandidates1 = None, exchangeCandidates2 = None):
    
        savings = []
        if 'exchange' in self.movesToUse:

            if exchangeCandidates1 == None: 
                exchangeCandidates1 = self._relocateCandidates.difference(self.verySpecialArcs)

            if exchangeCandidates2 == None: 
                exchangeCandidates2 = self._relocateCandidates.difference(self.verySpecialArcs)

            if self.nonAdjacentRestrictionExchange:
                exchangeCandidates1 = exchangeCandidates1.intersection(self.nonAdjacentExchangeArcs)
                exchangeCandidates2 = exchangeCandidates2.intersection(self.nonAdjacentExchangeArcs)
            
            savings += self._MoveCosts_MCARPTIF.exchangeMovesMCARPTIF(exchangeCandidates1, exchangeCandidates2, threshold = self.thresholdUse, nNearest = self.nnFracUse)
        
        return(savings)
    
    def calcCrossMoves(self, crossCandidates1 = None, crossCandidates2 = None):
        
        savings = []
        if 'cross' in self.movesToUse:

            if crossCandidates1 == None: 
                crossCandidates1 = self._solutionArcs.difference(self.verySpecialArcs).difference(self._beginTripArcs)
                
            if crossCandidates2 == None: 
                crossCandidates2 = self._solutionArcs.difference(self.verySpecialArcs).difference(self._beginTripArcs)

            if self.nonAdjacentRestrictionCross:
                crossCandidates1 = crossCandidates1.intersection(self.nonAdjacentInsertArcs)
                crossCandidates2 = crossCandidates2.intersection(self.nonAdjacentInsertArcs)

            savings += self._MoveCosts_MCARPTIF.crossMovesMCARPTIF(crossCandidates1, crossCandidates2, threshold = self.thresholdUse, nNearest = self.nnFracUse)
            
        return(savings) 
    
    def calcFlipMoves(self, flipCandidates = None):

        savings = []
        if 'flip' in self.movesToUse:

            if flipCandidates == None: 
                flipCandidates = self._solutionArcs.intersection(self._edgesS).difference(self.verySpecialArcs)
    
            savings += self._MoveCosts_MCARPTIF.flipMovesMCARPTIF(flipCandidates, threshold = self.thresholdUse)
            
        return(savings)

    def calcAllPossibleMoveCosts(self):
        '''
        Calculate the cost of neighbourhood moves to current solution.
        
        movesToUse = ['relocate',
                      'exchange',
                      'cross',
                      'relocateBeforeDummy',
                      'crossAtDummy',
                      'doubleCross',
                      'flip',
                      'doubleRelocate']
        '''

        savings = []
        savings += self.calcRelocateMoves()
        savings += self.calcDoubleRelocateMoves()
        savings += self.calcExchangeMoves()        
        savings += self.calcCrossMoves()
        savings += self.calcFlipMoves()
        savings += self.calcRelocatePreIFMoves()
        savings += self.calcRelocatePostIFMoves()
        return(savings)

    def calcSingleRouteCrossCosts(self, routeSavings, solution):
        '''
        Calculate the cost of neighbourhood moves to current solution.
        '''
        
        savings = []
        for route in routeSavings:
            thresholdUse = routeSavings[route][0][0]
            routeArcs = set(solution[route]['Route'][1:-1])
            solutionArcs = set(routeArcs)
            
            savings += self._MoveCosts.crossMoves(solutionArcs, solutionArcs, threshold = -thresholdUse, nNearest = self.nnFracUse)
        return(savings)
    
    def calcSingleRouteOutCosts(self, routeSavings, solution, relocateCandidates = None, solutionArcs = None, dummyArcPositions = None):
        '''
        Calculate the cost of neighbourhood moves to current solution.
        '''
        savings = []
        
        if relocateCandidates == None: 
            if not self.autoInvCosts: 
                relocateCandidates = self._relocateCandidates
            else:
                relocateCandidates = self._solutionArcs
        
        if solutionArcs == None: 
            solutionArcs = self._solutionArcs
            
        if dummyArcPositions == None: 
            dummyArcPositions = self._dummyArcPositions
        
        for route in routeSavings:

            thresholdUse = -routeSavings[route][0][0]
            
            routeArcs = solution[route]['Route'][1:-1]
            
            routeCandidates = routeArcs
            routeCandidates += [self._inv[arc] for arc in routeArcs if arc in self._edgesS]
            routeCandidates = set(routeCandidates)
            relocateCandidates = routeCandidates.intersection(relocateCandidates)
            relocateToCandidates = solutionArcs.difference(relocateCandidates)
            
            dummyArcPositionsTemp = dummyArcPositions[:]
            
            del dummyArcPositionsTemp[route + 1]
            
            savings += self._MoveCosts.relocateMoves(relocateCandidates, relocateToCandidates, threshold = thresholdUse, nNearest = self.nnFracUse)
            savings += self._MoveCosts.relocateEndRouteMoves(relocateCandidates, dummyArcPositionsTemp, threshold = thresholdUse, nNearest = self.nnFracUse) 
        
        return(savings)

        
    def _setNonAdjacentArcs(self):
        
        if self.nonAdjacentRestrictionCross or self.nonAdjacentRestrictionExchange or self.nonAdjacentRestrictionInsert:
        
            nonAdjacentInsertArcs = set()
            nonAdjacentExchangeArcs = set()
            for i in range(self._solution['nVehicles']):
                iRoute = self._solution[i]['Route']
                nArcs = len(iRoute)
                for iPos in range(1,nArcs - 1):
                    preArc = iRoute[iPos - 1]
                    arc = iRoute[iPos]
                    postArc = iRoute[iPos + 1]
                    if self._info.d[preArc][arc] != 0:
                        nonAdjacentInsertArcs.add(arc)
                        nonAdjacentExchangeArcs.add(arc)
                    elif self._info.d[arc][postArc] != 0:
                        nonAdjacentExchangeArcs.add(arc)
                            
            self.nonAdjacentInsertArcs = nonAdjacentInsertArcs
            self.nonAdjacentExchangeArcs = nonAdjacentExchangeArcs

class MovesFeasibleMCARPTIF(object):
    '''
    Check if moves are feasible
    '''
    def __init__(self, info):
        '''
        '''
        self.info = info
        self._demand = info.demandL
        self._servCost = info.serveCostL
        self._dumpCost = info.dumpCost
        self._d = info.d
        self._capacity = info.capacity
        self._maxTrip = info.maxTrip
        self.infeasibleLoadMoves = []
        self.infeasibleCostMoves = []
        self.doubleCrossMove = []
        self.exceedThresholdRemoveInsert = []
        self.exceedThresholdDoubleCross = []
        self.threshold = 0
        self._if_cost = info.if_cost_np
        self._if_arc = info.if_arc_np
        
    def restartFeasibility(self):
        self.infeasibleLoadMoves = []
        self.infeasibleCostMoves = []
        self.doubleCrossMove = []
        self.exceedThresholdRemoveInsert = []
        self.exceedThresholdDoubleCross = [] 
    
    def _relocateFeasibility(self, moveInfo, solutionMapping, solution, loadCheck = False):
        '''
        Determines if a relocate move is feasible. The move is feasible if the arc is relocated to the same route or if its relocate-to
        route has sufficient capacity.
        '''
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        (netCostRouteI, netCostRouteJ) = routeCosts
        
        if moveType.find('relocate') == -1: 
            raise NameError('Incorrect feasibility check (%s) for this kind of move (relocate).'%moveType)
        
        (routeI, tripI, posI) = solutionMapping[arcI]
        (routeJ, tripJ, posJ) = solutionMapping[arcJ]
            
        deltaChangeRouteI = 0
        deltaChangeRouteJ = 0
        
        if routeI != routeJ or tripI != tripJ: 
            deltaChangeRouteI = -self._demand[arcI]
            deltaChangeRouteJ = self._demand[arcI]
                                
        excessI = solution[routeI]['TripLoads'][tripI] + deltaChangeRouteI - self._capacity
        excessJ = solution[routeJ]['TripLoads'][tripJ] + deltaChangeRouteJ - self._capacity
        
        moveFeasible = excessI <= 0 and excessJ <= 0
        if not moveFeasible: moveToMake = 'nomoveLoad'
        else: moveToMake = 'feasible' 
        
        if moveFeasible or loadCheck:
        
            delateServiceRouteI = 0
            delateServiceRouteJ = 0
            
            if routeI != routeJ:  
                delateServiceRouteI = -self._servCost[arcI]
                delateServiceRouteJ = self._servCost[arcI]
                excessCostI = solution[routeI]['Cost'] + delateServiceRouteI + netCostRouteI - self._maxTrip
                excessCostJ = solution[routeJ]['Cost'] + delateServiceRouteJ + netCostRouteJ - self._maxTrip
            else:
                excessCostI = excessCostJ = solution[routeI]['Cost'] + moveCost - self._maxTrip
        
            moveFeasible = excessCostI <= 0 and excessCostJ <= 0
            
            if not moveFeasible: moveToMake = 'nomoveCost'
            else: moveToMake = 'feasible'
            
        return(moveToMake, deltaChangeRouteI, deltaChangeRouteJ)

    def _doubleRelocateFeasibility(self, moveInfo, solutionMapping, solution):
        '''
        Determines if a relocate move is feasible. The move is feasible if the arc is relocated to the same route or if its relocate-to
        route has sufficient capacity.
        '''
        (moveCost, (arcIa, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        (netCostRouteI, netCostRouteJ) = routeCosts
                
        arcIb = postArcJ
        
        if moveType != 'doubleRelocate': 
            raise NameError('Incorrect feasibility check (%s) for this kind of move (doubleRelocate).'%moveType)
        
        (routeI, tripI, posI) = solutionMapping[arcIa]
        (routeJ, tripJ, posJ) = solutionMapping[arcJ]
            
        deltaChangeRouteI = 0
        deltaChangeRouteJ = 0
        
        if routeI != routeJ or tripI != tripJ: 
            deltaChangeRouteI = -(self._demand[arcIa] + self._demand[arcIb])
            deltaChangeRouteJ = -deltaChangeRouteI
                                
        excessI = solution[routeI]['TripLoads'][tripI] + deltaChangeRouteI - self._capacity
        excessJ = solution[routeJ]['TripLoads'][tripJ] + deltaChangeRouteJ - self._capacity
        
        moveFeasible = excessI <= 0 and excessJ <= 0
        
        if moveFeasible:
        
            delateServiceRouteI = 0
            delateServiceRouteJ = 0
            
            if routeI != routeJ:  
                delateServiceRouteI = -(self._servCost[arcIa] + self._d[arcIa][arcIb] + self._servCost[arcIb])
                delateServiceRouteJ = -delateServiceRouteI
                excessCostI = solution[routeI]['Cost'] + delateServiceRouteI + netCostRouteI - self._maxTrip
                excessCostJ = solution[routeJ]['Cost'] + delateServiceRouteJ + netCostRouteJ - self._maxTrip
            else:
                excessCostI = excessCostJ = solution[routeI]['Cost'] + moveCost - self._maxTrip
        
            moveFeasible = excessCostI <= 0 and excessCostJ <= 0
        
        return(moveFeasible, deltaChangeRouteI, deltaChangeRouteJ)

    def _exchangeFeasibility(self, moveInfo, solutionMapping, solution, loadCheck = False):
        '''
        Determines if a exchange move is feasible. The move is feasible if the new arc per route can be accomodated
        instead of the old one without exceeds available capacities.
        '''
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        if moveType.find('exchange') == -1: raise NameError('Incorrect feasibility check (%s) for this kind of move (exchange).'%moveType)
        (netCostRouteI, netCostRouteJ) = routeCosts
        
        
        (routeI, tripI, posI) = solutionMapping[arcI]
        (routeJ, tripJ, posI) = solutionMapping[arcJ]
        
        deltaChangeRouteI = 0
        deltaChangeRouteJ = 0
        
        if routeI != routeJ or tripI != tripJ: 
            deltaChangeRouteI = self._demand[arcJ] - self._demand[arcI]
            deltaChangeRouteJ = -deltaChangeRouteI
        
        excessI = solution[routeI]['TripLoads'][tripI] + deltaChangeRouteI - self._capacity
        excessJ = solution[routeJ]['TripLoads'][tripJ] + deltaChangeRouteJ - self._capacity

        moveFeasible = excessI <= 0 and excessJ <= 0
        if not moveFeasible: moveToMake = 'nomoveLoad'
        else:  moveToMake = 'feasible' 

        if moveFeasible or loadCheck:
        
            delateServiceRouteI = 0
            delateServiceRouteJ = 0
            
            if routeI != routeJ:  
                delateServiceRouteI = self._servCost[arcJ] - self._servCost[arcI]
                delateServiceRouteJ = -delateServiceRouteI
                excessCostI = solution[routeI]['Cost'] + delateServiceRouteI + netCostRouteI - self._maxTrip
                excessCostJ = solution[routeJ]['Cost'] + delateServiceRouteJ + netCostRouteJ - self._maxTrip
            else:
                excessCostI = excessCostJ = solution[routeI]['Cost'] + moveCost - self._maxTrip
        
            moveFeasible = excessCostI <= 0 and excessCostJ <= 0

            if not moveFeasible: moveToMake = 'nomoveCost'
            else: moveToMake = 'feasible'

        return(moveToMake, deltaChangeRouteI, deltaChangeRouteJ)
    
    def _flipFeasibility(self, moveInfo, solutionMapping, solution):
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        (moveCostI, moveCostJ) = routeCosts
        if moveType.find('flip') == -1: raise NameError('Incorrect feasibility check (%s) for this kind of move (flip).'%moveType)
        (routeI, tripI, posI) = solutionMapping[arcI]
        excessCostI = solution[routeI]['Cost'] + moveCostI - self._maxTrip
        moveFeasible = excessCostI <= 0
        if moveFeasible: 
            moveToMake = 'feasible'
        else:
            moveToMake = 'nomoveCost'
        
        return(moveToMake, 0, 0, solution)
    
    def _testCrossMove(self, moveInfo, solutionMapping, solution):
        
        solutionTemp = deepcopy(solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        (moveCostI, moveCostJ) = routeCosts
        
        (routeI, tripI, arcPos1) = solutionMapping[arcI]
        (routeJ, tripJ, arcPos2) = solutionMapping[arcJ]       
        
        if tripI == len(solutionTemp[routeI]['Trips']) - 1: 
            iEnd = -2
            endAddI = [solutionTemp[routeI]['Trips'][tripI][-2], solutionTemp[routeI]['Trips'][tripI][-1]]
        else: 
            iEnd = -1
            endAddI = [solutionTemp[routeI]['Trips'][tripI][-1]]
        
        if tripJ == len(solutionTemp[routeJ]['Trips']) - 1: 
            jEnd = -2
            endAddJ = [solutionTemp[routeJ]['Trips'][tripJ][-2], solutionTemp[routeJ]['Trips'][tripJ][-1]]
        else: 
            jEnd = -1
            endAddJ = [solutionTemp[routeJ]['Trips'][tripJ][-1]]

        if solutionTemp[routeI]['Trips'][tripI][iEnd] == solutionTemp[routeJ]['Trips'][tripJ][jEnd]:
            tripMove = 'TripMove'
            seqI1 = solutionTemp[routeI]['Trips'][tripI][:arcPos1]
            seqI2 = solutionTemp[routeI]['Trips'][tripI][arcPos1:iEnd]
            seqJ1 = solutionTemp[routeJ]['Trips'][tripJ][:arcPos2]
            seqJ2 = solutionTemp[routeJ]['Trips'][tripJ][arcPos2:jEnd]
                        
            solutionTemp[routeI]['Trips'][tripI] =  seqI1 + seqJ2 + endAddI
            solutionTemp[routeJ]['Trips'][tripJ] =  seqJ1 + seqI2 + endAddJ
        
        elif routeI != routeJ:
            tripMove = 'RouteMove'
            seqI0 = solutionTemp[routeI]['Trips'][:tripI]
            seqI1 = solutionTemp[routeI]['Trips'][tripI][:arcPos1]
            seqI2 = solutionTemp[routeI]['Trips'][tripI][arcPos1:]
            seqI3 = solutionTemp[routeI]['Trips'][tripI+1:]         
            
            seqJ0 = solutionTemp[routeJ]['Trips'][:tripJ]
            seqJ1 = solutionTemp[routeJ]['Trips'][tripJ][:arcPos2]
            seqJ2 = solutionTemp[routeJ]['Trips'][tripJ][arcPos2:]
            seqJ3 = solutionTemp[routeJ]['Trips'][tripJ+1:]  
            
            solutionTemp[routeI]['Trips'] = seqI0 + [seqI1 + seqJ2] + seqJ3   
            solutionTemp[routeJ]['Trips'] = seqJ0 + [seqJ1 + seqI2] + seqI3

        if moveType.find('_1crossPostIF') != -1:
            bestIFI = self._if_arc[preArcI][arcJ]
            solutionTemp[routeI]['Trips'][tripI-1][-1] = bestIFI
            solutionTemp[routeI]['Trips'][tripI][0] = bestIFI
            #print(routeI, bestIFI)
    
        if moveType.find('_2crossPostIF') != -1:
            bestIFJ = self._if_arc[preArcJ][arcI]
            solutionTemp[routeJ]['Trips'][tripJ-1][-1] = bestIFJ
            solutionTemp[routeJ]['Trips'][tripJ][0] = bestIFJ    
            #print(routeJ, bestIFJ)
            
        c1 = 0
        for tripIact in solutionTemp[routeI]['Trips']:
            for q, a in enumerate(tripIact[:-1]):
                c1 += self._d[tripIact[q]][tripIact[q+1]] + self._servCost[a]
            c1 += self._dumpCost
        if c1 > self._maxTrip: return(False)
    
        if routeI != routeJ:
            c1 = 0
            for tripIact in solutionTemp[routeJ]['Trips']:
                for q, a in enumerate(tripIact[:-1]):
                    c1 += self._d[tripIact[q]][tripIact[q+1]] + self._servCost[a]
                c1 += self._dumpCost
            if c1 > self._maxTrip: return(False)
        return(True)

    def _crossFeasibility(self, moveInfo, solutionMapping, solution):
        #cum load per trip, so have to check if routes are different sum of remaining trip costs have to be added. Last entry in each.
        #if routes are the same and last arcs are the same only load has to be checked :)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        (moveCostI, moveCostJ) = routeCosts
        
        if moveType.find('cross') == 1: raise NameError('Incorrect feasibility check (%s) for this kind of move (cross).'%moveType)
        (routeI, tripI, posI) = solutionMapping[arcI]
        (routeJ, tripJ, posJ) = solutionMapping[arcJ]
        
        if tripI == len(solution[routeI]['Trips']) - 1: tripIend = -2
        else: tripIend = -1
        
        if tripJ == len(solution[routeJ]['Trips']) - 1: tripJend = -2
        else: tripJend = -1
        
        moveFeasible = False
        deltaChangeRouteI = 0
        deltaChangeRouteJ = 0
        sameRoute = False

        if tripI == 0 and posI == 1 and tripJ == 0 and posJ == 1:
            moveToMake = 'nomoveNoMove'
            return(moveToMake, deltaChangeRouteI, deltaChangeRouteJ, solution)
               
        if routeI == routeJ and tripI == tripJ:
            moveFeasible = None
            deltaChangeRouteI = 0
            deltaChangeRouteJ = 0
            moveToMake = 'nomoveSameRouteSameTrip'
        elif solution[routeI]['Trips'][tripI][tripIend] == solution[routeJ]['Trips'][tripJ][tripJend] and tripIend == tripJend:
            moveFeasible = True
            tripCross = True
        elif routeI == routeJ:
            moveToMake = 'nomoveSameRouteTripEndsDifferent'
            moveFeasible = None
        elif tripIend == tripJend:
            moveFeasible = True
            tripCross = False     
        else:
            moveFeasible = False    
            moveToMake = 'nomoveMidTripVsEndTrip'   
        
        if moveFeasible:
            #print(solution[routeJ])
            if not solution[routeI]['CumUpdate']:
                solution = updateMCARPcumulitiveSolution(self.info, solution, routeI)
            if not solution[routeJ]['CumUpdate']:
                solution = updateMCARPcumulitiveSolution(self.info, solution, routeJ)
            
            secIloadStart = solution[routeI]['CumLoad'][tripI][posI - 1]
            secIloadEnd  = solution[routeI]['CumLoad'][tripI][-1] - secIloadStart
            secJloadStart = solution[routeJ]['CumLoad'][tripJ][posJ - 1]
            secJloadEnd = solution[routeJ]['CumLoad'][tripJ][-1] - secJloadStart
            
            deltaChangeRouteI = secJloadEnd - secIloadEnd
            deltaChangeRouteJ = secIloadEnd - secJloadEnd
            
            excessI = solution[routeI]['TripLoads'][tripI] + deltaChangeRouteI - self._capacity
            excessJ = solution[routeJ]['TripLoads'][tripJ] + deltaChangeRouteJ - self._capacity
            
            moveFeasible = excessI <= 0 and excessJ <= 0

            moveFeasible = excessI <= 0 and excessJ <= 0
            if not moveFeasible: moveToMake = 'nomoveLoad'

        if moveFeasible:
            
            tripI_minOld = self._d[preArcI][arcI] 
            tripI_minNew = self._d[preArcI][arcJ] 
            
            tripJ_minOld = self._d[preArcJ][arcI] 
            tripJ_minNew = self._d[preArcI][arcJ] 
                         
            if tripCross:
                secICostStart = solution[routeI]['CumServe'][tripI][posI - 1]
                secICostEnd  = solution[routeI]['CumServe'][tripI][-1] - secICostStart - tripI_minOld 
                secJCostStart = solution[routeJ]['CumServe'][tripJ][posJ - 1]
                secJCostEnd = solution[routeJ]['CumServe'][tripJ][-1] - secJCostStart - tripJ_minOld                   
            else:
                secICostStart = sum([s[-1] for s in solution[routeI]['CumServe'][:tripI]]) + solution[routeI]['CumServe'][tripI][posI - 1]
                secICostEnd  = solution[routeI]['Cost'] - secICostStart - tripI_minOld
                secJCostStart = sum([s[-1] for s in solution[routeJ]['CumServe'][:tripJ]]) + solution[routeJ]['CumServe'][tripJ][posJ - 1] 
                secJCostEnd = solution[routeJ]['Cost'] - secJCostStart - tripJ_minOld 
            
            deltaCostChangeRouteI = secJCostEnd - secICostEnd + tripJ_minNew
            deltaCostChangeRouteJ = secICostEnd - secJCostEnd + tripI_minNew

#             if routeI == 0 and tripI ==2 and routeJ == 5 and tripJ == 2:     
#                 r = solution[routeI]['Trips'][tripI]
#                 
#                 for rI, r in enumerate(solution[routeI]['Trips']):
#                     c = [0]  
#                     s = [0]  
#                     dead = [0]          
#                     for ai, a in enumerate(r[1:]):
#                         rPos = ai + 1
#                         cCost = c[rPos - 1] + self._d[r[rPos - 1]][r[rPos]] + self._servCost[a]
#                         s.append(s[rPos - 1] + self._servCost[a])
#                         c.append(cCost)
#                         dead.append(dead[ai] + self._d[r[ai]][r[ai + 1]])
#                     c[-1] += self._dumpCost
#                     print('tC', rI, c)
#                     print('serve', rI, s)
#                     print('dead', rI, dead)
#                 print(solution[routeI]['Cost'], moveCostI, self._d[373][423] - self._d[373][815], solution[routeI]['CumServe'][tripI])
#                 
#                 r = solution[routeJ]['Trips'][tripJ]
#                 
#                 for rJ, r in enumerate(solution[routeJ]['Trips']):
#                     c2 = [0] 
#                     s2 = [0]   
#                     dead2 = [0]          
#                     for ai, a in enumerate(r[1:]):
#                         c2.append(c2[ai] + self._d[r[ai]][r[ai + 1]] + self._servCost[a])
#                         s2.append(s2[ai] + self._servCost[a])
#                         dead2.append(dead2[ai] + self._d[r[ai]][r[ai + 1]])
#                     c2[-1] += self._dumpCost
#                     print('tC', rJ, c2)
#                     print('serve', rJ, s2)
#                     print('dead', rJ, dead2)
#                 print(solution[routeJ]['Cost'], moveCostJ, self._d[579][815] - self._d[579][423], solution[routeJ]['CumServe'][tripJ])
#                 
            excessCostI = solution[routeI]['Cost'] + deltaCostChangeRouteI - self._maxTrip
            excessCostJ = solution[routeJ]['Cost'] + deltaCostChangeRouteJ - self._maxTrip           
             
            moveFeasible = excessCostI <= 0 and excessCostJ <= 0
            #moveFeasible = self._testCrossMove(moveInfo, solutionMapping, solution)
            if not moveFeasible:
                if tripCross: moveToMake = 'nomoveTripCost'
                else: moveToMake = 'nomoveRouteCost'
            else:
                if tripCross: moveToMake = 'feasibleTrip'
                else: moveToMake = 'feasibleRoute'               

        return(moveToMake, deltaChangeRouteI, deltaChangeRouteJ, solution)

    def _doubleCrossFeasibility(self, moveInfo, solutionMapping, solution):
        '''
        '''
        (costDummy, (moveInfo1, moveInfo2), moveType) = moveInfo
        if moveType != 'doubleCross': raise NameError('Incorrect feasibility check (%s) for this kind of move (doubleCross).'%moveType)
        
        (crossCost1, (arcI1, preArcI1, postArcI1, arcJ1, preArcJ1, postArcJ1), moveType, (routeIcostChange, routeJcostChange)) = moveInfo1
        if moveType.find('cross') == -1: raise NameError('Incorrect feasibility check (%s) for this kind of move (cross).'%moveType)
        (routeI1, tripI1, arcIpos1) = solutionMapping[arcI1]
        (routeJ1, tripJ1, arcIpos2) = solutionMapping[arcJ1]            
        arcIpos1, arcIpos2 = min([arcIpos1, arcIpos2]), max([arcIpos1, arcIpos2])

        (crossCost2, (arcI2, preArcI2, postArcI2, arcJ2, preArcJ2, postArcJ2), moveType, (routeIcostChange, routeJcostChange)) = moveInfo2
        if moveType.find('cross') == -1: NameError('Incorrect feasibility check (%s) for this kind of move (cross).'%moveType)
        (routeI2, tripI2, arcJpos1) = solutionMapping[arcI2]
        (routeJ2, tripJ2, arcJpos2) = solutionMapping[arcJ2]       
        
        if routeI1 != routeJ1 or tripI1 != tripJ1: return('nomove', 0, 0)
        if routeI2 != routeJ2 or tripI2 != tripJ2: return('nomove', 0, 0)
        if routeI1 != routeI2 or tripI1 != tripI2: return('nomove', 0, 0)

        arcJpos1, arcJpos2 = min([arcJpos1, arcJpos2]), max([arcJpos1, arcJpos2])
        
        seq = []
        if arcIpos1 < arcJpos1:
            seq = (arcIpos1, arcJpos1, arcIpos2, arcJpos2)
        else:
            seq = (arcJpos1, arcIpos1, arcJpos2, arcIpos2)
        feasible =  seq[0] + 1 < seq[1] and seq[1] < seq[2] - 1 and seq[2] + 1 < seq[3]
        if feasible: moveToMake = 'feasible'
        else: moveToMake = 'nomove'
        
        return(moveToMake, 0, 0)

    def _returnRouteInfo(self, moveInfo, solutionMapping, solution):
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        (routeI, tripI, posI) = solutionMapping[arcI]
        (routeJ, tripJ, posJ) = solutionMapping[arcJ]
        return(routeI, tripI, routeJ, tripJ)

    def doubleMoveFeasibility(self, moveInfo, solutionMapping, solution):
        '''
        '''
        (costDummy, (moveInfo1, moveInfo2), moveType) = moveInfo
        if moveType != 'comboMove': raise NameError('Incorrect feasibility check (%s) for this kind of move (comboMove).'%moveType)
        #solutionLoads = {i : {'Load' : solution[i]['Load']} for i in range(solution['nVehicles'])}
        solutionLoads = deepcopy(solution)
        
        (routeI1, tripI1, routeJ1, tripJ1) = self._returnRouteInfo(moveInfo1, solutionMapping, solution) 
        
        (feasible1, loadI, loadJ) = self.checkMoveFeasibility(moveInfo1, solutionMapping, solutionLoads, saveMoveInfo = False, loadCheck = True)
        if feasible1.find('feasible') == -1: return('nomove')
            
        solutionLoads[routeI1]['TripLoads'][tripI1] += loadI
        solutionLoads[routeJ1]['TripLoads'][tripJ1] += loadJ

        (routeI2, tripI2, routeJ2, tripJ2) = self._returnRouteInfo(moveInfo2, solutionMapping, solution) 
               
        (feasible2, loadI, loadJ) = self.checkMoveFeasibility(moveInfo2, solutionMapping, solutionLoads, saveMoveInfo = False, loadCheck = False)
        
        solutionLoads[routeI2]['TripLoads'][tripI2] += loadI
        solutionLoads[routeJ2]['TripLoads'][tripJ2] += loadJ
        
        #(feasible1, loadI, loadJ) = self.checkMoveFeasibility(moveInfo1, solutionMapping, solutionLoads, saveMoveInfo = False, loadCheck = False)
        #if feasible1.find('feasible') == -1: return('nomove')
        
        feasible1 = solutionLoads[routeI1]['TripLoads'][tripI1]  <= self._capacity and solutionLoads[routeJ1]['TripLoads'][tripJ1] <= self._capacity
        feasible2 = solutionLoads[routeI2]['TripLoads'][tripI2]  <= self._capacity and solutionLoads[routeJ2]['TripLoads'][tripJ2] <= self._capacity
        
        if feasible1 and feasible2:
            moveMake = 'feasible'
        else:
            moveMake = 'nomove'
            
        return(moveMake)

    def checkMoveFeasibility(self, moveInfo, solutionMapping, solution, saveMoveInfo = True, loadCheck = False):
        '''
        Check if move is feasible.
        '''
        moveType = moveInfo[2]
        self._solutionMapping = solutionMapping
        self._solution = solution
        if moveType.find('relocate') != -1:
            (feasible, loadI, loadJ) = self._relocateFeasibility(moveInfo, solutionMapping, solution, loadCheck)
        if moveType.find('exchange') != -1:
            (feasible, loadI, loadJ) = self._exchangeFeasibility(moveInfo, solutionMapping, solution, loadCheck)
        if moveType.find('cross') != -1:
            (feasible, loadI, loadJ, solution) = self._crossFeasibility(moveInfo, solutionMapping, solution)
        if moveType.find('flip') != -1:
            (feasible, loadI, loadJ, solution) = self._flipFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'doubleCross':
            (feasible, loadI, loadJ) = self._doubleCrossFeasibility(moveInfo, solutionMapping, solution)
            
        if moveType == 'doubleRelocate':
            (feasible, loadI, loadJ) = self._doubleRelocateFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'comboMove':
            (feasible, loadI, loadJ) = self._doubleMoveFeasibility(moveInfo, solutionMapping, solution)
        
        if moveType != 'cross' and saveMoveInfo:
            if feasible == 'nomoveLoad': self.infeasibleLoadMoves.append((moveInfo[0], loadI, loadJ, moveInfo))
            if feasible == 'nomoveCost': self.infeasibleCostMoves.append((moveInfo[0], loadI, loadJ, moveInfo))
            if moveType.find('relocate') != -1 and moveInfo[0] >= self.threshold:
                self.exceedThresholdRemoveInsert.append(moveInfo)
            
        if moveType.find('cross') != -1 and feasible == 'nomoveSameRouteSameTrip' and saveMoveInfo:
            self.doubleCrossMove.append(moveInfo)
            if moveInfo[0] >= self.threshold:
                self.exceedThresholdDoubleCross.append(moveInfo)

        if not saveMoveInfo:
            return(feasible, loadI, loadJ)
        else:
            return(feasible, solution)
    
    
class MakeMovesMCARPTIF(object):
    '''
    Make specific moves for the MCARP
    '''
    
    def __init__(self, info, testMoves = True):
        self.info = info
        self._d = info.d
        self._demand = info.demandL
        self._service = info.serveCostL
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self._depot = info.depotnewkey
        self._if_arc = info.if_arc_np
        self._if_cost = info.if_cost_np
        self._dumpCost = info.dumpCost
        
        self._searchPhase = 'unknown'
        self._testMoves = TestLocalSeach(info)
        self._testAll = testMoves
        self._printEachMove = True
        
    def setSolution(self, solution):
        self.solution = solution
        self.solutionMapping = self._genMCARPTIFsolutionMapping()
    
    def saveSolution(self):
        self.solutionCopy = deepcopy(self.solution)
        
    def restoreSolution(self):
        self.solution = deepcopy(self.solutionCopy)


    def returnSolutionCopy(self):
        return(deepcopy(self.solution))

    def retrieveSolutionCost(self):
        return(self.solution['TotalCost'])
    
    def setSearchPhase(self, searchPhase):
        self._searchPhase = searchPhase

    def _genMCARPTIFsolutionMapping(self):
        '''
        Takes an initial solution and maps all the required arcs to route and inter-route positions.
        '''
        solution = self.solution
        solutionMapping = {} # Mapping of an arc to its position (route and route position) in the solution.
        for i in range(solution['nVehicles']):
            nSubtrips = len(solution[i]['Trips'])
            for j in range(nSubtrips):
                subtrip = solution[i]['Trips'][j]
                for n, arc in enumerate(subtrip): # Each route consists of a start and end depot visit, with only one needed in the giant route.
                    solutionMapping[arc] = (i, j, n) # Since positioning starts at the first arc after the depot, j is increased by one.
                    if arc in self._edgesS: solutionMapping[self._inv[arc]] = (i, j, n) # Position of inverse arc is also captured, thus allowing for arc inversion (should come more into play with windy edges.
        return(solutionMapping)
    
    def _printMove(self, routeI, tripI, posI, routeJ, tripJ, posJ, tCost, extraInfo = ''):
        '''
        Print basic info of relocate move
        '''
        if self._printEachMove:
            printMove(self._moveInfo, routeI, tripI, posI, routeJ, tripJ, posJ, tCost, self._searchPhase, extraInfo)
    
    def _updateSolution(self, routeI, tripI, loadChange, costChange):
        '''
        Update solution with cost and route change
        '''
        self.solution[routeI]['CumUpdate'] = False
        self.solution[routeI]['TripLoads'][tripI] += loadChange
        self.solution[routeI]['Cost'] += costChange
        self.solution['TotalCost'] += costChange

    def _updateCrossSolution(self, routeI):
        '''
        Update solution with cost and route change
        '''
        self.solution = updateMCARPcumulitiveSolution(self.info, self.solution, routeI)
        nTrips = len(self.solution[routeI]['Trips'])
        self.solution[routeI]['TripLoads'] = []
        self.solution[routeI]['Cost'] = 0
        for i in range(nTrips):
            self.solution[routeI]['TripLoads'] += [self.solution[routeI]['CumLoad'][i][-1]]
            self.solution[routeI]['Cost'] += self.solution[routeI]['CumServe'][i][-1]

    def _updateArcPositions(self, routeI, tripI):
        '''
        Update solution positions of arc in a given route.
        '''
        for j, arc in enumerate(self.solution[routeI]['Trips'][tripI][1:-1]): # Note that j will start at zero, not 1
            self.solutionMapping[arc] = (routeI, tripI, j + 1) # Since positioning starts at the first arc after the depot, j is increased by one.
            if arc in self._edgesS: 
                self.solutionMapping[self._inv[arc]] = (routeI, tripI, j + 1)

    def _updateRouteArcPositions(self, routeI):
        '''
        Update solution positions of arc in a given route.
        '''
        for tripI in range(len(self.solution[routeI]['Trips'])):
            for j, arc in enumerate(self.solution[routeI]['Trips'][tripI][1:-1]): # Note that j will start at zero, not 1
                self.solutionMapping[arc] = (routeI, tripI, j + 1) # Since positioning starts at the first arc after the depot, j is increased by one.
                if arc in self._edgesS: 
                    self.solutionMapping[self._inv[arc]] = (routeI, tripI, j + 1)

    def _relocateMove(self):
        '''
        Make a relocate move.
        '''
        if self._testAll: self._testMoves._testRelocateMove(self._moveInfo,  self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, tripI, removePos) =  self.solutionMapping[arcI]
        (routeJ, tripJ, insertPos) =  self.solutionMapping[arcJ]
        
        dRelocate = self._demand[arcI]
        sRelocate = self._service[arcI]

        self._updateSolution(routeI, tripI, -dRelocate, moveCostsI - sRelocate)
        self._updateSolution(routeJ, tripJ, +dRelocate, moveCostsJ + sRelocate)

        if moveType.find('PreArcIF') != -1:
            bestIFarc = self._if_arc[preArcI][postArcI]
            if tripI == len(self.solution[routeI]['Trips']) - 1:
                self.solution[routeI]['Trips'][tripI][-2] = bestIFarc
            else:
                self.solution[routeI]['Trips'][tripI][-1] = bestIFarc
                self.solution[routeI]['Trips'][tripI + 1][0] = bestIFarc
                
        if moveType.find('PostArcIF') != -1:
            bestIFarc = self._if_arc[preArcI][postArcI]
            self.solution[routeI]['Trips'][tripI][0] = bestIFarc
            self.solution[routeI]['Trips'][tripI - 1][-1] = bestIFarc
        
        if routeI == routeJ and tripI == tripJ and removePos < insertPos:
            self.solution[routeI]['Trips'][tripI].insert(insertPos, arcI)
            del self.solution[routeI]['Trips'][tripI][removePos]
        else:
            del self.solution[routeI]['Trips'][tripI][removePos]                        
            self.solution[routeJ]['Trips'][tripJ].insert(insertPos, arcI)
            
        self._updateArcPositions(routeI, tripI)
        if routeI != routeJ or tripI != tripJ: self._updateArcPositions(routeJ, tripJ)
        #if len(self.solution[routeI]['Route']) < 3: self._removeRoute(routeI, updateTotalCost = True)
        self._printMove(routeI, tripI, removePos, routeJ, tripJ, insertPos, self.solution['TotalCost'])
        extraInfo = ""
        return(extraInfo)
        
    def _relocateMoveIF(self):
        '''
        Make a relocate move.
        '''
        if self._testAll: self._testMoves._testRelocateIFMove(self._moveInfo,  self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, tripI, removePos) =  self.solutionMapping[arcI]
        (routeJ, tripJ, insertPos) =  self.solutionMapping[arcJ]
        
        dRelocate = self._demand[arcI]
        sRelocate = self._service[arcI]

        self._updateSolution(routeI, tripI, -dRelocate, moveCostsI - sRelocate)
        self._updateSolution(routeJ, tripJ, +dRelocate, moveCostsJ + sRelocate)
    
        bestIFarc = self._if_arc[preArcI][postArcI]
        if moveType.find('relocatePreIF') != -1:
            if tripI == len(self.solution[routeI]['Trips']) - 1:
                self.solution[routeI]['Trips'][tripI][-2] = bestIFarc
            else:
                self.solution[routeI]['Trips'][tripI][-1] = bestIFarc
                self.solution[routeI]['Trips'][tripI + 1][0] = bestIFarc
                
        if moveType.find('relocatePostIF') != -1:
            self.solution[routeI]['Trips'][tripI][0] = bestIFarc
            self.solution[routeI]['Trips'][tripI - 1][-1] = bestIFarc
        
        
        if moveType.find('_PreIF') != -1:
        
            bestIFarc = self._if_arc[arcI][postArcJ]
            if tripJ == len(self.solution[routeJ]['Trips']) - 1:
                self.solution[routeJ]['Trips'][tripJ][-2] = bestIFarc
            else:
                self.solution[routeJ]['Trips'][tripJ][-1] = bestIFarc
                self.solution[routeJ]['Trips'][tripJ + 1][0] = bestIFarc
            
            if routeI == routeJ and tripI == tripJ and removePos < insertPos + 1:
                self.solution[routeI]['Trips'][tripI].insert(insertPos + 1, arcI)
                del self.solution[routeI]['Trips'][tripI][removePos]
            else:
                del self.solution[routeI]['Trips'][tripI][removePos]                        
                self.solution[routeJ]['Trips'][tripJ].insert(insertPos + 1, arcI)
                
        if moveType.find('_PostIF') != -1:

            bestIFarc = self._if_arc[preArcJ][arcI]
            self.solution[routeJ]['Trips'][tripJ][0] = bestIFarc
            self.solution[routeJ]['Trips'][tripJ - 1][-1] = bestIFarc
            
            if routeI == routeJ and tripI == tripJ and removePos < insertPos:
                self.solution[routeI]['Trips'][tripI].insert(insertPos, arcI)
                del self.solution[routeI]['Trips'][tripI][removePos]
            else:
                del self.solution[routeI]['Trips'][tripI][removePos]                        
                self.solution[routeJ]['Trips'][tripJ].insert(insertPos, arcI)
                
        self._updateArcPositions(routeI, tripI)
        if routeI != routeJ or tripI != tripJ: self._updateArcPositions(routeJ, tripJ)
        #if len(self.solution[routeI]['Route']) < 3: self._removeRoute(routeI, updateTotalCost = True)
        self._printMove(routeI, tripI, removePos, routeJ, tripJ, insertPos, self.solution['TotalCost'])
        extraInfo = ""
        return(extraInfo)

    def _doubleRelocateMove(self):
        '''
        Make a relocate move.
        '''
        if self._testAll: self._testMoves._testDoubleRelocateMove(self._moveInfo,  self.solutionMapping, self.solution)
        
        (moveCost, (arcIa, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, tripI, removePos) =  self.solutionMapping[arcIa]
        arcIb = postArcJ
        (routeJ, tripJ, insertPos) =  self.solutionMapping[arcJ]
        
        dRelocate = self._demand[arcIa] + self._demand[arcIb]
        sRelocate = self._service[arcIa] + self._d[arcIa][arcIb] + self._service[arcIb]

        self._updateSolution(routeI, tripI, -dRelocate, moveCostsI - sRelocate)
        self._updateSolution(routeJ, tripJ, +dRelocate, moveCostsJ + sRelocate)
        
        if routeI == routeJ and tripI == tripJ and removePos < insertPos:
            self.solution[routeI]['Trips'][tripI].insert(insertPos, arcIa)
            self.solution[routeI]['Trips'][tripI].insert(insertPos + 1, arcIb)
            del self.solution[routeI]['Trips'][tripI][removePos + 1]
            del self.solution[routeI]['Trips'][tripI][removePos]
        else:
            del self.solution[routeI]['Trips'][tripI][removePos + 1]
            del self.solution[routeI]['Trips'][tripI][removePos]                       
            self.solution[routeJ]['Trips'][tripJ].insert(insertPos, arcIa)
            self.solution[routeJ]['Trips'][tripJ].insert(insertPos + 1, arcIb)
            
        self._updateArcPositions(routeI, tripI)
        if routeI != routeJ or tripI != tripJ: self._updateArcPositions(routeJ, tripJ)
        #if len(self.solution[routeI]['Route']) < 3: self._removeRoute(routeI, updateTotalCost = True)
        self._printMove(routeI, tripI, removePos, routeJ, tripJ, insertPos, self.solution['TotalCost'])
        extraInfo = ""
        return(extraInfo)

    def _exchangeMove(self):
        '''
        Make an exchange move.
        '''
        if self._testAll: self._testMoves._testExchangeMove(self._moveInfo, self.solutionMapping, self.solution)
        
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        
        (routeI, tripI, arcPos1) = self.solutionMapping[arcI]
        (routeJ, tripJ, arcPos2) = self.solutionMapping[arcJ]
        
        dRelocate = self._demand[arcI] - self._demand[arcJ]
        sRelocate = self._service[arcI] - self._service[arcJ]
                
        self._updateSolution(routeI, tripI, -dRelocate, moveCostsI - sRelocate)
        self._updateSolution(routeJ, tripJ, +dRelocate, moveCostsJ + sRelocate)
        
        self.solution[routeI]['Trips'][tripI][arcPos1] = arcJ
        self.solution[routeJ]['Trips'][tripJ][arcPos2] = arcI

        if moveType.find('1excPostIF') != -1:
            bestIF = self._if_arc[preArcI][arcJ]
            self.solution[routeI]['Trips'][tripI][0] = bestIF
            self.solution[routeI]['Trips'][tripI - 1][-1] = bestIF
        elif moveType.find('1excPreIF') != -1:
            bestIF = self._if_arc[arcJ][postArcI]
            if tripI == len(self.solution[routeI]['Trips']) - 1:
                self.solution[routeI]['Trips'][tripI][-2] = bestIF
            else:
                self.solution[routeI]['Trips'][tripI][-1] = bestIF
                self.solution[routeI]['Trips'][tripI + 1][0] = bestIF  

        if moveType.find('2excPostIF') != -1:
            bestIF = self._if_arc[preArcJ][arcI]
            self.solution[routeJ]['Trips'][tripJ][0] = bestIF
            self.solution[routeJ]['Trips'][tripJ - 1][-1] = bestIF
        elif moveType.find('2excPreIF') != -1:
            bestIF = self._if_arc[arcI][postArcJ]
            if tripJ == len(self.solution[routeJ]['Trips']) - 1:
                self.solution[routeJ]['Trips'][tripJ][-2] = bestIF
            else:
                self.solution[routeJ]['Trips'][tripJ][-1] = bestIF
                self.solution[routeJ]['Trips'][tripJ + 1][0] = bestIF 

        self.solutionMapping[arcJ] = (routeI, tripI, arcPos1)
        if arcJ in self._edgesS: self.solutionMapping[self._inv[arcJ]] = (routeI, tripI, arcPos1)
            
        self.solutionMapping[arcI] = (routeJ, tripJ, arcPos2)
        if arcI in self._edgesS: self.solutionMapping[self._inv[arcI]] = (routeJ, tripJ, arcPos2)

        self._printMove(routeI, tripI, arcPos1, routeJ, tripJ, arcPos2, self.solution['TotalCost'])
        extraInfo = ""
        return(extraInfo)

    def _flipMove(self):
        '''
        Flip an arc task in place.
        '''
        if self._testAll: self._testMoves._testFlipMove(self._moveInfo, self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, tripI, arcPos1) = self.solutionMapping[arcI]
        
        dRelocate = 0
        sRelocate = 0
                
        self._updateSolution(routeI, tripI, -dRelocate, moveCostsI - sRelocate)
        
        self.solution[routeI]['Trips'][tripI][arcPos1] = arcJ

        if moveType.find('excPostIF') != -1:
            bestIF = self._if_arc[preArcI][arcJ]
            self.solution[routeI]['Trips'][tripI][0] = bestIF
            self.solution[routeI]['Trips'][tripI - 1][-1] = bestIF
        elif moveType.find('excPreIF') != -1:
            bestIF = self._if_arc[arcJ][postArcI]
            if tripI == len(self.solution[routeI]['Trips']) - 1:
                self.solution[routeI]['Trips'][tripI][-2] = bestIF
            else:
                self.solution[routeI]['Trips'][tripI][-1] = bestIF
                self.solution[routeI]['Trips'][tripI + 1][0] = bestIF  

        self.solutionMapping[arcJ] = (routeI, tripI, arcPos1)
        self.solutionMapping[self._inv[arcJ]] = (routeI, tripI, arcPos1)
        
        self._printMove(routeI, tripI, arcPos1, None, None, None, self.solution['TotalCost'])
        extraInfo = ""
        return(extraInfo)

    def _crossMove(self):
        '''
        Cross two end sections of two routes.
        '''
        if self._testAll: self._testMoves._testCrossMove(self._moveInfo, self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, tripI, arcPos1) = self.solutionMapping[arcI]
        (routeJ, tripJ, arcPos2) = self.solutionMapping[arcJ]     

        if tripI == len(self.solution[routeI]['Trips']) - 1: 
            iEnd = -2
            endAddI = [self.solution[routeI]['Trips'][tripI][-2], self.solution[routeI]['Trips'][tripI][-1]]
        else: 
            iEnd = -1
            endAddI = [self.solution[routeI]['Trips'][tripI][-1]]
        
        if tripJ == len(self.solution[routeJ]['Trips']) - 1: 
            jEnd = -2
            endAddJ = [self.solution[routeJ]['Trips'][tripJ][-2], self.solution[routeJ]['Trips'][tripJ][-1]]
        else: 
            jEnd = -1
            endAddJ = [self.solution[routeJ]['Trips'][tripJ][-1]]

        if self.solution[routeI]['Trips'][tripI][iEnd] == self.solution[routeJ]['Trips'][tripJ][jEnd]:
            tripMove = 'TripMove'
            seqI1 = self.solution[routeI]['Trips'][tripI][:arcPos1]
            seqI2 = self.solution[routeI]['Trips'][tripI][arcPos1:iEnd]
            seqJ1 = self.solution[routeJ]['Trips'][tripJ][:arcPos2]
            seqJ2 = self.solution[routeJ]['Trips'][tripJ][arcPos2:jEnd]
                        
            self.solution[routeI]['Trips'][tripI] =  seqI1 + seqJ2 + endAddI
            self.solution[routeJ]['Trips'][tripJ] =  seqJ1 + seqI2 + endAddJ
        
        elif routeI != routeJ:
            tripMove = 'RouteMove'
            seqI0 = self.solution[routeI]['Trips'][:tripI]
            seqI1 = self.solution[routeI]['Trips'][tripI][:arcPos1]
            seqI2 = self.solution[routeI]['Trips'][tripI][arcPos1:]
            seqI3 = self.solution[routeI]['Trips'][tripI+1:]         
            
            seqJ0 = self.solution[routeJ]['Trips'][:tripJ]
            seqJ1 = self.solution[routeJ]['Trips'][tripJ][:arcPos2]
            seqJ2 = self.solution[routeJ]['Trips'][tripJ][arcPos2:]
            seqJ3 = self.solution[routeJ]['Trips'][tripJ+1:]  
            
            self.solution[routeI]['Trips'] = seqI0 + [seqI1 + seqJ2] + seqJ3   
            self.solution[routeJ]['Trips'] = seqJ0 + [seqJ1 + seqI2] + seqI3

        if moveType.find('_1crossPostIF') != -1:
            bestIFI = self._if_arc[preArcI][arcJ]
            self.solution[routeI]['Trips'][tripI-1][-1] = bestIFI
            self.solution[routeI]['Trips'][tripI][0] = bestIFI
            #print(routeI, bestIFI)
            
            
        if moveType.find('_2crossPostIF') != -1:
            bestIFJ = self._if_arc[preArcJ][arcI]
            self.solution[routeJ]['Trips'][tripJ-1][-1] = bestIFJ
            self.solution[routeJ]['Trips'][tripJ][0] = bestIFJ    
            #print(routeJ, bestIFJ)
        
        if tripI < len(self.solution[routeI]['Trips']) - 1:
            postArc = self.solution[routeI]['Trips'][tripI][-2]
            postPostArc = self.solution[routeI]['Trips'][tripI + 1][1]
            postIF = self.solution[routeI]['Trips'][tripI][-1]
            bestPostIFI = self._if_arc[postArc][postPostArc]
            if bestPostIFI != postIF:
                prevLinkCost = self._d[postArc][postIF] + self._d[postIF][postPostArc] + self._dumpCost
                newLinkCost = self._if_cost[postArc][postPostArc]
                moveCost += (newLinkCost - prevLinkCost)
                self.solution[routeI]['Trips'][tripI][-1] = bestPostIFI
                self.solution[routeI]['Trips'][tripI + 1][0] = bestPostIFI
        else:
            postArc = self.solution[routeI]['Trips'][tripI][-3]
            postPostArc = self.solution[routeI]['Trips'][tripI][-1]  
            postIF = self.solution[routeI]['Trips'][tripI][-2]
            bestPostIFI = self._if_arc[postArc][postPostArc]    
            if bestPostIFI != postIF:
                prevLinkCost = self._d[postArc][postIF] + self._d[postIF][postPostArc] + self._dumpCost
                newLinkCost = self._if_cost[postArc][postPostArc]       
                moveCost += (newLinkCost - prevLinkCost) 
                self.self.solution[routeI]['Trips'][tripI][-2] = bestPostIFI

        if tripJ < len(self.solution[routeJ]['Trips']) - 1:
            postArc = self.solution[routeJ]['Trips'][tripJ][-2]
            postPostArc = self.solution[routeJ]['Trips'][tripJ + 1][1]
            postIF = self.solution[routeJ]['Trips'][tripJ][-1]
            bestPostIFI = self._if_arc[postArc][postPostArc]
            if bestPostIFI != postIF:
                prevLinkCost = self._d[postArc][postIF] + self._d[postIF][postPostArc] + self._dumpCost
                newLinkCost = self._if_cost[postArc][postPostArc]
                moveCost += (newLinkCost - prevLinkCost)
                self.solution[routeJ]['Trips'][tripJ][-1] = bestPostIFI
                self.solution[routeJ]['Trips'][tripJ + 1][0] = bestPostIFI
        else:
            postArc = self.solution[routeJ]['Trips'][tripJ][-3]
            postPostArc = self.solution[routeJ]['Trips'][tripJ][-1]  
            postIF = self.solution[routeJ]['Trips'][tripJ][-2]
            bestPostIFI = self._if_arc[postArc][postPostArc]    
            if bestPostIFI != postIF:
                prevLinkCost = self._d[postArc][postIF] + self._d[postIF][postPostArc] + self._dumpCost
                newLinkCost = self._if_cost[postArc][postPostArc]       
                moveCost += (newLinkCost - prevLinkCost) 
                self.self.solution[routeJ]['Trips'][tripJ][-2] = bestPostIFI
        
        self._moveInfo = (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ))
        
        self._updateCrossSolution(routeI)
        self._updateRouteArcPositions(routeI)
        if routeI != routeJ:
            self._updateCrossSolution(routeJ)
            self._updateRouteArcPositions(routeJ)
        self.solution['TotalCost'] += moveCost

#         if routeI == 0 and tripI ==2 and routeJ == 5 and tripJ == 2:     
#             r = self.solution[routeI]['Trips'][tripI]
#             
#             for rI, r in enumerate(self.solution[routeI]['Trips']):
#                 c = [0] 
#                 s = [0]  
#                 dead = [0]           
#                 for ai, a in enumerate(r[1:]):
#                     rPos = ai + 1
#                     cCost = c[rPos - 1] + self._d[r[rPos - 1]][r[rPos]] + self.info.serveCostL[a]
#                     c.append(cCost)
#                     s.append(s[rPos - 1] + self.info.serveCostL[a])
#                     dead.append(dead[ai] + self._d[r[ai]][r[ai + 1]])
#                 c[-1] += self.info.dumpCost
#                 print('tC', rI, c)
#                 print('serve', rI, s)
#                 print('dead', rI, dead)
#             #print(solution[routeI]['Cost'], moveCostI, self._d[373][423] - self._d[373][815], solution[routeI]['CumServe'][tripI])
#             
#             r = self.solution[routeJ]['Trips'][tripJ]
#             
#             for rJ, r in enumerate(self.solution[routeJ]['Trips']):
#                 c2 = [0]   
#                 s2 = [0]       
#                 dead2 = [0]         
#                 for ai, a in enumerate(r[1:]):
#                     c2.append(c2[ai] + self._d[r[ai]][r[ai + 1]] + self.info.serveCostL[a])
#                     s2.append(s2[ai] + self.info.serveCostL[a])
#                     dead2.append(dead2[ai] + self._d[r[ai]][r[ai + 1]])
#                 c2[-1] += self.info.dumpCost
#                 print('tC', rJ, c2)
#                 print('serve', rJ, s2)
#                 print('dead', rJ, dead2)
#             #print(solution[routeJ]['Cost'], moveCostJ, self._d[579][815] - self._d[579][423], solution[routeJ]['CumServe'][tripJ])
#             
#         print(self.info.serveCostL[arcI], self.info.serveCostL[arcJ])
#         print(self.solution[0]['Cost'], self.solution[5]['Cost'])
        
        self._printMove(routeI, tripI, arcPos1, routeJ, tripJ, arcPos2, self.solution['TotalCost'], extraInfo = tripMove)
            
        #print(self.solution[routeI]['Trips'][tripI-1], self.solution[routeI]['Trips'][tripI])
        #print(self.solution[routeJ]['Trips'][tripJ-1], self.solution[routeJ]['Trips'][tripJ])

        extraInfo = tripMove
        return(extraInfo)
        
    def _doubleCrossMove(self):
        '''
        Cross four sections of a route in a single route.
        '''
        (tCost, (moveInfo1, moveInfo2), moveType) = self._moveInfo
        
        if self._testAll: self._testMoves._testCrossMove(moveInfo1, self.solutionMapping, self.solution)
        if self._testAll: self._testMoves._testCrossMove(moveInfo2, self.solutionMapping, self.solution)
        (arcI1, preArcI1, postArcI1, arcJ1, preArcJ1, postArcJ1) = moveInfo1[1]
        (arcI2, preArcI2, postArcI2, arcJ2, preArcJ2, postArcJ2) = moveInfo2[1]
        (routeI, tripI, arcIPos1) = self.solutionMapping[arcI1]
        (routeJ, tripJ, arcIPos2) = self.solutionMapping[arcJ1]
        (routeI2, tripI2, arcJPos1) = self.solutionMapping[arcI2]
        (routeJ2, tripJ2, arcJPos2) = self.solutionMapping[arcJ2]
        
        arcIpos1, arcIpos2 = min([arcIPos1, arcIPos2]), max([arcIPos1, arcIPos2])
        arcJpos1, arcJpos2 = min([arcJPos1, arcJPos2]), max([arcJPos1, arcJPos2])

        if arcIpos1 < arcJpos1:
            seq = (arcIpos1, arcJpos1, arcIpos2, arcJpos2)
        else:
            seq = (arcJpos1, arcIpos1, arcJpos2, arcIpos2)

        if routeI != routeJ or routeI2 != routeJ2 or routeI != routeI2: raise NameError('Double cross move cannot be applied to different routes: %i and %i and %i and %i'%(routeI, routeJ, routeI2, routeJ2))
        if tripI != tripJ or tripI2 != tripJ2 or tripI != tripI2: raise NameError('Double cross move cannot be applied to different trips: %i and %i and %i and %i'%(tripI, tripJ, tripI2, tripJ2))
        
        changeIFs = False
        if moveInfo1[-2].find('_1crossPostIF') != -1:
            changeIFs = True
            bestIF = self._if_arc[preArcI1][arcJ1]
        elif moveInfo1[-2].find('_2crossPostIF') != -1:
            changeIFs = True
            bestIF = self._if_arc[preArcJ1][arcI1]
        
        if moveInfo2[-2].find('_1crossPostIF') != -1:
            changeIFs = True
            bestIF = self._if_arc[preArcI2][arcJ2]
        elif moveInfo1[-2].find('_2crossPostIF') != -1:
            changeIFs = True
            bestIF = self._if_arc[preArcJ2][arcI2]
        
        if changeIFs: 
            self.solution[routeI]['Trips'][tripI - 1][-1] = bestIF
            self.solution[routeI]['Trips'][tripI][0] = bestIF
        

        (arcIpos1, arcJpos1, arcIpos2, arcJpos2) = seq
        route = self.solution[routeI]['Trips'][tripI]
        sec1 = route[:arcIpos1]
        sec2 = route[arcIpos1:arcJpos1]
        sec3 = route[arcJpos1:arcIpos2]
        sec4 = route[arcIpos2:arcJpos2]
        sec5 = route[arcJpos2:]
        newRoute = sec1 + sec4 + sec3 + sec2 + sec5
        self.solution[routeI]['Trips'][tripI] = newRoute
        self._updateCrossSolution(routeI)
        self._updateArcPositions(routeI, tripI)
        self.solution['TotalCost'] += moveInfo1[0]
        
        self._moveInfo = moveInfo1
        self._printMove(routeI, tripI, arcIpos1, routeI, tripI, arcIpos2, self.solution['TotalCost'], extraInfo = moveInfo1[-2])
        self.solution['TotalCost'] += moveInfo2[0]
        self._moveInfo = moveInfo2
        self._printMove(routeI, tripI, arcJpos1, routeI, tripI, arcJpos2, self.solution['TotalCost'], extraInfo = moveInfo1[-2]) 

        extraInfo = moveInfo1[-2]
        return(extraInfo)

    def _comboMove(self):
        (potentialSavings, (moveInfo1, moveInfo2), moveType) = self._moveInfo
        extraInfo1 = self.makeMove(moveInfo2, self.solution)
        extraInfo2 = self.makeMove(moveInfo1, self.solution)
        return(extraInfo1, extraInfo2)
    
    def makeMove(self, moveInfo, solution):
        '''
        Make move associated with move type.
        '''
        printSolution = False
        self.solution = solution
        self._moveInfo = moveInfo
        moveType = self._moveInfo[2]
        extraInfo = ""
        if moveType.find('relocate') != -1:
            if moveType.find('_PreIF') != -1 or moveType.find('_PostIF') != -1: 
                self._relocateMoveIF() 
            else:
                self._relocateMove() 
        
        if moveType.find('exchange') != -1:
            self._exchangeMove()
        
        if moveType.find('cross') != -1:
            extraInfo = self._crossMove()
 
        if moveType.find('flip') != -1:
            self._flipMove()
            
        if moveType == 'doubleRelocate': self._doubleRelocateMove()
        if moveType == 'relocateBeforeDummy': self._relocateBeginnigRouteMove()
        if moveType == 'crossAtDummy': self._crossAtDummyMove()
        if moveType == 'doubleCross': self._doubleCrossMove()
        if moveType == 'comboMove': self._comboMove()
        self._moveInfo = []
        if printSolution:
            for i in self.solution:
                print (self.solution[i])
        return(self.solution, extraInfo)

class DoubleCrossMovesMCARPTIF(object):
    '''
    Make special double cross move in one route.
    '''
    def __init__(self, info):
        self._testMoves = TestLocalSeach(info)
        self._printEachMove = True
        self._checkFeasibility = MovesFeasibleMCARPTIF(info)
        self.threshold = 0
    
    def findDoubleCrossMoveCosts(self, solution, solutionMapping, doubleCross):
        '''
        Check for non-improving relocate moves which will allow infeasible moves to become feasible.
        '''
        routesSavings = {}
        for moveInfo in doubleCross:
            (crossCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (routeIcostChange, routeJcostChange)) = moveInfo
            (routeI, tripI, arcPos1) = solutionMapping[arcI]
            if (routeI, tripI) not in routesSavings:
                routesSavings[(routeI, tripI)] = []
            routesSavings[(routeI, tripI)].append(moveInfo)
        return(routesSavings)
    
    def pairFeasibleDoubleCrossMoves(self, solution, solutionMapping, doubleCross):
        savings = {}
        doubleCross.sort(key=lambda x: x if isinstance(x, str) else "")
        routesSavings = self.findDoubleCrossMoveCosts(solution, solutionMapping, doubleCross)
        for (route, trip) in routesSavings:
            savings_R = []
            nSavings = len(routesSavings[(route, trip)])
            for i in range(nSavings - 1):
                moveInfo1 = routesSavings[(route, trip)][i]
                for j in range(i, nSavings):
                    moveInfo2 = routesSavings[(route, trip)][j]
                    tCost = moveInfo1[0] + moveInfo2[0]
                    if tCost >= self.threshold: continue
                    moveInfo = (tCost, (moveInfo1, moveInfo2), 'doubleCross')
                    feasible = self._checkFeasibility.checkMoveFeasibility(moveInfo, solutionMapping, solution)[0]
                    if feasible.find('feasible') != -1:
                        savings_R.append((tCost, (moveInfo1, moveInfo2), 'doubleCross'))
            if savings_R:
                savings_R.sort(key=lambda x: x if isinstance(x, str) else "")
                savings[route] = savings_R[:]
        return(savings)       

class InfeasibleMovesMCARPTIF(object):
    '''
    Check if moves are feasible
    '''
    def __init__(self, info):
        '''
        '''
        self.info = info
        self.threshold = 0
                    
    def findInfeasibleMoveCosts(self, solution, solutionMapping, infeasibleMoves):
        '''
        Check for non-improving relocate moves which will allow infeasible moves to become feasible.
        '''
        routesSavings = {}
        for InfeasibleMoveInfo in infeasibleMoves:
            (moveCost, loadI, loadJ, moveInfo) = InfeasibleMoveInfo
            (crossCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (routeIcostChange, routeJcostChange)) = moveInfo
            (routeI, tripI, arcI) = solutionMapping[arcI]
            (routeJ, tripJ, arcJ) = solutionMapping[arcJ]
            capI = solution[routeI]['TripLoads'][tripI] + loadI
            capJ = solution[routeJ]['TripLoads'][tripJ] + loadJ
            if capI > capJ:
                routeExcess = (routeI, tripI)
            else:
                routeExcess = (routeJ, tripJ)
            if routeExcess not in routesSavings:
                routesSavings[routeExcess] = []
            routesSavings[routeExcess].append(InfeasibleMoveInfo)
        return(routesSavings)       

    def findOutRelocateMoveCosts(self, solution, solutionMapping, savings):
        '''
        Check for non-improving relocate moves which will allow infeasible moves to become feasible.
        '''
        routesSavings = {}
        for moveInfo in savings:
            (crossCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (routeIcostChange, routeJcostChange)) = moveInfo
            if moveType.find('relocate') == -1: continue
            (routeI, tripI, arcI) = solutionMapping[arcI]
            (routeJ, tripJ, arcJ) = solutionMapping[arcJ]
            
            if routeI != routeJ or tripI == tripJ: continue
            if routeI not in routesSavings:
                routesSavings[(routeI, tripI)] = []
            routesSavings[(routeI, tripI)].append(moveInfo)           
        return(routesSavings)  

    def infeasibleMoveCombos(self, solution, solutionMapping, infeasibleMoves, exceedThreshold):
        
        CompoundTemp = CompoundMoveFunctions(self.info, False)
        infeasibleGrouping = self.findInfeasibleMoveCosts(solution, solutionMapping, infeasibleMoves)
        
        if not infeasibleMoves:
            return([])
        
        outMoves = [move[3] for move in infeasibleMoves] + exceedThreshold
        outMoves.sort(key=lambda x: x if isinstance(x, str) else "")
        
        #print(infeasibleGrouping)
        #print(outMoves)
        
        outGrouping = self.findOutRelocateMoveCosts(solution, solutionMapping, outMoves)

        savingsCombo = []
        for (routeI, tripI) in infeasibleGrouping:
            if (routeI, tripI) not in outGrouping: continue
            for InfeasibleMoveInfo in infeasibleGrouping[(routeI, tripI)]:
                CompoundTemp.resetMoveInfluencers()
                (moveCost, loadI, loadJ, moveInfo) = InfeasibleMoveInfo
                CompoundTemp.addMoveInfluence(moveInfo)
                for outMoveInfo in outGrouping[(routeI, tripI)]:
                    if moveInfo[0] + outMoveInfo[0] >= self.threshold: continue
                    compoundComboOutFeasible = CompoundTemp.checkCompoundMoveFeasibility(outMoveInfo)
                    if compoundComboOutFeasible:
                        savingsCombo.append((moveInfo[0] + outMoveInfo[0], (moveInfo, outMoveInfo), 'comboMove'))
        
        savingsCombo.sort(key=lambda x: x if isinstance(x, str) else "")
        
        return(savingsCombo)

class CompoundMoveFunctions():

    def __init__(self, info, autoInvCosts = False):
        self.autoInvCosts = autoInvCosts
        self._depotArc = info.depotnewkey
        self._inv = info.reqInvArcList
        self._reqArcs = set(info.reqArcListActual)
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self._locationChanged = set()
        self._preLocationChanged = set()
        self._dummyRoutes = set()

    def _genMCARPTIFclassifications(self, solution):
        '''
        Takes an initial solution and generates a giant route with the necessary giant route arc position mapping. 
        '''
        solutionArcs = set()
        
        endTripArcs = set()
        endRouteArcs = set()
        beginTripArcs = set()
        beginRouteArcs = set()
        
        endTripArcsF = set()
        endRouteArcsF = set()
        beginTripArcsF = set()
        beginRouteArcsF = set()
        
        normalArcs = set()
        normalArcsF = set()
        
        k = 0
        for i in range(solution['nVehicles']):
            nSubtrips = len(solution[i]['Trips'])
            for j in range(nSubtrips):
                subtrip = solution[i]['Trips'][j]
                nArcs = len(subtrip)
                for n, arc in enumerate(subtrip): # Each route consists of a start and end depot visit, with only one needed in the giant route.
                    
                    if n == 0: continue
                    
                    k += 1
                    
                    normalPosition = True
                    if j == 0 and n == 1:
                        beginRouteArcs.add(arc)
                        beginRouteArcsF.add(arc)
                        if arc in self._edgesS: beginRouteArcsF.add(self._inv[arc])
                        normalPosition = False
                    if j > 0 and n == 1:
                        beginTripArcs.add(arc)
                        beginTripArcsF.add(arc)
                        if arc in self._edgesS: beginTripArcsF.add(self._inv[arc])
                        normalPosition = False   
                    if j == nSubtrips - 1 and n >= len(subtrip) - 3: 
                        normalPosition = False 
                        if n == len(subtrip) - 3:
                            endRouteArcs.add(arc)
                            endRouteArcsF.add(arc)
                            if arc in self._edgesS: endRouteArcsF.add(self._inv[arc])
                    if j < nSubtrips - 1 and n >= len(subtrip) - 2:
                        normalPosition = False 
                        if n == len(subtrip) - 2:
                            endTripArcs.add(arc)
                            endTripArcsF.add(arc)
                            if arc in self._edgesS: endTripArcsF.add(self._inv[arc])

                    if j == nSubtrips - 1 and n == nArcs - 2:
                        pass
                    elif j == nSubtrips - 1 and n == nArcs - 1:
                        pass
                    elif n == nArcs - 1:
                        pass
                    else:
                        solutionArcs.add(arc)
                        if normalPosition == True:
                            normalArcs.add(arc)
                            normalArcsF.add(arc)
                            if arc in self._edgesS: normalArcsF.add(self._inv[arc])

        singleRouteArcs = beginRouteArcs.intersection(endRouteArcs)
        singleTripArcs = (beginRouteArcs.union(beginTripArcs)).intersection(endRouteArcs.union(endTripArcs))
        singleTripArcs = singleTripArcs.difference(singleRouteArcs)
        
        singleRouteArcsF = singleRouteArcs.copy()
        for arc in singleRouteArcs:
            if arc in self._edgesS:
                singleRouteArcsF.add(self._inv[arc])
        
        singleTripArcsF = singleTripArcs.copy()
        for arc in singleTripArcs:
            if arc in self._edgesS:
                singleTripArcsF.add(self._inv[arc])
    
        self.solutionArcs = solutionArcs
        self.normalArcs = normalArcs
        self.normalArcsF = normalArcsF
        self.beginRouteArcs = beginRouteArcs
        self.beginRouteArcsF = beginRouteArcsF
        self.beginTripArcs = beginTripArcs
        self.beginTripArcsF = beginTripArcsF
        self.endRouteArcs = endRouteArcs
        self.endRouteArcsF = endRouteArcsF
        self.endTripArcs = endTripArcs
        self.endTripArcsF = endTripArcsF

        self.singleRouteArcs = singleRouteArcs
        self.singleRouteArcsF = singleRouteArcsF
        self.singleTripArcs = singleTripArcs        
        self.singleTripArcsF = singleTripArcsF
        self.verySpecialArcs = singleRouteArcsF.union(singleTripArcsF).union(singleRouteArcsF)

    def checkCompoundMoveFeasibility(self, moveInfo):   
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        
        feasible = True
        
        if moveType == 'doubleRelocate':
            arcI1 = arcI
            arcI2 = postArcJ
            if arcI1 in self._locationChanged or arcI2 in self._locationChanged or arcJ in self._preLocationChanged:
                feasible = False
                
        elif arcI in self._locationChanged:
            feasible = False
        
        if moveType.find('relocate') != -1:
            if moveType.find('_PreIF') != -1:
                if arcJ in self._preLocationChanged or postArcJ in self._preLocationChanged: 
                    feasible = False
            elif moveType.find('_PostIF') != -1 and arcJ in self._preLocationChanged:
                feasible = False
            elif arcJ in self._preLocationChanged:
                feasible = False
        elif moveType.find('exchange') != -1:
            if arcI in self._locationChanged or arcJ in self._locationChanged:
                feasible = False
        elif moveType.find('cross') != -1:
            if arcI in self._locationChanged or arcJ in self._locationChanged:
                feasible = False     
        elif moveType.find('flip') != -1:
            if arcI in self._locationChanged or arcJ in self._locationChanged:
                feasible = False            
            
        return(feasible)

    def checkCompoundDoubleMoveFeasibility(self, moveInfo):
        (moveCost, (moveInfo1, moveInfo2), moveType) = moveInfo   
        feasible = self.checkCompoundMoveFeasibility(moveInfo1) and self.checkCompoundMoveFeasibility(moveInfo2)
        return(feasible)

    def _addInverseArcInfleunce(self):
        
        for arc in set(self._locationChanged).intersection(self._edgesS):
            self._locationChanged.add(self._inv[arc])
        
        for arc in set(self._locationChanged).intersection(self._edgesS):
            self._preLocationChanged.add(self._inv[arc])

        for arc in set(self._dummyRoutes).intersection(self._edgesS):
            self._dummyRoutes.add(self._inv[arc])
    
    def addArc(self, arcs):
        addSet = set()
        for arc in arcs:
            if arc != self._depotArc:
                addSet.add(arc)
                if arc in self._edgesS:
                    addSet.add(self._inv[arc])
            
        return(addSet)
    
    def addMoveInfluence(self, moveInfo, solution = None, solutionMapping= None, feasible = ''):
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo                       

        self._locationChanged.update(self.addArc({preArcI, arcI, postArcI, preArcJ, arcJ, postArcJ}))
        self._preLocationChanged.update(self.addArc({preArcI, arcI, postArcI, preArcJ, arcJ, postArcJ}))
        
        if feasible.find('feasibleTrip') != -1:
            (routeI, tripI, posI) = solutionMapping[arcI]
            (routeJ, tripJ, posJ) = solutionMapping[arcJ]

            if tripI < len(solution[routeI]['Trips']) - 1:
                preArcI = solution[routeI]['Trips'][tripI][-2]
                postArcI = solution[routeI]['Trips'][tripI + 1][1]
            else:
                preArcI = solution[routeI]['Trips'][tripI][-3]            
            
            if tripJ < len(solution[routeJ]['Trips']) - 1:
                preArcJ = solution[routeJ]['Trips'][tripJ][-2]
                postArcJ = solution[routeJ]['Trips'][tripJ + 1][1]
            else:
                preArcJ = solution[routeJ]['Trips'][tripJ][-3]
            
            self._locationChanged.update(self.addArc({preArcI, postArcI, preArcJ, postArcJ}))
            self._preLocationChanged.update(self.addArc({preArcI, postArcI, preArcJ, postArcJ}))
    
    def addCrossMoveInfluence(self, moveInfo, solution, solutionMapping):
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo 
        
        (routeI, tripI, posI) = solutionMapping[arcI]
        (routeJ, tripJ, posJ) = solutionMapping[arcJ]
        
        if tripI < len(solution[routeI]['Trips']) - 1:
            preArcI = solution[routeI]['Trips'][tripI][-2]
            postArcI = solution[routeI]['Trips'][tripI + 1][1]
        else:
            preArcI = solution[routeI]['Trips'][tripI][-3]
            postArcI =  preArcI        
            
        if tripJ < len(solution[routeJ]['Trips']) - 1:
            preArcJ = solution[routeJ]['Trips'][tripJ][-2]
            postArcJ = solution[routeJ]['Trips'][tripJ + 1][1]
        else:
            preArcJ = solution[routeJ]['Trips'][tripJ][-3]   
            postArcJ = preArcJ
        
        self._locationChanged.update(self.addArc({preArcI, postArcI, preArcJ, postArcJ}))
        self._preLocationChanged.update(self.addArc({preArcI, postArcI, preArcJ, postArcJ}))

    def addDoubleMoveInfluence(self, moveInfo):
        (moveCost, (moveInfo1, moveInfo2), moveType) = moveInfo
        self.addMoveInfluence(moveInfo1)
        self.addMoveInfluence(moveInfo2)
        
    def returnNonCompoundMoves(self, moves):
        allowableMoves = []
        for moveInfo in moves:
            if self.checkCompoundMoveFeasibility(moveInfo):
                allowableMoves.append(moveInfo)
        return(allowableMoves)

    def returnNonCompoundInfeasibleMoves(self, moves):
        allowableMoves = []
        for compoundMoveInfo in moves:
            moveInfo = compoundMoveInfo[3]
            if self.checkCompoundMoveFeasibility(moveInfo):
                allowableMoves.append(compoundMoveInfo)
        return(allowableMoves)
    
    def returnRelocateArcs(self):
        relocateArcs = self._locationChanged.intersection(self._reqArcs).difference(self.verySpecialArcs)
        relocateArcsDiff = self._reqArcs.difference(relocateArcs).difference(self.verySpecialArcs)
        return(relocateArcs, relocateArcsDiff)

    def returnRelocateArcsNormal(self):
        relocateArcs = self._locationChanged.intersection(self.normalArcsF.union(self.beginRouteArcsF))
        normalArcsDiff = (self.normalArcsF.union(self.beginRouteArcsF)).difference(relocateArcs)
        return(relocateArcs, normalArcsDiff)
    
    def returnInsertPositionsNormal(self):
        insertLocations = self._locationChanged.intersection(self.normalArcs.union(self.beginRouteArcs).union(self.endRouteArcs).union(self.endTripArcs)).difference(self.verySpecialArcs)
        return(insertLocations)
    
    def returnInsertPositionsPreIF(self):
        insertLocations = self._locationChanged.intersection(self.endTripArcs.union(self.endRouteArcs).union(self.singleTripArcs).union(self.singleRouteArcs))
        return(insertLocations)
    
    def returnInsertPositionsPostIF(self):
        insertLocations = self._locationChanged.intersection(self.beginTripArcs).difference(self.verySpecialArcs)
        return(insertLocations)

    def returnSolutionArcs(self):
        solutionArcs = self._locationChanged.intersection(self.solutionArcs).difference(self.verySpecialArcs)
        return(solutionArcs)

    def returnCrossArcs(self):
        solutionArcs = self._locationChanged.intersection(self.solutionArcs).difference(self.verySpecialArcs).difference(self.beginTripArcs)
        return(solutionArcs)

    def returnSolutionEdges(self):
        solutionArcs = self._locationChanged.intersection(self.solutionArcs).intersection(self._edgesS).difference(self.verySpecialArcs)
        return(solutionArcs)

    def resetMoveInfluencers(self):
        self._locationChanged = set()
        self._preLocationChanged = set()
        self._dummyRoutes = set()
        
    def saveMoveInfluencers(self):
        self._locationChangedCopy = self._locationChanged.copy()
        self._preLocationChangedCopy = self._preLocationChanged.copy()
        
    def restoreMoveInfluencers(self):   
        self._locationChanged = self._locationChangedCopy.copy()
        self._preLocationChanged = self._preLocationChangedCopy.copy()

class ReduceFleetSize(object):
    
    def __init__(self, info):
        self._info = info
        self._reduceAllTrips = True
        self._targetFleetSize = 0
        self._ReduceRoutes = ReduceRoutes(info)
        self._printSummary = True
        
    def reduceFleet(self, solution):
        reduced = False
        if self._reduceAllTrips and solution['nVehicles'] > self._targetFleetSize:   
            prevCost = solution['TotalCost']         
            prevK = solution['nVehicles']
            (reduced, solution2) = self._ReduceRoutes.reduce_CLARPIF_solution(solution)
            if reduced:
                savings = solution2['TotalCost'] - prevCost
                fleetSavings = prevK - solution2['nVehicles']
                outS = (savings, 'reduced-routes', fleetSavings,prevK,solution2['nVehicles'])
                s = "\n Saving: %i \t Type: %s \t Fleet reduced by: %i from %i to %i"%outS
                if self._printSummary: print(s)
                solution = solution2
                solution = addMCARPcumulativeSolution(self._info, solution)
            else:
                if self._printSummary: print('\n Fleet of %i not reduced'%prevK)
        return(solution, reduced)

class LS_MCARPTIF(object):
    '''
    Class to implement MCARP moves.
    '''
    
    def __init__(self, info, nnList = None, testAll = True, autoInvCosts = False):
        '''
        Class initialization values.
        '''
        # Problem infos
        self.info = info
        self.nnFrac = 1
        self.threshold = 0
        self.thresholdUse = 1
        self.candidateMoves = False
        self._dumpCost = info.dumpCost
        
        # Move costs
        self.autoInvCosts = autoInvCosts
        self._MoveCosts = CalcMoveCosts(info, nnList = nnList, autoInvCosts = autoInvCosts)
        self._MovesFeasible = MovesFeasibleMCARPTIF(info)
        self._MovesMaker = MakeMovesMCARPTIF(info, testMoves = testAll)
        self._MovesDoubleCross = DoubleCrossMovesMCARPTIF(info)
        self._MovesCompound = CompoundMoveFunctions(info, autoInvCosts)
        self._MovesInfeasible = InfeasibleMovesMCARPTIF(info)
        
        # Move test
        self._testAll = testAll
        self._testMoves = TestLocalSeach(info)
        
        # Printing setup
        self._printEachMove = True
        self._printSummary = True
        self._movesNotUsed = []
        self._nMovesPrevious = 0
        self._nMoves = 0
        self._nCompoundMoves = 0
        self._solutionChange = 0
        self._previousCost = 0
        
        self.doubleCross = False
        self.comboFeasibleMoves = False
        self.comboMovesVN = False
        
        self.newDoubleCross = False
        self.newComboFeasibleMoves = False
        self.newComboMovesVN = False
        
        self.compoundMoves = False
        
        self.nonAdjacentRestrictionInsert = False
        self.nonAdjacentRestrictionExchange = False
        self.nonAdjacentRestrictionCross = False
        
        self._MoveCosts.autoInvCosts = True
        self.displaySolution = py_display_solution.display_solution_stats(info)

        self._ReduceFleet = ReduceFleetSize(info)

    def setNonAdjacentArcRestriction(self):
        self._MoveCosts.nonAdjacentRestrictionInsert = self.nonAdjacentRestrictionInsert
        self._MoveCosts.nonAdjacentRestrictionExchange = self.nonAdjacentRestrictionExchange
        self._MoveCosts.nonAdjacentRestrictionCross = self.nonAdjacentRestrictionCross
    
    def resetLocalSearchFunctions(self):
        self._movesNotUsed = []
        self._nMovesPrevious = 0
        self._nMoves = 0
        self._nCompoundMoves = 0
        self._solutionChange = 0
        self._previousCost = 0
    
    def setScreenPrint(self, printMoves):
        '''
        Specify which parts of the Local Search should be executed
        ''' 
        self._printEachMove = printMoves
        self._MovesMaker._printEachMove = printMoves
        self._MovesDoubleCross._printEachMove = printMoves
        self._printSummary = printMoves
        self._ReduceFleet._printSummary = printMoves
        
        
    def _initiateLocalSearchRoute(self):
        self._MovesFeasible.restartFeasibility()
        self._MovesCompound.resetMoveInfluencers()

    def _candidateCalculations(self, solution):
        
        #self._reduceCompoundMoves()
        self._MovesCompound._genMCARPTIFclassifications(solution)
        self._movesNotUsed = self._MovesCompound.returnNonCompoundMoves(self._movesNotUsed)
        movesToUse = self._movesNotUsed

        #routeArcs = self._MovesCompound.returnRouteArcs(solution)
        #routeArcsEnd = self._MovesCompound.returnRouteArcsEnd(solution)
        #routeArcsBegin = self._MovesCompound.returnRouteArcsBegin(solution)

        savings = movesToUse

        (relocateArcs, relocateArcsDiff) = self._MovesCompound.returnRelocateArcs()
        insertPositionsNormal = self._MovesCompound.returnInsertPositionsNormal()

        #savings += self._MoveCosts.calcRelocateMoves(relocateCandidates = None, insertCandidates = None)
        savings += self._MoveCosts.calcRelocateMoves(relocateCandidates = relocateArcs, insertCandidates = None)
        savings += self._MoveCosts.calcRelocateMoves(relocateCandidates = relocateArcsDiff, insertCandidates = insertPositionsNormal)
        
        insertPositionsPreIF = self._MovesCompound.returnInsertPositionsPreIF()
        #savings += self._MoveCosts.calcRelocatePreIFMoves(relocateCandidates = None, insertCandidates = None)
        savings += self._MoveCosts.calcRelocatePreIFMoves(relocateCandidates = relocateArcs, insertCandidates = None)
        savings += self._MoveCosts.calcRelocatePreIFMoves(relocateCandidates = relocateArcsDiff, insertCandidates = insertPositionsPreIF) 
    

        insertPositionsPostIF = self._MovesCompound.returnInsertPositionsPostIF()
        #savings += self._MoveCosts.calcRelocatePostIFMoves(relocateCandidates = None, insertCandidates = insertPositionsPostIF)
        savings += self._MoveCosts.calcRelocatePostIFMoves(relocateCandidates = relocateArcs, insertCandidates = None)
        savings += self._MoveCosts.calcRelocatePostIFMoves(relocateCandidates = relocateArcsDiff, insertCandidates = insertPositionsPostIF) 

        savings += self._MoveCosts.calcExchangeMoves(exchangeCandidates1 = relocateArcs, exchangeCandidates2 = None)
        savings += self._MoveCosts.calcExchangeMoves(exchangeCandidates1 = None, exchangeCandidates2 = relocateArcs) # optional
        
        crossArcs = self._MovesCompound.returnCrossArcs()
        savings += self._MoveCosts.calcCrossMoves(crossCandidates1 = crossArcs, crossCandidates2 = None) 
        savings += self._MoveCosts.calcCrossMoves(crossCandidates1 = None, crossCandidates2 = crossArcs) # optional
        
        solutionEdges = self._MovesCompound.returnSolutionEdges()
        savings += self._MoveCosts.calcFlipMoves(solutionEdges)
        
        return(savings)
    
    def _calculateMoveCosts(self, solution, candidateSearch = False):
        self._MoveCosts.setInputValues(self.thresholdUse, self.nnFrac)
        self._MoveCosts.setSolution(solution)
        self.setNonAdjacentArcRestriction()
        if not candidateSearch:
            savings = self._MoveCosts.calcAllPossibleMoveCosts()
        else:
            savings = self._candidateCalculations(solution)
        self._MoveCosts.freeSolution()
        return(savings)

    def _makeCompoundMoves(self, savings, solution):
        '''
        Find the best feasible move
        '''
        self._MovesMaker.setSolution(solution)
        self._MovesMaker.setSearchPhase('Feasible moves')
        feasibleMove = False
        
        nMoves = len(savings)
        for iMove, moveInfo in enumerate(savings):
            compoundFeasible = self._MovesCompound.checkCompoundMoveFeasibility(moveInfo)
            if not compoundFeasible: continue
            
            solutionMapping = self._MovesMaker.solutionMapping
            (feasible, solution) = self._MovesFeasible.checkMoveFeasibility(moveInfo, solutionMapping, solution)[:2]
            if feasible.find('feasible') == -1 or moveInfo[0] >= self.threshold:
                self._movesNotUsed.append(moveInfo)
                continue

            feasibleMove = True

            self._MovesCompound.addMoveInfluence(moveInfo, solution, solutionMapping, feasible)
            (solution, extraInfo) = self._MovesMaker.makeMove(moveInfo, solution)
            
            if extraInfo == "TripMove":
                self._MovesCompound.addCrossMoveInfluence(moveInfo, solution, solutionMapping)
            
            self._nMoves += 1

            if self._testAll: self._testMoves._testSolution(solution)
            
            if not self.compoundMoves: 
                self._movesNotUsed += savings[min(iMove + 1, nMoves):]
                break
        
        return(feasibleMove, solution)

    def _makeDoubleCrossCompoundMoves(self, solution):
        
        self._MovesMaker.setSearchPhase('Feasible double-cross moves')
        self._MovesMaker.setSolution(solution)
        
        self._MovesFeasible.doubleCrossMove = self._MovesCompound.returnNonCompoundMoves(self._MovesFeasible.doubleCrossMove)
        self._MovesFeasible.exceedThresholdDoubleCross = self._MovesCompound.returnNonCompoundMoves(self._MovesFeasible.exceedThresholdDoubleCross)
        
        doubleCrossMoves = self._MovesFeasible.doubleCrossMove + self._MovesFeasible.exceedThresholdDoubleCross
        
        savingsR = self._MovesDoubleCross.pairFeasibleDoubleCrossMoves(solution, self._MovesMaker.solutionMapping, doubleCrossMoves)
        feasibleMove = False
        
        for route in savingsR:
            for moveInfo in savingsR[route]:
                solutionMapping = self._MovesMaker.solutionMapping
                if moveInfo[0] >= self.threshold: continue
                compoundFeasible = self._MovesCompound.checkCompoundDoubleMoveFeasibility(moveInfo)
                if not compoundFeasible: continue
                self._MovesCompound.addDoubleMoveInfluence(moveInfo)
                self._nMoves += 1
                (solution, extraInfo) = self._MovesMaker.makeMove(moveInfo, solution)
                if self._testAll: self._testMoves._testSolution(solution)
                feasibleMove = True
                break
        return(feasibleMove, solution)
   
    def _makeInfeasibleCompoundMoves(self, solution):
            
        self._MovesMaker.setSearchPhase('Current infeasible moves')
        self._MovesMaker.setSolution(solution)
        self._MovesFeasible.infeasibleMoves = self._MovesCompound.returnNonCompoundInfeasibleMoves(self._MovesFeasible.infeasibleLoadMoves)
        self._MovesFeasible.exceedThresholdRemoveInsert = self._MovesCompound.returnNonCompoundMoves(self._MovesFeasible.exceedThresholdRemoveInsert)
        
        infeasibleMoves = self._MovesFeasible.infeasibleMoves
        costlyMoves = self._MovesFeasible.exceedThresholdRemoveInsert
        
        infeasibleMoveCombos = self._MovesInfeasible.infeasibleMoveCombos(solution, self._MovesMaker.solutionMapping, infeasibleMoves, costlyMoves)
        feasibleMove = False
        
        #print(infeasibleMoveCombos)
        
        for comboMove in infeasibleMoveCombos:
            #print(comboMove)
            compoundFeasible = self._MovesCompound.checkCompoundDoubleMoveFeasibility(comboMove)
            #print(compoundFeasible)
            if not compoundFeasible: continue
            feasible = self._MovesFeasible.doubleMoveFeasibility(comboMove, self._MovesMaker.solutionMapping, solution)
            (cost, (moveInfo1, moveInfo2), moveType) = comboMove
            if cost >= self.threshold: continue
            elif feasible.find('feasible') != -1:
                self._MovesCompound.addDoubleMoveInfluence(comboMove)
                self._nMoves += 1
                (solution, extraInfo) = self._MovesMaker.makeMove(comboMove, solution)
                feasibleMove = True
        
        return(feasibleMove, solution)
    
    def compoundLocalSearch(self, solution):
        
        solution = addMCARPcumulativeSolution(self.info, solution)
        candidateSearch = False
        self.setNonAdjacentArcRestriction()
        reducedFleet = False        
        
        while True:
            
            self._nCompoundMoves += 1
            self._nMovesPrevious = self._nMoves
            if self._printEachMove:
                #pass
                print('')            
            if self._testAll: self._testMoves._testSolution(solution)
            savings = self._calculateMoveCosts(solution, candidateSearch)
            if not savings: break
            candidateSearch = self.candidateMoves
            savings.sort(key=lambda x: x if isinstance(x, str) else "")
            
            self._movesNotUsed = []
            self._MovesCompound.resetMoveInfluencers()
            self._MovesFeasible.restartFeasibility()
                        
            feasibleMoves = []
            
            (feasibleMove, solution) = self._makeCompoundMoves(savings, solution)
            feasibleMoves.append(feasibleMove)
            
            if not self.comboMovesVN or (not True in feasibleMoves and self.comboMovesVN):
                if self.doubleCross:
                    (feasibleMove, solution) = self._makeDoubleCrossCompoundMoves(solution)
                    feasibleMoves.append(feasibleMove)
                if self.comboFeasibleMoves:
                    (feasibleMove, solution) = self._makeInfeasibleCompoundMoves(solution)
                    feasibleMoves.append(feasibleMove)
                    
            if not self.newComboMovesVN or (not True in feasibleMoves and self.newComboMovesVN):
                if self.newDoubleCross:
                    (feasibleMove, solution) = self._makeNewDoubleCrossCompoundMoves(solution)
                    feasibleMoves.append(feasibleMove)                    
                if self.newComboFeasibleMoves:
                    (feasibleMove, solution) = self._makeNewInfeasibleCompoundMoves(solution)
                    feasibleMoves.append(feasibleMove)

            if not True in feasibleMoves: 
                break
            else:
                nMovesMade = self._nMoves - self._nMovesPrevious
                self._solutionChange = solution['TotalCost'] - self._previousCost
                self._previousCost = solution['TotalCost']
                if self._printEachMove:
                    print('I: %i \t Saving: %i \t # Moves %i \t Moves made %i'%(self._nCompoundMoves, self._solutionChange, self._nMoves, nMovesMade))
            
            solution = build_CLARPIF_dict_correct(solution, self.info)
            #self.displaySolution.display_CLARPIF_solution_info(solution)
            (solution, reducedFleet) = self._ReduceFleet.reduceFleet(solution)
            #input('a=enter')
            if reducedFleet: break
            
        return(solution, reducedFleet)
    
    def twoPhaseCompoundLocalSearch(self, solution):
        self._previousCost = solution['TotalCost']
        self.nnFrac = 0.1
        #self._MoveCosts.movesToUse = ['relocate']# ['cross', 'crossAtDummy']
        self.candidateMoves = True
        (solution, reducedFleet) = self.compoundLocalSearch(solution)
        self.nnFrac = 1
        self.candidateMoves = True
        (solution, reducedFleet) = self.compoundLocalSearch(solution)
        self._MoveCosts.freeInputValues()
        fileOut = open('LocalOptima/' + self.info.name + '_Merge' + '.sol', 'w')
        cPickle.dump(solution, fileOut)
        fileOut.close()
        return(solution)
    
    def localSearch(self, solutionStart, nnFrac = 1, candidateMoves = True, compoundMoves = True):
        t = clock()
        solution = deepcopy(solutionStart)
        self._initialCost = solution['TotalCost']
        self._initialK = solution['nVehicles']
        self.nnFrac = nnFrac
        self.candidateMoves = candidateMoves
        self.compoundMoves = compoundMoves
        while True:
            self._previousCost = solution['TotalCost']
            (solution, reducedFleet) = self.compoundLocalSearch(solution)
            if not reducedFleet: break
        self._MoveCosts.freeInputValues()
        self.executionTime = clock() - t
        self._finalK = solution['nVehicles']
        self._finalCost = solution['TotalCost']
        self.searchSummary()
        return(solution)

    def returnStats(self, pSet, initial, moveStrategy = 'ScanAllMoves'):
        if self.candidateMoves: canList = 'TRUE'
        else: canList = 'FALSE'
        if self.compoundMoves: compoundMove = 'TRUE'
        else: compoundMove = 'FALSE'
        outputLine = '%s,%s,%s,%.2f,%s,%s,%i,%i,%i,%i,%.4f,%i,%i,%s\n'%(pSet,self.info.name,initial,self.nnFrac,canList,compoundMove,self._initialK, self._initialCost, self._finalK, self._finalCost,self.executionTime, self._nMoves, self._nCompoundMoves, moveStrategy)
        return(outputLine)

    def returnStatsFormat(self, pSet, initial, nSol, initTime):
        if self.candidateMoves: canList = 'TRUE'
        else: canList = 'FALSE'
        if self.compoundMoves: compoundMove = 'TRUE'
        else: compoundMove = 'FALSE'
        
        if self.comboFeasibleMoves and not self.comboMovesVN: moveStrategy = 'FALSE'
        elif self.comboFeasibleMoves and self.comboMovesVN: moveStrategy = 'TRUE'
        else: moveStrategy = 'FALSE'
        
        pType = 'MCARPTIF'
        outputLineInfo = (pSet, self.info.name, pType, self.nnFrac, canList, compoundMove, self._initialK, self._initialCost, self._finalK, self._finalCost, self.executionTime, self._nMoves, self._nCompoundMoves, moveStrategy, initial, nSol, initTime)
        #print(outputLineInfo)
        outputLineStr = '%s,%s,%s,%.2f,%s,%s,%i,%i,%i,%i,%.4f,%i,%i,%s,%s,%i,%.8f\n'%outputLineInfo
        return(outputLineStr)

    def locaSearchImbedded(self, solutionStart):#, nnFrac = 1, candidateMoves = True, compoundMoves = True):
        t = clock()
        solution = deepcopy(solutionStart)
        self._initialCost = solution['TotalCost']
        self._previousCost = solution['TotalCost']
        (solution, reducedFleet) = self.compoundLocalSearch(solution)
        self.executionTime = clock() - t
        return(deepcopy(solution))

    def improveSolution(self, solutionStart):
        return self.locaSearchImbedded(solutionStart)

    def locaSearchFree(self):
        self._MoveCosts.freeInputValues()

    def clearCythonModules(self):
        self._MoveCosts.freeInputValues()


    def searchSummary(self, ):
        (initK, initZ, finalK, finalZ) = (self._initialK, self._initialCost, self._finalK, self._finalCost)
        fleetSave = initK - finalK
        fleetSaveFrac = fleetSave/initK
        costSave = initZ - finalZ
        costSaveFrac = costSave/initZ
        if self._printSummary:
            print('')
            print('========================== LS SUMMARY ==========================')
            print('Initial fleet size: %i'%initK)
            print('New fleet size:     %i'%finalK)
            print('----------------------------------------------------------------')
            print('Fleet reduction:    %i (%.2f)'%(fleetSave, fleetSaveFrac))
            print('')
            print('Initial cost:       %i'%initZ)
            print('New cost:           %i'%finalZ)
            print('----------------------------------------------------------------')
            print('Cost reduction:     %i (%.4f)'%(costSave, costSaveFrac))
            print('')
            print('Exec time (sec):    %.4f'%self.executionTime)
            print('# Iterations:       %i \t (per iteration: %.4f)'%(self._nCompoundMoves, self.executionTime/max([1, self._nCompoundMoves])))
            print('# Moves:            %i \t (per move:      %.4f)'%(self._nMoves, self.executionTime/max([1, self._nMoves])))
            print('================================================================\n')
    
class TabuFunctions():
    '''
    '''
    
    def __init__(self, info):
        self.info = info
        self._tabuListMove = [0]*len(info.d)
        self._tabuListCompound = [0]*len(info.d)
        self._nMoves = 0
        self._nCompoundMoves = 0
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self.tabuTenure = 5
        self.compoundTabuList = True
        
        self._incZ = 1e3000000
        self._incZ_k = 1e3000000
        self._incK = 1e3000000
        self._incK_z = 1e3000000
        self._incZ_nM = []
        self._incZ_nCM = []
        self._incK_nM = []
        self._incK_nCM = []
        self._incZsol = {}
        self._incKsol = {}
    
    def resetTabuFunctions(self):
        self._tabuListMove = [0]*len(self.info.d)
        self._tabuListCompound = [0]*len(self.info.d)
        self._nMoves = 0
        self._nCompoundMoves = 0   
        self._incZ_nM += [0]
        self._incZ_nCM += [0]
        self._incK_nM += [0]
        self._incK_nCM += [0]     
    
    def setTabuInfo(self, nMoves = None, nCompoundMoves = None):
        if nMoves != None: self._nMoves = nMoves
        if nCompoundMoves != None: self._nCompoundMoves = nCompoundMoves
        
    def setTabuSettings(self, tabuTenure = None, compoundMoves = None):
        if tabuTenure: self._tabuTenure = tabuTenure
        if compoundMoves: self.compoundTabuList = compoundMoves
    
    def _checkTabuListMove(self, arc):
        moveFeasible = self._tabuListMove[arc] <= self._nMoves
        return(moveFeasible)
        
    def _checkTabuListCompoundMove(self, arc):
        moveFeasible = self._tabuListCompound[arc] <= self._nCompoundMoves
        return(moveFeasible)
    
    def _checkTabuList(self, arc):
        if self.compoundTabuList:
            feasible = self._checkTabuListCompoundMove(arc)
        else:
            feasible = self._checkTabuListMove(arc)
        return(feasible)       
    
    def checkMoveNotTabu(self, moveInfo):
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        if moveCost < 0:  return(True)
        
        if moveType == 'doubleRelocate':
            feasible = self._checkTabuList(arcI) and self._checkTabuList(postArcJ)
        else:
            feasible = self._checkTabuList(arcI)
        
        if not feasible: return(False)
        
        if moveType == 'exchange' or moveType == 'cross' or moveType == 'relocate' or moveType == 'doubleRelocate':
            feasible = self._checkTabuList(arcJ)
        return(feasible)
        
    def _updateTabuListMove(self, arc):

        self._tabuListMove[arc] = self._nMoves + self.tabuTenure
        if arc in self._edgesS: self._tabuListMove[self._inv[arc]] = self._nMoves + self.tabuTenure
        
    def _updateTabuListCompoundMove(self, arc):
        self._tabuListCompound[arc] = self._nCompoundMoves  + self.tabuTenure
        if arc in self._edgesS: self._tabuListCompound[self._inv[arc]] = self._nCompoundMoves + self.tabuTenure
        
    def updateTabuList(self, moveInfo):
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        
        if moveType == 'doubleRelocate':
            self._updateTabuListMove(arcI)
            self._updateTabuListCompoundMove(arcI)          
            self._updateTabuListMove(postArcJ)
            self._updateTabuListCompoundMove(postArcJ)        
        else:
            self._updateTabuListMove(arcI)
            self._updateTabuListCompoundMove(arcI)
        if moveType == 'exchange' or moveType == 'cross' or moveType == 'relocate':# or moveType == 'relocate':
            self._updateTabuListMove(arcJ)
            self._updateTabuListCompoundMove(arcJ)
            
    def checkAspirationCriteria(self, savings, solution):
        
        compoundCriteria = CompoundMoveFunctions(self.info)
        possibleSaving = 0
        for moveInfo in savings:
            if moveInfo[0] >= 0: break
            feasible = compoundCriteria.checkCompoundMoveFeasibility(moveInfo)
            if feasible:
                possibleSaving += moveInfo[0]
                compoundCriteria.addMoveInfluence(moveInfo)
        possibleNewIncumbent =  solution['TotalCost'] + possibleSaving < self._incZ
        return(possibleNewIncumbent)

    def resetIncumbentInfo(self):
        self._incZ = 1e3000000
        self._incZ_k = 1e3000000
        self._incK = 1e3000000
        self._incK_z = 1e3000000
        self._incZ_nM = []
        self._incZ_nCM = []
        self._incK_nM = []
        self._incK_nCM = []
        self._incZsol = {}
        self._incKsol = {}
    
    def checkIncumbent(self, solution):
        newIncumbent = False
        newZ = solution['TotalCost'] < self._incZ
        newK = solution['nVehicles'] < self._incK
        matchZ = solution['TotalCost'] == self._incZ
        matchK = solution['nVehicles'] == self._incK
        newZminK = solution['nVehicles'] < self._incZ_k 
        newKminZ = solution['TotalCost'] < self._incK_z
        
#         if newZ or (matchZ and newZminK):
#             newIncumbent = True
#             self._incZ = solution['TotalCost']
#             self._incZ_k = solution['nVehicles']
#             self._incZsol = deepcopy(solution)
#             self._incZ_nM += [self._nMoves]
#             self._incZ_nCM += [self._nCompoundMoves]
        if newK or (matchK and newKminZ):
            newIncumbent = True
            self._incK = solution['nVehicles']
            self._incK_z = solution['TotalCost']
            self._incKsol = deepcopy(solution)
            self._incK_nM += [self._nMoves]
            self._incK_nCM += [self._nCompoundMoves]
        return(newIncumbent)
    
    def returnIncumbentCopy(self):
        return(deepcopy(self._incZsol), deepcopy(self._incKsol))

import pickle
            
class TabuSearch_MCARPTIF(object):
    
    def __init__(self, info, nn_list, testAll = True):
        self.info = info
        self._LSfun = LS_MCARPTIF(info, nn_list, testAll = testAll)
        self._TSfun = TabuFunctions(info)
        self.tabuThreshold = 1
        self.improveThreshold = 0
        self._movesNotUsed = []
        self._testAll = testAll
        self._nMovesNoImprovement = 1e300000
        self._printOutput = False
        self.saveOutput = False
        self.nnFrac = 1
        self._LSfun.nnFrac = self.nnFrac
        self.tabuMoveLimit = 0.1
        self.tabuTenure =  5
        self.timeStepOutput = []
        self.timeStepSave = 60
        self.useAspirations = False
        self.saveSolution = False
        self.suppressOutput = False
        
    def setOutputString(self, problemSet, initial, experimentName, experimentNumber, outputFile):
        self.saveOutput = True
        self.outputFile = outputFile
        tenure = self.tabuTenure
        stringInfo = (experimentName, experimentNumber, problemSet, self.info.name, initial, self.nnFrac, self.tabuThreshold, tenure)
        self.heading = 'ExpName,ExpNumber,Problem,Set,Instance,Construct,NNL,moveThreshold,TabuTenure,conZ,conK,lsZ,lsK,t,i\n'
        self.outputLine = '%s,%i,MCARPTIF,%s,%s,%s,%.2f,%i,%i,'%stringInfo
        
        if not os.path.isfile(outputFile):
            outF = open(self.outputFile, 'w')
            outF.write(self.heading)
            outF.close()
        
    def writeOutput(self, solution):
        if self.saveOutput:
            outString = '%i,%i,%i,%i,%.4f,%i\n'%(self._initialCost, self._initialK, solution['TotalCost'], solution['nVehicles'], self.totalTime, self._TSfun._nCompoundMoves)
            outString = self.outputLine + outString
            outputF = open(self.outputFile, 'a')
            outputF.write(outString)
            outputF.close()
        if self.saveSolution:
            outF = open(self.saveSolutionFile, 'w')
            cPickle.dump(solution, outF)
            outF.close()

    def setMovesToUse(self, movesToUse = None):
        
        if movesToUse == None:
            movesToUse = ['flip', 
                          'cross', 
                          'exchange', 
                          'relocate', 
                          'relocatePreIF', 
                          'relocatePostIF']
            
        self.movesToUse = movesToUse

    def setTabuSearchParameters(self, compoundMoves = True, newCompoundMoves = False, 
                                 tabuTenure = 5, tabuThreshold = 1, nnFrac = 0.1, 
                                 tabuMoveLimit = 1000, maxNonImprovingMoves = 50,
                                 saveOutput = False, movesToUse = False, useAspiration = True, saveSolution = False, saveSolutionFile = ''):
        if compoundMoves:
            self._LSfun.comboMovesVN = True
            self._LSfun.comboFeasibleMoves = True
            self._LSfun.doubleCross = True
        else:
            self._LSfun.comboMovesVN = False
            self._LSfun.comboFeasibleMoves = False
            self._LSfun.doubleCross = False
            
        if newCompoundMoves:
            self._LSfun.newComboMovesVN = True
            self._LSfun.newCompoundMoves = True
            self._LSfun.newCandidateMoves = True
        else:
            self._LSfun.newComboMovesVN = False
            self._LSfun.newCompoundMoves = False
            self._LSfun.newCandidateMoves = False
        
        self.tabuTenure =  tabuTenure
        self.tabuMoveLimit = tabuMoveLimit
        self.tabuThreshold = tabuThreshold
        self.nnFrac = nnFrac
        self._nMovesNoImprovement = maxNonImprovingMoves 
        self._useAspiration = useAspiration
        
        self.saveOutput = saveOutput
        
        self.saveSolution = saveSolution
        self.saveSolutionFile = saveSolutionFile
        
        if movesToUse:
            self._LSfun._MoveCosts.setMovesToUse(movesToUse)
        
    def _initiateTabuSearch(self):
        self._TSfun.resetIncumbentInfo()
        self._LSfun.resetLocalSearchFunctions()
        self._TSfun.resetTabuFunctions()
        self._LSfun.compoundMoves = True
        self._LSfun.candidateMoves = True
        self.candidateMoves = True
        self._TSfun.compoundTabuList = True
        self._LSfun.setScreenPrint(printMoves = self._printOutput)
        self._LSfun.thresholdUse = self.tabuThreshold
        self._LSfun.nnFrac = self.nnFrac
        self._TSfun.tabuTenure = self.tabuTenure

    def _makeTabuFeasibleCompoundMoves(self, savings, solution):
        '''
        Find the best feasible move
        '''
        self._LSfun._movesNotUsed = []
        self._LSfun._MovesCompound.resetMoveInfluencers()
        self._LSfun._MovesFeasible.restartFeasibility()
        self._LSfun.threshold = self.tabuThreshold
        self._LSfun._MovesMaker.setSolution(solution)
        self._LSfun._MovesMaker.setSearchPhase('Tabu phase moves')
        feasibleMove = False
        
        tabuMoves = 0
        for iMove, moveInfo in enumerate(savings):
            compoundFeasible = self._LSfun._MovesCompound.checkCompoundMoveFeasibility(moveInfo)
            if not compoundFeasible: continue
            
            feasible = self._TSfun.checkMoveNotTabu(moveInfo)
            
            if feasible:
                solutionMapping = self._LSfun._MovesMaker.solutionMapping
                (feasible, solution) = self._LSfun._MovesFeasible.checkMoveFeasibility(moveInfo, solutionMapping, solution)[:2]
                if feasible.find('feasible') != -1: feasible = True
                else: feasible = False
                
            if not feasible or moveInfo[0] >= self.tabuThreshold:
                self._LSfun._movesNotUsed.append(moveInfo)
                continue

            feasibleMove = True

            self._LSfun._MovesCompound.addMoveInfluence(moveInfo)
            self._TSfun.updateTabuList(moveInfo)
            (solution, extraInfo) = self._LSfun._MovesMaker.makeMove(moveInfo, solution)
            
            if extraInfo == "TripMove":
                self._LSfun._MovesCompound.addCrossMoveInfluence(moveInfo, solution, solutionMapping)
            
            self._TSfun._nMoves += 1
            tabuMoves += 1
            if self._testAll: self._LSfun._testMoves._testSolution(solution)
            if tabuMoves >= self.tabuMoveLimit:
                self._LSfun._movesNotUsed += savings[iMove + 1:]
                break
                
        return(feasibleMove, solution)
    
    def _makeBestMoves(self, savings, originalSolution):
        
        #print('Aspiration criteria')
        solution = deepcopy(originalSolution)    
        self._LSfun.threshold = self.improveThreshold    
        
        self._LSfun._nCompoundMoves = 0
        self._LSfun._nMoves = 0
        (solution, reducedFleet) = self._LSfun.compoundLocalSearch(solution)
        newincumbent = self._TSfun.checkIncumbent(solution)
        
        if newincumbent or reducedFleet:
            self._LSfun._nMoves += self._TSfun._nMoves
            self._LSfun._nCompoundMoves = self._TSfun._nCompoundMoves
            #print('New incumbent')
            self.writeOutput(solution)
            return(True, solution, reducedFleet)
        else:
            #print('Aspiration failed\n')
            self._LSfun._nCompoundMoves = self._TSfun._nCompoundMoves
            self._LSfun._nMoves = self._TSfun._nMoves
            return(False, originalSolution, reducedFleet)
        
    def _makeTabuMoves(self, savings, solution):
        
        self._LSfun._movesNotUsed = []
        self._LSfun._MovesCompound.resetMoveInfluencers()
        self._LSfun._MovesFeasible.restartFeasibility()
        self._LSfun.threshold = self.tabuThreshold
        
        feasibleMoves = []
        
        (feasibleMove, solution) = self._makeTabuFeasibleCompoundMoves(savings, solution)
        feasibleMoves.append(feasibleMove)
        moveMade = True in feasibleMoves
        if moveMade:
            self._TSfun.checkIncumbent(solution)

        return(moveMade, solution)
    
    def moveSearch(self, solution, tLimit, timeStart, moveLimit):

        solution = addMCARPcumulativeSolution(self.info, solution)
        candidateSearch = False
        reducedFleet = False
        tprint = clock()
        i = 0
        while (self.totalTime < tLimit) and (i < moveLimit) and (self.nMovesSinceInc < self._nMovesNoImprovement):     
            i += 1  
            tpassedprint = clock() - tprint
            if tpassedprint > 0.5:
                p = True
                tprint = clock()
            else:
                p = False
            
            #print('')            

            if self._testAll: self._LSfun._testMoves._testSolution(solution)

            self._TSfun._nCompoundMoves += 1
            
            self.nMovesSinceInc = self._TSfun._nCompoundMoves - self._TSfun._incK_nCM[-1]
            
            savings = self._LSfun._calculateMoveCosts(solution, candidateSearch)
            savings.sort(key=lambda x: x if isinstance(x, str) else "")
            candidateSearch = self.candidateMoves
            self.totalTime = clock() - timeStart       
            
            if self._useAspiration:
                asspiration = self._TSfun.checkAspirationCriteria(savings, solution)
            else:
                asspiration = False
            
            if asspiration:
                (moveMade, solution, reducedFleet) = self._makeBestMoves(savings, solution)
            else:
                moveMade = False
                
            if not moveMade:
                reducedFleet = False
                (moveMade, solution) = self._makeTabuMoves(savings, solution)
                self._TSfun.checkIncumbent(solution)
            
            if not moveMade: 
                continue
            else:
                self._solutionChange = solution['TotalCost'] - self._previousCost
                self._previousCost = solution['TotalCost']
                if p: 
                    if not self.suppressOutput:
                        print('I: %i \t Saving: %i \t # Moves %i \t Inc: %i \t nMoves Inc: %i/%i \t Time: %.4f \t {NN, tau} = {%.2f,%i} '%(self._TSfun._nCompoundMoves, self._solutionChange, self._TSfun._nMoves, self._TSfun._incK_z, self.nMovesSinceInc, self._nMovesNoImprovement, self.totalTime, self.nnFrac, self.tabuTenure))
            
            if reducedFleet: break
        self.writeOutput(self._TSfun._incKsol)
        return(solution, reducedFleet)

    def compoundTabuSearch(self, solution, tLimit, moveLimit):
        
        self._previousCost = solution['TotalCost']
        self._initialCost = self._previousCost
        self._initialK = solution['nVehicles']
        self._TSfun.checkIncumbent(solution)
        timeStart = clock()
        self.totalTime = 0
        self.nMovesSinceInc = 0
        self.writeOutput(solution)        
    
        while True:
            self._initiateTabuSearch()
            (solution, reducedFleet) = self.moveSearch(solution, tLimit, timeStart, moveLimit)
            if not reducedFleet: break
        
        if not self.suppressOutput:
            print('\nInitial and incumbent cost: %i \t %i'%(self._TSfun._incK_z, self._initialCost))
            print('Initial and incumbent fleet size: %i \t %i\n'%(self._TSfun._incK, self._initialK))
        
    def tabuSearch(self, solution, tLimit = 1e300000, moveLimit = 1e300000):
        #
        #self._initiateTabuSearch()
        solution = self.compoundTabuSearch(solution, tLimit, moveLimit)
        self._LSfun._MoveCosts.freeInputValues()
        return(deepcopy(self._TSfun._incKsol))


    def clearCythonModules(self):
        self._LSfun._MoveCosts.freeInputValues()
        
        
    def improveSolution(self, solution):
        #
        self._initiateTabuSearch()
        solution = self.compoundTabuSearch(solution, tLimit = 1e300000, moveLimit = 1e300000)
        return(deepcopy(self._TSfun._incKsol)) 


    def returnStatsFormat(self, pSet, initial, nSol, initTime):
        canList = 'FALSE'
        compoundMove = 'True'
            
        moveStrategy = 'FALSE'
        
        pType = 'MCARPTIF'
        outputLineInfo = (pSet, self.info.name, pType, self.nnFrac, canList, compoundMove, self._initialK, self._initialCost, self._TSfun._incK, self._TSfun._incK_z, self.totalTime, self._TSfun._nMoves, self._TSfun._nCompoundMoves, moveStrategy, initial, nSol, initTime)
        #print(outputLineInfo)
        outputLineStr = '%s,%s,%s,%.2f,%s,%s,%i,%i,%i,%i,%.4f,%i,%i,%s,%s,%i,%.8f\n'%outputLineInfo
        return(outputLineStr)
        
        