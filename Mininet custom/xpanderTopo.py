from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel,info
from mininet.node import CPULimitedHost
from mininet.link import TCLink
import os
import time
import random
import math
import numpy as np
from numpy import linalg as LA

def get_spectral_gap(d):
    return 2*math.sqrt(d-1)

def jml_host(d, k, sp):
	return ((d+1)*k) * (sp-d)

# This piece of code from ankit singla github topobench-1/python/xpanderGen3.py
def random_k_lift(d, k):
	switches = (d+1)*k
	mat = np.zeros( (switches,switches) )
	for meta1 in range(d+1):
		for meta2 in range(meta1+1, d+1):
			perm = np.random.permutation(k)
			for src_ind in range(k):
				src = meta1*k + src_ind
				dst = meta2*k + perm[src_ind]
				
				# Mark connected switches
				mat[src,dst] = 1
				mat[dst,src] = 1
				
	eig,vecs = LA.eig(mat)
	eig = np.abs(eig)
	eig.sort()
	if eig[-2] < get_spectral_gap(d):
		return random_k_lift(d,k)
	
	return mat

class xpanderTopo(Topo):
	def __init__(self, **opts):
		Topo.__init__(self, **opts)
	
		# Build some host
		h = jml_host(d,k,sp)
		for i in range(h):
			host = self.addHost('h%s' % (i+1))
		
		# Build some switches
		switches = (d+1)*k
		for i in range(switches):
			switch = self.addSwitch('s%s' % (i+1))
			
		# Connecting host to switch
		cHost = 1
		for i in range(switches):
			for j in range(sp-d):
				self.addLink('h%s' % cHost,'s%s' % (j+1), bw=50)
				cHost += 1
				
		# Connecting between switches
		res = random_k_lift(d,k)
		for i in range(switches):
			for j in range(i + 1, switches):
				if (res[i,j] == 1):
					print ('s%s' % (i+1) + ' connected to ' + 's%s' % (j+1))
					self.addLink('s%s' % (i+1), 's%s' % (j+1), bw=50)

def run():
	os.system('mn -c')
	topo = xpanderTopo()
	net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
	net.start()
	print ('==== Total server(s) = %s' % h)
	print ('==== Total switches = %s' % switches)
	print ('==== Initiating topology test...')
	time.sleep(3)
	net.pingAll()
	CLI(net)
	net.stop()

# d = degree
# k = number of lift
# h = number of host(s)
# s = number of switches
# sp = number of port/switch

if __name__ == '__main__':
	d = 3
	k = 4
	sp = 16
	h = jml_host(d,k,sp)
	s = (d+1)*k
    setLogLevel('info')
    run()