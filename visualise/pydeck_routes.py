# -*- coding: utf-8 -*-
"""Transform a solution into GEOJSON file for kepler.gl visualisation.

Input is the full directed graph and required edges graph, generated from
`osmnx_network_extract.create_instance`, and the full solution data-frame
generated using `solver.solve`

Output is different path-based geo-data-frames, consisting of full routes,
and parts of the vehicle routes. These can be stored as geojson files.

History:
    Created on 14 June 2020
    @author: Elias J. Willemse
    @contact: ejwillemse@gmail.com
"""