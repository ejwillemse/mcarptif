'''
Created on 11 Jun 2015

@author: eliaswillemse

Class to implement Local Search for the Mixed Capacitated Arc Routing Problem.
'''

from __future__ import division

import pprint as pp
import os
import sysPath
import sys
sys = sysPath.addInputPaths(sys)
mainPath = sysPath.returnPath()

import random
import calcMoveCost
import py_display_solution
from copy import deepcopy
import pickle
from time import clock

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
        self._service = info.serveCostL
        self._capacity = info.capacity
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
        
    def _testSolution(self, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        totalCost = 0
        errorsFound = False
        arcsNotService = self._reqArcsSet.copy()
        for i in range(solution['nVehicles']):
            routeI = solution[i]['Route']
            demand = sum([self._demand[arc] for arc in routeI])
            serviceCost = sum([self._service[arc] for arc in routeI])
            deadheadCost = sum([self._d[routeI[j]][routeI[j+1]] for j in range(len(routeI)-1)]) + self._dumpCost
            if demand != solution[i]['Load']:
                errorsFound = True
                print('ERROR: Incorrect route load specified for route %i: actual %i vs %i'%(i, demand, solution[i]['Load']))
            if demand > self._capacity:
                errorsFound = True 
                print('ERROR: Route demand exceeds capacity for route %i: actual %i vs %i'%(i, demand, self._capacity))
            if serviceCost + deadheadCost != solution[i]['Cost']:
                errorsFound = True
                print('ERROR: Incorrect route cost specified for route %i: actual %i vs %i'%(i, serviceCost + deadheadCost, solution[i]['Cost']))
            totalCost += serviceCost + deadheadCost
            if routeI[0] != self._depot:
                errorsFound = True
                print('ERROR: First arc not the depot in route %i: %i'%(i, routeI[0]))
            if routeI[-1] != self._depot:
                errorsFound = True
                print('ERROR: Last arc not the depot in route %i: %i'%(i, routeI[-1]))                        
            for arc in routeI[1:-1]:
                if arc not in arcsNotService:
                    errorsFound = True
                    print('ERROR: Arc does not have to be serviced in route %i: %i'%(i, arc))
                else:
                    arcsNotService.remove(arc)
                    if arc in self._edgesS:
                        arcsNotService.remove(self._inv[arc])
                        
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
            print('Previous solution',self._prevSolution)
            print('Current solution ',solution)
            raise NameError('Errors found with solution above, please see comments above solution.')            
        
        self._prevSolution = deepcopy(solution)
        
    def _testRelocateMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        errorsFound = False
        
        if moveType != 'relocate': 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (relocate).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, removePos) = solutionMapping[arcI]
        preArc = solution[routeI]['Route'][removePos - 1]
        arc = solution[routeI]['Route'][removePos]
        postArc = solution[routeI]['Route'][removePos + 1]
        actualMoveCostsI = self._d[preArc][postArc] - (self._d[preArc][arc] + self._d[arc][postArc])
        
        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to remove not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print(solution[routeI]['Route'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Route'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Route'])
                    
        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated remove move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Route'])
            
        (routeJ, insertPos) = solutionMapping[arcJ]
        preArc = solution[routeJ]['Route'][insertPos - 1]
        arc = solution[routeJ]['Route'][insertPos]
        actuaMoveCostsJ = self._d[preArc][arcI] + self._d[arcI][arc]- self._d[preArc][arc]

        if arcJ != arc:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print(solution[routeJ]['Route'])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print(solution[routeJ]['Route'])
        
        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated insert move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Route'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Route'])
            print(solution[routeJ]['Route'])
                   
        if errorsFound:
            print(solution)
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
            
        (routeI, removePos) = solutionMapping[arcI1]
        preArc = solution[routeI]['Route'][removePos - 1]
        arc1 = solution[routeI]['Route'][removePos]
        arc2 = solution[routeI]['Route'][removePos + 1]
        postArc = solution[routeI]['Route'][removePos + 2]
        actualMoveCostsI = self._d[preArc][postArc] - (self._d[preArc][arc1] + self._d[arc2][postArc])
        
        if arcI1 != arc1 or arcI2 != arc2:
            errorsFound = True
            print('ERROR: Arc to remove not the same as the one currently in the route position %i: actual %i, %i vs %i, %i'%(routeI, arc1, arcI1, arc2, arcI2))
            print(solution[routeI]['Route'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Route'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Route'])
                    
        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated remove move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Route'])
            
        (routeJ, insertPos) = solutionMapping[arcJ]
        preArc = solution[routeJ]['Route'][insertPos - 1]
        arc = solution[routeJ]['Route'][insertPos]
        actuaMoveCostsJ = self._d[preArc][arcI1] + self._d[arcI2][arc]- self._d[preArc][arc]

        if arcJ != arc:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print(solution[routeJ]['Route'])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print(solution[routeJ]['Route'])
        
        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated insert move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Route'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Route'])
            print(solution[routeJ]['Route'])
                   
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
        
        if moveType != 'exchange': 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (relocate).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, removePos) = solutionMapping[arcI]

        preArc = solution[routeI]['Route'][removePos - 1]
        arc = solution[routeI]['Route'][removePos]
        postArc = solution[routeI]['Route'][removePos + 1]
        actualMoveCostsI = self._d[preArc][arcJ] + self._d[arcJ][postArc]  - (self._d[preArc][arc] + self._d[arc][postArc])

        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to exchange not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print(solution[routeI]['Route'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before exchange arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Route'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after exchange arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Route'])

        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated exchange move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Route'])
            
        (routeJ, removePos) = solutionMapping[arcJ]

        preArc = solution[routeJ]['Route'][removePos - 1]
        arc = solution[routeJ]['Route'][removePos]
        postArc = solution[routeJ]['Route'][removePos + 1]
        actuaMoveCostsJ = self._d[preArc][arcI] + self._d[arcI][postArc]  - (self._d[preArc][arc] + self._d[arc][postArc])
        
        if arcJ != arc and self._inv[arcJ] != arc:
            errorsFound = True
            print('ERROR: Arc to exchange not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print(solution[routeJ]['Route'])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before exchange not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print(solution[routeJ]['Route'])
            
        if postArc != postArcJ:
            errorsFound = True
            print('ERROR: Arc now after exchange not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, postArc, postArcJ))
            print(solution[routeJ]['Route'])

        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated exchange move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Route'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Route'])
            print(solution[routeJ]['Route'])
                        
        if errorsFound:
            print(solution)
            print(moveInfo)
            raise NameError('Errors found with move to solution above, please see comments above solution.')   

    def _testFlipMove(self, moveInfo, solutionMapping, solution):
        '''
        Test if solution is feasible and if route values are accurate.
        '''
        (flipCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI)) = moveInfo
        errorsFound = False
        
        if moveType != 'flip': 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (flip).'%moveType)

        if arcI not in self._edgesS: 
            errorsFound = True
            print('ERROR: Arc does not have an inverse: %i'%(arcI))
        
        (routeI, removePos) = solutionMapping[arcI]
        
        preArc = solution[routeI]['Route'][removePos - 1]
        arc = solution[routeI]['Route'][removePos]
        postArc = solution[routeI]['Route'][removePos + 1]
        actualMoveCostsI = self._d[preArc][self._inv[arc]] + self._d[self._inv[arc]][postArc]  - (self._d[preArc][arc] + self._d[arc][postArc])

        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to flip not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print(solution[routeI]['Route'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before flip arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Route'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after flip arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Route'])

        if actualMoveCostsI != flipCost: 
            errorsFound = True
            print('ERROR: Calculated flip move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, flipCost))
      
        if errorsFound:
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
            
        (routeI, removePos) = solutionMapping[arcI]

        preArc = solution[routeI]['Route'][removePos - 1]
        arc = solution[routeI]['Route'][removePos]
        postArc = solution[routeI]['Route'][removePos + 1]
        actualMoveCostsI = self._d[preArc][postArc] - (self._d[preArc][arc] + self._d[arc][postArc])

        if arcI != arc and self._inv[arcI] != arc:
            errorsFound = True
            print('ERROR: Arc to remove not the same as the one currently in the route position %i: actual %i vs %i'%(routeI, arc, arcI))
            print(solution[routeI]['Route'])            
        
        if preArc != preArcI:
            errorsFound = True
            print('ERROR: Arc now before remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, preArc, preArcI))
            print(solution[routeI]['Route'])
 
        if postArc != postArcI:
            errorsFound = True
            print('ERROR: Arc now after remove arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeI, postArc, postArcI))
            print(solution[routeI]['Route'])

        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated remove move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Route'])
            
        (routeJ, insertPos) = solutionMapping[preArcJ]
        preArc = solution[routeJ]['Route'][insertPos]
        arc = solution[routeJ]['Route'][insertPos + 1]
        actuaMoveCostsJ = self._d[preArc][arcI] + self._d[arcI][arc] - self._d[preArc][arc]

        if arcJ != arc:
            errorsFound = True
            print('ERROR: Arc to insert at not the same as the one currently in the route position %i: actual %i vs %i'%(routeJ, arc, arcJ))
            print(solution[routeJ]['Route'])  
 
        if preArc != preArcJ:
            errorsFound = True
            print('ERROR: Arc now before insert at arc not the one used for calculating move cost in route %i: actual %i vs %i'%(routeJ, preArc, preArcJ))
            print(solution[routeJ]['Route'])

        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated insert move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
            print(solution[routeJ]['Route'])
            
        if actualMoveCostsI + actuaMoveCostsJ != relocateCost:
            errorsFound = True
            print('ERROR: Actual cost change per route not the same as solution cost change: %i + %i != %i'%(actualMoveCostsI, actuaMoveCostsJ, relocateCost))
            print(solution[routeI]['Route'])
            print(solution[routeJ]['Route'])
             
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
        
        if moveType != 'cross': 
            errorsFound = True
            print('ERROR: Incorrect move test (%s) for this kind of move (cross).'%moveType)

        if relocateCost != moveCostsI + moveCostsJ: 
            errorsFound = True
            print('ERROR: Cost change per route not the same as solution cost change: %i + %i != %i'%(moveCostsI, moveCostsJ, relocateCost))
            
        (routeI, removePos1) = solutionMapping[arcI]
        (routeJ, removePos2) = solutionMapping[arcJ]

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
        
        if actualMoveCostsI != moveCostsI: 
            errorsFound = True
            print('ERROR: Calculated cross move cost not the same as given for route %i: actual %i vs %i'%(routeI, actualMoveCostsI, moveCostsI))
            print(solution[routeI]['Route'])
            
        actuaMoveCostsJ = self._d[preArc2][arc1] - self._d[preArc2][arc2]
      
        if actuaMoveCostsJ != moveCostsJ: 
            errorsFound = True
            print('ERROR: Calculated cross move cost not the same as given for route %i: actual %i vs %i'%(routeJ, actuaMoveCostsJ, moveCostsJ))
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

def genMCARPcumulativeRoute(info, route):
    _demand = info.demandL
    _servCost = info.serveCostL
    _d = info.d
    _dumpCost = info.dumpCost
    loads = [_demand[arc] for arc in route]
    costs = [_servCost[arc] for arc in route]
    cumLoad = [loads[0]]
    cumServe = [costs[0]]
    for i in range(1, len(loads)):
        lValue = cumLoad[i - 1] + loads[i]
        cumLoad.append(lValue)
        sValue = cumServe[i - 1] + _d[route[i - 1]][route[i]] + costs[i]
        cumServe.append(sValue)
    cumServe[-1] += _dumpCost
    return(cumLoad, cumServe)

def updateMCARPcumulitiveSolution(info, solution, routeI):
    (solution[routeI]['CumLoad'], solution[routeI]['CumServe']) = genMCARPcumulativeRoute(info, solution[routeI]['Route'])
    solution[routeI]['CumUpdate'] = True
    return(solution)

def addMCARPcumulativeSolution(info, solution):
    '''
    Generates the cumulative load and cost at an arc position in a route.
    '''
    for i in range(solution['nVehicles']):
        route = solution[i]['Route']
        (solution[i]['CumLoad'], solution[i]['CumServe']) = genMCARPcumulativeRoute(info, route)
        solution[i]['CumUpdate'] = True
    return(solution)

def printMove(moveInfo, routeI, posI, routeJ, posJ, tCost, _searchPhase = 'Unknown'):
    '''
    Print basic info of relocate move
    '''
    if moveInfo[2] == 'relocate':
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Relocate arc %i (%i, %i) before arc %i (%i, %i) \t %s'%(tCost, relocateCost, arcI, routeI, posI, arcJ, routeJ, posJ, _searchPhase))
    if moveInfo[2] == 'doubleRelocate':
        (relocateCost, (arcIa, preArcI, postArcI, arcJ, preArcJ, arcIb), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Double relocate arcs %i and %i (%i, %i) before arc %i (%i, %i) \t %s'%(tCost, relocateCost, arcIa, arcIb, routeI, posI, arcJ, routeJ, posJ, _searchPhase))
    if moveInfo[2] == 'exchange':
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Exchange arc %i (%i, %i) with arc %i (%i, %i) \t %s'%(tCost, relocateCost, arcI, routeI, posI, arcJ, routeJ, posJ, _searchPhase))
    if moveInfo[2] == 'flip':
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI)) = moveInfo
        print('Z: %i \t Savings: %i \t Flip arc %i (%i, %i) \t %s'%(tCost, relocateCost, arcI, routeI, posI, _searchPhase))
    if moveInfo[2] == 'relocateBeforeDummy':
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Relocate arc %i (%i, %i) after arc to end of route %i (%i, %i) \t %s'%(tCost, relocateCost, arcI, routeI, posI, arcJ, routeJ, posJ, _searchPhase))
    if moveInfo[2] == 'cross':
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Cross arc %i (%i, %i) to end with arc %i (%i, %i) to end \t %s'%(tCost, relocateCost, arcI, routeI, posI, arcJ, routeJ, posJ, _searchPhase))
    if moveInfo[2] == 'crossAtDummy':
        (relocateCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = moveInfo
        print('Z: %i \t Savings: %i \t Cross arc %i (%i, %i) to end with arc %i (%i, %i) to dummy \t %s'%(tCost, relocateCost, arcI, routeI, posI, arcJ, routeJ, posJ, _searchPhase))


class CalcMoveCosts(object):
    '''
    '''
    def __init__(self, info, nnList, cModules = True, autoInvCosts = False):
        self._info = info
        self._MoveCosts = calcMoveCost.CalcMoveCosts(info, cModules = cModules, nnList = nnList)
        self._MoveCosts.autoInvCosts = autoInvCosts
        self.autoInvCosts = autoInvCosts
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self._info._edgesS = set(self._edgesL)
        
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
        
        self.movesToUse = ['relocate',
                          'exchange',
                          'cross',
                          'relocateBeforeDummy',
                          'crossAtDummy',
                          'doubleCross',
                          'flip',
                          'doubleRelocate']
        
    def setMovesToUse(self, movesToUse = None):
        
        if movesToUse == None:
            movesToUse = ['relocate',
                          'exchange',
                          'cross',
                          'relocateBeforeDummy',
                          'crossAtDummy',
                          'doubleCross',
                          'flip',
                          'doubleRelocate']
            
        self.movesToUse = movesToUse
        
    def setInputDefaults(self, threshold = None, nnFrac = None):
        if threshold: self.threshold = threshold
        else: self.threshold = 0
        if nnFrac: self.nnFrac = nnFrac
        else:self.nnFrac = None
        self.thresholdUse = self.threshold
        self.nnFracUse = self.nnFrac
        self._MoveCosts.initiateCmodules()
    
    def setInputValues(self, threshold = None, nnFrac = None):
        if threshold: self.thresholdUse = threshold
        else: self.thresholdUse = self.threshold
        if nnFrac: self.nnFracUse = nnFrac
        else:self.nnFracUse = self.nnFrac
    
    def freeInputValues(self):
        self._MoveCosts.freeCmodules()
    
    def setSolution(self, solution):
        self._solution = solution
        (giantRoute, self._solutionArcs, self._dummyArcPositions, self._endArcs) = self._genMCARPgiantRouteMapping(solution)
        self._MoveCosts.setRoute(giantRoute)
        self._setNonAdjacentArcs()
        
    def freeSolution(self):
        self._MoveCosts.freeRoute()
        
    def terminateSearch(self):
        self.freeInputValues()
        self.freeSolution
        
    def _genMCARPgiantRouteMapping(self, solution):
        '''
        Takes an initial solution and generates a giant route with the necessary giant route arc position mapping. 
        '''
        solutionArcs = set()
        giantRoute = [self._depot] # Giant route starts with depot.        
        dummyArcPositions = [0]
        k = 0
        endArcs = set()
        for i in range(solution['nVehicles']):
            route = solution[i]['Route']
            for arc in route[1:]: # Each route consists of a start and end depot visit, with only one needed in the giant route.
                k += 1
                giantRoute.append(arc)
                if arc != self._depot: solutionArcs.add(arc) # Used to identify specific arc orientations.
            dummyArcPositions.append(k) # Last arc added in a route is the dummy arc.
            endArcs.add(route[-2])
        return(giantRoute, solutionArcs, dummyArcPositions, endArcs)
    
    def calcRelocateMoves(self, relocateCandidates = None, insertCandidates = None, dummyArcPositions = None):

        if relocateCandidates == None:
            if not self.autoInvCosts: 
                relocateCandidates = self._relocateCandidates
            else:
                relocateCandidates = self._solutionArcs
        
        if insertCandidates == None: 
            insertCandidates = self._solutionArcs

        savings = []
        
        if 'relocate' in self.movesToUse:
            
            if self.nonAdjacentRestrictionInsert:
                insertCandidates = insertCandidates.intersection(self.nonAdjacentInsertArcs)
            
            savings += self._MoveCosts.relocateMoves(relocateCandidates, insertCandidates, threshold = self.thresholdUse, nNearest = self.nnFracUse)

        return(savings)  

    def calcDoubleRelocateMoves(self, relocateCandidates = None, insertCandidates = None, dummyArcPositions = None):

        if relocateCandidates == None:
            #if not self.autoInvCosts: 
            #    relocateCandidates = self._relocateCandidates
            #else:
            relocateCandidates = self._solutionArcs.difference(self._endArcs)
        
        if insertCandidates == None: 
            insertCandidates = self._solutionArcs

        savings = []
        if 'doubleRelocate' in self.movesToUse:
            
            if self.nonAdjacentRestrictionInsert:
                insertCandidates = insertCandidates.intersection(self.nonAdjacentInsertArcs)
            
            savings += self._MoveCosts.doubleRelocateMoves(relocateCandidates, insertCandidates, threshold = self.thresholdUse, nNearest = self.nnFracUse)

        return(savings) 

    def calcRelocateBeforeDummyMoves(self, relocateCandidates = None, dummyArcPositions = None):  

        if relocateCandidates == None: 
            if not self.autoInvCosts: 
                relocateCandidates = self._relocateCandidates
            else:
                relocateCandidates = self._solutionArcs

        if dummyArcPositions == None: 
            dummyArcPositions = self._dummyArcPositions
            
        savings = []
        if 'relocateBeforeDummy' in self.movesToUse:
            savings += self._MoveCosts.relocateEndRouteMoves(relocateCandidates, dummyArcPositions, threshold = self.threshold, nNearest = self.nnFracUse)        
        
        return(savings)

    def calcExchangeMoves(self, exchangeCandidates1 = None, exchangeCandidates2 = None):

        if exchangeCandidates1 == None: 
            if not self.autoInvCosts: 
                exchangeCandidates1 = self._relocateCandidates
            else: 
                exchangeCandidates1 = self._solutionArcs
                
        if exchangeCandidates2 == None: 
            if not self.autoInvCosts: 
                exchangeCandidates2 = self._relocateCandidates
            else: 
                exchangeCandidates2 = self._solutionArcs

        savings = []
        if 'exchange' in self.movesToUse:
            
            if self.nonAdjacentRestrictionExchange:
                exchangeCandidates1 = exchangeCandidates1.intersection(self.nonAdjacentExchangeArcs)
                exchangeCandidates2 = exchangeCandidates2.intersection(self.nonAdjacentExchangeArcs)
            
            savings += self._MoveCosts.exchangeMoves(exchangeCandidates1, exchangeCandidates2, threshold = self.thresholdUse, nNearest = self.nnFracUse)
        
        return(savings)
    
    def calcCrossMoves(self, crossCandidates1 = None, crossCandidates2 = None):
        
        if crossCandidates1 == None: 
            crossCandidates1 = self._solutionArcs
            
        if crossCandidates2 == None: 
            crossCandidates2 = self._solutionArcs

        savings = []
        if 'cross' in self.movesToUse:
            
            if self.nonAdjacentRestrictionCross:
                crossCandidates1 = crossCandidates1.intersection(self.nonAdjacentInsertArcs)
                crossCandidates2 = crossCandidates2.intersection(self.nonAdjacentInsertArcs)
            
            savings += self._MoveCosts.crossMoves(crossCandidates1, crossCandidates2, threshold = self.thresholdUse, nNearest = self.nnFracUse)
            
        return(savings)
    
    def calcCrossAtDummyMoves(self, crossCandidates = None, dummyArcPositions = None):

        if crossCandidates == None: 
            crossCandidates = self._solutionArcs
            
        if dummyArcPositions == None: 
            dummyArcPositions = self._dummyArcPositions

        savings = []
        
        if 'crossAtDummy' in self.movesToUse:
            savings += self._MoveCosts.crossEndRouteMoves(crossCandidates, dummyArcPositions, threshold = self.thresholdUse, nNearest = self.nnFracUse)
        
        return(savings)    
    
    def calcFlipMoves(self, flipCandidates = None):

        if flipCandidates == None: 
            flipCandidates = self._solutionArcs

        savings = []
        if 'flip' in self.movesToUse:
            savings += self._MoveCosts.flipMoves(flipCandidates, threshold = self.thresholdUse)
            
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
        savings += self.calcRelocateBeforeDummyMoves()
        savings += self.calcExchangeMoves()        
        savings += self.calcCrossMoves()
        savings += self.calcCrossAtDummyMoves()
        savings += self.calcFlipMoves()
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

class MovesFeasibleMCARP(object):
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
        self.infeasibleMoves = []
        self.doubleCrossMove = []
        self.exceedThresholdRemoveInsert = []
        self.exceedThresholdDoubleCross = []
        self.threshold = 0
        
    def restartFeasibility(self):
        self.infeasibleMoves = []
        self.doubleCrossMove = []
        self.exceedThresholdRemoveInsert = []
        self.exceedThresholdDoubleCross = [] 
    
    def _relocateFeasibility(self, moveInfo, solutionMapping, solution):
        '''
        Determines if a relocate move is feasible. The move is feasible if the arc is relocated to the same route or if its relocate-to
        route has sufficient capacity.
        '''
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        if moveType != 'relocate' and moveType != 'relocateBeforeDummy': 
            raise NameError('Incorrect feasibility check (%s) for this kind of move (relocate).'%moveType)
        routeI = solutionMapping[arcI][0]
        if moveType == 'relocateBeforeDummy':
            routeJ = solutionMapping[preArcJ][0]
        else:
            routeJ = solutionMapping[arcJ][0]
        if routeI == routeJ:  
            deltaChangeRouteI = 0
            deltaChangeRouteJ = 0
        else:
            deltaChangeRouteI = -self._demand[arcI]
            deltaChangeRouteJ = self._demand[arcI] 
        excessI = solution[routeI]['Load'] + deltaChangeRouteI - self._capacity
        excessJ = solution[routeJ]['Load'] + deltaChangeRouteJ - self._capacity
        moveFeasible = excessI <= 0 and excessJ <= 0
        return(moveFeasible, deltaChangeRouteI, deltaChangeRouteJ)

    def _doubleRelocateFeasibility(self, moveInfo, solutionMapping, solution):
        '''
        Determines if a relocate move is feasible. The move is feasible if the arc is relocated to the same route or if its relocate-to
        route has sufficient capacity.
        '''
        (moveCost, (arcIa, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        arcIb = postArcJ
        if moveType != 'doubleRelocate': 
            raise NameError('Incorrect feasibility check (%s) for this kind of move (doubleRelocate).'%moveType)
        routeI = solutionMapping[arcIa][0]
        routeJ = solutionMapping[arcJ][0]
        if routeI == routeJ:  
            deltaChangeRouteI = 0
            deltaChangeRouteJ = 0
        else:
            deltaChangeRouteI = -(self._demand[arcIa] + self._demand[arcIb])
            deltaChangeRouteJ = self._demand[arcIa] + self._demand[arcIb]
        excessI = solution[routeI]['Load'] + deltaChangeRouteI - self._capacity
        excessJ = solution[routeJ]['Load'] + deltaChangeRouteJ - self._capacity
        moveFeasible = excessI <= 0 and excessJ <= 0
        return(moveFeasible, deltaChangeRouteI, deltaChangeRouteJ)

    def _exchangeFeasibility(self, moveInfo, solutionMapping, solution):
        '''
        Determines if a exchange move is feasible. The move is feasible if the new arc per route can be accomodated
        instead of the old one without exceeds available capacities.
        '''
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        if moveType != 'exchange': raise NameError('Incorrect feasibility check (%s) for this kind of move (exchange).'%moveType)
        
        routeI = solutionMapping[arcI][0]
        routeJ = solutionMapping[arcJ][0]
        if routeI == routeJ:  
            deltaChangeRouteI = 0
            deltaChangeRouteJ = 0
        else:
            deltaChangeRouteI = self._demand[arcJ] - self._demand[arcI]
            deltaChangeRouteJ = -deltaChangeRouteI
        excessI = solution[routeI]['Load'] + deltaChangeRouteI - self._capacity
        excessJ = solution[routeJ]['Load'] + deltaChangeRouteJ - self._capacity
        moveFeasible = excessI <= 0 and excessJ <= 0
        return(moveFeasible, deltaChangeRouteI, deltaChangeRouteJ)
    
    def _flipFeasibility(self, moveInfo, solutionMapping, solution):
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        if moveType != 'flip': raise NameError('Incorrect feasibility check (%s) for this kind of move (flip).'%moveType)
        return(True, 0, 0)

    def _crossFeasibility(self, moveInfo, solutionMapping, solution):
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        if moveType != 'cross': raise NameError('Incorrect feasibility check (%s) for this kind of move (cross).'%moveType)
        (routeI, posI) = solutionMapping[arcI]
        (routeJ, posJ) = solutionMapping[arcJ]
        
        if routeI == routeJ:
            moveFeasible = None
            deltaChangeRouteI = 0
            deltaChangeRouteJ = 0
        elif posI == 1 & posJ == 1:
            moveFeasible = False
            deltaChangeRouteI = 0
            deltaChangeRouteJ = 0            
        else:
            if not solution[routeI]['CumUpdate']:
                solution = updateMCARPcumulitiveSolution(self.info, solution, routeI)
            if not solution[routeJ]['CumUpdate']:
                solution = updateMCARPcumulitiveSolution(self.info, solution, routeJ)
            
            secIloadStart = solution[routeI]['CumLoad'][posI - 1]
            secIloadEnd  = solution[routeI]['CumLoad'][-1] - secIloadStart
            secJloadStart = solution[routeJ]['CumLoad'][posJ - 1]
            secJloadEnd = solution[routeJ]['CumLoad'][-1] - secJloadStart
            
            deltaChangeRouteI = secJloadEnd - secIloadEnd
            deltaChangeRouteJ = secIloadEnd - secJloadEnd
            
            excessI = solution[routeI]['Load'] + deltaChangeRouteI - self._capacity
            excessJ = solution[routeJ]['Load'] + deltaChangeRouteJ - self._capacity
            
            moveFeasible = excessI <= 0 and excessJ <= 0
        
        return(moveFeasible, deltaChangeRouteI, deltaChangeRouteJ, solution)

    def _crossEndFeasibility(self, moveInfo, solutionMapping, solution):
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        if moveType != 'crossAtDummy': raise NameError('Incorrect feasibility check (%s) for this kind of move (cross).'%moveType)
        (routeI, posI) = solutionMapping[arcI]
        if preArcJ not in solutionMapping:
            print('preArcsJ', preArcJ)
            for i in solution:
                print('Solutions',solution[i])
        
        (routeJ, posJ) = solutionMapping[preArcJ]
        posJ += 1
        
        if routeI == routeJ:
            moveFeasible = None
            deltaChangeRouteI = 0
            deltaChangeRouteJ = 0
        else:
            if not solution[routeI]['CumUpdate']:
                solution = updateMCARPcumulitiveSolution(self.info, solution, routeI)
            if not solution[routeJ]['CumUpdate']:
                solution = updateMCARPcumulitiveSolution(self.info, solution, routeJ)
            
            secIloadStart = solution[routeI]['CumLoad'][posI - 1]
            secIloadEnd  = solution[routeI]['CumLoad'][-1] - secIloadStart
            secJloadStart = solution[routeJ]['CumLoad'][posJ - 1]
            secJloadEnd = solution[routeJ]['CumLoad'][-1] - secJloadStart
            
            deltaChangeRouteI = secJloadEnd - secIloadEnd
            deltaChangeRouteJ = secIloadEnd - secJloadEnd
            
            excessI = solution[routeI]['Load'] + deltaChangeRouteI - self._capacity
            excessJ = solution[routeJ]['Load'] + deltaChangeRouteJ - self._capacity
            
            moveFeasible = excessI <= 0 and excessJ <= 0
        
        return(moveFeasible, deltaChangeRouteI, deltaChangeRouteJ, solution)

    def _doubleCrossFeasibility(self, moveInfo, solutionMapping, solution):
        '''
        '''
        (costDummy, (moveInfo1, moveInfo2), moveType) = moveInfo
        if moveType != 'doubleCross': raise NameError('Incorrect feasibility check (%s) for this kind of move (doubleCross).'%moveType)
        
        (crossCost1, (arcI1, preArcI1, postArcI1, arcJ1, preArcJ1, postArcJ1), moveType, (routeIcostChange, routeJcostChange)) = moveInfo1
        if moveType != 'cross': raise NameError('Incorrect feasibility check (%s) for this kind of move (cross).'%moveType)
        (routeI1, arcIpos1) = solutionMapping[arcI1]
        (routeJ1, arcIpos2) = solutionMapping[arcJ1]            
        arcIpos1, arcIpos2 = min([arcIpos1, arcIpos2]), max([arcIpos1, arcIpos2])

        (crossCost2, (arcI2, preArcI2, postArcI2, arcJ2, preArcJ2, postArcJ2), moveType, (routeIcostChange, routeJcostChange)) = moveInfo2
        if moveType != 'cross': raise NameError('Incorrect feasibility check (%s) for this kind of move (cross).'%moveType)
        (routeI2, arcJpos1) = solutionMapping[arcI2]
        (routeJ2, arcJpos2) = solutionMapping[arcJ2]       
        
        if routeI1 != routeJ1 or routeI2 != routeJ2 or routeI1 != routeI2: 
            feasible = False
        else: 
            arcJpos1, arcJpos2 = min([arcJpos1, arcJpos2]), max([arcJpos1, arcJpos2])
            
            seq = []
            if arcIpos1 < arcJpos1:
                seq = (arcIpos1, arcJpos1, arcIpos2, arcJpos2)
            else:
                seq = (arcJpos1, arcIpos1, arcJpos2, arcIpos2)
            feasible =  seq[0] + 1 < seq[1] and seq[1] < seq[2] - 1 and seq[2] + 1 < seq[3]
        return(feasible, 0, 0)

    def _returnRouteInfo(self, moveInfo, solutionMapping, solution):
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        (routeI, posI) = solutionMapping[arcI]
        if moveType == 'crossAtDummy' or moveType == 'relocateBeforeDummy':
            (routeJ, posJ) = solutionMapping[preArcJ]
        else:
            (routeJ, posJ) = solutionMapping[arcJ]
        return(routeI, routeJ)

    def doubleMoveFeasibility(self, moveInfo, solutionMapping, solution):
        '''
        '''
        (costDummy, (moveInfo1, moveInfo2), moveType) = moveInfo
        if moveType != 'comboMove': raise NameError('Incorrect feasibility check (%s) for this kind of move (comboMove).'%moveType)
        solutionLoads = {i : {'Load' : solution[i]['Load']} for i in range(solution['nVehicles'])}
        
        (routeI1, routeJ1) = self._returnRouteInfo(moveInfo1, solutionMapping, solution) 
        
        (feasible1, loadI, loadJ) = self.checkMoveFeasibility(moveInfo1, solutionMapping, solutionLoads, saveMoveInfo = False)
        
        solutionLoads[routeI1]['Load'] += loadI
        solutionLoads[routeJ1]['Load'] += loadJ
        
        (routeI2, routeJ2) = self._returnRouteInfo(moveInfo2, solutionMapping, solution) 
               
        (feasible2, loadI, loadJ) = self.checkMoveFeasibility(moveInfo2, solutionMapping, solutionLoads, saveMoveInfo = False)
        
        solutionLoads[routeI2]['Load'] += loadI
        solutionLoads[routeJ2]['Load'] += loadJ

        feasible = solutionLoads[routeI1]['Load']  <= self._capacity and solutionLoads[routeJ1]['Load'] <= self._capacity
        feasible2 = solutionLoads[routeI2]['Load']  <= self._capacity and solutionLoads[routeJ2]['Load'] <= self._capacity
        
        feasible2  = feasible and feasible2
        
        return(feasible1, feasible2)
    
    def checkMoveFeasibility(self, moveInfo, solutionMapping, solution, saveMoveInfo = True):
        '''
        Check if move is feasible.
        '''
        moveType = moveInfo[2]
        
        self._solutionMapping = solutionMapping
        self._solution = solution
        
        if moveType == 'relocate': 
            (feasible, loadI, loadJ) = self._relocateFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'doubleRelocate':
            (feasible, loadI, loadJ) = self._doubleRelocateFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'exchange':
            (feasible, loadI, loadJ) = self._exchangeFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'flip':
            (feasible, loadI, loadJ) = self._flipFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'relocateBeforeDummy':
            (feasible, loadI, loadJ) = self._relocateFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'cross':
            (feasible, loadI, loadJ, solution) = self._crossFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'crossAtDummy':
            (feasible, loadI, loadJ, solution) = self._crossEndFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'doubleCross':
            (feasible, loadI, loadJ) = self._doubleCrossFeasibility(moveInfo, solutionMapping, solution)
        if moveType == 'comboMove':
            (feasible, loadI, loadJ) = self._doubleMoveFeasibility(moveInfo, solutionMapping, solution)

        if moveType != 'cross' and moveType != 'crossAtDummy' and saveMoveInfo:
            if not feasible: self.infeasibleMoves.append((moveInfo[0], loadI, loadJ, moveInfo))
            if moveInfo[0] >= self.threshold:
                self.exceedThresholdRemoveInsert.append(moveInfo)
            
        if moveType == 'cross' and feasible == None and saveMoveInfo:
            self.doubleCrossMove.append(moveInfo)
            if moveInfo[0] >= self.threshold:
                self.exceedThresholdDoubleCross.append(moveInfo)
                        
        if not saveMoveInfo:
            return(feasible, loadI, loadJ)
        else:
            return(feasible, solution)
    
    
class MakeMovesMCARP(object):
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
        
        self._searchPhase = 'unknown'
        self._testMoves = TestLocalSeach(info)
        self._testAll = testMoves
        self._printEachMove = True
        
        self.moveCount = [0]*len(self._reqArcs)
        
    def setSolution(self, solution):
        self.solution = solution
        self.solutionMapping = self._genMCARPsolutionMapping()
    
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

    def _genMCARPsolutionMapping(self):
        '''
        Takes an initial solution and maps all the required arcs to route and inter-route positions.
        '''
        solution = self.solution
        dummyArcPositions = []
        solutionMapping = {} # Mapping of an arc to its position (route and route position) in the solution.
        for i in range(solution['nVehicles']):
            route = solution[i]['Route']
            for j, arc in enumerate(route[1:-1]): # Note that j will start zero, not 1
                solutionMapping[arc] = (i, j + 1) # Since positioning starts at the first arc after the depot, j is increased by one.
                if arc in self._edgesS: solutionMapping[self._inv[arc]] = (i, j + 1) # Position of inverse arc is also captured, thus allowing for arc inversion (should come more into play with windy edges.
            
        return(solutionMapping)
    
    def _printMove(self, routeI, posI, routeJ, posJ, tCost):
        '''
        Print basic info of relocate move
        '''
        arcI, arcJ = self._moveInfo[1][0], self._moveInfo[1][3]
        if arcI: self.moveCount[arcI] += 1
        if arcJ: self.moveCount[arcJ] += 1
        if self._printEachMove:
            printMove(self._moveInfo, routeI, posI, routeJ, posJ, tCost, self._searchPhase)
    
    def _updateSolution(self, routeI, loadChange, costChange):
        '''
        Update solution with cost and route change
        '''
        self.solution[routeI]['CumUpdate'] = False
        self.solution[routeI]['Load'] += loadChange
        self.solution[routeI]['Cost'] += costChange
        self.solution['TotalCost'] += costChange

    def _updateCrossSolution(self, routeI):
        '''
        Update solution with cost and route change
        '''
        self.solution = updateMCARPcumulitiveSolution(self.info, self.solution, routeI)
        self.solution[routeI]['Load'] = self.solution[routeI]['CumLoad'][-1]
        self.solution[routeI]['Cost'] = self.solution[routeI]['CumServe'][-1]            

    def _updateArcPositions(self, routeI):
        '''
        Update solution positions of arc in a given route.
        '''
        for j, arc in enumerate(self.solution[routeI]['Route'][1:-1]): # Note that j will start zero, not 1
            self.solutionMapping[arc] = (routeI, j + 1) # Since positioning starts at the first arc after the depot, j is increased by one.
            if arc in self._edgesS: 
                self.solutionMapping[self._inv[arc]] = (routeI, j + 1)

    def _relocateMove(self):
        '''
        Make a relocate move.
        '''
        if self._testAll: self._testMoves._testRelocateMove(self._moveInfo,  self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, removePos) =  self.solutionMapping[arcI]
        (routeJ, insertPos) =  self.solutionMapping[arcJ]
        
        dRelocate = self._demand[arcI]
        sRelocate = self._service[arcI]

        self._updateSolution(routeI, -dRelocate, moveCostsI - sRelocate)
        self._updateSolution(routeJ, +dRelocate, moveCostsJ + sRelocate)
        
        if routeI == routeJ and removePos < insertPos:
            self.solution[routeI]['Route'].insert(insertPos, arcI)
            del self.solution[routeI]['Route'][removePos]
        else:
            del self.solution[routeI]['Route'][removePos]                        
            self.solution[routeJ]['Route'].insert(insertPos, arcI)
            
        self._updateArcPositions(routeI)
        if routeI != routeJ: self._updateArcPositions(routeJ)
        if len(self.solution[routeI]['Route']) < 3: self._removeRoute(routeI, updateTotalCost = True)
        self._printMove(routeI, removePos, routeJ, insertPos, self.solution['TotalCost'])

    def _doubleRelocateMove(self):
        '''
        Make a relocate move.
        '''
        if self._testAll: self._testMoves._testDoubleRelocateMove(self._moveInfo,  self.solutionMapping, self.solution)
        
        (moveCost, (arcIa, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        arcIb = postArcJ #Is this right?????? Jip! postArcJ is used since there's no space to store arcIb
        (routeI, removePos) =  self.solutionMapping[arcIa]
        (routeJ, insertPos) =  self.solutionMapping[arcJ]
        
        dRelocate = self._demand[arcIa] + self._demand[arcIb]
        sRelocate = self._service[arcIa] + self._d[arcIa][arcIb] + self._service[arcIb]

        self._updateSolution(routeI, -dRelocate, moveCostsI - sRelocate)
        self._updateSolution(routeJ, +dRelocate, moveCostsJ + sRelocate)
        
        if routeI == routeJ and removePos < insertPos:
            self.solution[routeI]['Route'].insert(insertPos, arcIa)
            self.solution[routeI]['Route'].insert(insertPos + 1, arcIb)
            del self.solution[routeI]['Route'][removePos + 1]
            del self.solution[routeI]['Route'][removePos]
        else:
            del self.solution[routeI]['Route'][removePos + 1]
            del self.solution[routeI]['Route'][removePos]                       
            self.solution[routeJ]['Route'].insert(insertPos, arcIa)
            self.solution[routeJ]['Route'].insert(insertPos + 1, arcIb)
            
        self._updateArcPositions(routeI)
        if routeI != routeJ: self._updateArcPositions(routeJ)
        if len(self.solution[routeI]['Route']) < 3: self._removeRoute(routeI, updateTotalCost = True)
        self._printMove(routeI, removePos, routeJ, insertPos, self.solution['TotalCost'])

    def _exchangeMove(self):
        '''
        Make an exchange move.
        '''
        if self._testAll: self._testMoves._testExchangeMove(self._moveInfo, self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, arcPos1) = self.solutionMapping[arcI]
        (routeJ, arcPos2) = self.solutionMapping[arcJ]
        
        dRelocate = self._demand[arcI] - self._demand[arcJ]
        sRelocate = self._service[arcI] - self._service[arcJ]
                

        self._updateSolution(routeI, -dRelocate, moveCostsI - sRelocate)
        self._updateSolution(routeJ, +dRelocate, moveCostsJ + sRelocate)
        
        self.solution[routeI]['Route'][arcPos1] = arcJ
        self.solution[routeJ]['Route'][arcPos2] = arcI
        
        self.solutionMapping[arcJ] = (routeI, arcPos1)
        if arcJ in self._edgesS: self.solutionMapping[self._inv[arcJ]] = (routeI, arcPos1)
            
        self.solutionMapping[arcI] = (routeJ, arcPos2)
        if arcI in self._edgesS: self.solutionMapping[self._inv[arcI]] = (routeJ, arcPos2)

        self._printMove(routeI, arcPos1, routeJ, arcPos2, self.solution['TotalCost'])

    def _flipMove(self):
        '''
        Flip an arc task in place.
        '''
        if self._testAll: self._testMoves._testFlipMove(self._moveInfo, self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, arcPos1) = self.solutionMapping[arcI]

        self._updateSolution(routeI, 0, moveCost)
        self.solution[routeI]['Route'][arcPos1] = arcI
        
        self._printMove(routeI, arcPos1, None, None, self.solution['TotalCost'])
   
    def _relocateBeginnigRouteMove(self):
        '''
        Make a relocate move.
        '''
        if self._testAll: self._testMoves._testRelocateMoveEndRoute(self._moveInfo, self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, removePos) = self.solutionMapping[arcI]
        (routeJ, insertPos) = self.solutionMapping[preArcJ]
        insertPos += 1

        dRelocate = self._demand[arcI]
        sRelocate = self._service[arcI]
                
        self._updateSolution(routeI, -dRelocate, moveCostsI - sRelocate)
        self._updateSolution(routeJ, +dRelocate, moveCostsJ + sRelocate)
        
        if routeI == routeJ and removePos < insertPos:
            self.solution[routeI]['Route'].insert(insertPos, arcI)
            del self.solution[routeI]['Route'][removePos]
        else:
            del self.solution[routeI]['Route'][removePos]                        
            self.solution[routeJ]['Route'].insert(insertPos, arcI)
            
        self._updateArcPositions(routeI)
        if routeI != routeJ: self._updateArcPositions(routeJ)
        
        if len(self.solution[routeI]['Route']) < 3: self._removeRoute(routeI, updateTotalCost = True)
        
        self._printMove(routeI, removePos, routeJ, insertPos, self.solution['TotalCost'])

    def _crossMove(self):
        '''
        Cross two end sections of two routes.
        '''
        if self._testAll: self._testMoves._testCrossMove(self._moveInfo, self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, arcPos1) = self.solutionMapping[arcI]
        (routeJ, arcPos2) = self.solutionMapping[arcJ]     
        
        seqI1 = self.solution[routeI]['Route'][:arcPos1]
        seqI2 = self.solution[routeI]['Route'][arcPos1:]
        seqJ1 = self.solution[routeJ]['Route'][:arcPos2]
        seqJ2 = self.solution[routeJ]['Route'][arcPos2:]
        self.solution[routeI]['Route'] =  seqI1 + seqJ2
        self.solution[routeJ]['Route'] =  seqJ1 + seqI2
        self._updateCrossSolution(routeI)
        self._updateCrossSolution(routeJ)
        self.solution['TotalCost'] += moveCost
        self._updateArcPositions(routeI)
        self._updateArcPositions(routeJ)
        
        self._printMove(routeI, arcPos1, routeJ, arcPos2, self.solution['TotalCost'])

    def _crossAtDummyMove(self):
        '''
        Cross two end sections of two routes.
        '''
    
        if self._testAll: self._testMoves._testCrossAtDummyMove(self._moveInfo, self.solutionMapping, self.solution)
        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (moveCostsI, moveCostsJ)) = self._moveInfo
        (routeI, arcPos1) = self.solutionMapping[arcI]
        (routeJ, arcPos2) = self.solutionMapping[preArcJ]
        arcPos2 += 1  
        
        seqI1 = self.solution[routeI]['Route'][:arcPos1]
        seqI2 = self.solution[routeI]['Route'][arcPos1:]
        seqJ1 = self.solution[routeJ]['Route'][:arcPos2]
        seqJ2 = self.solution[routeJ]['Route'][arcPos2:]
        self.solution[routeI]['Route'] =  seqI1 + seqJ2
        self.solution[routeJ]['Route'] =  seqJ1 + seqI2
        self._updateCrossSolution(routeI)
        self._updateCrossSolution(routeJ)
        self.solution['TotalCost'] += moveCost
        self._updateArcPositions(routeI)
        self._updateArcPositions(routeJ)
        
        self._printMove(routeI, arcPos1, routeJ, arcPos2, self.solution['TotalCost'])
        
        
        if arcPos1 == 1: self._removeRoute(routeI, updateTotalCost = False)

        
    def _doubleCrossMove(self):
        '''
        Cross four sections of a route in a single route.
        '''
        (tCost, (moveInfo1, moveInfo2), moveType) = self._moveInfo
        
        if self._testAll: self._testMoves._testCrossMove(moveInfo1, self.solutionMapping, self.solution)
        if self._testAll: self._testMoves._testCrossMove(moveInfo2, self.solutionMapping, self.solution)
        (arcI1, preArcI1, postArcI1, arcJ1, preArcJ1, postArcJ1) = moveInfo1[1]
        (arcI2, preArcI2, postArcI2, arcJ2, preArcJ2, postArcJ2) = moveInfo2[1]
        (routeI, arcIPos1) = self.solutionMapping[arcI1]
        (routeJ, arcIPos2) = self.solutionMapping[arcJ1]
        (routeI2, arcJPos1) = self.solutionMapping[arcI2]
        (routeJ2, arcJPos2) = self.solutionMapping[arcJ2]
        
        arcIpos1, arcIpos2 = min([arcIPos1, arcIPos2]), max([arcIPos1, arcIPos2])
        arcJpos1, arcJpos2 = min([arcJPos1, arcJPos2]), max([arcJPos1, arcJPos2])

        if arcIpos1 < arcJpos1:
            seq = (arcIpos1, arcJpos1, arcIpos2, arcJpos2)
        else:
            seq = (arcJpos1, arcIpos1, arcJpos2, arcIpos2)

        if routeI != routeJ or routeI2 != routeJ2 or routeI != routeI2: raise NameError('Double cross move cannot be applied to different routes: %i and %i and %i and %i'%(routeI, routeJ, routeI2, routeJ2))
        
        (arcIpos1, arcJpos1, arcIpos2, arcJpos2) = seq
        route = self.solution[routeI]['Route']
        sec1 = route[:arcIpos1]
        sec2 = route[arcIpos1:arcJpos1]
        sec3 = route[arcJpos1:arcIpos2]
        sec4 = route[arcIpos2:arcJpos2]
        sec5 = route[arcJpos2:]
        newRoute = sec1 + sec4 + sec3 + sec2 + sec5
        self.solution[routeI]['Route'] = newRoute
        self._updateCrossSolution(routeI)
        self._updateArcPositions(routeI)
        self.solution['TotalCost'] += moveInfo1[0]
        
        self._moveInfo = moveInfo1
        self._printMove(routeI, arcIpos1, routeI, arcIpos2, self.solution['TotalCost'])
        self.solution['TotalCost'] += moveInfo2[0]
        self._moveInfo = moveInfo2
        self._printMove(routeI, arcJpos1, routeI, arcJpos2, self.solution['TotalCost']) 

    def _comboMove(self):
        (potentialSavings, (moveInfo1, moveInfo2), moveType) = self._moveInfo
        self.makeMove(moveInfo2, self.solution)
        self.makeMove(moveInfo1, self.solution)
    
    def _removeRoute(self, routeI, updateTotalCost = False):
        nVhicles = self.solution['nVehicles']
        for j in range(routeI, nVhicles - 1):
            self.solution[j] = self.solution[j + 1]
        del self.solution[nVhicles - 1]
        if updateTotalCost: self.solution['TotalCost'] -= self.info.dumpCost     
        self.solution['nVehicles'] -= 1
        self.solutionMapping = self._genMCARPsolutionMapping()  
         
    
    def makeMove(self, moveInfo, solution):
        '''
        Make move associated with move type.
        '''
        printSolution = False
        self.solution = solution
        self._moveInfo = moveInfo
        moveType = self._moveInfo[2]
        if moveType == 'relocate': self._relocateMove()
        if moveType == 'doubleRelocate': self._doubleRelocateMove()
        if moveType == 'exchange': self._exchangeMove()
        if moveType == 'flip': self._flipMove()
        if moveType == 'relocateBeforeDummy': self._relocateBeginnigRouteMove()
        if moveType == 'cross': self._crossMove()
        if moveType == 'crossAtDummy': self._crossAtDummyMove()
        if moveType == 'doubleCross': self._doubleCrossMove()
        if moveType == 'comboMove': self._comboMove()
        self._moveInfo = []
        if printSolution:
            for i in self.solution:
                print (self.solution[i])
        return(self.solution)

class DoubleCrossMovesMCARP(object):
    '''
    Make special double cross move in one route.
    '''
    def __init__(self, info):
        self._testMoves = TestLocalSeach(info)
        self._printEachMove = True
        self._checkFeasibility = MovesFeasibleMCARP(info)
        self.threshold = 0
    
    def findDoubleCrossMoveCosts(self, solution, solutionMapping, doubleCross):
        '''
        Check for non-improving relocate moves which will allow infeasible moves to become feasible.
        '''
        routesSavings = {}
        for moveInfo in doubleCross:
            (crossCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, (routeIcostChange, routeJcostChange)) = moveInfo
            (routeI, arcPos1) = solutionMapping[arcI]
            if routeI not in routesSavings:
                routesSavings[routeI] = []
            routesSavings[routeI].append(moveInfo)
        return(routesSavings)
    
    def pairFeasibleDoubleCrossMoves(self, solution, solutionMapping, doubleCross):
        savings = {}
        doubleCross.sort()
        routesSavings = self.findDoubleCrossMoveCosts(solution, solutionMapping, doubleCross)
        for route in routesSavings:
            savings_R = []
            nSavings = len(routesSavings[route])
            for i in range(nSavings - 1):
                moveInfo1 = routesSavings[route][i]
                for j in range(i, nSavings):
                    moveInfo2 = routesSavings[route][j]
                    tCost = moveInfo1[0] + moveInfo2[0]
                    if tCost >= self.threshold: continue
                    moveInfo = (tCost, (moveInfo1, moveInfo2), 'doubleCross')
                    feasible = self._checkFeasibility.checkMoveFeasibility(moveInfo, solutionMapping, solution)[0]
                    if feasible:
                        savings_R.append((tCost, (moveInfo1, moveInfo2), 'doubleCross'))
            if savings_R:
                savings_R.sort() 
                savings[route] = savings_R[:]
        return(savings)       

class InfeasibleMovesMCARP(object):
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
            if moveType == 'doubleRelocate': continue
            (routeI, arcI) = solutionMapping[arcI]
            if moveType == 'relocateBeforeDummy':
                arcJ = preArcJ
            (routeJ, arcJ) = solutionMapping[arcJ]
            capI = solution[routeI]['Load'] + loadI
            capJ = solution[routeJ]['Load'] + loadJ
            if capI > capJ:
                routeExcess = routeI
            else:
                routeExcess = routeJ
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
            if moveType != 'relocate' and moveType != 'relocateBeforeDummy': continue
            (routeI, arcI) = solutionMapping[arcI]
            if moveType == 'relocateBeforeDummy':
                arcJ = preArcJ
            (routeJ, arcJ) = solutionMapping[arcJ]
            if routeI == routeJ: continue
            if routeI not in routesSavings:
                routesSavings[routeI] = []
            routesSavings[routeI].append(moveInfo)           
        return(routesSavings)  

    def infeasibleMoveCombos(self, solution, solutionMapping, infeasibleMoves, costlyMoves):
        
        CompoundTemp = CompoundMoveFunctions(self.info, False)
        infeasibleGrouping = self.findInfeasibleMoveCosts(solution, solutionMapping, infeasibleMoves)
        
        if not infeasibleMoves:
            return([])
        
        outMoves = [move[3] for move in infeasibleMoves] + costlyMoves
        outMoves.sort(key=lambda x: x if isinstance(x, str) else "")
        
        outGrouping = self.findOutRelocateMoveCosts(solution, solutionMapping, outMoves)
        
        savingsCombo = []
        for routeI in infeasibleGrouping:
            if routeI not in outGrouping: continue
            for InfeasibleMoveInfo in infeasibleGrouping[routeI]:
                CompoundTemp.resetMoveInfluencers()
                (moveCost, loadI, loadJ, moveInfo) = InfeasibleMoveInfo
                CompoundTemp.addMoveInfluence(moveInfo)
                for outMoveInfo in outGrouping[routeI]:
                    if moveInfo[0] + outMoveInfo[0] >= self.threshold: continue
                    compoundComboOutFeasible = CompoundTemp.checkCompoundMoveFeasibility(outMoveInfo)
                    if compoundComboOutFeasible:
                        savingsCombo.append((moveInfo[0] + outMoveInfo[0], (moveInfo, outMoveInfo), 'comboMove'))
        
        savingsCombo.sort()
        
        return(savingsCombo)

class CompoundMoveFunctions():

    def __init__(self, info, autoInvCosts = False):
        self.autoInvCosts = autoInvCosts
        self._depotArc = info.depotnewkey
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self._locationChanged = set()
        self._preLocationChanged = set()
        self._dummyRoutes = set()

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
        
        if moveType == 'relocate' and arcJ in self._preLocationChanged:
            feasible = False
        elif moveType == 'relocateBeforeDummy' and (preArcJ in self._dummyRoutes or preArcJ in self._locationChanged):
            feasible = False
        elif moveType == 'crossAtDummy' and preArcJ in self._locationChanged:
            feasible = False
        elif moveType != 'flip' and arcJ in self._locationChanged:
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
    
    def addMoveInfluence(self, moveInfo):
                        
        (moveCost, (arcI, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, routeCosts) = moveInfo
        
        if moveInfo[2] == 'doubleRelocate':
            arcI1 = arcI
            arcI2 = postArcJ
            self._locationChanged.update(self.addArc({preArcI, arcI1, arcI2, preArcJ, arcJ}))
            self._preLocationChanged.update(self.addArc({arcI1, arcJ}))
            self._dummyRoutes.update(self.addArc({arcI1, arcJ}))
            
            self._locationChanged.update(self.addArc({postArcI}))
            self._preLocationChanged.update(self.addArc({postArcI}))
            self._dummyRoutes.update(self.addArc({postArcI}))
            
        elif moveInfo[2] == 'flip':
            self._locationChanged.update(self.addArc({preArcI, arcI, postArcI}))
            self._preLocationChanged.update(self.addArc({arcI, postArcI}))
            self._dummyRoutes.update(self.addArc({arcI, postArcI}))
        else:
            
            self._locationChanged.update(self.addArc({preArcI, arcI, preArcJ, arcJ}))
            self._preLocationChanged.update(self.addArc({arcI, arcJ}))
            self._dummyRoutes.update(self.addArc({arcI, arcJ}))
                
            if moveInfo[2] == 'relocate':
            
                self._locationChanged.update(self.addArc({postArcI}))
                self._preLocationChanged.update(self.addArc({postArcI}))
                self._dummyRoutes.update(self.addArc({postArcI}))
            
            if moveInfo[2] == 'relocateBeforeDummy':
                
                self._locationChanged.update(self.addArc({postArcI}))
                self._dummyRoutes.update(self.addArc({preArcJ}))
            
            if moveInfo[2] == 'exchange':
    
                self._locationChanged.update(self.addArc({postArcI, postArcJ}))
                self._preLocationChanged.update(self.addArc({postArcI, postArcJ}))
                self._dummyRoutes.update(self.addArc({postArcI, postArcJ}))
    
    def addDoubleMoveInfluence(self, moveInfo):
        (moveCost, (moveInfo1, moveInfo2), moveType) = moveInfo
        self.addMoveInfluence(moveInfo1)
        self.addMoveInfluence(moveInfo2)
        
    def returnNonCompoundMoves(self, moves):
        allowableMoves = []
        for moveInfo in moves:
            if self.checkCompoundMoveFeasibility(moveInfo) and moveInfo[2] != 'relocateBeforeDummy' and moveInfo[2] != 'crossAtDummy':
                allowableMoves.append(moveInfo)
        return(allowableMoves)

    def returnNonCompoundInfeasibleMoves(self, moves):
        allowableMoves = []
        for compoundMoveInfo in moves:
            moveInfo = compoundMoveInfo[3]
            if self.checkCompoundMoveFeasibility(moveInfo) and moveInfo[2] != 'relocateBeforeDummy' and moveInfo[2] != 'crossAtDummy':
                allowableMoves.append(compoundMoveInfo)
        return(allowableMoves)
    
    def returnRouteArcs(self, solution):
        routeArcs = []
        for i in range(solution['nVehicles']):
            routeArcs += solution[i]['Route'][1:-1]
        routeArcs = set(routeArcs)
        return(routeArcs)

    def returnRouteArcsEnd(self, solution):
        routeArcs = set()
        for i in range(solution['nVehicles']):
            routeArcs.add(solution[i]['Route'][-2])
        return(routeArcs)
           
    def returnRelocateArcs(self, routeArcs):
        if self.autoInvCosts: relocateArcs = self._locationChanged.intersection(routeArcs)
        else: relocateArcs = self._locationChanged
        return(relocateArcs)
    
    def returnInsertLocations(self, routeArcs):
        #insertLocations = self._preLocationChanged.intersection(routeArcs)
        insertLocations = self._locationChanged.intersection(routeArcs)
        return(insertLocations)
    
    def returnCrossArcs(self, routeArcs):
        crossLocations = self._locationChanged.intersection(routeArcs)
        return(crossLocations)
    
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



class LS_MCARP(object):
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
        self.candidateMoves = True
        
        # Move costs
        self.autoInvCosts = autoInvCosts
        self._MoveCosts = CalcMoveCosts(info, nnList = nnList, autoInvCosts = autoInvCosts)
        self._MovesFeasible = MovesFeasibleMCARP(info)
        self._MovesMaker = MakeMovesMCARP(info, testMoves = testAll)
        self._MovesDoubleCross = DoubleCrossMovesMCARP(info)
        self._MovesCompound = CompoundMoveFunctions(info, autoInvCosts)
        self._MovesInfeasible = InfeasibleMovesMCARP(info)
        
        # Move test
        self._testAll = testAll
        self._testMoves = TestLocalSeach(info)
        
        # Printing setup
        self._printEachMove = True
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
        
        
    def _initiateLocalSearchRoute(self):
        self._MovesFeasible.restartFeasibility()
        self._MovesCompound.resetMoveInfluencers()

    def _candidateCalculations(self, solution):
        
        #self._reduceCompoundMoves()
        self._movesNotUsed = self._MovesCompound.returnNonCompoundMoves(self._movesNotUsed)
        movesToUse = self._movesNotUsed

        routeArcs = self._MovesCompound.returnRouteArcs(solution)

        routeArcsEnd = self._MovesCompound.returnRouteArcsEnd(solution)
        removeArcs = self._MovesCompound.returnRelocateArcs(routeArcs)
        
        insertPositionArcs = self._MovesCompound.returnInsertLocations(routeArcs)
        crossArcs = self._MovesCompound.returnCrossArcs(routeArcs)
        
        allDoubleRemoveArcs = routeArcs.difference(routeArcsEnd)
        doubleRemoveArcs = crossArcs.difference(routeArcsEnd)
        
        savings = movesToUse
        
        savings += self._MoveCosts.calcRelocateMoves(relocateCandidates = removeArcs, insertCandidates = None)
        relocateCandidates2 = set(self._MoveCosts._relocateCandidates).difference(removeArcs)
        savings += self._MoveCosts.calcRelocateMoves(relocateCandidates = relocateCandidates2, insertCandidates = insertPositionArcs)
        
        savings += self._MoveCosts.calcDoubleRelocateMoves(relocateCandidates = doubleRemoveArcs, insertCandidates = None)
        doubleRelocateCandidates2 = set(allDoubleRemoveArcs).difference(doubleRemoveArcs)
        savings += self._MoveCosts.calcDoubleRelocateMoves(relocateCandidates = doubleRelocateCandidates2, insertCandidates = insertPositionArcs)
        
        savings += self._MoveCosts.calcRelocateBeforeDummyMoves(relocateCandidates = None)
        savings += self._MoveCosts.calcExchangeMoves(exchangeCandidates1 = removeArcs, exchangeCandidates2 = None)
        savings += self._MoveCosts.calcExchangeMoves(exchangeCandidates1 = None, exchangeCandidates2 = removeArcs) # optional
        savings += self._MoveCosts.calcCrossMoves(crossCandidates1 = crossArcs, crossCandidates2 = None) 
        savings += self._MoveCosts.calcCrossMoves(crossCandidates1 = None, crossCandidates2 = crossArcs) # optional
        savings += self._MoveCosts.calcCrossAtDummyMoves(crossCandidates = None)
        savings += self._MoveCosts.calcFlipMoves(insertPositionArcs)
        
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
            
            if not feasible or moveInfo[0] >= self.threshold:
                self._movesNotUsed.append(moveInfo)
                continue

            feasibleMove = True

            self._MovesCompound.addMoveInfluence(moveInfo)
            solution = self._MovesMaker.makeMove(moveInfo, solution)
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
                if moveInfo[0] >= self.threshold: continue
                compoundFeasible = self._MovesCompound.checkCompoundDoubleMoveFeasibility(moveInfo)
                if not compoundFeasible: continue
                self._MovesCompound.addDoubleMoveInfluence(moveInfo)
                self._nMoves += 1
                solution = self._MovesMaker.makeMove(moveInfo, solution)
                if self._testAll: self._testMoves._testSolution(solution)
                feasibleMove = True
                break
        return(feasibleMove, solution)

    def _makeNewDoubleCrossCompoundMoves(self, solution):
            
        self._MovesMaker.setSearchPhase('New double-cross moves')
        self._MovesMaker.setSolution(solution)

        self._MovesFeasible.doubleCrossMove = self._MovesCompound.returnNonCompoundMoves(self._MovesFeasible.doubleCrossMove)
                
        doubleCrossMoves = self._MovesFeasible.doubleCrossMove
        
        savingsR = self._MovesDoubleCross.findDoubleCrossMoveCosts(solution, self._MovesMaker.solutionMapping, doubleCrossMoves)
        
        self._MoveCosts.setSolution(solution)
        savings = self._MoveCosts.calcSingleRouteCrossCosts(savingsR, solution)
        self._MoveCosts.freeSolution()
        
        savingsR = self._MovesDoubleCross.pairFeasibleDoubleCrossMoves(solution, self._MovesMaker.solutionMapping, savings)
        
        feasibleMove = False
        
        compoundCheckTemp = CompoundMoveFunctions(self.info)
        for route in savingsR:
            for moveInfo in savingsR[route]:
                if moveInfo[0] >= self.threshold: continue
                compoundFeasible = compoundCheckTemp.checkCompoundDoubleMoveFeasibility(moveInfo)
                if not compoundFeasible: continue
                self._MovesCompound.addDoubleMoveInfluence(moveInfo)
                compoundCheckTemp.addDoubleMoveInfluence(moveInfo)
                self._nMoves += 1
                solution = self._MovesMaker.makeMove(moveInfo, solution)
                if self._testAll: self._testMoves._testSolution(solution)
                feasibleMove = True
                break
        
        return(feasibleMove, solution)        

    def _makeInfeasibleCompoundMoves(self, solution):
            
        self._MovesMaker.setSearchPhase('Current infeasible moves')
        self._MovesMaker.setSolution(solution)
        
        self._MovesFeasible.infeasibleMoves = self._MovesCompound.returnNonCompoundInfeasibleMoves(self._MovesFeasible.infeasibleMoves)
        self._MovesFeasible.exceedThresholdRemoveInsert = self._MovesCompound.returnNonCompoundMoves(self._MovesFeasible.exceedThresholdRemoveInsert)
        
        infeasibleMoves = self._MovesFeasible.infeasibleMoves
        costlyMoves = self._MovesFeasible.exceedThresholdRemoveInsert
        
        infeasibleMoveCombos = self._MovesInfeasible.infeasibleMoveCombos(solution, self._MovesMaker.solutionMapping, infeasibleMoves, costlyMoves)
        feasibleMove = False
        
        for comboMove in infeasibleMoveCombos:
            compoundFeasible = self._MovesCompound.checkCompoundDoubleMoveFeasibility(comboMove)
            if not compoundFeasible: continue
            (feasible1, feasible2) = self._MovesFeasible.doubleMoveFeasibility(comboMove, self._MovesMaker.solutionMapping, solution)
            (cost, (moveInfo1, moveInfo2), moveType) = comboMove
            if comboMove[0] >= self.threshold: continue
            if feasible1 and moveInfo1[0] < self.threshold:
                self._MovesCompound.addMoveInfluence(moveInfo1)
                self._nMoves += 1
                solution = self._MovesMaker.makeMove(moveInfo1, solution)
                feasibleMove = True
            elif feasible2:
                self._MovesCompound.addDoubleMoveInfluence(comboMove)
                self._nMoves += 1
                solution = self._MovesMaker.makeMove(comboMove, solution)
                feasibleMove = True
        
        return(feasibleMove, solution)

    def _makeNewInfeasibleCompoundMoves(self, solution):

        self._MovesMaker.setSearchPhase('New infeasible moves')
        self._MovesMaker.setSolution(solution)
        
        self._MovesFeasible.infeasibleMoves = self._MovesCompound.returnNonCompoundInfeasibleMoves(self._MovesFeasible.infeasibleMoves)

        infeasibleMoves = self._MovesFeasible.infeasibleMoves
        
        routeSavings = self._MovesInfeasible.findInfeasibleMoveCosts(solution, self._MovesMaker.solutionMapping, infeasibleMoves)
 
        self._MoveCosts.setSolution(solution)
        savings = self._MoveCosts.calcSingleRouteOutCosts(routeSavings, solution)
        self._MoveCosts.freeSolution()

        infeasibleMoveCombos = self._MovesInfeasible.infeasibleMoveCombos(solution, self._MovesMaker.solutionMapping, infeasibleMoves, savings)
        feasibleMove = False

        compoundCheckTemp = CompoundMoveFunctions(self.info)

        for comboMove in infeasibleMoveCombos:
            compoundFeasible = compoundCheckTemp.checkCompoundDoubleMoveFeasibility(comboMove)
            if not compoundFeasible: continue
            (feasible1, feasible2) = self._MovesFeasible.doubleMoveFeasibility(comboMove, self._MovesMaker.solutionMapping, solution)
            (cost, (moveInfo1, moveInfo2), moveType) = comboMove
            if comboMove[0] >= self.threshold: continue
            if feasible1 and moveInfo1[0] < self.threshold:
                compoundCheckTemp.addMoveInfluence(moveInfo1)
                self._MovesCompound.addMoveInfluence(moveInfo1)
                self._nMoves += 1
                solution = self._MovesMaker.makeMove(moveInfo1, solution)
                feasibleMove = True
            elif feasible2:
                compoundCheckTemp.addDoubleMoveInfluence(comboMove)
                self._MovesCompound.addDoubleMoveInfluence(comboMove)
                self._nMoves += 1
                solution = self._MovesMaker.makeMove(comboMove, solution)
                feasibleMove = True

        return(feasibleMove, solution)  
    
    def compoundLocalSearch(self, solution):
        
        solution = addMCARPcumulativeSolution(self.info, solution)
        candidateSearch = False
        self.setNonAdjacentArcRestriction()
        
        while True:
            
            self._nCompoundMoves += 1
            self._nMovesPrevious = self._nMoves
            if self._printEachMove:
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
        
        return(solution)
    
    def twoPhaseCompoundLocalSearch(self, solution):
        self._previousCost = solution['TotalCost']
        self.nnFrac = 0.1
        #self._MoveCosts.movesToUse = ['relocate']# ['cross', 'crossAtDummy']
        self.candidateMoves = True
        solution = self.compoundLocalSearch(solution)
        self.nnFrac = 1
        self.candidateMoves = True
        solution = self.compoundLocalSearch(solution)
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
            solution = self.compoundLocalSearch(solution)
            break
            #if not reducedFleet: break
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
        outputLine = '%s,%s,%s,%.2f,%s,%s,%i,%i,%i,%i,%.4f,%i,%i,%s\n'%(pSet,self.info.name,initial,self.nnFrac,canList,compoundMove,self._initialK, self._initialCost, self._initialK, self._finalCost,self.executionTime, self._nMoves, self._nCompoundMoves, moveStrategy)
        return(outputLine)
    
    def locaSearchImbedded(self, solutionStart):#, nnFrac = 1, candidateMoves = True, compoundMoves = True):
        t = clock()
        solution = deepcopy(solutionStart)
        self._initialCost = solution['TotalCost']
        self._previousCost = solution['TotalCost']
        solution = self.compoundLocalSearch(solution)
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
        self.resetIncumbentInfo()
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

            
class TabuSearch_MCARP(object):
    
    def __init__(self, info, nn_list, testAll = True):
        self.info = info
        self._LSfun = LS_MCARP(info, nn_list, testAll = testAll)
        self._TSfun = TabuFunctions(info)
        self.tabuThreshold = 1
        self.improveThreshold = 0
        self._movesNotUsed = []
        self._testAll = True
        self._nMovesNoImprovement = 50
        self._printOutput = False
        self.saveOutput = False
        self.nnFrac = 1
        self._LSfun.nnFrac = self.nnFrac
        self.tabuMoveLimit = 0.1
        self.tabuTenure =  5
        self.suppressOutput = False
    
    def setOutputString(self, problemSet, initial, experimentName, outputFile):
        self.saveOutput = True
        self.outputFile = outputFile
        tenure = self.tabuTenure
        stringInfo = (problemSet, self.info.name, initial, self.nnFrac, experimentName,
                      self.tabuThreshold, self.tabuMoveLimit, tenure, self._nMovesNoImprovement)
        self.outputLine = '%s,%s,%s,%.2f,%s,%i,%i,%i,%i,'%stringInfo
    
    def writeOutput(self, solution):
        if self.saveOutput:
            outString = '%i,%i,%.4f,%i,%i\n'%(self._initialCost,solution['TotalCost'], self.totalTime, self.nMovesSinceInc, self._TSfun._nCompoundMoves)
            outString = self.outputLine + outString
            outputF = open(self.outputFile, 'a')
            outputF.write(outString)
            outputF.close()
    
    def setTabuSearchParameters(self, compoundMoves = True, newCompoundMoves = False, 
                                 tabuTenure = 5, tabuThreshold = 1, nnFrac = 0.1, 
                                 tabuMoveLimit = 1000, maxNonImprovingMoves = 50,
                                 saveOutput = False):
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
        
        self.saveOutput = saveOutput
        
    def _initiateTabuSearch(self):
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
            
            if not feasible or moveInfo[0] >= self.tabuThreshold:
                self._LSfun._movesNotUsed.append(moveInfo)
                continue

            feasibleMove = True

            self._LSfun._MovesCompound.addMoveInfluence(moveInfo)
            self._TSfun.updateTabuList(moveInfo)
            solution = self._LSfun._MovesMaker.makeMove(moveInfo, solution)

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
        solution = self._LSfun.compoundLocalSearch(solution)
        newincumbent = self._TSfun.checkIncumbent(solution)
        
        
        if newincumbent:
            self._LSfun._nMoves += self._TSfun._nMoves
            self._LSfun._nCompoundMoves = self._TSfun._nCompoundMoves
            #print('New incumbent')
            self.writeOutput(solution)
            return(True, solution)
        else:
            #print('Aspiration failed\n')
            self._LSfun._nCompoundMoves = self._TSfun._nCompoundMoves
            self._LSfun._nMoves = self._TSfun._nMoves
            return(False, originalSolution)
        
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
    
    def compoundTabuSearch(self, solution):
        
        self._previousCost = solution['TotalCost']
        self._initialCost = self._previousCost
        self._TSfun.checkIncumbent(solution)
        timeStart = clock()
        self.totalTime = 0
        self.nMovesSinceInc = 0
        self.writeOutput(solution)        
        
        
        solution = addMCARPcumulativeSolution(self.info, solution)
        candidateSearch = False
        
        
        while self.nMovesSinceInc < self._nMovesNoImprovement:
            #print('')            
            self.totalTime = clock() - timeStart
            if self._testAll: self._LSfun._testMoves._testSolution(solution)

            self._TSfun._nCompoundMoves += 1
            
            self.nMovesSinceInc = self._TSfun._nCompoundMoves - self._TSfun._incK_nCM[-1]
            
            savings = self._LSfun._calculateMoveCosts(solution, candidateSearch)
            savings.sort(key=lambda x: x if isinstance(x, str) else "")
            candidateSearch = self.candidateMoves            
            asspiration = self._TSfun.checkAspirationCriteria(savings, solution)
            
            if asspiration:
                (moveMade, solution) = self._makeBestMoves(savings, solution)
            
            if not moveMade:
                (moveMade, solution) = self._makeTabuMoves(savings, solution)
                self._TSfun.checkIncumbent(solution)
                
            if not moveMade: 
                continue
            else:
                self._solutionChange = solution['TotalCost'] - self._previousCost
                self._previousCost = solution['TotalCost']
                if not self.suppressOutput:
                    print('I: %i \t Saving: %i \t # Moves %i \t Inc: %i \t nMoves Inc: %i/%i \t Time: %.4f \t {NN, tau} = {%.2f,%i} '%(self._TSfun._nCompoundMoves, self._solutionChange, self._TSfun._nMoves, self._TSfun._incK_z, self.nMovesSinceInc, self._nMovesNoImprovement, self.totalTime, self.nnFrac, self.tabuTenure))
        self.writeOutput(self._TSfun._incKsol)
        if not self.suppressOutput:
            print('Incumbent cost: %i\n'%self._TSfun._incK_z)
        return(solution)
        
    def tabuSearch(self, solution):
        #
        self._initiateTabuSearch()
        solution = self.compoundTabuSearch(solution)
        self._LSfun._MoveCosts.freeInputValues()
        return(deepcopy(self._TSfun._incKsol))
    
    def tabuSearchFree(self):
        self._initiateTabuSearch()
        
    def clearCythonModules(self):
        self._LSfun._MoveCosts.freeInputValues()
        
    def improveSolution(self, solution):
        #
        
        self._initiateTabuSearch()
        solution = self.compoundTabuSearch(solution)
        pp.pprint(self._LSfun._MovesMaker.moveCount)
        return(deepcopy(self._TSfun._incKsol))   
        
        
        