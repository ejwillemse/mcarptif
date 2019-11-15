'''
Created on 21 Jan 2012

@author: elias
'''

import numpy as np

def route_IF_cost_stats(route, d, IF_cost):
    costs = np.zeros(len(route)-1, int)
    for i in range(len(route)-1):
        costs[i] = IF_cost[route[i]][route[i+1]] - d[route[i]][route[i+1]]
    average = np.average(costs)
    max_s = np.max(costs)
    min_s = np.min(costs)
    std = np.std(costs)
    return(average, max_s, min_s, std)