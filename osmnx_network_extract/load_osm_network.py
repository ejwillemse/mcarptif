# -*- coding: utf-8 -*-
"""Prepare the OSM extracted network for arc routing.

This includes extracting the network, extracting it's key components,
and removing it's disconnected vertices.

History:
    Created on 12 June 2020
    @author: Elias J. Willemse
    @contact: ejwillemse@gmail.com
"""
import networkx as nx
import osmnx as ox
import pandas as pd
import logging


def find_disconnected_subgraphs(G):
    """Find all the disconnected subgraphs, and return their verticles as a
    pandas dataframe

    Args:
        G (networkx.graph): bidirectional graph returned via OSMNX.
    """
    disconnected_group = []
    disconnected_len = []
    disconnected_members = []
    disconnected_group_sum = []
    disconnected_len_sum = []
    logging.info('Finding the disconnected subgraphs and ordering them')
    disconnect_subgraph = sorted(nx.kosaraju_strongly_connected_components(G),
                                 key=len,
                                 reverse=True)
    n_subgraphs = len(disconnect_subgraph)
    logging.info('Number of subgraphs found: {}'.format(n_subgraphs))
    for i, c in enumerate(disconnect_subgraph):
        n = len(c)
        disconnected_group += [i] * n
        disconnected_len += [n] * n
        disconnected_members += list(c)

        disconnected_group_sum += [i]
        disconnected_len_sum += [n]

    subgraph_summary_df = pd.DataFrame({'subgraph': disconnected_group_sum,
                                        'n_vertices': disconnected_len_sum})
    subgraph_df = pd.DataFrame(
        {'subgraph': disconnected_group, 'n_vertices': disconnected_len,
         'u': disconnected_members})
    return subgraph_summary_df, subgraph_df


def remove_subgraphs(G, keep=None):
    """Remove all disconnected components of the network graph G.
    Arg:
        G (networkx.graph): bi-graph from the ox package
        keep (list): list of subgraphs to keep, from largest to smallest.
            Default is [0], only keep the largest sub-graph.
    """
    logging.info('Checking if network is strong connected')
    G = G.copy()
    strong_connected = nx.is_strongly_connected(G)
    logging.info('Network strongly connected: {}'.format(strong_connected))
    if not strong_connected:
        logging.info("Proceeding to remove disconnected vertices")
        if keep is None:
            keep = [0]
        n_edges = G.number_of_edges()
        n_nodes = G.number_of_nodes()
        subgraphs_sum, subgraphs = find_disconnected_subgraphs(G)
        subgraph_remove = subgraphs.loc[~subgraphs['subgraph'].isin(keep)]
        logging.info("Removing nodes from subgraph...")
        G.remove_nodes_from(subgraph_remove['u'])
        logging.info('n Edges removed: {}'.format(n_edges -
                                                 G.number_of_edges()))
        logging.info('n Nodes removed: {}'.format(n_nodes -
                                                 G.number_of_nodes()))
    strong_connected = nx.is_strongly_connected(G)
    logging.info('Network strongly connected: {}'.format(strong_connected))
    return G


def return_customer_filter():
    """Return custom filter to use for OSM extraction
    """
    drive_service_all = '["area"!~"yes"]["highway"!~"cycleway|footway|path|pedestrian|steps|track|corridor|elevator|escalator|proposed|construction|bridleway|abandoned|platform|raceway"]["motor_vehicle"!~"no"]["motorcar"!~"no"]'
    exclude_emergency_services = '["service"!~"emergency_access"]'
    exclude_custom_services = '["access"!~"private"]["service"!~"parking|parking_aisle|private|emergency_access"]'
    exclude_parking_privarte_emergency = '["access"!~"private"]["service"!~"parking|private|emergency_access"]'
    exclude_private = '["access"!~"private"]["service"!~"private"]'
    custom_filter = drive_service_all + exclude_emergency_services
    return custom_filter


def load_network(location='Singapore'):
    """Load OSM road-network, requires internet.

    Arg:
        location (str): location to extract, can be a city name.
        include_emergency (bool): whether emergency roads should be included in
            the network.
    """
    custom_filter = return_customer_filter()
    G = ox.graph_from_place(query=location, custom_filter=custom_filter)
    return G


def format_graph(G):
    """Format loaded graph and add index and node attributes.

    Arg:
        G (ox.graph): graph loaded using networkx.
    """
    pass
