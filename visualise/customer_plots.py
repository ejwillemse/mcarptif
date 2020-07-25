"""Pydeck visualisations of customers"""
import pydeck as pdk
import palettable
import seaborn as sns
import pandas as pd


MAX_RGB = 255


def perc_to_rgb(color_list):
    color_full = [[int(col_ind * 255) for col_ind in color_row] for color_row in color_list]
    return color_full


def color_df(df,
             group=None,
             palet = "Paired",
             col_rule='one',
             opacity=None):
    """
    Args:
        col_rule (str): 'one' for one uniform color or 'unique' for a different color for each row.
    """
    if group is not None:
        n_groups = df[group].nunique()
        col_pal = perc_to_rgb(sns.color_palette(palet, n_groups))
        color_frame = pd.DataFrame.from_dict({group : df[group].unique(), 'color': col_pal})
        df = pd.merge(df, color_frame, how='left', left_on=group, right_on=group)
    elif col_rule == 'one':
        col_pal = perc_to_rgb(sns.color_palette(palet, 1))
        df['color'] = col_pal  * len(df)
    elif col_rule == 'unique':
        n_groups = len(df)
        col_pal = perc_to_rgb(sns.color_palette(palet, n_groups))
        df['color'] = col_pal
    return df


def return_scatter_layer(df,
                         id,
                         lat_key,
                         lon_key,
                         color_key,
                         ):
    scatter_layer = pdk.Layer('ScatterplotLayer',
                                data=df,
                                id=id,
                                pickable=True,
                                opacity=0.8,
                                stroked=False,
                                filled=True,
                                radiusMinPixels=1.25,
                                radiusMaxPixels=10,
                                get_radius=5,
                                get_fill_color=color_key,
                                get_position='[{}, {}]'.format(lon_key,
                                                               lat_key))

    return scatter_layer


def return_arc_layer(df,
                         id,
                         lat1,
                         lon1,
                         lat2,
                         lon2,
                         col1,
                        col2):
    from_to_arcs_u = pdk.Layer('ArcLayer',
                               data=df,
                               id=id,
                               get_width=2.5,
                               get_source_position='[{}, {}]'.format(lon1,
                                                                     lat1),
                               get_target_position='[{}, {}]'.format(lon2,
                                                                     lat2),
                               get_source_color=col1,
                               get_target_color=col2,
                               pickable=False,
                               auto_highlight=True)
    return from_to_arcs_u