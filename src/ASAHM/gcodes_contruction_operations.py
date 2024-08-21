# coding: utf-8

from copy import deepcopy
import shapely


def is_clockwise(line_string):
    """
    Determine if a given line string has coordinates in a clockwise order.
    
    This function computes the signed area for the provided line string. A
    negative value indicates a clockwise order, while a positive value
    indicates a counterclockwise order.
    
    Args:
        line_string (shapely.geometry.linestring.LineString): The line string
        to check.

    Returns:
        bool: True if the line string is in clockwise order, False otherwise.

    Example:
        >>> from shapely.geometry import LineString
        >>> ls = LineString([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        >>> is_clockwise(ls)
        False
    """
    coords = list(line_string.coords)
    n = len(coords) - 1
    area = sum((coords[i][0]*coords[i+1][1] - coords[i+1][0]*coords[i][1])
               for i in range(n))
    return area < 0


# Function for reversing line strings if they are not in the desired
# orientation
def reverse_line_string(line_string):
    """
    Reverse the order of coordinates in a given line string.

    This function takes a LineString and returns a new LineString with its
    coordinates in the reverse order.
    
    Args:
        line_string (shapely.geometry.linestring.LineString): The line string
        to be reversed.

    Returns:
        shapely.geometry.linestring.LineString: The reversed line string.

    Example:
        >>> from shapely.geometry import LineString
        >>> ls = LineString([(0, 0), (1, 0), (1, 1)])
        >>> reverse_ls = reverse_line_string(ls)
        >>> print(reverse_ls)
        LINESTRING (1 1, 1 0, 0 0)

    Note:
        The resulting LineString will have the same geometric properties as the
        input, but with its coordinates reversed.
    """
    return shapely.LineString(list(line_string.coords)[::-1])


def construct_cnc_contouring_gcode(gcode_datas,
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
                                   write_folder):
    """
    Constructs CNC contouring G-code for a RepRap 3D printer based on provided
    parameters. This function processes each layer of the G-code and generates
    contouring toolpaths. If `write_isolate_contouring_code` is set to True,
    the function will write the contouring Gcode alone according to the
    write_folder given in the command-line.

    Args:
        gcode_datas (list of dict): Data for each G-code layer.
        buffered_contours_list (list of dict): Buffered contours for
        processing.
        contouring_speed (str): Contouring operation speed.
        bridge_speed (str): Bridge operation speed.
        print_tool_number (str): Number identifier for the print tool.
        contour_tool_number (str): Number identifier for the contour tool.
        jump_value (float): Value of jump between operations.
        layer_height (float): Height of individual layers.
        z_contouring_adjustment (float): Adjustment for Z contouring.
        write_isolate_contouring_code (bool): Whether to write the G-code to a
        file.
        contouring_shadow_pass (bool): Enable shadow pass for contouring.
        filename (str): Name of the G-code file, if saved.
        write_folder (str): Directory for saving the G-code file.

    Returns:
        dict: Dictionary with milling coordinates for each layer.
    """

    preamble = f'{contour_tool_number}'
    postamble = f'{print_tool_number}'
    contouring_corrected_jump_value = jump_value + z_contouring_adjustment
    positive_jump = [f'G91 G0 Z{contouring_corrected_jump_value}', 'G90']
    negative_jump = [
        f'G91 G1 Z-{contouring_corrected_jump_value + layer_height}', 'G90']
    dict_milling_coord = dict()

    for j, line in enumerate(gcode_datas):
        list_coord = list()
        z_layer_height = gcode_datas[j]['layer_z_height']
        z_layer_number = gcode_datas[j]['layer_number']

        list_coord.append(f';CNC Contour Z={z_layer_height}')
        list_coord.append(f';CNC Contour Layer n°{z_layer_number}')
        list_coord.append(preamble)
        list_coord.append(f'G0 Z{z_layer_height + jump_value} F{bridge_speed}')

        for buffered_type in ['buffered_int', 'buffered_ext']:
            for key in buffered_contours_list[j][buffered_type].keys():
                contour = buffered_contours_list[j][buffered_type][key]
                contour_type = ('intern' if buffered_type == 'buffered_int'
                                else 'extern')
                list_coord.append(f';Milling {contour_type} {key} / '
                                  f'Layer={z_layer_number} / '
                                  f'Z ={z_layer_height}')
                
                for i, point in enumerate(contour):
                    x = f'X{round(point[0], 2)}'
                    y = f'Y{round(point[1], 2)}'
                    val = (z_layer_height - z_contouring_adjustment -
                           layer_height)
                    z = f'Z{round(val, 2)}'
                    if i == 0:
                        list_coord.append(f'G0 {x} {y} F{bridge_speed}')
                        list_coord.append(f'{negative_jump[0]} '
                                          f'F{bridge_speed}')
                        list_coord.append(negative_jump[1])
                    elif i > 0:
                        list_coord.append(f'G1 {x} {y} {z} '
                                          f'F{contouring_speed}')
                        
                list_coord.append(f'{positive_jump[0]} F{bridge_speed}')
                list_coord.append(positive_jump[1])

                if contouring_shadow_pass:
                    list_coord.append(f';SHADOW Milling {contour_type} {key}')
                    for i, point in enumerate(contour):
                        x = f'X{round(point[0], 2)}'
                        y = f'Y{round(point[1], 2)}'
                        val = (z_layer_height - z_contouring_adjustment -
                               layer_height)
                        z = f'Z{round(val, 2)}'
                        if i == 0:
                            list_coord.append(f'G0 {x} {y} F{bridge_speed}')
                            list_coord.append(f'{negative_jump[0]} '
                                              f'F{bridge_speed}')
                            list_coord.append(negative_jump[1])
                        elif i > 0:
                            list_coord.append(f'G1 {x} {y} {z} '
                                              f'F{contouring_speed}')
                        
                    list_coord.append(f'{positive_jump[0]} F{bridge_speed}')
                    list_coord.append(positive_jump[1])

        list_coord.append(postamble)
        list_coord.append(' \n')
        list_coord.append(';Return at Z print')
        list_coord.append(f'G1 Z{round(z_layer_height + layer_height, 2)} '
                          f'F8000')
        dict_milling_coord[f'{z_layer_number}'] = list_coord

    if write_isolate_contouring_code:
        with open(f'{write_folder}/HBD_{filename}_contouring.gcode', 'w',
                  encoding="utf-8") as f:
            for lines in dict_milling_coord.values():
                for line in lines:
                    f.write(line + '\n')

    return dict_milling_coord


