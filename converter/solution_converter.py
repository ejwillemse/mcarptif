# -*- coding: utf-8 -*-
"""Converts an MCARPTIF solution dictionary into a pandas data frame. The
options are available:

    * First, the encoded solution, consisting just of required
    arcs can be stored. This can be used when evaluating solutions or when there
    is a need to reuse the solution, for instance, by another improvement
    procedure. In this case, the solution will be used in conjunction with the
    encoded input data, typically retrieved as `info`

    * Second, the full solution, corresponding to the original raw input file
    can be stored. This can be directly used as the final solution, and can be
    opened by any programme capable of dealing with the csv format, such as
    MS Excel and R.

If coordinates are available for the arc nodes of the original raw data, then
the routes can be visualised by merging the coordinates file with the solution
csv file. More detailed street segment names can similarly be added.

TODO:
    * Document standardized CSV format.

History:
    Created on 23 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import os
import pandas as pd
import converter.shortest_path as shortest_path
from copy import deepcopy


def solution_lists_to_df(solution_list):
    """Convert full solution lists to a pandas dataframe.

    Arg:
        solution_list (list of lists): each list represent an arc visit and
            contains its associated information.

    Returns:
        solution_df (df): a user-friendly pandas data frame of the encoded
            solution, thus to be used with the converted problem info, see
            convert_df for more detail.
    """
    headings = ['route',
                'subroute',
                'activity_id',
                'activity_type',
                'total_traversal_time_to_activity',
                'activity_time',
                'activity_demand',
                'remaining_capacity',
                'remaining_time',
                'cum_demand',
                'cum_time']

    solution_df = pd.DataFrame.from_records(solution_list, columns=headings)

    return solution_df


def convert_df(info, solution):
    """
    Covert the solution into a user-friendly pandas data frame (df).

    Args:
        info (class): information of the problem instance. See
            `load_data` for more information.ec
        solution (dict): a full solution dictionary of the solution.

    Returns:
        solution_df (df): a user-friendly pandas data frame of the encoded
            solution, thus to be used with the converted problem info, see the
            example below for more detail.

    Example:

        First retrieve input data and generate a starting solution:

        >>> from converter import solution_converter
        >>> from converter import load_instance
        >>> from solver import solve_instance
        >>> info = load_instance('data/Lpr_IF/Lpr_IF-c-03.txt')
        .
        .
        .
        >>> solution = solve_instance('data/Lpr_IF/Lpr_IF-c-03.txt', False)
        .
        .
        .
        >>> solution_df = solution_converter.convert_df(info, solution)

        To view the first five records (note that the display in terminal of
        this help file is not correct):

        >>> solution_df.head()
   route  subroute  activity_id activity_type  \
0      0         0            0   depot_start
1      0         0           66       collect
2      0         0          104       collect
3      0         0          122       collect
4      0         0          166       collect

   total_traversal_time_to_activity  activity_time  activity_demand  \
0                                 0              0                0
1                                 0            204              189
2                                 0            472              447
3                                 0            211              193
4                                 0            245              225

   remaining_capacity  remaining_time  cum_demand  cum_time
0               10000           28800           0         0
1                9811           28596         189       204
2                9364           28124         636       676
3                9171           27913         829       887
4                8946           27668        1054      1132

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

        total_traversal_time_to_activity (int): time to travel from the PREVIOUS
            service activity to the current service activity, which is based on
            the shortest-path (time-wise) input matrix.

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

    depot = info.depotnewkey
    facilities = info.IFarcsnewkey
    capacity = info.capacity
    max_trip = info.maxTrip
    demand = info.demandL
    serve_cost = info.serveCostL
    d = info.d
    dump_cost = info.dumpCost

    solution_list = []
    n_routes = solution['nVehicles']
    for vehicle_i in range(n_routes):
        n_subroutes = solution[vehicle_i]['nTrips']
        for subroute_i in range(n_subroutes):
            prev_arc = depot
            subroute = solution[vehicle_i]['Trips'][subroute_i]

            if subroute[-1] in facilities:
                subroute.append(subroute[-1])
            elif subroute[-2] in facilities:
                subroute.insert(-2, subroute[-2])

            for i, arc in enumerate(subroute):
                if arc == depot:  # depots is basically a reset
                    if i == 0:
                        serve_type = 'depot_start'
                        time_to_arc = 0
                        cum_demand = 0
                        cum_time = 0
                        remain_cap = capacity
                        remain_time = max_trip
                    else:
                        serve_type = 'depot_end'
                        time_to_arc = d[prev_arc][arc]
                        remain_time -= time_to_arc
                        cum_time += time_to_arc
                        if prev_arc in facilities:
                            remain_cap = capacity
                            cum_demand = 0
                    arc_serve_time = 0
                    arc_demand = 0
                elif arc in facilities:
                    if i == 0:  # first IF visit is a partial reset
                        serve_type = 'depart_if'
                        time_to_arc = 0
                        arc_serve_time = 0
                    elif prev_arc not in facilities:
                        # last IF visit is the actual offload
                        serve_type = 'arrive_if'
                        time_to_arc = d[prev_arc][arc]
                        arc_serve_time = 0
                        remain_time -= time_to_arc
                        cum_time += time_to_arc
                    else:
                        serve_type = 'offload'
                        time_to_arc = 0
                        arc_serve_time = dump_cost
                        remain_time -= arc_serve_time
                        cum_time += arc_serve_time
                        remain_cap = capacity
                        cum_demand = 0
                    arc_demand = 0
                else:
                    serve_type = 'collect'
                    time_to_arc = d[prev_arc][arc]
                    arc_serve_time = serve_cost[arc]
                    arc_demand = demand[arc]
                    remain_cap -= demand[arc]
                    remain_time -= (time_to_arc + arc_serve_time)
                    cum_demand += demand[arc]
                    cum_time += time_to_arc + arc_serve_time
                prev_arc = arc

                line_info = [vehicle_i, subroute_i, arc, serve_type,
                             time_to_arc, arc_serve_time, arc_demand,
                             remain_cap, remain_time, cum_demand, cum_time]
                solution_list.append(line_info)

    solution_df = solution_lists_to_df(solution_list)

    return solution_df


