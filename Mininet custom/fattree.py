from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.node import CPULimitedHost, RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from functools import partial
import os
import logging
import time

# =========================================
# k = pod number / total switch port
# =========================================
k = 14 # 4, 5, 6, 8, 9, 10, 11, 12, 13
swPort = 16
h = (k * k / 2) * (swPort - (k / 2))
s = ((k / 2) ** 2) + (k * k / 2) + (k * k / 2)
sw_list = []
CoreSwitchList = []
AggSwitchList = []
EdgeSwitchList = []
HostList = []
logging.basicConfig(filename='./fattree.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)


class FatTree(Topo):

    def __init__(self, k):
        " Create Fat Tree topo."
        self.pod = k
        self.iCoreLayerSwitch = (k / 2) ** 2
        self.iAggLayerSwitch = k * k / 2
        self.iEdgeLayerSwitch = k * k / 2
        self.density = swPort - (k / 2)
        self.iHost = self.iEdgeLayerSwitch * self.density

        self.bw_c2a = 1000
        self.bw_a2e = 1000
        self.bw_h2a = 1000 # / self.iHost

        # Init Topo
        Topo.__init__(self)

        self.createTopo()
        logger.debug("Finished topology creation!")

        self.createLink(bw_c2a=self.bw_c2a,
                        bw_a2e=self.bw_a2e,
                        bw_h2a=self.bw_h2a)
        logger.debug("Finished adding links!")
    #    self.set_ovs_protocol_13()
    #    logger.debug("OF is set to version 1.3!")
    def createTopo(self):
        self.createCoreLayerSwitch(self.iCoreLayerSwitch)
        self.createAggLayerSwitch(self.iAggLayerSwitch)
        self.createEdgeLayerSwitch(self.iEdgeLayerSwitch)
        self.createHost(self.iHost)
    """
    Create Switch and Host
    """
    def _addSwitch(self, number, level, switch_list):
        for x in xrange(1, number + 1):
            PREFIX = str(level) + "00"
            if x >= int(10):
                PREFIX = str(level) + "0"
            switch_list.append(self.addSwitch('s' + PREFIX + str(x)))

    def createCoreLayerSwitch(self, NUMBER):
        logger.debug("Create Core Layer")
        self._addSwitch(NUMBER, 1, CoreSwitchList)

    def createAggLayerSwitch(self, NUMBER):
        logger.debug("Create Agg Layer")
        self._addSwitch(NUMBER, 2, AggSwitchList)

    def createEdgeLayerSwitch(self, NUMBER):
        logger.debug("Create Edge Layer")
        self._addSwitch(NUMBER, 3, EdgeSwitchList)

    def createHost(self, NUMBER):
        logger.debug("Create Host")
        for x in xrange(1, NUMBER + 1):
            PREFIX = "h"
            if x >= int(10):
                PREFIX = "h"
            elif x >= int(100):
                PREFIX = "h"
            HostList.append(self.addHost(PREFIX + str(x)))
    """
    Add Link
    """
    def createLink(self, bw_c2a, bw_a2e, bw_h2a):
        logger.debug("Add link Core to Agg.")
        end = self.pod / 2
        for x in xrange(0, self.iAggLayerSwitch, end):
            for i in xrange(0, end):
                for j in xrange(0, end):
                    linkopts = dict(bw=bw_c2a, use_htb=True)
                    self.addLink(
                        CoreSwitchList[i * end + j],
                        AggSwitchList[x + i],
                        **linkopts)

        logger.debug("Add link Agg to Edge.")
        for x in xrange(0, self.iAggLayerSwitch, end):
            for i in xrange(0, end):
                for j in xrange(0, end):
                    linkopts = dict(bw=bw_a2e, use_htb=True)
                    self.addLink(
                        AggSwitchList[x + i], EdgeSwitchList[x + j],
                        **linkopts)
                    if (x + j) == 0:
                        sw_list.append(AggSwitchList[x + i])

        logger.debug("Add link Edge to Host.")
        for x in xrange(0, self.iEdgeLayerSwitch):
            for i in xrange(0, self.density):
                linkopts = dict(bw=bw_h2a, use_htb=True)
                self.addLink(
                    EdgeSwitchList[x],
                    HostList[self.density * x + i],
                    **linkopts)


def run():
    os.system('mn -c')
    c0 = RemoteController('c1', '127.0.0.1')
    ovs13 = partial(OVSKernelSwitch, protocols="OpenFlow13")
    topo = FatTree(k)
    net = Mininet(topo=topo, link=TCLink, controller=None, switch=ovs13, autoSetMacs=True)
    net.addController(c0)
    net.start()
    print ('==== Total server(s) = %s' % h)
    print ('==== Total switches(s) = %s' % s)
    print ('==== Initiating topology ping test...')
    host = []
    for i in range(h):
        host.append(net.get('h%s' % (i + 1)))

    # Make directory for result
    directory = '/home/DCResult/FatTree' + str(s)
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
    print('Wait 40 sec for test to complete')

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
    print sw_list
    host[-1].cmd('ping 10.0.0.1 -c 20 -D > ' + directory + '/convergence/convergence.txt &')
    time.sleep(3)
    for i in range(len(sw_list)):
        print 'cut off ', EdgeSwitchList[0], AggSwitchList[i]
        net.configLinkStatus(EdgeSwitchList[0], AggSwitchList[i], 'down')
    time.sleep(0.5)
    print 'turn up ', EdgeSwitchList[0], AggSwitchList[0]
    net.configLinkStatus(EdgeSwitchList[0], AggSwitchList[0], 'up')
    time.sleep(17)
    os.system('chmod -R 777 /home/DCResult')
    #CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
