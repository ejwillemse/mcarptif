import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from osmnx_network_extract.network_code import create_gdf
from osmnx_network_extract.network_code import required_arc_plot
import plotly.express as px
import cufflinks as cf
cf.go_offline(connected=True)
cf.set_config_file(colorscale='plotly', world_readable=True)


class RouteSummary:

    def __init__(self, network_info):
        self.collection_schedule = network_info.collection_schedule
        self.network_info = network_info
        self.cost_unit = 'h'
        self.cost_conv = 3600
        self.demand_unit = 'ton'
        self.demand_conv = 1000
        self.dist_unit = 'km'
        self.dist_conv = 1000
        self.solution_df = network_info.df_solution_full
        self.offload_table = network_info.offload_table_wide

        self.route_sum_columns = ['Route',
                                    '# offloads',
                                    'Demand collected (kg)',
                                    'Time collecting (h)',
                                    'Time travelling (h)',
                                    'Time at treatment facility (h)',
                                    'Route duration (h)']

        self.int_columns = None
        self.set_sum_column()
        self.solution_df_clean = None
        self.solution_df_geo = None
        self.offload = None
        self.depot = None

        self.ev_travel_demand = 1.2
        self.ev_service_demand = 2

    def set_ev_demand(self, non_service=1.2, service_demand=2):
        """Set EV demand formula """
        self.ev_travel_demand = non_service
        self.ev_service_demand = service_demand

    def extend_key_stats(self):
        self.prop_info = self.prop_info

    def set_sum_column(self):

        self.route_sum_columns = ['Route',
                                  'Offloads',
                                  'Bins collected',
                                  'Units served',
                                  'Demand collected ({})'.format(self.demand_unit),
                                  'Time collecting ({})'.format(self.cost_unit),
                                  'Time travelling ({})'.format(self.cost_unit),
                                  'Time at treatment facility ({})'.format(self.cost_unit),
                                  'Route duration ({})'.format(self.cost_unit),
                                  'Traveling distance ({})'.format(self.dist_unit),
                                  'Collecting distance ({})'.format(self.dist_unit),
                                  'Total route distance ({})'.format(self.dist_unit),
                                  'Electrical consumption (kWh)']

        if self.collection_schedule is not None:
            self.route_sum_columns.insert(1, 'Collection day')
            self.route_sum_columns.insert(0, 'Vehicle')


        self.int_columns = ['Route',
                            'Offloads',
                            'Bins collected',
                            'Units served',
                            'Vehicle']

    def route_summary(self):
        solution_df = self.solution_df.copy()
        solution_df_dist_travel = solution_df.loc[solution_df['activity_type'].isin(['travel'])]
        solution_df_dist_collect = solution_df.loc[solution_df['activity_type'].isin(['collect'])]

        solution_df_dist_travel = solution_df_dist_travel.groupby(['route']).agg(total_travel_dist=('length', 'sum')).reset_index()
        solution_df_dist_collect = solution_df_dist_collect.groupby(['route']).agg(total_collect_dist=('length', 'sum')).reset_index()

        solution_df = solution_df.loc[solution_df['activity_type'] != 'travel']
        activity_times = solution_df.groupby(['route', 'activity_type']).agg(total_time = ('activity_time', 'sum')).reset_index()
        activity_times_offload = activity_times.loc[activity_times['activity_type'] == 'offload'].reset_index(drop=True)
        activity_times_collect = activity_times.loc[
            activity_times['activity_type'] == 'collect'].reset_index(drop=True)

        activity_times_offload = activity_times_offload.rename(columns={'total_time': 'offload_time'})
        activity_times_collect = activity_times_collect.rename(columns={'total_time': 'collect_time'})

        route_summary = solution_df.groupby('route').agg(
            n_offloads=('subroute', 'nunique'),
            n_bins=('n_bins', 'sum'),
            n_units=('n_units', 'sum'),
            demand_collected=('activity_demand', 'sum'),
            travel_time=('total_traversal_time_to_activity', 'sum'),
            total_time=('cum_time', 'max')).reset_index()

        route_summary = pd.concat([route_summary,
                                   activity_times_collect[['collect_time']],
                                   activity_times_offload[['offload_time']],
                                   solution_df_dist_travel[['total_travel_dist']],
                                   solution_df_dist_collect[['total_collect_dist']]],
                                  axis=1)

        n_routes = route_summary['route'].nunique()
        route_summary['demand_collected'] = (route_summary['demand_collected'] / self.demand_conv)
        route_summary['offload_time'] = (route_summary['offload_time'] / self.cost_conv)
        route_summary['collect_time'] = (route_summary['collect_time'] / self.cost_conv)
        route_summary['total_time'] = (route_summary['total_time'] / self.cost_conv)
        route_summary['travel_time'] = (route_summary['travel_time'] / self.cost_conv)
        route_summary['total_travel_dist'] = (route_summary['total_travel_dist'] / self.dist_conv)
        route_summary['total_collect_dist'] = (route_summary['total_collect_dist'] / self.dist_conv)
        route_summary['total_dist'] = route_summary['total_travel_dist'] + route_summary['total_collect_dist']
        route_summary['ev_consumption'] = route_summary['total_travel_dist'] * self.ev_travel_demand + route_summary['total_collect_dist'] * self.ev_service_demand + route_summary['demand_collected'] * 1.5
        route_summary['route'] = route_summary['route'] + 1

        if self.collection_schedule is not None:
            route_summary['Vehicle'] = self.collection_schedule['Vehicle'].values
            route_summary['Collection day'] = self.collection_schedule['Collection day'].values

            route_summary = route_summary[['Vehicle', 'route', 'Collection day',
                                           'n_offloads', 'n_bins', 'n_units',
                                           'demand_collected', 'collect_time',
                                           'travel_time', 'offload_time',
                                           'total_time', 'total_travel_dist',
                                           'total_collect_dist', 'total_dist', 'ev_consumption']]
        else:
            route_summary = route_summary[['route', 'n_offloads', 'n_bins', 'n_units',
                                           'demand_collected', 'collect_time',
                                           'travel_time', 'offload_time',
                                           'total_time', 'total_travel_dist',
                                           'total_collect_dist']]

        route_summary.columns = self.route_sum_columns

        if self.offload_table is not None:
            route_summary = pd.merge(route_summary, self.offload_table, how='left')

        n_vehicles = route_summary['Vehicle'].nunique()
        route_summary = route_summary.append(route_summary.sum(numeric_only=True),
                                             ignore_index=True)
        n_rows = route_summary.shape[0]
        route_summary.loc[n_rows - 1, 'Vehicle'] = n_vehicles
        route_summary.loc[n_rows - 1, 'Route'] = n_routes
        route_summary = route_summary.reset_index()
        route_summary['index'] = ' '
        route_summary.iloc[-1, 0] = 'Total'
        route_summary = route_summary.round(2)
        route_summary = route_summary.rename(columns={'index': ''})

        route_summary.loc[:, self.int_columns] = route_summary[self.int_columns].astype(int)
        route_summary = route_summary.fillna('')

        return route_summary

    def subtrip_summary(self):
        solution_df = self.solution_df
        substrip_summary = solution_df.groupby(['route', 'subroute']).agg(
            demand_collected=('activity_demand', 'sum'),
            activity_time=('activity_time', 'sum'),
            travel_time=('total_traversal_time_to_activity', 'sum')).reset_index()

        substrip_summary['route'] = substrip_summary['route'] + 1
        substrip_summary['subroute'] = substrip_summary['subroute'] + 1
        substrip_summary['activity_time'] = (substrip_summary['activity_time'] / self.cost_conv)
        substrip_summary['travel_time'] = (substrip_summary['travel_time'] / self.cost_conv)
        substrip_summary['total_time'] = substrip_summary['travel_time'] + \
                                         substrip_summary['activity_time']
        substrip_summary = substrip_summary.round(2)
        return substrip_summary

    def route_trip_time_summary_bar(self):
        solution_df = self.solution_df
        solution_df = solution_df.groupby(['route', 'activity_type']).agg(activity_time=('activity_time', 'sum')).reset_index()
        solution_df['activity_time'] = solution_df['activity_time'] / self.cost_conv
        solution_df = solution_df.loc[solution_df['activity_type'].isin(['collect', 'travel', 'offload'])]
        solution_df.columns = ['Route', 'Activity', 'Activity time (h)']
        solution_df['Route'] = solution_df['Route'] + 1
        solution_df = solution_df.round(2)
        solution_df['Route'] = 'Route ' + solution_df['Route'].astype(int).astype(str)
        fig = px.bar(solution_df, x='Route', y='Activity time (h)', template='simple_white',  color="Activity",
                     width=1000, height=400, )

        return fig

    def route_trip_distance_summary_bar(self):
        solution_df = self.solution_df.copy()
        solution_df = solution_df.groupby(['route', 'activity_type']).agg(activity_distance=('length', 'sum')).reset_index()
        solution_df['activity_distance'] = solution_df['activity_distance'] / self.dist_conv
        solution_df = solution_df.loc[solution_df['activity_type'].isin(['collect', 'travel'])]
        solution_df.columns = ['Route', 'Activity', 'Activity distance (km)']
        solution_df['Route'] = solution_df['Route'] + 1
        solution_df = solution_df.round(2)
        solution_df['Route'] = 'Route ' + solution_df['Route'].astype(int).astype(str)
        fig = px.bar(solution_df, x='Route', y='Activity distance (km)', template='simple_white',  color="Activity",
                     width=1000, height=400, )

        return fig

    def clean_solution(self):
        solution_df = self.solution_df.copy()
        solution_df = solution_df.rename(columns={'activity_id': 'req_arc_index'})
        solution_df = solution_df.loc[solution_df['activity_type'] != 'depart_if']
        solution_df = solution_df.loc[solution_df['activity_type'] != 'depart_if']
        solution_df.loc[solution_df['activity_type'] == 'offload', 'total_traversal_time_to_activity'] = np.nan
        solution_df['total_traversal_time_to_activity'] = solution_df['total_traversal_time_to_activity'].fillna(method='ffill')
        solution_df = solution_df.loc[solution_df['activity_type'] != 'arrive_if']
        self.solution_df_clean = solution_df.copy()

    def geo_code_route(self):
        route_clean = self.solution_df_clean
        route_clean = route_clean.merge(self.network_info.main_arc_list, how='left',
                                        left_on='req_arc_index',
                                        right_on='req_arc_index')
        assert not route_clean['arc_index'].isna().any()
        route_clean = route_clean.merge(self.network_info.network, how='left',
                                        left_on='arc_index',
                                        right_on='arc_index')
        assert not route_clean['arc_id'].isna().any()
        self.solution_df_geo = create_gdf(route_clean.copy())
        self.offload = create_gdf(self.network_info.df_if)
        self.depot = create_gdf(self.network_info.df_depot)

    def plot_routes(self,
                    figsize=None,
                    linewidth_full=1,
                    linewidth_req=2.5):
        plot_solution = self.solution_df_geo
        plot_solution['route'] = 'Route ' + self.solution_df_geo['route'].astype(str)
        if figsize is None:
            figsize = (40, 40)
        fig, ax = plt.subplots(figsize=figsize)
        _ = self.network_info.df_required_arcs.plot(ax=ax, linewidth=linewidth_full)
        _ = plot_solution.plot(ax=ax,
                                      linewidth=linewidth_req,
                                      column='route',
                                      legend=True)
        _ = self.offload.plot(ax=ax,
                                   markersize=50,
                                   facecolor='red')
        _ = self.depot.plot(ax=ax,
                                    markersize=50,
                                   facecolor='red')
        return fig

    def decode_routes(self):
        routes = self.route_clean.copy()