def convert_df_full(info, solution_df, p_full=None):
    """Covert the solution into a user-friendly pandas data frame (df) that
    corresponds to the original raw input file

    Args:
        info (named tuple): information of the problem instance. See
            `load_data` for more information.
        solution_df (df): a user-friendly pandas data frame of the solution,
            see `convert_df` for more detail.

    Returns:
        solution_df_full (df): a user-friendly pandas data frame of the
            solution that corresponds to the original raw input file.

    Example:

        First retrieve input data and generate a starting solution:

        >>> from converter import solution_converter
        >>> from converter import load_instance
        >>> from solver import solve_instance
        >>> info = load_instance('data/Lpr_IF/Lpr_IF-c-03.txt')
        .
        .
        .
        >>> solution = solve_instance('data/Lpr_IF/Lpr_IF-c-03.txt', False)
        .
        .
        .
        >>> solution_df = solution_converter.convert_df(info, solution)
        >>> df_full = solution_converter.convert_df_full(info, solution_df)

        To view the first ten records (note that the display in terminal of
        this help file is not correct):

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

        activity_id (int): the ID of the arc visited.

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
    solution_df = solution_df.copy()
    solution_df['activity_id'] = [info.reqArcList[u] for u in
                                  solution_df['activity_id']]
    real_arcs = solution_df['activity_id']
    solution_list = []

    for i, u in enumerate(real_arcs[:-1]):
        current_arc_list = list(solution_df.iloc[i])
        solution_list.append(current_arc_list)

        v = real_arcs[i + 1]
        if p_full is None:
            activity_id = shortest_path.sp_full(info.p_full, u, v)
        else:
            activity_id = shortest_path.sp_full(p_full, u, v)

        for inter_u in activity_id:
            solution_list.append(deepcopy(current_arc_list))
            solution_list[-1][2] = inter_u
            solution_list[-1][3] = 'traversal'
            solution_list[-1][4] = 0
            solution_list[-1][5] = info.travelCostL[inter_u]
            solution_list[-1][6] = 0
            solution_list[-1][8] = solution_list[-2][8] - solution_list[-1][5]
            solution_list[-1][10] = solution_list[-2][10] + solution_list[-1][5]

    solution_list.append(list(solution_df.iloc[i + 1]))

    solution_df_full = solution_lists_to_df(solution_list)

    node_start = [info.allIndexD[u][0] for u in solution_df_full['activity_id']]
    node_end = [info.allIndexD[u][1] for u in solution_df_full['activity_id']]

    solution_df_full.insert(3, 'arc_start_node', node_start)
    solution_df_full.insert(4, 'arc_end_node', node_end)

    return solution_df_full


def write_solution_df(solution_df, file_path, overwrite=False):
    """Stores the solution dataframe at a specific location and file name.

    Args:
        solution_df (df): a pandas data frame of the solution.
        file_path (str): location and file name to which the data frame will be
            stored. A new file is created.
        overwrite (bool): whether `file_path` should be overwriten if it already
            exists.

    Raise:
        FileExistsError: if overwrite is false and the output file
            already exists.
    """

    if not overwrite and os.path.isfile(file_path):
        raise FileExistsError('`{0}` already exists and cannot be '
                              'overwritten. \nCheck module documentation on '
                              'how to overwrite files.'.format(file_path))

    solution_df.to_csv(file_path, index=False)


def read_solution_df(file_path):
    """Load the solution data frame

    Args:
        file_path (str):  location and file name of the solution data frame.

    Return:
        solution_df (df): a user-friendly pandas data frame of the solution,
            see `convert_df` for more detail.

    Raise:
        FileNotFoundError: file not found.
    """

    if not os.path.isfile(file_path):
        raise FileNotFoundError('Solution file `{0}` not '
                                'found.'.format(file_path))

    solution_df = pd.read_csv(file_path)

    return solution_df
