
# Read data from Lpr MCARP based instance set
# Creator: Elias Willemse (ejwillemse@gmail.com)

# Derived from the article:
# Lacomme, P., Prins, C., Ramdane-Cherif, W. (2000). Competitive Memetic 
# Algorithms for Arc Routing Problems. Annals of Operations Research, 131(4) 
# p. 159-185.
# Specifically pages 161-162.

import pyximport
import numpy
pyximport.install(setup_args={"include_dirs":numpy.get_include()})

import pickle
import os

#NB! Find and fix memory leak
#import c_alg_shortest_paths

import converter.py_data_read as py_data_read
import converter.c_alg_shortest_paths as c_alg_shortest_paths

#===============================================================================
# Read data from standard text file
#===============================================================================
class ArcInfo(object):
    
    def __init__(self, filePath):
        ''' 
        Initiate standard data for lpr instances. Possible extenstions are also 
        initiated, such as intermediate facilities and a mximum vehicle trip 
        length. Current format can not cope with multiple depots (future work). 
        '''
        self.filePath = filePath
        self.name = None
        self.dataFile = open(self.filePath)
        self.dataList = self.dataFile.readlines()
        self.nonReqArcs = None # One-ways without waste
        self.nonReqEdges = None # Two-ways without waste
        self.reqArcs = None # One-ways or splitted large two-ways with waste
        self.reqEdges = None # Small one-waste with waste. Zig-zag collections
        self.depot = None # Single vehicle depot
        self.IFs = None # Multiple dumpsites
        self.ACs = None # Multiple access points
        self.nVehicles = None # Number of avaialable vehicles - assuming homogenious fleet
        self.capacity = None # Capacity of each vehicle - assuming homogenious fleet
        self.maxTrip = None # Maximum trip length (usually time) of a vehicle e.g. 8 hours
        self.dumpCost = None # Cost or time of unloading at a dumpsite
            
    def problemInfo(self):
        '''
        Gets all the basic info from the text file. Everything except arcs and
        edges. 
        '''
        inputList = self.dataList
        for line in inputList:
            if line.find('NAME') != - 1: # get problem name and convert to a single string.
                nameWithExt = (line.split())[2] 
                self.name = nameWithExt[:nameWithExt.find('.')]
            if line.find('VEHICLES') != - 1: # get number of vehicles and convert to integer.
                self.nVehicles = int((line.split())[2])
            if line.find('CAPACITY') != - 1: # get vehicle capacity and convert to integer
                self.capacity = int((line.split())[2])
            if line.find('DUMPING_COST') != - 1: # get dumping cost and convert to integer
                self.dumpCost = int((line.split())[2])
            if line.find('MAX_TRIP') != - 1: # get the maximum trip length and convert to integer
                self.maxTrip = int((line.split())[2]) 
            if line.find('DEPOT') != - 1: # get depot and convert to integer. For multiple depots this will be a list
                self.depot = int((line.split())[2])
            if line.find('DUMPING_SITES') != - 1:# get dumping sites or IFs and converts to List. IFs must be seperated by ',' in data file
                IFstring = ((line.split())[2]).split(',')
                _IFs = []
                for i in IFstring:
                    _IFs.append(int(i))                
                self.IFs = _IFs
            if line.find('ACCESS_SITES') != - 1:# get dumping sites or IFs and converts to List. IFs must be seperated by ',' in data file
                APstring = ((line.split())[2]).split(',')
                _APs = []
                for i in APstring:
                    _APs.append(int(i))                
                self.ACs = _APs
                
    def reqArcInfo(self, ArcLine):
        '''
        Standard dictionary containing required arc (with waste) info. Single 
        line is split and appropriate data stored. Data file must be in the 
        sequence '(v, u)  serv_cost : x trav_cost : y demand : z'.
        '''
        arcInfo = ArcLine.split() # Split line in conjunction with spaces.
        nodesTemp = arcInfo[0].replace('(', '') # Determine begin and end nodes. Converts string to a list.
        nodesTemp = nodesTemp.replace(')', '')
        nodesTemp = nodesTemp.split(',')
        arcNodes = (int(nodesTemp[0]), int(nodesTemp[1]))
        reqArcsDict = {}
        reqArcsDict['nodes'] = arcNodes # standard entry data
        reqArcsDict['serv_cost'] = int(arcInfo[2])
        reqArcsDict['trav_cost'] = int(arcInfo[4])
        reqArcsDict['demand'] = int(arcInfo[6])
        return(reqArcsDict)
        
    def nonReqArcInfo(self, ArcLine):
        '''
        Standard dictionary containing non-required arc (no waste) info. Single 
        line is  split and appropriate data stored. Data file must be in the 
        sequence 
        '(v, u)  serv_cost : x  cost : y'.
        '''
        arcInfo = ArcLine.split() # Split line in conjunction with spaces.
        nodesTemp = arcInfo[0].replace('(', '') # Determine begin and end nodes. Converts string to a list.
        nodesTemp = nodesTemp.replace(')', '')
        nodesTemp = nodesTemp.split(',')
        arcNodes = (int(nodesTemp[0]), int(nodesTemp[1]))
        reqArcsDict = {}
        reqArcsDict['nodes'] = arcNodes # standard entry data
        reqArcsDict['trav_cost'] = int(arcInfo[2])
        return(reqArcsDict)

    def getReqArcs(self):
        '''
        Get required arcs data. Required arcs must begin with 
        'LIST_REQ_ARCS'
        '''
        inputList = self.dataList # All data file lines
        start = False #
        arcs = []
        for line in inputList: # check each line
            if (start == True) & (line[0] != '('): break; # end of required arc data in text file. New file heading.
            if start == True: # start of required arc data in text file.
                info = self.reqArcInfo(line) # generate required arc data line for line.
                arcs.append(info) # generates a list of arc data. List is usefull since there may be same source destination arcs.
            if line.find('LIST_REQ_ARCS') != - 1: start = True # req arcs info starts in data file.
        self.reqArcs = arcs
        
    def getReqEdges(self): # See getReqArcs.
        inputList = self.dataList
        start = False
        edges = []
        for line in inputList:
            if (start == True) & (line[0] != '('): break;
            if start == True:
                info = self.reqArcInfo(line)
                edges.append(info)
            if line.find('LIST_REQ_EDGES') !=- 1: start = True
        self.reqEdges = edges
        
    def getNonReqArcs(self): # See getReqArcs.
        inputList = self.dataList
        start = False
        arcs = []
        for line in inputList:
            if (start == True) & (line[0] != '('): break;
            if start == True:
                info = self.nonReqArcInfo(line)
                arcs.append(info)
            if line.find('LIST_NOREQ_ARCS') !=- 1: start = True
        self.nonReqArcs = arcs
        
    def getNonReqEdges(self): # See getReqArcs.
        inputList = self.dataList
        start = False
        arcs = []
        for line in inputList:
            if (start == True) & (line[0] != '('): break;
            if start == True:
                info = self.nonReqArcInfo(line)
                arcs.append(info)
            if line.find('LIST_NOREQ_EDGES') !=- 1: start = True
        self.nonReqEdges = arcs
        
    def generateAllData(self):
        '''
        Generate all problem date
        '''
        self.problemInfo()
        self.getReqEdges()
        self.getReqArcs()
        self.getNonReqEdges()
        self.getNonReqArcs()
                
