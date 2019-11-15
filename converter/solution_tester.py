# -*- coding: utf-8 -*-
"""Checks for error in the full pandas solution (_sol_full_), corresponding to
the original raw input file. The raw input file is converted and then tested
against the solution file. Thus, if there are errors in the converter, it will
go unnoticed.

The following is tested:

    * all required arcs and edges are serviced exactly once;
    * routes start and end at the depot;
    * the start node of an arc is the same as the end node of its predecessor
        arc;
    * traversal and service time, and arc demand per arc is correct;
    * vehicle capacity prior to offloads are not exceeded;
    * vehicle offloads at intermediate facilities;
    * offloading time is correct;
    * vehicle offloads at an intermediate facility before returning to
        the depot; and
    * reported total travel time and demand collected per route is correct.
"""
import pandas as pd
from converter.load_data import load_instance
from converter.load_data import ConvertedInputs


def load_solution_file(instance_path, solution_path, ignore_mismatch=False):
    """Load solution and converted info files

    Args:
        instance_path (str): path to the raw input file.
        solution_path (str): path to the full solution csv file for the
            instance.

    Kwarg:
        ignore_mismatch (bool): if mismatch between the raw instance file path
            file and solution file path should be ignored, in case some
            non-standard file names are used.

    Raises:
        AttributeError: mismatch between raw input file name and solution file
            name.
        FileNotFoundError: instance_path not found.
        FileNotFoundError: solution_path not found.
        AttributeError: solution_path does not present a full solution, it's
            probably the encoded solution.

    Return:
        info (named tuple): named tuple containing all the converted input data.
        full_df (df): pandas dataframe of the full solution.
    """
    if ignore_mismatch is False:
        instance_name = ConvertedInputs(instance_path).file_name
        solution_name = ConvertedInputs(solution_path).file_name

        n = len(instance_name)
        if instance_name != solution_name[:n]:
            error_massage = 'Mismatch between raw instance name `{0}` and ' \
                            'solution file name `{1}`. Was the correct files ' \
                            'loaded? If so, see docstring.'.format(
                            instance_name, solution_name)

            raise AttributeError()

    info = load_instance(instance_path)
    full_df = pd.read_csv(solution_path)

    file_columns = set(full_df.columns)

    expected_headings = {'route',
                         'subroute',
                         'activity_id',
                         'arc_start_node',
                         'arc_end_node',
                         'activity_type',
                         'total_traversal_time_to_activity',
                         'activity_time',
                         'activity_demand',
                         'remaining_capacity',
                         'remaining_time',
                         'cum_demand',
                         'cum_time'}

    encoded_columns = {'route',
                       'subroute',
                       'activity_id',
                       'activity_type',
                       'total_traversal_time_to_activity',
                       'activity_time',
                       'activity_demand',
                       'remaining_capacity',
                       'remaining_time',
                       'cum_demand',
                       'cum_time'}

    if expected_headings.difference(file_columns):
        if not encoded_columns.difference(file_columns):
            m = ' Columns consistent with encoded solution, not full ' \
                      'solution. Make sure the input file is the correct one.'
        else:
            m = ''
        m = '`{0}` has inconsistent column names.'.format(solution_path) + m
        raise AttributeError(m)

    return info, full_df


def consecutive_connected(full_df, raise_error=False):
    """Check that that the end start vertex of an edge is the same as the begin
    vertex of its predecessor.

    Arg:
        full_df (df): pandas dataframe of the full solution.

    Kwarg:
        raise_error (bool): if error should be directly raised.

    Return:
        error_message (str): error message displaying what's wrong.
    """
    start_nodes = list(full_df['arc_start_node'][1:])
    end_nodes = list(full_df['arc_end_node'][:-1])

    if start_nodes != end_nodes:
        error = 'Start node of arc not the same as its predecessor end arc'
        print(error)
        for i, node in enumerate(end_nodes):
            if node != start_nodes[i]:
                print('\nArc visit {0} vs {1}\n'.format(i, i + 1))
                print(full_df.iloc[i])
                print('\nend node different from start node of \n')
                print(full_df.iloc[i + 1])

        if raise_error:
            raise AttributeError('Start and end node error. See above for more '
                                 'info')

        return error


def return_arc_tuple(arc_visit_df):
    """Returns the arc tuple visited for an activity.

    Arg:
        arc_visit_df (df): pandas dataframe for a single visit activity.

    Return (tuple): start and end vertex of the arc, as a tuple.
    """
    return arc_visit_df.arc_start_node, arc_visit_df.arc_end_node


