'''
Created on 27 May 2015

@author: eliaswillemse

Memetic Algoritm framework for the MCARP, as developed by Lacomme et al (2004) and
Belenguer et al (2006)

Lacomme, P., Prins, C., & Ramdane-Cherif, W. (2004). Competitive memetic algorithms for arc routing problems. Annals of Operations Research, 131(1-4), 159-185.
Belenguer, J. M., Benavent, E., Lacomme, P., & Prins, C. (2006). Lower and upper bounds for the mixed capacitated arc routing problem. Computers & Operations Research, 33(12), 3363-3383.
'''
from __future__ import division

import cPickle
import os
import sysPath
import sys
sys = sysPath.addInputPaths(sys)
mainPath = sysPath.returnPath()

from time import perf_counter as clock

from random import randrange
from random import random
from random import shuffle
from copy import deepcopy

from py_solution_test  import test_solution
import py_display_solution

import py_alg_ulusoy_partition as split

import py_LS_CARP_neighbour_super_efficient_multiple_moves as LS_MCARP_Quick
import LS_MCARP

SOLUTIONS_FOLDER = mainPath + '/LS_InputData/IntitialSolutions/'

class MemeticCARP(object):
    '''
    MA algorithm for the MCARP.
    '''
    
    def __init__(self, info, problemSet, problemName, tabu = False):
        '''
        MA info.
        '''
        
        # Problem info
        self._info = info
        self._problemSet = problemSet
        self._problemName = problemName
        self._inv = info.reqInvArcList
        self._reqArcs = info.reqArcListActual
        self._edgesL = [arc for arc in self._reqArcs if self._inv[arc] != None]
        self._edgesS = set(self._edgesL)
        self._arcsL = [arc for arc in self._reqArcs if arc not in self._edgesS]
        self._arcsS = set(self._arcsL)
        self._tabu = tabu
        
        # General procedures
        self.disply = py_display_solution.display_solution_stats(info) # Display solution info
        self._dispalyUnits = 1
        self._nArcs = len(self._reqArcs)
        if self._nArcs < 100: self._dispalyUnits = 100
        elif self._nArcs < 250: self._dispalyUnits = 10
        else: self._dispalyUnits = 1
        
        # MA procedures
        split.populate_c(info) # Split through Ulusoy partitioning
        self._splitGiantRoute = split.Ulusoys(info)
        #local_search_tabu.populate_c_local_searc(info) # Efficient Local search procedures within Tabu Search
        #self._localSearch_tabu = LS_MCARP.LS_MCARP(info, nn_list, testAll = True)   
        
        # MA internal parameters
        self._parametersSet = False # Check if MA parameters have been initialized
        self._parametersLocalSearchSet = False # Check if local search parameters have been initialized
        self._parametersLocalSearchTabuSet = False
        self._objectives = set() # Set of the population objective functions used to prohibit clones.
        self._nClones = 0 # Tracks the number of clones generated.
        self._worstFrac = 0.5 # Can be an input parameter
        self._incumbentCost = 1e300000 # Cost of incumbent solution
        self._niC = 0
        self._nsC = 0
        self._nrC = 0
        self._time = 0
        self._incTime = 0
        self._incGlobalT = 0 
        self._globalT = 0
        
    def _freeC(self):
        '''
        Free all Cython parameters. Program stops working if this is not done. 
        '''
        split.free_c()
        if self._parametersLocalSearchSet:
            self._localSearch.locaSearchFree()
    
    def _testSolutoin(self, solution):
        '''
        Test solution for errors.
        '''
        test_solution(self._info, solution)
    
    def _displaySolution(self, solution):
        '''
        Display detailed information of solution.
        '''
        self.disply.display_solution_info(solution)
    
    def _setReplacementLimit(self):
        self._nc05 = int(self._worstFrac*self._nc) - 1
        
    def setMA(self, nc = None, pm = None, ni = None, ns = 6000, nr = 20, pmr = 0.2, ncr = 0.7, nir = 2000, tL = 3600):
        '''
        Set MA parameters:
        
         nc : Population size
         pm : Local search rate in Phase 1
         ni : Total number of crossovers allowed in Phase 1
         ns : Total number of crossovers allowed without improving the best solution in Phase 1
         nr : Number of short restarts in Phase 2
        pmr : Local search rate in restarts
        ncr : Number of chromosomes replaced per restart
        nir : Number of allowed crossovers per restart
        tL  : Total allowed execution time on 2GHz processor
        '''
        
        self._nc = nc
        self._pm = pm
        self._ni = ni
        self._ns = ns
        self._nr = nr
        self._pmr = pmr
        self._ncr = ncr
        self._nir = nir
        self._setReplacementLimit()
        self._parametersSet = True
        self._tLimit = 2400 # 3600*2/3 Because of 3GHz processor vs 2GHz
    
    def setMA_BelenguerParameters(self):
        '''
        Set MA parameters according to Belenguer et al (2006):
        
        Parameters:
        
         nc = 30     (Population size)
         pm = 0.1    (Local search rate in Phase 1)
         ni = 20000  (Total number of crossovers allowed in Phase 1)
         ns = 6000   (Total number of crossovers allowed without improving the best solution in Phase 1)
         nr = 20     (Number of short restarts in Phase 2)
        pmr = 0.2   (Local search rate in restarts)
        ncr = 7     (Number of chromosomes replaced per restart)
        nir = 2000  (Number of allowed crossovers per restart)
        tL  = 3600  (Total allowed execution time on 2GHz processor)
        '''       
        
        self._nc = 10
        self._pm = 0.1
        self._ni = 20000
        self._ns = 6000
        self._nr = 20
        self._pmr = 0.2
        self._ncr = 7
        self._nir = 2000
        self._setReplacementLimit()
        self._parametersSet = True
        self._tLimit = 3600##3600*2/3

    def setTwoSolutionCrossParameters(self):
        '''
        Set MA parameters according to Belenguer et al (2006):
        
        Parameters:
        
         nc = 30     (Population size)
         pm = 0.1    (Local search rate in Phase 1)
         ni = 20000  (Total number of crossovers allowed in Phase 1)
         tL  = 3600  (Total allowed execution time on 2GHz processor)
        '''       
        
        self._nc = 2
        self._pm = 1
        self._ni = 1000
        self._ns = 1000
        self._nr = 0
        self._pmr = 0
        self._ncr = 0
        self._nir = 0
        self._setReplacementLimit()
        self._parametersSet = True
        self._tLimit = 3600##3600*2/3
       
    def setLocalSearch(self, nnList = None, NN = 0.1, testAll = False):
        '''
        Set Local Search parameters:
        
        Parameters:
        
        CL   : Candidate list active
        VNS  : Use Variable Neighbourhood Search
        NN   : Fraction of nearest neighrbours to consider
        R    : Reset CL at local optimum
        2Opt : Full 2Opt with restart
        '''       

        #NN = 0.1
        #CL = False
        self._localSearch = LS_MCARP.LS_MCARP(self._info, nnList, testAll = testAll)
        self._localSearch.nnFrac = NN
        self._localSearch.threshold = 0   
        self._localSearch.thresholdUse = 0
        self._localSearch.compoundMoves = True
        self._localSearch.doubleCross = False
        self._localSearch.comboFeasibleMoves = False
        self._localSearch.comboMovesVN = False
        self._localSearch.newDoubleCross = False
        self._localSearch.newComboFeasibleMoves = False
        self._localSearch.newComboMovesVN = False

        self._localSearch.setScreenPrint(False)

        self._parametersLocalSearchSet = True
        
    def setQuickLocalSearch(self, nnList = None, NN = 0.1):
        LS_MCARP_Quick.populate_c_local_searc(self._info)
        self._localSearch = LS_MCARP_Quick.multiple_neighbourhood_search(self._info, nnList)   
        self._localSearch.print_execution = False
        self._localSearch.print_output = False
        self._localSearch.fraction_to_test = NN
        
        self._localSearch.all_moves = False 
        self._localSearch.findfirst = True
        self._localSearch.VNS = True
        self._localSearch.reset = False
        self._localSearch.opt_direct = False
        self._localSearch.findfirst = True
        self._localSearch.reduce_routes = False
        
        self._localSearch.can_list = True
           
        self._localSearch.RI_flag = True
        self._localSearch.RI.c_modules = True
    
        self._localSearch.Ex_flag = True
        self._localSearch.Ex.c_modules = True
        
        self._localSearch.Twoopt_flag = True
        self._localSearch.Twoopt.c_modules = True
        
        self._localSearch.TwooptF_flag = False
        self._localSearch.TwooptF1_flag = False
        self._localSearch.nnFrac = NN
        self._localSearch.test = False
        
        self._parametersLocalSearchSet = True

    def setLocalSearchTabu(self, CL = True, VNS = False, NN = 0.1, R = True):
        '''
        Set Local Search parameters:
        
        Parameters:
        
        CL   : Candidate list active
        VNS  : Use Variable Neighbourhood Search
        NN   : Fraction of nearest neighrbours to consider
        R    : Reset CL at local optimum
        2Opt : Full 2Opt with restart
        '''       
        #NN = 0.1
        #CL = False
        
        self._localSearch_tabu.can_list = CL
        self._localSearch_tabu.VNS = VNS
        self._localSearch_tabu.fraction_to_test = NN#1#NN
        self._localSearch_tabu.reset = R
        
        self._localSearch_tabu.set_tabu_search(tabu_tenure = 5, nMoves_no_improved = 50)
        self._localSearch_tabu.threshold = 1
        
        self._localSearch_tabu.all_moves = False
        self._localSearch_tabu.print_execution = False
        self._localSearch_tabu.print_output = False
        self._localSearch_tabu.LS_complete = False
        self._localSearch_tabu.LS_loads = False
        self._localSearch_tabu.opt_direct = True
        self._localSearch_tabu.print_not_output = True

        self._localSearch_tabu.test = False
        self._localSearch_tabu.TwooptF_flag = True
        self._localSearch_tabu.TwooptF1_flag = False 
        self._parametersLocalSearchTabuSet = True

    def _combine(self, solution):
        '''
        Transform feasible solution into a giant route, first route left.
        Does not contain depots. 
        
        Example:
        
        solutionList = [[1,2,3], [4,5,6], [7,8,9]]
        giantSolution = [1,2,3,4,5,6,7,8,9]
        '''
        nVehicles = solution['nVehicles']
        solutionList = [solution[i]['Route'][1:-1] for i in range(nVehicles)]
        giantSolution = [arcTask for route in solutionList for arcTask in route]
        cost = solution['TotalCost']
        return(cost, giantSolution, solution)
        
    def _split(self, giantSolution):
        ''' 
        Split a giant route into feasible subroutes using Ulusoy's partitioning. Return the list and their costs.
        ''' 
        partialSolution = self._splitGiantRoute.genSolutionPartial(giantSolution)
        cost = partialSolution['TotalCost']
        return(cost, partialSolution)

    def _completeSolution(self, solution):
        ''' 
        Split a giant route into feasible subroutes using Ulusoy's partitioning. Return the list and their costs.
        ''' 
        solution = self._splitGiantRoute.genCompleteSolutionPartial(solution)
        return(solution)
    
    def _genSingleRandomInitialSolutin(self):
        randomEdgeOrientation = []
        edgeArcs = deepcopy(self._edgesS) # Only one orientation of an edge needs to be included. The orientation is chosen at random.
        while edgeArcs: #  are still edges not included in the random orientation.
            arc = edgeArcs.pop() # Remove any arc from edgeArcs (not control over which one, but it's not random)
            edgeArcs.remove(self._inv[arc]) # Remove its inverse from edgeArcs
            if random <= 0.5: arc = self._inv[arc] # With 0.5 probability, include the inverse instead of original.
            randomEdgeOrientation.append(arc) # Add chose orientation
        randomGiantSolution = deepcopy(self._arcsL) + randomEdgeOrientation # Create a new list consisting of arc tasks and selected edge task orientations.
        shuffle(randomGiantSolution) # Shuffle (randomise) the list to generate a random giant route.
        (randomSolutionCost, randomSolution)  = self._split(randomGiantSolution) # Calculate the cost of the random solution using Split.
        return(randomSolutionCost, randomGiantSolution, randomSolution)
        
    def _genRandomInitialSolution(self, improveAll = False):
        '''
        Generate a random giant route.
        '''
        (randomSolutionCost, randomGiantSolution, randomSolution) = self._genSingleRandomInitialSolutin()

        randomSolutionInfo = (randomSolutionCost, randomGiantSolution, randomSolution)
        print(randomSolutionInfo[0])
        if improveAll: 
            randomSolutionInfo = self._performLocalSearch(randomSolutionInfo)
            print(randomSolutionInfo[0])
        if self._checkClones(randomSolutionInfo):
            self._nClones += 1
            if self._nClones == 100:
                a = input('Duplicate children, not enough diversification')
            return(self._genRandomInitialSolution())
        else:
            self._nClones = 0
        return(randomSolutionInfo)
    
    def _genConstructiveInitialSolution(self):
        '''
        Generate an initial solution using constructive heuristics.
        '''
        constructiveGiantSolutionCost = 0
        constructiveGiantSolution = []
        return(constructiveGiantSolutionCost, constructiveGiantSolution)
    
    def _loadConstructiveInitialSolutions(self, best = True, solutionFolder = SOLUTIONS_FOLDER, improveAll = False):
        '''
        Load constructive heuristic initial solution population. Solutions include
        Ulusoy-PS-5-Rule, Improved-Merge, Path-Scanning-5-Rule, Ellipse-Path-Scanning-5-Rule.
        '''
        constructivePopulation = []

        problemSet = self._problemSet
        problem = self._problemName
        solutionFiles = os.listdir(SOLUTIONS_FOLDER) 
        print(problemSet + '_' + problem + '_')
        inputSolutions = [s for s in solutionFiles if s.find(problemSet + '_' + problem + '_') != -1 and ((s.find('best') != -1 and best == True) | (s.find('best') == -1 and best == False))]    
        for s in inputSolutions:
            initial = s[len(problemSet + '_' + problem + '_'):s.find('.')]
            print(initial)
            solutionFile = open(solutionFolder + s,'r')
            solutionStart = cPickle.load(solutionFile)
            solutionFile.close()
            
            solutionInfo = self._combine(solutionStart) # Option to perform local search on all startings solutions.
            print(solutionInfo[0])
            if improveAll: solutionInfo = self._performLocalSearch(solutionInfo)
            constructivePopulation.append(solutionInfo)
            print(solutionInfo[0])
        constructivePopulation.sort()
        return(constructivePopulation)

    def _solutionLocalSearch(self, solution):
        '''
        Perform local search or Tabu Search on an individual solution.
        '''
        solutionComplete = self._completeSolution(solution)
        solutionImproved = self._localSearch.locaSearchImbedded(solutionComplete)
        return(solutionImproved)

    def _performLocalSearch(self, solutionInfo):
        '''
        Perform local search or Tabu Search on an individual solution.
        '''
        solution = solutionInfo[2]
        solutionImproved = self._solutionLocalSearch(solution)
        improvedSolutionInfo = self._combine(solutionImproved) 
        return(improvedSolutionInfo)
    
    def _mutateSolution(self, solutionInfo):
        '''
        Mutate solution with certain probability using Local Search.
        '''
        if random() <= self._pm:
            solutionInfo = self._performLocalSearch(solutionInfo)
        return(solutionInfo)
    
    def _oxCrossover(self, P1, P2, p, q):
        '''
        Use two parents to create an Offspring, using OX-crossover. Crossover two parents
        at two specific points.       
        '''
        included = set() # // included = {}. No arcs are initially included in the child
        routeLength = len(P1) # // routeLength = 10
        sectionA = P1[p:q] # // sectionA = [5,6,7]. Sequence [p:q) is in the giantOffspring
        included |= set(sectionA) # // included = {5, 6, 7}. All arcs in giant offspring is now included.
        sectionB = [arc for arc in P2[q:] if arc not in included and self._inv[arc] not in included] # // SectionB = [9,4]. In Parent 2, starting with position q, find all arcs not yet included in Section A, and include these in Section B, and also check for inverse arcs.
        sectionB += [arc for arc in P2[:q] if arc not in included and self._inv[arc] not in included] # // SectionB = [9,4,8,1,2,3,0]. Find the remaining arcs not yet included and add to the end of Section B (results in a circular list of not yet included arcs of P2 starting at position P). 
        giantOffspring = sectionB[routeLength - q:] + sectionA + sectionB[:routeLength - q] # // giantOffspring = [2,3,0] + [5,6,7] + [9,4,8,1] = [2,3,0,5,6,7,9,4,8,1]. Offspring includes Section A in its original position, followed by the first arcs in Section B to fill up positions after p, The end of Section B is added to the beginning of Section A. 
        (offspringCost, offspringSolution)  = self._split(giantOffspring) # Calculate the cost of the offspring using Split.
        offspringInfo = (offspringCost, giantOffspring, offspringSolution)
        return(offspringInfo)
        
    
    def _oxCrossOverTwins(self, giantSolutionParent1, giantSolutionParent2, incNic = True, LS = True):
        '''
        Use two parents to create two Offsprings, and keep both.
        
        // Example:
        P1 = [9,8,4,5,6,7,1,3,2,0]
        P2 = [8,7,1,2,3,0,9,5,4,6]
        Cut of points [p,q), randomly selected, are before 5 (p=3) and after 7 (q=6)
        Offspring resulting from XO crossover is:
        C = [2,3,0,5,6,7,9,4,8,1]
        '''
        P1 = giantSolutionParent1
        P2 = giantSolutionParent2
        
        routeLength = len(P1) # // routeLength = 10
        p = randrange(routeLength - 1) # // p = 3. Starting cut. Arc in position p will be included in child. 
        if p == 0: q = randrange(1, routeLength - 1) # If cut starts at zero it cannot end at last arc - solution remains unchanged.
        else: q = randrange(p + 1, routeLength) # // q = 6. End cut. Arcs until position q - 1 will be included in child 
        offspringInfo1 = self._oxCrossover(P1, P2, p, q)
        offspringInfo2 = self._oxCrossover(P2, P1, p, q)
        if LS: offspringInfo1 = self._mutateSolution(offspringInfo1)
        if LS: offspringInfo2 = self._mutateSolution(offspringInfo2)
        clone1 = self._checkClones(offspringInfo1)
        clone2 = self._checkClones(offspringInfo2)
        if not clone1 and (clone2 or offspringInfo1[0] < offspringInfo2[0]): # Find best offspring that is not a clone.
            offspringInfo = offspringInfo1
        elif not clone2:
            offspringInfo = offspringInfo2
        else:
            return(False)
        if incNic: self._niC += 1 # Prevents niC from being incremented during restart initiation.
        return(offspringInfo)
                   
    def _oxCrossOver(self, giantSolutionParent1, giantSolutionParent2, incNic = True, LS = True):
        '''
        Use two parents to create an Offspring, using OX-crossover. Randomly keep one and
        check for duplicates.
        
        // Example:
        P1 = [9,8,4,5,6,7,1,3,2,0]
        P2 = [8,7,1,2,3,0,9,5,4,6]
        Cut of points [p,q), randomly selected, are before 5 (p=3) and after 7 (q=6)
        Offspring resulting from XO crossover is:
        C = [2,3,0,5,6,7,9,4,8,1]
        '''
        
        # Increment the number of crossovers performed
        
        
        # Randomly select which parent will be P1 and P2. Same as choosing an offspring at random.
        seqParents = randrange(2)
        P1 = [giantSolutionParent1, giantSolutionParent2][seqParents]
        P2 = [giantSolutionParent1, giantSolutionParent2][1 - seqParents]
        
        included = set() # // included = {}. No arcs are initially included in the child
        routeLength = len(P1) # // routeLength = 10
        p = randrange(routeLength - 1) # // p = 3. Starting cut. Arc in position p will be included in child. 
        if p == 0: q = randrange(1, routeLength - 1) # If cut starts at zero it cannot end at last arc - solution remains unchanged.
        else: q = randrange(p + 1, routeLength) # // q = 6. End cut. Arcs until position q - 1 will be included in child 
        sectionA = P1[p:q] # // sectionA = [5,6,7]. Sequence [p:q) is in the giantOffspring
        included |= set(sectionA) # // included = {5, 6, 7}. All arcs in giant offspring is now included.
        sectionB = [arc for arc in P2[q:] if arc not in included and self._inv[arc] not in included] # // SectionB = [9,4]. In Parent 2, starting with position q, find all arcs not yet included in Section A, and include these in Section B, and also check for inverse arcs.
        sectionB += [arc for arc in P2[:q] if arc not in included and self._inv[arc] not in included] # // SectionB = [9,4,8,1,2,3,0]. Find the remaining arcs not yet included and add to the end of Section B (results in a circular list of not yet included arcs of P2 starting at position P). 
        giantOffspring = sectionB[routeLength - q:] + sectionA + sectionB[:routeLength - q] # // giantOffspring = [2,3,0] + [5,6,7] + [9,4,8,1] = [2,3,0,5,6,7,9,4,8,1]. Offspring includes Section A in its original position, followed by the first arcs in Section B to fill up positions after p, The end of Section B is added to the beginning of Section A. 
        (offspringCost, offspringSolution)  = self._split(giantOffspring) # Calculate the cost of the offspring using Split.
        offspringInfo = (offspringCost, giantOffspring, offspringSolution)
        if LS: offspringInfo = self._mutateSolution(offspringInfo)
        if self._checkClones(offspringInfo): 
            self._nClones += 1
            if self._nClones == 1000:
                a = input('Duplicate children, not enough diversification')
            return(False)
        else:
            self._nClones = 0
            if incNic: self._niC += 1
        return(offspringInfo)

    def _checkClones(self, solutionInfo):
        '''
        Check that the same solution is not already in the solution space.
        '''
        solutionCost = solutionInfo[0]
        inpopulation = solutionCost in self._objectives
        return(inpopulation)
    
    def _addSolutionToPopulation(self, population, solutionInfo):
        '''
        Add solution to the population and upload its cost to check for future clones
        '''
        solutionCost = solutionInfo[0]
        self._objectives.add(solutionCost)
        population.append(solutionInfo)
        return(population)
        
    def _localSearchMutation(self, giantOffspring):
        '''
        Mutate a child solution through local search.
        '''
        mutatedGiantOffspringCost = 0
        mutatedGiantOffspring = []
        return(mutatedGiantOffspringCost, mutatedGiantOffspring)
    
    def _binTournement(self, solutionPopulation, iP = None):
        '''
        Randomly select two solutions and choose the best as parent one. Repeat for parent two.
        '''
        iP1 = randrange(self._nc)
        while iP1 == iP: iP1 = randrange(self._nc)
        iP2 = randrange(self._nc)
        while iP1 == iP2 or iP2 == iP: iP2 = randrange(self._nc)

        if solutionPopulation[iP1][0] < solutionPopulation[iP2][0]:
            iP = iP1
            giantSolutionParent = solutionPopulation[iP1][1]
        else:
            iP = iP2
            giantSolutionParent = solutionPopulation[iP2][1]
        return(giantSolutionParent, iP)
    
    def _produceOffspring(self, solutionPopulation):
        '''
        Select two parents using binary tournament selection and produce one offspring using OX-crossover.
        '''
        while True:
            (P1, iP) = self._binTournement(solutionPopulation)
            (P2, iP) = self._binTournement(solutionPopulation, iP)
            offspringInfo = self._oxCrossOver(P1, P2)
            if offspringInfo != False: break
        return(offspringInfo)

    def _produceTwoOffspring(self, solutionPopulation):
        '''
        Select two parents using binary tournament selection and produce one offspring using OX-crossover.
        '''
        while True:
            P1 = solutionPopulation[0][1]
            P2 = solutionPopulation[1][1]
            offspringInfo = self._oxCrossOverTwins(P1, P2)
            if offspringInfo != False: break
        return(offspringInfo)

    def _checkIncumbent(self, solutionPopulation):
        '''
        Check if best individual in the solution is better than the incumbent.
        '''
        if solutionPopulation[0][0] < self._incumbentCost:
            self._incTime = self._time
            self._nsC = 0
            self._incumbentCost = solutionPopulation[0][0]
            self._incGlobalT = self._globalT
        else:
            self._nsC += 1

    def _replaceSolution(self, solutionPopulation, offspringInfo, worstID):
        '''
        Replace one of the worse solutions with the new offspring.
        '''
        self._objectives.remove(solutionPopulation[worstID][0])
        del solutionPopulation[worstID]
        solutionPopulation = self._addSolutionToPopulation(solutionPopulation, offspringInfo)
        solutionPopulation.sort()
        self._checkIncumbent(solutionPopulation)
        return(solutionPopulation)
    
    def _introduceChild(self, solutionPopulation, offspringInfo):
        '''
        Replace one of the worse solutions with the new offspring.
        '''
        worstID = randrange(self._nc05, self._nc)
        solutionPopulation = self._replaceSolution(solutionPopulation, offspringInfo, worstID)
        return(solutionPopulation)

    def _introduceChildKillWorst(self, solutionPopulation, offspringInfo):
        '''
        Replace one of the worse solutions with the new offspring.
        '''
        worstID = len(solutionPopulation) - 1
        solutionPopulation = self._replaceSolution(solutionPopulation, offspringInfo, worstID)
        return(solutionPopulation)

    def _partialReplacement(self, solutionPopulation):
        '''
        Partial restart procedure that replaces a number of solutions in the population
        with randomly generated solutions which are cross-overed with each one in the current
        population.
        '''
        
        self._nrC += 1
        self._pm = self._pmr
        self._ni = self._nir
        self._niC = 0
        self._nsC = 0
        
        newPopulation = []
        for i in range(self._ncr):
            randomSolutionInfo = self._genRandomInitialSolution()
            newPopulation.append(randomSolutionInfo)
        newPopulation.sort()
        
        replacementObj = set()
        
        for i, replacement in enumerate(newPopulation):
            #print(i, replacement)
            if replacement[0] < solutionPopulation[-1][0]:
                solutionPopulation = self._replaceSolution(solutionPopulation, replacement, worstID = -1)
                replacementObj.add(replacement[0])
            else:
                bestChild = self._allPopulationCross(solutionPopulation + newPopulation[i+1:], replacement, replacementObj)
                if bestChild[0] < solutionPopulation[-1][0]:
                    solutionPopulation = self._replaceSolution(solutionPopulation, bestChild, worstID = -1)
                    replacementObj.add(bestChild[0])  
        return(solutionPopulation)            
    
    def _allPopulationCross(self, solutionPopulation, candidate, exclusions):
        '''
        Crossover a candidate solution with all members in a population, excluding some,
        and return the best child.
        '''
        bestChild = (1e300000,[],[])
        
        for solution in solutionPopulation:
            childInfo = self._oxCrossOverTwins(solution[1], candidate[1], incNic = False, LS = False)
            if childInfo != False:
                #print(childInfo[0], bestChild[0], candidate[0], solution[0])
                if childInfo[0] < bestChild[0]:
                    bestChild = childInfo 
        return(bestChild)
            
    def _generateInitialPopulation(self):
        '''
        Generate an initial population, consisting of constructive heuristic solutions and random solutions.
        ''' 
        population = []
        constructivePopulation = self._loadConstructiveInitialSolutions(improveAll = False)
        for initialSolutionInfo in constructivePopulation: 
            if not self._checkClones(initialSolutionInfo):
                population = self._addSolutionToPopulation(population, initialSolutionInfo)
        nCurrenSize = len(population)
        for i in range(self._nc - nCurrenSize):
            randomSolutionInfo = self._genRandomInitialSolution()
            population = self._addSolutionToPopulation(population, randomSolutionInfo)
        population.sort()
        self._checkIncumbent(population)
        return(population)

    def _generateRandomdPopulation(self):
        '''
        Generate a random population.
        ''' 
        population = []
        for i in range(self._nc):
            randomSolutionInfo = self._genRandomInitialSolution()
            population = self._addSolutionToPopulation(population, randomSolutionInfo)
        population.sort()
        self._checkIncumbent(population)
        return(population)

    def _generateTwoPopulation(self):
        '''
        Generate an initial population, consisting of constructive heuristic solutions and random solutions.
        ''' 
        population = []
        constructivePopulation = self._loadConstructiveInitialSolutions(improveAll = True)
        for initialSolutionInfo in constructivePopulation: 
            if not self._checkClones(initialSolutionInfo):
                population = self._addSolutionToPopulation(population, initialSolutionInfo)
        population.sort()
        self._checkIncumbent(population)
        return(population[:2])
    
    def _populationStats(self, population):
        '''
        Calculate population fitness statistics: size, best, median, worst.
        '''
        sizeP = len(population)
        bestP = population[0][0]
        midP = population[self._nc05][0]
        worstP = population[-1][0]
        return(sizeP, bestP, midP, worstP)
  
    def _printInitialisation(self):
        '''
        Display basic problem info
        '''
        print('CARP MA')
        print(self._problemSet)
        print(self._problemName)
        print('')
  
    def _printPopulationStats(self, population):
        '''
        Display population statistics.
        '''
        (sizeP, bestP, midP, worstP) = self._populationStats(population)
        sOutput = 'Best: %i \t Mid: %i \t Worst: %i \t nc: %i \t ni: %i of %i \t ns: %i of %i \t nr: %i of %i \t Time: %.2f of %.2f'%(bestP, midP, worstP, sizeP, self._niC, self._ni, self._nsC, self._ns, self._nrC, self._nr, self._time, self._tLimit)
        if self._niC%self._dispalyUnits == 0:
            print(sOutput)

    def _returnBest(self, population):
        '''
        Find and test the incumbent solution
        '''
        bestSolution = population[0][2]
        completeSolution = self._completeSolution(bestSolution)
        self._displaySolution(completeSolution)
        self._testSolutoin(completeSolution)
        return(completeSolution)
    
    def runMA(self):
        '''
        Execute the Memetic Algorithm
        '''
        tStart = clock()
        
        self._printInitialisation()
        if not self._parametersSet:
            a = input('Need to set parameters first')
        
        self._time = 0
        population = self._generateInitialPopulation()
        self._globalT = 0 
        while self._nrC < self._nr or self._niC < self._nir:
            self._globalT += 1
            t = self._time
            offspringInfo = self._produceOffspring(population)
            population = self._introduceChild(population, offspringInfo)
            self._printPopulationStats(population)
            if self._nsC > self._ns or self._niC > self._ni:
                population = self._partialReplacement(population)
            self._time = clock() - tStart
            if self._time - t < 0.01: self._dispalyUnits = 100
            elif self._time - t < 0.1: self._dispalyUnits = 10
            if self._time >= self._tLimit: break
        completeSolution = self._returnBest(population)
        self._freeC()
        return(completeSolution)
    
    def returnStats(self, solution, version):
        metaheuristic = 'MemeticAlgorithm'
        l = '%s,%s,%s,%s,%.2f,%i,%.4f,%i,%i\n'%(self._problemSet, self._problemName, metaheuristic, version, self._localSearch.nnFrac, solution['TotalCost'], self._time, self._globalT, self._incGlobalT)
        return(l)
            
    def runTwoSolutionCross(self):
        '''
        Execute the Memetic Algorithm
        '''
        tStart = clock()
        
        self._printInitialisation()
        if not self._parametersSet:
            a = input('Need to set parameters first')
        
        self._time = 0
        population = self._generateTwoPopulation()
        self._globalT = 0 
        self._dispalyUnits = 1
        while self._niC < self._ni:
            self._globalT += 1
            t = self._time
            offspringInfo = self._produceTwoOffspring(population)
            population = self._introduceChildKillWorst(population, offspringInfo)
            self._printPopulationStats(population)
            self._time = clock() - tStart
            #if self._time - t < 0.001: self._dispalyUnits = 100
            #elif self._time - t < 0.01: self._dispalyUnits = 10
            if self._time >= self._tLimit: break       
        completeSolution = self._returnBest(population)
        self._freeC()
        return(completeSolution)    
        
