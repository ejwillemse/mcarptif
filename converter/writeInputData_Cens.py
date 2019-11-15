'''
Created on 20 Jan 2015

@author: ejwillemse
'''
from __future__ import division

from math import floor
            
def statsFull(filename, newFileName):
    f = open(filename, 'r')
    l = f.readlines()
    f.close()
    f2 = open(newFileName, 'w')
    for li in l:
        if li.find('serv_cost') != -1:
            info = li.split(' ')
            arcInfo = info[0]
            dCost = max(1,int(info[6]))
            q = int(info[8])
            sCost = dCost + floor(q/10)*10
            print(arcInfo, sCost, dCost, q)
            li = '%s  serv_cost %i  trav_cost %i  demand %i\n'%(arcInfo, sCost, dCost, q)
        elif li.find('cost') != - 1:
            info = li.split(' ')
            arcInfo = info[0]
            dCost = max(1,int(info[3]))
            li = '%s  cost %i\n'%(arcInfo, dCost)
        f2.write(li)
    f2.close()
    print(filename, dCost, sCost, q)
    return(dCost, sCost, q)

filename1 = 'Raw_input/Cen-IF-Full/Cen-If-Full.dat'
filename2 = 'Raw_input/Cen-IF-Full-2/Cen-IF-Full-2.dat'

statsFull(filename1, filename2)

