# Balun for EM simulation

import math, sys, os

# import inductor shape library
from pclab import *   # https://github.com/dgrujic/pcLab


tech = Technology("SG13G2.tech")

w = 4.0
s = 2.0
d_outer = 200 
nturns = 3.0

sig_lay = "TopMetal1"
underpass_lay = "Metal5"
secondary_lay= "TopMetal2"
ind_geom = "octagon" # valid choices: "rect", "octagon"


# Generate balun 
balun = balun2x1_broadsidecoupled(tech)
valid = balun.setupGeometry(d_outer, w, w, 0.0, sig_lay, underpass_lay, secondary_lay, s, ind_geom)
balun.genGeometry()

# Create layout file
balun_name = f"{type(balun).__name__}_{ind_geom}_do{d_outer}_w{w}_s{s}"
filename = balun_name + '.gds'
balun.genGDSII(balun_name + '.gds', structName = balun_name)
print('Created file ',balun_name + '.gds')

# create GDSII with ports for EM simulation, file suffix is "_forEM.gds" 
gds_pin2viaport(filename, width=w, port_layer_start=201, add_frame=True, frame_layer=8, frame_margin=20)             

