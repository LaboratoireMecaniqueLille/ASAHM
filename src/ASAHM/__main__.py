# coding: utf-8

from configparser import ConfigParser
import argparse
import os
import time

from .original_gcode_processing import extract_layer_data
from .model_processing import load_model
from .contouring_operations import (get_contour_sections,
                                    get_cnc_contouring_coords)
from .gcodes_contruction_operations import (construct_cnc_contouring_gcode,
                                            construct_cnc_surfacing_gcode,
                                            merge_contour_and_surfacing_codes,
                                            hbd_fdm_cnc_merge_codes)
from .surfacing_operations import (find_surfacing_zones,
                                   generate_surfacing_polygon,
                                   generate_raw_surfacing_toolpath,
                                   generate_surfacing_data,
                                   sort_toolpaths)

start_time = time.time()

parser = argparse.ArgumentParser(description="Description.")
parser.add_argument('path_3mf', type=str, help="Path to 3MF file.")
parser.add_argument('path_gcode', type=str, help="Path to GCODE file.")
parser.add_argument('--path_ini_file', type=str, 
                    help="Path to parameters INI file.", default=None)
parser.add_argument('--final_folder', type=str, 
                    help="Path to write your hybridized Gcode.", 
                    default=None)

args = parser.parse_args()
path_3mf = args.path_3mf
path_gcode = args.path_gcode
path_ini_file = args.path_ini_file
if path_ini_file is None:
    path_ini_file = "nonexistent"
    print("> Path to INI file not provided, using default values")
write_folder = args.final_folder
if write_folder is None:
    write_folder = os.path.dirname(path_gcode)
    print(f"> Destination folder not provided, creating file at "
          f":\n {write_folder}")

# Extract datas from the config file
# If not provided, will use the fallbacks
config = ConfigParser()
config.read(path_ini_file)

# subtractive parameters
subtractive_start_layer = config.getint(
    'subtractive', 'subtractive_start_layer', fallback=3)
z_contouring_adjustment = config.getfloat(
  'subtractive', 'z_contouring_adjustment', fallback=0.1)
contouring_direction = config.get(
    'subtractive', 'contouring_direction', fallback='conventional')
contouring_speed = config.get(
    'subtractive', 'contouring_speed', fallback='650')
bridge_speed = config.get('subtractive', 'bridge_speed', fallback='3500')
jump_value = config.getfloat('subtractive', 'jump_value', fallback=1)
surfacing_direction = config.get(
    'subtractive', 'surfacing_direction', fallback='conventional')
surfacing_speed = config.get('subtractive', 'surfacing_speed', fallback='850')
surfacing_jump_value = config.getfloat(
    'subtractive', 'surfacing_jump_value', fallback=0.5)
surfacing_swoop_speed = config.get(
    'subtractive', 'surfacing_swoop_speed', fallback='50')
surfacing_clearance = config.getfloat(
    'subtractive', 'surfacing_clearance', fallback=1)
surfacing_shadow_pass = config.getint(
    'subtractive', 'surfacing_shadow_pass', fallback=2)
surfacing_roughing_pass_value = config.getfloat(
  'subtractive', 'surfacing_roughing_pass_value', fallback=0.05)
surfacing_roughing_pass = config.getboolean(
    'subtractive', 'surfacing_roughing_pass', fallback=True)
surfacing_stepover = config.getfloat(
    'subtractive', 'surfacing_stepover', fallback=0.75)
# global parameters
stand_by_temp = config.get('global', 'stand_by_temp', fallback='150')
contouring_shadow_pass = config.getboolean(
    'subtractive', 'contouring_shadow_pass', fallback=False)
surfacing_tool_number = config.get(
    'global', 'surfacing_tool_number', fallback='T1')
surfacing_tool_radius = config.getfloat(
    'global', 'surfacing_tool_radius', fallback=0.73)
layer_height = config.getfloat('global', 'layer_height', fallback=0.2)
contour_tool_number = config.get(
    'global', 'contour_tool_number', fallback='T1')
print_tool_number = config.get('global', 'print_tool_number', fallback='T0')
contour_tool_radius = config.getfloat(
    'global', 'contour_tool_radius', fallback=0.73)
