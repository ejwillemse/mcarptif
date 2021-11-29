"""
Module to extract VRPTIF info using OSRM for shortest-path calcualtions.

This account Nodes.
"""
import logging
import pandas as pd
import numpy as np
import tables as tb
from osmnx_network_extract.create_instance import create_arc_id
from converter.shortest_path import sp_full
from osmnx_network_extract.network_code import create_gdf, create_latlon_gdf
from visualise.customer_plots import color_df

import matplotlib.pyplot as plt


class SetupInputData:
    """Extract all problem info in the format required for the MCARPTIF with the shortest
    cost matrix supplied via OSRM.

    As rules:
        * depot is always the first entry in the required arc list
        * thereafter, intermediate facilities
        * thereafter, required nodes, ordered according to their index.
        * only one arc orientation per (required?) edge is allowed
        * each node is assigned a type:
            `depot`, `offload`, `collection`
        * All time units should be in seconds (it can be anything,
        but seconds work well.)
        * Any speed based units should be per meter, because of open-street
        and the cost matrix which is in meters.
    """

    def __init__(self,
                 problem_info: pd.DataFrame,
                 osrm_port: str,
                 round_cost: bool = True):
        """
        Arg:
            problem_info (df): problem info
            osrm_port (str): port for OSRM shortest path calculations
            round_cost (bool): whether costs should be rounded to integers.
                Can cause issues with cost testing later.
        """
        self.network = problem_info.copy()
        self.network["arc_index"] = np.arange(0, self.network.shape[0])
        self.network["arc_id"] = self.network["arc_index"]
        self.network["u"] = self.network["arc_index"]
        self.network["v"] = self.network["arc_index"]
        self.network['oneway'] = True

        self.osrm_port = osrm_port
        self.round_cost = round_cost

        self.df_inv_list = None
        self.df_edges = None
        self.df_arcs = None

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

        self.collection_schedule = None

        self.offload_table_wide = None
        self.producer_demand = None
        self.producer_collection_schedule = None

    def set_mcarptif_columns(self):
        """Set columns unique to MCARPTIF"""
        if not (self.network["visit_index"] == np.arange(0, self.network.shape[0])).all():
            logging.error("`visit_index` not sequential starting from zero")
        self.network["arc_index"] = self.network["visit_index"]
        self.network["arc_index"] = np.arange(0, self.network.shape[0])
        self.network["arc_id"] = self.network["arc_index"]
        self.network["u"] = self.network["arc_index"]
        self.network["v"] = self.network["arc_index"]
        self.network['oneway'] = True
        self.network['arc_id_ordered'] = self.network["arc_id"]
        self.create_inv_list()

    def create_inv_list(self):
        """For this version, there should not be any inverse edges, just arcs.
        """
        logging.info('Creating inverse arc list')
        network = self.network
        circle = network['u'] == network['v']
        edges_flag = (network['oneway'] == False) & (circle == False)
        edges_inv = network.copy().loc[edges_flag][['u', 'v', 'oneway',
                                                 'arc_index', 'arc_id_ordered']]
        edges_key = network.copy().loc[edges_flag][['u', 'v',
                                                    'oneway',
                                                    'arc_index',
                                                    'arc_id',
                                                    'arc_id_ordered']]
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

    def load_required_arcs(self, required_arcs):
        """Load required arcs. Should not contain both arcs of an edge
        (will raise a warning if it does)
        """
        logging.info('Load required arcs')
        self.df_required_arc_index_orig = required_arcs.copy()

    def set_depot_arc(self, depot_arc_index):
        """Set depot arc info"""
        logging.info('Set depot')
        self.depotnewkey = 0
        self.n_dummy = 1
        self.depot_arc_index = depot_arc_index

    def set_if_arcs(self, if_arc_index):
        """Set if arc info"""
        logging.info('Set offload facilities')
        # depot always has index 0
        self.n_ifs = if_arc_index.shape[0]
        self.n_dummy = self.n_ifs + 1
        self.IFarcsnewkey = np.array(range(self.n_ifs)) + 1
        self.if_arc_index = if_arc_index
        self.dummy_req_indices = np.array(list(range(self.n_dummy)))

    def extend_required_inverse_arcs(self):
        """Extend required arcs with their inverse arcs."""
        # TODO: this should be easier now.

        self.reqArcList = self.network["arc_index"].values
        self.reqArcListActual = self.df_required_arc_index_orig
        self.reqEdgesPure = []
        self.reqArcsPure = self.reqArcListActual
        self.req_inv_list_full = [None] * self.network.shape[0]
        self.reqInvArcList = [None] * self.network.shape[0]

    def set_cost_matrix(self, d: np.array):
        """Set the cost matrix, based on OSRM retrieved time or distance matrix."""
        req_nodes = self.reqArcList
        self.d = d
        d_np_req = d[req_nodes, :]
        d_np_req = d_np_req[:, req_nodes]
        self.d_np_req_orig = d_np_req.copy()
        self.d = d_np_req.copy()
        logging.info('Creating nearest neighbour lists')
        self.nn_list = np.argsort(d_np_req, axis=1)

    def set_offload_time(self, offload):
        """Set offload costs"""
        self.offload_cost = offload
        self.dumpCost = offload

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

    def set_service_cost(self, service_cost):
        """Set service costs of required arcs.

        Arg:
            service_cost (dataframe): with 'arc_index', 'service_cost'
            column.

        Only required arcs should be included and only one of the arcs of
        edges. The one original loaded into the data frame.
        """
        logging.info('Setting service cost for network')
        self.serveCostL = service_cost

    def set_service_demand(self, service_demand):
        """Set demand of required arcs.

        Arg:
            df_demand (dataframe): with 'arc_index', 'demand'
            column.

        Only required arcs should be included and only one of the arcs of
        edges. The one original loaded into the data frame.
        """
        logging.info('Setting demand for network')
        self.demandL = service_demand

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
        demand = self.demandL
        service = self.serveCostL
        self.min_capacity = demand.max()
        req_arcs = self.reqArcListActual
        self.min_duration = self.d[0, req_arcs] + \
                            service[req_arcs] + self.if_cost_np[req_arcs, 0]
        self.min_duration = self.min_duration.max()

    def calc_min_capacity(self):
        """Calculate the minimum route capacity"""
        demand = self.demandL
        self.min_capacity = demand.max()

    def calc_min_duration(self):
        """Calculate the minimum route duration time"""
        service = self.serveCostL
        req_arcs = self.reqArcListActual
        self.min_duration = self.d[0, req_arcs] + \
                            service[req_arcs] + self.if_cost_np[req_arcs, 0]
        self.min_duration = self.min_duration.max()

    def set_vehicle_capacity_constraint(self, capacity):
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

        n_demand_df = self.demandL.shape[0]
        n_costs_df = self.serveCostL.shape[0]
        assert n_req_arcs == n_demand_df == n_costs_df

        n_req_arcs = self.df_required_arc_index_orig.shape[0]
        n_edges_pure = 0
        n_req_arcs_pure = self.df_required_arc_index_orig.shape[0]
        n_req_arcs_actual = self.reqArcListActual.shape[0]
        n_ifs = self.IFarcsnewkey.shape[0]
        n_req_arcs_full = self.reqArcList.shape[0]

        assert n_req_arcs == (n_edges_pure + n_req_arcs_pure)
        assert n_req_arcs_actual == (2 * n_edges_pure + n_req_arcs_pure)
        assert n_req_arcs_full == (2 * n_edges_pure + n_req_arcs_pure) + self.n_dummy
        assert (n_req_arcs_actual + self.n_dummy) == n_req_arcs_full
        assert self.n_dummy == n_ifs + 1