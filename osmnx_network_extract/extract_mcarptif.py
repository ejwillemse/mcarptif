"""Module to extract MCARPTIF info from OSM and pytables
"""
import logging
import pandas as pd
import numpy as np
import tables as tb
from osmnx_network_extract.create_instance import create_arc_id


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
    """

    def __init__(self, network, arc_h5_path):
        """
        Arg:
            network (df): full arc network.
            arc_h5_path (str): path to arc info h5 file, with shortest path
                info.
        """
        self.network = network.copy()
        self.arc_h5_path = arc_h5_path

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
        self.d_np_req = None  # meter (initially)
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
        self.travel_speed = 1  # m/s

        self.df_service_cost = None
        self.df_demand = None

        self.serveCostL = None
        self.demandL = None

        self.nn_list = None

        self.min_capacity = 0
        self.min_duration = 0

    def create_inv_list(self):
        """Create an inverse arc list for the network arcs."""
        logging.info('Creating inverse arc list')
        network = self.network
        edges_flag = network['oneway'] == False
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

    def load_required_arcs(self, required_arcs):
        """Load required arcs. Should not contain both arcs of an edge
        (will raise a worning if it does)
        """
        logging.info('Load required arcs')
        if required_arcs['arc_index'].isin(self.network['arc_index']).all() \
                is False:
            logging.error('Required arcs are not in network.')
            raise ValueError()

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

        self.reqInvArcList = req_inv_list_info

        self.create_main_arc_list()

    def create_main_arc_list(self):
        """Main arc list to be used for setting demand and service costs"""
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
        self.d_np_req_orig = d_np_req.copy()
        self.d_np_req = d_np_req.copy()
        logging.info('Creating nearest neighbour lists')
        self.nn_list = np.argsort(self.d_np_req_orig, axis=1)

    def offload_calculations(self):
        """Calculate best offload positions and facilities."""
        n_arcs = self.d_np_req.shape[0]
        logging.info('Calculate offloads: {} x {} x {}'.format(n_arcs,
                                                          n_arcs,
                                                          self.n_ifs))
        if_cost_np = np.full(self.d_np_req.shape, np.infty)
        if_arc_np = np.full(self.d_np_req.shape, 0)

        for j in range(n_arcs):
            if_cost_np[0][j] = self.d_np_req[0][j]  # note that an if visit
            # may be shorter here. This influences trip and vehicle
            # removals, if I'm not mistaken. A vehicle shouldn't want to
            # visit an arc right after starting it's route, unless it
            # carried waste.
            if_arc_np[0][j] = 0

        for k_if in self.IFarcsnewkey:
            for i in range(n_arcs):
                for j in range(n_arcs):
                    visitT = self.d_np_req[i][k_if] + \
                             self.d_np_req[k_if][j]
                    if visitT < if_cost_np[i][j]:
                        if_cost_np[i][j] = visitT
                        if_arc_np[i][j] = k_if
        self.if_cost_np_orig = if_cost_np.copy()
        self.if_arc_np = if_arc_np.copy()
        self.if_cost_np = self.if_cost_np_orig + self.offload_cost

    def offload_calculations3D(self):
        """Calculate best offload positions and facilities."""
        n_arcs = self.d_np_req.shape[0]
        logging.info('Calculate offloads: {} x {} x {}'.format(n_arcs,
                                                               n_arcs,
                                                               self.n_ifs))

        offload_costs = []
        for k_if in self.IFarcsnewkey:
            arc_to_if = self.d_np_req[:, k_if]
            if_to_arc = self.d_np_req[k_if, :]

            dist_x, dist_y = np.meshgrid(arc_to_if, if_to_arc)
            dist = dist_x + dist_y
            offload_costs.append(dist.T)

        np_offload_costs = np.dstack(offload_costs)
        if_cost_np_orig = np_offload_costs.min(axis=2)
        if_arc_np = np_offload_costs.argmin(axis=2)
        if_arc_np = if_arc_np + 1  # because depot

        if_cost_np_orig[0, :] = self.d_np_req[0, :]
        if_arc_np[0, :] = 0

        self.if_cost_np_orig = if_cost_np_orig.copy()
        self.if_arc_np = if_arc_np.copy()
        self.if_cost_np = self.if_cost_np_orig + self.offload_cost

    def set_travel_speed(self, travel_speed=1):
        """Set travel speed (m/s) and update required arc list.
        """
        self.travel_speed = travel_speed

    def set_offload_time(self, offload):
        """Set offload costs"""
        self.offload_cost = offload

    def update_cost_matrix(self):
        logging.info('Update travel durations.')
        self.d_np_req = self.d_np_req_orig.copy() / self.travel_speed

    def update_offload_cost(self):
        logging.info('Update offload durations.')
        self.if_cost_np = self.if_cost_np_orig.copy() / self.travel_speed + \
                          self.offload_cost

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

    def round_key_inputs(self):
        """Round key inputs for MCARPTIF solution files."""
        logging.info('Round key inputs')
        self.df_service_cost['service_cost'] = self.df_service_cost['service_cost'].astype(int)
        self.df_demand['demand'] = self.df_demand['demand'].astype(int)
        self.d_np_req = self.d_np_req.astype(int)
        self.if_cost_np = self.if_cost_np.astype(int)

    def calc_min_duration_capacity(self):
        """Calculate the minimum route duration time and capacity"""
        demand = self.df_demand['demand'].values
        service = self.df_service_cost['service_cost'].values
        self.min_capacity = demand.max()
        req_arcs = self.reqArcListActual
        self.min_duration = self.d_np_req[0, req_arcs] + \
                       service[req_arcs] + self.if_cost_np[req_arcs, 0]
        self.min_duration = self.min_duration.max()

    def check_shapes(self):
        """Check shapes to spot errors"""
        d_shape = self.d_np_req.shape
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


