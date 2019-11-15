# -*- coding: utf-8 -*-
"""Unit test for `ruin_recreate.py`.

    
History:
    Created on 22 Sep 2017
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import sys
sys.path.append('../Input_TestData/')

import unittest
import random

import ruin_recreate as rr

from copy import deepcopy
import py_return_problem_data


class RemoveArcsTests(unittest.TestCase):
    """Tests for the `ruin_recreate.py` function. Tests if arcs are correctly
    removed from a solution"""
    
    def setUp(self):
        """Fixture that creates a solution for `RemoveArcsTests` to use."""
        self.solution = [[[0,3,4,6,8,1],
                          [1,10,11,13,14,16,2],
                          [2,18,19,20,22,1,0]]
                         ,]
        
        self.solutionMCARP = [[[0,3,4,6,8,0], [0,10,11,13,14,16,0],
                               [0,18,19,20,22,0,None]],]
                
        self.inv_arcs = [0,1,2,None,5,4,7,6,9,8,None,12,11,None,15,14,17,16,
                         None,None,None,22,21,]
    
        self.solution_arcs = [3,4,6,8,10,11,13,14,16,18,19,20,22]    

        
    def test_arc_position_correct(self):
        "Check that `return_arc_position` returns the correct position of arc."
        self.assertEqual(rr.return_arc_position(self.solution,11), (0,1,2))

    def test_arc_inv_position_correct(self):
        """Check that `return_arc_position` returns the correct position of an
        with its inverse in the solution."""
        self.assertEqual(rr.return_arc_position(self.solution,12,11), (0,1,2))

    def test_arc_position_not_found_exception(self):
        """Check that `ValeuError` is raised if an arc is not found. Either
        the solution is incomplete, inverse arcs are not correctly specified, or
        a dummy arc is being removed"""
        with self.assertRaises(ValueError):
            rr.return_arc_position(self.solution, 24)

    def test_arc_position_not_found_exception_for_MCARP(self):
        """Check that `ValeuError` is raised if an arc is not found. Either
        the solution is incomplete, inverse arcs are not correctly specified, or
        a dummy arc is being removed"""
        with self.assertRaises(ValueError):
            rr.return_arc_position(self.solutionMCARP, 24)

    def test_all_arcs_positions_correct(self):
        """Check that `find_arcs` returns the correct positions of a list of
        arcs"""
        remove = [3,8,19,]
        expected_positions = [(0,0,1), (0,0,4), (0,2,2),]
        self.assertEqual(rr.find_arcs(self.solution,remove,self.inv_arcs), 
                         expected_positions)

    def test_all_arcs_witn_inv_positions_correct(self):
        """Check that `find_arcs` returns the correct positions of a list of
        arcs, including inverse arcs"""
        remove = [3,5,21]
        expected_positions = [(0,0,1), (0,0,2), (0,2,4)]
        self.assertEqual(rr.find_arcs(self.solution,remove,self.inv_arcs), 
                         expected_positions)


    def test_remove_arcs_correct(self):
        """Check that `remove_arcs` returns a solution with the correct arcs
        removed and that the original solution has not changed."""
        old_solution = deepcopy(self.solution)
        remove = [3,5,21]
        expected_solution = [[[0,6,8,1],[1,10,11,13,14,16,2],[2,18,19,20,1,0]],]
        self.assertEqual(rr.remove_arcs(self.solution, remove, self.inv_arcs), 
                         expected_solution)
        
        self.assertEqual(old_solution, self.solution)
        
        
    def test_remove_random_arcs_correct(self):
        """Check that `remove_rabdom_arcs` returns a solution with the correct 
        randomly selected arcs removed and that the original solution has not 
        changed."""
        
        setSeed = 1
        random.seed(setSeed)
        
        remove = random.sample(self.solution_arcs, 3) # If the seed is fixed at 
        # 1, the arcs to be removed should be [4, 19, 16]

        #  seeds work differently across python versions
        if sys.version_info.major == 2:
            expected_solution = [4, 19, 16]
        else:
            expected_solution = [6, 18, 4]
        self.assertEqual(rr.random_remove_arcs(self.solution, 3,  
                                            randomSeed=setSeed), 
                         expected_solution)
 
        
    def test_remove_pure_random_arcs_correct(self):
        """Check that `remove_rabdom_arcs` returns a solution with the correct 
        random number of randomly selected arcs are removed and that the 
        original solution has not changed."""
        
        setSeed = 5
        random.seed(setSeed)
        nArcs = random.randint(1, len(self.solution_arcs) - 1) # If the seed 
        # is fixed at 5, nArcs = 8
        random.seed(setSeed)
        remove = random.sample(self.solution_arcs, nArcs) # If the seed is fixed 
        # at 5, the arcs to be removed should be [16, 22, 20, 18, 13, 14, 3, 6]

        #  seeds work differently across python versions
        if sys.version_info.major == 2:
            expected_solution = [16, 22, 20, 18, 13, 14, 3, 6]
        else:
            expected_solution = [18, 10, 11, 16, 3, 14, 13, 4, 22, 19]
        self.assertEqual(rr.random_remove_arcs(self.solution,
                                            randomSeed=setSeed), 
                         expected_solution)
        

class ResinsertArcsMCARPTIFTests(unittest.TestCase):
    """Tests for the `ruin_recreate.py` function. Tests if removed arcs are 
    correctly re-inserted into a solution for the MCARPTIF."""
    
    def setUp(self):
        """Fixture that creates a solution for `ReinsertArcsTests` to use."""
        problem_set = 'Lpr_IF'
        filename = 'Lpr_IF-c-01_problem_info.dat'
        
        self.instance_info = py_return_problem_data.return_problem_data(
                            problem_set, filename, print_path=False)
        
        self.nn_list = py_return_problem_data.return_nearest_neighbour_data(
                            problem_set, filename)
        
        # Generate a solution to play with for Lpr_IF_c-01.
        self.solution_full = {0: {
            'Load': 16662, 'TripLoads': [10000, 6662], 
            'Service': 17797, 'Deadhead': 1040.0, 'TripServices': [10745, 7052], 
            'Cost': 18837.0, 'TripDeadheads': [479.0, 561.0], 
            'TripCosts': [11224.0, 7613.0], 'nTrips': 2, 
            'Trips': [[0, 16, 34, 48, 66, 86, 71, 8, 7, 51, 47, 32, 21, 15, 18, 
                       22, 24, 28, 39, 3, 26, 30, 43, 44, 61, 57, 53, 4, 36, 54, 
                       9, 58, 1], 
                      [1, 41, 5, 69, 75, 10, 12, 72, 78, 89, 13, 11, 83, 77, 90, 
                       85, 81, 63, 64, 6, 1, 0]]
                             }, 
            'TotalCost': 18837.0, 'nVehicles': 1, 'ProblemType': 'CLARPIF'}
        
        self.solution = [[[0, 16, 34, 48, 66, 86, 71, 8, 7, 51, 47, 32, 21, 
            15, 18, 22, 24, 28, 39, 3, 26, 30, 43, 44, 61, 57, 53, 4, 36, 54, 9, 
            58, 1], [1, 41, 5, 69, 75, 10, 12, 72, 78, 89, 13, 11, 83, 77, 90, 
            85, 81, 63, 64, 6, 1, 0]]]
        

    def tearDown(self):
        """Fixture that removes temporary variables once testing is 
            completed.""" 
            
        pass
    
    
    def test_MCAPRTIF_full_solution_decoded_correctly(self):
        """Check that `decode_MCARPTIF_solution` returns the correctly decoded
        full MCARPTIF solution."""

        self.assertEqual(rr.decode_MCARPTIF_solution(self.solution_full), 
                         self.solution)
        

    def test_construct_route_of_removed_arcs(self):
        """Check that a new solution is created using the removed arcs and that 
        the reqArcList and reqInvArcList info did not change."""
        
        original_reqArcList = deepcopy(self.instance_info.reqArcList)
        original_reqInvArcList = deepcopy(self.instance_info.reqInvArcList)
        
        removalArcs = [22, 30, 43, 89, 10]
        expected_solution = [[[0, 22, 30, 43, 10, 89, 1, 0]]]
        
        self.assertEqual(rr.construct_routes(removalArcs,
            self.instance_info), expected_solution)
        
        self.assertEqual(original_reqArcList, self.instance_info.reqArcList)
        self.assertEqual(original_reqInvArcList, 
                         self.instance_info.reqInvArcList)
        
        
    def test_de_re_construct_solution_of_removed_arcs(self):
        """Check that a solution is updated by removing arcs to create a 
        a new solution, which is added to the existing one, and that the 
        original solution did not change."""
        
        oldSolution = deepcopy(self.solution)
        removalArcs = [22, 30, 43, 89, 10]
        expected_solution = [
        [[0, 16, 34, 48, 66, 86, 71, 8, 7, 51, 47, 32, 21, 
                    15, 18, 24, 28, 39, 3, 26, 44, 61, 57, 53, 4, 36, 54, 9, 
                    58, 1], [1, 41, 5, 69, 75, 12, 72, 78, 13, 11, 83, 77, 90, 
                    85, 81, 63, 64, 6, 1, 0]], 
        [[0, 22, 30, 43, 10, 89, 1, 0]]
        ]
        self.assertEqual(rr.dec_construct_reconstruct_routes(self.solution,
            removalArcs, self.instance_info), expected_solution)
        
        self.assertEqual(oldSolution, self.solution)     


    def test_de_re_construct_solution_of_removed_inv_arcs(self):
        """Check that a solution is updated by removing some inversed arcs to 
        create a new solution, which is added to the existing one, and that the 
        original solution did not change."""
        
        oldSolution = deepcopy(self.solution)
        removalArcs = [22, 31, 42, 88, 10]
        expected_solution = [
        [[0, 16, 34, 48, 66, 86, 71, 8, 7, 51, 47, 32, 21, 
                    15, 18, 24, 28, 39, 3, 26, 44, 61, 57, 53, 4, 36, 54, 9, 
                    58, 1], [1, 41, 5, 69, 75, 12, 72, 78, 13, 11, 83, 77, 90, 
                    85, 81, 63, 64, 6, 1, 0]], 
        [[0, 22, 42, 31, 10, 88, 1, 0]]
        ]
        self.assertEqual(rr.dec_construct_reconstruct_routes(self.solution,
            removalArcs, self.instance_info), expected_solution) 
        
        self.assertEqual(oldSolution, self.solution)


    def test_MCARPTIF_LS_initiator_runs(self):
        """Check that LS is initialized and destroyed correctly"""
        
        LS = rr.initiate_improvement_setup_MCARPTIF(self.instance_info, 
            self.nn_list, improvement_procedure = 'LS')
        rr.clear_improvement_setup(LS)
        
        
    def test_MCARPTIF_LS_improvement_procedure_runs(self):
        """Check that LS improves a solution correctly"""
        
        LS = rr.initiate_improvement_setup_MCARPTIF(self.instance_info, 
            self.nn_list, improvement_procedure = 'LS')
        local_optimum = LS.improveSolution(self.solution_full)

        rr.clear_improvement_setup(LS)
        

class ResinsertArcsMCARPTests(unittest.TestCase):
    """Tests for the `ruin_recreate.py` function. Tests if removed arcs are 
    correctly re-inserted into a solution for the MCARP."""
    

    def setUp(self):
        """Fixture that creates a solution for `ReinsertArcsTests` to use."""
        problem_set = 'Lpr'
        filename = 'Lpr-c-01_problem_info.dat'
        
        self.instance_info = py_return_problem_data.return_problem_data(
                            problem_set, filename, print_path=False)
        
        self.nn_list = py_return_problem_data.return_nearest_neighbour_data(
                            problem_set, filename)
        
        # Generate a solution to play with for Lpr-c-01.
        self.solution_full = {
            0: {'Load': 9953, 'Deadhead': 464, 
            'Route': [0, 12, 18, 34, 48, 66, 8, 86, 88, 83, 63, 60, 78, 43, 29, 
            25, 26, 40, 59, 4, 37, 38, 54, 56, 74, 80, 77, 72, 9, 11, 69, 0], 
            'Cost': 11032, 'Service': 10568}, 
            1: {'Load': 6709, 'Deadhead': 608, 
            'Route': [0, 14, 30, 16, 20, 22, 1, 45, 46, 5, 6, 64, 84, 10, 70, 3, 
                      7, 51, 52, 2, 32, 0], 
            'Cost': 7837, 'Service': 7229}, 
                              'TotalCost': 18869, 'ProblemType': 'CARP', 
                              'nVehicles': 2}
        
        self.solution = [
        [0, 12, 18, 34, 48, 66, 8, 86, 88, 83, 63, 60, 78, 43, 29, 25, 26, 40, 
         59, 4, 37, 38, 54, 56, 74, 80, 77, 72, 9, 11, 69, 0],
        [0, 14, 30, 16, 20, 22, 1, 45, 46, 5, 6, 64, 84, 10, 70, 3, 7, 51, 52, 
         2, 32, 0],]
        
        self.solution_MCARPTIF = [
        [[0, 12, 18, 34, 48, 66, 8, 86, 88, 83, 63, 60, 78, 43, 29, 25, 26, 40, 
         59, 4, 37, 38, 54, 56, 74, 80, 77, 72, 9, 11, 69, 0],
        [0, 14, 30, 16, 20, 22, 1, 45, 46, 5, 6, 64, 84, 10, 70, 3, 7, 51, 52, 
         2, 32, 0, 0]],]


    def tearDown(self):
        """Fixture that removes temporary variables once testing is 
            completed.""" 
            
        pass
    
    
    def test_MCARP_solution_encoded_correctly(self):
        """Test that the MCARP solution is coded correctly into an MCARPTIF
        solution and that the original solution is unchanged."""
        
        oldSolution = deepcopy(self.solution)
        
        self.assertEqual(rr.encode_MCARP_solution(self.solution), 
                                                  self.solution_MCARPTIF)
        
        self.assertEqual(oldSolution, self.solution)


    def test_MCARPTIF_solution_reverted_correctly_to_MCARP(self):
        """Test that the MCARPTIF solution is reverted correctly into an 
        MCARPTIF solution and that the original solution is unchanged."""
        
        oldSolution = deepcopy(self.solution_MCARPTIF)
        
        self.assertEqual(rr.revert_MCARP_solution(self.solution_MCARPTIF), 
                                                  self.solution)
        
        self.assertEqual(oldSolution, self.solution_MCARPTIF)


    def test_MCAPRT_full_solution_decoded_correctly(self):
        """Check that `decode_MCARP_solution` returns the correctly decoded
        full MCARPTIF solution."""

        self.assertEqual(rr.decode_MCARP_solution(self.solution_full), 
                         self.solution_MCARPTIF)
        

    def test_construct_route_of_removed_arcs(self):
        """Check that a new solution is created using the removed arcs and that 
        the reqArcList and reqInvArcList info did not change."""
        
        original_reqArcList = deepcopy(self.instance_info.reqArcList)
        original_reqInvArcList = deepcopy(self.instance_info.reqInvArcList)
        
        removalArcs = [22, 30, 43, 10]
        expected_solution = [[[0, 30, 22, 43, 10, 0, 0]]]
        
        self.assertEqual(rr.construct_routes(removalArcs,
            self.instance_info, problemType='MCARP'), expected_solution)
        
        self.assertEqual(original_reqArcList, self.instance_info.reqArcList)
        self.assertEqual(original_reqInvArcList, 
                         self.instance_info.reqInvArcList)
        

    def test_de_re_construct_solution_of_removed_arcs(self):
        """Check that a solution is updated by removing arcs to create a 
        a new solution, which is added to the existing one, and that the 
        original solution did not change."""
        
        oldSolution = deepcopy(self.solution_MCARPTIF)
        removalArcs = [22, 30, 43, 10]
        expected_solution = [
        [[0, 12, 18, 34, 48, 66, 8, 86, 88, 83, 63, 60, 78, 29, 25, 26, 40, 
         59, 4, 37, 38, 54, 56, 74, 80, 77, 72, 9, 11, 69, 0],
        [0, 14, 16, 20, 1, 45, 46, 5, 6, 64, 84, 70, 3, 7, 51, 52, 
         2, 32, 0],[0, 30, 22, 43, 10, 0, 0]],]
        self.assertEqual(rr.dec_construct_reconstruct_routes(
            self.solution_MCARPTIF, removalArcs, self.instance_info, 
            problemType='MCARP'), expected_solution)
        
        self.assertEqual(oldSolution, self.solution_MCARPTIF)


    def test_initial_solution_constructor(self):
        """Check that a feasible initial solution is generated for the MCARP."""
        
        solution = rr.create_initial_solution(self.instance_info, 
                                              problemType='MCARP')
        
        self.assertEqual(solution, self.solution_full)

    
    def test_MCARP_LS_initiator_runs(self):
        """Check that LS is initialized and destroyed correctly"""
        
        LS = rr.initiate_improvement_setup_MCARP(self.instance_info, 
            self.nn_list, improvement_procedure = 'LS')
        rr.clear_improvement_setup(LS)
        
        
    def test_MCARP_LS_improvement_procedure_runs(self):
        """Check that LS improves a solution correctly"""
        
        LS = rr.initiate_improvement_setup_MCARP(self.instance_info, 
            self.nn_list, improvement_procedure = 'LS')
        local_optimum = LS.improveSolution(self.solution_full)
        
        rr.clear_improvement_setup(LS)
        

    def test_MCARP_TS_initiator_runs(self):
        """Check that TS is initialized and destroyed correctly"""
        
        TS = rr.initiate_improvement_setup_MCARP(self.instance_info, 
            self.nn_list, improvement_procedure = 'TS')
        rr.clear_improvement_setup(TS)
        
        
    def test_MCARP_TS_improvement_procedure_runs(self):
        """Check that TS improves a solution correctly"""
        
        TS = rr.initiate_improvement_setup_MCARP(self.instance_info, 
            self.nn_list, improvement_procedure = 'TS')
        local_optimum = TS.improveSolution(self.solution_full)
        
        rr.clear_improvement_setup(TS)


def test_ruin_recreate_random_MCARP_runs():
    """Check that MCARP random runs correctly"""
    
    problem_set = 'Lpr'
    filename = 'Lpr-c-04_problem_info.dat'
    
    instance_info = py_return_problem_data.return_problem_data(
                        problem_set, filename, print_path=False)
    
    nn_list = py_return_problem_data.return_nearest_neighbour_data(
                        problem_set, filename)
    
    local_optimum = rr.ruin_recreate_random_MCARP(instance_info, 
        nn_list, improvement_procedure='TS', randomSeed = 1)


def test_ruin_recreate_random_MCARPTIF_runs():
    """Check that MCARPTIF random runs correctly"""
    
    problem_set = 'Lpr_IF'
    filename = 'Lpr_IF-c-03_problem_info.dat'
    
    instance_info = py_return_problem_data.return_problem_data(
                        problem_set, filename, print_path=False)
    
    nn_list = py_return_problem_data.return_nearest_neighbour_data(
                        problem_set, filename)
    
    local_optimum = rr.ruin_recreate_random_MCARPTIF(instance_info, 
        nn_list, improvement_procedure='TS', randomSeed = 1)
    

if __name__ == '__main__':
    unittest.main()
    test_ruin_recreate_random_MCARP_runs()
    test_ruin_recreate_random_MCARPTIF_runs()