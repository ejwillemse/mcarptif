# -*- coding: utf-8 -*-
"""Transform an OSMNX graph-generated pandas data-frame into a raw txt file
that can be imported using the solvers.

Input is a directed-graph, generated using <https://github.com/gboeing/osmnx>.

The data-frame has to have specific column names. Wrappers can be developed to
translate between a existing and required names.

The names required are:

 * `u`: start vertex of an arc
 * `v`: end vertex of an arc
 * `key`: secondary identifier, separating parallel arcs with the same
 start and end vertices.
 * `travel_cost`: travel/traversal cost of an arc (can be in length, time,
 money, etc.)
 * `oneway`: whether an arc is one-way or two-way (can be 1 or True for "is
 a one-way")

For arcs that the required service data-frame, the following names are also
required:

 * `demand`: demand to be collected from the arc.
 * `service_cost`: service cost of an arc (can be in length, time, money, etc.)

`oneway` should be bool, and all columns have to be in integer. If accuracy is
required, add a 10^x multiplier.

`service_cost` should be > 0, which is a problem if integer rounding is use
for small arcs. Some algorithms use a `demand` to `service_cost`
ratio, which becomes inf due to numpy.

The following additional columns are created and changed through the
transformation:

Dummy arcs are added to separate parallel arcs, so copies of the originals
are created:

 * `u_orig`: original start vertex
 * `v_orig`: original end vertex
 * `arc_id_orig`: a `u_orig-v_orig-key` key id

These columns are then updated for parallel-arcs:

 * `u`: start vertex (changed for parallel arcs)
 * `v`: end vertex (changed for parallel arcs)
 * `arc_id`: a `u-v` key id (changed for parallel arcs)
 * `arc_id_ordered`: a `u-v` ordered key id, such that `u`<`v` for arcs that
 are not one-way. For one-way arcs, this is the same as `arc_id`.

All other columns are retained.

NOTES:

Given the potential sparsity of required graphs, demand and service info is
not included in the full graph, through this info could just be set to zero.
This allows updates and changes to the required graph, without having to
manipulate the larger full network graph.

When solving the MCARPTIF, the max-route cost limit `maxTrip` is related to
`service_cost` and `travel_cost`, so these should be in the same units. If this
limit is not used, they can be in different units. The same with capacity,
`capacity`. It should be in the same unit as `demand`.

For large graphs, calculating the distance matrix is time-consuming,
which depends on `u`, `v`, `key` and `travel_cost`. The required arc parameters
can be changed and the problem solved without having to calculate the above.

Required arcs cannot be removed without have to recalculate the input
parameters. The distance matrix is reduced to required arcs to reduce memory
requirements. The algorithms will have to be updated to take as input
required-arcs and edges lists.

History:
    Created on 12 June 2020
    @author: Elias J. Willemse
    @contact: ejwillemse@gmail.com
"""
from copy import copy

import pandas as pd
import numpy as np


def test_column_exists(df, *column_names):
    """Check that columns are in the data-frame.

    Args:
        df (pd.DataFrame): data-frame to check.
        column_names (str): column names to check for.

    Raise:
        TypeError: column not of required type.
    """
    df_columns = df.columns
    for col_name in column_names:
        if col_name not in df_columns:
            out = 'Column `{}` not found'.format(col_name)
            raise NameError(out)


def test_column_type(df, **column_types):
    """Check that columns are of a specific type

    Args:
        df (pd.DataFrame): data-frame to check.
        column_types ({str, type}): column names and their required types.

    Raise:
        TypeError: column not of required type.
    """
    for column_name, require_type in column_types.items():
        column_type = df[column_name].dtypes
        if column_type != require_type:
            out = 'Columns `{}` of type `{}` requires to be `{}`'.format(
                column_name, column_type, require_type)
            raise TypeError(out)


def test_vertex_exist(df, vertices, columns):
    """Check if vertices exists in columns.

    Args:
        df (pd.DataFrame): dataframe to check.
        vertices (list <int>): list of vertices to check.
        columns (list <str>): list of columns to check.
    """
    for vertex in vertices:
        vertex_exists = False
        for col in columns:
            vertex_exists = (df[col] == vertex).any()
            if vertex_exists:
                break
        if not vertex_exists:
            raise ValueError('Vertex {} not found'.format(vertex))


