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


# Inductor calculation based on Inductor Toolkit for ADS by Volker Muehlhaus

import math

MU0 = 4*math.pi*1e-7

# calculate diameter for given target inductance

def calculate_inductor_diameter (N, w, s, Ltarget, K1, K2, L0):
  # Calculate the inductance from Wheeler's equation, based on N,w,s and target L
  # This calculation is for DC, no high frequency effects
  # Valid for normal spiral and overlay transformer

  # input data is required in MKS units

  # K1, K2 vary by shape and can also vary by technology (metal layer thickness etc.)
  # L0 is an offset that accounts for feedline inductance, on top of the "core" inductor shape

  # calculation must be done in MKS units
  um = 1E-6
  
  Lsyn = Ltarget - L0
  b = 2*N*w*um + 2*(N-1)*s*um # difference between outer and inner diameter
  c = K1*MU0*N*N 	      # constant in Wheeler's equation

  p = -(b + Lsyn/c)
  q = b*b/4 - Lsyn*b*(K2-1)/(2*c)
  Dout = (-p/2 + math.sqrt(p*p/4-q))/um # output is in micron
  return Dout


def calculate_octa_diameter (N, w, s, Ltarget, K1=2.25, K2=3.55, L0=0):
  # standard value for octagon: K1=2.25, K2=3.55
  return calculate_inductor_diameter (N, w, s, Ltarget, K1, K2, L0)

def calculate_square_diameter (N, w, s, Ltarget, K1=2.34, K2=2.75, L0=0):
  # standard value for square: K1=2.34, K2=2.75
  return calculate_inductor_diameter (N, w, s, Ltarget, K1, K2, L0)