#===============================================================================
# Convert text file data into standard lists
#===============================================================================
class ArcConvertLists(ArcInfo):
    
    def __init__(self, fileName=''):
        '''
        Converts data file information to multiple dictionaries. All arcs, 
        depots and dumpsites are assigned unique keys, which are used in all
        dictionaries. Original arcs are stored in allIndexD
        '''
        ArcInfo.__init__(self, fileName)
        self.nArcs = 0 # number of arcs including two arcs per edge, depots and ifs.
        self.depotArc = None # index of the depot arc. Mulitple depots will require a dictionary
        self.IFarcs = [] # List of intermedaite facility arcs
        self.ACarcs = []
        self.beginL = [] # begin node of every arcs u of (u,v)
        self.endL = [] # end node of every arc v of (v,u)
        self.serveCostL = [] # cost of servicing a required arc
        self.travelCostL = [] # cost of travesing any arc
        self.demandL = [] # demand (kg of waste for example) of required arcs
        self.invArcL = [] # inverse of an arc. Applies to edges where each are presented as two arcs, and each being the inverse of the other.
        self.sucArcL = [] # succesor arcs of an arc, i.e. arcs whos begin vertex is the same as the arc in question's en vertex suc(u, v) = (v, x) and (v,y) 
        self.allIndexD = {} # dictionary with arc keys relating the keys back to the original arcs
        self.generateAllData()
        self.generateKeys()
        self.reqArcList = [] # list of all the required arcs.
        self.reqArcListActual = [] # list of all the required arcs.
        self.reqEdgesPure = []
        self.reqArcsPure = []
        self.reqArcs_map = []
        self.reqInvArcL = []
        self.keysIter = -1
        self.depotnewkey = None
        self.IFarcsnewkey = []
        self.ACarcsnewkey = []
        self.outputextension = '_info_lists_pickled.dat'
        self.ban_U2 = False
    
    def generateKeys(self):
        '''
        Determines number unique keys required for all arcs, edges, depots and ifs.
        '''
        nArcKeys = 0
        if self.nonReqArcs: 
            nArcKeys = nArcKeys + len(self.nonReqArcs) # one to one relation. Each arc has on key 
        if self.nonReqEdges: 
            nArcKeys = nArcKeys + 2 * len(self.nonReqEdges) # one to two relation. Each edge has two arcs, each with a key 
        if self.reqArcs: 
            nArcKeys = nArcKeys + len(self.reqArcs) # one to one relation. Each arc has on key 
        if self.reqEdges: 
            nArcKeys = nArcKeys + 2 * len(self.reqEdges) # one to two relation. Each edge has two arcs, each with a key 
        if self.depot: 
            nArcKeys = nArcKeys + 1 # one key per depot
        if self.IFs: 
            nArcKeys = nArcKeys + len(self.IFs) # one key per dumbsite
        if self.ACs: 
            nArcKeys = nArcKeys + len(self.ACs) # one key per dumbsite
        self.nArcs = nArcKeys
    
    def initialiseLists(self):
        self.generateKeys()
        self.beginL = [0]*self.nArcs
        self.endL = [0]*self.nArcs
        self.travelCostL = [0]*self.nArcs
        self.invArcL = [0]*self.nArcs
        self.sucArcL = [[]]*self.nArcs        
            
    def generateDepoIFList(self, depot=None):
        '''
        Generate depot info. Demand, service and traversal cost is included and
        can thus be treated as a required arcs.
        '''
        if depot == None: depot = self.depot
        self.keysIter += 1 # assign depfileNameot or IF the current index
        key = self.keysIter 
        self.allIndexD[key] = (depot, depot) #(v,v)
        self.beginL[key] = depot # Loop arc
        self.endL[key] = depot # Loop arc
        self.reqArcList.append(key)
        self.reqArcs_map.append(key)
        self.reqInvArcL.append(key)
        self.serveCostL.append(0) 
        self.travelCostL[key] = 0
        self.demandL.append(0)
        self.invArcL[key] = key # undirected
    
    def generateNonArcList(self, arc):
        '''
        Generate info for a non-required arcs - also used for required edges. 
        Works with arcs not edges.
        '''
        self.keysIter += 1
        key = self.keysIter 
        self.allIndexD[key] = arc['nodes'] # refers to (u, v)
        self.beginL[key] = arc['nodes'][0] 
        self.endL[key] = arc['nodes'][1] 
        self.travelCostL[key] = arc['trav_cost']
        self.invArcL[key] = None # directed so there is no inverse
    
    def generateNonEdgeList(self, arc):
        '''
        Generates info for non-required edge. Two arcs are created, one for each
        side of the road, and are linked with the inverse key.
        '''
        self.keysIter += 1
        key1 = self.keysIter
        self.keysIter += 1
        key2 = self.keysIter
        
        self.allIndexD[key1] = arc['nodes']
        self.allIndexD[key2] = (arc['nodes'][1], arc['nodes'][0]) # edge reversed
        self.beginL[key1] = self.endL[key2] = arc['nodes'][0] # begin node of one arcs is the same as end node of the opesite arc 
        self.endL[key1] = self.beginL[key2] = arc['nodes'][1] # same as above
        self.travelCostL[key1] = self.travelCostL[key2] = arc['trav_cost'] # both arcs have the same cost
        self.invArcL[key1] = key2 # rever to the opesite arc
        self.invArcL[key2] = key1 #
        return(key1, key2)
    
    def addRequiredData(self, key, arc):
        '''
        Adds demand and service cost to required arcs. With required edge the 
        same information is assigned to both arcs.
        '''
        self.serveCostL.append(arc['serv_cost'])
        self.demandL.append(arc['demand'])
        self.reqArcList.append(key)
        self.reqArcs_map.append(len(self.reqArcList) - 1)
        self.reqArcListActual.append(len(self.reqArcList)-1)
    
    def genSuccesorArcs(self):
        '''
        Generates a dictionary of successor arcs for each arc. Used with 
        shortest path algorithms. Each arc is compared to all other arcs and if
        the begin node is the same as the end node, then it is a successor arc.
        Might be usefull to include turn penalties here by expanding dictionaries.
        Also, successor arcs with TPs dictionary may be provided as input.
        
        Must be a faster way to do this than enumerating both lists.
        '''
        self.sucArcL = []
        if self.ban_U2:
            for i, k in enumerate(self.endL): #Every arc and its endnode
                tempsucArcL = [] 
                for j, l in enumerate(self.beginL):#every arc and its begin node
                    if (k == l) and (i!=self.invArcL[j]):
                        tempsucArcL.append(j)#check if arc j's begin node is same as arc i's end node and add to list
                self.sucArcL.append(tempsucArcL[:])
        else:
            for k in self.endL: #Every arc and its endnode
                tempsucArcL = [] 
                for j, l in enumerate(self.beginL):#every arc and its begin node
                    if k == l:
                        tempsucArcL.append(j)#check if arc j's begin node is same as arc i's end node and add to list
                self.sucArcL.append(tempsucArcL[:])
                
    def generateLists(self):
        '''
        Gnerate all the required dictionaries by calling each of gen 
        definitions for the different type of arcs.
        '''
        self.initialiseLists()
        if self.depot: # generate depot info
            self.generateDepoIFList()
            self.depotArc = self.keysIter # links arc index to depot
            self.depotnewkey = len(self.reqArcList)-1
        if self.IFs: # same as above, only done for each if
            for IF in self.IFs:
                self.generateDepoIFList(IF)
                self.IFarcs.append(self.keysIter)
                self.IFarcsnewkey.append(len(self.reqArcList)-1)
        if self.ACs: # same as above, only done for each if
            for AC in self.ACs:
                self.generateDepoIFList(AC)
                self.ACarcs.append(self.keysIter)
                self.ACarcsnewkey.append(len(self.reqArcList)-1)
        if self.nonReqArcs:
            for arc in self.nonReqArcs:
                self.generateNonArcList(arc)
        if self.nonReqEdges:
            for edge in self.nonReqEdges:
                self.generateNonEdgeList(edge)
        if self.reqArcs:
            for arc in self.reqArcs:
                self.generateNonArcList(arc) # add general info by treating edge as non-required
                self.addRequiredData(self.keysIter, arc) # add required info - service cost and demand
                self.reqInvArcL.append(None)
                self.reqArcsPure.append(len(self.reqArcList)-1)                
        if self.reqEdges:
            for edge in self.reqEdges:
                (key1, key2) = self.generateNonEdgeList(edge) # add general info by creating two arcs for each edge 
                self.reqInvArcL.append(len(self.reqArcList)+1) 
                self.reqInvArcL.append(len(self.reqArcList)) 
                self.addRequiredData(key1, edge) # add required edge info to each arc
                self.reqEdgesPure.append(len(self.reqArcList)-1)
                self.addRequiredData(key2, edge)
        self.genSuccesorArcs()

    def return_data(self):
        self.generateLists()
        data = (self.name,
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
                    self.ACarcsnewkey)
        return data

    def write_info_lists(self, outPutFolder = None, name = None):
        if name is None:
            name = self.name

        if outPutFolder:
            self.generateLists()
            if name is None:
                ActualPath = outPutFolder + self.name + self.outputextension
                self.newname = self.name + self.outputextension
                fileOpen = open(ActualPath, 'wb')
            else:
                fileOpen = open(outPutFolder + name + self.outputextension, 'wb')
            data = (self.name,
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
                    self.ACarcsnewkey)
            pickle.dump(data, fileOpen)
            fileOpen.close()
        else:print('No folder specified')

