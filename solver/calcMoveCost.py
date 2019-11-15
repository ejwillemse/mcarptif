'''
Created on 03 Jun 2015

@author: eliaswillemse

Class to calculate the cost of different neighbourhood moves within a Local Search framework for the Mixed Capacitated Arc Routing Problems. Moves considered are remove-insert (relocate), 
exchange, and cross (special case of two-opt). Relocate removes an arc from a route and inserts in another position; exchange swaps the location of two routes; and cross swaps the end 
portions of two different routes. Relocate and exchange works on the same or two routes. Traditional Two-Opt moves are not considered as their efficient implementation is not trivial
on mixed networks, specifically as route inversions may result in different costs for the inverted section.

Moves are performed using required arcs as a reference and efficiency frameworks of Beullens et al (2003) are applied, such as candidate arcs and nearest neighbour lists, as
well as their move encoding scheme. Compound moves are also considered within an exhaustive neighbourhood search method, as well as exhaustive neighbourhood descent, first move descent and n
descent. 

The move encoding scheme was inspired by Irnich et al (2006) who use a giant route solution representation with inter route depot visits included, to calculate move costs. This should
allow for easier implementation for the MCARP under route length limit and Intermediate Facilities, as well as other versions of the problem. The general solution encoding scheme 
of Belenguer et al (2006) is used for input variables. The class be used for pure local search, metaheuristics or more complex efficient search frameworks, such as that proposed 
by Zachariadis & Kiranoudis (2010). 

Belenguer, J. M., Benavent, E., Lacomme, P., & Prins, C. (2006). Lower and upper bounds for the mixed capacitated arc routing problem. Computers & Operations Research, 33(12), 3363-3383.
Beullens, P., Muyldermans, L., Cattrysse, D., & Van Oudheusden, D. (2003). A guided local search heuristic for the capacitated arc routing problem. European Journal of Operational Research, 147(3), 629-643.
Irnich, S., Funke, B., & Grunert, T. (2006). Sequential search and its application to vehicle-routing problems. Computers & Operations Research, 33(8), 2405-2429.
Zachariadis, E. E., & Kiranoudis, C. T. (2010). A strategy for reducing the computational complexity of local search-based methods for the vehicle routing problem. Computers & Operations Research, 37(12), 2089-2105.
'''

from __future__ import division

import solver.sysPath as sysPath
import sys
sys = sysPath.addInputPaths(sys)
mainPath = sysPath.returnPath()

import pyximport
pyximport.install()

from math import ceil
import random
import copy
import solver.calcMoveCost_c as c_calcMoveCost
import solver.calcMoveCostMCARPTIF_c as calcMoveCostMCARPTIF_c

