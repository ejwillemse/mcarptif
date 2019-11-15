# -*- coding: utf-8 -*-
"""Generate and improve a solution for the Mixed Capacitated Arc Routing
Problem under Time restrictions with Intermediate Facilities (MCARTIF). Initial
solution is generated using the Path-Scanning-Heuristic developed in [1]. The
solution is improved using the Local Search or Tabu Search algorithm developed
in [2].

References:

    [1] Willemse, E. J. and Joubert, J. W. (2016). Constructive heuristics for
        the mixed capacity arc routing problem under time restrictions with
        intermediate facilities. Computers & Operations Research, 68:30–62.

    [2] Willemse, E. J. (2016). Heuristics for large-scale Capacitated Arc
        Routing Problems on mixed networks. PhD thesis, University of Pretoria,
        Pretoria. Available online from
        http://hdl.handle.net/2263/57510 (Last viewed on 2017-01-16).

History:
    Created on 23 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import solver.py_alg_extended_path_scanning_rr as EPS
import solver.LS_MCARPTIF as LS
from converter.load_data import load_instance
from converter.load_data import ConvertedInputs
from converter.solution_converter import convert_df
from converter.solution_converter import convert_df_full
from converter.solution_converter import write_solution_df


def gen_solution(info, reduce_trips=True):
    """Generate a feasible solution using a deterministic Path-Scanning
    constructive heuristic.

    Arg:
        info (namedtuple): converted input data of a problem instance. See
            help(`converter.load_data.load_instance`) for more info.

    Returns:
        solution (dict): standardised solution dictionary for the problem
            instance.
    """

    EPS.populate_c_local_search(info, True)
    initial_solver = EPS.EPS_IF(info)
    initial_solver.c_modules = True
    initial_solver.reduce_all_trips = reduce_trips
    solution = initial_solver.EPS_IF_solver(rule_type='EPS_all_rules')[0][0]
    EPS.free_c_local_search()

    return solution


def initiate_local_search(info):
    """Initiate the Local Search algorithm with specific parameter values.

    Arg:
        info (namedtuple): converted input data of a problem instance. See
            help(`converter.load_data.load_instance`) for more info.

    Return:
        improve (class): solution improvement class
    """
    improve = LS.LS_MCARPTIF(info, info.nn_list, testAll=False,
                             autoInvCosts=False)

    # Defaults
    improve.doubleCross = True
    improve.comboFeasibleMoves = True
    improve.comboMovesVN = True
    improve.threshold = 0
    improve.thresholdUse = 1

    # Activate acceleration functions
    improve.candidateMoves = True
    improve.compoundMoves = True

    # Do not print output
    improve.setScreenPrint(True)

    # Non default
    improve.nnFrac = 1  # Set nearest neighbor fraction, to be changed.

    return improve


def initiate_tabu_search(info):
    """Initiate the Tabu Search algorithm with specific parameter values.

    Arg:
        info (namedtuple): converted input data of a problem instance. See
            help(`converter.load_data.load_instance`) for more info.

    Return:
        improve (class): solution improvement class
    """
    improve = LS.TabuSearch_MCARPTIF(info, info.nn_list, testAll=False)

    # Defaults
    compoundMoves = True
    newCompoundMoves = False
    tabuTenure = 5
    tabuThreshold = 1
    tabuMoveLimit = 1000
    saveOutput = False
    improve._printOutput = False  # Do not print output
    improve.suppressOutput = False

    # Non-default
    nnFrac = 1
    maxNonImprovingMoves = 50

    improve.setTabuSearchParameters(compoundMoves,
                                    newCompoundMoves,
                                    tabuTenure,
                                    tabuThreshold,
                                    nnFrac,
                                    tabuMoveLimit,
                                    maxNonImprovingMoves,
                                    saveOutput)
    return improve


def clear_improvement_setup(improvement_procedure):
    """Clears cython modules of the improvement procedure"""
    improvement_procedure.clearCythonModules()


def improve_solution(info, initial_solution, improvement='LS'):
    """Improve a give initial solution using metaheuristics.

    Arg:
        info (namedtuple): converted input data of a problem instance. See
            help(`converter.load_data.load_instance`) for more info.
        initial_solution (dict): standardised solution dictionary for the
            problem instance.

    Kwarg:
        improvement (str): improvement procedure to be used to improve the
            solution, which can either be Local Search or Tabu Search.

    Returns:
        solution (dict): standardised improved solution dictionary for the
            problem instance.
    """
    if improvement == 'LS':
        improver = initiate_local_search(info)
    if improvement == 'TS':
        improver = initiate_tabu_search(info)
    solution = improver.improveSolution(initial_solution)
    clear_improvement_setup(improver)

    return solution


def solve_instance(file_path, improve=None, reduce_initial_trips=True):
    """Generate and improve a solution from a raw instance file.

    Arg:
        file_path (str): path to raw text file, in Belenguer et al (2006)
        format.
    Kwarg:
        improve (str): whether the initial solution should be improved with a
            Local Search (='LS'), tabu-search (='TS'), or not all (=None).
            Increases the computation time to generate a solution if activated.
        reduce_initial_trips (bool): whether the routes in the initial solution should
            improved.

    Returns:
        solution (dict): standardised improved solution dictionary for the
            problem instance.

    Example:

        >>> from solver import solve_instance
        >>> solution = solve_instance('data/Lpr_IF/Lpr_IF-c-03.txt')
        .
        .
        .
        I: 2 	 Saving: 0 	 # Moves 37 	 Inc: 112977...
        I: 3 	 Saving: -125 	 # Moves 37 	 Inc: 112852...
        I: 4 	 Saving: -13 	 # Moves 56 	 Inc: 112839...
        .
        .
        .
        Initial and incumbent cost: 111921 	 114908
        Initial and incumbent fleet size: 4 	 4

        >>> solution['TotalCost']
        111921.0

        >>> solution['nRoutes']
        4

        Extracting information for vehicle 0:

        >>> solution[0]['Cost']
        27697

        First ten required arcs serviced by vehicle 1 in trip 0:

        >>> solution[1]['Trips'][0][:10]
        [0, 66, 104, 122, 166, 182, 340, 390, 418, 420]

    """
    info = load_instance(file_path)
    solution = gen_solution(info, reduce_trips)
    if improve is not None:
        solution = improve_solution(info, solution, improve)

    return solution


def solve_store_instance(file_path, out_path=None, improve=None, reduce_initial_trips=True,
                         full_output=True, overwrite=True):
    """Solve a specific problem instance and store the partial and full solution
    in the same folder as the raw input data. Two solution files are stored:
    one ending with `_sol_[solver].csv` and `_sol_full_[solver].csv`, where
    [solver] is the type of solver or improvement procedure used. Currently
    `ps`, `ps_local_search` and `ps_tabu_search` is supported, where `ps`
    stands for path-scanning

    The solutions can be viewed with any programme capable of dealing with the
    csv format.

    Arg:
        file_path (str): path to raw text file, in Belenguer et al (2006)
        format.

    Kwarg:
        out_path (str): partial output path, excluding extensions, where the
            results should be stored. If none is specified, the file is stored
            in the same folder as the raw input file, starting with the raw
            input file name, and ending with the `sol_[solver].csv` and
            `_sol_full_[solver].csv`, where [solver] is the type of solver or
            improvement procedure to be used. Setting out_path='' stores the
            solution in the current directory. Setting out_path='/' gives an
            error, not sure why.
        improve (str): whether the initial solution should be improved with a
            Local Search (='LS'), tabu-search (='TS'), or not all (=None).
            Increases the computation time. Set to None if a solution should be
            quickly generated.
        reduce_initial_trips (bool): whether the routes in the initial solution should
            improved.
        full_output (bool): whether the full solution, corresponding to the raw
            input file, and with shortest path arc visits including, should be
            stored, as `_sol_full.csv`, with the encoded solution file.
        overwrite (bool): whether existing solution files for the raw input file
            should be overwritten.

    Examples:

        >>> from solver import solve_store_instance
        >>> solve_store_instance('data/Lpr_IF/Lpr_IF-c-03.txt')

            Viewing the 'Lpr_IF-c-03_sol.csv' files:

        >>> import os
        >>> os.listdir('data/Lpr_IF/')
        [...'Lpr_IF-c-03.txt', 'Lpr_IF-c-03_info_lists_pickled.dat',
        'Lpr_IF-c-03_nn_list.dat', 'Lpr_IF-c-03_problem_info.dat',
        'Lpr_IF-c-03_sol.csv', 'Lpr_IF-c-03_sol_full.csv',
        'Lpr_IF-c-03_sp_data_full.dat,'...]

            Viewing the encoded solution file via pandas:

        >>> import pandas as pd
        >>> solution_csv = pd.read_csv('data/Lpr_IF/Lpr_IF-c-03_sol_ps.csv')

            To view the first five records (note that the display in terminal of
            this help file is not correct):

        >>> solution_df.head()
           route  subroute  activity_id activity_type  travel_time_to_activity  \
