# -*- coding: utf-8 -*-
"""Calculating and returning shortest paths for a connected graph.

TODO:
    Add shortest-path calculations
    Link with profiler compare different speed-up packagest.

History:
    Created on 3 April 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""


def sp_full(p_full, origin, destination, full=False):
    """Returns the full shortest path between two vertices.

    Arg:
        info.p_full (n*n matrix): predecessor arc before v on the shortest path
            between arcs u and v.

        origin (int): origin arc from where the shortest path starts
        destination (int): destination arc where the shortest path ends.

    Kwarg:
        full (bool): whether the origin and destination arcs should be included
            in the shortest path

    Raises:
        AttributeError: when the destination arc cannot be reaced from the
            origin.

    Return:
        path (list): arc visitation sequence for the shortest path from the
            origin to destination arc. This means there is something wrong with
            the input data.
    """
    path = []
    p_origin = p_full[origin]
    n_arcs = len(p_origin)
    v = destination

    #TODO: hack, for error in p_full when the precedessor p_full[i][i] = 0 instead of i.
    if origin == destination:
        return path

    while True:
        v = p_origin[v]
        if v == origin:
            break
        path.insert(0, v)
        #  At worst all other arcs should be visited, otherwise there is a cycle
        #  in the graph and the destination cannot be reached.
        if len(path) == n_arcs:
            raise AttributeError('Destination `{0}` could not be reached from '
                                 '`{1}`.'.format(destination, origin))

    if full:
        path.insert(0, origin)
        path.append(destination)

    return path
