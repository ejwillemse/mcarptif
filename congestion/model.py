# -*- coding: utf-8 -*-
"""Simulate waste collection vehicles that have to off-load waste at facilities
that account for congestion.

The simulation employs agent-based-modelling and extends on the MCARPTIF [1].

Waste collection vehicles are modelled as agents. Each vehicle has predefined
set of arcs to service in a specific sequence, given as a route. Vehicles have 
autonomy on when they want to off-load waste at facilities, but without 
exceeding their available carrying capacity. Off-loading time at the facility 
depends on the number of other agents already at the facility. The objective
of each agents is to minimize the total time to complete the route.

The scenario modelled is that of a local authority assign service areas to sub-
contractors in the form of a service schedule of arcs. Contractors have limited
autonomy on when to offload waste.

Future extensions:

    1. Allow vehicles to plan when to start their route, subject to total
        time duration restrictions.
    2. Allow vehicles to plan their service sequence.
    3. Compare an autonomous approach with a system approach where facility
        visits are pre-scheduled taking congestion into account, with the 
        objective to minimise total system cost, instead of individual vehicle 
        costs. Vehicles will therefore have zero autonomy.

References:
    
    [1] Willemse, E. J. (2016). Heuristics for large-scale Capacitated Arc 
        Routing Problems on mixed networks (Doctoral dissertation, 
        University of Pretoria).

History:
    Created on 26 Feb 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""