def construct_cnc_surfacing_gcode(surfacing_data,
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
                                  write_folder):
    """
    Constructs CNC surfacing G-code based on the provided parameters.

    Args:
        surfacing_data (list): Dictionary containing the surfacing data.
        surfacing_speed (str): Speed for the surfacing operation.
        bridge_speed (str): Speed for bridging operations.
        surfacing_tool_number (str): Tool number for surfacing.
        print_tool_number (str): Tool number for printing.
        surfacing_jump_value (float): Jump value for surfacing.
        layer_height (float): Height of each layer.
        write_isolate_surfacing_code:
        surfacing_swoop_speed (str): Speed for surfacing swoop.
        surfacing_shadow_pass (int): Number of shadow passes for surfacing.
        surfacing_roughing_pass_value (float): Value for surfacing roughing
        pass.
        surfacing_roughing_pass (bool): Whether to perform a roughing pass.
        filename (str): Name of the output file.
        write_folder (str): Destination folder for the output file.

    Returns:
        dict_surfacing_coord (dict): Dictionary containing the coordinates for
        surfacing.

    Notes:
        This function generates G-code for CNC surfacing operations based on
        the input parameters. If `write_isolate_surfacing_code` is True, the
        generated G-code alone will be written to the write_folder folder.

    """

    preamble = f'{surfacing_tool_number}'
    postamble = f'{print_tool_number}'
    surfacing_corrected_jump_value = surfacing_jump_value
    dict_surfacing_coord = {}

    negative_jump = [f'G91 G1 Z-{surfacing_corrected_jump_value}', 'G90']

    for j, operation in enumerate(surfacing_data):
        list_surfacing_path = list()
        z_layer_height = operation['Surface_z_height']
        list_surfacing_path.append(f';CNC Surfacing Z={z_layer_height}')
        list_surfacing_path.append(preamble)
        val = z_layer_height + surfacing_corrected_jump_value
        list_surfacing_path.append(f'G0 Z{val} F{bridge_speed}')
        
        geometries = surfacing_data[j]['Surfacing_passes']
        if isinstance(geometries, shapely.geometry.LineString):
            geometries = [geometries]
        else:
            geometries = list(geometries.geoms)
            
        for i, toolpath in enumerate(geometries):
            if is_clockwise(toolpath):
                geometries[i] = reverse_line_string(toolpath)

        if surfacing_roughing_pass:
            list_surfacing_path.append(f'\n;ROUGH PASS Surfacing Z='
                                       f'{z_layer_height}')
            
            for toolpath in geometries:
                list_coord = list(toolpath.coords)
                for i, coord in enumerate(list_coord):
                    x = f'X{round(coord[0], 3)}'
                    y = f'Y{round(coord[1], 3)}'
                    z = f'Z{z_layer_height + surfacing_roughing_pass_value}'
                    if i == 0:
                        list_surfacing_path.append(f'G0 {x} {y} '
                                                   f'F{bridge_speed}')
                        list_surfacing_path += (negative_jump +
                                                [f'F{surfacing_swoop_speed}'])
                    else:
                        list_surfacing_path.append(f'G1 {x} {y} {z} '
                                                   f'F{surfacing_speed}')
                val = z_layer_height + surfacing_corrected_jump_value
                list_surfacing_path.append(f'G0 Z{val} '
                                           f'F{surfacing_swoop_speed}')
            
        for toolpath in geometries:
            list_coord = list(toolpath.coords)
            for i, coord in enumerate(list_coord):
                x = f'X{round(coord[0], 3)}'
                y = f'Y{round(coord[1], 3)}'
                z = f'Z{z_layer_height}'
                if i == 0:
                    list_surfacing_path.append(f'G0 {x} {y} F{bridge_speed}')
                    list_surfacing_path += (negative_jump +
                                            [f'F{surfacing_swoop_speed}'])
                else:
                    list_surfacing_path.append(f'G1 {x} {y} {z} '
                                               f'F{surfacing_speed}')
            val = z_layer_height + surfacing_corrected_jump_value
            list_surfacing_path.append(f'G0 Z{val} F{surfacing_swoop_speed}')

        if surfacing_shadow_pass == 1:
            list_surfacing_path.append(f'\n;SHADOW Surfacing '
                                       f'Z={z_layer_height}')
            for toolpath in geometries:
                list_coord = list(toolpath.coords)
                for i, coord in enumerate(list_coord):
                    x = f'X{round(coord[0], 3)}'
                    y = f'Y{round(coord[1], 3)}'
                    z = f'Z{z_layer_height}'
                    if i == 0:
                        list_surfacing_path.append(f'G0 {x} {y} '
                                                   f'F{bridge_speed}')
                        list_surfacing_path += (negative_jump +
                                                [f'F{surfacing_swoop_speed}'])
                    else:
                        list_surfacing_path.append(f'G1 {x} {y} {z} '
                                                   f'F{surfacing_speed}')
                val = z_layer_height + surfacing_corrected_jump_value
                list_surfacing_path.append(f'G0 Z{val} '
                                           f'F{surfacing_swoop_speed}')
            
        if surfacing_shadow_pass == 2:
            list_surfacing_path.append(f'\n;SHADOW Surfacing N° 1 '
                                       f'Z={z_layer_height}')
            for toolpath in geometries:
                list_coord = list(toolpath.coords)
                for i, coord in enumerate(list_coord):
                    x = f'X{round(coord[0], 3)}'
                    y = f'Y{round(coord[1], 3)}'
                    z = f'Z{z_layer_height}'
                    if i == 0:
                        list_surfacing_path.append(f'G0 {x} {y} '
                                                   f'F{bridge_speed}')
                        list_surfacing_path += (negative_jump +
                                                [f'F{surfacing_swoop_speed}'])
                    else:
                        list_surfacing_path.append(f'G1 {x} {y} {z} '
                                                   f'F{surfacing_speed}')
                val = z_layer_height + surfacing_corrected_jump_value
                list_surfacing_path.append(f'G0 Z{val} '
                                           f'F{surfacing_swoop_speed}')
            
            list_surfacing_path.append(f'\n;SHADOW Surfacing N° 2 '
                                       f'Z={z_layer_height}')
            for toolpath in geometries:
                list_coord = list(toolpath.coords)
                for i, coord in enumerate(list_coord):
                    x = f'X{round(coord[0], 3)}'
                    y = f'Y{round(coord[1], 3)}'
                    z = f'Z{z_layer_height}'
                    if i == 0:
                        list_surfacing_path.append(f'G0 {x} {y} '
                                                   f'F{bridge_speed}')
                        list_surfacing_path += (negative_jump +
                                                [f'F{surfacing_swoop_speed}'])
                    else:
                        list_surfacing_path.append(f'G1 {x} {y} {z} '
                                                   f'F{surfacing_speed}')
                val = z_layer_height + surfacing_corrected_jump_value
                list_surfacing_path.append(f'G0 Z{val} '
                                           f'F{surfacing_swoop_speed}')

        list_surfacing_path.append(postamble)
        list_surfacing_path.append(' \n')
        list_surfacing_path.append(';Return at Z print')
        val = z_layer_height + layer_height
        list_surfacing_path.append(f'G1 Z{round(val, 2)} F8000')
        dict_surfacing_coord[f'{z_layer_height}'] = list_surfacing_path
        
    if write_isolate_surfacing_code:
        with open(f'{write_folder}/HBD_{filename}_surfacing_CNC.gcode', 'w',
                  encoding="utf-8") as f:
            for key, lines in dict_surfacing_coord.items():
                for line in lines:
                    f.write(line + '\n')
                
    return dict_surfacing_coord


