# -*- coding: utf-8 -*-
"""
pytest for `solution_to_csv.py`

History:
    Created on 23 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import pytest
import os
import pandas as pd
from converter.load_data import load_instance
from solver.solve import solve_instance
from converter.solution_converter import convert_df
from converter.solution_converter import write_solution_df
from converter.solution_converter import convert_df_full


def test_convert_pd():
    info = load_instance('test_data/Lpr_IF-c-03.txt')
    solution = solve_instance('test_data/Lpr_IF-c-03.txt', improve=False)
    solution_df = convert_df(info, solution)

    df_test = pd.read_csv('../test_data/Lpr_IF-c-03_ps.csv')
    pd.testing.assert_frame_equal(solution_df, df_test)
    same = solution_df.equals(df_test)
    assert same is True


def test_store_solution_df():
    info = load_instance('test_data/Lpr_IF-c-03.txt')
    solution = solve_instance('test_data/Lpr_IF-c-03.txt', improve=False)
    solution_df = convert_df(info, solution)
    with pytest.raises(FileExistsError):
        write_solution_df(solution_df, 'tempfile.txt')

    if os.path.isfile('tempfile2.txt'):
        os.remove('tempfile2.txt')
    write_solution_df(solution_df, 'tempfile2.txt')

    assert os.path.isfile('tempfile2.txt') is True
    os.remove('tempfile2.txt')


def test_store_solution_content():
    info = load_instance('test_data/Lpr_IF-c-03.txt')
    solution = solve_instance('test_data/Lpr_IF-c-03.txt', improve=False)
    solution_df = convert_df(info, solution)

    if os.path.isfile('tempfile2.txt'):
        os.remove('tempfile2.txt')
    write_solution_df(solution_df, 'tempfile2.txt')

    solution_df2 = pd.read_csv('tempfile2.txt')

    os.remove('tempfile2.txt')

    df_test = pd.read_csv('../test_data/Lpr_IF-c-03_ps.csv')
    pd.testing.assert_frame_equal(solution_df2, df_test)
    same = solution_df2.equals(df_test)

    assert same is True


def test_convert_df_full():
    info = load_instance('test_data/Lpr_IF-c-03.txt')
    solution = solve_instance('test_data/Lpr_IF-c-03.txt', improve=False)
    solution_df = convert_df(info, solution)
    df_full = convert_df_full(info, solution_df)
    df_test = pd.read_csv('../test_data/Lpr_IF-c-03_ps_full.csv')
    pd.testing.assert_frame_equal(df_full, df_test)
    same = df_full.equals(df_test)
    assert same is True