class CreateInputDataClass(object):

    def __init__(self, input_data):
        (self.name,
        self.RD.capacity,
        self.RD.maxTrip,
        self.RD.dumpCost,
        self.RD.nArcs,
        self.RD.reqArcList,
        self.RD.reqArcListActual,
        self.RD.depotnewkey,
        self.RD.IFarcsnewkey,
        self.RD.ACarcsnewkey,
        self.RD.reqEdgesPure,
        self.RD.reqArcsPure,
        self.RD.reqInvArcL,
        self.RD.serveCostL,
        self.RD.demandL) = input_data

#===============================================================================
#===============================================================================


class WriteInfoLists(object): 
    
    def __init__(self, outputfolder, inputfolder, inputfile=None):
        self.outsub = 'info_lists/'
        self.outextension = '_info_lists_pickled.dat'
        self.outputfolder = outputfolder
        self.inputfolder = inputfolder
        self.inputfile = inputfile
            
    def writeout(self, inputfile):
        filepath = self.inputfolder+inputfile
        acl = ArcConvertLists(filepath)
        acl.outputextension = self.outextension
        acl.write_info_lists(self.outfolderD)
        return(acl.newname)
    
    def execute(self):
        if not os.path.isdir(self.outputfolder):os.mkdir(self.outputfolder)
        self.outfolderD = self.outputfolder + self.outsub
        if not os.path.isdir(self.outfolderD):os.mkdir(self.outfolderD)
        if self.inputfile:
            return(self.writeout(self.inputfile))
        else:
            inputFiles = os.listdir(self.inputfolder)
            for file in inputFiles:
                if file != '.svn':
                    print(file)
                    self.writeout(file)

