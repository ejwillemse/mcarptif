'''
Created on 14 Jul 2015

@author: ejwillemse
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

def addInfo(solution, info):

    for i in range(solution['nVehicles']):
        if 'Service' not in solution[i]:
            solution[i]['Service'] = sum([info.serveCostL[arc] for arc in solution[i]['Route']])
        if 'Deadhead' not in solution[i]:
            solution[i]['Deadhead'] = solution[i]['Cost'] - solution[i]['Service']
    return(solution)

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
        print('Loading time: %.4f'%(time.clock() - t))

        MAt = MA_MCARP.MemeticCARP(info, problemSet, info.name)
        MAt._nc = testSetup['nSolutions']
        population = MAt._generateRandomdPopulation()
        for i, s in enumerate(population):
            solution = addInfo(s[2], info)
            outFileName = problemSet + '_' + info.name + '_random' + str(i) + '.dat'
            outfile = open(SOLUTIONS_FOLDER + outFileName, 'w')
            cPickle.dump(solution, outfile)
            outfile.close()
        MAt._freeC()

                        
def exp1():
    problemSet = 'Act'
    testSetup = {'nSolutions' : 4}
    runExperiments(problemSet, testSetup)
    
def exp2():
    problemSet = 'mval'
    testSetup = {'nSolutions' : 4}
    runExperiments(problemSet, testSetup)
    
def exp3():
    problemSet = 'Lpr'
    testSetup = {'nSolutions' : 4}
    runExperiments(problemSet, testSetup)
    
def exp4():
    problemSet = 'Cen-Part'
    testSetup = {'nSolutions' : 4}
    runExperiments(problemSet, testSetup)
    
exp2()
exp4()