# -*- coding: utf-8 -*-
"""Transform an OSMNX graph-generated geo-dataframe into a raw txt file that
can be imported using the solvers.

History:
    Created on 12 June 2020
    @author: Elias J. Willemse
    @contact: ejwillemse@gmail.com
"""

import pandas as pd
import numpy as np
from pprint import pprint


class PrepareGraph:
    """Prepare the full pandas data-frame graph, to make it compatible with
    MCARPTIF solver.
    """

    def __init__(self, df_graph):
        """Key input data is the full network graph.

        Args:
            df_graph (pd.DataFrame): data-frame of full network.
        """
        self._df_graph = df_graph.copy()
        self.u_key = None
        self.v_key = None
        self.oneway_key = None
        self._keys = None

        self._parallel_arcs = True

    def _set_keys(self):
        """Combine all keys into lists with expected types."""
        self._keys = {'u_key': [self.u_key, int],
                      'v_key': [self.v_key, int],
                      'oneway_key': [self.oneway_key, bool]}

    def set_graph_parameters(self,
                             u_key='u',
                             v_key='v',
                             oneway_key='oneway'):
        """Set variable names for arc data frames

        Args:
            u_key (str): column name of start node of arcs. Default 'u' is
                from osmnx.
            v_key (str): column name of end node of arcs. Default 'v' is
                from osmnx.
            oneway_key (str): column name bool of whether street is oneway (
            True or 1) or not (False or 0). Default 'oneway' is
                from osmnx.
        """
        self.u_key = u_key
        self.v_key = v_key
        self.oneway_key = oneway_key
        self._set_keys()  # combine keys into list for dtype checking

    def convert_to_int(self):
        """Convert all non-bool data columns into int"""
        for key_name, key_value in self._keys.items():
            key_value, type_expect = key_value
            if type_expect == int:
                self._df_graph[key_value] = self._df_graph[key_value].astype(int)

    def test_columns(self):
        """Check if data columns exist.

        Raise:
            NameError: data column is not found.
        """
        column_not_found = []
        frame_columns = self._df_graph.columns
        if self.u_key not in frame_columns:
            output = 'Data column `{}` not found in edges frame'.format(
                self.u_key)
            column_not_found.append(output)

        if self.v_key not in frame_columns:
            output = 'Data column `{}` not found in edges frame'.format(
                self.v_key)
            column_not_found.append(output)

        if self.oneway_key not in frame_columns:
            output = 'Data column `{}` not found in edges frame'.format(
                self.oneway_key)
            column_not_found.append(output)

        if column_not_found:
            pprint(column_not_found)
            raise TypeError('Columns not found.')

    def test_dtype(self):
        """Check if data in columns are compatible for MCARPTIF solution
        reader. Requirements are that all columns should be integer, except
        oneway which should be bool.

        Raise:
            TypeError: data columns is not of integer type.
        """
        def check_frame(key, df, error_list):
            key, type_expect = key
            key_type = df[key].dtypes
            if key_type != type_expect:
                out = '`{}` ({}) not of type {}'.format(key,
                                                        key_type,
                                                        type_expect)
                error_list.append(out)

        type_errors = []
        for key_name, key_value in self._keys.items():
            check_frame(key_value, self._df_graph, type_errors)

        if type_errors:
            pprint(type_errors)
            raise TypeError('Columns of wrong type')

    def _test_for_parallel_arcs(self):
        """Test whether there are any parallel arcs"""
        u, v = self.u_key, self.v_key
        duplicates = self._df_graph.duplicated(subset=[u, v], keep=False)
        n_parallel = len(self._df_graph.loc[duplicates])
        if len(n_parallel) > 1:
            self._parallel_arcs = True
        else:
            self._parallel_arcs = False

    def _extend_parallel(self):
        """Find arcs and edges with same start and end-nodes (arcs-ids) create
        connected dummy nodes and arcs for them. New `u_orig, v_orig`
        columns are created to keep track of where the dummy arcs where
        assigned and where they came from.

        Args:
            osm_key (bool): whether the osm_key is present to help keep track
                of parallel arcs for latter visualisation and to assign demand
                etc. to the right arcs and edges.

        The easiest way to explain this is that we assign a new (u, v) ids
        for the first parallel arc. This arc is not connected to the graph.
        To connect it, we create a zero length/demand arc out from u to u' and
        then back in from v' to v. To check the logic, it helps a lot
        just make the dummy u and v negative. If u or v is zero, or if there
        are negative keys, the code will break. So a max key value is
        added.
        """
        u, v = self.u_key, self.v_key

        # keep track of the original nodes.
        self._df_graph[[u + '_orig', v + '_orig']] = self._df_graph[[u, v]]

        max_key = max(self._df_graph['u'].max(), self._df_graph['v'].max())
        min_key = min(self._df_graph['u'].min(), self._df_graph['v'].min())

        # find all parallel arcs
        duplicates = self._df_graph.duplicated(subset=[u, v], keep=False)
        df_dups = self._df_graph.loc[duplicates].copy()

        # find first occurrence of parallel arcs
        dup_inter = df_dups.duplicated(subset=[u, v])
        df_dup_inter = df_dups.loc[dup_inter].copy()

        # create new dummy nodes
        dummy_keys = df_dup_inter['key']
        u_nodes = df_dup_inter[u].copy()
        v_nodes = df_dup_inter[v].copy()
        u_dummy = u_nodes + max_key
        v_dummy = v_nodes + max_key

        # these are new dummy arcs to be a added to reconnect the parallel
        # arcs with new nodes back to the graph. They won't have original
        # nodes.
        new_arcs_u = u_nodes.append(v_dummy)
        new_arcs_v = u_dummy.append(v_nodes)
        dummy_arcs = pd.DataFrame.from_dict({u: new_arcs_u, v: new_arcs_v})

        # these are all the parallel arcs, with their nodes updated.
        df_dups = pd.concat([df_dups, dummy_arcs])

        # We combine them back into the original data frame. We can use the
        # orig node to keep track of which are the original ones.
        self._df_graph = pd.concat([self._df_graph.loc[~duplicates].copy(),
                                    df_dups])

    def _create_arc_ids(self, u=None, v=None, arc_id=None, key_id=None):
        """Create arc keys. Note that where nan u and v are filled with
        zeros, the resulting key will have 0 in places, which may represent an
        actual arc key for another arc.

        Args:
            replace_nan_val (int): value to replace NaN u's and v's
        """
        if u is None:
            u = self.u_key
        if v is None:
            v = self.v_key
        if arc_id is None:
            arc_id = 'arc_id'

        u_ids = self._df_graph[u].fillna(0).astype(int).astype(str)
        v_ids = self._df_graph[v].fillna(0).astype(int).astype(str)
        self._df_graph[arc_id] = u_ids + '-' + v_ids
        if key_id is not None:
            key = self._df_graph[key_id].fillna(0).astype(int).astype(str)
            self._df_graph[arc_id] = self._df_graph[arc_id] + '-' + key

        na_keys = self._df_graph[u].isna() | self._df_graph[v].isna()
        if key_id is not None:
            na_keys = na_keys | self._df_graph[key_id].isna()
        self._df_graph.loc[na_keys, arc_id] = np.nan

    def _create_ordered_ids(self, nan_oneway_fill_val=False):
        """Create key-pairs, 'u-v', ordered for edges, unordered for
        arcs. Requires `arc_id` through `self._create_arc_ids`

        Args:
            nan_oneway_fill_val (bool): value to fill the oneway column with.
        """
        def ordered_key(df_frame):
            u_val, v_val = df_frame[u], df_frame[v]
            u_ord = min(u_val, v_val)
            v_ord = max(u_val, v_val)
            edge_key_ordered = '{}-{}'.format(u_ord, v_ord)
            return edge_key_ordered

        u, v, oneway = self.u_key, self.v_key, self.oneway_key

        self._df_graph[oneway] = self._df_graph[oneway].fillna(
            value=nan_oneway_fill_val)

        self._df_graph['arc_id_order'] = self._df_graph.apply(ordered_key,
                                                              axis=1)
        one_ways = self._df_graph[oneway] == True
        self._df_graph.loc[one_ways, 'arc_id_order'] = self._df_graph.loc[
            one_ways]['arc_id']


