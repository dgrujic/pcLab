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



def calc_resize_factor (L_target, L_is_ftarget, L_is_DC):
  # finetune step: rescale diameter after initial simulation that was based on predicted DC inductance
  return L_target/L_is_ftarget *  math.pow(L_is_ftarget/L_is_DC, 0.3)


def finetune_rescale_dout (L_target, L_is_ftarget, dout, ftarget, fSRF):
  # used when repeating the finetune step
  
  fratio=math.pow(ftarget/fSRF, 0.8)
  dnew=dout*L_target/L_is_ftarget*(1-fratio) + dout*fratio
  return dnew
