"""
Tests for network_prep.py
"""

import pytest
import pandas as pd
import numpy as np
import os
from converter import load_instance
from pandas._testing import array_equivalent
from converter.network_prep import key_columns_not_exists
from converter.network_prep import key_columns_exists
from converter.network_prep import return_successor_arcs_indices
from converter.network_prep import Network
from converter.import_Belenguer_format import convert_file
from converter.network_prep import ShortestPath


def gen_test_network():
    u = [1, 2, 3, 4, 5, 6]
    v = [2, 3, 4, 5, 6, 7]
    cost = [1] * len(v)
    df_test = pd.DataFrame({'arc_u': u, 'arc_v': v, 'arc_cost': cost})
    return df_test.copy()


def gen_success_test_network():
    u = [1, 2, 2, 2, 3, 3]
    v = [2, 3, 4, 5, 1, 2]
    success_array = np.array([[1, 2, 3],
                             [4, 5],
                             [],
                             [],
                             [0],
                             [1, 2, 3]])

    success_array = np.array([np.array(x) for x in success_array])
    cost = [1] * len(v)
    df_test = pd.DataFrame({'arc_u': u, 'arc_v': v, 'arc_cost': cost})
    return df_test.copy(), success_array.copy()


def test_key_columns():
    df_test = gen_test_network()
    with pytest.raises(AttributeError):
        key_columns_exists(df_test, [['random1', 'random2']])


def test_key_columns_in():
    df_test = gen_test_network()
    with pytest.raises(AttributeError):
        key_columns_not_exists(df_test, [['arc_u', 'arc_v']])


def test_network_start_column_error():
    df_test = gen_test_network()
    df_test = df_test[['arc_u']]
    with pytest.raises(AttributeError):
        network = Network(df_test)


def test_network_key_column_error():
    df_test = gen_test_network()
    network = Network(df_test, calc_successor=False)
    assert df_test.equals(network.network_df)
    assert df_test.values.base is not network.network_df.values.base

    df_test['arc_pair_test'] = ['1-2', '2-3', '3-4', '4-5', '5-6', '6-7']
    assert np.array_equal(network.arc_u, df_test['arc_u'].values)
    assert np.array_equal(network.arc_v, df_test['arc_v'].values)
    assert np.array_equal(network.arc_cost, df_test['arc_cost'].values)
    assert np.array_equal(network.arc_index, df_test.index)
    assert np.array_equal(network.arc_pair, df_test['arc_pair_test'].values)
    assert network.arc_successor_index_list is None


def test_return_successor_arcs():
    df_test, success_array_test = gen_success_test_network()
    u = df_test['arc_u']
    v = df_test['arc_v']
    success_arcs_index = return_successor_arcs_indices(u, v)
    for i, index_array in enumerate(success_arcs_index):
        assert np.array_equal(success_arcs_index[i], success_array_test[i])


def test_successor_list_prepare_network():
    df_test, success_array_test = gen_success_test_network()
    network = Network(df_test)
    network.generate_successor_list()
    for i, index_array in enumerate(network.arc_successor_index_list):
        assert np.array_equal(index_array, success_array_test[i])


def test_update_network():
    df_test, _ = gen_success_test_network()
    df_test['arc_index'] = 0
    network = Network(df_test, calc_successor=False)
    network.generate_successor_list()

    with pytest.raises(AttributeError):
        network.update_network_df()

    df_test, _ = gen_success_test_network()
    network = Network(df_test, calc_successor=False)

    with pytest.raises(AttributeError):
        network.update_network_df()

    network = Network(df_test)
    network.update_network_df()
    assert np.array_equal(network.network_df['arc_index'].values, network.arc_index)
    for i, index_array in enumerate(network.network_df[
                                        'arc_successor_index_list']):
        assert np.array_equal(index_array, network.arc_successor_index_list[i])


