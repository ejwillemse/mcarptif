"""Module to extract MCARPTIF info from OSM and pytables
"""
import logging
import pandas as pd
import numpy as np
import tables as tb
from osmnx_network_extract.create_instance import create_arc_id
from converter.shortest_path import sp_full
from osmnx_network_extract.network_code import create_gdf, create_latlon_gdf

import matplotlib.pyplot as plt
import qgrid


class NetworkExtract:
    """Extract all network info in the format required for the MCARPTIF.

    As rules:
        * depot is always the first entry in the required arc list
        * thereafter, intermediate facilities
        * thereafter, required arcs and edges (sorted according to their arc
            index) so can be mixed.
        * only one arc orientation per edge is allowed
        * inverse arc orientations are included in the end of the full
        required arc list
        * each arc is assigned a type:
            `depot`, `offload`, `collection`
        * depot and offload facilities do not have inverse arcs (though I
        think they can have).
        * All time units should be in seconds (it can be anything,
        but seconds work well.)
        * Any speed based units should be per meter, because of open-street
        and the cost matrix which is in meters.
        * This is a hard rule if OSM was use.
    """

    def __init__(self,
                 network,
                 arc_h5_path,
                 round_cost=True,
                 length_int=True):
        """
        Arg:
            network (df): full arc network.
            arc_h5_path (str): path to arc info h5 file, with shortest path
                info.
            round_cost (bool): whether costs should be rounded to integers.
                Can causse issues with cost testing later.
            length_int (bool): convert arc length into integer
        """
        self.network = network.copy()
        if length_int:
            self.network['length'] = self.network['length'].astype(int)
        self.arc_h5_path = arc_h5_path
        self.round_cost = round_cost

        self.df_inv_list = None
        self.df_edges = None
        self.df_arcs = None

        self.create_inv_list()

        self.df_depot = None
        self.df_if = None

        self.depot_arc_index = None
        self.if_arc_index = None

        self.depotnewkey = None
        self.IFarcsnewkey = None

        self.df_required_arcs = None
        self.df_required_arcs_full = None
        self.df_required_arc_index_orig = None

        self.req_inv_list_full = None
        self.reqArcList = None
        self.reqArcListActual = None
        self.reqInvArcList = None
        self.d = None  # meter (initially)
        self.d_np_req_orig = None  # meter (initially)

        self.reqEdgesPure = None
        self.reqArcsPure = None

        self.n_ifs = 0
        self.n_dummy = 0
        self.dummy_req_indices = None

        self.main_arc_list = None

        self.if_cost_np_orig = None  # meters without offload costs
        self.if_cost_np = None  # seconds
        self.if_arc_np = None

        self.offload_cost = 0  # seconds
        self.dumpCost = 0
        self.travel_speed = 1  # m/s

        self.df_service_cost = None
        self.df_demand = None

        self.serveCostL = None
        self.demandL = None

        self.nn_list = None

        self.min_capacity = 0
        self.min_duration = 0

        self.capacity = None
        self.maxTrip = None

        self.df_solution = None

        self.prop_info = None
        self.prop_info_extended = None

        self.df_solution = None
        self.df_solution_full = None

    def create_inv_list(self):
        """Create an inverse arc list for the network arcs. We limit it to
        arcs with 'oneway' is True, and that are not circular, i.e. with the
        same start and end points. Only one of these are in the road network.
        But they will get flagged as reversable.
        """
        logging.info('Creating inverse arc list')
        network = self.network
        circle = network['u'] == network['v']
        edges_flag = (network['oneway'] == False) & (circle == False)
        edges_inv = network.copy().loc[edges_flag][['u', 'v', 'oneway',
                                                 'arc_index', 'arc_id_ordered']]
        edges_key = network.copy().loc[edges_flag][['u', 'v', 'oneway', 'arc_index', 'arc_id', 'arc_id_ordered']]
        edges_inv = create_arc_id(edges_inv, 'arc_id', 'v', 'u')
        logging.info('Number of edges: {}'.format(edges_inv.shape[0]))

        edges_list = pd.merge(edges_key[['arc_index', 'arc_id']],
                            edges_inv[['arc_index', 'arc_id']],
                            left_on=['arc_id'], right_on=['arc_id'])
        logging.info('Edges with inverse pairs: {}'.format(edges_list.shape[0]))
        edges_list = edges_list[['arc_index_x', 'arc_index_y']].copy()
        edges_list.columns = ['arc_index', 'arc_index_inv']

        arcs = network.loc[~network['arc_index'].isin(edges_list['arc_index'])]
        arcs_index = arcs[['arc_index']]
        logging.info('Number of arcs: {}'.format(arcs_index.shape[0]))

        inv_list_full = pd.concat([edges_list, arcs_index]).sort_values([
            'arc_index'])
        inv_list_full = inv_list_full.reset_index(drop=True)

        self.df_inv_list = inv_list_full.copy()
        self.df_edges = edges_list.copy()
        self.df_arcs = arcs_index.copy()

    def load_required_arcs(self, required_arcs, merge_network=True):
        """Load required arcs. Should not contain both arcs of an edge
        (will raise a worning if it does)
        """
        logging.info('Load required arcs')
        if required_arcs['arc_index'].isin(self.network['arc_index']).all() \
                is False:
            logging.error('Required arcs are not in network.')
            raise ValueError()

        if merge_network is True:
            logging.info('Merging with the network')
            required_arcs = required_arcs.merge(self.network, how='left')

        if required_arcs.duplicated(['arc_id_ordered']).any() is True:
            logging.warning('Required network contains both sides of edges, '
                            'it should contain only one.')

        self.df_required_arcs = required_arcs.copy()
        self.df_required_arcs['arc_type'] = 'collection'
        self.df_required_arcs = self.df_required_arcs.sort_values('arc_index')
        self.df_required_arc_index_orig = self.df_required_arcs['arc_index'].copy()

    def set_depot_arc(self, depot_arc_index):
        """Set depot arc info"""
        logging.info('Set depot')
        self.df_depot = self.network.loc[self.network['arc_index'] ==
                                         depot_arc_index].iloc[[0]].copy()
        self.df_depot['arc_type'] = 'depot'
        self.depotnewkey = 0
        self.n_dummy = 1
        self.depot_arc_index = depot_arc_index

    def set_if_arcs(self, if_arc_index):
        """Set if arc info"""
        logging.info('Set offload facilities')
        self.df_if = self.network.loc[self.network['arc_index'].isin(
            if_arc_index)].copy()
        self.df_if['arc_type'] = 'offload'
        # depot always has index 0
        self.n_ifs = self.df_if.shape[0]
        self.n_dummy = self.n_ifs + 1
        self.IFarcsnewkey = np.array(range(self.n_ifs)) + 1
        self.if_arc_index = if_arc_index
        self.dummy_req_indices = np.array(list(range(self.n_dummy)))

    def loc_in_required_arcs(self):
        """Lock in required arcs, excluding opposing edge directions."""
        self.df_required_arcs_full = pd.concat([self.df_depot,
                                                self.df_if,
                                                self.df_required_arcs])
        self.df_required_arcs_full = self.df_required_arcs_full.reset_index(
            drop=True)
        self.df_required_arcs_full['req_arc_index'] = \
            self.df_required_arcs_full.index

    def extend_required_inverse_arcs(self):
        """Extend required arcs with their inverse arcs."""
        logging.info('Extend required arcs with inverse edge arcs')
        req_arcs_pure = self.df_required_arcs_full.loc[self.df_required_arcs_full['arc_type'] ==
                                                       'collection'].copy()
        req_arcs_full = req_arcs_pure.merge(self.df_inv_list, how='left')
        req_list = req_arcs_pure['arc_index']
        inverse_list = req_arcs_full['arc_index_inv'].dropna()
        full_list = pd.concat([req_list, inverse_list])
        full_list = full_list.astype(int).values
        req_inv_list = pd.DataFrame({'arc_index': full_list,
                                     'arc_index_inv': self.df_inv_list.iloc[full_list]['arc_index_inv'].values})

        req_inv_list['req_arc_index'] = req_inv_list.index + self.n_dummy
        req_inv_list_pure = req_inv_list[['req_arc_index', 'arc_index_inv']]
        req_inv_list_pure.columns = ['req_arc_index_inv', 'arc_index']
        req_inv_list_pure = req_inv_list_pure.dropna().astype(int)

        req_inv_list = req_inv_list.merge(req_inv_list_pure, how='left')

        dummy_index = np.concatenate([[self.depot_arc_index],
                                       self.if_arc_index])
        dummy_req_arc_index = self.dummy_req_indices

        dummy_inv_list = pd.DataFrame({'arc_index': dummy_index,
                                       'req_arc_index': dummy_req_arc_index})

        req_inv_list_full = pd.concat([dummy_inv_list, req_inv_list])

        req_inv_list_full = req_inv_list_full.replace({np.nan: None})
        req_inv_list_full = req_inv_list_full[['arc_index', 'arc_index_inv',
                                     'req_arc_index', 'req_arc_index_inv']]
        req_inv_list_full = req_inv_list_full.reset_index(drop=True)
        req_inv_list_info = req_inv_list_full['req_arc_index_inv'].values

        self.req_inv_list_full = req_inv_list_full.copy()

        self.reqArcList = req_inv_list_full['arc_index'].copy().values

        self.reqArcListActual = req_inv_list['req_arc_index'].copy().values

        orig = req_inv_list.loc[req_inv_list['arc_index'].isin(
            self.df_required_arc_index_orig)]

        self.reqEdgesPure = orig.dropna(subset=['arc_index_inv'])[
            'req_arc_index'].values.copy()

        self.reqArcsPure = orig.loc[orig['arc_index_inv'].isna()][
            'req_arc_index'].values.copy()

        req_inv_list_info = [int(x) if x is not None else None for x in
                             req_inv_list_info]

        self.reqInvArcList = req_inv_list_info

        self.create_main_arc_list()

    def create_main_arc_list(self):
        """Main arc list to be used for setting demand and service costs.

        Arg:
            check_errors (bool): few basic error checks.
        """
        self.main_arc_list = self.req_inv_list_full.copy()
        self.main_arc_list = self.main_arc_list.replace({None: -1}).astype(int)
        self.main_arc_list['arc_category'] = 'required_edge_inverse'
        self.main_arc_list.loc[self.depotnewkey, 'arc_category'] = 'depot'
        self.main_arc_list.loc[self.IFarcsnewkey, 'arc_category'] = 'offload'
        self.main_arc_list.loc[self.reqEdgesPure, 'arc_category'] = \
            'required_edge'
        self.main_arc_list.loc[self.reqArcsPure, 'arc_category'] = \
            'required_arc'
        self.main_arc_list.loc[self.reqArcsPure, 'arc_category'] = \
            'required_arc'

    def check_main_list(self):
        """Few basic error checks on the main list"""
        logging.info('Checking master list')
        depot = self.main_arc_list.loc[self.main_arc_list['arc_category'] ==
                                       'depot']
        ifs = self.main_arc_list.loc[self.main_arc_list['arc_category'] ==
                                       'offload']
        arcs = self.main_arc_list.loc[~self.main_arc_list['arc_category'].isin([
            'depot', 'offload'])]
        if depot.shape[0] > 1:
            logging.error('More than one depot')
            raise ValueError
        if depot['arc_index_inv'][0] != -1:
            logging.error('Depot cannot have inverse arc.')
            raise ValueError
        if ifs.duplicated(['arc_index']).any():
            logging.error('Duplicate offload facilities.')
            raise ValueError
        if (ifs['arc_index_inv'] != -1).any():
            logging.error('Offload cannot have inverse arc.')
            raise ValueError
        if arcs.duplicated(['arc_index']).any():
            logging.error('Duplicate required arcs.')
            raise ValueError

    def load_distance_matrix(self):
        """Load distance matrix."""
        temp_frame = self.reqArcList
        n_arcs = temp_frame.shape[0]
        logging.info('Load distance matrix: {} x {}'.format(n_arcs, n_arcs))
        temp_frame = pd.DataFrame({'reqArcList': temp_frame})
        temp_frame2 = temp_frame.copy().drop_duplicates(['reqArcList'])
        temp_frame2['index'] = temp_frame2.reset_index().index
        temp_frame = pd.merge(temp_frame, temp_frame2, how='left')
        unique_req_arcs = temp_frame2['reqArcList'].values
        redraw = temp_frame['index'].values

        with tb.open_file(self.arc_h5_path, 'r') as h5file:
            sp_info = h5file.root.shortest_path_info
            d_np_req = sp_info.cost_matrix[unique_req_arcs, :]
            d_np_req = d_np_req[:, unique_req_arcs]
            d_np_req = d_np_req[redraw, :]
            d_np_req = d_np_req[:, redraw]
        #d_np_req = d_np_req.copy().astype(int)
        self.d_np_req_orig = d_np_req.copy()
        self.d = self.d_np_req_orig.copy()
        logging.info('Creating nearest neighbour lists')
        self.nn_list = np.argsort(self.d_np_req_orig, axis=1)

    def offload_calculations(self):
        """Calculate best offload positions and facilities."""
        n_arcs = self.d.shape[0]
        logging.info('Calculate offloads: {} x {} x {}'.format(n_arcs,
                                                          n_arcs,
                                                          self.n_ifs))
        if_cost_np = np.full(self.d.shape, np.infty)
        if_arc_np = np.full(self.d.shape, 0)

        for j in range(n_arcs):
            if_cost_np[0][j] = self.d[0][j]  # note that an if visit
            # may be shorter here. This influences trip and vehicle
            # removals, if I'm not mistaken. A vehicle shouldn't want to
            # visit an arc right after starting it's route, unless it
            # carried waste.
            if_arc_np[0][j] = 0

        for k_if in self.IFarcsnewkey:
            for i in range(n_arcs):
                for j in range(n_arcs):
                    visitT = self.d[i][k_if] + \
                             self.d[k_if][j]
                    if visitT < if_cost_np[i][j]:
                        if_cost_np[i][j] = visitT
                        if_arc_np[i][j] = k_if
        self.if_cost_np_orig = if_cost_np.copy()
        self.if_arc_np = if_arc_np.copy()
        self.if_cost_np = self.if_cost_np_orig + self.offload_cost

    def offload_calculations3D(self):
        """Calculate best offload positions and facilities."""
        n_arcs = self.d.shape[0]
        logging.info('Calculate offloads: {} x {} x {}'.format(n_arcs,
                                                               n_arcs,
                                                               self.n_ifs))

        offload_costs = []
        for k_if in self.IFarcsnewkey:
            arc_to_if = self.d[:, k_if]
            if_to_arc = self.d[k_if, :]

            dist_x, dist_y = np.meshgrid(arc_to_if, if_to_arc)
            dist = dist_x + dist_y
            offload_costs.append(dist.T)

        np_offload_costs = np.dstack(offload_costs)
        if_cost_np_orig = np_offload_costs.min(axis=2)
        if_arc_np = np_offload_costs.argmin(axis=2)
        if_arc_np = if_arc_np + 1  # because depot

        if_cost_np_orig[0, :] = self.d[0, :]
        if_arc_np[0, :] = 0

        self.if_cost_np_orig = if_cost_np_orig.copy()
        self.if_arc_np = if_arc_np.copy()
        self.if_cost_np = self.if_cost_np_orig.copy() + self.offload_cost

    def set_travel_speed(self, travel_speed=1):
        """Set travel speed (m/s) and update required arc list.
        """
        self.travel_speed = travel_speed

    def set_offload_time(self, offload):
        """Set offload costs"""
        self.offload_cost = offload
        self.dumpCost = offload

    def update_cost_matrix(self):
        logging.info('Update travel durations.')
        self.d = self.d_np_req_orig.copy() / self.travel_speed
        if self.round_cost:
            self.d = self.d.astype(int)

    def update_offload_cost(self):
        logging.info('Update offload durations.')
        self.if_cost_np = self.if_cost_np_orig.copy() / self.travel_speed
        if self.round_cost:
            self.if_cost_np = self.if_cost_np.astype(int)
        self.if_cost_np = self.if_cost_np + self.offload_cost

    def set_inverse_values(self, df_value, col):
        """Set inverse values to required arcs. Typically includes 'demand'
        and 'service_cost"""

        if not df_value['arc_index'].isin(self.df_required_arcs['arc_index']).all():
            logging.error('Costs are included for arcs that are not required '
                          'to service.')
            raise ValueError

        if not self.df_required_arcs['arc_index'].isin(df_value['arc_index']).all():
            logging.error('Not all required arcs have been assigned a '
                          'service cost')
            raise ValueError

        df_value = df_value.copy()
        col_inv = col + '_inv'
        inv_arc_cost_full = self.main_arc_list.copy()
        inv_arc_cost_full = inv_arc_cost_full.merge(df_value, how='left')
        inv_arc_cost_full.loc[self.dummy_req_indices, col] = 0
        df_value[col+'_inv'] = df_value[col]
        df_value['arc_index_inv'] = df_value['arc_index']
        inv_arc_cost_full = inv_arc_cost_full.merge(df_value[['arc_index_inv', col_inv]], how='left')
        inv_cost_assign = ~inv_arc_cost_full[col_inv].isna()
        inv_arc_cost_full.loc[inv_cost_assign, col] = inv_arc_cost_full.loc[
            inv_cost_assign][col_inv]
        return inv_arc_cost_full

    def set_service_cost(self, df_service_cost):
        """Set service costs of required arcs.

        Arg:
            df_service_cost (dataframe): with 'arc_index', 'service_cost'
            column.

        Only required arcs should be included and only one of the arcs of
        edges. The one original loaded into the data frame.
        """
        logging.info('Setting service cost for network')
        self.df_service_cost = self.set_inverse_values(df_service_cost,
                                                       'service_cost').copy()
        self.serveCostL = self.df_service_cost['service_cost'].values.copy()

    def set_service_demand(self, df_demand):
        """Set demand of required arcs.

        Arg:
            df_demand (dataframe): with 'arc_index', 'demand'
            column.

        Only required arcs should be included and only one of the arcs of
        edges. The one original loaded into the data frame.
        """
        logging.info('Setting demand for network')
        self.df_demand = self.set_inverse_values(df_demand,
                                                 'demand')
        self.demandL = self.df_demand['demand'].values.copy()

    def set_service_cost_and_demand(self, df):
        """Set service and demand per arc"""
        self.set_service_cost(df)
        self.set_service_demand(df)

    def round_key_inputs(self):
        """Round key inputs for MCARPTIF solution files."""
        logging.info('Round key inputs')
        #self.df_service_cost['service_cost'] = self.df_service_cost[
        # 'service_cost'].astype(int)
        #self.serveCostL = self.df_service_cost['service_cost'].copy()
        #self.df_demand['demand'] = self.df_demand['demand'].astype(int)
        #self.demandL = self.df_demand['demand'].copy()
        #self.d = self.d.astype(int)
        #self.if_cost_np = self.if_cost_np.astype(int)

    def calc_min_duration_capacity(self):
        """Calculate the minimum route duration time and capacity"""
        demand = self.df_demand['demand'].values
        service = self.df_service_cost['service_cost'].values
        self.min_capacity = demand.max()
        req_arcs = self.reqArcListActual
        self.min_duration = self.d[0, req_arcs] + \
                            service[req_arcs] + self.if_cost_np[req_arcs, 0]
        self.min_duration = self.min_duration.max()

    def calc_min_capacity(self):
        """Calculate the minimum route capacity"""
        demand = self.df_demand['demand'].values
        self.min_capacity = demand.max()

    def calc_min_duration(self):
        """Calculate the minimum route duration time"""
        service = self.df_service_cost['service_cost'].values
        req_arcs = self.reqArcListActual
        self.min_duration = self.d[0, req_arcs] + \
                            service[req_arcs] + self.if_cost_np[req_arcs, 0]
        self.min_duration = self.min_duration.max()

    def set_vechile_capacity_constraint(self, capacity):
        """Set capacity of the vehicle"""
        self.calc_min_capacity()
        if capacity < self.min_capacity:
            logging.warning('Vehicle capacity limit is too low at {}'.format(
                capacity))
            logging.warning('Highest collection point demand is {}'.format(
                self.min_capacity))
        self.capacity = capacity

    def set_vehicle_duration_constraint(self, duration):
        """Set duration constraint of the vehicle"""
        self.calc_min_duration()
        if duration < self.min_duration:
            logging.warning('Vehicle duration limit is too short at {}'.format(
                duration))
            logging.warning('Longest collection point time, including travel '
                            'to, service, offload and travel back to the '
                            'depot is: '
                            '{}'.format(self.min_duration))
        self.maxTrip = duration

    def check_shapes(self):
        """Check shapes to spot errors"""
        d_shape = self.d.shape
        if_d_shape = self.if_cost_np.shape
        if_d_shape2 = self.if_arc_np.shape
        assert d_shape == if_d_shape == if_d_shape2

        n_req_arcs = self.reqArcList.shape[0]
        assert n_req_arcs == d_shape[0]

        n_demand_df = self.df_demand.shape[0]
        n_costs_df = self.df_service_cost.shape[0]
        assert n_req_arcs == n_demand_df == n_costs_df

        n_req_arcs = self.df_required_arcs.shape[0]
        n_edges_pure = self.reqEdgesPure.shape[0]
        n_req_arcs_pure = self.reqArcsPure.shape[0]
        n_req_arcs_actual = self.reqArcListActual.shape[0]
        n_ifs = self.IFarcsnewkey.shape[0]
        n_req_arcs_full = self.reqArcList.shape[0]

        assert n_req_arcs == (n_edges_pure + n_req_arcs_pure)
        assert n_req_arcs_actual == (2 * n_edges_pure + n_req_arcs_pure)
        assert n_req_arcs_full == (2 * n_edges_pure + n_req_arcs_pure) + self.n_dummy
        assert (n_req_arcs_actual + self.n_dummy) == n_req_arcs_full
        assert self.n_dummy == n_ifs + 1

    def extend_prop_info(self):
        """Extend all arc info to their inverse arcs. Here we heavily rely on
        'arc-id-ordered'."""
        prop_info_extended = self.prop_info.copy()
        network = self.network

        prop_info_extended = pd.merge(prop_info_extended,
                                      network[['arc_index', 'arc_id_ordered']],
                                      how='left',
                                      left_on='arc_index',
                                      right_on='arc_index')

        all_index = network.loc[network['arc_id_ordered'].isin(prop_info_extended['arc_id_ordered'])][['arc_index', 'arc_id_ordered']]
        prop_info_extended = prop_info_extended.drop(columns=['arc_index'])
        prop_info_extended = pd.merge(prop_info_extended, all_index,
                                                      how='left',
                                                      left_on='arc_id_ordered',
                                                      right_on='arc_id_ordered')

        prop_info_extended = self.main_arc_list.merge(prop_info_extended, how='left')
        self.prop_info_extended = prop_info_extended.copy()


    def network_gdf(self, producers=None):
        self.network_plot = self.network.copy()
        self.network_plot = create_gdf(self.network_plot, dropna_geom=True)
        if producers is None:
            self.df_required_arcs_plot = create_gdf(self.df_required_arcs, dropna_geom=True)
        else:
            self.df_required_arcs_plot = create_latlon_gdf(producers,
                                                    dropna_geom=True)

    def plot_required_arcs(self,
                           figsize=None,
                           linewidth_full=1,
                           linewidth_req=2.5):
        if figsize is None:
            figsize = (40, 40)

        fig, ax = plt.subplots(figsize=figsize)
        _ = self.network_plot.plot(ax=ax, linewidth=linewidth_full)
        _ = self.df_required_arcs_plot.plot(ax=ax, markersize=linewidth_req, color='red')

        
    def add_solution(self, df_solution, extend=True):
        """Add solution to network, and do a few quick modifications."""
        if extend:
            self.extend_prop_info()
        df_solution = df_solution.copy()
        df_solution = df_solution.rename(
            columns={'activity_id': 'req_arc_index'})
        df_solution = df_solution.merge(self.main_arc_list,
                                          left_on='req_arc_index',
                                          right_on='req_arc_index',
                                          how='left')
        df_solution = df_solution.loc[df_solution['activity_type'] != 'depart_if']
        df_solution.loc[df_solution['activity_type'] == 'offload', 'total_traversal_time_to_activity'] = np.nan
        df_solution['total_traversal_time_to_activity'] = df_solution['total_traversal_time_to_activity'].fillna(method='ffill')
        df_solution = df_solution.loc[df_solution['activity_type'] != 'arrive_if']
        df_solution = df_solution.merge(self.prop_info_extended, how='left')
        self.df_solution = df_solution.copy()

    def deconstruct_solution(self):
        """Fill shortest paths arc indices into solution and assign arc
        categories."""
        routes = self.df_solution
        routes['solution_index'] = routes.index
        frame_index = routes['solution_index'].values
        route_number = routes['route'].values
        arc_index = routes['arc_index'].values
        n_solution_arcs = routes.shape[0]
        routes['solution_group'] = frame_index

        filler_frames = []
        with tb.open_file(self.arc_h5_path, 'r') as h5file:
            sp_info = h5file.root.shortest_path_info
            p_full = sp_info.predecessor_matrix

            for i in range(1, n_solution_arcs - 1):
                arc_i = arc_index[i]
                arc_j = arc_index[i + 1]
                frame_i = frame_index[i]

                if route_number[i] == route_number[i + 1]:
                    sp_path = sp_full(p_full, arc_i, arc_j)
                    n_arcs = len(sp_path)
                    if n_arcs > 0:
                        new_index = frame_i + np.array(
                            range(1, n_arcs + 1)) / (n_arcs + 1)
                        new_arcs = np.array(sp_path)
                        temp_frame = pd.DataFrame({'solution_index': new_index,
                                                   'arc_index': new_arcs})
                        temp_frame['arc_category'] = 'travel'
                        temp_frame['activity_type'] = 'travel'
                        temp_frame['solution_group'] = frame_i
                        filler_frames.append(temp_frame.copy())
        travel_paths = pd.concat(filler_frames)
        routes_full = pd.concat([routes, travel_paths])
        routes_full = routes_full.sort_values(['solution_index'])
        routes_full[['route', 'subroute']] = routes_full[['route', 'subroute']].fillna(method='ffill')
        routes_full = routes_full.reset_index()
        routes_full = routes_full.drop(columns='solution_index')
        routes_full = routes_full.merge(self.network[['arc_index', 'geometry', 'length', 'maxspeed']], how='left')
        routes_full = create_gdf(routes_full, dropna_geom=True)
        self.df_solution_full = routes_full.copy()

    def plot_routes(self,
                    figsize = None,
                    plot_customers = True,
                    linewidth_full= 1.5,
                    linewidth_req = 3,
                    linewidth_req_cust=1):

        if figsize is None:
            figsize = (40, 40)

        df_solution_map = self.df_solution_full.copy()
        df_solution_map['Route'] = df_solution_map['route'] + 1
        df_solution_map['Route'] = 'Route ' + df_solution_map['Route'].astype(str)

        df_solution_map_travel = df_solution_map.loc[df_solution_map['activity_type'] == 'travel']
        df_solution_map_collect = df_solution_map.loc[df_solution_map['activity_type'] != 'travel']

        fig, ax = plt.subplots(figsize=figsize)
        #_ = self.network_plot.plot(ax=ax, linewidth=linewidth_full, color='grey')
        _ = df_solution_map_travel.plot(ax=ax, linewidth=linewidth_full,
                                 column='Route', legend=True, ls='dotted')
        _ = df_solution_map_collect.plot(ax=ax, linewidth=linewidth_req,
                                 column='Route', legend=True)
        if plot_customers:
            _ = self.df_required_arcs_plot.plot(ax=ax, markersize=linewidth_req_cust,
                                                color='red')

    def add_traversal_time(self):
        df = self.df_solution_full
        travels = df['activity_type'] == 'travel'
        df.loc[travels, 'activity_time'] = df['length'] / self.travel_speed
        df['activity_count'] = 1
        df['cum_time'] = df.groupby(['route'])['activity_time'].cumsum()
        self.df_solution_full = df

    def add_time_formatted(self,
                           start_time='2020-06-14 08:00:00',
                           t_col='cum_time',
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
        df = self.df_solution_full
        df['time'] = start_time
        df['time'] = pd.to_datetime(df['time'])
        if tz:
            df['time'] = df['time'].dt.tz_localize(
                None).dt.tz_localize('Asia/Singapore')
        df['time'] = df['time'] + pd.to_timedelta(
            df[t_col], unit=t_units)
        self.df_solution_full = df

    def add_constant_duration_time(self,
                                   start_time='2020-06-14 08:00:00',
                                   duration=30,
                                   t_units='sec'):
        """Add fake time with each activity assigned a constant duration.

        Args:
            start_time (str): start time as string (Y-m-d H:M:S)
            duration (int): duration of each activity.
            t_units (str): time units, s: seconds, m: minutes...
        """
        df = self.df_solution_full
        df['time_const_dur'] = start_time
        df['time_const_dur'] = pd.to_datetime(df['time_const_dur'])
        df['duration'] = duration
        df['duration'] = df.groupby('route')['duration'].cumsum()
        df['time_const_dur'] = df['time_const_dur'] + pd.to_timedelta(df['duration'],
                                                                    unit=t_units)
        self.df_solution_full = df

    def arc_consolidation_standard(self, prod):
        """Extract key general info per arc_index."""
        prop_info = prod.groupby(['arc_index']).agg(n_bins=('Postal Code', 'count'),
                                                    n_buildings=('Postal Code', 'count'),
                                                    n_units=('total units', 'sum'),
                                                    people=('total_people', 'sum')).reset_index()

        prop_info = prop_info.merge(self.network[['arc_index', 'length', 'maxspeed']], how='left')
        prop_info = prop_info.rename(columns={'length': 'distance', 'maxspeed': 'speed'})
        self.prop_info = prop_info.copy()
        return self.prop_info

    def bin_center_consolidation(self, prod):
        """Extract key producer info per bin center and arc."""
        prop_info = prod.groupby(['arc_index']).agg(n_bins=('Postal Code', 'count'),
                                                    n_bins_indirect=('No of Blks Served', 'sum'),
                                                    n_units=('Total units', 'sum'),
                                                    demand=('Calculated weight', 'sum')).reset_index()

        self.prop_info = prop_info.copy()
        self.prop_info = self.prop_info.merge(self.network[['arc_index', 'length', 'maxspeed']], how='left')
        self.prop_info = self.prop_info.rename(columns={'length': 'distance', 'maxspeed': 'speed'})
        return self.prop_info

    def calc_bin_center_demand_fancy(self, prod, units=1):
        """
        args
        """
        weight_col1 = 'Weight per day per flat'
        weight_col1_link = 'D units'
        weight_col2 = 'Weight per day per ND'
        weight_col2_link = 'ND units'
        weight_col3 = 'Weight per day per hawker'
        weight_col3_link = 'H/M units'
        prod['demand'] = prod[weight_col1] * prod[weight_col1_link] + \
            prod[weight_col2] * prod[weight_col2_link] + \
            prod[weight_col3] * prod[weight_col3_link]
        prod['demand'] = prod['demand'] * units
        return prod.copy()

    def calc_bin_center_demand_simple(self, prod, units=1):
        """
        args
        """
        weight_col1 = 'D_demand'
        weight_col1_link = 'D units'
        weight_col2 = 'ND_demand'
        weight_col2_link = 'ND units'
        weight_col3 = 'HK_demand'
        weight_col3_link = 'H/M units'
        prod['demand'] = prod[weight_col1] * prod[weight_col1_link] + \
            prod[weight_col2] * prod[weight_col2_link] + \
            prod[weight_col3] * prod[weight_col3_link]
        prod['demand'] = prod['demand'] * units
        return prod.copy()

    def calc_normal_demand_simple(self, prod, units=1):
        """
        args
        """
        weight_col1 = 'D_demand'
        weight_col1_link = 'dwelling units'
        weight_col2 = 'ND_demand'
        weight_col2_link = 'non-dwelling units'
        weight_col3 = 'nan_demand'
        prod[weight_col1_link] = prod[weight_col1_link].fillna(0)
        prod[weight_col2_link] = prod[weight_col2_link].fillna(0)
        prod['demand'] = prod[weight_col1] * prod[weight_col1_link] + \
            prod[weight_col2] * prod[weight_col2_link]
        prod['demand'] = prod['demand'] * units
        unknown_demand = prod['demand'] == 0
        prod.loc[unknown_demand, 'demand'] = prod.loc[unknown_demand]['nan_demand']
        return prod.copy()

    def add_demand_service_cost_to_ars(self, df, speed=10/3.6):
        df_arc = df.groupby(['arc_index']).agg(demand=('demand', 'sum'),
                                               bin_service_cost=('bin_service_cost', 'sum')).reset_index()
        df_arc = df_arc.merge(self.network[['arc_index', 'length']])
        df_arc['service_travel_cost'] = df_arc['length'] / speed
        df_arc['service_cost'] = df_arc['bin_service_cost'] + df_arc['service_travel_cost']
        return df_arc

    def calc_bin_center_service_fancey(self, prod, units=60):
        """
        args
        """
        service_col1 = 'Equipment discharge speed (kg/min)'
        service_col1_link = 'demand'
        service_col2 = 'Time to connect equipment (min)'

        prod['service_cost'] = prod[service_col1_link] / prod[service_col1] + \
            prod[service_col2]
        prod['service_cost'] = prod['service_cost'] * 60
        return prod.copy()

    def calc_bin_center_service(self, prod, units=1):
        """
        args
        """
        service_col1 = 'discharge'
        service_col1_link = 'demand'
        service_col2 = 'bin_connect'

        prod['bin_service_cost'] = prod[service_col1_link] / prod[service_col1] + \
            prod[service_col2]
        return prod.copy()

    def calc_normal_center_service(self, prod, units=1):
        """
        args
        """
        service_col1 = 'discharge'
        service_col1_link = 'demand'
        service_col2 = 'bin_connect'

        prod['bin_service_cost'] = prod[service_col1_link] / prod[service_col1] + \
            prod[service_col2]
        return prod.copy()
