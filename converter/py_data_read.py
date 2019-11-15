'''
Created on 26 Sep 2011

@author: elias
'''

import pickle

class ReadArcConvertLists(object):
    
    def __init__(self, filename):
        fileOpen = open(filename, "rb")
        data = pickle.load(fileOpen)
        fileOpen.close()
        (self.name,
        self.capacity,
        self.maxTrip,
        self.dumpCost,
        self.nArcs,
        self.depotArc,
        self.IFarcs,
        self.ACarcs,
        self.beginL,
        self.endL,
        self.serveCostL,
        self.travelCostL,
        self.demandL,
        self.invArcL,
        self.sucArcL,
        self.allIndexD,
        self.reqArcList,
        self.reqArcListActual,
        self.reqArcs_map,
        self.reqEdgesPure,
        self.reqArcsPure,
        self.reqInvArcL,
        self.depotnewkey,
        self.IFarcsnewkey,
        self.ACarcsnewkey) = data

class ReadSPdata(object):
    def __init__(self, filename):
        fileOpen = open(filename, "rb")
        data = pickle.load(fileOpen)
        fileOpen.close()
        (self.d_full,
         self.p_full) = data

class ReadData(object):    
    def __init__(self, filename):
        fileOpen = open(filename, "rb")
        data = pickle.load(fileOpen)
        fileOpen.close()
        (self.name,
         self.capacity,
         self.maxTrip,
         self.dumpCost,
         self.nArcs,
         self.reqArcList,
         self.reqArcListActual,
         self.depotnewkey,
         self.IFarcsnewkey,
         self.ACarcsnewkey,
         self.reqEdgesPure,
         self.reqArcsPure,
         self.reqInvArcList,
         self.serveCostL,
         self.demandL,
         self.d,
         self.if_cost_np,
         self.if_arc_np) = data

if __name__ == "__main__":       
    print('Test read problem data on Lpr_IF_data_set/problem_info/Lpr-b-05_problem_info.dat')
    directory = 'Actonville_3Feb2012_presentation'
    filename = 'Actonville_problem_info.dat'
    print(directory)
    DirectoryPath = 'Input_data/' + directory + '/problem_info/' + filename
    info = ReadData(DirectoryPath)
    print('')
    print(info.name)
    print(info.capacity)
    print(info.maxTrip)
    print(info.dumpCost)
    print(info.nArcs)
    print(info.reqArcList)
    print(info.reqInvArcList)
    print(info.reqArcListActual)
    print(info.depotnewkey)
    print(info.IFarcsnewkey)
    print(info.serveCostL)
    print(info.demandL)
    print(info.d)
    print(info.if_cost_np)
    print(info.if_arc_np)
    print('')
    print('Done with test')