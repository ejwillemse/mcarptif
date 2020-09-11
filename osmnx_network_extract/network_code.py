"""Functions to assign key points to a undirected OSM street network.
"""
import osmnx as ox
import pandas as pd
import geopandas as gpd
from shapely import wkt
import numpy as np
from pyproj import Proj
import matplotlib.pyplot as plt
import logging
from osmnx_network_extract.create_instance import create_arc_id


def return_crs(country='SG'):
    """Return crs for a specified country.

    Arg:
        country (str): country acronym.

    Return:
        country_crs (dict: {'latlon': <str>, 'xy': <str>}): lat-lon and
        projected coordinate reference system.
    """
    country_pairs = {'SG': {'latlon': 'EPSG:4326', 'xy': 'EPSG:3414'}}
    return country_pairs[country]


def geom_to_points(df):
    """Convert geometry layer into points layer for pydeck plotting.

    Arg:
        df (geo.dataframe): Geo-dataframe whose active geometry layer will be
            converted.

    Return:
        points column: [(lon, lat)] for each lon-lat coordinate pair.
    """
    df['points'] = df.apply(lambda x: [y for y in x.geometry.coords], axis=1)
    return df


def calc_dist(df, x0='x', y0='y', x1='x1', y1='y1'):
    dist = ( ( ( df[x0].subtract(df[x1]) ).pow(2) ).add( ( df[y0].subtract(df[y1]) ).pow(2) ) ).pow(0.5)
    return dist


def create_gdf(df, crs='EPSG:4326', dropna_geom=False):
    """Convert data frame into geopandas data frame.

    Arg:
        df (data.frame): to convert, must have `geometry` column.
        crs (str): coordinate reference system.
        dropna_geom (bool): drop geometries that are nan
    """
    df = df.copy()
    if dropna_geom is True:
        df = df.dropna(subset=['geometry'])
    if df['geometry'].dtype == 'O':
        df['geometry'] = df['geometry'].astype(str).apply(wkt.loads)
    df = gpd.GeoDataFrame(df, geometry=df['geometry'], crs=crs)
    return df


def create_latlon_gdf(df, crs='EPSG:4326', x_col='lon', y_col='lat', dropna_geom=True):
    """Convert data frame into geopandas data frame.

    Arg:
        df (data.frame): to convert, must have `geometry` column.
        crs (str): coordinate reference system.
    """
    if dropna_geom is True:
        df = df.dropna(subset=[x_col, y_col])
    df = gpd.GeoDataFrame(df,
                          geometry=gpd.points_from_xy(df[x_col], df[y_col]),
                          crs=crs)
    return df


def add_xy_proj(df, crs, lon_key='lon', lat_key='lat'):
    pp = Proj(crs)
    xx, yy = pp(df[lon_key].values, df[lat_key].values)
    df['x'] = xx
    df['y'] = yy
    return df


def add_lonlat_proj(df, crs, lon_key='lon', lat_key='lat'):
    pp = Proj(crs)
    xx, yy = pp(df[lon_key].values, df[lat_key].values)
    df['x'] = xx
    df['y'] = yy
    return df


def extract_node_gdf(df, crs):
    """Extract a node data frame from arc data"""
    df = df[['u', 'v', 'geometry']].copy()
    df['points'] = df.apply(lambda x: [y for y in x['geometry'].coords],
                            axis=1)
    df['u_lon'] = df['points'].apply(lambda x: x[0][0])
    df['u_lat'] = df['points'].apply(lambda x: x[0][1])
    df['v_lon'] = df['points'].apply(lambda x: x[-1][0])
    df['v_lat'] = df['points'].apply(lambda x: x[-1][1])
    df_u = df[['u', 'u_lon', 'u_lat']]
    df_u.columns = ['u', 'x', 'y']
    df_v = df[['v', 'v_lon', 'v_lat']]
    df_v.columns = ['u', 'x', 'y']
    df = pd.concat([df_u, df_v])
    df = df.drop_duplicates()
    df = df.set_index(['u'], drop=False)
    df.index.name = None

    df = gpd.GeoDataFrame(df,
                          geometry=gpd.points_from_xy(df['x'], df['y']),
                          crs=crs)

    return df


def customer_network_plot(customers,
                          network,
                          figsize=None,
                          markersize=5,
                          linewidth=1):
    if figsize is None:
        figsize = (40, 40)

    fig, ax = plt.subplots(figsize=figsize)
    _ = customers.plot(ax=ax, markersize=markersize, facecolor='red')
    _ = network.plot(ax=ax, linewidth=linewidth)
    return fig


