# -*- coding: utf-8 -*-
"""Unit test for `generate_agents.py`.
    
History:
    Created on 26 Feb 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import sys
import unittest
import pandas as pd
from pprint import pprint

sys.path.append('../MCARPTIF_solvers/Input_TestData/')
sys.path.append('../MCARPTIF_solvers/MS/')
import py_return_problem_data #  read problem info
import generate_agents
import test_generate_agents_input as gen_input


class CreateInitialSolutionTests(unittest.TestCase):
    """Tests if a solution is correctly generated"""

    def setUp(self):
        """Fixture that creates a solution to use."""
        problem_set = 'Lpr_IF'
        self.instance = 'Lpr_IF-c-02'
        filename = self.instance + '_problem_info.dat'
        
        self.instance_info = py_return_problem_data.return_problem_data(
            problem_set, filename,
            problem_path='../MCARPTIF_solvers/Input_TestData/Input_data/',
            print_path=False)
        
        self.nn_list = py_return_problem_data.return_nearest_neighbour_data(
                        problem_set, filename,
            problem_path='../MCARPTIF_solvers/Input_TestData/Input_data/')
        
        # Generate a solution test with.
        self.solution_full = gen_input.return_solution_full(self.instance)
        
        self.solution_csv_path = 'test_input/test_' + self.instance + \
                                 '_tabu_improved_decoded.csv'
        
        with open(self.solution_csv_path, 'r') as f:
            self.solution_csv = ''.join(f.readlines())

        self.agents = gen_input.return_agents(self.instance)
        self.agents_added = gen_input.return_added_agents(self.instance)
        self.agents_removed = gen_input.return_removed_agents(self.instance)

    def test_generate_solution(self):
        """Check that a solution is correctly generated and returned."""
        solution = generate_agents.generate_solution(self.instance_info,
                                                     self.nn_list)

        self.assertEqual(solution, self.solution_full)
    
    def test_encode_solution_csv(self):
        """Check that a solution is correctly encoded into a csv format."""
        solution_csv = generate_agents.encode_solution_csv(
                                            self.instance_info, 
                                            self.solution_full)
        self.assertEqual(solution_csv, self.solution_csv)
        
    def test_encode_solution_df(self):
        """Check that a solution is correctly decoded into a pandas dataframe"""
        solution_df = pd.read_csv(self.solution_csv_path)
        solution_df_gen = generate_agents.encode_solution_df(self.solution_csv)
        same_df = solution_df.equals(solution_df_gen)
        self.assertTrue(same_df)

    def test_create_agents(self):
        """Check that agents are correctly created from solution dataframe"""
        solution_df = pd.read_csv(self.solution_csv_path)
        generate_agents.create_agents(solution_df)

    def test_initialise_agents(self):
        """Check that agents are correctly initialised"""
        agents = generate_agents.initialise_agents(self.instance_info,
                                                   self.nn_list)
        print(agents)
        print(self.agents)
        for agent_key in agents:
            self.assertIn(agent_key, self.agents.keys())
            agents_test_for = agents[agent_key]
            agents_test_against = self.agents[agent_key]
            same_df = agents_test_for.equals(agents_test_against)
            self.assertTrue(same_df)

    def test_add_agent(self):
        """Check that agent is added correctly"""
        agents = self.agents.copy()
        new_agent = agents[0]
        agents = generate_agents.add_agent(agents, new_agent)

        for agent_key in agents:
            self.assertIn(agent_key, self.agents_added.keys())
            same_df = agents[agent_key].equals(self.agents_added[agent_key])
            self.assertTrue(same_df)

    def test_remove_agent(self):
        """Check that agent is removed correctly"""
        agents = self.agents.copy()
        agents = generate_agents.remove_agent(agents, agent_key=0)

        for agent_key in agents:
            self.assertIn(agent_key, self.agents_removed.keys())
            same_df = agents[agent_key].equals(self.agents_removed[agent_key])
            self.assertTrue(same_df)


def test_larger_instances():
    """Tests on larger instances, not formally part of the unit testing"""

    problem_set = 'Lpr_IF'
    filename = 'Lpr_IF-c-05_problem_info.dat'

    instance_info = py_return_problem_data.return_problem_data(problem_set,
                                                               filename,
                                                               print_path=False)

    nn_list = py_return_problem_data.return_nearest_neighbour_data(problem_set,
                                                                   filename)

    solution = generate_agents.generate_solution(instance_info, nn_list)

    solution_csv = generate_agents.encode_solution_csv(instance_info,
                                                         solution)

    with open('test_Lpr_IF-c-03_tabu_improved_decoded.csv', 'w') as f:
        f.write(solution_csv)

    solution_df = generate_agents.encode_solution_df(solution_csv)

    print(solution_df)

    agents = generate_agents.create_agents(solution_df)

    for i in agents:
        print(agents[i])


if __name__ == '__main__':
    unittest.main()
    #  test_larger_instances()