def create_arc_id(df, arc_id='arc_id', *keys):
    """Create new id based on a bunch of columns.

    Note that where nan u and v are filled with zeros, the resulting key
    will have 0 in places, which may represent an actual arc key for another
    arc.

    Args:
        df (pd.DataFrame): data-frame to create a new id columns with
        arc_id (str): column name of id
        keys (column name): column names of new ids, has to be integer.

    Return df (pd.DataFrame): data-frame with id column.
    """
    df[arc_id] = ''
    key_nan = []
    for i, key in enumerate(keys):
        key_i = df[key].fillna(0).astype(int).astype(str)
        if i == 0:
            df[arc_id] = key_i
            key_nan = df[key].isna()
        else:
            df[arc_id] = df[arc_id] + '-' + key_i
            key_nan = key_nan | key_nan
    if len(key_nan):
        df.loc[key_nan, arc_id] = np.nan
    return df


def convert_to_int(df, *keys):
    """Convert columns in data.frame to int, as required for MCARPTIF.

    Arcs:
        df (pd.DataFrame): data-frame to create a new id columns with
        arc_id (str): column name of id
        *keys (column name): names of columns to convert to int.

    Return df (pd.DataFrame): data-frame with columns not int.
    """
    for key in keys:
        df[key] = df[key].astype(int)
    return df


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
        self._parallel_arcs = True
        self.dummy_arcs = None  # data-frame of dummy arcs

    def _test_graph_parameters(self):
        """Test if the graph meets column name requirements."""
        test_column_exists(self._df_graph,
                           'u',
                           'v',
                           'k',
                           'travel_cost',
                           'oneway')

    def _convert_to_int(self, fix_columns_int=True):
        """
        Args:
            fix_columns_int (bool): convert all number columns to int.
        """

        if fix_columns_int:
            self._df_graph = convert_to_int(self._df_graph,
                                            'u',
                                            'v',
                                            'key',
                                            'travel_cost')

        test_column_type(self._df_graph, **{'u': int,
                                            'v': int,
                                            'key': int,
                                            'travel_cost': int,
                                            'oneway': bool})

    def _check_for_parallel_arcs(self):
        """Check whether there are any parallel arcs"""
        duplicates = self._df_graph.duplicated(subset=['u', 'v'], keep=False)
        n_parallel = len(self._df_graph.loc[duplicates])
        return n_parallel > 1

    def _extend_parallel(self):
        """Find arcs and edges with same start and end-nodes (arcs-ids) create
        connected dummy nodes and arcs for them. New `u_orig, v_orig`
        columns are created to keep track of where the dummy arcs where
        assigned and where they came from.

        The easiest way to explain this is that we assign a new (u, v) ids
        for the first parallel arc. This arc is not connected to the graph.
        To connect it, we create a zero length/demand arc out from u to u' and
        then back in from v' to v. To check the logic, it helps a lot
        just make the dummy u and v negative. If u or v is zero, or if there
        are negative keys, the code will break. So a max key value is
        added.
        """
        # keep track of the original nodes.
        self._df_graph[['u_orig', 'v_orig']] = self._df_graph[['u', 'v']]

        max_key = max(self._df_graph['u'].max(), self._df_graph['v'].max())

        # find all parallel arcs
        duplicates = self._df_graph.duplicated(subset=['u', 'v'], keep=False)
        df_dups = self._df_graph.loc[duplicates].copy()

        # find first occurrence of parallel arcs
        dup_inter = df_dups.duplicated(subset=['u', 'v'])
        df_dup_inter = df_dups.loc[dup_inter].copy()

        # create new dummy nodes and assign them
        u_nodes = df_dup_inter['u'].copy()
        v_nodes = df_dup_inter['v'].copy()
        u_dummy = u_nodes + max_key
        v_dummy = v_nodes + max_key
        df_dups.loc[dup_inter, 'u'] = u_dummy
        df_dups.loc[dup_inter, 'v'] = v_dummy

        # create new dummy arcs to be a added to reconnect the parallel
        # arcs with new nodes back to the graph. They won't have original
        # nodes.
        new_arcs_u = u_nodes.append(v_dummy)
        new_arcs_v = u_dummy.append(v_nodes)
        dummy_arcs = pd.DataFrame.from_dict({'u': new_arcs_u, 'v': new_arcs_v})
        self.dummy_arcs = dummy_arcs.copy()
        dummy_arcs['travel_cost'] = 0  # since they are dummy arcs, this is
        # zero.

        # these are all the parallel arcs, with their nodes updated.
        df_dups = pd.concat([df_dups, dummy_arcs])

        # We combine them back into the original data frame. We can use the
        # orig node to keep track of which are the original ones.
        self._df_graph = pd.concat([self._df_graph.loc[~duplicates].copy(),
                                    df_dups])

    def _create_ordered_ids(self,
                            arc_id='arc_id',
                            arc_id_ordered='arc_id_ordered',
                            nan_oneway_fill_val=False):
        """Create key-pairs, 'u-v', ordered for edges, unordered for
        arcs. Requires `arc_id` through `self._create_arc_ids`

        Args:
            arc_id (str): name of existing id column
            arc_id_ordered (str): name of new ordered id column
            nan_oneway_fill_val (bool): value to fill the oneway column with.
        """
        def ordered_key(df_frame):
            u_val, v_val = df_frame['u'], df_frame['v']
            u_ord = min(u_val, v_val)
            v_ord = max(u_val, v_val)
            edge_key_ordered = '{}-{}'.format(u_ord, v_ord)
            return edge_key_ordered

        self._df_graph['oneway'] = self._df_graph['oneway'].fillna(
            value=nan_oneway_fill_val)

        self._df_graph[arc_id_ordered] = self._df_graph.apply(ordered_key,
                                                              axis=1)
        one_ways = self._df_graph['oneway'] == True
        self._df_graph.loc[one_ways, arc_id_ordered] = self._df_graph.loc[
            one_ways][arc_id]

    def prep_osmnx_graph(self):
        """Complete all graph preparations, including converting required
        columns to int, adding arc keys, and creating dummy arcs for parallel
        arcs with the same start and end nodes.

        Return:
            df (pd.DataFrame): with all preparations done.
        """
        self._convert_to_int()

        self._df_graph = create_arc_id(self._df_graph,
                                       'arc_id_orig',
                                       'u',
                                       'v',
                                       'key')

        self._df_graph['u_orig'] = self._df_graph['u'].copy()
        self._df_graph['v_orig'] = self._df_graph['v'].copy()

        self._parallel_arcs = self._check_for_parallel_arcs()
        if self._parallel_arcs:
            self._extend_parallel()

        self._df_graph = create_arc_id(self._df_graph,
                                       'arc_id',
                                       'u',
                                       'v')

        self._create_ordered_ids()

        if self._check_for_parallel_arcs():
            raise TypeError('Parallel arcs in network')
        return self._df_graph


