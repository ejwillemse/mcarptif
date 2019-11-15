'''
Created on Jan 13, 2012

@author: ewillemse
'''

import os
import converter.py_data_write #From Dev_LancommeARPconversions
from pprint import pprint as pp
import converter.py_gen_nearest_neighbour_lists

raw_input_data_path = 'Raw_input/'
abs_raw_input_path = os.path.abspath(raw_input_data_path) + '/'
output_data_path = 'Input_data/'
if not os.path.isdir(output_data_path):os.mkdir(output_data_path)
abs_output_path = os.path.abspath(output_data_path) + '/'

def write_data_set(data_set = 'Lpr'):
    print('')
    print('Problem set to create %s' %data_set)
    print('')
    
    input_folder = raw_input_data_path + data_set + '/'
    output_folder = output_data_path +  data_set + '/'
    if not os.path.isdir(output_folder):os.mkdir(output_folder)
    
    gen_input_data = py_data_write.WriteAllData(output_folder, input_folder)
    gen_input_data.execute()

def write_multiple_data_sets(problems = ['Lpr']):
    for data_set in problems: write_data_set(data_set)

def return_paths():
    return(abs_raw_input_path)

def write_all_problem_info():
    problem_sets = os.listdir(raw_input_data_path)
    write_multiple_data_sets(problem_sets)

def write_problem_file(problemset, pFile):
    py_data_write.WriteAllData(problemset, pFile)


if __name__ == "__main__":
    problem_sets = ['Lpr_IF']
    write_multiple_data_sets(problem_sets)
    py_gen_nearest_neighbour_lists.execute(problem_sets[0])


