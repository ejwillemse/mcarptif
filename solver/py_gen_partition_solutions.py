'''
Created on 17 Jan 2012

@author: elias
'''

import numpy as np
import py_alg_ulusoy_partition as part
from py_return_problem_data  import return_problem_data # From Dev_TestData 
from py_solution_test  import test_solution # From Dev_SolutionOperators
import time
from py_display_solution import display_solution_stats 
from copy import deepcopy
from time import perf_counter as clock
from py_reduce_number_trips import Reduce_Trips 
import py_solution_builders
import evaluatesolutions

def get_edges_arcs(reqArcs, invArcs):
    edge = []
    arc = []
    invArcsTemp = invArcs[:]
    for i in reqArcs:
        if invArcs[i]:
            if invArcsTemp[i]:
                edge.append(i)
                invArcsTemp[invArcs[i]] = None
        else:
            arc.append(i)
    return(edge, arc)  

def genRandomRoute(reqArcs, invArcs):
    
    (edges, arcs) = get_edges_arcs(reqArcs, invArcs)
    
    route = arcs[:]
    
    for i in edges:
        choose = np.random.randint(0,2)
        if choose == 0:route.append(i)
        else: route.append(invArcs[i])
    
    new_route = route[:]
    route_index = np.random.permutation(len(route))
    for k, i in enumerate(route_index):
        new_route[k] = route[i]
    return(new_route)

def gen_random_CARP_solution(info, test = 'True'):
    disp = display_solution_stats(info)
    print('Generate random route')
    random_route = genRandomRoute(info.reqArcListActual, info.reqInvArcList)
    print('Partition random route')
    ulusoy_part = part.Ulusoys(info)
    solution = ulusoy_part.genSolution(random_route)
    disp.display_solution_info(solution)
    if test: 
        test_solution(info, solution)
    return(solution)

def gen_random_CLARPIF_solution(info, test = 'True'):
    disp = display_solution_stats(info)
    print('Generate random route')
    random_route = genRandomRoute(info.reqArcListActual, info.reqInvArcList)
    print('Partition random route')
    ulusoy_part = part.UlusoysIFs(info)
    solution = ulusoy_part.genSolution(random_route)
    disp.display_solution_info(solution)
    if test: 
        test_solution(info, solution)
    return(solution)

def gen_random_CLARPIF_solution_Efficient(info, test=True):
    disp = display_solution_stats(info)
    print('Generate random route')
    random_route = genRandomRoute(info.reqArcListActual, info.reqInvArcList)
    print('Partition random route')
    ulusoy_part = part.UlusoysIFs_efficient(info)
    solution = ulusoy_part.gen_solution(random_route)
    disp.display_solution_info(solution)
    if test: 
        test_solution(info, solution)
    return(solution)
    
