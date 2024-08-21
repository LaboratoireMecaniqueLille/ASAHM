import matplotlib.pyplot as plt
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import shapely
from shapely.geometry import MultiPolygon
from shapely.geometry.multipolygon import MultiPolygon as ShapelyMultiPolygon


def find_surfacing_zones(model):
    """
    Scans a model and returns a set of Z heights where pure horizontal surfaces exist, 
    and those surfaces need CNC surfacing.

    Args:
        model (Mesh object): The STL model object to analyze.

    Returns:
        list[float]: A sorted list of Z coordinates where surfacing has to be done. 
                    If no surfacing zones are found, the list contains a single element [0].

    Example:
        >>> python3 -m hybridator /home/user/Desktop/samples/example_1.3mf
        /home/user/Desktop/samples/example_1.stl /home/user/Desktop/samples/example_1.gcode
        > Path to INI file not provided, using default values
        > Destination folder not provided, creating file at :
        /home/user/Desktop/samples

    """

    facets_normals = model.facets_normal
    z_surfaces = set()
    for i, normal in enumerate(facets_normals):
        if round(normal[2], 9) == 1:
            face = model.facets[i][0]
            z_surfaces.add(round(model.triangles_center[face][2], 2))

    z_surfaces = sorted(z_surfaces) if z_surfaces else [0]
    return z_surfaces


def generate_surfacing_polygon(model_center_base, model, z_surfaces, t_2d, surfacing_clearance, show_surfacing_polygons):
    """
    Generate polygons for CNC surfacing operations based on detected heights of horizontal planes.
    This function is necessary because the surfacing operation must not machine nearby surfaces or elements
    of our part. The way that the polygon will be generated will vary if the surface is at the top of the part (there will be
    no nearby elements) or in the middle of the part. The function also "cleans" the surfaces by ignoring the faces that are too 
    small to be machined.

    Args:
        model_center_base (list): The center of the model.
        model (Mesh object): The STL model object to analyze.
        z_surfaces (list): List of heights where surfacing zones exist.
        t_2d (Transformation object): 2D transformation to apply to the generated polygons, inherited from the 3mf.
        surfacing_clearance (float): Clearance value for surfacing, the distance going out of the bulk of material to clean chips.
        show_surfacing_polygons (bool): If True, display the generated polygons for visualization.

    Returns:
        list[shapely.geometry.MultiPolygon]: A list of cleaned and buffered shapely MultiPolygons representing
                                            the faces to be surfaced at specified heights.
    """
    cleaned_z_surfaces = []

    for i, height in enumerate(z_surfaces):
        #Case where the Z coordinate coresponds to the top of the part
        if height == round(model.bounds[1][2], 2):

            section_surfaces = model.section_multiplane(plane_origin=model_center_base, plane_normal=[0, 0, 1], heights=[(height - 0.0075)])
            temporary_poly = MultiPolygon(list(section_surfaces[0].polygons_full))
            #If the surface is a MultiPolygon, there might be some elements too small to be machined and we have to eliminate them
            if isinstance(temporary_poly, ShapelyMultiPolygon):
                cleaned_polys = [poly for poly in temporary_poly.geoms if poly.area > 0.5]
                final_poly = MultiPolygon(cleaned_polys)
            else:
                final_poly = temporary_poly
            final_poly = final_poly.buffer(surfacing_clearance)
            cleaned_z_surfaces.append(final_poly)
            #plt.style.use('seaborn-whitegrid')
            if show_surfacing_polygons:
                gpd.GeoSeries(final_poly).plot()
        # All other cases
        else:
            section_surfaces = model.section_multiplane(plane_origin=model_center_base, plane_normal=[0, 0, 1],
                                            heights=[(height - 0.0075), height, (height + 0.0075)])
                
            lower_offset_polygon = MultiPolygon(list(section_surfaces[0].polygons_full))
            upper_offset_polygon = MultiPolygon(list(section_surfaces[2].polygons_full))
            dirty_poly = lower_offset_polygon.difference(upper_offset_polygon)
            if isinstance(dirty_poly, ShapelyMultiPolygon):
                cleaned_polys = [poly for poly in dirty_poly.geoms if poly.area > 0.5]
                temporary_poly = MultiPolygon(cleaned_polys)
            else:
                temporary_poly = dirty_poly
            buffered_poly = temporary_poly.buffer(surfacing_clearance)
            final_poly = buffered_poly.difference(upper_offset_polygon)
            cleaned_z_surfaces.append(final_poly)
            #plt.style.use('seaborn-whitegrid')
            if show_surfacing_polygons:
                gpd.GeoSeries(final_poly).plot()

    return cleaned_z_surfaces