#===============================================================================
#===============================================================================

class WriteSpIfInputData(object):

    def __init__(self, inputfolder='', inputfile=None):
        self.inputfolder = inputfolder
        self.inputfolder_sub = 'info_lists/'
        self.inputfile = inputfile
        self.sp_out_subfolder = 'sp_full/'
        self.sp_inputfolder_sub = 'sp_full/'
        self.sp_out_extension = '_sp_data_full.dat'
        self.sp_extension = '_sp_data_full.dat'
        self.info_out_subfolder = 'problem_info/'
        self.info_out_extension = '_problem_info.dat'
        self.pre_calc = True

    def return_sp_info(self, info_list):
        cL = info_list.travelCostL
        sL = info_list.sucArcL
        reqArcList = info_list.reqArcList
        dumpCost = info_list.dumpCost
        IFarcsnewkey = info_list.IFarcsnewkey
        depotArc = info_list.depotnewkey

        (d_np,
         p_np,
         d_np_req,
         if_cost_np,
         if_arc_np) = c_alg_shortest_paths.SP_IFs_complete(cL, sL, reqArcList,
                                                            dumpCost, depotArc,
                                                            IFarcsnewkey)
        sp_info = (d_np, p_np)
        instance_info_data = ( info_list.name,
                               info_list.capacity,
                               info_list.maxTrip,
                               info_list.dumpCost,
                               info_list.nArcs,
                               info_list.reqArcList,
                               info_list.reqArcListActual,
                               info_list.depotnewkey,
                               info_list.IFarcsnewkey,
                               info_list.ACarcsnewkey,
                               info_list.reqEdgesPure,
                               info_list.reqArcsPure,
                               info_list.reqInvArcL,
                               info_list.serveCostL,
                               info_list.demandL,
                               d_np_req,
                               if_cost_np,
                               if_arc_np)

        return sp_info, instance_info_data


    def calculateSpIf(self, inputfile=None, input_path=None):
        if inputfile is not None:
            self.RD = py_data_read.ReadArcConvertLists(self.inputfolder + self.inputfolder_sub + inputfile)
        elif input_path is not None:
            self.RD = py_data_read.ReadArcConvertLists(input_path)

        cL = self.RD.travelCostL
        sL = self.RD.sucArcL
        reqArcList = self.RD.reqArcList
        dumpCost = self.RD.dumpCost
        IFarcsnewkey = self.RD.IFarcsnewkey
        depotArc = self.RD.depotnewkey
        if self.pre_calc:
            (self.d_np, 
             self.p_np, 
             self.d_np_req, 
             self.if_cost_np, 
             self.if_arc_np) = c_alg_shortest_paths.SP_IFs_complete(cL, sL, reqArcList, dumpCost, depotArc, IFarcsnewkey)
        else:
            (self.d_np, 
             self.p_np, 
             self.d_np_req, 
             self.if_cost_np, 
             self.if_arc_np) = c_alg_shortest_paths.SP_IFs(cL, sL, reqArcList, dumpCost, depotArc, IFarcsnewkey)            

    def writedata(self, inputfile=None, ext_write=False,
                  output_path=None):
        if ext_write:
            self.RD = py_data_read.ReadArcConvertLists(self.inputfolder + self.inputfolder_sub + inputfile)
            self.outfolderD = self.inputfolder+ self.sp_out_subfolder
            if not os.path.isdir(self.outfolderD):os.mkdir(self.outfolderD)

        if output_path is not None:
            fileoutname = output_path + self.sp_out_extension
        else:
            fileoutname = self.outfolderD + self.RD.name + self.sp_out_extension

        fileout = open(fileoutname,'wb')
        pickle.dump((self.d_np, self.p_np), fileout)
        fileout.close()

        if ext_write:
            self.outfolderD = self.inputfolder + self.info_out_subfolder
            if not os.path.isdir(self.outfolderD):os.mkdir(self.outfolderD)

        if output_path is not None:
            outputfile = output_path + self.info_out_extension
        else:
            outputfile = self.outfolderD + self.RD.name + self.info_out_extension
        fileopen = open(outputfile,'wb')
        writedata = (self.RD.name,
                     self.RD.capacity,
                     self.RD.maxTrip,
                     self.RD.dumpCost,
                     self.RD.nArcs,
                     self.RD.reqArcList,
                     self.RD.reqArcListActual,
                     self.RD.depotnewkey,
                     self.RD.IFarcsnewkey,
                     self.RD.ACarcsnewkey,
                     self.RD.reqEdgesPure,
                     self.RD.reqArcsPure,
                     self.RD.reqInvArcL,
                     self.RD.serveCostL,
                     self.RD.demandL,
                     self.d_np_req,
                     self.if_cost_np,
                     self.if_arc_np)
        pickle.dump(writedata, fileopen)
        fileopen.close()     

    def return_sp_data(self, info_lists):
        self.RD = info_lists


    def execute(self):
        if self.inputfile: 
            print(self.inputfile)
            self.calculateSpIf(self.inputfile)
            self.writedata(self.inputfile)
        else:
            inputFiles = os.listdir(self.inputfolder+self.inputfolder_sub)
            for file_s in inputFiles: 
                if file_s == '.svn':continue
                print(file_s)
                self.calculateSpIf(file_s)
                self.writedata(file_s)

