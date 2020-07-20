# -*- coding: utf-8 -*-
"""
Import MCARPTIF raw files in Belenguer format into pandas dataframe
"""

from converter.input_converter import Converter
import pandas as pd
import numpy as np


def convert_file(file_path):
    """Convert the file at `file_path`

    Arg:
        file_path (str): path to raw text file to be converted.

    Return:
        instance_df (pandas.DataFrame): frame of the raw input file with
            `arc_index` `arc_u`, `arc_v`, `arc_cost`, `arc_inverse_index`,
            `arc_successor_index_list` and `arc_oneway` columns added.
    """

    convert = Converter(file_path)
    instance_info = convert.extract_inputs()
    success_array = np.array([np.array(x) for x in instance_info['sucArcL']])
    instance_df = pd.DataFrame(
        {'arc_u': instance_info['beginL'], 'arc_v': instance_info['endL'],
         'arc_cost': instance_info['travelCostL']})
    instance_df['arc_index'] = instance_df.index.values
    instance_df['arc_inverse_index'] = instance_info['invArcL']
    instance_df['arc_inverse_index'] = instance_df['arc_inverse_index'].fillna(
        -1).astype(int)
    instance_df.loc[
        instance_df['arc_inverse_index'] == -1, 'arc_oneway'] = True
    instance_df.loc[
        instance_df['arc_inverse_index'] != -1, 'arc_oneway'] = False
    instance_df['arc_successor_index_list'] = np.nan
    instance_df['arc_successor_index_list'] = instance_df[
        'arc_successor_index_list'].astype(object)
    instance_df.at[:, 'arc_successor_index_list'] = success_array
    return instance_df
