#!/usr/bin/python
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.node import CPULimitedHost
from mininet.node import OVSSwitch
import networkx as nx

REMOTE_CONTROLLER_IP = "127.0.0.1"

def main():
    setLogLevel('info')

    net = Mininet(controller=None, host=CPULimitedHost, link=TCLink, autoSetMacs=True)
    net.addController("c0", controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP, port=6633)

    G = nx.barabasi_albert_graph(6,3)
    G = nx.DiGraph(G)
    
    host_range = [1]

    for node in G.nodes:
        net.addSwitch("s%s" % node)
        if int(node) in host_range:
            net.addHost("h%s" % node)
            net.addLink("s%s" % node, "h%s" % node)
    for (node1, node2) in G.edges:
        net.addLink('s%s' % node1,'s%s' % node2)

    #host_1 = net.addHost('h1')
    #host_2 = net.addHost('h2')
    #host_3 = net.addHost('h3')
    #host_4 = net.addHost('h4')
    #server_1 = net.addHost('h5', cpu=0.5)
    #server_2 = net.addHost('h6', cpu=0.5)
    #switch = net.addSwitch('s1')

    #net.addLink(switch, host_1, bw=10, delay='50ms')
    #net.addLink(switch, host_2, bw=10, delay='50ms')
    #net.addLink(switch, host_3, bw=10, delay='50ms')
    #net.addLink(switch, host_4, bw=10, delay='50ms')
    #net.addLink(switch, server_1, bw=10, delay='50ms')
    #net.addLink(switch, server_2, bw=10, delay='50ms')

    net.start()
    #server_1.sendCmd("python -m SimpleHTTPServer 80 >& ./http_1.log &")
    #server_2.sendCmd("python -m SimpleHTTPServer 80 >& ./http_2.log &")
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()

