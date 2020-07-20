# -*- coding: utf-8 -*-
"""Transform a solution into GEOJSON file for kepler.gl visualisation.

Input is the full directed graph, required edges graph and key-locations,
generated from `osmnx_network_extract.create_instance`, and the full
solution data-frame generated using `solver.solve`

Output is a geo-json based data-frame, where route sections are LINESTRING
and key-locations are POINTS. These can be stored as csv and displayed
directly in kepler.gl

History:
    Created on 14 June 2020
    @author: Elias J. Willemse
    @contact: ejwillemse@gmail.com
"""
import pandas as pd
from osmnx_network_extract.create_instance import test_column_exists, \
    create_arc_id


class CreateRoutesGeo:
    """Create a geo-json based data-frame of the solution.

    Args:
        df_arcs (pd.DataFrame): OSMNX based data-frame of full arc network (
            must contain a geometry, amongst others)
        df_key_locations (pd.DataFrame): OSMNX based data-frame of key
            locations, must include the depot and offload facilities.
        solution (pd.DataFrame): data-frame of full solution
        cost (str): how cost is measured, default is distance, other options
            are time and money.
    """

    def __init__(self,
                 df_arcs,
                 df_key_locations,
                 solution,
                 cost='distance'):

        test_column_exists(df_arcs,
                           'geometry',
                           'arc_id',
                           'arc_id_orig',
                           'name',
                           'highway')

        test_column_exists(df_key_locations,
                           'geometry',
                           'highway',
                           'u')

        self._df_arcs = df_arcs
        self._df_key_locations = df_key_locations
        self.solution = solution.copy()

        if 'bins' not in self._df_arcs.columns:
            self._df_arcs.columns['bins'] = 0

    def _merge_solution(self):
        """Merge arc and key-location info into solution frame"""
        traversals = self.solution['activity_type'].isin(['traversal',
                                                          'collect'])
        solution_traversals = self.solution.loc[traversals].copy()

        solution_traversals = create_arc_id(solution_traversals,
                                            'arc_id',
                                            'arc_start_node',
                                            'arc_end_node')

        solution_traversals = pd.merge(solution_traversals,
                                       self._df_arcs[['arc_id',
                                                      'arc_id_orig'
                                                      ]],
                                       how='left')

        solution_traversals = pd.merge(solution_traversals, self._df_arcs[
            ['arc_id_orig', 'geometry', 'name', 'highway', 'length', 'bins']],
                                       how='left')

        solution_traversals.loc[solution_traversals['activity_type'] !=
                                'collect', 'bins'] = 0

        solution_traversals = solution_traversals.dropna(subset=['geometry'])

        solution_keypoints = self.solution[~traversals].copy()

        solution_keypoints = pd.merge(solution_keypoints,
                                      self._df_key_locations[['geometry',
                                                              'highway',
                                                              'u']],
                                      how='left', left_on='arc_start_node',
                                      right_on='u')

        solution_keypoints = solution_keypoints.drop(columns=['u'])
        solution_traversals = solution_traversals.sort_values(['index'])
        self.solution = pd.concat([solution_keypoints, solution_traversals])
        self.solution = self.solution.sort_values(['index'])

    def add_custom_duration(self, speed_df):
        """Add custom duration based on speed formula, if `activity_time` and
        `activity_speed` is in a length or cost unit. The time is set as `t`.

        speed_df (pd.DataFrame): speed data frame, where each activity (
            `offload`, `traversal`, `collect`...) are assigned a speed.
        """
        self.solution = pd.merge(self.solution, speed_df, how='left')
        self.solution = self.solution.sort_values(['index'])
        self.solution['activity_duration'] = self.solution['activity_time'] \
                                             / self.solution['activity_speed']
        offloads = self.solution['activity_type'] == 'offload'
        self.solution.loc[offloads, 'activity_duration'] = \
            self.solution.loc[offloads]['activity_speed']
        self.solution['t'] = self.solution.groupby(['route'])[
            'activity_duration'].cumsum().round()

    def add_time_formatted(self,
                           start_time='2020-06-14 08:00:00',
                           t_col='t',
                           t_units='s',
                           tz=None,
                           ):
        """Add formatted time column

        Args:
            start_time (str): start time as string (Y-m-d H:M:S)
            t_col (str): column to use to calculate the time, such as
                `cum_time` or `t`.
            t_units (str): time units, s: seconds, m: minutes...
            tz (str): time-zone to use, if any`
        """
        self.solution['time'] = start_time
        self.solution['time'] = pd.to_datetime(self.solution['time'])
        if tz:
            self.solution['time'] = self.solution['time'].dt.tz_localize(
                None).dt.tz_localize('Asia/Singapore')
        self.solution['time'] = self.solution['time'] + pd.to_timedelta(
            self.solution[t_col], unit=t_units)

    def add_constant_duration_time(self,
                                   start_time='2020-06-14 08:00:00',
                                   duration=1,
                                   t_units='m'):
        """Add fake time with each activity assigned a constant duration.

        Args:
            start_time (str): start time as string (Y-m-d H:M:S)
            duration (int): duration of each activity.
            t_units (str): time units, s: seconds, m: minutes...
        """
        self.solution['time_const_dur'] = start_time
        self.solution['time_const_dur'] = pd.to_datetime(self.solution[
                                                             'time_const_dur'])
        duration = list(range(len(self.solution))) * duration
        sol_temp = self.solution.copy()
        sol_temp['duration'] = duration
        route_dur = sol_temp.groupby(['route']).agg(min_dur=('duration',
                                                             'min')).reset_index()
        sol_temp = pd.merge(sol_temp, route_dur)
        sol_temp['duration'] = sol_temp['duration'] - \
                                    sol_temp['min_dur']
        sol_temp = sol_temp.sort_values(['index'])
        sol_temp = sol_temp['duration'].values
        self.solution['time_const_dur'] = self.solution['time_const_dur'] + \
                                          pd.to_timedelta(sol_temp,
                                                          unit=t_units)

    def simplify_output(self, keep=None, keep_additional=None):
        """Simplify the output for display purposes

        Args:
            keep (list <str>): core columns to keep, with defaults.
            keep_additional (list <str>): additional columns to keep.
        """

        if keep is None:
            keep = ['index',
                    'route',
                    'subroute',
                    'activity_type',
                    'activity_time',
                    'activity_demand',
                    'cum_demand',
                    'cum_time',
                    'remaining_capacity',
                    'remaining_time',
                    'geometry',
                    'highway',
                    'name']

        if keep_additional is not None:
            keep += keep_additional

        self.solution = self.solution[keep]

        self.solution['activity_type'] = self.solution[
            'activity_type'].str.replace('depot_start', 'depot')
        self.solution = self.solution.loc[~self.solution[
            'activity_type'].isin(['arrive_if', 'depart_if'])]
        self.solution['activity_type'] = self.solution[
            'activity_type'].str.replace('depot_end', 'depot')
        self.solution['activity_type'] = self.solution[
            'activity_type'].str.replace('arrive_if', 'offload')
        self.solution['activity_type'] = self.solution[
            'activity_type'].str.replace('depart_if', 'offload')

    def prettify_columns_dist(self,
                              rename_values=None,
                              distance_units='m',
                              demand_units='kg'):
        """Prettify column names when cost is distance.

        Args:
            rename_values (dict <str:str>): from and to names.
            distance_units (str): units for distance.
            demand_units (str): units for demand.
        """

        if rename_values is None:
            rename_values = {'route': 'Vehicle ID',
                             'subroute': 'Sub-route',
                             'activity_type': 'Activity',
                             'activity_time': 'Distance ({})'.format(
                                 distance_units),
                             'activity_demand': 'Demand ({})'.format(
                                 demand_units),
                             'cum_demand': 'Total demand collected on '
                                           'sub-route '
                                           '({})'.format(demand_units),
                             'remaining_capacity': 'Remaining capacity '
                                                   '({})'.format(demand_units),
                             'cum_time': 'Total distance travelled '
                                         '({})'.format(distance_units),
                             'remaining_time': 'Remaining distance capacity '
                                               '({})'.format(distance_units),
                             'highway': 'Road-type',
                             'name': 'Name (road or location)',
                             'time': 'Time',
                             'time_const_dur': 'Time (cons dur)'}
        self.solution = self.solution.rename(columns=rename_values)

    def add_distance_columns(self):
        """Add distance columns based on `length` of arcs"""
        self.solution['distance'] = self.solution['length']
        self.solution['distance'] = self.solution['distance'].fillna(0)
        self.solution['cum_distance'] = self.solution.groupby(['route'])[
            'length'].cumsum()
        self.solution['cum_distance'] = self.solution['cum_distance'].fillna(0)
        self.solution['cum_distance'] = self.solution[
                                            'cum_distance'].astype(int)

    def add_bin_columns(self):
        """Add bins served columns"""
        self.solution['cum_bins'] = self.solution.groupby(['route'])[
            'bins'].cumsum()
        self.solution['bins'] = self.solution['bins'].fillna(0)
        self.solution['bins'] = self.solution['bins'].astype(int)

    def prettify_columns_time(self,
                              rename_values=None,
                              time_units='sec',
                              demand_units='kg'):
        """Prettify column names when cost is distance.

        Args:
            rename_values (dict <str:str>): from and to names.
            distance_units (str): units for distance.
            demand_units (str): units for demand.
        """

        if rename_values is None:
            rename_values = {'route': 'Vehicle ID',
                             'subroute': 'Sub-route',
                             'activity_type': 'Activity',
                             'activity_time': 'Duration ({})'.format(
                                 time_units),
                             'distance': 'Activity distance (m)',
                             'activity_demand': 'Demand ({})'.format(
                                 demand_units),
                             'bins': 'Bins served',
                             'cum_demand': 'Total demand collected on '
                                           'sub-route '
                                           '({})'.format(demand_units),
                             'cum_bins': 'Total bins served',
                             'remaining_capacity': 'Remaining capacity '
                                                   '({})'.format(demand_units),
                             'cum_time': 'Total duration of route '
                                         '({})'.format(time_units),
                             'remaining_time': 'Remaining time available '
                                               '({})'.format(time_units),
                             'cum_distance': 'Total distance travelled (m)',
                             'highway': 'Road-type',
                             'name': 'Name (road or location)',
                             'time': 'Time',
                             'time_const_dur': 'Time (cons dur)'}
        self.solution = self.solution.rename(columns=rename_values)

    def prepare_solution(self):
        """Prepare solution file. A bunch of other stuff can be done in
        addition to this"""
        self._merge_solution()

    def write_solution(self, file):
        """Write the solution file.

        Arg:
            file (str): output file to write to.
        """

        self.solution.to_csv(file, index=False)


