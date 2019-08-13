from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.node import CPULimitedHost, RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from functools import partial
import os
import time
import random
import math
import numpy as np
from numpy import linalg as LA

# d = jumlah derajat // tidak bisa kurang dari 3 untuk skala besar
# k = jumlah lift
# sp = jumlah port per switch
# h = jumlah host
# s = jumlah switch (d +1) * k
d = 3 # 3, 3, 4
k = 51 # 5. 7. 9
sp = 16
h = ((d + 1) * k) * (sp - d)
bw = 1000
bw_client = 1000 / h
sw_list = []
s = (d + 1) * k
mat = np.zeros((s, s))

def get_spectral_gap(d):
    return 2 * math.sqrt(d - 1)


def jml_host(d, k, sp):
    return ((d + 1) * k) * (sp - d)


def random_k_lift(d, k):
    for meta1 in range(d + 1):
        for meta2 in range(meta1 + 1, d + 1):
            perm = np.random.permutation(k)
            for src_ind in range(k):
                src = meta1 * k + src_ind
                dst = meta2 * k + perm[src_ind]
                mat[src, dst] = 1
                mat[dst, src] = 1
    eig, vecs = LA.eig(mat)
    eig = np.abs(eig)
    eig.sort()
    if eig[-1] < get_spectral_gap(d):
        return random_k_lift(d, k)

    return mat


class xpanderTopo(Topo):
    def __init__(self, **opts):
        Topo.__init__(self, **opts)

        # Membuat host
        h = jml_host(d, k, sp)
        for i in range(h):
            self.addHost('h%s' % (i + 1))

        # Membuat switch
        switches = (d + 1) * k
        for i in range(switches):
            self.addSwitch('s%s' % (i + 1))

        # Menghubungkan host dengan switch
        cHost = 1
        for i in range(switches):
            for j in range(sp - d):
                if cHost == 1:
                    self.addLink('h%s' % cHost, 's%s' % (i + 1), bw=bw)
                else:
                    self.addLink('h%s' % cHost, 's%s' % (i + 1), bw=bw)
                cHost += 1

        # Menghubungkan antar switch
        mat = random_k_lift(d, k)
        for i in range(switches):
            for j in range(i + 1, switches):
                if (mat[i, j] == 1):
                    print ('s%s' % (i + 1) + ' connected to ' + 's%s' % (j + 1))
                    self.addLink('s%s' % (i + 1), 's%s' % (j + 1), bw=bw)


def run():
    os.system('mn -c')
    topo = xpanderTopo()
    OVS13 = partial(OVSKernelSwitch, protocols='OpenFlow13')
    net = Mininet(topo=topo, link=TCLink, controller=None, switch=OVS13)
    c = RemoteController('c0', '127.0.0.1')
    net.addController(c)
    net.start()
    print ('==== Total server(s) = %s' % h)
    print ('==== Total switches(s) = %s' % s)

    # Getting switch few switches
    for i in range(s):
        if mat[0, i] == 1:
            sw_list.append('s%s' % (i + 1))

    host = []
    for i in range(h):
        host.append(net.get('h%s' % (i + 1)))

    # Make directory for result
    directory = '/home/DCResult/Xpander' + str(s)
    os.system('mkdir -p ' + directory + '/latency')
    os.system('mkdir -p ' + directory + '/convergence')
    os.system('mkdir -p ' + directory + '/throughput')

    # Homemade pingall
    print '==== Pingall from h1 to all hosts to initiate paths...'
    print '==== Pingall will be initiate in 1 second'
    time.sleep(1)
    for i in range(1, len(host)):
        # print "h1 pinging to %s" % host[i]
        host[0].cmd('ping %s -c 1 &' % host[i].IP())

    print('Wait 30 sec for test to complete')
    print '==== Latency test'
    for i in range(1, len(host)):
        host[i].cmd('ping 10.0.0.1 -c 10 > ' + directory + '/latency/h%s.txt &' % (i + 1))
    time.sleep(10)

    print '==== Throughput test'
    # Using Nping as background traffic
    ips = ''
    for i in range(2, len(host) - 1):
        ips += host[i].IP() + ' '

    host[0].cmd('iperf -s &')
    host[1].cmd('nping -c 10 --tcp ' + ips + '&')
    host[-1].cmd('iperf -c 10.0.0.1 -t 10 -i 1 > ' + directory + '/throughput/throughput.txt &')
    time.sleep(10)

    print '==== Convergence test'
    host[-1].cmd('ping 10.0.0.1 -c 20 -D > ' + directory + '/convergence/convergence.txt &')
    time.sleep(3)
    for i in range(0, len(sw_list)):
        net.configLinkStatus('s1', sw_list[i], 'down')
    time.sleep(0.5)
    net.configLinkStatus('s1', sw_list[0], 'up')
    time.sleep(17)

    os.system('chmod -R 777 /home/DCResult')
    #CLI(net)
    net.stop()


if __name__ == '__main__':
    h = jml_host(d, k, sp)

    setLogLevel('info')
    run()
