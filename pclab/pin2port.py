# Copyright 2026 Volker Muehlhaus (volker@muehlhaus.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, math, gdspy

PORT_SIDE_LEFT   = 0
PORT_SIDE_TOP    = 1
PORT_SIDE_RIGHT  = 2
PORT_SIDE_BOTTOM = 3
PORT_SIDE_UNKNOWN = 4

DELTA = 0.1 # size of port perpendicular to width


def gds_pin2viaport (input_filename, width=10, port_layer_start=201, add_frame=True, frame_layer=0, frame_width = 0, frame_margin=0):
    """Read GDSII file (created by pclab shape generator) and save to new file (suffix _forEM.gds) with EM ports and ground frame added for gds2palace EM workflow

    Args:
        input_filename (string): GDSII input file from pclad, with labels for pins
        width (int): Width of terminals at the ports. Defaults to 10.
        port_layer_start (int, optional): First layer number for generating port geometry. Defaults to 201.
        add_frame (bool, optional): Switch for adding ground frame. Defaults to True.
        frame_layer (int, optional): Layer number for ground frame. Defaults to 0.
        frame_width (float, optional): Width of ground frame. Defaults to 5*width.
        frame_margin (float, optional): Distance from GDSII geometry to inner side of ground frame. Defaults to 0.5*bounding box size (measured in x direction).

    Returns:
        dictionary: key is pin name, value is array [created port layer, pox x, pos y]
    """
    port_dict = {}  # this is where we store port (pin) information: name and position


    if os.path.isfile(input_filename):
        output_filename = input_filename.replace(".gds","_forEM.gds")
        output_library = gdspy.GdsLibrary(infile=input_filename)

        toplevel_cell_list = output_library.top_level()
        cell = output_library.cells.get('', toplevel_cell_list[0])

        bbox = cell.get_bounding_box()
        xmin = bbox[0][0]
        xmax = bbox[1][0]
        ymin = bbox[0][1]
        ymax = bbox[1][1]
        # print(f'xmin = {xmin}, xmax = {xmax}, ymin ={ymin}, ymax = {ymax}')

        # read labels and place geometry for via port there
        # store for each side which ports we have there
        ports_left = []
        ports_right = []
        ports_top = []
        ports_bottom = []


        for n, label in enumerate(cell.labels):
            xlabel = label.position[0]
            ylabel = label.position[1]

            # estimate port orientation from label position relative to bounding box
            if xlabel==xmin:
                # label on left side
                position = PORT_SIDE_LEFT
                ports_left.append(label.text)
            elif xlabel==xmax:
                # label on right side
                position = PORT_SIDE_RIGHT
                ports_right.append(label.text)
            elif ylabel==ymax:
                # label on top side
                position = PORT_SIDE_TOP
                ports_top.append(label.text)
            elif ylabel==ymin:
                # label on bottom side
                position = PORT_SIDE_BOTTOM
                ports_bottom.append(label.text)
            else:
                # label position not on any boundary
                position = PORT_SIDE_UNKNOWN

            # process only ports on the bounding box
            if position in [PORT_SIDE_LEFT, PORT_SIDE_RIGHT, PORT_SIDE_TOP, PORT_SIDE_BOTTOM]:
                port_layer = port_layer_start+n
                port_dict[label.text]=[port_layer, xlabel, ylabel]
                # draw a line on port_layer with width specified as a parameter in call to this function
                if position in [PORT_SIDE_LEFT]:
                    # draw line in y direction
                    p1 = (xlabel, ylabel-width/2)
                    p2 = (xlabel+DELTA, ylabel+width/2)
                elif position in [PORT_SIDE_RIGHT]:
                    # draw line in y direction
                    p1 = (xlabel, ylabel-width/2)
                    p2 = (xlabel-DELTA, ylabel+width/2)
                elif position in [PORT_SIDE_TOP]:
                    # draw line in x direction
                    p1 = (xlabel-width/2, ylabel)
                    p2 = (xlabel+width/2, ylabel-DELTA)
                else:
                    # draw line in x direction
                    p1 = (xlabel-width/2, ylabel)
                    p2 = (xlabel+width/2, ylabel+DELTA)
                rect = gdspy.Rectangle(p1, p2, layer=port_layer, datatype=0)
                cell.add(rect)

        # create ground frame 
        if add_frame:
            if frame_width==0:
                frame_width = 5 * width
            if frame_margin==0:
                frame_margin = 0.5*(xmax-xmin) # half component size

            # raw frame at the given distance        
            # calculate inner and outer edges of the frame
            xmin_frame_inner = xmin - frame_margin
            xmax_frame_inner = xmax + frame_margin
            ymin_frame_inner = ymin - frame_margin
            ymax_frame_inner = ymax + frame_margin

            xmin_frame_outer = xmin_frame_inner - frame_width
            xmax_frame_outer = xmax_frame_inner + frame_width
            ymin_frame_outer = ymin_frame_inner - frame_width
            ymax_frame_outer = ymax_frame_inner + frame_width

            rect = gdspy.Rectangle((xmin_frame_outer,ymin_frame_outer), (xmin_frame_inner,ymax_frame_outer), layer=frame_layer, datatype=0)
            cell.add(rect)
            rect = gdspy.Rectangle((xmax_frame_inner,ymin_frame_outer), (xmax_frame_outer,ymax_frame_outer), layer=frame_layer, datatype=0)
            cell.add(rect)
            rect = gdspy.Rectangle((xmin_frame_inner,ymin_frame_inner), (xmax_frame_inner, ymin_frame_outer), layer=frame_layer, datatype=0)
            cell.add(rect)
            rect = gdspy.Rectangle((xmin_frame_inner,ymax_frame_inner), (xmax_frame_inner, ymax_frame_outer), layer=frame_layer, datatype=0)
            cell.add(rect)

            # check for all 4 sides what port positions we have there
            if len(ports_top)>0:
                pos_xmin =  math.inf
                pos_xmax = -math.inf
                for port_name in ports_top:
                    port = port_dict[port_name]
                    x = port[1]
                    pos_xmin = min(pos_xmin, x)
                    pos_xmax = max(pos_xmax, x)
                # extend ground on that side to port
                rect = gdspy.Rectangle((pos_xmin-width,ymax_frame_inner), (pos_xmax+width, ymax-width/2), layer=frame_layer, datatype=0)
                cell.add(rect)


            if len(ports_bottom)>0:
                pos_xmin =  math.inf
                pos_xmax = -math.inf
                for port_name in ports_bottom:
                    port = port_dict[port_name]
                    x = port[1]
                    pos_xmin = min(pos_xmin, x)
                    pos_xmax = max(pos_xmax, x)
                # extend ground on that side to port
                rect = gdspy.Rectangle((pos_xmin-width,ymin_frame_inner), (pos_xmax+width, ymin+width/2), layer=frame_layer, datatype=0)
                cell.add(rect)

            if len(ports_left)>0:
                pos_ymin =  math.inf
                pos_ymax = -math.inf
                for port_name in ports_left:
                    port = port_dict[port_name]
                    y = port[2]
                    pos_ymin = min(pos_ymin, y)
                    pos_ymax = max(pos_ymax, y)
                # extend ground on that side to port
                rect = gdspy.Rectangle((xmin_frame_inner, pos_ymin-width), (xmin+width/2, pos_ymax+width), layer=frame_layer, datatype=0)
                cell.add(rect)

            if len(ports_right)>0:
                pos_ymin =  math.inf
                pos_ymax = -math.inf
                for port_name in ports_right:
                    port = port_dict[port_name]
                    y = port[2]
                    pos_ymin = min(pos_ymin, y)
                    pos_ymax = max(pos_ymax, y)
                # extend ground on that side to port
                rect = gdspy.Rectangle((xmax_frame_inner, pos_ymin-width), (xmax-width/2, pos_ymax+width), layer=frame_layer, datatype=0)
                cell.add(rect)

        
        output_library.write_gds(output_filename)         
    else:
        print(f"File not found: {filename}")
    return port_dict


if __name__ == "__main__":
    filename = 'balun2x1_edgecoupled_octagon_do200.0_w6.0_s2.0.gds'
    # port_dict = gds_pin2viaport(filename, width=6, port_layer_start=201, add_frame=True, frame_layer=8, frame_margin=20)
    # print(port_dict)