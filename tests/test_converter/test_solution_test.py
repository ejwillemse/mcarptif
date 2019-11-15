# -*- coding: utf-8 -*-
"""
pytest for `solution_tester.py`

History:
    Created on 13 April 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""
import pytest
import pandas as pd
from converter.solution_tester import load_solution_file
from converter.solution_tester import consecutive_connected
from converter.solution_tester import start_end_depot


def test_load_solution_input_files_mismatch():
    with pytest.raises(AttributeError):
        load_solution_file('test_data/Lpr_IF-c-02.txt',
                           '../test_data/Lpr_IF-c-03_sol_full_ps.csv')


def test_load_solution_files_info_not_found():
    with pytest.raises(FileNotFoundError):
        load_solution_file('not_exist/Lpr_IF-c-03.txt',
                           '../test_data/Lpr_IF-c-03_sol_full_ps.csv')


def test_load_solution_files_solution_not_found():
    with pytest.raises(FileNotFoundError):
        load_solution_file('test_data/Lpr_IF-c-03.txt',
                           'not_exist/Lpr_IF-c-03_sol_ps.csv')


def test_load_solution_file_inconsistent_heading_error():
    with pytest.raises(AttributeError):
        load_solution_file('test_data/Lpr_IF-c-03.txt',
                           '../test_data/Lpr_IF-c-03_sol_ps.csv')


def test_load_solution_file():
    (info, full_df) = load_solution_file('../test_data/Lpr_IF-c-03.txt',
                                         '../test_data/Lpr_IF-c-03_sol_full_ps.csv')


def test_disconnected_path_error():
    sol = pd.read_csv('../test_data/Lpr_IF-c-03_sol_full_ps.csv')
    sol = sol.drop(10)
    sol = sol.drop(1)

    with pytest.raises(AttributeError):
        error = consecutive_connected(sol, True)


def test_start_end_depot():
    (info, sol) = load_solution_file('../test_data/Lpr_IF-c-03.txt',
                                     '../test_data/Lpr_IF-c-03_sol_full_ps.csv')

    n_arcs = len(sol)
    sol = sol.drop(n_arcs - 1)
    sol = sol.drop(0)

    with pytest.raises(AttributeError):
        errors = start_end_depot(info, sol, True)
