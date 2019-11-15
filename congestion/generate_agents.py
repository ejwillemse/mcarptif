# -*- coding: utf-8 -*-
"""Generate routes for the MCARPTIF.

This module generates routes for the Mixed Capacitated Arc Routing Problem under
Time Restrictions with Intermediate Facilities (MCARPTIF) using constructive,
improvement and metaheuristics from [1].

The formal of the routes is somewhat cumbersome, and is therefore converted to a
standardized Comma-Separated-Value (CSV).

TODO:
    * Document standardized CSV format.
    
References:
    
    [1] Willemse, E. J. (2016). Heuristics for large-scale Capacitated Arc
        Routing Problems on mixed networks. PhD thesis, University of Pretoria,
        Pretoria. Available online from
        http://hdl.handle.net/2263/57510 (Last viewed on 2017-01-16).
        
History:
    Created on 26 Feb 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import pandas as pd
import sys
from io import StringIO

import sys
sys.path.append('../MCARPTIF_solvers/Input_TestData/')
sys.path.append('../MCARPTIF_solvers/MS/')
import ruin_recreate  # used to construct and improve solutions


def generate_solution(instance_info, nn_list, improvement_procedure='TS'):
    """Construct and improve a solution for the MCARPTIF using ruin_recreate
    procedures.
    
    Arcs:
        instance_info (class): information of the problem instance.
        nn_list (list): nearest neighbour-lists required for Local Search.
        improvement_procedure (str): type of improvement procedure to setup,
            with `LS` (for Local Search) and `TS` (for Tabu Search) recognized.
        
    Returns:
        solution (dict): a full solution dictionary of the improved solution.
    """
    
    solution = ruin_recreate.create_improve_MCARPTIF(
                    instance_info, 
                    nn_list, 
                    improvement_procedure=improvement_procedure)
    
    return solution


def encode_solution_csv(instance_info, solution, dump_costs=None):
    """
    Encode the solution into a comma-separated-value file, which makes for 
    easier verification.
    
    Args:
        instance_info (class): information of the problem instance.
        solution (dict): a full solution dictionary of the improved solution.
        dump_costs (list of list): dumpCosts for all vehicle routes and
            subroutes, when calculated externally. Else, default is used.
        
    Returns:
        solution_csv (str): a comma-separated-value format of the solution with
            appropriate column headings.
    """
    
    depot = instance_info.depotnewkey
    facilities = instance_info.IFarcsnewkey
    capacity = instance_info.capacity
    max_trip = instance_info.maxTrip
    demand = instance_info.demandL
    serve_cost = instance_info.serveCostL
    d = instance_info.d
    if dump_costs is None:
        dump_cost = instance_info.dumpCost
    
    headings = ['Route', 'Subroute', 'ActivityID', 'ActivityType', 
                'TravelTimeToActivity', 'ActivityTime', 'ActivityDemand', 
                'RemainingCapacity', 'RemainingTime', 
                'CumDemand', 'CumTime']
    
    solution_csv = ','.join(headings) + '\n'
    n_routes = solution['nVehicles']
    for vehicle_i in range(n_routes):
        n_subroutes = solution[vehicle_i]['nTrips']
        for subroute_i in range(n_subroutes):
            prev_arc = depot
            subroute = solution[vehicle_i]['Trips'][subroute_i]
            
            if subroute[-1] in facilities:
                subroute.append(subroute[-1])
            elif subroute[-2] in facilities:
                subroute.insert(-2, subroute[-2])
                
            for i, arc in enumerate(subroute):
                if arc == depot:  # depots is basically a reset
                    if i == 0:
                        serve_type = 'depot_start'
                        time_to_arc = 0
                        cum_demand = 0
                        cum_time = 0
                        remain_cap = capacity
                        remain_time = max_trip
                    else:
                        serve_type = 'depot_end'
                        time_to_arc = d[prev_arc][arc]
                        remain_time -= time_to_arc
                        cum_time += time_to_arc
                        if prev_arc in facilities:
                            remain_cap = capacity
                            cum_demand = 0
                    arc_serve_time = 0
                    arc_demand = 0
                elif arc in facilities:
                    if i == 0:  # first IF visit is a partial reset
                        serve_type = 'depart_if'
                        time_to_arc = 0
                        arc_serve_time = 0
                    elif prev_arc not in facilities:
                        # last IF visit is the actual offload
                        serve_type = 'arrive_if'
                        time_to_arc = d[prev_arc][arc]
                        arc_serve_time = 0
                        remain_time -= time_to_arc
                        cum_time += time_to_arc
                    else:
                        serve_type = 'offload'
                        time_to_arc = 0
                        if dump_costs is not None:
                            arc_serve_time = dump_costs[vehicle_i][subroute_i]
                        else:
                            arc_serve_time = dump_cost
                        remain_time -= arc_serve_time
                        cum_time += arc_serve_time
                        remain_cap = capacity
                        cum_demand = 0
                    arc_demand = 0
                else:
                    serve_type = 'collect'
                    time_to_arc = d[prev_arc][arc]
                    arc_serve_time = serve_cost[arc]
                    arc_demand = demand[arc]
                    remain_cap -= demand[arc]
                    remain_time -= (time_to_arc + arc_serve_time)
                    cum_demand += demand[arc]
                    cum_time += time_to_arc + arc_serve_time
                prev_arc = arc
                
                line_info = [vehicle_i, subroute_i, arc, serve_type, 
                             time_to_arc, arc_serve_time, arc_demand, 
                             remain_cap, remain_time, cum_demand, cum_time]
                solution_csv += ','.join(str(bit) for bit in line_info) + '\n'
    
    return solution_csv
                    

def encode_solution_df(solution_csv):
    """
    Decode the csv solution into a pandas dataframe
    
    Args:
        solution_csv (str): a comma-separated-value format of the solution with
            appropriate column headings.
        
    Returns:
        solution_df (pandas dataframe): a pandas data frame of the solution
            which allows for easier analysis and manipulation.
    """
    
    solution_df = pd.read_csv(StringIO(solution_csv))

    return solution_df


def create_agents(solution_df):
    """
    Create individual agents using the solution dataframe.

    Args:
        solution_df (pandas dataframe):

    Returns:
        agents (dict of route dataframes): a dictionary of routes, each encoded
            as a pandas data frame.
    """

    agents = {}
    route_ids = pd.unique(solution_df['Route'])
    for agent_key, route_i in enumerate(route_ids):
        agents[agent_key] = solution_df.query('Route == {0}'.format(route_i))

    return agents


def initialise_agents(instance_info, nn_list, improvement_procedure='TS'):
    """Create agents that service the given instance area.

    Args:
        instance_info (class): information of the problem instance.
        nn_list (list): nearest neighbour-lists required for Local Search.
        improvement_procedure (str): type of improvement procedure to setup,
            with `LS` (for Local Search) and `TS` (for Tabu Search) recognized.

    Returns:
        agents (dict of route data frames): a dictionary of routes, each encoded
            as a pandas data frame.
    """

    solution = generate_solution(instance_info, nn_list, improvement_procedure)
    solution_csv = encode_solution_csv(instance_info, solution)
    solution_df = encode_solution_df(solution_csv)
    agents = create_agents(solution_df)

    return agents


def add_agent(agents, agent_df):
    """Add a new agent to the population.

    Args:
        agents (dict of route dataframes): a dictionary of routes, each encoded
            as a pandas data frame.
        agent_df (pandas dataframe): dataframe of the new agent to add.

    Returns:
        agents (dict of route dataframes): dictionary of routes, with the new
            agent added and allocated a unique ID.
    """

    max_id = max(agents.keys())
    agents[max_id + 1] = agent_df.copy()

    return agents


def remove_agent(agents, agent_key):
    """Remove an agent from the population.

    Args:
        agents (dict of route dataframes): a dictionary of routes, each encoded
            as a pandas data frame.
        agent_key (key): key of agetnt to be removed
    Returns:
        agents (dict of route dataframes): dictionary of routes, with the agent
            with the key removed.
    """

    del agents[agent_key]

    return agents
