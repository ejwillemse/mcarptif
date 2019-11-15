# -*- coding: utf-8 -*-
"""Re-plan individual facility visits for waste collection vehicles of an 
MCARPTIF solution.

This module re-plans intermediate facility visits for waste collection vehicles
with the objective to reduce the total time required by each vehicle to 
complete its route.

The arcs to service and service sequence is fixed. The timing of the 
intermediate facility visits can be changed by relocating it in the service 
sequence, but while ensuring that capacity of a vehicle is not exceeded. 
Additional or less facility visits can be performed if required.

It is assumed the vehicle follows the same route day after day, and that the 
route being evaluated is that after the first day.

The following two extensions are considered:

    1. A vehicle must offload its waste before returning to the depot at the 
        end of its route.
    2. A vehicle may return directly to the depot, but will then start the same
        route with the left-over waste from the previous day.

When visiting an intermediate facility, the off-loading time can be either:

    1. Constant.
    2. Random, according to a distribution.
    3. Dependent on how many vehicles are currently at the facility.
    4. Random, with the distribution parameters dependent on how many vehicles
        are currently at the facility.
    5. Based on a discrete event simulation model with two consecutive resources,
        each following size-time distributions.
        
Each vehicle can re-plan its own visits, but is unaware of the plans of other
vehicles.

TODO:
    * Extension (2) on the offload timing, and (2), (4) and (5) on the offload
        duration.

History:
    Created on 26 Feb 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""
