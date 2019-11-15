'''
Created on Jan 13, 2012

@author: ewillemse
'''
import os
import converter.py_data_read as py_data_read # From Dev_LancommeARPconversions
from converter.py_return_raw_data import return_raw_data as rraw
import pickle

def allindices(string, sub, listindex=[], offset=0):
    i = string.find(sub, offset)
    while i >= 0:
        listindex.append(i)
        i = string.find(sub, i + 1)
    return listindex

def return_path():
    current_abs_project_path = os.path.abspath('py_return_problem_data.py')
    path_index = allindices(current_abs_project_path,'/')
    workspace_path = current_abs_project_path[:(path_index[-2]+1)]
    test_data_path = workspace_path + 'Input_TestData/Input_data/'
    return(test_data_path)

def return_raw_path():
    current_abs_project_path = os.path.abspath('py_return_problem_data.py')
    path_index = allindices(current_abs_project_path,'/')
    workspace_path = current_abs_project_path[:(path_index[-2]+1)]
    test_data_path = workspace_path + 'Input_TestData/Raw_input/'
    return(test_data_path)

def return_problem_data(problem_set, filename, problem_path=None, print_path=True):
    if problem_path is None:
        problem_path = return_path() + problem_set + '/problem_info/' + filename
    else:
        problem_path = problem_path + problem_set + '/problem_info/' + filename
    if print_path: print(problem_path)
    return(py_data_read.ReadData(problem_path))

def return_sp_data(problem_set, filename):
    filename = filename[:-16] + 'sp_data_full.dat'
    problem_path = return_path() + problem_set + '/sp_full/' + filename
    return(py_data_read.ReadSPdata(problem_path))

def return_arc_data(problem_set, filename):
    filename = filename[:-16] + 'info_lists_pickled.dat'
    problem_path = return_path() + problem_set + '/info_lists/' + filename
    return(py_data_read.ReadArcConvertLists(problem_path))

def return_problem_data_list(problem_set):
    problem_path = return_path() + problem_set + '/problem_info/'
    inputFiles = os.listdir(problem_path)
    problem_info_list = []
    for file_n in inputFiles: 
        if file_n != '.svn':
            problem_info_list.append(file_n)
    return(problem_info_list)

def return_raw_data(problem_set, file_name):
    problem_path = return_raw_path() + problem_set + '/' + file_name + '.txt'
    return(rraw(problem_path))


def return_nearest_neighbour_data(problem_set, filename, problem_path=None):
    filename = filename[:-16] + 'nn_list.dat'
    if problem_path is None:
        problem_path = return_path() + problem_set + '/nearest_neighbour_list/' + filename
    else:
        problem_path = problem_path + problem_set + '/nearest_neighbour_list/' + filename
    fileOpen = open(problem_path, 'rb')
    data = pickle.load(fileOpen)
    fileOpen.close()
    return(data)

if __name__=="__main__":
    directory = 'Actonville_3Feb2012_presentation'
    filename = 'Actonville_problem_info.dat'
    ab = return_problem_data(directory, filename)
    print(ab.ACarcsnewkey)