class PrepareRequiredArcs:
    """Prepare the the required arcs pandas data-frame graph, to make it
    compatible with MCARPTIF solver.
    """

    def __init__(self, df_graph_req):
        """Inputs is the required arcs network graph, formatted using

        Args:
            df_graph_req (pd.DataFrame): data-frame with required arcs.
        """
        self._df_graph_req = df_graph_req.copy()

    def _test_graph_parameters(self):
        """Test if the graph meets column name requirements."""
        test_column_exists(self._df_graph_req,
                           'u',
                           'v',
                           'key',
                           'travel_cost',
                           'oneway',
                           'demand',
                           'service_cost',
                           'arc_id_ordered')

    def _convert_to_int(self, fix_columns_int=True, fix_service_cost=True):
        """
        Args:
            fix_columns_int (bool): convert all number columns to int.
            fix_service_cost (bool): replace zero service cost with 1.

        Raise:
            ValueError: if service cost zero.
        """

        if fix_columns_int:
            self._df_graph_req = convert_to_int(self._df_graph_req,
                                                'u',
                                                'v',
                                                'key',
                                                'travel_cost',
                                                'demand',
                                                'service_cost')

        test_column_type(self._df_graph_req, **{'u': int,
                                                'v': int,
                                                'key': int,
                                                'travel_cost': int,
                                                'oneway': bool,
                                                'demand': int,
                                                'service_cost': int})

        zero_cost = self._df_graph_req['service_cost'] == 0

        if fix_service_cost:
            self._df_graph_req.loc[zero_cost, 'service_cost'] = 1
        elif len(self._df_graph_req.loc[zero_cost]):
            raise ValueError('`service_cost` cannot be zero')

    def _consolidate_edges(self):
        """Consolidate the demand and service cost of edges into one arc.
        This is required since demand is assigned to one of the two arcs.
        For now, the first found ordered arc occurrence is used."""

        edges = self._df_graph_req['oneway'] == False
        df_edges = self._df_graph_req.loc[edges].copy()
        demand_group = df_edges.groupby(['arc_id_ordered']).agg(demand=(
            'demand', 'sum')).reset_index()
        df_edges = df_edges.drop(columns='demand')
        df_edges = df_edges.drop_duplicates(subset=['arc_id_ordered'])
        df_edges = pd.merge(df_edges, demand_group)
        self._df_graph_req = pd.concat([self._df_graph_req.loc[~edges],
                                        df_edges])

    def prepare_required_arcs(self):
        """Prepare required arcs for writing."""
        self._test_graph_parameters()
        self._convert_to_int()
        self._consolidate_edges()