def start_end_depot(info, full_df, raise_error=False):
    """Check that each route starts and ends at the depot

    Arg:
        info (named tuple): named tuple containing all the converted input data.
        full_df (df): pandas dataframe of the full solution.

    Kwarg:
        raise_error (bool): if error should be directly raised.

    Return:
        error_message (str): error message displaying what's wrong.
    """

    route_ids = full_df.route.unique()

    depot_key = info.reqArcList[info.depotnewkey]
    depot_arc = info.allIndexD[depot_key]
    errors = []
    for route_id in route_ids:

        route = full_df.loc[full_df.route == route_id, ]

        depot_start_tuple = return_arc_tuple(route.iloc[0])
        depot_end_tuple = return_arc_tuple(route.iloc[-1])

        depot_start_error = False
        depot_end_error = False

        if depot_start_tuple != depot_arc:
            depot_start_error = True
            errors.append('route {0} depot start arc error'.format(route_id))
            print('\nRoute {0} does not start at the depot {1}\n'.format(route_id,
                                                                     depot_arc))

        if route.iloc[0].activity_type != 'depot_start':
            depot_start_error = True
            errors.append('route {0} depot start activity '
                          'error'.format(route_id))
            print('Route {0} does not start with a `depot_start` '
                  'activity.'.format(route_id))

        if depot_start_error:
            print('\nFirst activity in route {0}:\n'.format(route_id))
            print(route.iloc[0])

        if depot_end_tuple != depot_arc:
            depot_end_error = True
            errors.append('route {0} depot end arc error'.format(route_id))
            print('\nRoute {0} does not end at the depot {1}\n'.format(route_id,
                                                                   depot_arc))

        if route.iloc[-1].activity_type != 'depot_end':
            depot_end_error = True
            errors.append('route {0} depot end activity error'.format(route_id))
            print('\nRoute {0} does not end with a `depot_end` '
                  'activity.\n'.format(route_id))

        if depot_end_error:
            print('\nLast activity in route {0}:\n'.format(route_id))
            print(route.iloc[-1])

    if raise_error:
        raise AttributeError('\nDepot error. See above for more info\n')

    return errors


def check_if_arrival_offload(subroute, if_arcs):
    """Check if IF arrival and offload is correct.

    Args:
        subroute (df): pandas dataframe of a single subroute.
        if_arcs (ls): list of IF arc tuples.

    returns:
        errors (str): list of potential errors.
        if_arc (tuple): tuple of IF arc visited.
    """

    errors = []
    offload = subroute.iloc[0]
    if_arc = return_arc_tuple(offload)
    if if_arc not in if_arcs:
        errors.append('First arc in subroute not an IF arc')
        print('First arc {0} in subroute not on list of IF arcs {1}'.format(
            if_arc, if_arcs
        ))

    if offload.activity_type != 'depart_if':
        errors.append('First arc in subroute not a `depart_if` activity arc')

    print('First activity {0}  in subroutenot not `depart_if`'.format(
        offload.activity_type
    ))

    return errors, if_arc


def check_if_departure(subroute):
    """Check if IF departure is correct.

    Args:
        subroute (df): pandas dataframe of a single subroute.

    returns:
        errors (str): list of potential errors.
        if_arc (tuple): tuple of IF arc visited.
    """

    errors = []
    offload = subroute.iloc[0]
    if_arc = return_arc_tuple(offload)
    if if_arc not in if_arcs:
        errors.append('First arc in subroute not an IF arc')
        print('First arc {0} in subroute not on list of IF arcs {1}'.format(
            if_arc, if_arcs
        ))

    if offload.activity_type != 'depart_if':
        errors.append('First arc in subroute not a `depart_if` activity arc')

    print('First activity {0}  in subroutenot not `depart_if`'.format(
        offload.activity_type
    ))

    return errors, if_arc

def check_last_if_departure(subroute):
    """Check if last IF departure before returning to the depot is correct.

    Args:
        subroute (df): pandas dataframe of a single subroute.
    """



def if_visits(info, full_df, raise_error=False):
    """Check that offload visits are included correctly.

    Arg:
        info (named tuple): named tuple containing all the converted input data.
        full_df (df): pandas dataframe of the full solution.

    Kwarg:
        raise_error (bool): if error should be directly raised.

    Return:
        error_message (str): error message displaying what's wrong.
    """

    route_ids = full_df.route.unique()

    if_keys = [info.reqArcList[u] for u in info.IFarcsnewkey]
    if_arcs = [info.allIndexD[u] for u in if_keys]
    errors = []

    for route_id in route_ids:

        route = full_df.loc[full_df.route == route_id, ]
        subroute_ids = route.subroute.unique()

        # check first subroute
        subroute = route.loc[route.subroute == subroute_ids[0], ]
        if_arrive = subroute.iloc[-2]
        if_offload = subroute.iloc[-1]

        for mid_route_id in subroute_ids[1:-1]:
            # check mid-subroute
            subroute = route.loc[route.subroute == mid_route_id, ]
            if_departh = subroute.iloc[0]
            if_arrive = subroute.iloc[-2]
            if_offload = subroute.iloc[-1]

        # check last subroute, not that easy :(
        subroute = route.loc[route.subroute == subroute_ids[-1], ]
        if_departh = subroute.iloc[0]
        if_arrive = subroute.iloc[-2]
        if_offload = subroute.iloc[-1]
