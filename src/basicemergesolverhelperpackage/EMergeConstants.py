import numpy as np

m = 1.0
cm = 1e-2
mm = 1e-3
um = 1e-6
nm = 1e-9

GOhm = 1e9
MOhm = 1e6
kOhm = 1e3
Ohm = 1.0
mOhm = 1e-3
uOhm = 1e-6

H = 1.0
mH = 1e-3
uH = 1e-6
nH = 1e-9
pH = 1e-12

F = 1.0
mF = 1e-3
uF = 1e-6
nF = 1e-9
pF = 1e-12

class series_impedance:
	def __init__(self, R=0.0, L=0.0, C=0.0):
		self.R = R
		self.L = L
		self.C = C

	def __call__(self, f):
		return self.R + 1j*2*np.pi*f*self.L + (0.0 if self.C==0.0 else 1/(1j*2*np.pi*f*self.C))

class parallel_impedance:
	def __init__(self, R=0.0, L=0.0, C=0.0):
		self.R = R
		self.L = L
		self.C = C

	def __call__(self, f):
		return 1/((0.0 if self.R==0.0 else 1/self.R) + (0.0 if self.L==0 else 1/(1j*2*np.pi*f*self.L)) + 1j*2*np.pi*f*self.C)
