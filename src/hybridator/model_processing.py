import os
import trimesh
import numpy as np

#>>> def load_model(path_3mf, path_stl):
def load_model(path_3mf):
    """
    Load and process 3MF file.

    Args:
        path_3mf (str): Path to the 3MF file.

    Returns:
        trimesh.Trimesh: Transformed 3MF model.
        numpy.ndarray: 3x4 transformation matrix extracted from the 3MF file.
        numpy.ndarray: 3x3 2D transformation matrix calculated based on T.
        str: Base name of the 3MF file without its extension.
        list of float: Shifts in the x and y direction calculated by comparing 
        the centroid of the STL model to its hull center.

    Notes:
        Given path to a 3MF, this function loads the models, 
        calculates transformations, and extracts information like centroids and 
        bounding box. USE_PYGEOS environment variable is set to '0' at the beginning 
        to avoid potential conflicts or issues related to pygeos library.
    """
    os.environ['USE_PYGEOS'] = '0'
    pack = trimesh.load(path_3mf)
    for key in pack.graph.nodes:
        if any(substring in key.lower() for substring in ('stl', '3mf')):
            stl = key

    data = {'matrix_transform': pack.graph[stl][0], 'nom_geom': pack.graph[stl][1]}
    original_model = pack.geometry[data['nom_geom']]
    T = data['matrix_transform']
    model = original_model.apply_transform(T)
    x = T[0][3]
    y = T[1][3]
    t_2d = np.array([[1, 0, x], [0, 1, y], [0, 0, 1]])
    filename_with_extension = os.path.basename(path_3mf)
    filename, _ = os.path.splitext(filename_with_extension)

    # stl = trimesh.load(path_stl)
    # x_min = stl.bounds[0][0]
    # x_max = stl.bounds[1][0]
    # y_min = stl.bounds[0][1]
    # y_max = stl.bounds[1][1]
    # x_center = round((abs(x_max) - abs(x_min)) / 2, 2)
    # y_center = round((abs(y_max) - abs(y_min)) / 2, 2)
    # hull_center = np.array([[round(x_center, 2)], [round(y_center, 2)]])
    # stl_centroid = np.array([[round(stl.centroid[0], 2)], [round(stl.centroid[1], 2)]])
    # xy_shift = [
    #     round(stl_centroid[0][0] - hull_center[0][0], 2),
    #     round(stl_centroid[1][0] - hull_center[1][0], 2)
    # return model, T, t_2d, filename, xy_shift
    return model, T, t_2d, filename