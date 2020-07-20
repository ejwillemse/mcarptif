import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

from converter.input_converter import Converter
from converter.import_Belenguer_format import convert_file
import converter.py_data_write as py_data_write
import converter.shortest_paths as shortest_paths
from converter import load_instance
from converter import Network
from converter import ShortestPath
import tables as tb
import logging
logging.basicConfig(level=logging.DEBUG)

file = 'temp/landed_recycling_GeylangKalangToaPayoh' 
instance_info = convert_file('{}.txt'.format(file))
instance_df = instance_info[['arc_u', 'arc_v', 'arc_cost']]
network = Network(instance_df)
network.create_pytable('{}_fixed_test_play.h5'.format(file), overwrite=False)
sp_calc = ShortestPath()
sp_calc.load_from_pytable('{}_fixed_test_play.h5'.format(file))
sp_calc.calc_shortest_path_pytable()

with tb.open_file('temp/{}.h5'.format(file), 'r') as h5file:
    sp_info = h5file.root.shortest_path_info
    cost_matrix = sp_info.cost_matrix
    predecessor_matrix = sp_info.predecessor_matrix
    cost_matrix[:, :]
    predecessor_matrix[:, :]