'''
Created on Oct 17, 2014

@author: ejwillemse (ejwillemse@gmail.com)

This module compares and updates MCARP and MCLARPIF solutions and incumbents (best solution found so far) for different preemptive objectives. 
'''
import copy

HUGE = 1e300000
DEFAULT_CRITERIA = 'TotalCost'
DEFAULT_MIN_OBJECTIVE = True

def _write_output_to_file(outFileName, line):
    '''
    Write results to the end of a results file.
    '''
    outfile = open(outFileName,'a')
    outfile.write(line)
    outfile.close()

def _compare_solutions_on_criteria(candidate_solution, incumbent_solution, criterion, min_objective):
    '''
    Check if the candidate solution is better than or equal to incumbent on specified criteria.
    '''
    
    # max Z is equivalent to min -Z
    if min_objective == True: sign = 1
    else: sign = - 1
    
    # candidate_solution and incumbent_solution are dictionaries of the form {criterion 1 : value, criterion 2 : value ...}
    if sign*candidate_solution[criterion] < sign*incumbent_solution[criterion]:
        new_incumbent = True
        same_incumbent = False
    elif sign*candidate_solution[criterion] == sign*incumbent_solution[criterion]:
        new_incumbent = False
        same_incumbent = True
    else:
        new_incumbent = False
        same_incumbent = False       
    return(new_incumbent, same_incumbent)

def _create_incumbent(objective_measures):
    '''
    Creates an incumbent that will reassigned the the candidate
    '''
    incumbent_solution = {}
    for criteria in objective_measures:
        incumbent_solution[criteria] = HUGE    
    return(incumbent_solution)

def _set_objective_type(objectives_min, criterion_index):
    '''
    Set the objective direction (min, which is the default, or max) of the criterion to be compared.
    '''
    min_objective = DEFAULT_MIN_OBJECTIVE
    if objectives_min:
        min_objective = objectives_min[criterion_index]
    return(min_objective)

def check_incumbents(candidate_solution, incumbent_solution = {}, objective_measures = [DEFAULT_CRITERIA], objectives_min = []):
    '''
    Preemptively compares a candidate solution against incumbents on a list of objectives, ordered from most to least important.
    Assumed to be min objectives, but can be specified as True (min) or False (max) per objective as input.
    '''
    new_incumbent_found = False

    if not incumbent_solution: incumbent_solution = _create_incumbent(objective_measures)
                        
    for criterion_index, criterion in enumerate(objective_measures):

        min_objective = _set_objective_type(objectives_min, criterion_index)

        # check if candidate is better, and go to next objective if it is the same
        (new_incumbent, same_incumbent) = _compare_solutions_on_criteria(candidate_solution, incumbent_solution, criterion, min_objective)
        
        if new_incumbent == True: 
            new_incumbent_found = True
            break
        elif same_incumbent == False:
            break
    
    return(new_incumbent_found)

def update_number_of_vehicles_incumbent(candidate_solution, incumbent_solution = {}):
    '''
    Update incumbent on number of vehicles then total cost
    '''
    objective_measures = ['nVehicles', 'TotalCost']
    if check_incumbents(candidate_solution, incumbent_solution, objective_measures):
        incumbent_solution = copy.deepcopy(candidate_solution)
    return(incumbent_solution)
    
def update_total_cost_incumbent(candidate_solution, incumbent_solution = {}):
    '''
    Update incumbent on total cost then number of vehicles
    '''
    objective_measures = ['TotalCost', 'nVehicles']
    if check_incumbents(candidate_solution, incumbent_solution, objective_measures):
        incumbent_solution = copy.deepcopy(candidate_solution)
    return(incumbent_solution)

def update_pure_total_cost_incumbent(candidate_solution, incumbent_solution = {}):
    '''
    Update incumbent only on total cost
    '''
    objective_measures = ['TotalCost']
    if check_incumbents(candidate_solution, incumbent_solution, objective_measures):
        incumbent_solution = copy.deepcopy(candidate_solution)
    return(incumbent_solution)

def update_all_incumbents(candidate_solution, incumbent_solutions):
    '''
    Compare update and return all three incumbents for different objectives.
    '''
    # Unpack incumbents
    (incumbent_n_vehicles, incumbent_cost, incumbent_cost_only) = incumbent_solutions
    
    # min vehicles then cost objectives
    incumbent_n_vehicles = update_number_of_vehicles_incumbent(candidate_solution, incumbent_n_vehicles)
    
    # min cost then vehicles objectives
    incumbent_cost = update_total_cost_incumbent(candidate_solution, incumbent_cost)
    
    # only min cost objectives
    incumbent_cost_only = update_pure_total_cost_incumbent(candidate_solution, incumbent_cost_only)
    return(incumbent_n_vehicles, incumbent_cost, incumbent_cost_only)

def initital_all_incumbents():
    '''
    Initiate all three incumbents to empty dictionaries.
    '''
    incumbent_n_vehicles = {}
    incumbent_cost = {}
    incumbent_cost_only = {}
    return(incumbent_n_vehicles, incumbent_cost, incumbent_cost_only)

if __name__ == '__main__':
    pass