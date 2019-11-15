# -*- coding: utf-8 -*-
"""
pytest for converter.py

History:
    Created on 14 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""
import pandas as pd
import os
import pytest
from converter.load_data import load_instance
from solver.solve import gen_solution
from solver.solve import initiate_tabu_search
from solver.solve import clear_improvement_setup
from solver.solve import improve_solution
from solver.solve import solve_instance
from solver.solve import solve_store_instance


def test_gen_initial_solution():
    info = load_instance('test_data/Lpr_IF-c-03.txt')
    solution = gen_solution(info)
    assert solution['TotalCost'] == 114908
    assert solution['nVehicles'] == 4
    assert solution[0]['Cost'] == 28770
    assert solution[1]['Cost'] == 28773
    assert solution[2]['Cost'] == 28798
    assert solution[3]['Cost'] == 28567


def test_initiate_tabu_search():
    info = load_instance('test_data/Lpr_IF-c-03.txt')
    improver = initiate_tabu_search(info)
    clear_improvement_setup(improver)


def test_improve_solution_ts():
    info = load_instance('test_data/Lpr_IF-c-03.txt')
    initial_solution = gen_solution(info)
    solution = improve_solution(info, initial_solution, improvement='TS')
    assert solution['TotalCost'] == 111921
    assert solution['nVehicles'] == 4
    assert solution[0]['Cost'] == 27697
    assert solution[1]['Cost'] == 28443
    assert solution[2]['Cost'] == 28018
    assert solution[3]['Cost'] == 27763


def test_improve_solution_ls():
    info = load_instance('test_data/Lpr_IF-c-03.txt')
    initial_solution = gen_solution(info)
    solution = improve_solution(info, initial_solution, improvement='LS')
    assert solution['TotalCost'] == 112977.0
    assert solution['nVehicles'] == 4
    assert solution[0]['Cost'] == 27492
    assert solution[1]['Cost'] == 28344
    assert solution[2]['Cost'] == 28433
    assert solution[3]['Cost'] == 28708


def test_solver_initial():
    solution = solve_instance('test_data/Lpr_IF-c-03.txt')
    assert solution['TotalCost'] == 114908
    assert solution['nVehicles'] == 4
    assert solution[0]['Cost'] == 28770
    assert solution[1]['Cost'] == 28773
    assert solution[2]['Cost'] == 28798
    assert solution[3]['Cost'] == 28567


def test_solve_store_instance():
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_ps.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_ps.csv')
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_full_ps.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_full_ps.csv')

    solve_store_instance('test_data/Lpr_IF-c-03.txt')
    solution_csv = pd.read_csv('test_data/Lpr_IF-c-03_sol_ps.csv')
    solution_csv_full = pd.read_csv('test_data/Lpr_IF-c-03_sol_full_ps.csv')

    test_instance = pd.read_csv('../test_data/Lpr_IF-c-03_sol_ps.csv')
    test_instance_full = pd.read_csv('../test_data/Lpr_IF-c-03_sol_full_ps.csv')

    pd.testing.assert_frame_equal(solution_csv, test_instance)
    pd.testing.assert_frame_equal(solution_csv_full, test_instance_full)

    if os.path.isfile('test_data/Lpr_IF-c-03_sol_ps.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_ps.csv')
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_full_ps.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_full_ps.csv')


def test_solve_store_instance_ls():
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_ps_local_search.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_ps_local_search.csv')
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_full_ps_local_search.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_full_ps_local_search.csv')

    solve_store_instance('test_data/Lpr_IF-c-03.txt', improve='LS')
    solution_csv = pd.read_csv('test_data/Lpr_IF-c-03_sol_ps_local_search.csv')
    solution_csv_full = pd.read_csv('test_data/Lpr_IF-c-03_sol_full_ps_local_search.csv')

    test_instance = pd.read_csv('../test_data/Lpr_IF-c-03_sol_ps_local_search.csv')
    test_instance_full = pd.read_csv('../test_data/Lpr_IF-c-03_sol_full_ps_local_search.csv')

    pd.testing.assert_frame_equal(solution_csv, test_instance)
    pd.testing.assert_frame_equal(solution_csv_full, test_instance_full)

    if os.path.isfile('test_data/Lpr_IF-c-03_sol_ps_local_search.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_ps_local_search.csv')
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_full_ps_local_search.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_full_ps_local_search.csv')


def test_solve_store_instance_ls():
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_ps_tabu_search.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_ps_tabu_search.csv')
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_full_ps_tabu_search.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_full_ps_tabu_search.csv')

    solve_store_instance('test_data/Lpr_IF-c-03.txt', improve='TS')
    solution_csv = pd.read_csv('test_data/Lpr_IF-c-03_sol_ps_tabu_search.csv')
    solution_csv_full = pd.read_csv('test_data/Lpr_IF-c-03_sol_full_ps_tabu_search.csv')

    test_instance = pd.read_csv('../test_data/Lpr_IF-c-03_sol_ps_tabu_search.csv')
    test_instance_full = pd.read_csv('../test_data/Lpr_IF-c-03_sol_full_ps_tabu_search.csv')

    pd.testing.assert_frame_equal(solution_csv, test_instance)
    pd.testing.assert_frame_equal(solution_csv_full, test_instance_full)

    if os.path.isfile('test_data/Lpr_IF-c-03_sol_ps_tabu_search.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_ps_tabu_search.csv')
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_full_ps_tabu_search.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_full_ps_tabu_search.csv')


def test_solve_store_new_path():
    if os.path.isfile('test_data/tmp/Lpr_IF-c-03_sol_ps.csv'):
        os.remove('test_data/tmp/Lpr_IF-c-03_sol_ps.csv')
    if os.path.isfile('tmp/Lpr_IF-c-03_sol_full_ps.csv'):
        os.remove('test_data/tmp/Lpr_IF-c-03_sol_full_ps.csv')

    solve_store_instance('test_data/Lpr_IF-c-03.txt', out_path='test_data/tmp/')
    solution_csv = pd.read_csv('test_data/tmp/Lpr_IF-c-03_sol_ps.csv')
    solution_csv_full = pd.read_csv('test_data/tmp/Lpr_IF-c-03_sol_full_ps.csv')

    test_instance = pd.read_csv('../test_data/Lpr_IF-c-03_sol_ps.csv')
    test_instance_full = pd.read_csv('../test_data/Lpr_IF-c-03_sol_full_ps.csv')

    pd.testing.assert_frame_equal(solution_csv, test_instance)
    pd.testing.assert_frame_equal(solution_csv_full, test_instance_full)

    if os.path.isfile('test_data/tmp/Lpr_IF-c-03_sol_ps.csv'):
        os.remove('test_data/tmp/Lpr_IF-c-03_sol_ps.csv')
    if os.path.isfile('tmp/Lpr_IF-c-03_sol_full_ps.csv'):
        os.remove('test_data/tmp/Lpr_IF-c-03_sol_full_ps.csv')


def test_solve_store_new_path():
    if os.path.isfile('test_data/tmp/Lpr_IF-c-03_sol_ps.csv'):
        os.remove('test_data/tmp/Lpr_IF-c-03_sol_ps.csv')
    if os.path.isfile('tmp/Lpr_IF-c-03_sol_full_ps.csv'):
        os.remove('test_data/tmp/Lpr_IF-c-03_sol_full_ps.csv')

    solve_store_instance('test_data/Lpr_IF-c-03.txt',
                         out_path='test_data/tmp/', full_output=False)
    solution_csv = pd.read_csv('test_data/tmp/Lpr_IF-c-03_sol_ps.csv')
    solution_csv_full = pd.read_csv('test_data/tmp/Lpr_IF-c-03_sol_full_ps.csv')

    test_instance = pd.read_csv('../test_data/Lpr_IF-c-03_sol_ps.csv')

    assert os.path.isfile('tmp/Lpr_IF-c-03_sol_full_ps.csv') is False

    if os.path.isfile('test_data/tmp/Lpr_IF-c-03_sol_ps.csv'):
        os.remove('test_data/tmp/Lpr_IF-c-03_sol_ps.csv')
    if os.path.isfile('tmp/Lpr_IF-c-03_sol_full_ps.csv'):
        os.remove('test_data/tmp/Lpr_IF-c-03_sol_full_ps.csv')


def test_solve_store_no_overwrite():
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_ps.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_ps.csv')
    if os.path.isfile('test_data/Lpr_IF-c-03_sol_full_ps.csv'):
        os.remove('test_data/Lpr_IF-c-03_sol_full_ps.csv')

    with pytest.raises(FileExistsError):
        solve_store_instance('test_data/Lpr_IF-c-03.txt',
                             out_path='../test_data/',
                             overwrite=False)
