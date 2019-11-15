'''
Created on 18 Sep 2017

@author: eliaswillemse
'''

inputfile = 'Raw_input/Lpr/MCGRP-Lpr-a-05.dat' 

with open(inputfile, 'r') as testFile:
    for l in testFile.readlines(): print(l, 'test')