class WriteAllData(object):
    
    def __init__(self, outputfolder, inputfolder, inputfile=None):
        self.outputfolder = outputfolder
        self.inputfolder = inputfolder
        self.inputfile = inputfile
        
    def execute(self):
        if self.inputfile:
            wrt = WriteInfoLists(self.outputfolder, self.inputfolder, self.inputfile) 
            self.inputfile2 = wrt.execute()
            wrtSpIf = WriteSpIfInputData(self.outputfolder, self.inputfile2)
            wrtSpIf.execute()
        else:
            print(self.inputfolder)
            print('Writing lists')
            wrt = WriteInfoLists(self.outputfolder, self.inputfolder)
            wrt.execute()
            print('Writing IF and SP data')
            wrtSpIf = WriteSpIfInputData(self.outputfolder)
            wrtSpIf.execute() 

class ReadData(object):    
    def __init__(self, filename):
        fileOpen = open(filename)
        data = pickle.load(fileOpen)
        fileOpen.close()
        (self.datalists.name,
         self.datalists.capacity,
         self.datalists.maxTrip,
         self.datalists.dumpCost,
         self.datalists.nArcs,
         self.datalists.reqArcList,
         self.datalists.reqArcListActual,
         self.datalists.depotnewkey,
         self.datalists.IFarcsnewkey,
         self.d,
         self.if_cost_np,
         self.if_arc_np) = data  
        
if __name__ == "__main__":
    print('Test write problem data on Lpr_IF_data_set/Lpr-b-05.txt')
    directory = 'lpr_IF_data_set'
    print(directory)
    inputDirectory = 'Problem_data_raw/' + directory + '/'
    outPutFolder = 'Problem_data_transformed/' + directory + '/'
    file = 'Lpr-b-05.txt'
    wrt = WriteAllData(outPutFolder, inputDirectory, file)
    wrt.execute()
    print('Done with test')
        