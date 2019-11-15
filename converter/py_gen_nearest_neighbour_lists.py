'''
Created on Nov 4, 2013

@author: ejwillemse
'''
import numpy as np
import pyximport
pyximport.install(setup_args={"include_dirs":np.get_include()})

import converter.py_return_problem_data as py_return_problem_data
from converter.py_return_problem_data  import return_problem_data
from converter.py_return_problem_data  import return_problem_data_list
from converter.py_return_problem_data  import return_path

import pickle

import os

def return_nn_lists(d):
    nArcs = len(d)
    nearest_neighbour_list = np.zeros((nArcs, nArcs), dtype="int")
    for i in range(nArcs):
        nearest_neighbour_list[i, :] = np.argsort(d[i][:])
    nearest_neighbour_list = nearest_neighbour_list.tolist()
    return nearest_neighbour_list

def execute(prob_set):
    output_path = return_path() + prob_set + '/' + 'nearest_neighbour_list/'
    if not os.path.isdir(output_path):os.mkdir(output_path)
    problem_names = return_problem_data_list(prob_set)
    for name in problem_names:
        info = return_problem_data(prob_set, name)
        nArcs = len(info.d)#.shape[0]
        nearest_neighbour_list = np.zeros((nArcs,nArcs),dtype="int")
        for i in range(nArcs): nearest_neighbour_list[i,:] = np.argsort(info.d[i][:])
        nearest_neighbour_list = nearest_neighbour_list.tolist()
        outputfile = output_path + info.name + '_nn_list.dat'
        fileopen = open(outputfile,'wb')
        pickle.dump(nearest_neighbour_list, fileopen)
        fileopen.close()     

if __name__ == "__main__":
    
    problem_sets = ['bccm','gdb', 'bmcv','eglese','egl-large']#['Lpr','bccm', 'mval', 'gdb', 'bmcv','eglese','egl-large','Act','Cen']#

    #problem_sets = []
    
    for problem_set in problem_sets:
        execute(problem_set)