0      0         0            0   depot_start                        0
1      0         0           66       collect                        0
2      0         0          104       collect                        0
3      0         0          122       collect                        0
4      0         0          166       collect                        0

   activity_time  activity_demand  remaining_capacity  remaining_time  \
0              0                0               10000           28800
1            204              189                9811           28596
2            472              447                9364           28124
3            211              193                9171           27913
4            245              225                8946           27668

   cum_demand  cum_time
0           0         0
1         189       204
2         636       676
3         829       887
4        1054      1132

        Each row in the data frame represents an activity of the current
        vehicle. The intra route ordering is therefore significant. The order of
        the routes is not significant.

        The following variables are defined per activity row.

        route (int): unique ID of the route

        subroute (int): subroute ID of the current route. Subroutes are mini
            routes between waste offloads.

        activity_id (int): the ID of the required arc visited.

        activity_type (factor): type of activity being performed, which can be
            one of the following:
                - depot_start: collection route starts at the vehicle depot.
                - collect: vehicle services the arc at the activity_id, with
                    depot and waste facilities also having unique IDs.
                - arrive_if: vehicle arrives at a facility, ready to offload
                    waste.
                - offload: vehicle offloads waste at the facility.
                - depart_if: vehicle departs the facility to resume its
                    waste collection, or return to the vehicle depot.
                - depot_end: vehicle arrives back at the depot and thereby ends
                    its collection route.

        travel_time_to_activity (int): time to travel from the PREVIOUS activity
            to the current activity, which is based on the shortest-path (time
            wise) input matrix.

        activity_time (int): time required to complete the current activity.

        activity_demand (int): amount of waste to be collected at the activity.

        remaining_capacity (int): remaining capacity of the vehicle, and which
            is reset to its maximum when waste is offloaded.

        remaining_time (int): remaining work time of the vehicle to complete its
            route.

        cum_demand (int): total demand collected by the vehicle thus far in its
            subroute.

        cum_time (int): total time spend by the vehicle thus far in its route.

        See pandas help files and documentation on more information on working
        with pandas data frames.

            Viewing the full solution file via pandas:

        >>> import pandas as pd
        >>> df_full = pd.read_csv('data/Lpr_IF/Lpr_IF-c-03_sol_full_ps.csv')
        >>> df_full[:10]
   route  subroute  activity_id  arc_start_node   arc_end_node activity_type  \
