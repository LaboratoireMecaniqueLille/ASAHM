# ASAHM : Automated Subtractive Additive Hybrid Manufacturing, a Python module for native hybrid FFF ⁄ CNC manufacturing

Read our SoftwareX article for further informations

# Hybrid G-Code Generator

This module provides functionality for generating a hybridized G-code (containing CNC machining and 3d printing commands) usable on a RepRap multi tool machine equipped with CNC milling system and FFF 3d printing extruders. The module works given 3MF, STL, and GCODE files. The Gcode has to be generated with Cura Slicer, some conditions must be met when using programming printing on the slicer:
- Only one STL model can be treated on the workspace.
- A Gcode post-processing macro must be set up within the slicer so that each time a layer is changed, the     
string “LAYER CHANGE” appears. This is the “trigger” used by ASAHM to detect the beginning and end of a 
layer within the original Gcode.
- The end of the printing Gcode, also configurable in the slicer, must contain the string “ ;MESH:NONMESH” as 
the first line of the block. 

Example:
To use this module, provide the paths to the 3MF and GCODE files as command-line arguments. Optionally, provide 
paths to the parameters INI file and the output folder. For example:
python3 -m asham /home/user/example_part.3mf /home/user/example_part.gcode --path_ini_file /home/user/hybrid_parameters.ini 

Attributes:
path_3mf (str): Path to the 3MF file.
path_stl (str): Path to the STL file.
--path_ini_file (str, optional): Path to the parameters INI file.
Default is None.
--final_folder (str, optional): Path to write the hybridized Gcode. Default
is the directory of the GCODE file.

Functions:
    raise_nonmesh_travel_speed(): Modifies non-mesh travel speeds in G-code. / 
    extract_layer_data(): Extracts data from the G-code, like layer numbers and
    Z coordinates. / 
    load_model(): Loads and positions the STL model for the 3D printer. / 
    get_contour_sections(): Slices the STL at the correct heights. / 
    get_cnc_contouring_coords(): Generates a list of buffered contour slices. / 
    construct_cnc_contouring_gcode(): Produces G-code from buffered contours. / 
    find_surfacing_zones(): Scans the STL for areas to be CNC surfaced. / 
    generate_surfacing_polygon(): Creates polygons for machining from STL. / 
    generate_raw_surfacing_toolpath(): Generates raw toolpaths for surfacing. / 
    generate_surfacing_data(): Produces a list with surfacing operations info. / 
    construct_cnc_surfacing_gcode(): Produces G-code for all surfacing / 
    operations.
    merge_contour_and_surfacing_codes(): Merges contouring and surfacing / 
    G-code.
    hbd_fdm_cnc_merge_codes(): Finalizes and writes the hybridized G-code.