def generate_raw_surfacing_toolpath(cleaned_z_surfaces, surfacing_tool_radius, surfacing_stepover, show_surfacing_toolpaths):
    """
    Generates surfacing toolpaths doing consecutive offsets of the polygons corresponding to surfaces that have to be surfaced.

    Args:
        cleaned_z_surfaces (list):  List of clean polygons representing surfaces to be machined.
        surfacing_tool_radius (float): Radius of the endmill.
        surfacing_stepover (float): The surfacing step (offset) to be applied when generating paths.
        show_surfacing_toolpaths (bool, optional): If True, displays intermediate toolpath steps. Defaults to False.

    Returns:
        list: A list of tool paths in Shapely multilineString format (MultiLineString).

    Note:
        This function does not connect the toolpaths generated for the same polygon. The tool will have to make "Z hops" beetwen 
        every offset.
        
    Example:
        cleaned_surfaces = [polygon1, polygon2, ...]
        radius = 5.0
        stepover = 2.0
        toolpaths = generate_raw_surfacing_toolpath(cleaned_surfaces, radius, stepover, show=True)
    """
    temp_surfacable_heights=[]
    stepover = (surfacing_tool_radius * 2) * surfacing_stepover
    raw_surfacing_toolpath = []
    
    for i, poly in enumerate(cleaned_z_surfaces):
        area = poly.area
        actual_poly = poly
        temp_toolpaths_list = []
        
        while area > 3:
            actual_poly = actual_poly.buffer(-stepover)
            area = actual_poly.area
            if not actual_poly.is_empty:
                temp_toolpaths_list.append(actual_poly.boundary)
                
        #Generates toolpaths merging all offsets together in one multilinestring
        multilinestring = shapely.MultiLineString()
        for j, element in enumerate(temp_toolpaths_list):
            multilinestring = multilinestring.union(element)
        
        raw_surfacing_toolpath.append(multilinestring)
        
        if temp_toolpaths_list and show_surfacing_toolpaths:
            ax = gpd.GeoSeries(temp_toolpaths_list[::]).plot()
            plt.show()
        
        if not multilinestring.is_empty:
            temp_surfacable_heights.append(i)
    surfacable_heights = list(set(temp_surfacable_heights))
    surfacable_heights.sort()
    
    return raw_surfacing_toolpath , surfacable_heights


def generate_surfacing_data(surfacable_heights, z_surfaces, cleaned_z_surfaces, raw_surfacing_toolpath):
    """
    Generates a list of dictionaries that contain all the data needed to then generate G-codes for surfacing.

    Args:
        z_surfaces (list): List of heights where horizontal faces have been detected.
        cleaned_z_surfaces (list): List of polygons (after cleaning) representing surfaces to be machined.
        raw_surfacing_toolpath (list): List of MultiLineString representing surfacing tool paths.

    Returns:
        list: A list of dictionaries containing the data required to generate G-codes for surfacing.

    Example:
        z_heights = [0.1, 0.2, 0.3]
        cleaned_surfaces = [polygon1, polygon2, polygon3]
        toolpaths = [multilinestring1, multilinestring2, multilinestring3]
        surfacing_data_list = generate_surfacing_data(z_heights, cleaned_surfaces, toolpaths)
    """
    surfacing_data = []

    for i in surfacable_heights:
        dicsurf={}
        dicsurf["Surface_z_height"] = z_surfaces[i]
        dicsurf["Surface_poly"] = cleaned_z_surfaces[i]
        dicsurf["Surfacing_passes"] = raw_surfacing_toolpath[i]
        surfacing_data.append(dicsurf)
    return surfacing_data


def sort_toolpaths(surfacing_data, surfacing_direction):
    """
    Sort the toolpaths in the given surfacing data based on their length (polygon area).

    This function iterates over the surfacing data and for each element that contains a MultiLineString under the
    key 'Surfacing_passes', it sorts the geometries based on the area of the corresponding polygon they form. 
    It then replaces the original MultiLineString with a sorted version in the surfacing data.
    
    Args:
        surfacing_data (list[dict]): A list of dictionaries where each dictionary contains surfacing data.
            The key 'Surfacing_passes' in each dictionary should have a value that is a 
            shapely.geometry.MultiLineString instance or any other geometry.

    Returns:
        list[dict]: The surfacing data with sorted toolpaths.

    Note:
        This function assumes that the 'Surfacing_passes' key in the surfacing data will always contain a valid 
        geometry or MultiLineString, otherwise it might throw an error. Ensure that the input data adheres to this format.
    """
    for element in surfacing_data:
        if isinstance(element['Surfacing_passes'], shapely.geometry.MultiLineString):
            # Determining the sorting order based on surfacing direction choosed
            reverse_sort = True if surfacing_direction != 'climbing' else False

            # Sorting the toolpaths by their length (corresponding polygon area)
            sorted_geoms = sorted(element['Surfacing_passes'].geoms, key=lambda geom: shapely.geometry.Polygon(geom).area, reverse=reverse_sort)

            # Replace the MultiLineString with a sorted multilinestring
            element['Surfacing_passes'] = shapely.geometry.MultiLineString(sorted_geoms)
    return surfacing_data