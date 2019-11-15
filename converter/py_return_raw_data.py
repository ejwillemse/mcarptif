'''
Created on 05 Jun 2012

@author: elias
'''
import os

def return_raw_data(file_path):
    
    dataFile = open(file_path)
    dataList = dataFile.readlines() 
    dataFile.close()
    
    name = ''
    node = 0
    req_arcs = 0
    noreq_arcs = 0
    req_edges = 0
    noreq_edges = 0
    vehicles = 0
    capacity = 0
    dumping_cost = 0
    max_trip = 0
    ndepots = 0
    nIFs = 0
    problem_size = 0


    req_edges_begin = False
    noreq_edges_begin = False
    req_edgesL = []
    noreq_edgesL = []
    
    for line in dataList:
        info = line.split()
        print(info)
        if line.find('NAME : ') != -1: name = info[2][:-4]
        elif line.find('NODES') != -1: node = info[2]
        elif line.find('REQ_ARCS') != -1:
            if len(info) > 2: req_arcs = info[2]
        elif line.find('NOREQ_ARCS') != -1:
            if len(info) > 2: noreq_arcs = info[2]
        elif line.find('REQ_EDGES') != -1:
            if len(info) > 2: req_edges = info[2]
        elif line.find('NOREQ_EDGES') != -1:
            if len(info) > 2: noreq_edges = info[2]
        elif line.find('VEHICLES') != -1: vehicles = info[2]
        elif line.find('CAPACITY') != -1: capacity = info[2]
        elif line.find('DUMPING_COST') != -1: dumping_cost = info[2]
        elif line.find('MAX_TRIP') != -1: max_trip = info[2]
        elif line.find('DEPOT') != -1: ndepots = len(info[2].split(','))
        elif line.find('DUMPING_SITES') != -1: nIFs = len(info[2].split(','))
    
    problem_size = req_arcs + 2*req_edges
    return(name,
           node,
           problem_size,
           req_arcs,
           noreq_arcs,
           req_edges,
           noreq_edges,
           vehicles,
           capacity,
           dumping_cost,
           max_trip,
           ndepots,
           nIFs,
           problem_size)
        
if __name__=="__main__":
    print(return_raw_data('Raw_input/Lpr_IF/Lpr_IF-c-05.txt'))