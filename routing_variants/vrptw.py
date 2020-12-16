"""
Solving the Vehicle Routing Problem with Time Windows, using OR-tools and
the Open Source Routing Machine (OSRM).

See https://developers.google.com/maps/documentation/directions/overview#traffic-model
for examples on the OR-tools.

Details on OSRM can be found here.

See https://github.com/WasteLabs/OSRM-map-matching/blob/map_matching_full_data_return/docs/OSRM_alternative_setup.md
on setting up the routing engine.

Inputs are pandas dataframes and other parameters, including:

 * Facilities data frame, with the depot and disposal sites, and their
    operating times.
 * Pick-up locations, with time-windows, demand and service time.
 * Vehicle capacity.
 * Maximum route duration.

Facilities and pick-up locations also have lat-lon coordinate pairs.
"""
import os
import sys
import importlib
import logging

import pandas as pd
import geopandas as gpd
import numpy as np
import itertools
import requests
import json

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def return_seconds_from_midnight(df, time_col):
    time_prep = df_prep.PrepRouteGPS(df, city='Singapore')
    time_prep.df['time'] = time_prep.df[time_col]
    time_prep.standard_time_prep(time_col='time')
    return time_prep.df.t_midnight.values


class VrtpwSolver:
    """Solver for VRPTW"""

    def __init__(self, df_pickup, df_depot, root_str='http://localhost:8989'):
        """
        Args:
            df_pickup (df): pickup locations
            df_depot (df): depot locations
            root_str (str): root access point for OSRM
        """
        self.df_pickup = df_pickup.copy()
        self.df_depot = df_depot.copy()
        self.root_str = root_str
        self.depot_index = None
        self.time_matrix = None
        self.depot_start = None
        self.time_window_list = None

    def generate_time_matrix(self):
        """Generate shortest-time matrix between all locations."""
        depot = self.df_depot['lon'].round(5).astype(str) + ',' + \
            self.df_depot['lat'].round(5).astype(str)
        depot = depot.values.tolist()
        pickup = self.df_pickup['Longitude'].round(5).astype(str) + ',' + \
            self.df_pickup['Latitude'].round(5).astype(str)
        pickup = pickup.values.tolist()
        all_locations = depot + pickup
        self.depot_index = 0
        all_locations_str = ';'.join(all_locations)
        api_reqeust = self.root_str + '/table/v1/driving/' + all_locations_str
        results = requests.get(api_reqeust)
        results = results.json()
        self.time_matrix = results['durations']
        self.df_pickup['distance_index'] = self.df_pickup.index + 1
        self.df_depot['distance_index'] = 0

    def set_time_window_parameters(self, leave_depot, return_depot):
        """
        Args:
            leave_depot (int): time in seconds before soonest pickup that
                vehicles can leave the depot.
            return_depot (int): max route duration in seconds
        """
        time_window_df = self.df_pickup[['Time window start', 'Time window end', 'distance_index']].copy()
        no_end = time_window_df['Time window end'].isna()
        time_window_df[no_end, 'Time window end'] = time_window_df[no_end]['Time window start']
        time_window_df['start_sec'] = pd.to_datetime(time_window_df['Time window start']).astype(int) // 10 ** 9
        time_window_df['end_sec'] = pd.to_datetime(time_window_df['Time window end']).astype(int) // 10 ** 9

        earliest_pickup = time_window_df['start_sec'].min()
        latest_pickup = time_window_df['start_sec'].max()
        depot_start = earliest_pickup - leave_depot
        depot_start = int(depot_start)
        self.depot_start = depot_start
        depot_end = int(return_depot)

        time_window_df['start_sec_sd'] = time_window_df['start_sec'] - depot_start
        time_window_df['end_sec_sd'] = time_window_df['end_sec'] - depot_start

        start_time = getattr(time_window_df['start_sec_sd'], "tolist", lambda: start_time)()
        end_time = getattr(time_window_df['end_sec_sd'], "tolist", lambda: start_time)()

        time_window_list = [(0, depot_end)]
        self.time_window_list = time_window_list + list(zip(start_time, end_time))