class Ulusoy_Partion(object):
    
    def __init__(self, info):
        self.info = info
        self.classic_rules = ['MaxDepo', 'MinDepo', 'MaxYield', 'MinYield']
        self.bestSol = 1e300000
        self.bestSolN = 1e300000
        self.bestSolComp = {}
        self.bestVeh = 1e300000
        self.bestVehN = 1e300000
        self.bestVehN = {}
        self.ulusoy_part = part.Ulusoys(info)
        self.ulusoy_part_CLARPIF = part.UlusoysIFs(info)
        self.ulusoy_part_CLARPIF_efficient = part.UlusoysIFs_efficient(info)
        self.ulusoy_prat_CLARPIF_2 = part.UlusoysIFs_efficient2(info)
        self.adjust_estimate = 0.4
        self.testsolutions = False
        self.disp = display_solution_stats(info)
        self.break_even_point = 1e300000
        self.break_even_iter_limit = 1
        self.problem_type = 'MCARP'
        self.efficient = False
        self.efficient2 = False
        self.Reduce_Trips = Reduce_Trips(info)
        self.reduce_all_trips = True
        #self.reduce_all_trips_v2 = True
        self.reduce_best_trips = False
        self.builder = py_solution_builders.build_solutions(info)
        self.print_iter = 1
        self.write_output = False
        self.file_write = None
        self.nRoutesLB = 0
        self._allSolutions = []
        self._outputStats = []
        self._displaySolution = display_solution_stats(info)
        self._showFinalSolution = True
        
    def resetIncumbent(self):
        self.bestSol = 1e300000
        self.bestSolN = 1e300000
        self.bestSolComp = {}
        self.bestVeh = 1e300000
        self.bestVehN = 1e300000
        self.bestVehComp = {}

    def updateIncumbent(self, solution):
        if solution['TotalCost'] < self.bestSol:
            self.bestSol = solution['TotalCost']
            self.bestSolN = solution['nVehicles']
            self.bestSolComp = deepcopy(solution)
        if solution['nVehicles'] < self.bestVehN:
            self.bestVeh = solution['TotalCost']
            self.bestVehN = solution['nVehicles']
            self.bestVehComp = deepcopy(solution)
        elif (solution['nVehicles'] == self.bestVehN) & (solution['TotalCost'] < self.bestVeh): 
            self.bestVeh = solution['TotalCost']
            self.bestVehN = solution['nVehicles']
            self.bestVehComp = deepcopy(solution)

    def get_edges_arcs(self):
        edge = []
        arc = []
        invArcsTemp = self.info.reqInvArcList[:]
        for i in self.info.reqArcListActual:
            if self.info.reqInvArcList[i]:
                if invArcsTemp[i]:
                    edge.append(i)
                    invArcsTemp[self.info.reqInvArcList[i]] = None
            else:
                arc.append(i)
        return(edge, arc)  
    
    def genRandomRoute(self):
        (edges, arcs) = self.get_edges_arcs()
        route = arcs[:]
        for i in edges:
            choose = np.random.randint(0,2)
            if choose == 0:route.append(i)
            else: route.append(self.info.reqInvArcList[i])
        new_route = route[:]
        route_index = np.random.permutation(len(route))
        for k, i in enumerate(route_index):
            new_route[k] = route[i]
        return(new_route)
    
    def gen_solution(self, route, min_k = True):
        if self.problem_type == 'MCARP':
            solution_min_k = self.ulusoy_part.genSolution(route, min_k = True)
            #solution_min_c = self.ulusoy_part.genSolution(route, min_k = False)
            solution = (solution_min_k, solution_min_k)
            #solution = (solution_min_k, solution_min_c)
        elif self.problem_type == 'CLARPIF':
#             if self.efficient:
#                 print('Efficient 2')
            solution_min_k = self.ulusoy_part_CLARPIF_efficient.gen_solution_efficient(route, min_k = True)
            solution_min_c = self.ulusoy_part_CLARPIF_efficient.gen_solution_efficient(route, min_k = False)
            solution = (solution_min_k, solution_min_c)
            if self.testsolutions:
                self.tester(solution_min_k)
                self.tester(solution_min_c)
