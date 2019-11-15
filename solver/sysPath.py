'''
Created on 09 Dec 2014

@author: ejwillemse
'''
import os

def returnPath():
    absPath = os.path.abspath(__file__)
    relName = os.path.basename(__file__)
    thisProject = absPath[:absPath.find(relName)]
    thisProject = thisProject[:thisProject.rfind('/')]
    thisProject = thisProject[thisProject.rfind('/'):]
    hobbes_path = absPath[:absPath.find(thisProject)]
    return(hobbes_path)

def addInputPaths(sys):
    hobbes_path = returnPath()
    p1 = hobbes_path + '/Support_Modules'
    p2 = hobbes_path + '/Input_TestData'
    p3 = hobbes_path + '/LS'
    p4 = hobbes_path + '/LS_Efficient'
    sys.path += [p1, p2, p3, p4]
    return(sys)