0      0         0            0               1              1   depot_start
1      0         0           80               1             14       collect
2      0         0          118              14             21       collect
3      0         0          136              21             35       collect
4      0         0          180              35             40       collect
5      0         0          196              40             54       collect
6      0         0            9              54             63     traversal
7      0         0          270              63             90       collect
8      0         0          354              90            105       collect
9      0         0          404             105            118       collect

   total_traversal_time_to_activity  activity_time  activity_demand  \
0                                 0              0                0
1                                 0            204              189
2                                 0            472              447
3                                 0            211              193
4                                 0            245              225
5                                 0            383              365
6                                 0             16                0
7                                16            425              386
8                                 0            449              432
9                                 0            454              436

   remaining_capacity  remaining_time  cum_demand  cum_time
0               10000           28800           0         0
1                9811           28596         189       204
2                9364           28124         636       676
3                9171           27913         829       887
4                8946           27668        1054      1132
5                8581           27285        1419      1515
6                8581           27269        1419      1531
7                8195           26844        1805      1956
8                7763           26395        2237      2405
9                7327           25941        2673      2859

        Each row in the data frame represents an activity of the current
        vehicle. The intra route ordering is therefore significant. The order of
        the routes is not significant.

        The following variables are defined per activity row.

        route (int): unique ID of the route

        subroute (int): subroute ID of the current route. Subroutes are mini
            routes between waste offloads.

        activity_id (int): the ID of the arc visited. This is different from
            the encoded solution since a unique arc ID exists for all arcs.

        arc_start_node (int): the start node of the arc visited, conforming to
            the original raw input data.

        arc_end_node (int): the end node of the arc visited, conforming to
            the original raw input data.

        activity_type (factor): type of activity being performed, which can be
            one of the following:
                - depot_start: collection route starts at the vehicle depot.
                - collect: vehicle services the arc at the activity_id, with
                    depot and waste facilities also having unique IDs.
                - traverse: vehicle travels between service, depot and offload
                    activities.
                - arrive_if: vehicle arrives at a facility, ready to offload
                    waste.
                - offload: vehicle offloads waste at the facility.
                - depart_if: vehicle departs the facility to resume its
                    waste collection, or return to the vehicle depot.
                - depot_end: vehicle arrives back at the depot and thereby ends
                    its collection route.

        total_traversal_time_to_activity (int): time to travel from the PREVIOUS
            service activity to the current service activity, which is based on
            the shortest-path (time-wise) input matrix and is the sum of all
            traverse activities between the current and previous service
            activities. Here, depot and IF visits are also considered service
            activities.

        activity_time (int): time required to complete the current activity.

        activity_demand (int): amount of waste to be collected at the activity.

        remaining_capacity (int): remaining capacity of the vehicle, and which
            is reset to its maximum when waste is offloaded.

        remaining_time (int): remaining work time of the vehicle to complete its
            route.

        cum_demand (int): total demand collected by the vehicle thus far in its
            subroute.

        cum_time (int): total time spend by the vehicle thus far in its route.

        See pandas help files and documentation on more information on working
        with pandas data frames.
    """
    improvement_ext = {'LS' : '_local_search', 'TS' : '_tabu_search'}
    ext = 'ps'

    info = load_instance(file_path)
    solution = gen_solution(info, reduce_initial_trips)
    if improve is not None:
        solution = improve_solution(info, solution, improve)
        ext += improvement_ext[improve]

    solution_df = convert_df(info, solution)
    conv = ConvertedInputs(file_path)
    if out_path is None:
        out_path = conv.folder_path + conv.file_name
    else:
        out_path += conv.file_name

    output_file = out_path + '_sol_' + ext + '.csv'
    print('Writing encoded solution to {0}'.format(output_file))
    write_solution_df(solution_df, output_file, overwrite)

    if full_output is True:
        solution_df_full = convert_df_full(info, solution_df)
        output_file_full = out_path + '_sol_full_' + ext + '.csv'
        print('Writing full solution to {0}'.format(output_file_full))
        write_solution_df(solution_df_full, output_file_full, overwrite)
