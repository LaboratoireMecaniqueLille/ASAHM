# coding: utf-8

import os
import trimesh


def load_model(path_3mf):
    """
    Load and process 3MF file.

    Args:
        path_3mf (str): Path to the 3MF file.

    Returns:
        trimesh.Trimesh: Transformed 3MF model.
        numpy.ndarray: 3x4 transformation matrix extracted from the 3MF file.
        numpy.ndarray: 3x3 2D transformation matrix calculated based on t.
        str: Base name of the 3MF file without its extension.
        list of float: Shifts in the x and y direction calculated by comparing 
        the centroid of the STL model to its hull center.

    Notes:
        Given path to a 3MF, this function loads the models, 
        calculates transformations, and extracts information like centroids and 
        bounding box. USE_PYGEOS environment variable is set to '0' at the
        beginning  to avoid potential conflicts or issues related to pygeos
        library.
    """

    os.environ['USE_PYGEOS'] = '0'
    pack = trimesh.load(path_3mf)
    stl = None
    for key in pack.graph.nodes:
        if any(substring in key.lower() for substring in ('stl', '3mf')):
            stl = key

    if stl is None:
        raise RuntimeError("Unable to find stl")
    data = {'matrix_transform': pack.graph[stl][0],
            'nom_geom': pack.graph[stl][1]}
    original_model = pack.geometry[data['nom_geom']]
    t = data['matrix_transform']
    model = original_model.apply_transform(t)
    filename_with_extension = os.path.basename(path_3mf)
    filename, _ = os.path.splitext(filename_with_extension)

    return model, t, filename
