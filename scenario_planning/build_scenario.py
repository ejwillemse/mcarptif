"""Build scenario for planning purposes, to be used with jupyter lab and
widgets"""

from IPython.display import display, HTML
from ipywidgets import interact, interactive, fixed, interact_manual
import ipywidgets as widgets
import pandas as pd
import networkx as nx


def calculate_shortest_paths(origins, destinations):
    """Calculate the shortest paths and return the dataframe of edges in the
    path, as well as a dictionary of the paths and their distances.
    """
    routes = []
    distance_matrix = {}


def generate_instance_info(arc_file,
                           depot,
                           IF,
                           required_arcs,
                           inv_list):
    """Generate all the instance info required for solving the MCARPTIF:

    Args:
        sp_file (str): path to arc .h5 file, including shortest path.
        depot (list): indices of depot
        IF (list): indices of IF
        required_arcs (list): indices of required arcs
        inverse list of edges (list): indices of inverse arcs of edges.
    """
    pass