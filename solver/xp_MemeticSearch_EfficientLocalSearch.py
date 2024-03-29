'''
Created on 30 Jun 2015

@author: eliaswillemse
'''
'''
Created on 04 Jun 2015

@author: eliaswillemse

MemeticSearcg_EfficientLocalSearch_2Jul2015

(2) Memetic Algorithm

Version 2: Standard MA embedded with the most efficient performing local search heuristic, ignoring Nearest Neighbour (set = 1).

Tests:

Module: MA_MCARP.py
Initial Solution factors = {M, EPS, PS, U}                ( 1 =  1x1) --- All are used
Nearest Neighbours (NN) factors = {1}                     ( 1 =  1x1 = 1)
Candidate list = {TRUE}                                   ( 1 =  1x1 = 1)
Compound move = {TRUE}                                    ( 1 =  1x1 = 1 per problem)    
Set = {Act (3), mval (34), Lpr (15), Cen-Part (5)}        (57 =  1x57 = 57 runs)

Output format:

Set,Problem,Initial,NN,CanList,CompoundMove,Z_Init,Z_final,Time\n

Output folder: ExperimentOutput/
Output file: Experiments_LocalSearch_FindBest_20Jun2015.csv
'''

import cPickle
import os
import sysPath
import sys
import cProfile
import time

sys = sysPath.addInputPaths(sys)
mainPath = sysPath.returnPath()

import py_return_problem_data

import MA_MCARP

SOLUTIONS_FOLDER = mainPath + '/LS_InputData/IntitialSolutions/'
OUTPUT_FOLDER = 'ExperimentOutput/'
OUTPUT_FILE = 'Experiments_MemeticSearch_EfficientLocalSearch_72H_2Jul2015.csv'
OUTPUT_FILE_PATH = OUTPUT_FOLDER + OUTPUT_FILE
OUTPUT_HEADING = 'Set,Problem,Metaheuristic,Version,NN,Z_final,Time,Iterations,IncIteration\n'

if not os.path.isfile(OUTPUT_FILE_PATH):
    outFile = open(OUTPUT_FILE_PATH, 'w')
    outFile.write(OUTPUT_HEADING)
    outFile.close()
    
def runExperiments(problemSet, testSetup, specifics = None):
    
    problems = py_return_problem_data.return_problem_data_list(problem_set = problemSet)
    problems.sort()
    if specifics != None:
        prob = []
        for i in specifics:
            prob.append(problems[i])
        problems = prob
        
    for problem in problems:

        print('Load problem info')
        t = time.clock()
        info = py_return_problem_data.return_problem_data(problemSet, problem)
        nn_list = py_return_problem_data.return_nearest_neighbour_data(problemSet, problem)
        print('Loading time: %.4f'%(time.clock() - t))

        for nnFrac in testSetup['nnFracs']:
            MAt = MA_MCARP.MemeticCARP(info, problemSet, info.name)
            MAt.setMA_BelenguerParameters()
            MAt.setLocalSearch(nnList = nn_list, NN=nnFrac, testAll=False)
            MAt._tLimit = 72*3600
            solution = MAt.runMA()
            l = MAt.returnStats(solution, version = 'EfficientLocalSearch')
            outFile = open(OUTPUT_FILE_PATH, 'a')
            outFile.write(l)
            outFile.close()
                        
def exp1():
    problemSet = 'Act'
    testSetup = {'nnFracs' : [1]}
    runExperiments(problemSet, testSetup)
    
def exp2():
    problemSet = 'mval'
    testSetup = {'nnFracs' : [1]}
    runExperiments(problemSet, testSetup)

def exp3a3():
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    specifics = [2]
    runExperiments(problemSet, testSetup, specifics)

def exp3b3():
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    specifics = [7]
    runExperiments(problemSet, testSetup, specifics)

def exp3c3():
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    specifics = [12]
    runExperiments(problemSet, testSetup, specifics)

def exp3a4():
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    specifics = [3]
    runExperiments(problemSet, testSetup, specifics)

def exp3b4():
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    specifics = [8]
    runExperiments(problemSet, testSetup, specifics)

def exp3c4():
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    specifics = [13]
    runExperiments(problemSet, testSetup, specifics)

def exp3a5():
    specifics = [4]
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    runExperiments(problemSet, testSetup, specifics)

def exp3b5():
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    specifics = [9]
    runExperiments(problemSet, testSetup, specifics)

def exp3c5():
    problemSet = 'Lpr'
    testSetup = {'nnFracs' : [1]}
    specifics = [14]
    runExperiments(problemSet, testSetup, specifics)

def exp4a():
    problemSet = 'Cen-Part'
    testSetup = {'nnFracs' : [1]}
    specifics = [0]
    runExperiments(problemSet, testSetup, specifics)
    
def exp4b1():
    problemSet = 'Cen-Part'
    testSetup = {'nnFracs' : [1]}
    specifics = [1]
    runExperiments(problemSet, testSetup, specifics)
    
def exp4b2():
    problemSet = 'Cen-Part'
    testSetup = {'nnFracs' : [1]}
    specifics = [2]
    runExperiments(problemSet, testSetup, specifics)
    
def exp4c1():
    problemSet = 'Cen-Part'
    testSetup = {'nnFracs' : [1]}
    specifics = [3]
    runExperiments(problemSet, testSetup, specifics)
    
def exp4c2():
    problemSet = 'Cen-Part'
    testSetup = {'nnFracs' : [1]}
    specifics = [4]
    runExperiments(problemSet, testSetup, specifics)