class CreateMcarptifFormat:
    """Transform geo-data-frames into MCARPTIF raw text format."""

    def __init__(self,
                 df_graph,
                 df_graph_req,
                 depot_vertex=None,
                 if_vertices=None):
        """Key input data is the full network graph and required network graph.
        They are split for the workflow where the required graph is
        split, updated with changes to demand, service time, etc. Both should
        be prepared using PrepareGraph and contain arc-ids and no duplicates.

        Args:
            df_graph (pd.DataFrame): data-frame of full network.
            df_graph_req (pd.DataFrame): data-frame with required edges.
            depot_vertex (int): vertex of depot
            if_vertices (list <int>): vertices of offload sites.
        """
        self._df_graph = df_graph.copy()
        self._df_graph_req = df_graph_req.copy()

        self.name = ''

        self.n_nodes = None
        self.n_req_edges = None
        self.n_nonreq_edges = None
        self.n_req_arcs = None
        self.n_nonreq_arcs = None

        self.vehicles = 0
        self.capacity = 0
        self.dumping_cost = 0
        self.max_trip = 0

        self.depot_vertex = depot_vertex
        self.if_vertices = if_vertices

        self._output_str = ''

    def _check_graph_parameters(self):
        test_column_exists(self._df_graph,
                           'u',
                           'v',
                           'key',
                           'oneway',
                           'travel_cost')

        test_column_exists(self._df_graph_req,
                           'u',
                           'v',
                           'key',
                           'oneway',
                           'service_cost',
                           'demand',
                           'travel_cost')

    def _check_type(self):
        test_column_type(self._df_graph, **{'u': int,
                                            'v': int,
                                            # 'key': int, #  doesn't
                                            # have to be int
                                            'travel_cost': int,
                                            'oneway': bool})

        test_column_type(self._df_graph_req, **{'u': int,
                                                'v': int,
                                                # 'key': int, #  doesn't
                                                # have to be int
                                                'travel_cost': int,
                                                'oneway': bool,
                                                'demand': int,
                                                'service_cost': int})

    def set_problem_parameters(self,
                               name=None,
                               vehicles=None,
                               capacity=None,
                               dumping_cost=None,
                               max_trip=None):
        """Set key input parameters for problem instance

        Args:
            name (str): name of instance
            vehicles (int): number of vehicles
            capacity (int): capacity of vehicle
            dumping_cost (int): cost to offload at processing points (
             assumed to be consistent for all points)
            max_trip (int): max cost of vehicle route

        Of these, `capacity`, `dump_cost` and `max_trip` are the most
        important. `dump_cost` can't be changed. The rest can.
        """
        if name is not None:
            self.name = name

        if vehicles is not None:
            self.vehicles = vehicles

        if capacity is not None:
            self.capacity = capacity

        if dumping_cost is not None:
            self.dumping_cost = dumping_cost

        if max_trip is not None:
            self.max_trip = max_trip

    def _calc_graph_properties(self):
        """Calculate graph properties, including number node, arcs and edges,
        required and non-required"""

        node_keys = pd.concat([self._df_graph_req['u'],
                               self._df_graph_req['v']])

        self.n_nodes = len(node_keys.unique())
        req_edges = self._df_graph_req['oneway'] == False
        edges = self._df_graph['oneway'] == False
        self.n_req_edges = len(self._df_graph_req.loc[req_edges])
        self.n_nonreq_edges = len(self._df_graph.loc[edges]) - self.n_req_edges
        self.n_req_arcs = len(self._df_graph_req) - self.n_req_edges
        self.n_nonreq_arcs = len(self._df_graph) - self.n_req_arcs - \
                             self.n_req_edges - self.n_nonreq_edges

    def set_depot(self, depot_vertex):
        """Set depot vertex from where vehicles will be dispatched.

        Args:
            depot_vertex (int): vertex of depot

        Raise:
            ValueError: vertex not in graph
        """
        test_vertex_exist(self._df_graph, [depot_vertex], ['u', 'v'])
        self.depot_vertex = depot_vertex

    def set_ifs(self, if_vertices):
        """Set offload vertices where vehicles dispose their waste.

        Args:
            if_vertices (list <int>): vertices of dumpsites

        Raise:
            ValueError: vertex not in graph
        """
        test_vertex_exist(self._df_graph, if_vertices, ['u', 'v'])
        self.if_vertices = copy(if_vertices)

    def _add_req_arc_str(self):
        """Add output string for required arcs and edges to data-frame"""
        u = self._df_graph_req['u'].astype(str)
        v = self._df_graph_req['v'].astype(str)

        serve = self._df_graph_req['service_cost'].astype(str)
        trav = self._df_graph_req['travel_cost'].astype(str)
        dem = self._df_graph_req['demand'].astype(str)

        out_str = '(' + u + ',' + v + ')' + '   serv_cost   ' + serve + \
                  '   trav_cost   ' + trav + '   demand   ' + dem + '\n'
        self._df_graph_req['out_str'] = out_str

    def _add_arc_str(self):
        """Add output string for all arcs and edges to data-frame"""
        u = self._df_graph['u'].astype(str)
        v = self._df_graph['v'].astype(str)
        trav = self._df_graph['travel_cost'].astype(str)
        out_str = '(' + u + ',' + v + ')' + '   cost   ' + trav + '\n'
        self._df_graph['out_str'] = out_str

    def _set_depot_str(self):
        out = 'DEPOT : {}\n'.format(self.depot_vertex)
        return out

    def _set_dump_str(self):
        dumpsites_list = str(self.if_vertices).strip('[]').replace(' ', '')
        out = 'DUMPING_SITES : ' + dumpsites_list
        return out

    def _set_header_str(self):
        """Create file header, none are really required."""
        header_str = ''
        header_str += "NAME : {}\n".format(self.name)
        header_str += "NODES : {}\n".format(self.n_nodes)
        header_str += "REQ_EDGES : {}\n".format(self.n_req_edges)
        header_str += "NOREQ_EDGES : {}\n".format(self.n_nonreq_edges)
        header_str += "REQ_ARCS : {}\n".format(self.n_req_arcs)
        header_str += "NOREQ_ARCS : {}\n".format(self.n_nonreq_arcs)
        header_str += "VEHICLES : {}\n".format(self.vehicles)
        header_str += "CAPACITY : {}\n".format(self.capacity)
        header_str += "DUMPING_COST : {}\n".format(self.dumping_cost)
        header_str += "MAX_TRIP : {}\n".format(self.max_trip)
        return header_str

    def _create_instance_str(self):
        """Create full string of instance"""
        req_edges_i = self._df_graph_req['oneway'] == False
        req_edges = self._df_graph_req.loc[req_edges_i]
        req_arcs = self._df_graph_req.loc[~req_edges_i]

        non_req_i = ~self._df_graph['arc_id_ordered'].isin(
            self._df_graph_req['arc_id_ordered'])
        df_graph_nonreq = self._df_graph.loc[non_req_i]
        edges_i = df_graph_nonreq['oneway'] == False
        edges = df_graph_nonreq.loc[edges_i]
        arcs = df_graph_nonreq.loc[~edges_i]

        self._output_str = ''
        self._output_str += self._set_header_str()

        self._output_str += 'LIST_REQ_EDGES : \n'
        for out in req_edges['out_str']:
            self._output_str += out

        self._output_str += 'LIST_REQ_ARCS : \n'
        for out in req_arcs['out_str']:
            self._output_str += out

        self._output_str += 'LIST_NOREQ_EDGES : \n'
        for out in edges['out_str']:
            self._output_str += out

        self._output_str += 'LIST_NOREQ_ARCS : \n'
        for out in arcs['out_str']:
            self._output_str += out

        self._output_str += self._set_depot_str()
        self._output_str += self._set_dump_str()

    def create_instance(self, check_inputs=True):
        """Create problem instance text file.

        Args:
            check_inputs (bool): if inputs should be checked.
        """

        if check_inputs:
            print('Checking inputs...')
            self._check_graph_parameters()
            self._check_type()
            self.set_depot(self.depot_vertex)
            self.set_ifs(self.if_vertices)
            self._calc_graph_properties()
            print('done')

        print('Converting inputs to string...')
        self._add_req_arc_str()
        self._add_arc_str()
        self._set_depot_str()
        self._set_dump_str()
        self._set_header_str()
        self._create_instance_str()
        print('done')

    def write_instance(self, file_name):
        """Write instance to a file"""
        print('Writing instance to `{}`...'.format(file_name))
        with open(file_name, 'w') as file:
            file.write(self._output_str)
        print('done')