def required_arc_plot(full_network,
                      required_arcs,
                      figsize=None,
                      linewidth_full=1,
                      linewidth_req=2.5):
    if figsize is None:
        figsize = (40, 40)

    fig, ax = plt.subplots(figsize=figsize)
    _ = full_network.plot(ax=ax, linewidth=linewidth_full)
    _ = required_arcs.plot(ax=ax, linewidth=linewidth_req, color='red')
    return fig


class NetworkCode:
    """Assign points to OSM network, can either be to the nearest point or
    nearest arcs. Highly recommended to use a directed graph when snapping
    multiple points to single arcs or edges, otherwise neighbouring
    points will be snapped to opposing edges.
    """

    def __init__(self,
                 df_network=None,
                 path=None,
                 country='SG',
                 xy_converted=True):
        """
        Arg:
            df_network (pandas.df): osmnx extracted network graph, stored as df.
            path (str): path to osmnx extracted network graph.
            country (str): country or region in which network geocoding is
                taking place.
            xy_converted (bool): convert all frames to xy (speeds up everything)
        """
        if df_network is None:
           self.df_network = pd.read_csv(path)
        else:
            self.df_network = df_network.copy()
        self.crs = return_crs(country)
        self.df_network = create_gdf(self.df_network,
                                     self.crs['latlon'],
                                     dropna_geom=True)

        self.crs_ref = self.crs['latlon']
        self.xy_converted = xy_converted
        if self.xy_converted is True:
            self.crs_ref = self.crs['xy']
            self.project(xy=True)

        self.df = None
        self.df_collection_points = None
        self.df_nodes = self.create_nodes_gdf(self.df_network)
        self.df_network_filter = self.df_network.copy()
        self.df_nodes_filter = self.df_nodes.copy()

        self.df_solution = None

    def plot_customers_network(self):
        return customer_network_plot(self.df, self.df_network)

    def add_customers(self, df_points, gdf_convert=True):
        """Add customers. Must have lon-lat points.
        Arg:
            df_points (pandas.df): pandas data frame of customer points,
                must have lat-lon coordinate pair.
            gdf_convert (pandas.df): convert customer data frame into
                same crs as main network.
        """
        logging.info('Adding {} customers.'.format(df_points.shape[0]))
        self.df = df_points.copy()
        self.df = add_xy_proj(self.df, crs=self.crs['xy'])
        self.df = create_latlon_gdf(self.df,
                                    crs=self.crs['latlon'],
                                    x_col='lon',
                                    y_col='lat')
        if gdf_convert:
            self.df = self.df.to_crs(self.crs_ref)

    def project(self, xy=True):
        """Convert network input to xy coordinates or lat-lon. Speeds up
        snapping calculations.

        Arg:
            xy (bool): true to convert to xy, false to convert to lon-lat
        """
        logging.info('Convert network to x-y')
        if xy is True:
            self.crs_ref = self.crs['xy']
        else:
            self.crs_ref = self.crs['latlon']
        self.df_network = self.df_network.to_crs(self.crs_ref)
        self.xy_converted = xy

    def create_nodes_gdf(self, df_network):
        """Create nodes geo-data-frame, based on arcs.

        Arg:
            df_network: to convert
        Return:
            df_nodes: nodes of the network
        """
        logging.info('Extracting nodes from network')
        df_nodes = extract_node_gdf(df_network,
                                    self.crs_ref)
        return df_nodes

    def convert_direct(self,
                       arc_id_ordered_key='arc_id_ordered',
                       set_filter=True):
        """Converted the graph into an undirected graph, by removing one of
        the arcs associated with two-way streets.
        Arg:
            arc_id_ordered_key (str): ordered arc ID pair, to remove
                duplicates with.
            replace (bool): if the original network should be stored.
            set_filter (bool): set filter to directed network as well.
        """
        logging.info('Removing opposing network arcs (only need one).')
        n_prev = self.df_network.shape[0]
        self.df_network = self.df_network.drop_duplicates([arc_id_ordered_key])
        if set_filter:
            self.df_network_filter = self.df_network.copy()
        logging.info('Arcs removed: {}.'.format(n_prev - self.df_network.shape[0]))

    def filter_network(self,
                       filter_values,
                       filter_column='highway'):
        """Filter internal network based on filter scolumns.

        Filtering is usual done per road type, contained in `highway` with
        typical values of:
            'residential' for landed properties
            `service`: for internal estate and HDB property networks.

        Arg:
            filter_values (list <str>): filter values to keep.
            filter_column (str): filter column, which can be `highway` for
                road type.
            contained (array <bool>): existing contain values to continue with.
                Useful if filtering over multiple columns.

        Returns:
            contained (array <bool>): filtered
        """
        if type(filter_values) != list:
            logging.error('Terms should be in a list')
            logging.error(filter_values)
            raise TypeError()

        logging.info('Filtering network on: {}'.format(filter_column))
        network_col = self.df_network[filter_column]

        contained = np.full(self.df_network.shape[0], False)
        for string in filter_values:
            contained = contained.copy() | network_col.str.contains(
                string, regex=False)

        self.df_network_filter = self.df_network.loc[contained]
        uv = np.append(self.df_network_filter['u'], self.df_network_filter[
            'v'])
        uv = np.unique(uv)
        self.df_nodes_filter = self.df_nodes.loc[self.df_nodes['u'].isin(uv)]
        n_remove = self.df_network.shape[0] - self.df_network_filter.shape[0]
        logging.info('Arcs removed: {}'.format(n_remove))

    def assign_closest_edge_vertex(self, df):
        """After assigning nodes to arcs, find the closest vertex of the arc
        to the point"""
        logging.info('Find closest assigned end point')
        df = df.copy()
        vertices = self.df_nodes_filter.copy()
        vertices_u_min = vertices[['u', 'x', 'y']].copy()
        vertices_u_min.columns = ['arc_u', 'x_u', 'y_u']
        vertices_v_max = vertices[['u', 'x', 'y']].copy()
        vertices_v_max.columns = ['arc_v', 'x_v', 'y_v']

        df = df.merge(vertices_u_min)
        df = df.merge(vertices_v_max)
        df['dist_u'] = calc_dist(df, 'x', 'y', 'x_u', 'y_u')
        df['dist_v'] = calc_dist(df, 'x', 'y', 'x_v', 'y_v')

        u_closest = df['dist_u'] < df['dist_v']

        df.loc[u_closest, 'closest_u'] = df.loc[u_closest, 'arc_u']
        df.loc[~u_closest, 'closest_u'] = df.loc[~u_closest, 'arc_v']

        df.loc[u_closest, 'dist_u'] = df.loc[u_closest, 'dist_u']
        df.loc[~u_closest, 'dist_u'] = df.loc[~u_closest, 'dist_v']

        df = df.drop(columns=['x_u', 'y_u', 'x_v', 'y_v', 'dist_v'])

        vertices_keep = vertices[['u', 'geometry']].copy().rename(columns={
            'u': 'closest_u'})
        vertices_keep = vertices_keep.to_crs(self.crs['latlon'])
        vertices_keep['lon_u'] = vertices_keep.geometry.x
        vertices_keep['lat_u'] = vertices_keep.geometry.y
        vertices_keep = vertices_keep.to_crs(self.crs_ref)
        vertices_keep = vertices_keep.rename(columns={'geometry': 'geometry_u'})
        df = df.merge(vertices_keep, left_on='closest_u', right_on='closest_u')
        return df

    def snap_customers(self, df):
        """Find nearest point on assigned arc and snap to."""
        logging.info('Find closest point on assigned arc')
        def arc_snapping(df_row):
            arc = edges_df.loc[
                edges_df['arc_id'] == df_row.name].geometry.unary_union
            points = df_row.geometry
            result = points.apply(
                lambda row: arc.interpolate(arc.project(row)))
            return pd.DataFrame(result)

        df = df.copy()
        edges_df = self.df_network_filter

        df['geometry_arc_snap_point'] = df.groupby(['arc_id']).apply(arc_snapping)
        df = df.set_geometry('geometry_arc_snap_point')

        df['x_arc_snap'] = df.geometry.x
        df['y_arc_snap'] = df.geometry.y

        df = df.to_crs(self.crs['latlon'])

        df['lon_arc_snap'] = df.geometry.x
        df['lat_arc_snap'] = df.geometry.y

        df = df.to_crs(self.crs['xy'])

        df['arc_dist'] = calc_dist(df, 'x', 'y', 'x_arc_snap', 'y_arc_snap')

        return df

    @staticmethod
    def find_best_collection(df):
        """Find the best collection point between the end of a vertex or
        directly on it"""
        logging.info('Find best collection point')
        arc_closest = df['arc_dist'] < df['dist_u']
        df['arc_collect'] = arc_closest
        df.loc[arc_closest, 'lon_collect'] = df.loc[arc_closest][
            'lon_arc_snap']
        df.loc[arc_closest, 'lat_collect'] = df.loc[arc_closest][
            'lat_arc_snap']
        df.loc[~arc_closest, 'lon_collect'] = df.loc[~arc_closest]['lon_u']
        df.loc[~arc_closest, 'lat_collect'] = df.loc[~arc_closest]['lat_u']

        df.loc[arc_closest, 'dist_collect'] = df.loc[
            arc_closest, 'arc_dist']
        df.loc[~arc_closest, 'dist_collect'] = df.loc[
            ~arc_closest, 'dist_u']
        return df

    def find_nearest_collection_point(self,
                                      dist=None,
                                      snap_arcs=True,
                                      key_merge=False):
        """Find the nearest collection points, nodes or edges.

        Arg:
            dist (float): tolerance, in meters, since we convert to xy,
                of snapping.
            snap_arcs (bool): snap point to nearest arc, can be disabled to
                speed up calculations.
        """
        df_fit = self.df.copy()
        network = self.df_network_filter.copy()
        if self.xy_converted:
            method = 'kdtree'
            x_col = 'x'
            y_col = 'y'
            if dist is None:
                dist = 20
        else:
            logging.warning('Network should be converted to xy coordinates')
            method = 'balltree'
            x_col = 'lon'
            y_col = 'lat'
            if dist is None:
                dist = 0.0001
        logging.info('Find nearest arc')
        logging.info('Number of arcs {} number of points {}'.format(
            network.shape[0], df_fit.shape[0]))
        G = ox.graph_from_gdfs(self.df_nodes_filter, self.df_network_filter)
        edge_assign = ox.get_nearest_edges(G,
                                           df_fit[x_col],
                                           df_fit[y_col],
                                           method=method,
                                           dist=dist)

        u = edge_assign[:, 0]
        v = edge_assign[:, 1]
        k = edge_assign[:, 2]
        df_fit['arc_u'] = u
        df_fit['arc_v'] = v
        if key_merge:
            df_fit['arc_key'] = k
            df_fit = create_arc_id(df_fit,
                                   'arc_id',
                                   'arc_u',
                                   'arc_v',
                                   'arc_key')
        df_fit = self.assign_closest_edge_vertex(df_fit)
        network = network.rename(columns={'geometry': 'geometry_arc'})
        df_fit = df_fit.merge(network[['arc_id', 'geometry_arc']], how='left')
        if snap_arcs:
            df_fit = self.snap_customers(df_fit)
            df_fit = self.find_best_collection(df_fit)
        self.df_collection_points = df_fit.copy()

    def merge_network(self):
        """Add arc attributes"""
        logging.info('Adding arc attributes.')
        self.df_collection_points = self.df_collection_points.merge(self.df_network_filter[['arc_id', 'arc_index', 'highway', 'oneway']])

    def convert_geometries_latlon(self, columns=None):
        """Convert all geometry columns to crs. Needed for kepler.gl that
        crashes when geometries are not on lat-lon.

        Args:
            columns (list <str>): geometry columns to convert. If none,
            any column with `geometry` in it will be converted.
        """
        logging.info('Convert geometries to lat-lon')
        if columns is None:
            columns = [x for x in self.df_collection_points.columns if x.find('geometry')
                       != -1]

        for col in columns:
            self.df_collection_points = self.df_collection_points.set_geometry(col, crs=self.crs['xy'])
            self.df_collection_points = self.df_collection_points.to_crs(crs=self.crs['latlon'])

    def network_to_points(self):
        logging.info('Convert geometry to geom-point objects.')
        self.df_network = geom_to_points(self.df_network)


def prepare_node_routing(node_list, edge_list):
    node_list['u'] = node_list.index
    node_list = node_list.reset_index(drop=True)
    node_list['index'] = node_list.index
    edge_list['u-v'] = edge_list['u'].astype(int).astype(str) + '-' + \
                       edge_list['v'].astype(int).astype(str)
    edge_list['arc_index'] = edge_list.index
    edge_list['arc_id'] = edge_list['u'].astype(str) + '-' + edge_list['v'].astype(str) + '-' + edge_list['key'].astype(str)
    return node_list, edge_list