#             elif self.efficient2:
#                 print('Efficient 3')
#                 solution = self.ulusoy_prat_CLARPIF_2.gen_solution(route)
#             else: 
#                 print('Efficient 1')
#                 solution = self.ulusoy_part_CLARPIF.genSolution(route)
        return(solution)



    def generate_random_solution(self):
        route = self.genRandomRoute()
        solution = self.gen_solution(route)
        #self.tester(solution)
        return(solution)
   
    def generate_EPS_solution(self, rule = 'MaxDepo'):
        route = self.eps.buildgiantroute(rule)
        solution = self.gen_solution(route)
        #self.tester(solution)
        return(solution)
    
    def split_EPS_solution(self, giantSolution):
        route = giantSolution[0]['Route'][1:-1]
        solution = self.gen_solution(route)
        #self.tester(solution)
        return(solution)        
    
    def EPS_four_rules(self):
        '''
        Use one of four classical EPS rules to break ties.
        '''
        print('EPS Ulusoy - All 4 Rules \n')
        self.resetIncumbent()
        i = -1
        tick = clock()
        for rule in self.classic_rules:
            i += 1
            self.rule = rule
            s = self.generate_EPS_solution(rule)
            if self.reduce_all_trips: s = self.Reduce_Trips.reduce_trip(s)[0]
            print('Rule %s \t Cost %i \t nVehicles %i '%(rule, s['TotalCost'], s['nVehicles']))
            if self.write_output: self.file_write.write('%i,%.4f,%i,%i,\n'%(i,clock() - tick, s['nVehicles'],s['TotalCost']))
            self.updateIncumbent(s)
            
    def EPS_random(self, rule, nSolutions=8):
        '''
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        '''
        solution = []
        print('EPS Ulusoy - Random %s \n' %rule)
        self.resetIncumbent()
        tick = clock()
        for i in range(nSolutions):
            t = clock()
            s = self.generate_EPS_solution(rule)
            if self.reduce_all_trips: 
                if s['nVehicles'] > self.nRoutesLB:
                    s = self.Reduce_Trips.reduce_trip(s)[0]
            if i%self.print_iter == 0: print('S %i \t Cost %i \t nVehicles %i '%(i+1, s['TotalCost'], s['nVehicles']))
            self.updateIncumbent(s)
            solution.append((s['TotalCost'], s['nVehicles'], clock()-t))
            if self.write_output: self.file_write.write('%i,%.4f,%i,%i,\n'%(i,clock() - tick, s['nVehicles'],s['TotalCost']))
        return(self.bestVehComp, self.bestSolComp)
        
    def EPS_random_break_even(self, rule):
        '''
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        '''
        print('EPS Ulusoy - Random %s break even \n' %rule)
        self.resetIncumbent()
        i = 0
        while True:
            i += 1
            s = self.generate_EPS_solution(rule)
            print('S %i  \t Goal %i \t Cost %i \t nVehicles %i '%(i+1, self.break_even_point, s['TotalCost'], s['nVehicles']))
            self.updateIncumbent(s) 
            if self.break_even_iter_limit <= i:break
            if self.bestVehComp['TotalCost'] <= self.break_even_point:break
        return(i)

    def Ulusoy_EPS_solver(self, rule_type, nSolutions=5):
        if rule_type == 'EPS_four_rules':
            self.EPS_four_rules()
        elif rule_type == 'EPS_random_four_rules':
            self.EPS_random(rule = 'RandomRule', nSolutions = nSolutions)
        elif rule_type == 'EPS_random_arc':
            self.EPS_random(rule = 'RandomArc', nSolutions = nSolutions)
        self.tester(self.bestVehComp)
        self.disp.display_solution_info(self.bestVehComp)
        return(self.bestVehComp, self.bestSolComp)

    def Ulusoy_EPS_solver_break_even(self, rule_type):
        if rule_type == 'EPS_random_four_rules':
            nSolutions = self.EPS_random_break_even(rule = 'RandomRule')
        elif rule_type == 'EPS_random_arc':
            nSolutions = self.EPS_random_break_even(rule = 'RandomArc')
        self.tester(self.bestVehComp)
        self.disp.display_solution_info(self.bestVehComp)
        return(self.bestVehComp, nSolutions)

    def Ulusoy_random_route_solver(self, nSolutions=8):
        '''
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        '''
        print('Ulusoy - Random route \n')
        self.resetIncumbent()
        for i in range(nSolutions):
            s = self.generate_random_solution()
            if self.reduce_all_trips: s = self.Reduce_Trips.reduce_trip(s)[0]
            self.updateIncumbent(s)
            print('S %i \t Cost %i \t nVehicles %i '%(i+1, s['TotalCost'], s['nVehicles']))
        self.tester(self.bestVehComp)
        self.builder.display_solution_info(self.bestVehComp)
        py_alg_extended_path_scanning.free_c_local_search()
        return(self.bestVehComp)

    def _printSolutionFinal(self, timeTotal, incumbents, i):
        self._nSolutions = i + 1
        '''
        Print info of incumbent solutions.
        '''        
        if self._showFinalSolution:
            for solution in incumbents:
                self._displaySolution.display_solution_info(solution)
        
        if self._showFinalSolution:
            print('')
            print('Total # iterations: %i'%self._nSolutions)
            print('Total time:         %.2f'%timeTotal)
            print('Time per iteration: %.2f'%(timeTotal/self._nSolutions))
            print('')
            print('Min K - Z: %i'%incumbents[0]['TotalCost'])
            print('        K: %i'%incumbents[0]['nVehicles'])
            print('Min Z - Z: %i'%incumbents[1]['TotalCost'])
            print('        K: %i'%incumbents[1]['nVehicles'])
    
    def ulusoyRandom(self, giantSolutions, outFileName=None):
        '''
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        '''
        solutions = []
        timeStart = time.clock()
        incumbent_solutions = evaluatesolutions.initital_all_incumbents()
        incumbent_solutions_reduce_routes = evaluatesolutions.initital_all_incumbents()
        self._outputStats = []
        if self.reduce_all_trips:
            heading = 'T,Z_z,K_z,Z_k,K_k,RR_Z_z,RR_K_z,RR_Z_k,RR_K_k\n'
        else:
            heading = 'T,Z,K_z,Z_k,K_k\n'
        self._outputStats.append(heading)
        if outFileName: evaluatesolutions._write_output_to_file(outFileName, heading)
        for i, giantSol in enumerate(giantSolutions):
            (s1_k, s1_z) = self.split_EPS_solution(giantSol)
            outline = '%i,%i,%i,%i,%i'%(i,s1_z['TotalCost'],s1_z['nVehicles'],s1_k['TotalCost'],s1_k['nVehicles'])
            incumbent_solutions = evaluatesolutions.update_all_incumbents(s1_z, incumbent_solutions)
            incumbent_solutions = evaluatesolutions.update_all_incumbents(s1_k, incumbent_solutions)
            if (i%self.print_iter) == 0:
                print('S %i RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1, s1_z['TotalCost'], s1_k['nVehicles'], incumbent_solutions[1]['TotalCost'], incumbent_solutions[0]['nVehicles']))
            
            if self.reduce_all_trips: 
                #s2_z = self.Reduce_Trips.reduce_trip(s1_z)[0]
                s2_k = self.Reduce_Trips.reduce_trip(s1_k)[0]
                s2_z = s2_k
                incumbent_solutions_reduce_routes = evaluatesolutions.update_all_incumbents(s2_z, incumbent_solutions_reduce_routes)
                incumbent_solutions_reduce_routes = evaluatesolutions.update_all_incumbents(s2_k, incumbent_solutions_reduce_routes)
                outline += ',%i,%i,%i,%i'%(s2_z['TotalCost'],s2_z['nVehicles'],s2_k['TotalCost'],s2_k['nVehicles'])
                solutions.append(s2_k)
                if (i%self.print_iter) == 0:
                    print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1,  s2_z['TotalCost'], s2_k['nVehicles'], incumbent_solutions_reduce_routes[1]['TotalCost'], incumbent_solutions_reduce_routes[0]['nVehicles']))
                    
            outline += '\n'
            self._outputStats.append(outline)
            if outFileName: evaluatesolutions._write_output_to_file(outFileName, outline)
        timeTotal = time.clock() - timeStart
        #self._printSolutionFinal(timeTotal, incumbent_solutions, i)
        return(solutions)
    
    def Ulusoy_random_route_solver_break_even(self):
        '''
        Generate a specified number of solutions by randomly choosing
        a classical rule to break ties.
        '''
        print('Ulusoy - Random route break even \n')
        self.resetIncumbent()
        i = 0
        while True:
            i += 1
            s = self.generate_random_solution()
            self.updateIncumbent(s) 
            print('S %i \t Goal %i \t Cost %i \t nVehicles %i '%(i, self.break_even_point, s['TotalCost'], s['nVehicles']))
            if self.break_even_iter_limit <= i:break
            if self.bestVehComp['TotalCost'] <= self.break_even_point:break
        self.disp.display_solution_info(self.bestVehComp)
        return(self.bestVehComp, i)

    def tester(self, solution):
        if self.testsolutions:
            test_solution(self.info, solution)
    
    def partition_MCARP_solutions(self, solution_list):
        
        s_min_k_incumbent, s_min_c_incumbent = {}, {}
        s_min_k_incumbent_rr, s_min_c_incumbent_rr = {}, {}
        
        for i, giant_route in enumerate(solution_list):
            (s_min_k, s_min_c) = self.gen_solution(giant_route)
            if self.reduce_all_trips: 
                s_min_k_rr = self.Reduce_Trips.reduce_trip(s_min_k)[0]
                s_min_c_rr = self.Reduce_Trips.reduce_trip(s_min_c)[0]
            
            s_min_k_incumbent = evaluatesolutions.update_number_of_vehicles_incumbent(s_min_k, s_min_k_incumbent)
            s_min_k_incumbent_rr = evaluatesolutions.update_number_of_vehicles_incumbent(s_min_k_rr, s_min_k_incumbent_rr)
            s_min_c_incumbent = evaluatesolutions.update_total_cost_incumbent(s_min_c, s_min_c_incumbent)
            s_min_c_incumbent_rr = evaluatesolutions.update_total_cost_incumbent(s_min_c_rr, s_min_c_incumbent_rr)
                   
            if (i%self.print_iter) == 0:
                print('S %i RR No \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1, s_min_c['TotalCost'], s_min_k['nVehicles'], s_min_c_incumbent['TotalCost'], s_min_k_incumbent['nVehicles']))
                print('S %i RR Ye \t Cost %i \t nVehicles %i \t Cost Inc %i \t nVehicles Inc %i '%(i+1, s_min_c_rr['TotalCost'], s_min_k_rr['nVehicles'], s_min_c_incumbent_rr['TotalCost'], s_min_k_incumbent_rr['nVehicles']))
            
            if self.testsolutions:
                self.tester(s_min_k)
                self.tester(s_min_k_rr)
                self.tester(s_min_c)
                self.tester(s_min_c_rr)
            
        return((s_min_k_incumbent, s_min_c_incumbent),(s_min_k_incumbent_rr, s_min_c_incumbent_rr))

            
    
    def pop_ulusoy(self):
        if self.problem_type == 'CLARPIF':
            part.populate_c(self.info, True)
        else:
            part.populate_c(self.info, False)
            
    def free_ulusoy(self):
        if self.problem_type == 'CLARPIF':
            part.free_c(True)
        else:
            part.free_c(False) 
                   
import py_return_problem_data
def test_ulusoy(problem_set = 'Centurion'):
    problem_sets = ['Lpr_IF_075L']
    for problem_set in problem_sets:
        problem_list = py_return_problem_data.return_problem_data_list(problem_set)
        problem_list.sort()
        extension   = ['_v1', '_v2','_v3']#['_v1', '_v2', '_v3']
        extension2  = ['_RR', '_RA']#['_RR', '_RA']
        extension3  = ['', '_NR']
        for filename in problem_list:
            for ext in extension:
                for ext2 in extension2:
                    for ext3 in extension3:
                        name = 'Prelim_test_output/' + problem_set + '/' + filename[:-len('_problem_info.dat')] + ext2 + ext + ext3 + '.csv'
                        info = return_problem_data(problem_set, filename)
                        NNS = Ulusoy_Partion(info)
                        NNS.problem_type = 'CLARPIF'
                        NNS.pop_ulusoy()
                        NNS.write_output = True
                        NNS.file_write = open(name,'w')
                        if ext == '_v1': 
                            NNS.efficient = False
                            NNS.efficient2 = False
                        if ext == '_v2':
                            NNS.efficient = True
                            NNS.efficient2 = False
                        if ext == '_v3':
                            NNS.efficient = False
                            NNS.efficient2 = True
                        if ext3 == '_NR': NNS.reduce_all_trips = False
                        else: NNS.reduce_all_trips = True           
                        if ext2 == '_RR': NNS.Ulusoy_EPS_solver('EPS_random_arc', 200)
                        if ext2 == '_RA': NNS.Ulusoy_EPS_solver('EPS_random_four_rules', 200)
                        if ext2 == '_4R': NNS.Ulusoy_EPS_solver('EPS_four_rules')
                        NNS.file_write.close()
                        NNS.free_ulusoy()

if __name__ == "__main__":
    print('Test Ulusoy on Lpr_data_set')
    test_ulusoy()
#    problem_set = 'Lpr_IF'
#    filename = 'Lpr_IF-c-01_problem_info.dat'
#    problem_set = 'Centurion'
#    filename = 'Centurion_b_problem_info.dat'
#    info = return_problem_data(problem_set, filename)
#    EPS_Ulusoy = EPS_Ulusoy_Partion(info)
#    EPS_Ulusoy.generate_route()
#    gen_random_CLARPIF_solution(info)
#    gen_random_CLARPIF_solution_Efficient(info)
    