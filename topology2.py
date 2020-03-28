#!/usr/bin/python

from mininet.topo import Topo

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.topo import Topo
from mininet.node import RemoteController


REMOTE_CONTROLLER_IP = "127.0.0.1"


class MyTopo(Topo):
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        # Add hosts and switches
        host_1 = self.addHost('h1')
        host_2 = self.addHost('h2')
        host_3 = self.addHost('h3')
        host_4 = self.addHost('h4')
        server_1 = self.addHost('h5')
        server_2 = self.addHost('h6')
        switch = self.addSwitch('s1')

        # Add Links
        self.addLink(switch, host_1, bw=10)
        self.addLink(switch, host_2, bw=10)
        self.addLink(switch, host_3, bw=10)
        self.addLink(switch, host_4, bw=10)
        self.addLink(switch, server_1, bw=10)
        self.addLink(switch, server_2, bw=10)


def main():
    setLogLevel('info')
    topo = {'mytopo': (lambda: MyTopo())}
    net = Mininet(topo=topo,
                  controller=None,
                  autoStaticArp=True)
    net.addController("c0",
                      controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP,
                      port=6633)
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()

