#!/usr/bin/python
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.node import CPULimitedHost
from mininet.node import OVSSwitch
import os, sys
import signal
from requests import put
import re
import socket
import fcntl
import array
import struct
import sys


REMOTE_CONTROLLER_IP = "127.0.0.1"


def getIfInfo(dst):
    is_64bits = sys.maxsize > 2 ** 32
    struct_size = 40 if is_64bits else 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    max_possible = 8  # initial value
    while True:
        bytes = max_possible * struct_size
        names = array.array('B')
        for i in range(0, bytes):
            names.append(0)
        outbytes = struct.unpack('iL', fcntl.ioctl(
            s.fileno(),
            0x8912,  # SIOCGIFCONF
            struct.pack('iL', bytes, names.buffer_info()[0])
        ))[0]
        if outbytes == bytes:
            max_possible *= 2
        else:
            break
    try:
        namestr = names.tobytes()
        namestr = namestr.decode('utf-8')
    except AttributeError:
        namestr = names.tostring()
    s.connect((dst, 0))
    ip = s.getsockname()[0]
    for i in range(0, outbytes, struct_size):
        name = namestr[i:i + 16].split('\0', 1)[0]
        addr = socket.inet_ntoa(namestr[i + 20:i + 24].encode('utf-8'))
        if addr == ip:
            return (name, addr)

def sendTopology(net, agent, collector):
    print("*** Sending topology")
    topo = {'nodes': {}, 'links': {}}
    for s in net.switches:
        topo['nodes'][s.name] = {'agent': agent, 'ports': {}}
    path = '/sys/devices/virtual/net/'
    for child in os.listdir(path):
        parts = re.match('(^.+)-(.+)', child)
        if parts is None: continue
        if parts.group(1) in topo['nodes']:
            ifindex = open(path + child + '/ifindex').read().split('\n', 1)[0]
            topo['nodes'][parts.group(1)]['ports'][child] = {'ifindex': ifindex}

    for link in net.links:
        switchName = re.findall('^s[0-9]', str(link))[0]
        switchPort = re.findall('^s[0-9]-eth[0-9]', str(link))[0]
        hostName = re.findall('h[0-9]', str(link))[0]
        hostPort = re.findall('h[0-9]-eth[0-9]', str(link))[0]
        linkName = "{}-{}".format(switchName, hostName)
        topo['links'][linkName] = {'node1': switchName, 'port1': switchPort,
                                   'node2': hostName, 'port2': hostPort}
        
    # print(topo)

    put('http://%s:8008/topology/json' % collector, json=topo)

def main():
    setLogLevel('info')

    net = Mininet(controller=None, host=CPULimitedHost, link=TCLink, autoSetMacs=True, autoStaticArp=True)
    net.addController("c0", controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP, port=6633)

    host_1 = net.addHost('h1')
    host_2 = net.addHost('h2')
    host_3 = net.addHost('h3')
    host_4 = net.addHost('h4')
    server_1 = net.addHost('h5', cpu=0.1)
    server_2 = net.addHost('h6', cpu=0.1)
    switch = net.addSwitch('s1', cls=OVSSwitch, protocols='OpenFlow15')

    net.addLink(switch, host_1, bw=10, delay='50ms')
    net.addLink(switch, host_2, bw=10, delay='100ms')
    net.addLink(switch, host_3, bw=10, delay='150ms')
    net.addLink(switch, host_4, bw=10, delay='200ms')
    net.addLink(switch, server_1, bw=10, delay='50ms')
    net.addLink(switch, server_2, bw=10, delay='50ms')

    net.start()
    server_1.sendCmd("python -m SimpleHTTPServer 80 >& ./http_1.log &")
    server_2.sendCmd("python -m SimpleHTTPServer 80 >& ./http_2.log &")
    #server_1.sendCmd("python -m SimpleHTTPServer 3000 >& ./http_1.log &")
    #server_2.sendCmd("python -m SimpleHTTPServer 3000 >& ./http_2.log &")
    os.system("ovs-vsctl -- --id=@sflow create sflow agent=lo target=\"127.0.0.1\" sampling=16 polling=10 -- set bridge s1 sflow=@sflow")
    collector = os.environ.get('COLLECTOR', '127.0.0.1')
    (ifname, agent) = getIfInfo(collector)
    sendTopology(net, agent, collector)
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()