# Merges the contouring and surfacing ops at the right heights
def merge_contour_and_surfacing_codes(dict_surfacing_coord,
                                      dict_milling_coord,
                                      write_cnt_surf_merged_code,
                                      filename,
                                      write_folder):
    """
    Merges contouring and surfacing operations at the specified Z heights.

    This function combines the G-code operations from `dict_surfacing_coord`
    (surfacing) and `dict_milling_coord` (contouring). If
    `write_cnt_surf_merged_code` is True, it will write a file of Gcode alone.

    Args:
        dict_surfacing_coord (dict): Dictionary with Z heights as keys and
        their corresponding surfacing G-code as values.
        dict_milling_coord (dict): Dictionary with layer information as keys
        and their corresponding contouring G-code as values.
        write_cnt_surf_merged_code (bool): If True, writes the merged G-code to
        a file.
        filename (str): Name of the output file if `write_cnt_surf_merged_code`
        is True.
        write_folder (str): Destination folder for the output file if
        `write_cnt_surf_merged_code` is True.

    Returns:
        dict: Dictionary with layer information as keys and the merged G-code
        for both contouring and surfacing as values.

    """

    merged_cnt_surfacing_dict = dict()
    surfacing_heights = list(dict_surfacing_coord.keys())
    for layer in dict_milling_coord.keys():
        z = dict_milling_coord[layer][0][15::]
        cnt_content = dict_milling_coord[layer]
        for key in surfacing_heights:
            if float(z) >= float(key):
                surf_content = dict_surfacing_coord[key]
                # remove T2 call, because we are going to contour after...
                del surf_content[-4]
                # remove T3 call, because surf op already called it
                del cnt_content[2]
                cnt_content = surf_content + cnt_content
                surfacing_heights.remove(key)
                
        merged_cnt_surfacing_dict[f'{layer}'] = cnt_content
         
    if write_cnt_surf_merged_code:
        with open(f'{write_folder}/HBD_{filename}_merged_CNC.gcode', 'w',
                  encoding="utf-8") as f:
            for lines in merged_cnt_surfacing_dict.values():
                for line in lines:
                    f.write(line + '\n')
    return merged_cnt_surfacing_dict


