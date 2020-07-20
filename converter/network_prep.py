# -*- coding: utf-8 -*-
"""
Writing of MCARPTIF problem data using pydeck.

Author: ejwillemse@gmail.com

Data needed of the network for shortest path calculations:

 * arc_u: list of all start vertices of arcs
 * arc_v: list of all end vertices of arcs
 * arc_cost: costs of all arcs, can be length, traversal time, or cost. Take
    care with this one. Significant changes later-on will render the shortest
    path calculations invalid.
"""
import pandas as pd
import numpy as np
import logging
import os
import tables as tb
import converter.shortest_paths as shortest_paths
from time import perf_counter as clock


def key_columns_exists(df, required_columns):
    """Test if 'columns' are in the data.frame (df)

    Args:
        df (pandas.DataFrame)
        required_columns (list <str>): columns to check for
    Raises:
        AttributeError: column not found
    """
    df_columns = df.columns.values
    diff = np.setdiff1d(required_columns, df_columns, assume_unique=False)
    if diff.shape[0] != 0:
        not_in = str(list(diff))
        logging.error('The following required columns are not in the data '
                      'frame: {}'.format(diff))
        raise AttributeError


def key_columns_not_exists(df, place_holder_columns):
    """Test if 'columns' are in the data.frame (df)

    Args:
        df (pandas.DataFrame)
        place_holder_columns (list <str>): columns to check for as they will be
        used later on, and will be overwritten.
    Raises:
        AttributeError: column not found
    """
    df_columns = df.columns.values
    intersect = np.intersect1d(place_holder_columns, df_columns,
                               assume_unique=False)
    if intersect.shape[0] != 0:
        is_in = str(list(intersect))
        logging.error('The following columns are in the data '
                      'frame and will be overwritten, recommend renaming '
                      'them: {}'.format(is_in))
        raise AttributeError


def return_successor_arcs_indices(u, v):
    """Find successor arc indices based on arc start vertices, u, and end
    vertices v. u and v have to be in the order of the their arcs.

    Args:
        u (list/np.array): start vertices of arcs
        v (list/np.array): end vertices of arcs

    Returns:
        successor_list (np.array <np.array>) = a mixed numpy array with the
        index of each arc that is a successor of arc i.
    """
    u_np = np.array(u)
    v_np = np.array(v)

    successor_list = np.array([np.where(x == u_np)[0] for x in v_np])
    return successor_list


