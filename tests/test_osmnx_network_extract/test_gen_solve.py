import os
import sys
sys.path.insert(0, os.path.abspath('../../../'))

import logging
logging.basicConfig(level=logging.INFO)

import pandas as pd
import geopandas as gpd
from shapely import wkt
import numpy as np
import pathlib
print(pathlib.Path().absolute())

from osmnx_network_extract.extract_mcarptif import NetworkExtract
from solver import solve_store_instance

network_file = '../../../hobbes_projects/wasted_large_instances/outputs/city_punggol_full_internal_50m_buffer.h5'
test_network = pd.read_csv('../../../hobbes_projects/wasted_large_instances/outputs/city_punggol_full_internal_50m_buffer_original_dataframe.csv')
test_network = test_network.drop(columns=['Unnamed: 0'])

test_size = 100

sample = np.random.randint(0, test_network.shape[0], size=test_size)
sample = np.unique(sample)
req_arcs = test_network.iloc[sample, :].copy()
req_arcs = req_arcs.sort_values(['arc_index'])
req_arcs = req_arcs.drop_duplicates(['arc_id_ordered'])
req_arcs = req_arcs.dropna(subset=['geometry'])
req_arcs['geometry'] = req_arcs['geometry'].apply(wkt.loads)
req_arcs = gpd.GeoDataFrame(req_arcs, geometry=req_arcs['geometry'], crs='EPSG:4326')

req_arcs.shape

_ = req_arcs.plot(figsize=(10, 10), linewidth=2.5)

network_info = NetworkExtract(test_network, network_file)

depot = req_arcs['arc_index'].iloc[0]
ifs = req_arcs['arc_index'].iloc[-4:]

network_info.load_required_arcs(req_arcs)
network_info.set_depot_arc(depot)
network_info.set_if_arcs(ifs)
network_info.loc_in_required_arcs()
network_info.extend_required_inverse_arcs()
network_info.check_main_list()

network_info.load_distance_matrix()
network_info.offload_calculations3D()

demand = 1 # unit
df_demand = req_arcs[['arc_index']].copy()
df_demand['demand'] = 1

network_info.set_service_demand(df_demand)

network_info.set_travel_speed(1)
network_info.set_offload_time(15 * 60)
network_info.update_cost_matrix()
network_info.update_offload_cost()

service_speed = 1# / 3.6
service_costs = req_arcs[['arc_index', 'length']].copy()
service_costs['service_cost'] = service_costs[['length']]
network_info.set_service_cost(service_costs)

network_info.round_key_inputs()

network_info.d.mean()
network_info.if_cost_np.mean()

network_info.check_shapes()


network_info.calc_min_duration_capacity()

network_info.set_vechile_capacity_constraint(10)
network_info.set_vehicle_duration_constraint(300000)

solution_df = solve_store_instance('', improve='LS',
                                   write_results=False,
                                   info=network_info,
                                   overwrite=True,
                                   test_solution=True,
                                   full_output=False,
                                   debug_test_solution=True)