def summarise_routes(df):
    """Summarise the solution dictionary, generating stats per route.
    """
    summary = df.groupby(['Vehicle ID']).agg(
        properties_served=('Demand (kg)', 'sum'),
        distance_travelled=('Activity distance (m)', 'sum'),
        start=('Time', 'min'),
        end=('Time', 'max'),
        duration_h=('Duration (seconds)', 'sum'),
        bins_served=('Bins served', 'sum')).reset_index()

    summary['duration'] = summary['end'] - summary['start']
    summary['duration'] = summary['duration']  # .astype('timedelta64[h]')
    summary['duration'] = summary['duration'].astype(str).str[-18:-10]
    summary['distance_travelled'] = summary['distance_travelled'] / 1000
    summary['distance_travelled'] = summary['distance_travelled'].round(2)
    summary['duration_h'] = (summary['duration_h'] / 3600).round(2)

    summary = summary.rename(columns={'duration': 'Route duration (h:m:s)',
                                      'duration_h': 'Route duration (h)',
                                      'properties_served': 'Total demand collected (kg)',
                                      'start': 'Start date and time',
                                      'end': 'End date and time',
                                      'distance_travelled': 'Total distance travelled (km)',
                                      'bins_served': 'Total bins served'})
    summary = summary[
        ['Vehicle ID', 'Total demand collected (kg)', 'Total bins served',
         'Total distance travelled (km)', 'Route duration (h)',
         'Route duration (h:m:s)']]

    return summary


def summarise_routes_and_activities(df):
    """Summarise the route with columns linked to activities"""
    full_sum = summarise_routes(df)
    service_sum = summarise_routes(df.loc[df['Activity'] == 'collect'])
    service_sum = service_sum[['Vehicle ID', 'Total distance travelled (km)',
                               'Route duration (h)']]

    new_cols = ['Vehicle ID',
                'Service total distance travelled (km)',
                'Service duration (h)']
    service_sum.columns = new_cols

    travel_sum = summarise_routes(df.loc[df['Activity'] != 'collect'])
    travel_sum = travel_sum[['Vehicle ID', 'Total distance travelled (km)',
                             'Route duration (h)']]
    new_cols = ['Vehicle ID',
                'Non-service total distance travelled (km)',
                'Non-service duration (h)']
    travel_sum.columns = new_cols

    full_sum = full_sum.merge(service_sum)
    full_sum = full_sum.merge(travel_sum)
    full_sum = full_sum.sort_values(['Vehicle ID'])

    return full_sum
