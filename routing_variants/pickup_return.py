"""
Custom functions for variants of the MCARPTIF
"""
import numpy as np
import tables as tb
import logging


class PickUpReturn:
    """Variant where vehicles take a container from a client to the nearest
    offload site and then returns it. For this variant, an additional service
    cost of travelling to and from the offloads are added.
    """

    def __init__(self, required_arcs, offload_arcs, arc_h5_path):
        """
        Arg:
            required_arcs (list <int>): indices of all required arcs.
            offload_arcs (list <int>): indices of offload arcs.
            cost_matrix (np.array <int, int>): cost matrix for arcs, including
            the required arcs and offload arcs
        """
        self.required_arcs = required_arcs
        self.offload_arcs = offload_arcs
        self.arc_h5_path = arc_h5_path

        self.min_offload_costs = None
        self.min_offload_arc = None

    def calculate_offload_costs(self):
        """Calculate the best offload cost and IF."""
        logging.info('Calculating pickup and return trip length')
        required_arcs = self.required_arcs
        with tb.open_file(self.arc_h5_path, 'r') as h5file:

            sp_info = h5file.root.shortest_path_info
            cost_matrix = sp_info.cost_matrix

            offload_costs_to = cost_matrix[required_arcs, :]
            offload_costs_to = offload_costs_to[:, self.offload_arcs]

            offload_costs_from = cost_matrix[self.offload_arcs, :]
            offload_costs_from = offload_costs_from[:, required_arcs].T

            offload_costs = offload_costs_to + offload_costs_from

            self.min_offload_costs = np.min(offload_costs, axis=1)
            self.min_offload_arc = self.offload_arcs[np.argmin(offload_costs, axis=1)]
