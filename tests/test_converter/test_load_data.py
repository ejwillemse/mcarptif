# -*- coding: utf-8 -*-
"""
pytest for load_data.py

History:
    Created on 23 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import pytest
import os
from converter.load_data import ConvertedInputs
from converter.load_data import load_instance


class TestConvertedInputs(object):

    def test_extract_folder(self):
        file_path = 'folder1/folder2/test.txt'
        conv_inputs = ConvertedInputs(file_path)
        folder_path = conv_inputs.extract_folder()
        assert folder_path == 'folder1/folder2/'

        file_path = 'test.txt'
        conv_inputs = ConvertedInputs(file_path)
        folder_path = conv_inputs.extract_folder()
        assert folder_path == '/'

    def test_extract_striped_filename(self):
        file_path = 'folder1/folder2/test.txt'
        conv_inputs = ConvertedInputs(file_path)
        file_name = conv_inputs.extract_striped_filename()
        assert file_name == 'test'

        file_path = 'test.txt'
        conv_inputs = ConvertedInputs(file_path)
        file_name = conv_inputs.extract_striped_filename()
        assert file_name == 'test'

        file_path = 'test.test.txt'
        conv_inputs = ConvertedInputs(file_path)
        file_name = conv_inputs.extract_striped_filename()
        assert file_name == 'test.test'

    def test_check_converted_input_exists(self):
        file_path = 'tempdir/lpr_if_in/Lpr_IF-c-01.txt'
        conv_inputs = ConvertedInputs(file_path)
        exists = conv_inputs.check_converted_input_exists()
        assert exists is False

        file_path = 'tempdir/lpr_if_test/Lpr_IF-c-01.txt'
        conv_inputs = ConvertedInputs(file_path)
        exists = conv_inputs.check_converted_input_exists()
        assert exists is True

        file_path = 'tempdir/lpr_if_in_partial/Lpr_IF-c-01.txt'
        conv_inputs = ConvertedInputs(file_path)
        with pytest.raises(FileNotFoundError):
            exists = conv_inputs.check_converted_input_exists()

    def test_converted_input(self):
        file_path = 'tempdir/lpr_if_in/test.txt'
        part = 'tempdir/lpr_if_in/test'
        with open(part + '_info_lists_pickled.dat', 'wb'):
            pass
        with open(part + '_nn_list.dat', 'wb'):
            pass
        with open(part + '_problem_info.dat', 'wb'):
            pass
        with open(part + '_sp_data_full.dat', 'wb'):
            pass
        conv_inputs = ConvertedInputs(file_path)
        conv_inputs.remove_converted_input()

        assert os.path.isfile(part + '_info_lists_pickled.dat') is False
        assert os.path.isfile(part + '_nn_list.dat') is False
        assert os.path.isfile(part + '_problem_info.dat') is False
        assert os.path.isfile(part + '_sp_data_full.dat') is False


class TestLoadInstance():

    def test_file_not_found(self):
        with pytest.raises(s):
            load_instance('check_file.txt')

    def test_file_converted_removed(self):
        load_instance('tempdir/lpr_if_in/Lpr_IF-c-01.txt', cache=False)
        part = 'tempdir/lpr_if_in/Lpr_IF-c-01'
        assert os.path.isfile(part + '_info_lists_pickled.dat') is False
        assert os.path.isfile(part + '_nn_list.dat') is False
        assert os.path.isfile(part + '_problem_info.dat') is False
        assert os.path.isfile(part + '_sp_data_full.dat') is False

    def test_instance_info_return(self):
        info = load_instance('tempdir/lpr_if_in/Lpr_IF-c-01.txt', cache=False)
        assert info.name == 'Lpr_IF-c-01'
        assert info.capacity == 10000
        assert info.maxTrip == 28800
        assert info.dumpCost == 300
        assert info.reqArcList == [0, 1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                                   15, 16, 17, 18, 19, 20,
            21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
            38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
            55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
            72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
            89, 90, 91, 92, 93]
        assert info.reqArcListActual == [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                                         14, 15, 16, 17, 18, 19, 20,
            21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
            38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
            55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
            72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
            89, 90, 91]
        assert info.depotnewkey == 0
        assert info.IFarcsnewkey == [1, 2]
        assert info.ACarcsnewkey == []
        assert info.reqEdgesPure == [14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34,
                                     36, 38, 40, 42, 44, 46,
            48, 50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80,
            82, 84, 86, 88, 90]
        assert info.reqInvArcList[20] == 21
        assert info.reqInvArcList[5] is None
        assert info.serveCostL[5] == 427
        assert info.demandL[5] == 399
        assert info.d[5][8] == 19
        assert info.if_cost_np[5][8] == 355
        assert info.if_arc_np[5][8] == 1
        assert info.nn_list[5][:10] == [69, 74, 55, 5, 72, 9, 10, 88, 13, 12]
        assert info.reqArcs_map[5] == 5
        assert info.allIndexD[5] == (9, 4)
        assert len(info.reqArcs_map) == 92
        assert len(info.d_full) == 94
        assert info.travelCostL[5] == 22
        assert info.d_full[5][93] == 113
        assert info.p_full[5][93] == 86