class Network:
    """Network on which the shortest path calculations will be performed.
    The class works exclusively with indices, and can return the indices and
    arc pairs (u-v) as secondary keys. This is the core network."""

    def __init__(self, network_df, calc_successor=True, second_key=None):
        """
        Args:
            network_df (pandas.DataFrame): pandas data-frame with `arc_u`,
            `arc_v` and `arc_cost` columns.
            calc_successor (bool): if the successor index list should be
            calculated immediately (will slow down initiation with large (5k+)
                networks.
            second_key (str): optional secondary key, for tracing the
                network back to its origins.

        Raise:
            AttributeError: if the three key columns are not in the dataframe.
            AttributeError: if id columns are already in the dataframe.

        Key class attributes:
            arc_index (np.array <int>): index of each arc from the original
                data.frame.
            arc_u (np.array): start vertex of each arc 'i'
            arc_v (np.array): end vertex of each arc 'i'
            arc_pair (np.array <str>): arc pair secondary key <'arc_u-arc_v'>
            generate_successor_list (np.array <np.array>): multi-dimensional
                array with the successor arc indices (in an array) of each
                arc, again, per index.
            secondary_key (np.array): ptional secondary key, for tracing the
                arcs back to their origins.

        All of the above can be stored in a pytable object.
        """
        key_columns = ['arc_u', 'arc_v', 'arc_cost']
        key_columns_exists(network_df, key_columns)

        self.network_df = network_df.copy()
        self.arc_u = self.network_df['arc_u'].values.copy()
        self.arc_v = self.network_df['arc_v'].values.copy()
        self.arc_cost = self.network_df['arc_cost'].values.copy()
        self.arc_index = np.array(self.network_df.index.copy())

        self.arc_pair = self.network_df['arc_u'].astype(str) + '-' + \
            self.network_df['arc_v'].astype(str)

        self.arc_pair = self.arc_pair.values.astype(str)

        self.arc_successor_index_list = None
        if calc_successor:
            self.generate_successor_list()

        self.second_key = second_key
        if second_key:
            self.secondary_arc_key = self.network_df['second_key']
        else:
            self.secondary_arc_key = None

        self.network_file = None

    def generate_successor_list(self):
        """Prepare network and generate successor arcs, those where v == u.
        """
        self.arc_successor_index_list = return_successor_arcs_indices(self.arc_u,
                                                                      self.arc_v)

    def update_network_df(self, include_successor_list=True):
        """Update the network data.frame with the generated network info
        added as new columns.

        Arg:
            include_successor_list (bool): whether the successor list should
                be included

        Raises:
             AttributeError: if any of the key columns already exists.
             AttributeError: if successor list has not yet been captured.
        """
        key_columns_not_exists(self.network_df, ['arc_index'])
        self.network_df['arc_index'] = self.arc_index

        if include_successor_list:
            key_columns_not_exists(self.network_df, ['arc_successor_index_list'])

            if self.arc_successor_index_list is None:
                logging.warning('Successor index list not yet calculated')
                raise AttributeError

            self.network_df['arc_successor_index_list'] = np.nan
            self.network_df['arc_successor_index_list'] = self.network_df[
                'arc_successor_index_list'].astype(object)

            self.network_df.at[:, 'arc_successor_index_list'] = \
                self.arc_successor_index_list

    def create_pytable(self,
                       path,
                       overwrite=False):
        """Store network info as a pytable, to be used for constructing
        shortest path graph.

        Arg:
            path (str): path to pytable object.
            overwrite (str): can override existing table, but use this very
            carefully. Default should alway be False otherwise a lot of hour's
            computation time can be quickly overwritten.

        Raise:
            ValueError: if file already exists and it shouldn't be
                over-written.
        """
        file_exists = os.path.isfile(path)
        if overwrite is False and file_exists:
            logging.error('File {} already exists.'.format(path))
            raise ValueError
        elif file_exists:
            logging.warning('File {} will be overwritten'.format(path))
            a = input("Press 'y' to continue")
            if a != 'y':
                logging.error("Entered `{}`. Unable to confirm if "
                              "the file should be overwritten, "
                              "so aborting".format(a))
                raise ValueError

        if self.arc_successor_index_list is None:
            logging.error('Successor index is required and can be generated '
                          'by calling `Network(calc_successor=False)` or '
                          '`network.generate_successor_list()`' )
            raise ValueError

        arc_index = self.arc_index
        arc_pair = self.arc_pair
        arc_u = self.arc_u
        arc_v = self.arc_v
        arc_cost = self.arc_cost
        second_key = self.secondary_arc_key
        arc_successor_index_list = self.arc_successor_index_list

        with tb.open_file(path, 'w') as h5file:
            logging.info('Creating a network pytable at {}'.format(path))
            arc_info_group = h5file.create_group(h5file.root, 'arc_info',
                                                 'Network arc info (all are index based)')

            h5file.create_array(arc_info_group, 'arc_index', arc_index,
                                "Arc index (original position starting at 0)")
            h5file.create_array(arc_info_group, 'arc_u', arc_u,
                                "Start node of arc")
            h5file.create_array(arc_info_group, 'arc_v', arc_v,
                                "End node of arc")
            h5file.create_array(arc_info_group, 'arc_pair', arc_pair,
                                "Arc pair '{arc_u}-{arc_v}', can be used as "
                                "a  secondary key")
            h5file.create_array(arc_info_group, 'arc_cost', arc_cost,
                                "Cost of traversing arc")

            if self.second_key:
                h5file.create_array(arc_info_group, 'secondary_key',
                                    second_key, "Secondary key to trace the "
                                                "network back to its origins")
            vlarray = h5file.create_vlarray(arc_info_group,
                                            'arc_successor_index_list',
                                            tb.Atom.from_dtype(arc_v.dtype),
                                            "Successor arc indices of arc u-v",
                                            filters=tb.Filters(1))
            logging.info('Writing successor arcs')
            for success_index in arc_successor_index_list:
                vlarray.append(success_index)
            logging.info('Pytable successfully created.')
            logging.info(h5file)

        self.network_file = path