def hbd_fdm_cnc_merge_codes(gcode,
                            gcode_datas,
                            merged_cnt_surfacing_dict,
                            filename,
                            write_folder):
    """
    Merges FDM and CNC G-codes into a single G-code sequence.
    This function inserts the CNC G-code operations from
    `merged_CNT_surfacing_dict` at the correct positions in the original
    `gcode` based on the layer information provided in `gcode_datas`. The
    merged G-code is saved to a file in the `write_folder`.

    Args:
        gcode (list[str]): Initial G-code sequence.
        gcode_datas (list[dict]): Information about each layer, including the
        layer's ending line (`layer_ending_line`) and its number
        (`layer_number`).
        merged_cnt_surfacing_dict (dict): Dictionary with layer numbers as keys
        and corresponding CNC G-code operations as values.
        filename (str): Name for the output file.
        write_folder (str): Directory to save the output file.

    Returns:
        list[str]: Merged G-code sequence.

    Notes:
        - The function uses deep copying to ensure the original `gcode` remains
          unchanged.
        - The resulting G-code contains sequences from both FDM printing and
          CNC operations in the correct execution order.
    """

    temp_merged_gcode = deepcopy(gcode)
    for index, line in reversed(list(enumerate(temp_merged_gcode))):
        for i, data in enumerate(gcode_datas):
            if index == gcode_datas[i]['layer_ending_line']:
                layer = str(gcode_datas[i]['layer_number'])
                if i == len(gcode_datas) - 1:
                    temp_merged_gcode.insert(index,
                                             merged_cnt_surfacing_dict[layer])
                else:
                    temp_merged_gcode.insert(index + 5,
                                             merged_cnt_surfacing_dict[layer])
    merged_gcode = list()
    for line in temp_merged_gcode:
        if isinstance(line, str):
            merged_gcode.append(line)
        if isinstance(line, list):
            for element in line:
                merged_gcode.append(element)
    with open(f'{write_folder}/HBD_{filename}.gcode', 'w',
              encoding="utf-8") as f:
        for line in merged_gcode:
            f.write(line + '\n')
    return merged_gcode
