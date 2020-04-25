#!/usr/bin/python
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.node import CPULimitedHost

REMOTE_CONTROLLER_IP = "127.0.0.1"

def main():
    setLogLevel('info')

    net = Mininet(controller=None, host=CPULimitedHost, link=TCLink, autoSetMacs=True, autoStaticArp=True)
    net.addController("c0", controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP, port=6633)

    host_1 = net.addHost('h1')
    host_2 = net.addHost('h2')
    host_3 = net.addHost('h3')
    host_4 = net.addHost('h4')
    server_1 = net.addHost('h5', cpu=0.01)
    server_2 = net.addHost('h6', cpu=0.01)
    switch = net.addSwitch('s1')

    net.addLink(switch, host_1, bw=10)
    net.addLink(switch, host_2, bw=10)
    net.addLink(switch, host_3, bw=10)
    net.addLink(switch, host_4, bw=10)
    net.addLink(switch, server_1, bw=10)
    net.addLink(switch, server_2, bw=10)

    net.start()
    server_1.sendCmd("python -m SimpleHTTPServer 80 >& ./http_1.log &")
    server_2.sendCmd("python -m SimpleHTTPServer 80 >& ./http_2.log &")
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()