class CreateMcarptifFormat:
    """Transform geo-data-frames into MCARPTIF raw text format."""

    def __init__(self, df_graph, df_graph_req):
        """Key input data is the full network graph and required network graph.
        They are split for the workflow where the required graph is
        split, updated with changes to demand, service time, etc.

        Args:
            df_graph (pd.DataFrame): data-frame of full network.
            df_graph_req (pd.DataFrame): data-frame with required edges.
        """
        self._df_graph = df_graph.copy()
        self._df_graph_req = df_graph_req.copy()

        self.u_key = None
        self.v_key = None
        self.oneway_key = None
        self.demand_key = None
        self.service_time_key = None
        self.travel_time_key = None
        self._keys = None

    def _set_keys(self):
        """Combine all keys into lists with expected types."""
        self._keys = {'u_key': [self.u_key, int],
                      'v_key': [self.v_key, int],
                      'oneway_key': [self.oneway_key, bool],
                      'travel_time_key': [self.travel_time_key, int]}

        self._req_keys = {'demand_key': [self.demand_key, int],
                          'service_time_key': [self.service_time_key, int]}

    def set_graph_parameters(self,
                             u_key='u',
                             v_key='v',
                             demand_key='demand',
                             oneway_key='oneway',
                             service_time_key='length',
                             travel_time_key='length'):
        """Set variable names for arc data frames

        Args:
            u_key (str): column name of start node of arcs. Default 'u' is
                from osmnx.
            v_key (str): column name of end node of arcs. Default 'v' is
                from osmnx.
            oneway_key (str): column name bool of whether street is oneway (
            True or 1) or not (False or 0). Default 'oneway' is
                from osmnx.
            demand_key (str): column name of demand of required arcs and edges.
            service_time_key (str): column name of service time of required
                arcs and edges.
            travel_time_key (str): column name of travel time of all
                arcs and edges.
        """
        self.u_key = u_key
        self.v_key = v_key
        self.oneway_key = oneway_key
        self.demand_key = demand_key
        self.service_time_key = service_time_key
        self.travel_time_key = travel_time_key
        self._set_keys()  # combine keys into list for dtype checking

    def test_columns_exist(self):
        """Check if data columns exist.

        Raise:
            NameError: data column is not found.
        """
        def check_frame(key, columns, error_list):
            output = None
            if key not in columns:
                output = 'Data column `{}` not found in edges frame'.format(
                    key_value[0])
                error_list.append(output)

        not_found_error = []
        frame_columns = self._gdf_graph.columns
        frame_columns_req = self._gdf_graph_req.columns
        for key_name, key_value in self._keys.items():
            check_frame(key_value[0], frame_columns, not_found_error)
            check_frame(key_value[0], frame_columns_req, not_found_error)

        for key_name, key_value in self._req_keys.items():
            check_frame(key_value[0], frame_columns_req, not_found_error)

        if not_found_error:
            pprint(not_found_error)
            raise TypeError('Columns not in data frame')

    def test_dtype(self):
        """Check if data in columns are compatible for MCARPTIF solution
        reader. Requirements are that all columns should be integer, except
        oneway which should be bool.

        Raise:
            TypeError: data columns is not of integer type.
        """
        def check_frame(key, df, error_list):
            key, type_expect = key
            key_type = df[key].dtypes
            if key_type != type_expect:
                out = '`{}` ({}) not of type {}'.format(key,
                                                        key_type,
                                                        type_expect)
                error_list.append(out)

        type_errors = []
        for key_name, key_value in self._keys.items():
            check_frame(key_value, self._df_graph, type_errors)
            check_frame(key_value, self._df_graph_req, type_errors)

        for key_name, key_value in self._req_keys.items():
            check_frame(key_value, self._df_graph_req, type_errors)

        if type_errors:
            pprint(type_errors)
            raise TypeError('Columns of wrong type')

    def convert_to_int(self):
        """Convert all non-bool data columns into int"""
        for key_name, key_value in self._keys.items():
            key_value, type_expect = key_value
            if type_expect == int:
                self._df_graph_non_req[key_value] = \
                    self._gdf_graph_non_req[key_value].astype(int)
                self._gdf_graph_req[key_value] = \
                    self._gdf_graph_req[key_value].astype(int)

        for key_name, key_value in self._req_keys.items():
            key_value, type_expect = key_value
            if type_expect == int:
                self._gdf_graph_req[key_value] = \
                    self._gdf_graph_req[key_value].astype(int)

    def _create_ordered_ids_df(self, df):
        """Create key-pairs, 'u-v', ordered for edges, unordered for
        arcs.

        Args:
            df (pd.DataFrame): dataframe of edges to be assigned keys and
                ordered keys, for two-way streets.

        Return:
            df (pd.DataFrame): with u-v string `arc_id` column, and u-v ordered
                `arc_id_order` column
        """

        def ordered_key(df_frame):
            edge_key_ordered = '{}-{}'.format(min([df_frame[u], df_frame[v]]),
                                              max([df_frame[u], df_frame[v]]))
            return edge_key_ordered
        u, v, oneway = self.u_key, self.v_key, self.oneway_key
        df['arc_id'] = df[u].astype(str) + '-' + df[v].astype(str)
        df['arc_id_order'] = df.apply(ordered_key, axis=1)
        df.loc[df[oneway] == True, 'arc_id_order'] = df['arc_id']
        return df

    def _create_df_ids(self):
        """Create ids for required and non-required edges"""
        self._gdf_graph_req = self._create_ordered_ids_df(self._gdf_graph_req)
        self._gdf_graph_non_req = self._create_ordered_ids_df(
            self._gdf_graph_non_req)

    def _find_duplicates_ids(self, df):
        """Find all arcs and edges with duplicate IDs. One-ways are supposed
        to have only one id and two-way should have opposing arcs, so two-ids.

        Args:
            df (pd.DataFrame): dataframe to test.
        """
