# -*- coding: utf-8 -*-
"""Ruin and recreate algorithm for the MCARPTIF.

This module is an implementation of the ruin and recreate metaheuristic for the 
Mixed Capacitated Arc Routing problem under Time Restrictions with Intermediate 
Facilities (MCARPITF). The module works with an existing solution, removes a 
specified set of arcs and creates new routes using the removed arcs and the 
Path-Scanning greedy-heuristic. The modified solution is returned and can then
be improved using Local Search, or more advanced single-solution based 
metaheuristics.

Algorithm steps:

    Input: Initial solution, improvement procedure, ruin-strategy, stopping
        criteria.
        
    Set the initial solution to the current solution
    Improve current solution using the improvement procedure.
    
    Update incumbent with current solution
    
    While stopping criteria has not been met:

        1. Ruin the current solution using the ruin-strategy
        2. Improve current solution using the improvement procedure.
        3. Update incumbent with current solution
        
    return incumbent solution

Note:

* Improvement procedure can be Local Search, or any single-solution based meta-
heuristic.

* Ruin-strategy can be pure-random where a random number of randomly selected
arcs are removed and included in a new solution; semi-random where a specified
number of arcs are randomly selected; or deterministic where specific arcs are
selected, optionally based on Local Search performance.

* Restart option at incumbent possible instead of always ruining the current
solution.

Solutions are represented as lists of lists of lists up-to subtrips which 
consists of arc visitation sequences INCLUDING the required depot and IF visits.

T = [[[depo1,arc1,arc2,...,IF1], [IF1,arc3,arc4,...,]]]
T = [route1, route2,...,route_K]
route1 = [subtrip1, subtrip2,...,subtrip_K]
subtrip1 = [depot, arc1, arc2,...,IF]

The module can be used as-is for the MCARP by representing it as a single route 
with subtrips, each representing the actual route, and including a dummy depot 
at the end of the last subtrip (required since MCARPTIF ends with an IF and then 
depot).

Deepcopy is used extensively since the heuristic should be able to work with 
and generate candidate solutions.

Todo:
    * Convert solutions to lists of lists [Done].
    * Add a transformation function to the MCARP.
    * Create a better unit test for recreating a solution by hard-coding a 
        solution and all it's problem info [Partially done, problem info not].
    * Create a clean implementation of path-scanning.
    * Consider the validity of returning new solution copies.
    * Consider adding unit test to check that the depot or IF arcs are not
        removed.
    * Recreate black-boxes: reduce trips, solution builders, LS
    * Fix errors in LS when an empty route is left in the solution and not
        automatically deleted.
    
History:
    Created on 22 Sep 2017
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import random
import solver.py_alg_extended_path_scanning_rr as EPS
import solver.LS_MCARP as LS_MCARP
import solver.LS_MCARPTIF as LS_MCARPTIF

from solver.py_solution_builders_rr import build_solutions
from solver.py_reduce_number_trips_rr import Reduce_Trips

from math import floor
from copy import deepcopy
from time import clock


def return_arc_position(solution, arc, inv_arc = None):
    """Finds the position of an arc or its inverse in the solution.
    
    Args:
        solution (list): solution for the MCARPTIF.
        arc (int): arc to find in the solution.
        inv_arc (int): inverse arc to also look for in the solution.
        
    Returns:
        routeI (int): index of the first route in which the arc is served, 
            returns None if arc is not found.
        subrouteJ (int): index of the first subroute in route i in which the arc 
            is served, returns None if arc is not found.
        positionK (int): index of the first position of the arc in subroute i of 
            route i in which the arc is served, and returns None if arc is not 
            found.
        
    Raises:
         ValueError: If `arc` or `inv_arc` could not be found in the solution.
    """
    # Necessary to check inv arc, else the error will be raised for inv arcs.
    for i, route in enumerate(solution):
        for j, subroute in enumerate(route):
            if arc is not None and arc in subroute:
                return i, j, subroute.index(arc)
            elif inv_arc is not None and inv_arc in subroute: # Prevents the 
                # position of None from being returned if it's in the solution 
                # as a place-holder, i.e. MCARP.
                return i, j, subroute.index(inv_arc)
            
    raise ValueError


def find_arcs(solution, removal, inv_arcs=None):
    """Find positions of arcs in the solution.
    
    Args:
        solution (list): solution for the MCARPTIF.
        removal (set): set of arcs to remove from the solution.
        inv_arcs (list): optional list inversed arcs mapping. Inversed arcs in 
            `removal` may be present in the solution and should be removed.
        
    Returns:
        removal_positions (list): a list of tuple positions of arcs to be 
        to be removed.
    """
    removal_positions = []
    for arc in removal:
        (i, j, k) = return_arc_position(solution, arc, inv_arcs[arc])
        removal_positions.append((i, j, k))
        
    return removal_positions


def remove_arcs(solution, removal, inv_arcs):
    """Removes specified arcs from the solution and returns the modified 
    solution.
    
    Args:
        solution (list): solution for the MCARPTIF.
        removal (set): set of arcs to remove from the solution.
        inv_arcs (list): optional list inversed arcs mapping. Inversed arcs in 
            `removal` may be present in the solution and should be removed.
        
    Returns:
        solution_update (list): a deep copy of the solution with arcs from 
            `removal` successfully removed.
            
    Todo:
        * Automatically remove empty subtrips and routes from the solution, but 
        note that it will require us to recalculate the best IF locations. 
        Although, this will be required in any case since we may have changed 
        arc locations relative to IFs.     
    """
    removal_positions = find_arcs(solution, removal, inv_arcs)
    solution_update = deepcopy(solution)
    for (i, j, k) in removal_positions:
        solution_update[i][j][k] = None  # If we use del we have to update
        # indices of following removals.
    
    # We can now rebuild the subtrips by excluding `None` arcs that were 
    # removed.
    for i, route in enumerate(solution_update):
        for j, subtrip in enumerate(route):
            solution_update[i][j] = [arc for arc in subtrip if arc is not None]

    return solution_update


def random_remove_arcs(solution, nArcs=None, nArcsFrac=None, randomSeed=None):
    """Removes a specified number of randomly selected arcs from the solution 
    and returns the modified solution.
    
    Args:
        solution (list): solution for the MCARPTIF.
        nArcs (int): number of arcs to remove from the solution.
        inv_arcs (list): optional list inversed arcs mapping. Inversed arcs in 
            `removal` may be present in the solution and should be removed.
        randomSeed (int): specify the seed number, used for testing.
        
    Returns:
        removal (list): random arcs to be removed.
    """
    
    solutionArcs = []
    for route in solution:
        for j, subtrip in enumerate(route):
            # IFs and depots should not be removed.
            if j == len(route) - 1:
                n = -2
            else:
                n = -1
            solutionArcs += subtrip[1:n]

    if nArcs == None and nArcsFrac == None:  # If the number of arcs is not
        # specified, a random number is selected.
        if randomSeed != None: 
            random.seed(randomSeed)
        nArcs = random.randint(1, len(solutionArcs) - 1)
        
    if nArcs == None and nArcsFrac != None:
        nArcs = int(round(nArcsFrac*len(solutionArcs), 0))
        
    if randomSeed != None: 
        random.seed(randomSeed)
        
    removal = random.sample(solutionArcs, nArcs)

    return removal


def construct_routes(arcs, instance_info, problemType='MCARPTIF'):
    """Creates new routes that cover the given arcs using the path-scanning 
        greedy heuristic.
    
    Args:
        arcs (set): set of arcs used to create the new solution.
        instance_info (class): information of the problem instance, required by 
            the greedy heuristic to generate a feasible solution from arcs.
        problemType (str): problem class, with MCARPTIF and MCARP recognized.
        
    Returns:
        solution (list): a solution with feasible routes covering the given 
            arcs.  
    """
    
    allArcs = instance_info.reqArcList[:] # Still passes unit test without [:]
    allInvArcs = instance_info.reqInvArcList[:]
    
    instance_info.reqArcList = arcs
    instance_info.reqInvArcList = [None]*len(instance_info.reqInvArcList)
    
    if problemType == 'MCARPTIF':
        NNS = EPS.EPS_IF(instance_info)
    elif problemType == 'MCARP':
        NNS = EPS.EPS(instance_info)
        
    NNS.reqArcs = arcs
    NNS.invArcList = instance_info.reqInvArcList
    NNS.c_modules = False
    NNS.reduce_all_trips = False # Optional to try and reduce the trips after 
    # being called.
    NNS.print_iter = 10000
    
    if problemType == 'MCARPTIF':
        solution = NNS.EPS_IF_solver(rule_type = 'EPS_all_rules')[0][0]
        solution_lists = decode_MCARPTIF_solution(solution)
    elif problemType == 'MCARP':
        solution = NNS.EPS_solver(rule_type = 'EPS_five_rules')[0]
        solution_lists = decode_MCARP_solution(solution) # A dummy arc is 
        # therefore automatically included in the last route.

    instance_info.reqArcList = allArcs
    instance_info.reqInvArcList = allInvArcs
    
    return solution_lists


def dec_construct_reconstruct_routes(solution, arcs, instance_info, 
                                     problemType='MCARPTIF'):
    """De-construct a solution by removing arcs, and reconstruct the solution
    by creating a new route from the arcs and inserting them into the solution
    as new routes.
    
    Args:
        solution (list): solution from which arcs will be removed and 
            reinserted.
        arcs (set): set of arcs to remove.
        instance_info (class): information of the problem instance, required by 
            the greedy heuristic to generate a feasible solution from arcs.
        problemType (str): problem class, with MCARPTIF and MCARP recognized.
        
    Returns:
        solution_update (list): a solution deep copy with removed arcs 
            reinserted as new routes to the solution.
    """
    
    solution_update = remove_arcs(solution, arcs, instance_info.reqInvArcList)
    solution_new = construct_routes(arcs, instance_info, problemType)
    
    if problemType == 'MCARPTIF':
        solution_update += solution_new
    elif problemType == 'MCARP':
        # First, the dummy arc is removed and then reformatted
        # into a singe route with subtrips.
        solution_update = [revert_MCARP_solution(solution_update)]
                
        # The new routes, i.e. subtrips of the single route with the last one 
        # having a dummy depot, is added to the end of the single route 
        # solution. 
        solution_update[0] += solution_new[0]
        
    return solution_update


def decode_MCARPTIF_solution(solution):
    """Decodes the full solution dictionary into the required solution format
    for `ruin_recreate.py`.
    
    Args:
        solution (dict): full MCARPTIF solution dictionary.
        
    Returns:
        solution_list (list): a solution in the form of lists of lists of lists.
    """
    solution_list = []
    for i in range(solution['nVehicles']):
        solution_list.append(solution[i]['Trips'])
    
    return solution_list


def encode_MCARP_solution(solution):
    """Encode the MCARP solution into the MCARPTIF for `ruin_recreate.py`.
    
    Args:
        solution (list): MCARP solution list.
        
    Returns:
        solution_MCARPTIF (list): a solution deepcopy in the MCARPTIF format.
            Not sure if a deepcopy is necessary though.
    """
    solution_MCARPTIF = [deepcopy(solution)] # MCARP is converted into a single
    # route MCARPTIF. Subtrips represent MCARP routes.
    solution_MCARPTIF[0][-1].append(solution_MCARPTIF[0][-1][-1]) # MCARPTIF 
    # ends with an IF and depot, which are not considered for removal. A dummy 
    # depot visit is added to the last subtrip in the single route.
    
    return solution_MCARPTIF


def revert_MCARP_solution(solution):
    """Revert the MCARPTIF solution representation of the MCARP into the MCARP  
    for `ruin_recreate.py`.
    
    Args:
        solution (list): MCARPTIF solution list of the MCARP.
        
    Returns:
        solution_MCARP (list): a solution deepcopy in the MCARP format.
            Not sure if a deepcopy is necessary though.
    """
    solution_MCARP = deepcopy(solution[0]) # MCARPIF is converted back into
    # a MCARP.
    del solution_MCARP[-1][-1] # The dummy depot visit at the end of the last
    # route is removed.
    
    return solution_MCARP


def decode_MCARP_solution(solution):
    """Decodes the full MCARPsolution dictionary into the required solution 
    format for `ruin_recreate.py`.
    
    Args:
        solution (dict): full MCARP solution dictionary.
        
    Returns:
        solution_list (list): a solution in the form of lists of lists of lists.
    """
    solution_list = []
    for i in range(solution['nVehicles']):
        solution_list.append(solution[i]['Route'])
    
    solution_list = encode_MCARP_solution(solution_list)
    
    return solution_list


def create_initial_solution(instance_info, problemType='MCARPTIF'):
    """Create a feasible initial solution for the problem instance
    
    Arcs:
        instance_info (class): information of the problem instance.
        problemType (str): problem class, with MCARPTIF and MCARP recognized.
        
    Returns:
        initial_solution (dict): full solution dictionary for the instance.
    """
    
    if problemType == 'MCARPTIF':
        EPS.populate_c_local_search(instance_info, True)
        NNS = EPS.EPS_IF(instance_info)
    elif problemType == 'MCARP':
        NNS = EPS.EPS(instance_info)
        EPS.populate_c_local_search(instance_info)
    
    NNS.c_modules = True
    NNS.reduce_all_trips = True 
        
    if problemType == 'MCARPTIF':
        initial_solution = NNS.EPS_IF_solver(rule_type = 'EPS_all_rules')[0][0]
    elif problemType == 'MCARP':
        initial_solution = NNS.EPS_solver(rule_type = 'EPS_five_rules')[0]
    
    EPS.free_c_local_search()
    
    return initial_solution
    

def update_incumbent(candidate_solution, incumbent_solution):
    """Updates the incumbent solution
    
    Args:
        candidate_solution (dict): full candidate solution
        incumbent_solution (dict): full incumbent solution
        
    Returns:
        incumbent_solution (dict): possibly new incumbent solution deepcopy
        new_incumbent (Flag): True if new incumbent solution was found 
    """
    
    new_incumbent = False
    if candidate_solution['nVehicles'] < incumbent_solution['nVehicles']:
        new_incumbent = True
    elif candidate_solution['nVehicles'] == incumbent_solution['nVehicles']:
        if candidate_solution['TotalCost'] < incumbent_solution['TotalCost']:
            new_incumbent = True
    
    if new_incumbent:
        incumbent_solution = deepcopy(candidate_solution)
        
    return incumbent_solution, new_incumbent


def ruin_recreate_template(instance_info, improvement_procedure, ruin_strategy, 
        stopping_criteria, initial_solution=None, problemType='MCARPTIF'):
    
    """Apply ruin and recreate metaheuristic to an initial solution.
    
    Arcs:
        instance_info (class): information of the problem instance.
        improvement_procedure (class): pre-setup improvement procedure used to
             improve solutions.
        ruin_strategy (dict): conditions for stopping the procedure.
        initial_solution (dict): full solution dictionary, if None is provided
            a solution is generated using Path-Scanning.
        problemType (str): problem class, with MCARPTIF and MCARP recognized.
            
    Returns:
        incumbent_soltion (dict): a full incumbent solution dictionary of the 
            final solution.
        output (dict): output of the algorithm execution performance, including
            total execution time, time of and solution at each ruin-recreate-
            improve step, and total improvement percentage over the initial
            solution.
    
    Raises:
         ValueError: If solution at any point during the search is no longer 
             feasible.
    """
    
    # Create initial solution of required.
    # Improve initial solution
    
    # Start ruin and recreate strategy
    
    return None


def initiate_improvement_setup_MCARP(instance_info, nn_list, 
        improvement_procedure = 'LS'):
    """Initiates the specified improvement procedures solver with hard
    coded :( parameters.
    
    Args:
        instance_info (class): information of the problem instance.
        nn_list (list): nearest neighbour-lists required for Local Search.
        improvement_procedure (str): type of improvement procedure to setup,
            with `LS` (for Local Search) and `TS` (for Tabu Search) recognized.
            
    Returns:
        imp_proc (class): initialised improvement procedure.
    """
    if improvement_procedure == 'LS':
        # cython files are automatically initialized
        imp_proc = LS_MCARP.LS_MCARP(instance_info, nn_list, testAll = False, 
                           autoInvCosts = False)
        
        # ======= DEFAULT =======
        # Activate extended Local Search
        imp_proc.doubleCross = True
        imp_proc.comboFeasibleMoves = True
        imp_proc.comboMovesVN = True
        
        # Activate acceleration functions
        restrict = False
        imp_proc.nonAdjacentRestrictionInsert = restrict
        imp_proc.nonAdjacentRestrictionExchange = restrict
        imp_proc.nonAdjacentRestrictionCross = restrict
        
        # Activate acceleration functions
        imp_proc.candidateMoves = True
        imp_proc.compoundMoves = True
        
        # Do not print output
        imp_proc.setScreenPrint(False)

        # ======= NON-DEFAULT =======
        imp_proc.nnFrac = 1 # Set nearest neighbor fraction, to be changed. 
        
        
    if improvement_procedure == 'TS':
        imp_proc = LS_MCARP.TabuSearch_MCARP(instance_info, nn_list, 
                                             testAll = False)
        
        # ======= DEFAULT =======
        compoundMoves = True
        newCompoundMoves = False
        tabuTenure = 5
        tabuThreshold = 1
        tabuMoveLimit = 1000
        saveOutput = False
        imp_proc._printOutput = False #Do not print output
        imp_proc.suppressOutput = False
        
        # ======= NON-DEFAULT =======
        nnFrac = 1
        maxNonImprovingMoves = 50
        
        imp_proc.setTabuSearchParameters(compoundMoves, newCompoundMoves,
            tabuTenure, tabuThreshold, nnFrac, tabuMoveLimit, 
            maxNonImprovingMoves, saveOutput)
        
    return imp_proc


def clear_improvement_setup(improvement_procedure):
    """Clears cython modules of the improvement procedure"""
    improvement_procedure.clearCythonModules()


def ruin_recreate_random_MCARP(instance_info, nn_list, 
        improvement_procedure='LS', randomSeed=None):   
    
    """Apply ruin recreate for the MCARP
        
    Arcs:
        instance_info (class): information of the problem instance.
        nn_list (list): nearest neighbour-lists required for Local Search.
        improvement_procedure (str): type of improvement procedure to setup,
            with `LS` (for Local Search) and `TS` (for Tabu Search) recognized.
        randomSeed (int): specify the seed number, used for testing.
        
    Returns:
        incumbent_soltion (dict): a full incumbent solution dictionary of the 
            final solution.
    """
    
    start_time = clock()
    
    # Used to reduce the number of routes and rebuild a solution dictionary from
    # the solution lists.
    RT = Reduce_Trips(instance_info)
    SB = build_solutions(instance_info)
    
    if randomSeed != None: 
        random.seed(randomSeed)
    
    # Setup the improvement procedure
    impr_proc = initiate_improvement_setup_MCARP(instance_info, nn_list, 
        improvement_procedure)
    
    current_solution = create_initial_solution(instance_info, 
                                               problemType="MCARP")
    
    # Improve the initial solution and set it to the incumbent
    current_solution = impr_proc.improveSolution(current_solution)
    incumbent_solution = deepcopy(current_solution)
    
    print('Starting solution: {0}'.format(current_solution['TotalCost']))
    return None
    # Stopping criteria is simply total number of ruins and recreates
    for i in range(20):
        # Perform pure random ruin and recreate
        current_solution_lists = decode_MCARP_solution(current_solution)
        removeArcs = random_remove_arcs(current_solution_lists, nArcsFrac=0.1)
        
        current_solution_lists = dec_construct_reconstruct_routes(
            current_solution_lists, removeArcs, instance_info, 
            problemType='MCARP')
        
        # Revert to dictionary for improvement
        current_solution_lists = revert_MCARP_solution(current_solution_lists)
        current_solution = SB.build_MCARP_solution_dict(current_solution_lists)
        # Attempt to reduced number of routes, can generate errors
        current_solution = RT.reduce_CARP_solution(current_solution)[1]
        cost_pre_improvement = current_solution['TotalCost']
        # Improve solution using improvement procedure
        current_solution = impr_proc.improveSolution(current_solution)
        
        # Update incumbent solution
        incumbent_solution = update_incumbent(current_solution, 
                                              incumbent_solution)[0]
        
        # Print execution
        execution_time = clock() - start_time
        output = '{0} -> Pre-improve cost: {1} \t Current cost: {2} \t Current fleet size: {3} \t Incumbent cost: {4} \t Execution time (sec): {5}'.format(i, cost_pre_improvement, current_solution['TotalCost'], current_solution['nVehicles'], incumbent_solution['TotalCost'], round(execution_time, 2)) 
        print(output)
    
    clear_improvement_setup(impr_proc)
    
    return incumbent_solution


def initiate_improvement_setup_MCARPTIF(instance_info, nn_list, 
        improvement_procedure = 'LS'):
    """Initiates the specified improvement procedures solver with hard
    coded :( parameters.
    
    Args:
        instance_info (class): information of the problem instance.
        nn_list (list): nearest neighbour-lists required for Local Search.
        improvement_procedure (str): type of improvement procedure to setup,
            with `LS` (for Local Search) and `TS` (for Tabu Search) recognized.
            
    Returns:
        imp_proc (class): initialised improvement procedure.
    """
    if improvement_procedure == 'LS':
        # cython files are automatically initialized
        imp_proc = LS_MCARPTIF.LS_MCARPTIF(instance_info, nn_list, 
            testAll = False, autoInvCosts = False)
        
        # ======= DEFAULT =======
        # Activate extended Local Search
        imp_proc.doubleCross = True
        imp_proc.comboFeasibleMoves = True
        imp_proc.comboMovesVN = True
        imp_proc.threshold = 0
        imp_proc.thresholdUse = 1
        
        # Activate acceleration functions
        imp_proc.candidateMoves = True
        imp_proc.compoundMoves = True
        
        # Do not print output
        imp_proc.setScreenPrint(False)

        # ======= NON-DEFAULT =======
        imp_proc.nnFrac = 1 # Set nearest neighbor fraction, to be changed. 

    if improvement_procedure == 'TS':
        imp_proc = LS_MCARPTIF.TabuSearch_MCARPTIF(instance_info, nn_list, 
                                             testAll = False)
        
        # ======= DEFAULT =======
        compoundMoves = True
        newCompoundMoves = False
        tabuTenure = 5
        tabuThreshold = 1
        tabuMoveLimit = 1000
        saveOutput = False
        imp_proc._printOutput = False #Do not print output
        imp_proc.suppressOutput = False
        
        # ======= NON-DEFAULT =======
        nnFrac = 1
        maxNonImprovingMoves = 100
        
        imp_proc.setTabuSearchParameters(compoundMoves, newCompoundMoves,
            tabuTenure, tabuThreshold, nnFrac, tabuMoveLimit, 
            maxNonImprovingMoves, saveOutput)
        
    return imp_proc


def create_improve_MCARPTIF(instance_info, nn_list, improvement_procedure='LS'):
    
    """Construct and improve a solution for the MCARPTIF.
    
    Arcs:
        instance_info (class): information of the problem instance.
        nn_list (list): nearest neighbour-lists required for Local Search.
        improvement_procedure (str): type of improvement procedure to setup,
            with `LS` (for Local Search) and `TS` (for Tabu Search) recognized.
        
    Returns:
        solution (dict): a full solution dictionary of the improved solution.
    """
    
    impr_proc = initiate_improvement_setup_MCARPTIF(instance_info, nn_list, 
    improvement_procedure)
    
    solution = create_initial_solution(instance_info, 
                                               problemType="MCARPTIF")
    
    # Improve the initial solution and set it to the incumbent
    solution = impr_proc.improveSolution(solution)
    return(solution)
    

def ruin_recreate_random_MCARPTIF(instance_info, nn_list, 
        improvement_procedure='LS', randomSeed=None):   
    
    """Apply ruin recreate for the MCARPTIF
        
    Arcs:
        instance_info (class): information of the problem instance.
        nn_list (list): nearest neighbour-lists required for Local Search.
        improvement_procedure (str): type of improvement procedure to setup,
            with `LS` (for Local Search) and `TS` (for Tabu Search) recognized.
        randomSeed (int): specify the seed number, used for testing.
        
    Returns:
        incumbent_soltion (dict): a full incumbent solution dictionary of the 
            final solution.
    """
    
    start_time = clock()
    
    # Used to reduce the number of routes and rebuild a solution dictionary from
    # the solution lists.
    RT = Reduce_Trips(instance_info)
    SB = build_solutions(instance_info)
    
    if randomSeed != None: 
        random.seed(randomSeed)
    
    # Setup the improvement procedure
    impr_proc = initiate_improvement_setup_MCARPTIF(instance_info, nn_list, 
        improvement_procedure)

    # Generate and improve the initial solution and set it to the incumbent
    current_solution = create_improve_MCARPTIF(
                            instance_info, 
                            nn_list,
                            improvement_procedure=improvement_procedure, 
                            randomSeed=randomSeed)
    
    incumbent_solution = deepcopy(current_solution)
    
    print('Starting solution: {0}'.format(current_solution['TotalCost']))

    # Stopping criteria is simply total number of ruins and recreates
    for i in range(20):
        # Perform pure random ruin and recreate
        current_solution_lists = decode_MCARPTIF_solution(current_solution)
        removeArcs = random_remove_arcs(current_solution_lists, nArcsFrac=0.1)
        
        current_solution_lists = dec_construct_reconstruct_routes(
            current_solution_lists, removeArcs, instance_info, 
            problemType='MCARPTIF')
  
        # Revert to dictionary for improvement
        current_solution = SB.build_CLARPIF_dict(current_solution_lists)
        # Attempt to reduced number of routes, can generate errors
        current_solution = RT.reduce_CLARPIF_solution_v2(current_solution)[1]
        cost_pre_improvement = current_solution['TotalCost']
        # Improve solution using improvement procedure
        current_solution = impr_proc.improveSolution(current_solution)
        
        # Update incumbent solution
        incumbent_solution = update_incumbent(current_solution, 
                                              incumbent_solution)[0]
        
        # Print execution
        execution_time = clock() - start_time
        output = '{0} -> Pre-improve cost: {1} \t Current cost: {2} \t Current fleet size: {3} \t Incumbent cost: {4} \t Execution time (sec): {5}'.format(i, cost_pre_improvement, current_solution['TotalCost'], current_solution['nVehicles'], incumbent_solution['TotalCost'], round(execution_time, 2))
        print(output)
    
    clear_improvement_setup(impr_proc)
    
    return incumbent_solution
