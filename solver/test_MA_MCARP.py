'''
Created on 27 May 2015

@author: eliaswillemse
'''
import cPickle
import os
import sysPath
import sys
import cProfile

sys = sysPath.addInputPaths(sys)
mainPath = sysPath.returnPath()

import py_return_problem_data
from MA_MCARP import MemeticCARP

OUTPUTFOLDERFILE = mainPath + '/Metaheuristics/MAstd_run1/run1.csv'

if not os.path.isfile(OUTPUTFOLDERFILE):
    f = open(OUTPUTFOLDERFILE, 'w')
    f.write('Set,Name,TimeInc,TimeTotal,Z,K\n')
    f.close()

problemSet = 'Lpr'
problemName = 'Lpr-a-03'
problem = problemName + '_problem_info.dat' 
info = py_return_problem_data.return_problem_data(problemSet, problem)
nn_list = py_return_problem_data.return_nearest_neighbour_data(problemSet, problem)
MAt = MemeticCARP(info, problemSet, problemName, tabu = False)
MAt.setMA_BelenguerParameters()
#MAt.setTwoSolutionCrossParameters()
#MAt.setLocalSearch(nnList = nn_list, NN=0.1)
MAt.setQuickLocalSearch(nnList = nn_list, NN=0.1)
#MAt._tLimit = 60
#MAt.runTwoSolutionCross()
cProfile.run('MAt.runMA(); print', sort=1)
raise NameError
completeSolution = MAt.runMA()

#f = open(OUTPUTFOLDERFILE, 'a')
t1 = MAt._incTime
t2 = MAt._time
Z = completeSolution['TotalCost']
K = completeSolution['nVehicles']
#f.write('%s,%s,%.4f,%.4f,%i,%i,\n'%(problemSet,problemName,t1,t2,Z,K))
#f.close()
print(completeSolution['TotalCost'],completeSolution['nVehicles'])
print(MAt._incTime)
print(MAt._time)