# code parameters
write_isolate_contouring_code = config.getboolean(
    'codes', 'write_isolate_contouring_code', fallback=False)
write_isolate_surfacing_code = config.getboolean(
    'codes', 'write_isolate_surfacing_code', fallback=False)
write_cnt_surf_merged_code = config.getboolean(
    'codes', 'write_cnt_surf_merged_code', fallback=False)
show_surfacing_polygons = config.getboolean(
    'codes', 'show_surfacing_polygons', fallback=False)
show_surfacing_toolpaths = config.getboolean(
    'codes', 'show_surfacing_toolpaths', fallback=False)
non_mesh_travel_speed = config.getint(
    'codes', 'non_mesh_travel_speed', fallback=11000)

# Load the Gcode File
with open(path_gcode, 'r', encoding='UTF-8') as gcode:
    gcode = (gcode.read()).split("\n")

# Export datas in the original gcode (layer n°, Z height, starting & ending
# line of each layer)
# Generates a list with the Z coordinates where the model has been sliced in
# the gcode
gcode_datas, gcode_z_slices = extract_layer_data(gcode,
                                                 subtractive_start_layer,
                                                 layer_height)

# Put the model (STL) in the right position for the 3d printer
model, T, filename = load_model(path_3mf)

# Makes slices on the STL on which we applied our transform matrix on XY at
# correct heights
sections_2d, model_center_base = get_contour_sections(model,
                                                      gcode_z_slices)

# Generates a list containing every buffered slice
buffered_contours_list = get_cnc_contouring_coords(sections_2d,
                                                   contour_tool_radius,
                                                   contouring_direction)

# Takes the buffered contours and for each points of the curves generates a
# machining command
# Returns a gcode readable by rep rap 3D printer
dict_milling_coord = construct_cnc_contouring_gcode(
    gcode_datas,
    buffered_contours_list,
    contouring_speed,
    bridge_speed,
    print_tool_number,
    contour_tool_number,
    jump_value,
    layer_height,
    z_contouring_adjustment,
    write_isolate_contouring_code,
    contouring_shadow_pass,
    filename,
    write_folder)

# Scans the STL and returns a list where the Z of faces to be CNC surfaced are
# present
z_surfaces = find_surfacing_zones(model)

# Generates a list containing the different polygons (cleaned and offset) to
# be machined
cleaned_z_surfaces = generate_surfacing_polygon(model_center_base,
                                                model,
                                                z_surfaces,
                                                surfacing_clearance,
                                                show_surfacing_polygons)

# From previous polygons, we generate toolpaths and put them in a list
raw_surfacing_toolpath, surfaceable_heights = generate_raw_surfacing_toolpath(
    cleaned_z_surfaces,
    surfacing_tool_radius,
    surfacing_stepover,
    show_surfacing_toolpaths)

# Generates a list with surfacing operations infos (polygon, Z height,
# toolpaths)
surfacing_data = generate_surfacing_data(surfaceable_heights, z_surfaces,
                                         cleaned_z_surfaces,
                                         raw_surfacing_toolpath)

# Sort the surfacing toolpaths from large to little toolpath length to
# machining phases
surfacing_data = sort_toolpaths(surfacing_data, surfacing_direction)

# Generates a gcode with all the surfacing operations
dict_surfacing_coord = construct_cnc_surfacing_gcode(
    surfacing_data,
    surfacing_speed,
    bridge_speed,
    surfacing_tool_number,
    print_tool_number,
    surfacing_jump_value,
    layer_height,
    write_isolate_surfacing_code,
    surfacing_swoop_speed,
    surfacing_shadow_pass,
    surfacing_roughing_pass_value,
    surfacing_roughing_pass,
    filename,
    write_folder)

# Generate a merged gcode of contouring and surfacing ops
merged_cnt_surfacing_dict = merge_contour_and_surfacing_codes(
    dict_surfacing_coord,
    dict_milling_coord,
    write_cnt_surf_merged_code,
    filename,
    write_folder)

# Write HBD Gcode
merged_gcode = hbd_fdm_cnc_merge_codes(gcode, gcode_datas,
                                       merged_cnt_surfacing_dict, filename,
                                       write_folder)

end_time = time.time()
total_time = end_time - start_time
print(f"Elapsed time: {total_time} seconds.")
