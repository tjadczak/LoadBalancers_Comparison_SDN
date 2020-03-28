#!/usr/bin/python
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.link import TCLink


REMOTE_CONTROLLER_IP = "127.0.0.1"


def main():
    setLogLevel('info')

    net = Mininet(controller=None, link=TCLink, autoSetMacs=True)
    net.addController("c0", controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP, port=6633)
    s1 = net.addSwitch('s1')

    host_1 = net.addHost('h1')
    host_2 = net.addHost('h2')
    host_3 = net.addHost('h3')
    host_4 = net.addHost('h4')
    server_1 = net.addHost('h5')
    server_2 = net.addHost('h6')
    switch = net.addSwitch('s1')

    net.addLink(switch, host_1, bw=10)
    net.addLink(switch, host_2, bw=10)
    net.addLink(switch, host_3, bw=10)
    net.addLink(switch, host_4, bw=10)
    net.addLink(switch, server_1, bw=10)
    net.addLink(switch, server_2, bw=10)

    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()

