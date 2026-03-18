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

# This code adds IHP SG13G2-specific layout features to an existing GDSII file

import os, gdspy, math


# ------------------------------------------------------------------------------
# Settings that are specific to IHP SG13G2 OPDK layer numbers and GDSII data types

EXTRA_LAYER_PURPOSE_PAIRS = [
    (1,23), # Activ.nofill
    (5,23), # Gatpoly nofill
    (8,23), # Metal1.nofill
    (10,23), # Metal2.nofill
    (30,23), # Metal3.nofill
    (50,23), # Metal4.nofill
    (67,23), # Metal5.nofill
    (126,23), # TopMetal1.nofill
    (134,23), # TopMetal2.nofill
    (46,21), # Pwell.block
    (148,0), # NoRCX.drawing
    (27,0)  # IND.drawing
]
PIN_PURPOSE = 2  # data type for pin shapes on metal layers

IND_PIN = (27,2)    # layer and purpose used for inductor pins in SG13G2 OPDK
IND_TEXT = (27,25)  # layer and purpose used for inductor pin labels in SG13G2 OPDK

TEXT_DRAWING = (63,0)  # layer to show additional text information

GRID = 0.01

# ------------------------------------------------------------------------------



def gds_add_sg13_features (input_filename, output_filename, optional_text='', pin_size=2):
    if os.path.isfile(input_filename):
        output_library = gdspy.GdsLibrary(infile=input_filename)

        toplevel_cell_list = output_library.top_level()
        cell = output_library.cells.get('', toplevel_cell_list[0])

        # get bounding box, so that we can design the extra layer polygons
        bbox = cell.get_bounding_box()

        xmin = bbox[0][0]
        ymin = bbox[0][1]
        xmax = bbox[1][0]
        ymax = bbox[1][1]

        # assume that we have an inductor with center at (0,0)
        # get outer coordinates (should be at feedline pins, but we evaluate all drawing now)
        # Note this is a coordinate, NOT the diameter
        max_value = max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
        
        c = max_value * (1 - 1/(2*math.sqrt(2)))
        c = round(c / GRID) * GRID 

        points = [
            (-max_value + c, -max_value),
            ( max_value - c, -max_value),
            ( max_value, -max_value + c),
            ( max_value,  max_value - c),
            ( max_value - c,  max_value),
            (-max_value + c,  max_value),
            (-max_value,  max_value - c),
            (-max_value, -max_value + c),
        ]

        # Now iterate over the EXTRA_LAYER_PURPOSE_PAIRS and add an octagon on each of them
        for LPP in EXTRA_LAYER_PURPOSE_PAIRS:
            layer, datatype = LPP
            octagon = gdspy.Polygon(points, layer=layer, datatype=datatype)
            cell.add(octagon)


        # The second step is to add pin shapes on the metal layers AND the IND layer,
        # and also add the pin text on IND.text 

        done_list = []

        for label in cell.labels:
            xlabel = label.position[0]
            ylabel = label.position[1]
            pintext = label.text
            metallayer = label.layer

            if pintext not in done_list:

                # create pin shape on the metal layer where that pin is
                p1 = (xlabel-pin_size/2, ylabel-pin_size/2)
                p2 = (xlabel+pin_size/2, ylabel+pin_size/2)
                rect = gdspy.Rectangle(p1, p2, layer=metallayer, datatype=PIN_PURPOSE)            
                cell.add(rect)

                # also add pin shape on PIN layer
                rect = gdspy.Rectangle(p1, p2, layer=IND_PIN[0], datatype=IND_PIN[1])            
                cell.add(rect)

                # clone pin label text to layer IND.text
                label = gdspy.Label(pintext, (xlabel, ylabel), layer=IND_TEXT[0], texttype=IND_TEXT[1])
                cell.add(label)

                # mark this pin label done, so that we don't repeat with extra pins created just now
                done_list.append(pintext)

        # remove pin labels from all metal layers (just leave them on IND_PIN)
        cell.remove_labels(lambda label: label.layer != IND_TEXT[0])

        # add optional text, used to show inductor parameters

        label = gdspy.Label(optional_text, (0,0), layer=TEXT_DRAWING[0], texttype=TEXT_DRAWING[1])
        cell.add(label)

       
        output_library.write_gds(output_filename)  
        return True       
    else:
        print(f"File not found: {filename}")
        return False



if __name__ == "__main__":
    # test code goes here
    filename = '../indSym_octagon_N2_do68.35_w2.01_s2.01.gds'
    gds_add_sg13_features (filename, '../final.gds', optional_text = 'line 1\nline 2\nline 3', pin_size=2)