class ShortestPath:
    """Calculate the shortest path from a network file."""

    def __init__(self,
                 solver='Floyd-Warshall',
                 in_memory=False):
        """
        Arg:
            solver (str): shortest-path algorithm to use, currently only
                Floyd-Warshall is supported.
            in_memory (bool): whether shortest path calculations should be
                done in memory and stored in the class, or stored in a pytable.
        """
        self.solver = solver
        self.in_memory = in_memory
        self.arc_u = None
        self.arc_v = None
        self.arc_cost = None
        self.arc_index = None
        self.arc_pair = None
        self.arc_successor_index_list = None
        self.pytable_path = None
        self.cost_matrix = None
        self.predecessor_matrix = None
        self.shortest_path_processing_time = None

    def load_from_pytable(self, path):
        """Load network inputs directly from pytable.

        Arg:
            path (str): path to pytable file to load from.
        """
        with tb.open_file(path, 'r') as h5file:
            logging.info('Loading {}'.format(path))
            logging.info(h5file)
            arc_info = h5file.root.arc_info
            self.arc_index = arc_info.arc_index.read()
            self.arc_pair = arc_info.arc_pair.read().astype(str)
            self.arc_u = arc_info.arc_u.read()
            self.arc_v = arc_info.arc_v.read()
            self.arc_cost = arc_info.arc_cost.read()
            self.arc_successor_index_list = np.array([np.array(x) for x in
                arc_info.arc_successor_index_list])

        self.pytable_path = path

    def load_from_network(self, network):
        """Load from Network class

        Arg:
            network (Network): load directly from network class
        """
        self.arc_index = network.arc_index
        self.arc_pair = network.arc_pair
        self.arc_u = network.arc_u
        self.arc_v = network.arc_v
        self.arc_cost = network.arc_cost
        self.arc_successor_index_list = np.array([np.array(x) for x in
            network.arc_successor_index_list])

    def set_network(self, arc_u, arc_v, arc_cost=None):
        """Set the network properties directly and calculate additional once if
        not specified"

        Arg:
            arc_u (list): start vertex of each arc 'i'
            arc_v (list): end vertex of each arc 'i'
            arc_cost (list <int>): cost of traversing arc 'i', if not
                specified, unit 1 is given.
        """
        if arc_cost is None:
            n_arcs = len(arc_u)
            arc_cost = [1] * n_arcs

        temp_df = pd.DataFrame({'arc_u': arc_u,
                                'arc_v': arc_v,
                                'arc_cost': arc_cost})
        temp_network = Network(temp_df)
        self.load_from_network(temp_network)

    def calc_shortest_path_internal(self):
        """Calculate the shortest path and set the distance matrix internally.
        """
        t_start = clock()
        d_np, p_np = shortest_paths.SP(self.arc_cost,
                                       self.arc_successor_index_list)
        self.cost_matrix = d_np
        self.predecessor_matrix = p_np
        self.shortest_path_processing_time = clock() - t_start
        logging.info('Shortest path calculations took {} seconds'.format(
            round(self.shortest_path_processing_time, 0)))

    def store_shortest_path_internal(self, pytable_path=None):
        """Store the shortest path to a pytable

        Arg:
            pytable_path (str): path to pytable, if not set, the internally
                flagged one will be used. A new table can be created,
                but it is STRONGLY advised against, since it will only have
                the index pairs. The remaining network info is critical for
                using it.
        """
        if pytable_path is None:
            pytable_path = self.pytable_path
        with tb.open_file(pytable_path, 'a') as h5file:
            logging.info('Writing shortest path info to {}'.format(pytable_path))
            filters = tb.Filters(complevel=1)
            sp_info = h5file.create_group(h5file.root, 'shortest_path_info',
                                          'Shortest path info for network')

            l = self.cost_matrix.shape[0]

            cost_matrix = h5file.create_carray(sp_info,
                                               'cost_matrix',
                                               tb.Int32Col(),
                                               shape=(l, l),
            title='shortest path cost matrix between all arc indices',
                                               filters=filters)
            predecessor_matrix = h5file.create_carray(sp_info,
                                                     'predecessor_matrix',
                                                     tb.Int32Col(),
                                                     shape=(l, l),
            title='shortest path predecessor index matrix between all arc indices',
                                                     filters=filters)

            cost_matrix[:, :] = self.cost_matrix
            predecessor_matrix[:, :] = self.predecessor_matrix
            logging.info('Shortest path info added.')
            logging.info(h5file)

    def calc_shortest_path_pytable(self, pytable_path=None):
        """Calculate the shortest path and set the distance matrix in pytable.

        Arg:
            pytable_path (str): path to pytable, if not set, the internally
                flagged one will be used. A new table can be created,
                but it is STRONGLY advised against, since it will only have
                the index pairs. The remaining network info is critical for
                using it.
        """

        t_start = clock()
        if pytable_path is None:
            pytable_path = self.pytable_path

        with tb.open_file(pytable_path, 'a') as h5file:
            logging.info(
                'Writing shortest path info to {}'.format(pytable_path))
            filters = tb.Filters(complevel=1)
            sp_info = h5file.create_group(h5file.root, 'shortest_path_info',
                                          'Shortest path info for network')

            l = self.arc_cost.shape[0]

            cost_matrix = h5file.create_carray(sp_info,
                                               'cost_matrix',
                                               tb.Int32Col(),
                                               shape=(l, l),
            title='shortest path cost matrix between all arc indices',
                                               filters=filters)
            predecessor_matrix = h5file.create_carray(sp_info,
                                                      'predecessor_matrix',
                                                      tb.Int32Col(),
                                                      shape=(l, l),
            title='shortest path predecessor index matrix between all arc indices',
                                                      filters=filters)

            logging.info('Shortest path info added.')

            shortest_paths.SP_pytable(self.arc_cost,
                                      self.arc_successor_index_list,
                                      cost_matrix, predecessor_matrix)

            t_end = clock() - t_start
            self.shortest_path_processing_time = t_end
            logging.info('Shortest path calculations took {} seconds'.format(
                round(t_end, 0)))

            h5file.create_array(sp_info, 'calculation_time', np.array([t_end]),
                                "Shortest path calculation time (seconds)")
            logging.info('Done')
            logging.info('h5file')