class TestMoveCostsMCARP(object):
    '''
    Test move calculations to see if they are accurate. No longer valid. 
    '''
    def __init__(self, info):
        '''
        Class initialization values.
        '''
        # Problem info
        self._info = info
        self._d = info.d
        self._depot = info.depotnewkey
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._nReqArcs = len(self._reqArcs)
        self._nEliments = len(self._d)
        self._reqArcsSet = set(self._reqArcs)
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self._arcsL = [arc for arc in self._reqArcs if arc not in self._edgesS]
        self._arcsS = set(self._arcsL)
        self._genGiantMCARPRoute = MCARPmoveFunctions(info)
        
    def testRelocateSavings(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate, preArcI, postArcI, arcToRelocateBefore, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionRemove = routeMapping[arcRelocate]
            arcInRoute = route[arcPositionRemove]
            if arcRelocate != arcInRoute and self._inv[arcRelocate] != arcInRoute: 
                raise NameError('Remove arc positions incorrect', arcRelocate, arcInRoute)
            
            arcPositionInsert = routeMapping[arcToRelocateBefore]
            arcInRoute = route[arcPositionInsert]        
            if arcToRelocateBefore != arcInRoute: 
                raise NameError('insert arc position incorrect', arcToRelocateBefore, arcInRoute)
            
            arcBefore = route[arcPositionRemove - 1]
            arcInRoute = route[arcPositionRemove]
            arcAfter = route[arcPositionRemove + 1]
            
            costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter1 = self._d[arcBefore][arcAfter]
            
            insertBefore = route[arcPositionInsert - 1]
            insertAfter = route[arcPositionInsert]
            
            costBefore2 = self._d[insertBefore][insertAfter]
            costAfter2 = self._d[insertBefore][arcRelocate] + self._d[arcRelocate][insertAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                raise NameError('Returned move cost incorrect', relocateCost, net_cost)
                
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                if arcPositionRemove < arcPositionInsert:
                    routeChange.insert(arcPositionInsert, arcRelocate)
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionInsert, arcRelocate)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    raise NameError('Actual move cost incorrect', relocateCost, costActual)
                    
    def testExchangeSavings(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (exchangeArc1, perArcI, postArcI, exchangeArc2, preArcI, postArcI), moveType, moveCosts) = saving
            
            
            arcPosition1 = routeMapping[exchangeArc1]
            arcInRoute = route[arcPosition1]
            if exchangeArc1 != arcInRoute and self._inv[exchangeArc1] != arcInRoute: 
                print('Arc1 arc positions incorrect', exchangeArc1, arcInRoute)
                a = input('Stop!')
            
            arcPosition2 = routeMapping[exchangeArc2]
            arcInRoute = route[arcPosition2]        
            if exchangeArc2 != arcInRoute and self._inv[exchangeArc2] != arcInRoute: 
                print('insert arc position incorrect', exchangeArc2, arcInRoute)
                a = input('Stop!')
                
            arcBefore = route[arcPosition1 - 1]
            arcInRoute = route[arcPosition1]
            arcAfter = route[arcPosition1 + 1]
            
            costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter1 = self._d[arcBefore][exchangeArc2] + self._d[exchangeArc2][arcAfter]
            
            arcBefore = route[arcPosition2 - 1]
            arcInRoute = route[arcPosition2]
            arcAfter = route[arcPosition2 + 1]
            
            costBefore2 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter2 = self._d[arcBefore][exchangeArc1] + self._d[exchangeArc1][arcAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print('Move cost incorrect', relocateCost, net_cost, exchangeArc1, arcPosition1, exchangeArc2, arcPosition2)
                print(saving)
                a = input('Stop!')
                
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                routeChange[arcPosition1] = exchangeArc2
                routeChange[arcPosition2] = exchangeArc1
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    print('Move cost incorrect (Route)', relocateCost, costActual)
                    print(routeChange)
                    print(saving)
                    a = input('Stop!')                 

    def testCrossSavings(self, savings, route, routeMapping, solutionMapping, inputSolution):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        for saving in savings:
            
            (relocateCost, (exchangeArc1, preArcI, postArcI, exchangeArc2, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPosition1 = routeMapping[exchangeArc1]
            arcInRoute = route[arcPosition1]
            if exchangeArc1 != arcInRoute and self._inv[exchangeArc1] != arcInRoute: 
                print('Arc1 arc positions incorrect', exchangeArc1, arcInRoute)
                a = input('Stop!')
            
            arcPosition2 = routeMapping[exchangeArc2]
            arcInRoute = route[arcPosition2]        
            if exchangeArc2 != arcInRoute and self._inv[exchangeArc2] != arcInRoute: 
                print('insert arc position incorrect', exchangeArc2, arcInRoute)
                a = input('Stop!')
                
            arcBefore = route[arcPosition1 - 1]
            arcInRoute = route[arcPosition1]
            
            costBefore1 = self._d[arcBefore][arcInRoute]
            costAfter1 = self._d[arcBefore][exchangeArc2]
            
            arcBefore = route[arcPosition2 - 1]
            arcInRoute = route[arcPosition2]
            
            costBefore2 = self._d[arcBefore][arcInRoute]
            costAfter2 = self._d[arcBefore][exchangeArc1]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print('Move cost incorrect', relocateCost, net_cost, exchangeArc1, arcPosition1, exchangeArc2, arcPosition2)
                print(saving)
                a = input('Stop!')
                
            r = random.random()
            if r <= 1:
                solution = copy.deepcopy(inputSolution)
                (k1, p1) = solutionMapping[exchangeArc1]
                (k2, p2) = solutionMapping[exchangeArc2]

                if k1 != k2:
                    route1 = solution[k1]['Route']
                    route2 = solution[k2]['Route']
                    route1seq = route1[p1:]
                    route2seq = route2[p2:]
                    solution[k1]['Route'] = route1[:p1] + route2seq
                    solution[k2]['Route'] = route2[:p2] + route1seq
                    routeChange = self._genGiantMCARPRoute.genMCARPgiantRouteMapping(solution)[0]
                    routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                    costActual = routeCost2 - routeCost
                    print(relocateCost, costActual, moveType)
                    if costActual != relocateCost:
                        print('Move cost incorrect (Route)', relocateCost, costActual)
                        print(exchangeArc1, exchangeArc2)
                        print(k1, p1, k2, p2)
                        print(route)
                        print(routeChange)
                        print(inputSolution)
                        print(solution)
                        a = input('Stop!')  
#                 
    def testDoubleCrossSavings(self, savings, route, solutionMapping, inputSolution):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        routeChange = route[:]
        
        for i, saving1 in enumerate(savings[:-1]):
            (relocateCost1, (exchangeArc1, preArcI, postArcI, exchangeArc2, preArcI, postArcJ), moveType, moveCosts) = saving1
            arcIposA = solutionMapping[exchangeArc1][1]
            arcIposB = solutionMapping[exchangeArc2][1]
            if arcIposA > arcIposB:
                arcIpos1 = arcIposB
                arcIpos2 = arcIposA
            else:
                arcIpos1 = arcIposA
                arcIpos2 = arcIposB                
            for j, saving2 in enumerate(savings[i+1:]):
                (relocateCost2, (exchangeArc1, preArcI, postArcI, exchangeArc2, preArcI, postArcJ), moveType, moveCosts) = saving2
                if relocateCost1 + relocateCost2 >= 0: break
                arcJposA = solutionMapping[exchangeArc1][1]
                arcJposB = solutionMapping[exchangeArc2][1]
                if arcJposA > arcJposB:
                    arcJpos1 = arcJposB
                    arcJpos2 = arcJposA
                else:
                    arcJpos1 = arcJposA
                    arcJpos2 = arcJposB                    
                moveAB = arcIpos1 + 1 < arcJpos1 and arcJpos1 < arcIpos2 - 1 and arcIpos2 + 1 <  arcJpos2
                moveBA = arcJpos1 + 1 < arcIpos1 and arcIpos1 < arcJpos2 - 1 and arcJpos2 + 1 <  arcIpos2
                if moveAB:
                    sec1 = routeChange[:arcIpos1]
                    sec2 = routeChange[arcIpos1:arcJpos1]
                    sec3 = routeChange[arcJpos1:arcIpos2]
                    sec4 = routeChange[arcIpos2:arcJpos2]
                    sec5 = routeChange[arcJpos2:]
                    newRoute = sec1 + sec4 + sec3 + sec2 + sec5
                    routeCostNew = sum([self._d[newRoute[i]][newRoute[i + 1]] for i in range(len(newRoute) - 1)])
                    print(routeCostNew - routeCost, relocateCost1 + relocateCost2)
                elif moveBA:
                    sec1 = routeChange[:arcJpos1]
                    sec2 = routeChange[arcJpos1:arcIpos1]
                    sec3 = routeChange[arcIpos1:arcJpos2]
                    sec4 = routeChange[arcJpos2:arcIpos2]
                    sec5 = routeChange[arcIpos2:]
                    newRoute = sec1 + sec4 + sec3 + sec2 + sec5
                    routeCostNew = sum([self._d[newRoute[i]][newRoute[i + 1]] for i in range(len(newRoute) - 1)])
                    print(routeCostNew - routeCost, relocateCost1 + relocateCost2)
                 
                
    def testFlipMove(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        for saving in savings:
            (relocateCost, (exchangeArc1, preArcI, postArcI, arcJ, preArcJ, postArcJ), moveType, moveCosts) = saving
            
            arcPosition1 = routeMapping[exchangeArc1] 
            arcInRoute = route[arcPosition1]
            if self._inv[exchangeArc1] != arcInRoute: 
                print('Arc1 arc positions incorrect', exchangeArc1, arcInRoute)
                a = input('Stop!')
                
            arcBefore = route[arcPosition1 - 1]
            arcInRoute = route[arcPosition1]
            arcAfter = route[arcPosition1 + 1]
            
            costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter1 = self._d[arcBefore][exchangeArc1] + self._d[exchangeArc1][arcAfter]
            
            net_cost = costAfter1 - costBefore1
            if net_cost != relocateCost:
                print('Move cost incorrect')
                print(saving)
                a = input('Stop!')
            
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                routeChange[arcPosition1] = exchangeArc1
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    print('Move cost incorrect (Route)', relocateCost, costActual)
                    print(routeChange)
                    print(saving)
                    a = input('Stop!')   
    
    def testRemoveInsertDepot(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate, preArcI, postArcI, dummyArc, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionRemove = routeMapping[arcRelocate]
            arcInRoute = route[arcPositionRemove]
            if arcRelocate != arcInRoute and self._inv[arcRelocate] != arcInRoute: 
                print('Remove arc positions incorrect', arcRelocate, arcInRoute)
                a = input('Stop!')
            preArcPosition = routeMapping[preArcJ]
            arcPositionDummy = preArcPosition + 1
            arcInRoute = route[arcPositionDummy]        
            if arcInRoute != self._info.depotnewkey: 
                print('insert arc position incorrect', arcInRoute, self._info.depotArc)
                a = input('Stop!')
                
            arcBefore = route[arcPositionRemove - 1]
            arcInRoute = route[arcPositionRemove]
            arcAfter = route[arcPositionRemove + 1]
            
            costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter1 = self._d[arcBefore][arcAfter]
            
            insertBefore = route[arcPositionDummy - 1]
            insertAfter = route[arcPositionDummy]
            
            costBefore2 = self._d[insertBefore][insertAfter]
            costAfter2 = self._d[insertBefore][arcRelocate] + self._d[arcRelocate][insertAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print('Move cost incorrect', relocateCost, net_cost)
                a = input('Stop!')
                
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                if arcPositionRemove < arcPositionDummy:
                    routeChange.insert(arcPositionDummy, arcRelocate)
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionDummy, arcRelocate)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    print('Move cost incorrect', relocateCost, costActual)
                    a = input('Stop!')

    def testCrossEndSavings(self, savings, route, routeMapping, solutionMapping, inputSolution):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        for saving in savings:
            
            (relocateCost, (exchangeArc1, preArcI, postArcI, exchangeArc2, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPosition1 = routeMapping[exchangeArc1]
            arcInRoute = route[arcPosition1]
            if exchangeArc1 != arcInRoute: 
                print('Cross arc positions incorrect', exchangeArc1, arcInRoute)
                a = input('Stop!')
            preArcPosition = routeMapping[preArcJ]
            arcPositionDummy = preArcPosition + 1
            arcInRoute = route[arcPositionDummy]        
            if arcInRoute != self._info.depotnewkey: 
                print('insert arc position incorrect', arcInRoute, self._info.depotArc)
                a = input('Stop!')
                
            arcBefore = route[arcPosition1 - 1]
            arcInRoute = route[arcPosition1]
            
            dummyArc = route[arcPositionDummy]
            
            costBefore1 = self._d[arcBefore][arcInRoute]
            costAfter1 = self._d[arcBefore][dummyArc]
            
            arcBefore = route[preArcPosition]
            arcInRoute = route[arcPositionDummy]
            
            costBefore2 = self._d[arcBefore][dummyArc]
            costAfter2 = self._d[arcBefore][exchangeArc1]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print('Move cost incorrect', relocateCost, net_cost, exchangeArc1, arcPosition1, exchangeArc2, arcPositionDummy)
                print(saving)
                a = input('Stop!')
                
            r = random.random()
            if r <= 1:
                solution = copy.deepcopy(inputSolution)
                (k1, p1) = solutionMapping[exchangeArc1]
                (k2, p2) = solutionMapping[preArcJ]

                if k1 != k2:
                    route1 = solution[k1]['Route']
                    route2 = solution[k2]['Route']
                    route1seq = route1[p1:]
                    route2seq = route2[p2 + 1:]
                    solution[k1]['Route'] = route1[:p1] + route2seq
                    solution[k2]['Route'] = route2[:p2 + 1] + route1seq
                    routeChange = self._genGiantMCARPRoute.genMCARPgiantRouteMapping(solution)[0]
                    routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                    costActual = routeCost2 - routeCost
                    print(relocateCost, costActual, moveType)
                    if costActual != relocateCost:
                        print('Move cost incorrect (Route)', relocateCost, costActual)
                        print(exchangeArc1, exchangeArc2)
                        print(k1, p1, k2, p2)
                        print('R1i',inputSolution[k1]['Route'])
                        print('R2i',inputSolution[k2]['Route'])
                        print('R1',solution[k1]['Route'])
                        print('R2',solution[k2]['Route'])
                        print(routeChange)
                        print(inputSolution)
                        print(solution)
                        a = input('Stop!')  

    def testDoubleRelocateMoves(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate1, preArcI, postArcI, arcToRelocateBefore, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcRelocate2 = postArcJ
            arcPositionRemove = routeMapping[arcRelocate1]
            arcInRoute = route[arcPositionRemove]
            arcInRoute2 = route[arcPositionRemove + 1] 
            if arcRelocate1 != arcInRoute and arcRelocate2 != arcInRoute2: 
                raise NameError('Remove arc positions incorrect', arcRelocate1, arcInRoute, arcRelocate2, arcInRoute2)
            
            arcPositionInsert = routeMapping[arcToRelocateBefore]
            arcInRoute = route[arcPositionInsert]        
            if arcToRelocateBefore != arcInRoute: 
                raise NameError('insert arc position incorrect', arcToRelocateBefore, arcInRoute)
            
            arcBefore = route[arcPositionRemove - 1]
            arcInRoute1 = route[arcPositionRemove]
            arcInRoute2 = route[arcPositionRemove + 1]
            arcAfter = route[arcPositionRemove + 2]
            
            costBefore1 = self._d[arcBefore][arcRelocate1] + self._d[arcRelocate2][arcAfter]
            costAfter1 = self._d[arcBefore][arcAfter]
            
            insertBefore = route[arcPositionInsert - 1]
            insertAfter = route[arcPositionInsert]
            
            costBefore2 = self._d[insertBefore][insertAfter]
            costAfter2 = self._d[insertBefore][arcRelocate1] + self._d[arcRelocate2][insertAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print(saving, arcPositionRemove, arcPositionRemove + 1, arcPositionInsert)
                raise NameError('Returned move cost incorrect', relocateCost, net_cost)
                
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                if arcPositionRemove < arcPositionInsert:
                    routeChange.insert(arcPositionInsert, arcRelocate1)
                    routeChange.insert(arcPositionInsert + 1, arcRelocate2)
                    del routeChange[arcPositionRemove + 1]
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove + 1]
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionInsert, arcRelocate1)
                    routeChange.insert(arcPositionInsert + 1, arcRelocate2)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    raise NameError('Actual move cost incorrect', relocateCost, costActual)

class TestMoveCostsMCARPTIF(object):
    '''
    Test move calculations to see if they are accurate. No longer valid. 
    '''
    def __init__(self, info):
        '''
        Class initialization values.
        '''
        # Problem info
        self._info = info
        self._d = info.d
        self._depot = info.depotnewkey
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._nReqArcs = len(self._reqArcs)
        self._nEliments = len(self._d)
        self._reqArcsSet = set(self._reqArcs)
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self._arcsL = [arc for arc in self._reqArcs if arc not in self._edgesS]
        self._arcsS = set(self._arcsL)
        self._genGiantMCARPTIFRoute = MCARPTIFmoveFunctions(info)
        self._if_cost = info.if_cost_np
        self._if_arc = info.if_arc_np

    def testRelocateSavingsOld(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate, preArcI, postArcI, arcToRelocateBefore, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionRemove = routeMapping[arcRelocate]
            arcInRoute = route[arcPositionRemove]
            if arcRelocate != arcInRoute and self._inv[arcRelocate] != arcInRoute: 
                raise NameError('Remove arc positions incorrect', arcRelocate, arcInRoute)
            
            arcPositionInsert = routeMapping[arcToRelocateBefore]
            arcInRoute = route[arcPositionInsert]        
            if arcToRelocateBefore != arcInRoute: 
                raise NameError('insert arc position incorrect', arcToRelocateBefore, arcInRoute)
            
            arcBefore = route[arcPositionRemove - 1]
            arcInRoute = route[arcPositionRemove]
            arcAfter = route[arcPositionRemove + 1]
            
            costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter1 = self._d[arcBefore][arcAfter]
            
            insertBefore = route[arcPositionInsert - 1]
            insertAfter = route[arcPositionInsert]
            
            costBefore2 = self._d[insertBefore][insertAfter]
            costAfter2 = self._d[insertBefore][arcRelocate] + self._d[arcRelocate][insertAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                raise NameError('Returned move cost incorrect', relocateCost, net_cost)
                
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                if arcPositionRemove < arcPositionInsert:
                    routeChange.insert(arcPositionInsert, arcRelocate)
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionInsert, arcRelocate)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    raise NameError('Actual move cost incorrect', relocateCost, costActual)

    def testRemoveInsertDepot(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate, preArcI, postArcI, dummyArc, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionRemove = routeMapping[arcRelocate]
            arcInRoute = route[arcPositionRemove]
            if arcRelocate != arcInRoute and self._inv[arcRelocate] != arcInRoute: 
                print('Remove arc positions incorrect', arcRelocate, arcInRoute)
                a = input('Stop!')
            preArcPosition = routeMapping[preArcJ]
            arcPositionDummy = preArcPosition + 1
            arcInRoute = route[arcPositionDummy]        
            if arcInRoute not in self._info.IFarcsnewkey: 
                print('insert arc position incorrect', arcInRoute, self._info.IFarcsnewkey)
                a = input('Stop!')
                
            arcBefore = route[arcPositionRemove - 1]
            arcInRoute = route[arcPositionRemove]
            arcAfter = route[arcPositionRemove + 1]
            
            costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter1 = self._d[arcBefore][arcAfter]
            
            insertBefore = route[arcPositionDummy - 1]
            insertAfter = route[arcPositionDummy]
            
            costBefore2 = self._d[insertBefore][insertAfter]
            costAfter2 = self._d[insertBefore][arcRelocate] + self._d[arcRelocate][insertAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print('Move cost incorrect', relocateCost, net_cost)
                a = input('Stop!')
                
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                if arcPositionRemove < arcPositionDummy:
                    routeChange.insert(arcPositionDummy, arcRelocate)
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionDummy, arcRelocate)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    print('Move cost incorrect', relocateCost, costActual)
                    a = input('Stop!')

    def testExchangeSavingsOld(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (exchangeArc1, perArcI, postArcI, exchangeArc2, preArcI, postArcI), moveType, moveCosts) = saving
            
            
            arcPosition1 = routeMapping[exchangeArc1]
            arcInRoute = route[arcPosition1]
            if exchangeArc1 != arcInRoute and self._inv[exchangeArc1] != arcInRoute: 
                print('Arc1 arc positions incorrect', exchangeArc1, arcInRoute)
                a = input('Stop!')
            
            arcPosition2 = routeMapping[exchangeArc2]
            arcInRoute = route[arcPosition2]        
            if exchangeArc2 != arcInRoute and self._inv[exchangeArc2] != arcInRoute: 
                print('insert arc position incorrect', exchangeArc2, arcInRoute)
                a = input('Stop!')
                
            arcBefore = route[arcPosition1 - 1]
            arcInRoute = route[arcPosition1]
            arcAfter = route[arcPosition1 + 1]
            
            costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter1 = self._d[arcBefore][exchangeArc2] + self._d[exchangeArc2][arcAfter]
            
            arcBefore = route[arcPosition2 - 1]
            arcInRoute = route[arcPosition2]
            arcAfter = route[arcPosition2 + 1]
            
            costBefore2 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
            costAfter2 = self._d[arcBefore][exchangeArc1] + self._d[exchangeArc1][arcAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print('Move cost incorrect', relocateCost, net_cost, exchangeArc1, arcPosition1, exchangeArc2, arcPosition2)
                print(saving)
                a = input('Stop!')
                
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                routeChange[arcPosition1] = exchangeArc2
                routeChange[arcPosition2] = exchangeArc1
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    print('Move cost incorrect (Route)', relocateCost, costActual)
                    print(routeChange)
                    print(saving)
                    a = input('Stop!')              

    def testDoubleRelocateMoves(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate1, preArcI, postArcI, arcToRelocateBefore, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcRelocate2 = postArcJ
            arcPositionRemove = routeMapping[arcRelocate1]
            arcInRoute = route[arcPositionRemove]
            arcInRoute2 = route[arcPositionRemove + 1] 
            if arcRelocate1 != arcInRoute and arcRelocate2 != arcInRoute2: 
                raise NameError('Remove arc positions incorrect', arcRelocate1, arcInRoute, arcRelocate2, arcInRoute2)
            
            arcPositionInsert = routeMapping[arcToRelocateBefore]
            arcInRoute = route[arcPositionInsert]        
            if arcToRelocateBefore != arcInRoute: 
                raise NameError('insert arc position incorrect', arcToRelocateBefore, arcInRoute)
            
            arcBefore = route[arcPositionRemove - 1]
            arcInRoute1 = route[arcPositionRemove]
            arcInRoute2 = route[arcPositionRemove + 1]
            arcAfter = route[arcPositionRemove + 2]
            
            costBefore1 = self._d[arcBefore][arcRelocate1] + self._d[arcRelocate2][arcAfter]
            costAfter1 = self._d[arcBefore][arcAfter]
            
            insertBefore = route[arcPositionInsert - 1]
            insertAfter = route[arcPositionInsert]
            
            costBefore2 = self._d[insertBefore][insertAfter]
            costAfter2 = self._d[insertBefore][arcRelocate1] + self._d[arcRelocate2][insertAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print(saving, arcPositionRemove, arcPositionRemove + 1, arcPositionInsert)
                raise NameError('Returned move cost incorrect', relocateCost, net_cost)
                
            r = random.random()
            if r <= 1:
                routeChange = route[:]
                if arcPositionRemove < arcPositionInsert:
                    routeChange.insert(arcPositionInsert, arcRelocate1)
                    routeChange.insert(arcPositionInsert + 1, arcRelocate2)
                    del routeChange[arcPositionRemove + 1]
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove + 1]
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionInsert, arcRelocate1)
                    routeChange.insert(arcPositionInsert + 1, arcRelocate2)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    raise NameError('Actual move cost incorrect', relocateCost, costActual)

    def testRelocatePreIFSavings(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate, preArcI, postArcI, arcToRelocateAfter, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionRemove = routeMapping[arcRelocate]
            arcInRoute = route[arcPositionRemove]
            
            if arcRelocate != arcInRoute and self._inv[arcRelocate] != arcInRoute: 
                raise NameError('Remove arc positions incorrect', arcRelocate, arcInRoute)
            
            if moveType == 'relocate_PreIF':
                arcBefore = route[arcPositionRemove - 1]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 1]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._d[arcBefore][arcAfter]
            
            elif moveType == 'relocatePreIF_PreIF':
                arcBefore = route[arcPositionRemove - 1]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 2]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._if_cost[arcInRoute][arcAfter]
                costAfter1 = self._if_cost[arcBefore][arcAfter]
            
            elif moveType == 'relocatePostIF_PreIF':
                arcBefore = route[arcPositionRemove - 2]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 1]
            
                costBefore1 = self._if_cost[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._if_cost[arcBefore][arcAfter]

            arcPositionInsert = routeMapping[arcToRelocateAfter]
            arcInRoute = route[arcPositionInsert]     

            if arcToRelocateAfter != arcInRoute: 
                raise NameError('insert arc position incorrect', arcToRelocateAfter, arcInRoute) 
                       
            insertAfter = route[arcPositionInsert]
            insertPostIF = route[arcPositionInsert + 2]
    
            costBefore2 = self._if_cost[insertAfter][insertPostIF]
            costAfter2 = self._d[insertAfter][arcRelocate] + self._if_cost[arcRelocate][insertPostIF]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print (saving)
                print (costAfter1 - costBefore1, costAfter2 - costBefore2)
                print (moveCosts)
                raise NameError('Returned move cost incorrect', relocateCost, net_cost)
                
            r = random.random()
            if r <= 1:
                #print(route)
                routeChange = route[:]
                #print('IF', routeChange[arcPositionInsert + 1])
                routeChange[arcPositionInsert + 1] = self._if_arc[arcRelocate][insertPostIF]
                
                if moveType == 'relocatePreIF_PreIF':
                    routeChange[arcPositionRemove + 1] = self._if_arc[arcBefore][arcAfter]
                    
                if moveType == 'relocatePostIF_PreIF':
                    routeChange[arcPositionRemove - 1] = self._if_arc[arcBefore][arcAfter]
                
                if arcPositionRemove < arcPositionInsert + 1:
                    routeChange.insert(arcPositionInsert + 1, arcRelocate)
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionInsert + 1, arcRelocate)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    print(routeChange)
                    print(saving)
                    raise NameError('Actual move cost incorrect', relocateCost, costActual)

    def testRelocatePostIFSavings(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate, preArcI, postArcI, arcToRelocateBefore, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionRemove = routeMapping[arcRelocate]
            arcInRoute = route[arcPositionRemove]
            
            if arcRelocate != arcInRoute and self._inv[arcRelocate] != arcInRoute: 
                raise NameError('Remove arc positions incorrect', arcRelocate, arcInRoute)
            
            if moveType == 'relocate_PostIF':
                arcBefore = route[arcPositionRemove - 1]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 1]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._d[arcBefore][arcAfter]
            
            elif moveType == 'relocatePreIF_PostIF':
                arcBefore = route[arcPositionRemove - 1]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 2]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._if_cost[arcInRoute][arcAfter]
                costAfter1 = self._if_cost[arcBefore][arcAfter]
            
            elif moveType == 'relocatePostIF_PostIF':
                arcBefore = route[arcPositionRemove - 2]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 1]
            
                costBefore1 = self._if_cost[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._if_cost[arcBefore][arcAfter]

            arcPositionInsert = routeMapping[arcToRelocateBefore]
            arcInRoute = route[arcPositionInsert]     

            if arcToRelocateBefore != arcInRoute: 
                raise NameError('insert arc position incorrect', arcToRelocateBefore, arcInRoute) 
                       
            insertPreIF = route[arcPositionInsert - 2]
            insertBefore = route[arcPositionInsert]
    
            costBefore2 = self._if_cost[insertPreIF][insertBefore]
            costAfter2 = self._if_cost[insertPreIF][arcRelocate] + self._d[arcRelocate][insertBefore]
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print (saving)
                print (costAfter1 - costBefore1, costAfter2 - costBefore2)
                print (moveCosts)
                raise NameError('Returned move cost incorrect', relocateCost, net_cost)
                
            r = random.random()
            if r <= 1:
                #print(route)
                routeChange = route[:]
                #print('IF', routeChange[arcPositionInsert + 1])
                routeChange[arcPositionInsert - 1] = self._if_arc[insertPreIF][arcRelocate]
                if arcPositionRemove < arcPositionInsert:
                    routeChange.insert(arcPositionInsert, arcRelocate)
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionInsert, arcRelocate)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    print('')
                    print(route)
                    print(routeChange)
                    print(saving)
                    raise NameError('Actual move cost incorrect', relocateCost, costActual)

    def testRelocateSavings(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (relocateCost, (arcRelocate, preArcI, postArcI, arcToRelocateBefore, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionRemove = routeMapping[arcRelocate]
            arcInRoute = route[arcPositionRemove]
            
            if arcRelocate != arcInRoute and self._inv[arcRelocate] != arcInRoute: 
                raise NameError('Remove arc positions incorrect', arcRelocate, arcInRoute)
            
            if moveType == 'relocate':
                arcBefore = route[arcPositionRemove - 1]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 1]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._d[arcBefore][arcAfter]
            
            elif moveType == 'relocatePreArcIF':
                arcBefore = route[arcPositionRemove - 1]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 2]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._if_cost[arcInRoute][arcAfter]
                costAfter1 = self._if_cost[arcBefore][arcAfter]
            
            elif moveType == 'relocatePostArcIF':
                arcBefore = route[arcPositionRemove - 2]
                arcInRoute = route[arcPositionRemove]
                arcAfter = route[arcPositionRemove + 1]
            
                costBefore1 = self._if_cost[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._if_cost[arcBefore][arcAfter]

            arcPositionInsert = routeMapping[arcToRelocateBefore]
            arcInRoute = route[arcPositionInsert]     

            if arcToRelocateBefore != arcInRoute: 
                raise NameError('insert arc position incorrect', arcToRelocateBefore, arcInRoute) 
                       
            insertPreIF = route[arcPositionInsert - 1]
            insertBefore = route[arcPositionInsert]
    
            costBefore2 = self._d[insertPreIF][insertBefore]
            costAfter2 = self._d[insertPreIF][arcRelocate] + self._d[arcRelocate][insertBefore]
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print (saving)
                print (costAfter1 - costBefore1, costAfter2 - costBefore2)
                print (moveCosts)
                raise NameError('Returned move cost incorrect', relocateCost, net_cost)
                
            r = random.random()
            if r <= 1:
                #print(route)
                routeChange = route[:]
                #print('IF', routeChange[arcPositionInsert + 1])
                if arcPositionRemove < arcPositionInsert:
                    routeChange.insert(arcPositionInsert, arcRelocate)
                    del routeChange[arcPositionRemove]
                else:
                    del routeChange[arcPositionRemove]
                    routeChange.insert(arcPositionInsert, arcRelocate)
                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(relocateCost, costActual, moveType)
                if costActual != relocateCost:
                    print(routeChange)
                    print(saving)
                    raise NameError('Actual move cost incorrect', relocateCost, costActual)

    def testExchangeSavings(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (excCost, (arcExI, preArcI, postArcI, arcExJ, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionI = routeMapping[arcExI]
            arcInRoute = route[arcPositionI]
            
            if arcExI != arcInRoute and self._inv[arcExI] != arcInRoute: 
                raise NameError('Remove arc positions incorrect', arcExI, arcInRoute)
            
            if moveType.find('1excPostIF') != -1:
                #print('1excPostIF')
                arcBefore = route[arcPositionI - 2]
                arcInRoute = route[arcPositionI]
                arcAfter = route[arcPositionI + 1]
            
                costBefore1 = self._if_cost[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._if_cost[arcBefore][arcExJ] + self._d[arcExJ][arcAfter]
                
            elif moveType.find('1excPreIF') != -1:
                #print('1excPreIF')
                arcBefore = route[arcPositionI - 1]
                arcInRoute = route[arcPositionI]
                arcAfter = route[arcPositionI + 2]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._if_cost[arcInRoute][arcAfter]
                costAfter1 = self._d[arcBefore][arcExJ] + self._if_cost[arcExJ][arcAfter]
            
            else:
                #print('normal')
                arcBefore = route[arcPositionI - 1]
                arcInRoute = route[arcPositionI]
                arcAfter = route[arcPositionI + 1]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._d[arcBefore][arcExJ] + self._d[arcExJ][arcAfter]

            arcPositionJ = routeMapping[arcExJ]
            arcInRoute = route[arcPositionJ]
            
            if arcExJ != arcInRoute and self._inv[arcExJ] != arcInRoute: 
                raise NameError('Remove arc positions incorrect', arcExJ, arcInRoute)
            
            if moveType.find('2excPostIF') != -1:
                #print('2excPostIF')
                arcBefore = route[arcPositionJ - 2]
                arcInRoute = route[arcPositionJ]
                arcAfter = route[arcPositionJ + 1]
            
                costBefore2 = self._if_cost[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter2 = self._if_cost[arcBefore][arcExI] + self._d[arcExI][arcAfter]
            
            elif moveType.find('2excPreIF') != -1:
                #print('2excPreIF')
                arcBefore = route[arcPositionJ - 1]
                arcInRoute = route[arcPositionJ]
                arcAfter = route[arcPositionJ + 2]
            
                costBefore2 = self._d[arcBefore][arcInRoute] + self._if_cost[arcInRoute][arcAfter]
                costAfter2 = self._d[arcBefore][arcExI] + self._if_cost[arcExI][arcAfter]
            
            else:
                #print('normal')
                arcBefore = route[arcPositionJ - 1]
                arcInRoute = route[arcPositionJ]
                arcAfter = route[arcPositionJ + 1]
            
                costBefore2 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter2 = self._d[arcBefore][arcExI] + self._d[arcExI][arcAfter]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            
            
            if net_cost != excCost:
                print (saving)
                print (costAfter1 - costBefore1, costAfter2 - costBefore2)
                print (moveCosts)
                raise NameError('Returned move cost incorrect', excCost, net_cost)
                
            r = random.random()
            if r <= 1:
                #print(route)
                routeChange = route[:]
                #print('IF', routeChange[arcPositionInsert + 1])
                
                routeChange[arcPositionJ] = arcExI
                routeChange[arcPositionI] = arcExJ
                
                if moveType.find('1excPostIF') != -1:
                    route[arcPositionI - 1] = self._if_arc[preArcI][arcExJ]
                if moveType.find('1excPreIF') != -1:
                    route[arcPositionI + 1] = self._if_arc[arcExJ][postArcI]
                if moveType.find('2excPostIF') != -1:
                    route[arcPositionJ - 1] = self._if_arc[preArcJ][arcExI]
                if moveType.find('2excPreIF') != -1:
                    route[arcPositionJ + 1] = self._if_arc[arcExI][postArcJ]

                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(excCost, costActual, moveType)
                if costActual != excCost:
                    print(routeChange)
                    print(saving)
                    raise NameError('Actual move cost incorrect', excCost, costActual)


    def testCrossSavings(self, savings, route, routeMapping, solutionMapping, inputSolution):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        for saving in savings:
            
            (relocateCost, (exchangeArc1, preArcI, postArcI, exchangeArc2, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPosition1 = routeMapping[exchangeArc1]
            arcInRoute = route[arcPosition1]
            if exchangeArc1 != arcInRoute and self._inv[exchangeArc1] != arcInRoute: 
                raise NameError('Arc1 arc positions incorrect', exchangeArc1, arcInRoute)
            
            arcPosition2 = routeMapping[exchangeArc2]
            arcInRoute = route[arcPosition2]        
            if exchangeArc2 != arcInRoute and self._inv[exchangeArc2] != arcInRoute: 
                raise NameError('insert arc position incorrect', exchangeArc2, arcInRoute)
            
            if moveType.find('_1crossPostIF') != -1:
                arcBefore = route[arcPosition1 - 2]
                arcInRoute = route[arcPosition1]
                
                costBefore1 = self._if_cost[arcBefore][arcInRoute]
                costAfter1 = self._if_cost[arcBefore][exchangeArc2]
            else:
                arcBefore = route[arcPosition1 - 1]
                arcInRoute = route[arcPosition1]
                
                costBefore1 = self._d[arcBefore][arcInRoute]
                costAfter1 = self._d[arcBefore][exchangeArc2]
            

            if moveType.find('_2crossPostIF') != -1:
                arcBefore = route[arcPosition2 - 2]
                arcInRoute = route[arcPosition2]
                
                costBefore2 = self._if_cost[arcBefore][arcInRoute]
                costAfter2 = self._if_cost[arcBefore][exchangeArc1]
            else:
                arcBefore = route[arcPosition2 - 1]
                arcInRoute = route[arcPosition2]
                
                costBefore2 = self._d[arcBefore][arcInRoute]
                costAfter2 = self._d[arcBefore][exchangeArc1]
            
            net_cost = costAfter1 - costBefore1 + costAfter2 - costBefore2
            if net_cost != relocateCost:
                print('Move cost incorrect', relocateCost, net_cost, exchangeArc1, arcPosition1, exchangeArc2, arcPosition2)
                print(saving)
                raise NameError('Stop!')
                
            r = random.random()
            if r <= 1:
                solution = copy.deepcopy(inputSolution)
                (k1, p1, n1) = solutionMapping[exchangeArc1]
                (k2, p2, n2) = solutionMapping[exchangeArc2]
                
                if k1 != k2 or p1 != p2:
                    
                    if moveType.find('_1crossPostIF') != -1 and k1 == k2 and p1 == p2 - 1: continue
                    if moveType.find('_2crossPostIF') != -1 and k1 == k2 and p2 == p1 - 1: continue

                    if p1 == len(solution[k1]['Trips']) - 1: endI = -2
                    else: endI = -1
                    if p2 == len(solution[k1]['Trips']) - 1: endJ = -2
                    else: endJ = -1
                    
                    route1 = solution[k1]['Trips']
                    route2 = solution[k2]['Trips']
                    
                    trip1 = route1[p1]
                    trip2 = route2[p2]
                    
                    if solution[k1]['Trips'][p1][endI] == solution[k2]['Trips'][p2][endJ]:
                        if p1 == len(route1) - 1 and p2 != len(route2) - 1:
                            solution[k1]['Trips'][p1] = trip1[:n1] + trip2[n2:] + [trip1[-1]] 
                            solution[k2]['Trips'][p2] = trip2[:n2] + trip1[n1:-1]
                        elif p2 == len(route2) - 1 and p1 != len(route1) - 1:
                            solution[k1]['Trips'][p1] = trip1[:n1] + trip2[n2:-1]   
                            solution[k2]['Trips'][p2] = trip2[:n2] + trip1[n1:] + [trip2[-1]] 
                        else:
                            solution[k1]['Trips'][p1] = trip1[:n1] + trip2[n2:]   
                            solution[k2]['Trips'][p2] = trip2[:n2] + trip1[n1:]
                            
                        if moveType.find('_1crossPostIF') != -1:
                            bestIF = self._if_arc[solution[k1]['Trips'][p1-1][-2]][solution[k1]['Trips'][p1][1]]
                            solution[k1]['Trips'][p1-1][-1] = bestIF
                            solution[k1]['Trips'][p1][0] = bestIF
                        if moveType.find('_2crossPostIF') != -1:
                            bestIF = self._if_arc[solution[k2]['Trips'][p2-1][-2]][solution[k2]['Trips'][p2][1]]
                            solution[k2]['Trips'][p2-1][-1] = bestIF
                            solution[k2]['Trips'][p2][0] = bestIF                            
                            
                        routeChange = self._genGiantMCARPTIFRoute.genMCARPTIFgiantRouteMapping(solution)[0]
                        routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                        costActual = routeCost2 - routeCost
                        
                        print(relocateCost, costActual, moveType)
                        
                        if costActual != relocateCost:
                            print('Move cost incorrect (Route)', relocateCost, costActual)
                            print(saving)
                            print(exchangeArc1, exchangeArc2)
                            print(k1, p1, n1, k2, p2, n2)
                            print(route)
                            print(routeChange)
                            print('')
                            print(inputSolution[k1]['Trips'][p1])
                            print(inputSolution[k2]['Trips'][p2])
                            print('')
                            print(solution[k1]['Trips'][p1])
                            print(solution[k2]['Trips'][p2])
                            raise NameError('error found!') 
                    
                    elif k1 != k2:
                                
                        solution[k1]['Trips'] = route1[:p1] + [trip1[:n1] + trip2[n2:]] + route2[p2 + 1:]      
                        solution[k2]['Trips'] = route2[:p2] + [trip2[:n2] + trip1[n1:]] + route1[p1 + 1:]

                        if moveType.find('_1crossPostIF') != -1:
                            bestIF = self._if_arc[solution[k1]['Trips'][p1-1][-2]][solution[k1]['Trips'][p1][1]]
                            solution[k1]['Trips'][p1-1][-1] = bestIF
                            solution[k1]['Trips'][p1][0] = bestIF
                        elif moveType.find('_2crossPostIF') != -1:
                            bestIF = self._if_arc[solution[k2]['Trips'][p2-1][-2]][solution[k2]['Trips'][p2][1]]
                            solution[k2]['Trips'][p2-1][-1] = bestIF
                            solution[k2]['Trips'][p2][0] = bestIF   

                        routeChange = self._genGiantMCARPTIFRoute.genMCARPTIFgiantRouteMapping(solution)[0]
                        routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                        costActual = routeCost2 - routeCost
                        print(relocateCost, costActual, moveType)
                        if costActual != relocateCost:
                            print('Move cost incorrect (Route)', relocateCost, costActual)
                            print(exchangeArc1, exchangeArc2)
                            print(k1, p1, n1, k2, p2, n2)
                            print(route)
                            print(routeChange)
                            print('')
                            print(inputSolution[k1]['Trips'][p1])
                            print(inputSolution[k2]['Trips'][p2])
                            print('')
                            print(solution[k1]['Trips'][p1])
                            print(solution[k2]['Trips'][p2])
                            raise NameError('error found!') 

    def testDoubleCrossSavings(self, savings, solutionMapping, inputSolution):
        '''
        '''
        
        for i, saving1 in enumerate(savings[:-1]):
            (relocateCost1, (exchangeArc1A, preArcIA, postArcI, exchangeArc2A, preArcJA, postArcJ), moveType1, moveCosts) = saving1
            
            (k1A, p1A, n1A) = solutionMapping[exchangeArc1A]
            (k2A, p2A, n2A) = solutionMapping[exchangeArc2A]
            
            if k1A != k2A or p1A != p2A: continue
            route = inputSolution[k1A]['Trips'][p1A][:]
            routeChange = inputSolution[k1A]['Trips'][p1A][:]
            
            arcIposA = n1A
            arcIposB = n2A
            
            if arcIposA > arcIposB:
                arcIpos1 = arcIposB
                arcIpos2 = arcIposA
            else:
                arcIpos1 = arcIposA
                arcIpos2 = arcIposB                
            for j, saving2 in enumerate(savings[i+1:]):
                (relocateCost2, (exchangeArc1B, preArcIB, postArcI, exchangeArc2B, preArcJB, postArcJ), moveType2, moveCosts) = saving2
                if relocateCost1 + relocateCost2 >= 0: break
                (k1B, p1B, n1B) = solutionMapping[exchangeArc1B]
                (k2B, p2B, n2B) = solutionMapping[exchangeArc2B]
                
                if k1B != k2B or p1B != p2B: continue
                if k1A != k1B or p1A != p1B: continue

                arcJposA = n1B
                arcJposB = n2B
                
                if arcJposA > arcJposB:
                    arcJpos1 = arcJposB
                    arcJpos2 = arcJposA
                else:
                    arcJpos1 = arcJposA
                    arcJpos2 = arcJposB  
                                      
                moveAB = arcIpos1 + 1 < arcJpos1 and arcJpos1 < arcIpos2 - 1 and arcIpos2 + 1 <  arcJpos2
                moveBA = arcJpos1 + 1 < arcIpos1 and arcIpos1 < arcJpos2 - 1 and arcJpos2 + 1 <  arcIpos2
                
                if moveAB or moveBA:
                    routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
                    #print(routeCost)
                
                if moveType1.find('_1crossPostIF') != -1:
                    routeChange[n1A - 1] = self._if_arc[preArcIA][exchangeArc2A]
                elif moveType1.find('_2crossPostIF') != -1:
                    routeChange[n2A - 1] = self._if_arc[preArcJA][exchangeArc1A]
 
                if moveType2.find('_1crossPostIF') != -1:
                    routeChange[n1B - 1] = self._if_arc[preArcIB][exchangeArc2B]
                elif moveType2.find('_2crossPostIF') != -1:
                    routeChange[n2B - 1] = self._if_arc[preArcJB][exchangeArc1B]
                    
                if moveAB:
                    sec1 = routeChange[:arcIpos1]
                    sec2 = routeChange[arcIpos1:arcJpos1]
                    sec3 = routeChange[arcJpos1:arcIpos2]
                    sec4 = routeChange[arcIpos2:arcJpos2]
                    sec5 = routeChange[arcJpos2:]
                    newRoute = sec1 + sec4 + sec3 + sec2 + sec5
                    routeCostNew = sum([self._d[newRoute[i]][newRoute[i + 1]] for i in range(len(newRoute) - 1)])
                    #print(saving1)
                    #print(saving2)
                    print(routeCostNew - routeCost, relocateCost1 + relocateCost2, 'doubleCross')
                    #print(route)
                    #print(newRoute)
                elif moveBA:
                    sec1 = routeChange[:arcJpos1]
                    sec2 = routeChange[arcJpos1:arcIpos1]
                    sec3 = routeChange[arcIpos1:arcJpos2]
                    sec4 = routeChange[arcJpos2:arcIpos2]
                    sec5 = routeChange[arcIpos2:]
                    newRoute = sec1 + sec4 + sec3 + sec2 + sec5
                    routeCostNew = sum([self._d[newRoute[i]][newRoute[i + 1]] for i in range(len(newRoute) - 1)])
                    #print(saving1)
                    #print(saving2)
                    print(routeCostNew - routeCost, relocateCost1 + relocateCost2, 'doubleCross')
                    #print(route)
                    #print(newRoute)

    def testFlipSavings(self, savings, route, routeMapping):
        '''
        '''
        routeCost = sum([self._d[route[i]][route[i + 1]] for i in range(len(route) - 1)])
        print(routeCost)
        
        for saving in savings:
            
            (excCost, (arcExI, preArcI, postArcI, arcExJ, preArcJ, postArcJ), moveType, moveCosts) = saving
            arcPositionI = routeMapping[arcExI]
            arcInRoute = route[arcPositionI]
            
            if arcExI != arcInRoute or arcExJ != self._inv[arcExI]: 
                raise NameError('Remove arc positions incorrect', arcExI, arcInRoute)
            
            if moveType.find('excPostIF') != -1:
                #print('1excPostIF')
                arcBefore = route[arcPositionI - 2]
                arcInRoute = route[arcPositionI]
                arcAfter = route[arcPositionI + 1]
            
                costBefore1 = self._if_cost[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._if_cost[arcBefore][arcExJ] + self._d[arcExJ][arcAfter]
                
            elif moveType.find('excPreIF') != -1:
                #print('1excPreIF')
                arcBefore = route[arcPositionI - 1]
                arcInRoute = route[arcPositionI]
                arcAfter = route[arcPositionI + 2]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._if_cost[arcInRoute][arcAfter]
                costAfter1 = self._d[arcBefore][arcExJ] + self._if_cost[arcExJ][arcAfter]
            
            else:
                #print('normal')
                arcBefore = route[arcPositionI - 1]
                arcInRoute = route[arcPositionI]
                arcAfter = route[arcPositionI + 1]
            
                costBefore1 = self._d[arcBefore][arcInRoute] + self._d[arcInRoute][arcAfter]
                costAfter1 = self._d[arcBefore][arcExJ] + self._d[arcExJ][arcAfter]

            
            net_cost = costAfter1 - costBefore1
                        
            if net_cost != excCost:
                print (saving)
                print (costAfter1 - costBefore1)
                print (moveCosts)
                raise NameError('Returned move cost incorrect', excCost, net_cost)
                
            r = random.random()
            if r <= 1:
                #print(route)
                routeChange = route[:]
                #print('IF', routeChange[arcPositionInsert + 1])
                
                routeChange[arcPositionI] = arcExJ
                
                if moveType.find('excPostIF') != -1:
                    route[arcPositionI - 1] = self._if_arc[preArcI][arcExJ]
                if moveType.find('excPreIF') != -1:
                    route[arcPositionI + 1] = self._if_arc[arcExJ][postArcI]

                routeCost2 = sum([self._d[routeChange[i]][routeChange[i + 1]] for i in range(len(routeChange) - 1)])
                costActual = routeCost2 - routeCost
                print(excCost, costActual, moveType)
                if costActual != excCost:
                    print(routeChange)
                    print(saving)
                    raise NameError('Actual move cost incorrect', excCost, costActual)

                    
class CalcMoveCosts(object):
    '''
    Calculate move costs for a Arc Routing Problems. Input is one route, can be a giant route, 
    and the set of arcs between which moves should be evaluated.
    '''
    
    def __init__(self, info, cModules = True, nnList = None):
        '''
        Class initialization values.
        '''
        # Problem info
        self._info = info
        self._depot = self._info.depotnewkey
        self._d = info.d
        self._inv = info.reqInvArcList
        self._edgesL = [arc for arc, invFlag in enumerate(self._inv) if invFlag != None]
        self._edgesS = set(self._edgesL)
        self.cModules = cModules
        self.route = []
        self._dumpCost = info.dumpCost
        self._dummyArcs = {self._depot}
        
        if nnList == None:
            print(nnList)
            self._nnList = [[]]
        else:
            self._nnList = nnList
    
        self.autoInvCosts = True   
        
        
    def initiateCmodules(self):
        '''
        '''
        if self.cModules:
            c_calcMoveCost.init_input(self._d, self._nnList, self._inv, self._dumpCost, self._dummyArcs)
        
    def freeCmodules(self):
        '''
        '''
        if self.cModules:
            c_calcMoveCost.free_input()
    
    def setRoute(self, route):
        '''
        '''
        if self.cModules:
            c_calcMoveCost.init_route(route)
        else:
            self.route = route
            routeMapping = [-1]*len(self._d)
            for i, arc in enumerate(route):
                routeMapping[arc] = i
                if arc in self._edgesS:
                    routeMapping[self._inv[arc]] = i
            self.routeMapping = routeMapping
        

    def freeRoute(self):
        '''
        '''
        if self.cModules:
            c_calcMoveCost.free_route()     
    
    def _twoArcCost(self, preArc, arc):
        '''
        Calculate the cost between two arcs.
        '''
        if self.cModules: 
            return(c_calcMoveCost._twoArcCost(preArc, arc))
        else: 
            cost = self._d[preArc][arc]
        return(cost)

    def _twoSeqCost(self, arcPosition):
        '''
        Calculate the cost of two consecutive arcs in a route.
        '''
        if self.cModules: 
            return(c_calcMoveCost._twoSeqCost(arcPosition))
        else:
            preArc = self.route[arcPosition - 1]
            arc = self.route[arcPosition]
            cost = self._twoArcCost(preArc, arc)
        return(cost, preArc, arc)
    
    def _threeArcCost(self, preArc, arc, postArc):
        '''
        Calculate the cost between three arcs.
        '''
        if self.cModules: 
            return(c_calcMoveCost._threeArcCost(preArc, arc, postArc))
        else:
            cost = self._d[preArc][arc] + self._d[arc][postArc]
        return(cost)
    
    def _threeSeqCost(self, arcPosition):
        '''
        Calculate the cost of three consecutive arcs in a route.
        '''
        if self.cModules:
            return(c_calcMoveCost._threeSeqCost(arcPosition))
        else:         
            preArc = self.route[arcPosition - 1]
            arc = self.route[arcPosition]
            postArc = self.route[arcPosition + 1]
            cost = self._threeArcCost(preArc, arc, postArc)
        return(cost, preArc, arc, postArc)
        
    def _calcRemoveCost(self, arcPosition):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            return(c_calcMoveCost._calcRemoveCost(arcPosition))
        else:    
            (currentCost, preArc, currentArc, postArc) = self._threeSeqCost(arcPosition)
            newCost = self._twoArcCost(preArc, postArc)
            netCost = newCost - currentCost
        return(netCost, preArc, postArc)
    
    def _calcInsertCost(self, arcPosition, arc):
        '''
        Calculate the cost of inserting an arc in a position.
        '''
        if self.cModules:
            return(c_calcMoveCost._calcInsertCost(arcPosition, arc))
        else:  
            (currentCost, preArc, postArc) = self._twoSeqCost(arcPosition)
            newCost = self._threeArcCost(preArc, arc, postArc)
            netCost = newCost - currentCost
        return(netCost, preArc)
        
    def _calcReplaceCost(self, arcP, arc):
        '''
        Calculate the cost of replacing an arc in a position.
        '''
        if self.cModules:
            return(c_calcMoveCost._calcReplaceCost(arcP, arc))
        else:  
            preArc = self.route[arcP - 1]
            currentArc = self.route[arcP]
            postArc = self.route[arcP + 1]
            currentCost = self._d[preArc][currentArc] + self._d[currentArc][postArc]
            newCost = self._d[preArc][arc] +  self._d[arc][postArc]
            netCost = newCost - currentCost
        return(netCost, currentCost, newCost)
    
    def _initiateMoveCostCalculations(self, moveCandidates, threshold = None):
        moveCandidates = set(moveCandidates)
        if threshold == None: threshold = 1e300000
        return(moveCandidates, threshold)
    
    def _findNearestNeighboursCandidates(self, arc, nNearest, candidates):
        if nNearest: 
            if nNearest <= 1:
                nIndex = int(ceil(len(self._nnList)*nNearest))
            else:
                nIndex = nNearest
            nearestArcSet = set(self._nnList[arc][:nIndex])#set(nnList[arc][:nNearest])
            arcNearestCandidates = candidates.intersection(nearestArcSet)
        else: 
            arcNearestCandidates = candidates
        return(arcNearestCandidates)

    def _findNearestNeighboursCandidatesAfter(self, arc, nNearest, candidates):
        if nNearest: 
            if nNearest <= 1:
                nIndex = int(ceil(len(self._nnList)*nNearest))
            else:
                nIndex = nNearest
            nearestArcSet = set(self._nnList[arc][:nIndex])#set(nnList[arc][:nNearest])
            arcNearestCandidates = candidates.intersection(nearestArcSet)
        else: 
            arcNearestCandidates = candidates
        return(arcNearestCandidates)

    def _relocateToPositions(self, arcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold):
        '''
        Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(c_calcMoveCost._relocateToPositions(arcRelocate, arcPositionRemove, netCostRemove, arcToInsertAt, threshold))
        else:
            savings = []
            for arcToRelocateBefore in arcToInsertAt:
                arcPositionInsert = self.routeMapping[arcToRelocateBefore] # Relocate position
                (netCostInsert, arcToRelocateBeforePreArc) = self._calcInsertCost(arcPositionInsert, arcRelocate) # Calculate cost of inserting an arc.
                relocateCost = netCostRemove + netCostInsert
                if relocateCost < threshold:
                    relocateAccurate = arcPositionInsert < arcPositionRemove or arcPositionInsert > arcPositionRemove + 1
                    if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
                    savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, arcToRelocateBefore, arcToRelocateBeforePreArc, None), 'relocate', (netCostRemove, netCostInsert)))
            return(savings)
 
    def _relocateToPositionsAfter(self, arcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold):
        '''
        Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(c_calcMoveCost._relocateToPositions(arcRelocate, arcPositionRemove, netCostRemove, arcToInsertAt, threshold))
        else:
            savings = []
            for arcToRelocateAfter in arcToInsertAt:
                arcPositionInsert = self.routeMapping[arcToRelocateAfter] # Relocate position
                arcToRelocateAfterPreArc = self.routeMapping[arcToRelocateAfter - 1]
                arcToRelocateAfterPostArc = self.routeMapping[arcToRelocateAfter - +1]
                (netCostInsert, arcToRelocateBeforePreArc) = self._calcInsertCost(arcPositionInsert + 1, arcRelocate) # Calculate cost of inserting an arc.
                relocateCost = netCostRemove + netCostInsert
                if relocateCost < threshold:
                    relocateAccurate = arcPositionInsert < arcPositionRemove or arcPositionInsert > arcPositionRemove + 1
                    if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
                    savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, arcToRelocateAfter, arcToRelocateAfterPreArc, arcToRelocateAfterPostArc), 'relocateAfter', (netCostRemove, netCostInsert)))
            return(savings)
                
    def relocateMovesAfter(self, relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules and self.autoInvCosts:
            return(c_calcMoveCost.relocateMovesWithInv(relocateCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        elif self.cModules:
            return(c_calcMoveCost.relocateMoves(relocateCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        else:
            savings = []
            (arcToRelocateBeforeCandidates, threshold) = self._initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
            
            for arcRelocate in relocateCandidates:
                arcPositionRemove = self.routeMapping[arcRelocate]
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
                arcToInsertAt = self._findNearestNeighboursCandidates(arcRelocate, nNearest, arcToRelocateBeforeCandidates)
                savings += self._relocateToPositionsAfter(arcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)
#                 if arcRelocate in self._edgesS:
#                     invArcRelocate = self._inv[arcRelocate]
#                     savings += self._relocateToPositions(invArcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)
        return(savings)

    def relocateMoves(self, relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules and self.autoInvCosts:
            return(c_calcMoveCost.relocateMovesWithInv(relocateCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        elif self.cModules:
            return(c_calcMoveCost.relocateMoves(relocateCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        else:
            savings = []
            (arcToRelocateBeforeCandidates, threshold) = self._initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
            
            for arcRelocate in relocateCandidates:
                arcPositionRemove = self.routeMapping[arcRelocate]
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
                arcToInsertAt = self._findNearestNeighboursCandidates(arcRelocate, nNearest, arcToRelocateBeforeCandidates)
                savings += self._relocateToPositions(arcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)
#                 if arcRelocate in self._edgesS:
#                     invArcRelocate = self._inv[arcRelocate]
#                     savings += self._relocateToPositions(invArcRelocate, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)
        return(savings)

    def _exchangeWithPosition(self, arcsToExchange, arcExhangePosition1, preArc1, arcExchange1, postArc1, currenCost1, threshold):
        '''
        Calculate the move cost of exchanging a specified arc with other arcs.
        '''
        if self.cModules and self.autoInvCosts:
            return(c_calcMoveCost._exchangeWithPosition(arcsToExchange, arcExhangePosition1, preArc1, arcExchange1, postArc1, currenCost1, threshold))
        else:
            savings = []
            for arcExchange2 in arcsToExchange:
                arcExhangePosition2 = self.routeMapping[arcExchange2]
                exchangeArcs = arcExhangePosition2 > arcExhangePosition1 + 1 # Prevents re-evaluation of exchanges (B with A is the same as A with B), and for two consecutive arcs to be exchanged (1,2,3(A),4(B),5,6).
                if not exchangeArcs: continue
        
                (currenCost2, preArc2, arc2, postArc2) = self._threeSeqCost(arcExhangePosition2) # Calculate cost of inserting an arc. 
                newCost1 = self._threeArcCost(preArc1, arcExchange2, postArc1) # Cost of new sequences with middle arcs replaced.
                newCost2 = self._threeArcCost(preArc2, arcExchange1, postArc2)
                netCostRoute1 = newCost1 - currenCost1
                netCostRoute2 = newCost2 - currenCost2
                exchangeCost = netCostRoute1 + netCostRoute2
                if exchangeCost < threshold: # If it's below (better than) a threshold the move is added to the savings list.
                    savings.append((exchangeCost, (arcExchange1, preArc1, postArc1, arcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1, netCostRoute2)))
#                 
#                 bothExchange = True
#                 
#                 if arcExchange2 in self._edgesS:
#                     invArcExchange2 = self._inv[arcExchange2]
#                     newCost1inv = self._threeArcCost(preArc1, invArcExchange2, postArc1)
#                     netCostRoute1inv = newCost1inv - currenCost1
#                     exchangeCostinv = netCostRoute1inv + netCostRoute2
#                     if exchangeCostinv < threshold: # If it's below (better than) a threshold the move is added to the savings list.
#                         savings.append((exchangeCostinv, (arcExchange1, preArc1, postArc1, invArcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1inv, netCostRoute2)))
#                 else:
#                     bothExchange = False
#                     
#                 if arcExchange1 in self._edgesS:
#                     invArcExchange1 = self._inv[arcExchange1]
#                     newCost2inv = self._threeArcCost(preArc2, invArcExchange1, postArc2)
#                     netCostRoute2inv = newCost2inv - currenCost2
#                     exchangeCostinv = netCostRoute1 + netCostRoute2inv
#                     if exchangeCostinv < threshold: # If it's below (better than) a threshold the move is added to the savings list.
#                         savings.append((exchangeCostinv, (invArcExchange1, preArc1, postArc1, arcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1, netCostRoute2inv)))
#                 else:
#                     bothExchange = False
#                     
#                 if bothExchange:
#                     exchangeCostinv = netCostRoute1inv + netCostRoute2inv
#                     if exchangeCostinv < threshold: # If it's below (better than) a threshold the move is added to the savings list.
#                         savings.append((exchangeCostinv, (invArcExchange1, preArc1, postArc1, invArcExchange2, preArc2, postArc2), 'exchange', (netCostRoute1inv, netCostRoute2inv)))                
        return(savings)
                  
    def exchangeMoves(self, exchangeCandidatesI, exchangeCandidatesJ, 
                       threshold = None, nNearest = None):
        '''
        Calculate the move cost of exchanging two arcs. To enable the nearest-neighbour list, the preceding arc of an
        exchange is determined, and its neighbours are used, which may include the depot arc.
        '''
        if self.cModules and self.autoInvCosts:
            return(c_calcMoveCost.exchangeMovesWithInv(exchangeCandidatesI, exchangeCandidatesJ, threshold, nNearest))
        elif self.cModules:
            return(c_calcMoveCost.exchangeMoves(exchangeCandidatesI, exchangeCandidatesJ, threshold, nNearest))
        else: 
            savings = []
            (exchangeCandidatesI, threshold) = self._initiateMoveCostCalculations(exchangeCandidatesI, threshold)
            exchangeCandidatesJ = set(exchangeCandidatesJ)
            
            for arcExchange1 in exchangeCandidatesI:
                arcExhangePosition1 = self.routeMapping[arcExchange1]
                (currenCost1, preArc1, arc1, postArc1) = self._threeSeqCost(arcExhangePosition1)
                arcsToExchange = self._findNearestNeighboursCandidates(preArc1, nNearest, exchangeCandidatesJ) # Select nearest neighbours of arcRelocate 
                savings += self._exchangeWithPosition(arcsToExchange, arcExhangePosition1, preArc1, arcExchange1, postArc1, currenCost1, threshold)
        return(savings)
    
    def _crossWithPositions(self, arcsToExchange, arcExhangePosition1, preArc1, arcExchange1, currenCost1, threshold):
        '''
        Calculate the move costs with a specified arc and all others.
        '''
        if self.cModules:
            return(c_calcMoveCost._exchangeWithPosition(arcsToExchange, arcExhangePosition1, preArc1, arcExchange1, currenCost1, threshold))
        else:
            savings = []
            for arcExchange2 in arcsToExchange:
                arcExhangePosition2 = self.routeMapping[arcExchange2]
                exchangeArcs = arcExhangePosition2 > arcExhangePosition1 + 1 # Prevents re-evaluation of exchanges (B with A is the same as A with B), and for two consecutive arcs to be exchanged (1,2,3(A),4(B),5,6).
                if not exchangeArcs: continue
        
                (currenCost2, preArc2, arc2) = self._twoSeqCost(arcExhangePosition2) # Calculate cost of inserting an arc. 
                newCost1 = self._twoArcCost(preArc1, arcExchange2) # Cost of new sequences with middle arcs replaced.
                newCost2 = self._twoArcCost(preArc2, arcExchange1)
                exchangeCost = (newCost1 - currenCost1) +  (newCost2 - currenCost2)
                if exchangeCost < threshold: # If it's below (better than) a threshold the move is added to the savings list.
                    savings.append((exchangeCost, (arcExchange1, preArc1, None, arcExchange2, preArc2, None), 'cross', (newCost1 - currenCost1, newCost2 - currenCost2)))
        return(savings)
        
    def crossMoves(self, crossCandidatesI, crossCandidatesJ,
                    threshold = None, nNearest = None):
        '''
        Calculate the move cost of crossing two end sections in a route. Same principles applies as exchange.
        '''
        if self.cModules:
            return(c_calcMoveCost.crossMoves(crossCandidatesI, crossCandidatesJ, threshold, nNearest))
        else:
            savings = []
            (crossCandidatesI, threshold) = self._initiateMoveCostCalculations(crossCandidatesI, threshold)
            crossCandidatesJ = set(crossCandidatesJ)
            
            for arcExchange1 in crossCandidatesI:
                arcExhangePosition1 = self.routeMapping[arcExchange1]
                (currenCost1, preArc1, arc1) = self._twoSeqCost(arcExhangePosition1)
                arcsToExchange = self._findNearestNeighboursCandidates(preArc1, nNearest, crossCandidatesJ) # Select nearest neighbours of arcRelocate 
                savings += self._crossWithPositions(arcsToExchange, arcExhangePosition1, preArc1, arcExchange1, currenCost1, threshold)
        return(savings)

    def flipMoves(self, flipCandidates, threshold = None):
        '''
        Calculate the move cost of inverting an edge arc task.
        '''
        if self.cModules:
            return(c_calcMoveCost.flipMoves(flipCandidates, threshold))
        else:
            savings = []
            (flipCandidates, threshold) = self._initiateMoveCostCalculations(flipCandidates, threshold)
            flipEdges = flipCandidates.intersection(self._edgesS)
            for arc in flipEdges:
                arcPosition = self.routeMapping[arc]
                invArc = self._inv[arc]
                (currenCost, preArc, arc, postArc) = self._threeSeqCost(arcPosition)
                newCost = self._threeArcCost(preArc, invArc, postArc)
                flipCost = newCost - currenCost
                if flipCost < threshold:
                    savings.append((flipCost, (invArc, preArc, postArc, None, None, None), 'flip', (flipCost, None)))
        return(savings)
    
    def relocateEndRouteMoves(self, relocateCandidates, routeDummyArcs, threshold = None, nNearest = None):
        '''
        Calculate the move cost of exception relocating an arc from current position before a dummy arc:
            - End of a route before the depot.
        First dummy arc(s) in the giant route should thus NOT be in dummyArcs set.
        '''
        if self.cModules and self.autoInvCosts:
            return(c_calcMoveCost.relocateEndRouteMovesWithInv(relocateCandidates, routeDummyArcs, threshold, nNearest))
        elif self.cModules:
            return(c_calcMoveCost.relocateEndRouteMoves(relocateCandidates, routeDummyArcs, threshold, nNearest))
        else:
            savings = []
            for dummyArcPosition in routeDummyArcs: # Arc will be inserted before the last dummy arc of a route, thus end of a route.
                if dummyArcPosition == 0: continue # Arc cannot be inserted before the giant route.
                (relocateCandidates, threshold) = self._initiateMoveCostCalculations(relocateCandidates, threshold)
                (currentDepotCost, preArc, dummyArc) = self._twoSeqCost(dummyArcPosition)
                arcToInsertAfter = self._findNearestNeighboursCandidates(preArc, nNearest, relocateCandidates)
                for arcRelocate in arcToInsertAfter:
                    arcPositionRemove = self.routeMapping[arcRelocate]
                    (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
                    
                    netCostInsert = self._threeArcCost(preArc, arcRelocate, dummyArc)
                    relocateCost = netCostRemove + netCostInsert - currentDepotCost
                    if relocateCost < threshold:
                        relocateAccurate = dummyArcPosition < arcPositionRemove or dummyArcPosition > arcPositionRemove + 1
                        if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
                        savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, dummyArc, preArc, None), 'relocateBeforeDummy', (netCostRemove, netCostInsert - currentDepotCost)))
#                     
#                     if arcRelocate in self._edgesS:
#                         arcRelocateInv = self._inv[arcRelocate]
#                         
#                         netCostInsert = self._threeArcCost(preArc, arcRelocateInv, dummyArc)
#                         relocateCost = netCostRemove + netCostInsert - currentDepotCost
#                         if relocateCost < threshold:
#                             relocateAccurate = dummyArcPosition < arcPositionRemove or dummyArcPosition > arcPositionRemove + 1
#                             if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
#                             savings.append((relocateCost, (arcRelocateInv, removePreArc, removePostArc, dummyArc, preArc, None), 'relocateBeforeDummy', (netCostRemove, netCostInsert - currentDepotCost)))
                        
        return(savings)

    def crossEndRouteMoves(self, crossCandidates, routeDummyArcs, threshold = None, nNearest = None):
        '''
        Calculate the move cost of crossing two end sections in a route. Same principles applies as exchange.
        '''
        if self.cModules:
            return(c_calcMoveCost.crossEndRouteMoves(crossCandidates, routeDummyArcs, threshold, nNearest))
        else:
            savings = []
            for dummyArcPosition in routeDummyArcs: # Arc will be inserted before the last dummy arc of a route, thus end of a route.
                if dummyArcPosition == 0: continue # Arc cannot be inserted before the giant route.
                (crossCandidates, threshold) = self._initiateMoveCostCalculations(crossCandidates, threshold)
                (currenCost1, preArc1, dummyArc) = self._twoSeqCost(dummyArcPosition)
                arcToCrossAfter = self._findNearestNeighboursCandidates(preArc1, nNearest, crossCandidates)
                for arcExchange2 in arcToCrossAfter:
                    arcExhangePosition2 = self.routeMapping[arcExchange2]
                    exchangeArcs = dummyArcPosition > arcExhangePosition2 + 1 or dummyArcPosition < arcExhangePosition2# Prevents re-evaluation of exchanges (B with A is the same as A with B), and for two consecutive arcs to be exchanged (1,2,3(A),4(B),5,6).
                    if not exchangeArcs: continue
                    (currenCost2, preArc2, arc2) = self._twoSeqCost(arcExhangePosition2) # Calculate cost of inserting an arc. 
                    newCost1 = self._twoArcCost(preArc1, arcExchange2) # Cost of new sequences with middle arcs replaced.
                    newCost2 = self._twoArcCost(preArc2, dummyArc)
                    exchangeCost = (newCost1 - currenCost1) +  (newCost2 - currenCost2)
                    if arcExhangePosition2 == 1: 
                        exchangeCost -= self._dumpCost 
                    if exchangeCost < threshold: # If it's below (better than) a threshold the move is added to the savings list.
                        savings.append((exchangeCost, (arcExchange2, preArc2, None, dummyArc, preArc1, None), 'crossAtDummy', (newCost2 - currenCost2, newCost1 - currenCost1)))
        return(savings)

    def _threeArcDoubleCost(self, preArc, arc1, arc2, postArc):
        '''
        Calculate the cost between three arcs.
        '''
        if self.cModules: 
            return(c_calcMoveCost._threeArcDoubleCost(preArc, arc1, arc2, postArc))
        else:
            cost = self._d[preArc][arc1] + self._d[arc2][postArc]
        return(cost)
    
    def _calcDoubleInsertCost(self, arcPosition, arc1, arc2):
        '''
        Calculate the cost of inserting an arc in a position.
        '''
        if self.cModules:
            return(c_calcMoveCost._calcDoubleInsertCost(arcPosition, arc1, arc2))
        else:  
            (currentCost, preArc, postArc) = self._twoSeqCost(arcPosition)
            newCost = self._threeArcDoubleCost(preArc, arc1, arc2, postArc)
            netCost = newCost - currentCost
        return(netCost, preArc)

    def _doubleRelocateToPositions(self, arcRelocate1, arcRelocate2, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold):
        '''
        Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(c_calcMoveCost._doubleRelocateToPositions(arcRelocate1, arcRelocate2, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold))
        else:
            savings = []
            for arcToRelocateBefore in arcToInsertAt:
                arcPositionInsert = self.routeMapping[arcToRelocateBefore] # Relocate position
                (netCostInsert, arcToRelocateBeforePreArc) = self._calcDoubleInsertCost(arcPositionInsert, arcRelocate1, arcRelocate2) # Calculate cost of inserting an arc.
                relocateCost = netCostRemove + netCostInsert
                if relocateCost < threshold:
                    relocateAccurate = arcPositionInsert < arcPositionRemove or arcPositionInsert > arcPositionRemove + 2
                    if not relocateAccurate: continue# Ensures that arc is not inserted in its current position, or directly after its current position, which has no effect but will give a cost savings because the prearc is calculated as the arc itself with zerio distance between them..
                    savings.append((relocateCost, (arcRelocate1, removePreArc, removePostArc, arcToRelocateBefore, arcToRelocateBeforePreArc, arcRelocate2), 'doubleRelocate', (netCostRemove, netCostInsert)))
            return(savings)
    
    def _threeSeqDoubleCost(self, arcPosition):
        '''
        Calculate the cost of three consecutive arcs in a route.
        '''
        if self.cModules:
            return(c_calcMoveCost._threeSeqDoubleCost(arcPosition))
        else:         
            preArc = self.route[arcPosition - 1]
            arc1 = self.route[arcPosition]
            arc2  = self.route[arcPosition + 1]
            postArc = self.route[arcPosition + 2]
            cost = self._threeArcDoubleCost(preArc, arc1, arc2, postArc)
        return(cost, preArc, arc1, arc2, postArc)
        
    def _calcDoubleRemoveCost(self, arcPosition):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            return(c_calcMoveCost._calcDoubleRemoveCost(arcPosition))
        else:    
            (currentCost, preArc, currentArc1, currentArc2, postArc) = self._threeSeqDoubleCost(arcPosition)
            newCost = self._twoArcCost(preArc, postArc)
            netCost = newCost - currentCost
        return(netCost, preArc, currentArc2, postArc)

    def doubleRelocateMoves(self, relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(c_calcMoveCost.doubleRelocateMoves(relocateCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        else:
            savings = []
            (arcToRelocateBeforeCandidates, threshold) = self._initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
            
            for arcRelocate1 in relocateCandidates:
                arcPositionRemove = self.routeMapping[arcRelocate1]
                (netCostRemove, removePreArc, arcRelocate2, removePostArc) = self._calcDoubleRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
                arcToInsertAt = self._findNearestNeighboursCandidates(arcRelocate2, nNearest, arcToRelocateBeforeCandidates)
                savings += self._doubleRelocateToPositions(arcRelocate1, arcRelocate2, removePreArc, removePostArc, arcPositionRemove, netCostRemove, arcToInsertAt, threshold)
        return(savings)




class CalcMoveCostsMCARPTIFspecial(object):
    
    def __init__(self, info, cModules = True, nnList = None):
        '''
        Class initialization values.
        '''
        # Problem info
        # Problem info
        self._info = info
        self._depot = self._info.depotnewkey
        self._d = info.d
        self._inv = info.reqInvArcList
        self._edgesL = [arc for arc, invFlag in enumerate(self._inv) if invFlag != None]
        self._edgesS = set(self._edgesL)
        self.cModules = cModules
        self.route = []
        self._dumpCost = info.dumpCost
        
        self._dummyArcs = {self._depot}
        
        self._if_cost = info.if_cost_np
        self._ifs = info.IFarcsnewkey

        if nnList == None:
            print(nnList)
            self._nnList = [[]]
        else:
            self._nnList = nnList
    
        self.autoInvCosts = True

    def initiateCmodules_MCARPTIF(self):
        '''
        '''
        if self.cModules:
            calcMoveCostMCARPTIF_c.init_input(self._d, self._nnList, self._inv, self._dumpCost, self._dummyArcs, self._if_cost, self._ifs)
        
    def freeCmodules_MCARPTIF(self):
        '''
        '''
        if self.cModules:
            calcMoveCostMCARPTIF_c.free_input()
            
    def setRoute_MCARPTIF(self, route):
        '''
        '''
        if self.cModules:
            #pass
            calcMoveCostMCARPTIF_c.init_route(route)
        else:
            self.route = route
            routeMapping = [-1]*len(self._d)
            for i, arc in enumerate(route):
                routeMapping[arc] = i
                if arc in self._edgesS:
                    routeMapping[self._inv[arc]] = i
            self.routeMapping = routeMapping
    
    def freeRoute_MCARPTIF(self):
        '''
        '''
        if self.cModules:
            calcMoveCostMCARPTIF_c.free_route()   

    def _calcRemoveCostMCARPTIF(self, arcPosition):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._calcRemoveCostMCARPTIF(arcPosition))
        else:    
            preArc = self.route[arcPosition - 1]
            arc = self.route[arcPosition]
            postArc = self.route[arcPosition + 1]
            currentCost = self._d[preArc][arc] + self._d[arc][postArc]
            newCost = self._d[preArc][postArc]
            netCost = newCost - currentCost
            return(netCost, preArc, postArc)
        
    def _calcRemoveCostPostIF(self, arcPosition):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._calcRemoveCostPostIF(arcPosition))
        else:    
            preArc = self.route[arcPosition - 2]
            arc = self.route[arcPosition]
            postArc = self.route[arcPosition + 1]
            currentCost = self._if_cost[preArc][arc] + self._d[arc][postArc]
            newCost = self._if_cost[preArc][postArc]
            netCost = newCost - currentCost
            return(netCost, preArc, postArc)

    def _calcRemoveCostPreIF(self, arcPosition):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._calcRemoveCostPreIF(arcPosition))
        else:    
            preArc = self.route[arcPosition - 1]
            arc = self.route[arcPosition]
            postArc = self.route[arcPosition + 2]
            currentCost = self._d[preArc][arc] + self._if_cost[arc][postArc]
            newCost = self._if_cost[preArc][postArc]
            netCost = newCost - currentCost
            return(netCost, preArc, postArc)

    def _calcInsertCostPostIF(self, arcPosition, insertArc):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._calcInsertCostPostIF( arcPosition, insertArc))
        else:    
            preArc = self.route[arcPosition - 2]
            arc = self.route[arcPosition]
            currentCost = self._if_cost[preArc][arc]
            newCost = self._if_cost[preArc][insertArc] + self._d[insertArc][arc]
            netCost = newCost - currentCost
            return(netCost, preArc)

    def _calcInsertCostPreIF(self, arcPosition, insertArc):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._calcInsertCostPreIF(arcPosition, insertArc))
        else:    
            arc = self.route[arcPosition]
            postArc = self.route[arcPosition + 2]
            currentCost = self._if_cost[arc][postArc]
            newCost = self._d[arc][insertArc] + self._if_cost[insertArc][postArc]
            netCost = newCost - currentCost
            return(netCost, postArc)

    def _calcInsertCostMCARPTIF(self, arcPosition, insertArc):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._calcInsertCostPreIF(arcPosition, insertArc))
        else:    
            preArc = self.route[arcPosition - 1]
            arc = self.route[arcPosition]
            currentCost = self._d[preArc][arc]
            newCost = self._d[preArc][insertArc] + self._d[insertArc][arc]
            netCost = newCost - currentCost
            return(netCost, preArc)

    def _initiateMoveCostCalculations(self, moveCandidates, threshold = None):
        moveCandidates = set(moveCandidates)
        if threshold == None: threshold = 1e300000
        return(moveCandidates, threshold)

    def _findNearestNeighboursCandidates(self, arc, nNearest, candidates):
        if nNearest: 
            if nNearest <= 1:
                nIndex = int(ceil(len(self._nnList)*nNearest))
            else:
                nIndex = nNearest
            nearestArcSet = set(self._nnList[arc][:nIndex])#set(nnList[arc][:nNearest])
            arcNearestCandidates = candidates.intersection(nearestArcSet)
        else: 
            arcNearestCandidates = candidates
        return(arcNearestCandidates)

    def _relocateToPreIF(self, arcsToRelocate, arcRelocateAfter, threshold):
        '''
        Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._relocateToPreIF(arcsToRelocate, arcRelocateAfter, threshold))
        else:
            savings = []
            arcPositionInsert = self.routeMapping[arcRelocateAfter]
            for arcToRelocate in arcsToRelocate:
                arcPositionRemove = self.routeMapping[arcToRelocate]
                relocateAccurate = arcPositionRemove < arcPositionInsert or arcPositionInsert + 2 < arcPositionRemove
                if not relocateAccurate: continue
                preArc = self.route[arcPositionRemove - 1]
                postArc = self.route[arcPositionRemove + 1]
                if preArc in self._ifs: 
                    specialIF = 'PostIF'
                    (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostPostIF(arcPositionRemove)
                elif postArc in self._ifs: 
                    specialIF = 'PreIF'
                    (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostPreIF(arcPositionRemove)
                else:
                    specialIF = ''
                    (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostMCARPTIF(arcPositionRemove)
                (netCostInsert, arcToRelocateAfterPost) = self._calcInsertCostPreIF(arcPositionInsert, arcToRelocate)
                relocateCost = netCostRemove + netCostInsert
                if relocateCost < threshold:
                    savings.append((relocateCost, (arcToRelocate, removePreArc, removePostArc, arcRelocateAfter, None, arcToRelocateAfterPost), 'relocate' + specialIF + '_PreIF', (netCostRemove, netCostInsert)))
            return(savings)

    def relocateMovesPreIF(self, relocateCandidates, arcToRelocateAfterCandidates, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c.relocateMovesPreIF(relocateCandidates, arcToRelocateAfterCandidates, threshold, nNearest))
        else:
            savings = []
            (relocateCandidates, threshold) = self._initiateMoveCostCalculations(relocateCandidates, threshold)
            for arcRelocateAfter in arcToRelocateAfterCandidates:
                arcsToRelocate = self._findNearestNeighboursCandidates(arcRelocateAfter, nNearest, relocateCandidates)      
                savings += self._relocateToPreIF(arcsToRelocate, arcRelocateAfter, threshold)
            return(savings)

    def _relocateToPostIF(self, arcRelocate, arcToRelocateBeforeCandidates, threshold):
        '''
        Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._relocateToPostIF(arcRelocate, arcToRelocateBeforeCandidates, threshold))
        else:
            savings = []
            arcPositionRemove = self.routeMapping[arcRelocate]
            preArc = self.route[arcPositionRemove - 1]
            postArc = self.route[arcPositionRemove + 1]            

            if preArc in self._ifs: 
                specialIF = 'PostIF'
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostPostIF(arcPositionRemove)
            elif postArc in self._ifs: 
                specialIF = 'PreIF'
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostPreIF(arcPositionRemove)
            else:
                specialIF = ''
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostMCARPTIF(arcPositionRemove)
            
            for arcToRelocateBefore in arcToRelocateBeforeCandidates:
                arcPositionInsert = self.routeMapping[arcToRelocateBefore]
                relocateAccurate = arcPositionRemove > arcPositionInsert or arcPositionInsert > arcPositionRemove + 2
                if not relocateAccurate: continue
                (netCostInsert, arcToRelocateBeforePre) = self._calcInsertCostPostIF(arcPositionInsert, arcRelocate)
                relocateCost = netCostRemove + netCostInsert
                if relocateCost < threshold:
                    savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, arcToRelocateBefore, arcToRelocateBeforePre, None), 'relocate' + specialIF + '_PostIF', (netCostRemove, netCostInsert)))
            return(savings)

    def relocateMovesPostIF(self, relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c.relocateMovesPostIF(relocateCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        else:
            savings = []
            (arcToRelocateBeforeCandidates, threshold) = self._initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
            for arcRelocate in relocateCandidates:
                arcToRelocateBeforeCandidates = self._findNearestNeighboursCandidates(arcRelocate, nNearest, arcToRelocateBeforeCandidates)      
                savings += self._relocateToPostIF(arcRelocate, arcToRelocateBeforeCandidates, threshold)
            return(savings)

    def _relocateBeforeArc(self, arcRelocate, arcToRelocateBeforeCandidates, threshold):
        '''
        Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._relocateBeforeArc(arcRelocate, arcToRelocateBeforeCandidates, threshold))
        else:
            savings = []
            arcPositionRemove = self.routeMapping[arcRelocate]
            preArc = self.route[arcPositionRemove - 1]
            postArc = self.route[arcPositionRemove + 1]            

            if preArc in self._ifs: 
                specialIF = 'PostArcIF'
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostPostIF(arcPositionRemove)
                arcPositionRemoveAdd = + 1
            elif postArc in self._ifs: 
                specialIF = 'PreArcIF'
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostPreIF(arcPositionRemove)
                arcPositionRemoveAdd = + 2
            else:
                specialIF = ''
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCostMCARPTIF(arcPositionRemove)
                arcPositionRemoveAdd = + 1
                
            for arcToRelocateBefore in arcToRelocateBeforeCandidates:
                arcPositionInsert = self.routeMapping[arcToRelocateBefore]
                relocateAccurate = arcPositionRemove > arcPositionInsert or arcPositionInsert > arcPositionRemove + arcPositionRemoveAdd
                if not relocateAccurate: continue
                (netCostInsert, arcToRelocateBeforePre) = self._calcInsertCostMCARPTIF(arcPositionInsert, arcRelocate)
                relocateCost = netCostRemove + netCostInsert
                if relocateCost < threshold:
                    savings.append((relocateCost, (arcRelocate, removePreArc, removePostArc, arcToRelocateBefore, arcToRelocateBeforePre, None), 'relocate' + specialIF, (netCostRemove, netCostInsert)))
            return(savings)

    def relocateMovesMCARPTIF(self, relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c.relocateMovesMCARPTIF(relocateCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        else:
            savings = []
            (arcToRelocateBeforeCandidates, threshold) = self._initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
            for arcRelocate in relocateCandidates:
                arcToRelocateBeforeCandidates = self._findNearestNeighboursCandidates(arcRelocate, nNearest, arcToRelocateBeforeCandidates)      
                savings += self._relocateBeforeArc(arcRelocate, arcToRelocateBeforeCandidates, threshold)
            return(savings)

    def _threeSeqCost(self, arcPosition, n):
        '''
        Calculate the cost of three consecutive arcs in a route.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._threeSeqCost(arcPosition))
        else:         
            preArc = self.route[arcPosition - 1]
            arc = self.route[arcPosition]
            postArc = self.route[arcPosition + 1]
            
            if preArc in self._ifs: 
                exchangePos = n + 'excPostIF'
                preArc = self.route[arcPosition - 2]
                cost = self._if_cost[preArc][arc] + self._d[arc][postArc]
            elif postArc in self._ifs: 
                exchangePos = n + 'excPreIF'
                postArc = self.route[arcPosition + 2]
                cost = self._d[preArc][arc] + self._if_cost[arc][postArc]
            else: 
                exchangePos = ''
                cost = self._d[preArc][arc] + self._d[arc][postArc]
            return(cost, preArc, arc, postArc, exchangePos)

    def _replaceCost(self, preArc, postArc, replaceArc, exchangePos):
        '''
        Calculate the cost of three consecutive arcs in a route.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._replaceCost(replaceArc))
        else:                     
            if exchangePos.find('excPostIF') != -1: 
                cost = self._if_cost[preArc][replaceArc] + self._d[replaceArc][postArc]
            elif exchangePos.find('excPreIF') != -1:
                cost = self._d[preArc][replaceArc] + self._if_cost[replaceArc][postArc]
            else: 
                cost = self._d[preArc][replaceArc] + self._d[replaceArc][postArc]
            return(cost)

    def exchangeMovesMCARPTIF(self, exchangeCandidates1, exchangeCandidates2, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c.exchangeMovesMCARPTIF(exchangeCandidates1, exchangeCandidates2, threshold, nNearest))
        else:
            savings = []
            (exchangeCandidates1, threshold) = self._initiateMoveCostCalculations(exchangeCandidates1, threshold)
            for arcExchange1 in exchangeCandidates1:
                arcPositionExc1 = self.routeMapping[arcExchange1]
                (cost1, preArc1, arc1, postArc1, exchangePos1) = self._threeSeqCost(arcPositionExc1, n= '_1')
                exchangeCandidates2 = self._findNearestNeighboursCandidates(preArc1, nNearest, exchangeCandidates2) 
                for arcExchange2 in exchangeCandidates2:
                    arcPositionExc2 = self.routeMapping[arcExchange2]
                    (cost2, preArc2, arc2, postArc2, exchangePos2) = self._threeSeqCost(arcPositionExc2, n = '_2')
                    if exchangePos1 == '_1excPreIF' and exchangePos2 == '_2excPostIF':
                        exchangeArcs = arcPositionExc2 > arcPositionExc1 + 2
                    else: 
                        exchangeArcs = arcPositionExc2 > arcPositionExc1 + 1
                    if not exchangeArcs: continue
                    cost1new = self._replaceCost(preArc1, postArc1, arcExchange2, exchangePos1)
                    cost2new = self._replaceCost(preArc2, postArc2, arcExchange1, exchangePos2)
                    netExc1 = cost1new - cost1
                    netExc2 = cost2new - cost2
                    netExc = netExc1 + netExc2
                    if netExc1 + netExc2 < threshold:
                        savings.append((netExc, (arcExchange1, preArc1, postArc1, arcExchange2, preArc2, postArc2), 'exchange' + exchangePos1 + exchangePos2, (netExc1, netExc2)))
            return(savings)

    def flipMovesMCARPTIF(self, exchangeCandidates1, threshold = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c.flipMovesMCARPTIF(exchangeCandidates1, threshold))
        else:
            savings = []
            (exchangeCandidates1, threshold) = self._initiateMoveCostCalculations(exchangeCandidates1, threshold)
            for arcExchange1 in exchangeCandidates1:
                invExchange = self._inv[arcExchange1]
                arcPositionExc1 = self.routeMapping[arcExchange1]
                (cost1, preArc1, arc1, postArc1, exchangePos1) = self._threeSeqCost(arcPositionExc1, n= '_')
                cost1new = self._replaceCost(preArc1, postArc1, invExchange, exchangePos1)
                netFlip = cost1new - cost1
                if netFlip < threshold:
                    savings.append((netFlip, (arcExchange1, preArc1, postArc1, invExchange, None, None), 'flip' + exchangePos1, (netFlip, 0)))
            return(savings)

    def _twoSeqCost(self, arcPosition, n):
        '''
        Calculate the cost of three consecutive arcs in a route.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._twoSeqCost(arcPosition, n))
        else:         
            preArc = self.route[arcPosition - 1]
            arc = self.route[arcPosition]
            
            if preArc in self._ifs: 
                crossPos = n + 'crossPostIF'
                preArc = self.route[arcPosition - 2]
                cost = self._if_cost[preArc][arc]
            else: 
                crossPos = ''
                cost = self._d[preArc][arc]
            return(cost, preArc, arc, crossPos)

    def _relinkCost(self, preArc, relinkArc, crossPos):
        '''
        Calculate the cost of three consecutive arcs in a route.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c._relinkCost(preArc, relinkArc, crossPos))
        else:                     
            if crossPos.find('crossPostIF') != -1: 
                cost = self._if_cost[preArc][relinkArc]
            else: 
                cost = self._d[preArc][relinkArc]
            return(cost)

    def crossMovesMCARPTIF(self, relinkCandidates1, relinkCandidates2, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(calcMoveCostMCARPTIF_c.crossMovesMCARPTIF(relinkCandidates1, relinkCandidates2, threshold, nNearest))
        else:
            savings = []
            (relinkCandidates1, threshold) = self._initiateMoveCostCalculations(relinkCandidates1, threshold)
            for arcRelink1 in relinkCandidates1:
                arcPositionRelink1 = self.routeMapping[arcRelink1]
                (cost1, preArc1, arc1, relinkPos1) = self._twoSeqCost(arcPositionRelink1, n= '_1')
                relinkCandidates2 = self._findNearestNeighboursCandidates(preArc1, nNearest, relinkCandidates2) 
                for arcRelink2 in relinkCandidates2:
                    arcPositionRelink2 = self.routeMapping[arcRelink2]
                    (cost2, preArc2, arc2, relinkPos2) = self._twoSeqCost(arcPositionRelink2, n = '_2')
                    if relinkPos1 == '_1crossPreIF' and relinkPos2 == '_2crossPostIF':
                        exchangeArcs = arcPositionRelink2 > arcPositionRelink1 + 2
                    else: 
                        exchangeArcs = arcPositionRelink2 > arcPositionRelink1 + 1
                    if not exchangeArcs: continue
                    cost1new = self._relinkCost(preArc1, arcRelink2, relinkPos1)
                    cost2new = self._relinkCost(preArc2, arcRelink1, relinkPos2)
                    netLink1 = cost1new - cost1
                    netLink2 = cost2new - cost2
                    netLinkNew = netLink1 + netLink2
                    if netLinkNew < threshold:
                        savings.append((netLinkNew, (arcRelink1, preArc1, None, arcRelink2, preArc2, None), 'cross' + relinkPos1 + relinkPos2, (netLink1, netLink2)))
            return(savings)

    def _calcRemoveTripCost(self, arcPosition):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            pass
            #return(c_calcMoveCost._calcRemoveCost(arcPosition))
        else:    
            #(currentCost, preArc, currentArc, postArc) = self._threeSeqCost(arcPosition)
            preArc = self.route[arcPosition - 2]
            arc = self.route[arcPosition]
            postArc = self.route[arcPosition + 2]
            currentCost = self._if_costs[preArc][arc] + self._if_costs[arc][postArc]
            newCost = self._if_costs[preArc][postArc]
            netCost = newCost - currentCost # two _if_costs are subtracted so no need to subtract info.dumpCost again.
        return(netCost, preArc, postArc)
 
    def _calcRemoveRouteCost(self, arcPosition):
        '''
        Calculate the cost of removing an arc.
        '''
        if self.cModules:
            pass
            #return(c_calcMoveCost._calcRemoveCost(arcPosition))
        else:    
            preArc = self.route[arcPosition - 1]
            arc = self.route[arcPosition]
            postArc = self.route[arcPosition + 2]
            currentCost = self._d[preArc][arc] + self._if_costs[arc][postArc]
            netCost = - currentCost
        return(netCost, preArc, postArc)
    
class MCARPmoveFunctions(object):
    '''
    MCARP specific operators and move cost calculators.
    '''
    
    def __init__(self, info):
        '''
        Set parameters to be inherited.
        '''
        self._d = info.d 
        self._nArcs = len(self._d)
        self._inv = info.reqInvArcList
        self._edgesL = [arc for arc, invFlag in enumerate(self._inv) if invFlag != None]
        self._edgesS = set(self._edgesL)
        self._depot = info.depotnewkey
        self._reqArcs = info.reqArcListActual
        self._nReqArcs = len(self._reqArcs)
        self._reqArcsSet = set(self._reqArcs)
        self._demand = info.demandL
        self._servCost = info.serveCostL
        self._dumpCost = info.dumpCost
    
    def returnRequiredArcs(self):
        return(self._reqArcs)
     
    def genMCARPsolutionMapping(self, solution):
        '''
        Takes an initial solution and maps all the required arcs to route and inter-route positions.
        '''
        dummyArcPositions = []
        giantRoute = [self._depot] # Giant route starts with depot.
        solutionMapping = {} # Mapping of an arc to its position (route and route position) in the solution.
        for i in range(solution['nVehicles']):
            route = solution[i]['Route']
            giantRoute += route[1:] # Each route consists of a start and end depot visit, with only one needed in the giant route.
            for j, arc in enumerate(route[1:-1]): # Note that j will start zero, not 1
                solutionMapping[arc] = (i, j + 1) # Since positioning starts at the first arc after the depot, j is increased by one.
                if arc in self._edgesS: solutionMapping[self._inv[arc]] = (i, j + 1) # Position of inverse arc is also captured, thus allowing for arc inversion (should come more into play with windy edges.
             
        return(solutionMapping)
     
    def genMCARPcumulativeRoute(self, route):
        loads = [self._demand[arc] for arc in route]
        costs = [self._servCost[arc] for arc in route]
        cumLoad = [loads[0]]
        cumServe = [costs[0]]
        for i in range(1, len(loads)):
            lValue = cumLoad[i - 1] + loads[i]
            cumLoad.append(lValue)
            sValue = cumServe[i - 1] + self._d[route[i - 1]][route[i]] + costs[i]
            cumServe.append(sValue)
        cumServe[-1] += self._dumpCost
        return(cumLoad, cumServe)
     
    def updateMCARPcumulitiveSolution(self, solution, routeI):
        (solution[routeI]['CumLoad'], solution[routeI]['CumServe']) = self.genMCARPcumulativeRoute(solution[routeI]['Route'])
        solution[routeI]['CumUpdate'] = True
        return(solution)
 
    def addMCARPcumulativeSolution(self, solution):
        '''
        Generates the cumulative load and cost at an arc position in a route.
        '''
        for i in range(solution['nVehicles']):
            route = solution[i]['Route']
            (solution[i]['CumLoad'], solution[i]['CumServe']) = self.genMCARPcumulativeRoute(route)
            solution[i]['CumUpdate'] = True
        return(solution)
 
    def genMCARPgiantRouteMapping(self, solution):
        '''
        Takes an initial solution and generates a giant route with the necessary giant route arc position mapping. 
        '''
        giantMapping = [0]*self._nArcs # List mapping of arcs to their position in the giant route. Will also include dummy arcs.
        solutionArcs = set()
        giantRoute = [self._depot] # Giant route starts with depot.        
        dummyArcPositions = [0]
        endArcs = set()
        k = 0
        for i in range(solution['nVehicles']):
            route = solution[i]['Route']
            for arc in route[1:]: # Each route consists of a start and end depot visit, with only one needed in the giant route.
                k += 1
                giantRoute.append(arc)
                giantMapping[arc] = k # Since positioning starts at the first arc after the depot, j is increased by one.
                if arc != self._depot: solutionArcs.add(arc) # Used to identify specific arc orientations.
                if arc in self._edgesS: giantMapping[self._inv[arc]] = k # Position of inverse arc is also captured, thus allowing for arc inversion (should come more into play with windy edges.
            endArcs.add(route[-2])
            dummyArcPositions.append(k) # Last arc added in a route is the dummy arc.
             
        giantMapping[self._depot] = 2*self._nArcs
        return(giantRoute, giantMapping, solutionArcs,  dummyArcPositions, endArcs)
    

    def insertMoves(self, insertCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(c_calcMoveCost.relocateMoves(insertCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        else:
            savings = []
            (arcToRelocateBeforeCandidates, threshold) = self._initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
            
            for arcInsert in insertCandidates:        
                arcToInsertAt = self._findNearestNeighboursCandidates(arcInsert, nNearest, arcToRelocateBeforeCandidates)
                savings += self._insertToPositions(arcInsert, arcToInsertAt, threshold)

        return(savings)

    def _insertToPositions(self, arcInsert, arcToInsertAt, threshold):
        '''
        Calculate the move cost of relocating a given from its current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            True
            #return(c_calcMoveCost._relocateToPositions(arcRelocate, arcPositionRemove, netCostRemove, arcToInsertAt, threshold))
        else:
            savings = []
            for arcToRelocateBefore in arcToInsertAt:
                arcPositionInsert = self.routeMapping[arcToRelocateBefore] # Relocate position
                (netCostInsert, arcToRelocateBeforePreArc) = self._calcInsertCost(arcPositionInsert, arcInsert) # Calculate cost of inserting an arc.
                relocateCost = netCostInsert
                if relocateCost < threshold:
                    savings.append((relocateCost, (arcInsert, None, None, arcToRelocateBefore, arcToRelocateBeforePreArc, None), 'insert', (0, netCostInsert)))
            return(savings)

    def insertEndRouteMoves(self, insertCandidates, routeDummyArcs, threshold = None, nNearest = None):
        '''
        Calculate the move cost of exception relocating an arc from current position before a dummy arc:
            - End of a route before the depot.
        First dummy arc(s) in the giant route should thus NOT be in dummyArcs set.
        '''
        if self.cModules:
            True
            #return(c_calcMoveCost.relocateEndRouteMoves(relocateCandidates, routeDummyArcs, threshold, nNearest))
        else:
            savings = []
            for dummyArcPosition in routeDummyArcs: # Arc will be inserted before the last dummy arc of a route, thus end of a route.
                if dummyArcPosition == 0: continue # Arc cannot be inserted before the giant route.
                (insertCandidates, threshold) = self._initiateMoveCostCalculations(insertCandidates, threshold)
                (currentDepotCost, preArc, dummyArc) = self._twoSeqCost(dummyArcPosition)
                arcToInsertAfter = self._findNearestNeighboursCandidates(preArc, nNearest, insertCandidates)
                for arcRelocate in arcToInsertAfter:        
                    netCostInsert = self._threeArcCost(preArc, arcRelocate, dummyArc)
                    relocateCost = netCostInsert - currentDepotCost
                    if relocateCost < threshold:
                        savings.append((relocateCost, (arcRelocate, None, None, dummyArc, preArc, None), 'insertBeforeDummy', (0, netCostInsert - currentDepotCost)))
                        
        return(savings)

    def relocateNewRoute(self, relocateCandidates, arcToRelocateBeforeCandidates, threshold = None, nNearest = None):
        '''
        Calculate the move cost of relocating an arc from current position to another. Exceptions are not calculated, such as moving
        an arc to the end of a route and replacing an arc with its inverse self.
        '''
        if self.cModules:
            return(c_calcMoveCost.relocateMoves(relocateCandidates, arcToRelocateBeforeCandidates, threshold, nNearest))
        else:
            savings = []
            (arcToRelocateBeforeCandidates, threshold) = self._initiateMoveCostCalculations(arcToRelocateBeforeCandidates, threshold)
            
            for arcRelocate in relocateCandidates:
                arcPositionRemove = self.routeMapping[arcRelocate]
                (netCostRemove, removePreArc, removePostArc) = self._calcRemoveCost(arcPositionRemove) # Calculate cost of removing an arc.         
                insertCost = self._d[self._depot][arcRelocate] + self._d[arcRelocate][self._depot] + self._dumpCost
                relocateCost = netCostRemove + insertCost
                savings.append((relocateCost, (relocateCost, removePreArc, removePostArc, None, None, None), 'relocateNewRoute', (netCostRemove, insertCost)))
        return(savings)
    
class MCARPTIFmoveFunctions(object):
    '''
    MCARP specific operators and move cost calculators.
    '''
    
    def __init__(self, info):
        '''
        Set parameters to be inherited.
        '''
        self._d = info.d 
        self._nArcs = len(self._d)
        self._inv = info.reqInvArcList
        self._edgesL = [arc for arc, invFlag in enumerate(self._inv) if invFlag != None]
        self._edgesS = set(self._edgesL)
        self._depot = info.depotnewkey
        self._reqArcs = info.reqArcListActual
        self._nReqArcs = len(self._reqArcs)
        self._reqArcsSet = set(self._reqArcs)
        self._demand = info.demandL
        self._servCost = info.serveCostL
        self._dumpCost = info.dumpCost
        self._if_cost = info.if_cost_np
        self._if_arc = info.if_arc_np
        self._ifs = info.IFarcsnewkey
    
    def returnRequiredArcs(self):
        return(self._reqArcsSet)
     
    def genMCARPTIFsolutionMapping(self, solution):
        '''
        Takes an initial solution and maps all the required arcs to route and inter-route positions.
        '''
        solutionMapping = {} # Mapping of an arc to its position (route and route position) in the solution.
        for i in range(solution['nVehicles']):
            nSubtrips = len(solution[i]['Trips'])
            for j in range(nSubtrips):
                subtrip = solution[i]['Trips'][j]
                for n, arc in enumerate(subtrip): # Each route consists of a start and end depot visit, with only one needed in the giant route.
                    solutionMapping[arc] = (i, j, n) # Since positioning starts at the first arc after the depot, j is increased by one.
                    if arc in self._edgesS: solutionMapping[self._inv[arc]] = (i, j, n) # Position of inverse arc is also captured, thus allowing for arc inversion (should come more into play with windy edges.
        return(solutionMapping)
     
    def genMCARPcumulativeRoute(self, route):
        loads = [self._demand[arc] for arc in route]
        costs = [self._servCost[arc] for arc in route]
        cumLoad = [loads[0]]
        cumServe = [costs[0]]
        for i in range(1, len(loads)):
            lValue = cumLoad[i - 1] + loads[i]
            cumLoad.append(lValue)
            sValue = cumServe[i - 1] + self._d[route[i - 1]][route[i]] + costs[i]
            cumServe.append(sValue)
        cumServe[-1] += self._dumpCost
        return(cumLoad, cumServe)
     
    def updateMCARPcumulitiveSolution(self, solution, routeI):
        (solution[routeI]['CumLoad'], solution[routeI]['CumServe']) = self.genMCARPcumulativeRoute(solution[routeI]['Route'])
        solution[routeI]['CumUpdate'] = True
        return(solution)
 
    def addMCARPcumulativeSolution(self, solution):
        '''
        Generates the cumulative load and cost at an arc position in a route.
        '''
        for i in range(solution['nVehicles']):
            route = solution[i]['Route']
            (solution[i]['CumLoad'], solution[i]['CumServe']) = self.genMCARPcumulativeRoute(route)
            solution[i]['CumUpdate'] = True
        return(solution)
 
    def genMCARPTIFgiantRouteMapping(self, solution):
        '''
        Takes an initial solution and generates a giant route with the necessary giant route arc position mapping. 
        '''
        giantMapping = [2*self._nArcs]*self._nArcs # List mapping of arcs to their position in the giant route. Will also include dummy arcs.
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
                    giantMapping[arc] = k # Since positioning starts at the first arc after the depot, j is increased by one.
                    if arc in self._edgesS: 
                        giantMapping[self._inv[arc]] = k # Position of inverse arc is also captured, thus allowing for arc inversion (should come more into play with windy edges.
                    
                    if j == nSubtrips - 1 and n == nArcs - 2:
                        dummyIFArcPositions.append(k)
                        giantMapping[arc] = 2*self._nArcs
                    elif j == nSubtrips - 1 and n == nArcs - 1:
                        dummyDepotArcPositions.append(k)
                        giantMapping[arc] = 2*self._nArcs
                    elif n == nArcs - 1:
                        dummyIFArcPositions.append(k)
                        giantMapping[arc] = 2*self._nArcs
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
        for arc in singleRouteArcs:
            if arc in self._edgesS:
                singleTripArcsF.add(self._inv[arc])
        
        verySpecialArcs = singleRouteArcsF.union(singleTripArcsF)        
        specialArcs = (beginRouteArcs, beginRouteArcsF, beginTripArcs, beginTripArcsF, endRouteArcs, endRouteArcsF, endTripArcs, endTripArcsF, singleRouteArcs, singleRouteArcsF, singleTripArcs, singleTripArcsF, verySpecialArcs)
        return(giantRoute, giantMapping, solutionArcs, specialArcs, normalArcs, normalArcsF, dummyDepotArcPositions, dummyIFArcPositions)
    
    
    
    
    
    
    
    
    
    