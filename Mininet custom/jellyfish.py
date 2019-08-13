from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.node import CPULimitedHost, RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from functools import partial
import os
import time
import numpy as np

# n = num of nodes
# swPort = num of port per switch
# netPort = num of network port per switch
# toLink = switch to pair
# degreeUsed = to check if switch has fulfil the network degree
# h = num of hosts is equal to h = n * (swPort - netPort)

# =================================================
# Edit parameter here
# =================================================
OFVersion = "OpenFlow13"
n = 204  # 20, 28, 45
swPort = 16
netPort = 4
h = n * (swPort - netPort)
bw = 1000
bw_client = 1000 / h
sw_list = []
mat = np.zeros((n, n))


def jml_host(n, swPort, netPort):
    return (n * (swPort - netPort))


def Jellyfish(n, swPort, netPort):
    print("Creating Jellyfish Topology with RRG(%s, %s, %s)" % (n, swPort, netPort))

    toLink = []
    degreeUsed = []
    for i in range(n):
        toLink.append(i)
        degreeUsed.append(0)

    stopSign = False

    while (len(toLink) != 0 and not stopSign):
        p1 = -1
        p2 = -1
        found = False
        iteration = 1

        while (not found and (iteration < 1000)):
            p1 = np.random.randint(len(toLink))
            p2 = p1
            while (p2 == p1):
                p2 = np.random.randint(len(toLink))

            src = toLink[p1]
            dst = toLink[p2]
            if (mat[src, dst] != 1 and mat[src, dst] != 1):
                found = True
                mat[src, dst] = 1
                mat[dst, src] = 1

        if (iteration > 1000):
            print('Unable to find new pair for link between: ', toLink)
            stopSign = True

        if (not stopSign):
            degreeUsed[p1] += 1
            degreeUsed[p2] += 1
            p1Deleted = False
            if (degreeUsed[p1] == netPort):
                toLink.pop(p1)
                degreeUsed.pop(p1)
                p1Deleted = True

            if (p1Deleted and p1 < p2):
                p2 -= 1

            if (degreeUsed[p2] == netPort):
                toLink.pop(p2)
                degreeUsed.pop(p2)

        if (len(toLink) == 1):
            print('Remaining just one node to link with degree ', degreeUsed[0], ' out of ', netPort)
            stopSign = True

        iteration += 1
    return mat


class JFTopo(Topo):
    def __init__(self, **opts):
        Topo.__init__(self, **opts)

        # Make hosts
        h = jml_host(n, swPort, netPort)
        for i in range(h):
            self.addHost('h%s' % (i + 1))

        # Make switches
        sw = n
        for i in range(sw):
            self.addSwitch('s%s' % (i + 1))

        # Connecting hosts with switches
        cHost = 1
        for i in range(sw):
            for j in range(swPort - netPort):
                if cHost == 1:
                    self.addLink('h%s' % cHost, 's%s' % (i + 1), bw=bw)
                else:
                    self.addLink('h%s' % cHost, 's%s' % (i + 1), bw=bw)
                cHost += 1

        # Connecting all switches
        mat = Jellyfish(n, swPort, netPort)
        for i in range(sw):
            for j in range(i + 1, sw):
                if (mat[i, j] == 1):
                    print('s%s' % (i + 1) + ' connected to ' + 's%s' % (j + 1))
                    self.addLink('s%s' % (i + 1), 's%s' % (j + 1), bw=bw)


def run():
    os.system('mn -c')
    c0 = RemoteController('c1', '127.0.0.1')
    ovs13 = partial(OVSKernelSwitch, protocols=OFVersion)
    topo = JFTopo()
    net = Mininet(topo=topo, link=TCLink, controller=None, switch=ovs13, autoSetMacs=True)
    net.addController(c0)
    net.start()
    print('==== Total server(s) = %s' % h)
    print('==== Total switches(s) = %s' % n)
    print('==== Initiating topology ping test...')

    # Getting switch few switches
    for i in range(n):
        if mat[0, i] == 1:
            sw_list.append('s%s' % (i + 1))

    # Fetch all host
    host = []
    for i in range(h):
        host.append(net.get('h%s' % (i + 1)))

    # net.pingAll()

    # Make directory for result
    directory = '/home/DCResult/Jellyfish' + str(n)
    os.system('mkdir -p ' + directory + '/latency')
    os.system('mkdir -p ' + directory + '/convergence')
    os.system('mkdir -p ' + directory + '/throughput')

    # Homemade pingall
    print
    '==== Pingall from h1 to all hosts to initiate paths...'
    print
    '==== Pingall will be initiate in 1 second'
    time.sleep(1)
    for i in range(1, len(host)):
        # print "h1 pinging to %s" % host[i]
        host[0].cmd('ping %s -c 1 &' % host[i].IP())

    # h1 as iperf server
    print('Wait 55 sec for test to complete')

    print
    '==== Latency test'
    for i in range(1, len(host)):
        host[i].cmd('ping 10.0.0.1 -c 10 > ' + directory + '/latency/h%s.txt &' % (i + 1))
        # host[i].cmdPrint('iperf -c 10.0.0.1 -b 100 > /home/DCResult/Jellyfish/iperf/resIperf-h%s.txt &' % (i + 1))
        # host[i].cmd('iperf -c 10.0.0.1 -t 10 -y C >> /home/DCResult/Jellyfish/throughput/throughput.csv &')
    time.sleep(15)

    print
    '==== Throughput test'
    # Using Nping as background traffic
    ips = ''
    for i in range(2, len(host) - 1):
        ips += host[i].IP() + ' '

    host[0].cmd('iperf -s &')
    host[1].cmd('nping -c 10 --tcp ' + ips + '&')
    host[-1].cmd('iperf -c 10.0.0.1 -t 10 -i 1 > ' + directory + '/throughput/throughput.txt &')
    time.sleep(20)

    print
    '==== Convergence test'
    host[-1].cmd('ping 10.0.0.1 -c 20 -D > ' + directory + '/convergence/convergence.txt &')
    time.sleep(3)
    for i in range(0, len(sw_list)):
        net.configLinkStatus('s1', sw_list[i], 'down')
    time.sleep(0.5)
    net.configLinkStatus('s1', sw_list[0], 'up')
    time.sleep(17)

    os.system('chmod -R 777 /home/DCResult')

    # CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()
