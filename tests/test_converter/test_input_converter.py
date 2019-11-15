# -*- coding: utf-8 -*-
"""
pytest for converter.py

History:
    Created on 14 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""
import pytest
import os
from converter.input_converter import Converter
from converter.input_converter import InstanceInfo


class TestConverter(object):

    def test_converter_initialisation_no_file_folder(self):
        """Error is raised when no file or folder is specified"""
        conv = Converter()
        with pytest.raises(AttributeError):
            conv._check_basic_inputs()

    def test_converter_file_and_folder_set(self):
        """Error is raised when a file and folder is specified"""
        conv = Converter(instance_path='non_existing_file.txt',
                        instance_folder='non_existing_folder/')
        with pytest.raises(AttributeError):
            conv._check_basic_inputs()

    def test_converter_input_file_not_found(self):
        """Error is raised when input file does not exist"""

        conv = Converter(instance_path='non_existing_file.txt')
        with pytest.raises(FileNotFoundError):
            conv._check_basic_inputs()

    def test_converter_input_folder_not_found(self):
        """Error is raised when input folder does not exist"""
        conv = Converter(instance_folder='non_existing_folder/')
        with pytest.raises(NotADirectoryError):
            conv._check_basic_inputs()

        conv = Converter(instance_folder='')
        with pytest.raises(NotADirectoryError):
            conv._check_basic_inputs()

    def test_file_found_and_set(self):
        """Test that an existing file is found and set as input path"""
        conv = Converter(instance_path='tempdir/tempfile.txt')
        assert conv._instance_path == 'tempdir/tempfile.txt'

        conv = Converter(instance_path='tempfile.txt')
        assert conv._instance_path == 'tempfile.txt'

    def test_input_folder_found_and_set(self):
        """Test that an existing file is found and set as input path"""
        conv = Converter(instance_folder='tempdir/')
        assert conv._instance_folder == 'tempdir/'

        # Corner cases
        conv = Converter(instance_folder='tempdir')
        assert conv._instance_folder == 'tempdir'

        conv = Converter(instance_folder='/')
        assert conv._instance_folder == '/'

    def test_output_folder_not_found(self):
        """Test that the specified output folder was not found"""
        conv = Converter(instance_folder='tempdir/',
                      output_folder='non_existing_folder/')
        with pytest.raises(NotADirectoryError):
            conv._check_basic_inputs()

        conv = Converter(instance_folder='tempdir/', output_folder='')
        with pytest.raises(NotADirectoryError):
            conv._check_basic_inputs()

    def test_output_folder_found_and_set(self):
        conv = Converter(instance_folder='tempdir/', output_folder='tempdir/')
        assert conv._output_folder == 'tempdir/'

        # Corner cases
        conv = Converter(instance_folder='tempdir/', output_folder='tempdir')
        assert conv._output_folder == 'tempdir'

        conv = Converter(instance_folder='tempdir/', output_folder='/')
        assert conv._output_folder == '/'

    def test_input_folder_and_output_name_key_given(self):
        """Test that the outfile_key is not specified when an input folder
        is used."""

        conv = Converter(instance_folder='tempdir/', outfile_key='test')
        with pytest.raises(AttributeError):
            conv._check_basic_inputs()

    def test_output_folder_set_based_on_input_folder(self):
        """Test that the output folder is correctly set, based on input
        options"""

        conv = Converter(instance_path='tempdir/tempfile.txt')
        conv._set_output_folder()
        assert conv._output_folder == '/'

        conv = Converter(instance_path='tempdir/tempfile.txt',
                         out_to_in=True)
        conv._set_output_folder()
        assert conv._output_folder == 'tempdir/'

        conv = Converter(instance_path='tempdir/tempdir2/tempfile.txt',
                         out_to_in=True)
        conv._set_output_folder()
        assert conv._output_folder == 'tempdir/tempdir2/'

        conv = Converter(instance_path='tempfile.txt', out_to_in=True)
        conv._set_output_folder()
        assert conv._output_folder == '/'

        conv = Converter(instance_folder='tempdir/', out_to_in=True)
        conv._set_output_folder()
        assert conv._output_folder == 'tempdir/'

        conv = Converter(instance_folder='/', out_to_in=True)
        conv._set_output_folder()
        assert conv._output_folder == '/'

    def test_pad_folder(self):
        conv = Converter(instance_folder='tempdir',
                         output_folder='tempdir/tempdir2')
        conv._set_output_folder()
        conv._pad_folders()

        assert conv._instance_folder == 'tempdir/'
        assert conv._output_folder == 'tempdir/tempdir2/'

        # Corner cases

        conv = Converter(instance_folder='tempdir')
        conv._set_output_folder()
        conv._pad_folders()
        assert conv._output_folder == '/'

    def test_extract_key(self):
        conv = Converter(instance_path='tempdir/tempfile.txt')
        conv._extract_key()
        assert conv._outfile_key == 'tempfile'

        # Corner cases

        conv = Converter(instance_path='tempdir/tempfile.tempfile.txt')
        conv._extract_key()
        assert conv._outfile_key == 'tempfile.tempfile'

    def test_check_output_files_exist(self):

        conv = Converter(instance_path='tempdir/tempfile.txt', out_to_in=True)
        conv._set_output_folder()
        conv._pad_folders()
        conv._extract_key()
        with pytest.raises(FileExistsError):
            conv._check_output_files_exist()

        conv = Converter(instance_path='tempdir/tempfile.txt', out_to_in=True,
                         overwrite=True)
        conv._set_output_folder()
        conv._pad_folders()
        conv._extract_key()
        conv._check_output_files_exist()

        conv = Converter(instance_path='tempdir/tempfile.txt',
                         output_folder='tempdir/tempdir2',
                         overwrite=False)
        conv._set_output_folder()
        conv._pad_folders()
        conv._extract_key()
        with pytest.raises(FileExistsError):
            conv._check_output_files_exist()

        conv = Converter(instance_path='tempdir/tempfile.txt', out_to_in=True,
                         outfile_key='keytest')
        conv._set_output_folder()
        conv._pad_folders()
        with pytest.raises(FileExistsError):
            conv._check_output_files_exist()

    def test_input_files_in_directory(self):
        """Test whether all files in a directory are correctly tested."""
        conv = Converter(instance_folder='tempdir/tempdir3/', out_to_in=True)
        conv._set_output_folder()
        conv._pad_folders()
        conv._ignores['extension'].append('dat')
        with pytest.raises(FileExistsError):
            conv._check_all_files_in_directory()

        conv = Converter(instance_folder='tempdir/tempdir4/')
        conv._set_output_folder()
        conv._pad_folders()
        with pytest.raises(FileNotFoundError):
            conv._check_all_files_in_directory()

    def test_convert_intances(self):
        """Test whether input data is correctly converted and stored"""
        conv = Converter(instance_path='tempdir/Lpr_IF-b-02.txt',
                         out_to_in=True)

        if os.path.isfile('tempdir/Lpr_IF-b-02_info_lists_pickled.dat'):
            os.remove('tempdir/Lpr_IF-b-02_info_lists_pickled.dat')
        if os.path.isfile('tempdir/Lpr_IF-b-02_sp_data_full.dat'):
            os.remove('tempdir/Lpr_IF-b-02_sp_data_full.dat')
        if os.path.isfile('tempdir/Lpr_IF-b-02_problem_info.dat'):
            os.remove('tempdir/Lpr_IF-b-02_problem_info.dat')
        if os.path.isfile('tempdir/Lpr_IF-b-02_nn_list.dat'):
            os.remove('tempdir/Lpr_IF-b-02_nn_list.dat')

        conv.convert_instance()

        assert os.path.isfile('tempdir/Lpr_IF-b-02_info_lists_pickled.dat') \
               is True
        assert os.path.isfile('tempdir/Lpr_IF-b-02_sp_data_full.dat') is True
        assert os.path.isfile('tempdir/Lpr_IF-b-02_problem_info.dat') is True
        assert os.path.isfile('tempdir/Lpr_IF-b-02_nn_list.dat') is True

        os.remove('tempdir/Lpr_IF-b-02_info_lists_pickled.dat')
        os.remove('tempdir/Lpr_IF-b-02_sp_data_full.dat')
        os.remove('tempdir/Lpr_IF-b-02_problem_info.dat')
        os.remove('tempdir/Lpr_IF-b-02_nn_list.dat')

    def test_convert_multiple_instance(self):
        """Test whether multiple instances are read and their output correctly
        captured."""

        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_info_lists_pickled.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_info_lists_pickled.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_sp_data_full.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_sp_data_full.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_problem_info.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_problem_info.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_nn_list.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_nn_list.dat')

        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_info_lists_pickled.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_info_lists_pickled.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_sp_data_full.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_sp_data_full.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_problem_info.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_problem_info.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_nn_list.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_nn_list.dat')

        conv = Converter(instance_folder='tempdir/lpr_if_in',
                         out_to_in=True)

        conv.convert_multiple_instances()

        assert os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_info_lists_pickled.dat') \
               is True
        assert os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_sp_data_full.dat') is True
        assert os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_problem_info.dat') is True
        assert os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_nn_list.dat') is True

        assert os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_info_lists_pickled.dat') \
               is True
        assert os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_sp_data_full.dat') is True
        assert os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_problem_info.dat') is True
        assert os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_nn_list.dat') is True

        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_info_lists_pickled.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_info_lists_pickled.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_sp_data_full.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_sp_data_full.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_problem_info.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_problem_info.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_nn_list.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_nn_list.dat')

        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_info_lists_pickled.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_info_lists_pickled.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_sp_data_full.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_sp_data_full.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_problem_info.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_problem_info.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_nn_list.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_nn_list.dat')

        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_info_lists_pickled.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_info_lists_pickled.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_sp_data_full.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_sp_data_full.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_problem_info.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_problem_info.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-01_nn_list.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-01_nn_list.dat')

        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_info_lists_pickled.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_info_lists_pickled.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_sp_data_full.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_sp_data_full.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_problem_info.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_problem_info.dat')
        if os.path.isfile('tempdir/lpr_if_in/Lpr_IF-c-03_nn_list.dat'):
            os.remove('tempdir/lpr_if_in/Lpr_IF-c-03_nn_list.dat')

        conv = Converter(instance_folder='tempdir/lpr_if_in',
                         output_folder='tempdir')

        conv.convert_multiple_instances()

        assert os.path.isfile('tempdir/Lpr_IF-c-01_info_lists_pickled.dat') \
               is True
        assert os.path.isfile('tempdir/Lpr_IF-c-01_sp_data_full.dat') is True
        assert os.path.isfile('tempdir/Lpr_IF-c-01_problem_info.dat') is True
        assert os.path.isfile('tempdir/Lpr_IF-c-01_nn_list.dat') is True

        assert os.path.isfile('tempdir/Lpr_IF-c-03_info_lists_pickled.dat') \
               is True
        assert os.path.isfile('tempdir/Lpr_IF-c-03_sp_data_full.dat') is True
        assert os.path.isfile('tempdir/Lpr_IF-c-03_problem_info.dat') is True
        assert os.path.isfile('tempdir/Lpr_IF-c-03_nn_list.dat') is True

        if os.path.isfile('tempdir/Lpr_IF-c-01_info_lists_pickled.dat'):
            os.remove('tempdir/Lpr_IF-c-01_info_lists_pickled.dat')
        if os.path.isfile('tempdir/Lpr_IF-c-01_sp_data_full.dat'):
            os.remove('tempdir/Lpr_IF-c-01_sp_data_full.dat')
        if os.path.isfile('tempdir/Lpr_IF-c-01_problem_info.dat'):
            os.remove('tempdir/Lpr_IF-c-01_problem_info.dat')
        if os.path.isfile('tempdir/Lpr_IF-c-01_nn_list.dat'):
            os.remove('tempdir/Lpr_IF-c-01_nn_list.dat')

        if os.path.isfile('tempdir/Lpr_IF-c-03_info_lists_pickled.dat'):
            os.remove('tempdir/Lpr_IF-c-03_info_lists_pickled.dat')
        if os.path.isfile('tempdir/Lpr_IF-c-03_sp_data_full.dat'):
            os.remove('tempdir/Lpr_IF-c-03_sp_data_full.dat')
        if os.path.isfile('tempdir/Lpr_IF-c-03_problem_info.dat'):
            os.remove('tempdir/Lpr_IF-c-03_problem_info.dat')
        if os.path.isfile('tempdir/Lpr_IF-c-03_nn_list.dat'):
            os.remove('tempdir/Lpr_IF-c-03_nn_list.dat')


class TestInstanceInfo(object):

    def test_input_not_found_error(self):
        instance = InstanceInfo(instance_folder='non_existing_folder/',
                                instance_name='test')

        with pytest.raises(NotADirectoryError):
            instance._check_instance_locations()

        instance = InstanceInfo(instance_folder='tempdir/tempdir4/',
                                instance_name='test')

        with pytest.raises(FileNotFoundError):
            instance._check_instance_locations()

    def test_set_instance_lists(self):

        instance = InstanceInfo(instance_folder='tempdir/lpr_if_test',
                                instance_name='Lpr_IF-c-01')

        instance._check_instance_locations()
        instance.set_instance_lists()

        assert instance.name == 'Lpr_IF-c-01'
        assert instance.reqArcsPure == [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

    def test_set_required_arc_instance_info(self):

        instance = InstanceInfo(instance_folder='tempdir/lpr_if_test',
                                instance_name='Lpr_IF-c-01')

        instance._check_instance_locations()
        instance.set_required_arc_instance_info()

        assert instance.d_np_req[4][2] == 133

    def test_set_nn_list(self):
        instance = InstanceInfo(instance_folder='tempdir/lpr_if_test',
                                instance_name='Lpr_IF-c-01')

        instance._check_instance_locations()
        instance.set_nn_lists()
        assert instance.nn_list[0][:10] == [0, 16, 14, 34, 32, 17, 20, 18, 15,
                                            46]

    def test_sp_lists(self):
        instance = InstanceInfo(instance_folder='tempdir/lpr_if_test',
                                instance_name='Lpr_IF-c-01')

        instance._check_instance_locations()
        instance.set_sp_lists()

        assert instance.d_full[12][23] == 71
        assert instance.p_full[12][23] == 39
