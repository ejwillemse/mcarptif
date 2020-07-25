import pytest
import os

import pandas as pd
from osmnx_network_extract.network_code import return_crs
from osmnx_network_extract.network_code import NetworkCode



def test_return_crs():
    crs = return_crs('SG')
    assert crs == {'latlon': 'EPSG:4326', 'xy': 'EPSG:3414'}

def test_network_code_init():
    network_path = 'test/cit_punggol_internal_50m_buffer_contain.csv'
    network_test = NetworkCode(df_point=[], path=network_path)