def test_compare_against_belenguer():
    file = '../../data/Lpr_IF/Lpr_IF-c-05.txt'
    instance_df = convert_file(file)
    instance_df_convert = instance_df[['arc_u', 'arc_v', 'arc_cost']]
    network = Network(instance_df_convert)
    network.update_network_df()
    assert array_equivalent(network.network_df, instance_df[
        ['arc_u', 'arc_v', 'arc_cost', 'arc_index',
         'arc_successor_index_list']])


def test_create_pytable():
    file = '../../data/Lpr_IF/Lpr_IF-c-05.txt'
    instance_df = convert_file(file)
    instance_df_convert = instance_df[['arc_u', 'arc_v', 'arc_cost']]
    network = Network(instance_df_convert, calc_successor=False)

    with pytest.raises(ValueError):
        network.create_pytable('../../data/Lpr_IF/Lpr_IF-c-05.txt')

    with pytest.raises(ValueError):
        network.create_pytable('temp/temp_file.h5')

    network = Network(instance_df_convert)
    network.create_pytable('temp/temp_file.h5')
    os.remove('temp/temp_file.h5')


def test_shortest_paths_pytable_load():
    file = '../../data/Lpr_IF/Lpr_IF-c-05.txt'
    instance_df = convert_file(file)
    instance_df_convert = instance_df[['arc_u', 'arc_v', 'arc_cost']]
    network = Network(instance_df_convert)
    sp_calc = ShortestPath()
    sp_calc.load_from_pytable('temp/Lpr_IF-c-05_fixed_test.h5')

    assert np.array_equal(sp_calc.arc_index, network.arc_index)
    assert np.array_equal(sp_calc.arc_u, network.arc_u)
    assert np.array_equal(sp_calc.arc_v, network.arc_v)
    assert np.array_equal(sp_calc.arc_cost, network.arc_cost)
    assert np.array_equal(sp_calc.arc_pair, network.arc_pair)

def test_shortest_paths_network_load():
    file = '../../data/Lpr_IF/Lpr_IF-c-05.txt'
    instance_df = convert_file(file)
    instance_df_convert = instance_df[['arc_u', 'arc_v', 'arc_cost']]
    network = Network(instance_df_convert)
    sp_calc = ShortestPath()
    sp_calc.load_from_network(network)

    assert np.array_equal(sp_calc.arc_index, network.arc_index)
    assert np.array_equal(sp_calc.arc_u, network.arc_u)
    assert np.array_equal(sp_calc.arc_v, network.arc_v)
    assert np.array_equal(sp_calc.arc_cost, network.arc_cost)
    assert np.array_equal(sp_calc.arc_pair, network.arc_pair)


def test_shortest_paths_network_manual_set():
    file = '../../data/Lpr_IF/Lpr_IF-c-05.txt'
    instance_df = convert_file(file)
    instance_df_convert = instance_df[['arc_u', 'arc_v', 'arc_cost']]
    network = Network(instance_df_convert)

    u = instance_df_convert['arc_u'].values
    v = instance_df_convert['arc_v'].values
    cost = instance_df_convert['arc_cost'].values

    sp_calc = ShortestPath()
    sp_calc.set_network(u, v, cost)

    assert np.array_equal(sp_calc.arc_index, network.arc_index)
    assert np.array_equal(sp_calc.arc_u, network.arc_u)
    assert np.array_equal(sp_calc.arc_v, network.arc_v)
    assert np.array_equal(sp_calc.arc_cost, network.arc_cost)
    assert np.array_equal(sp_calc.arc_pair, network.arc_pair)


def test_in_memory_sp_calcs():
    sp_calc = ShortestPath()
    sp_calc.load_from_pytable('temp/Lpr_IF-b-01_fixed_test.h5')
    sp_calc.calc_shortest_path_internal()
    info = load_instance(file_path='temp/Lpr_IF-b-01.txt')
    d_test = np.array(info.d_full)
    assert np.array_equal(d_test, sp_calc.sp_arc_distances)

