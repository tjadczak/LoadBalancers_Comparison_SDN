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
import time


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
        switchName = re.findall('^s\d{1,2}', str(link))[0]
        switchPort = re.findall('^s\d{1,2}-eth\d{1,2}', str(link))[0]
        hostName = re.findall('h\d{1,2}', str(link))[0]
        hostPort = re.findall('h\d{1,2}-eth\d{1,2}', str(link))[0]
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
    host_5 = net.addHost('h5')
    host_6 = net.addHost('h6')
    host_7 = net.addHost('h7')
    host_8 = net.addHost('h8')
    host_9 = net.addHost('h9')
    host_10 = net.addHost('h10')
    server_1 = net.addHost('h11', cpu=0.05)
    server_2 = net.addHost('h12', cpu=0.05)
    server_3 = net.addHost('h13', cpu=0.05)
    switch = net.addSwitch('s1', cls=OVSSwitch, protocols='OpenFlow15')

    net.addLink(switch, host_1, bw=5, delay='20ms')
    net.addLink(switch, host_2, bw=5, delay='40ms')
    net.addLink(switch, host_3, bw=5, delay='60ms')
    net.addLink(switch, host_4, bw=5, delay='80ms')
    net.addLink(switch, host_5, bw=5, delay='100ms')
    net.addLink(switch, host_6, bw=5, delay='120ms')
    net.addLink(switch, host_7, bw=5, delay='140ms')
    net.addLink(switch, host_8, bw=5, delay='160ms')
    net.addLink(switch, host_9, bw=5, delay='180ms')
    net.addLink(switch, host_10, bw=5, delay='200ms')
    net.addLink(switch, server_1, bw=20, delay='20ms')
    net.addLink(switch, server_2, bw=20, delay='50ms')
    net.addLink(switch, server_3, bw=25, delay='70ms')

    net.start()
    server_1.sendCmd("nohup python -m SimpleHTTPServer 80 &")
    server_2.sendCmd("nohup python -m SimpleHTTPServer 80 &")
    server_3.sendCmd("nohup python -m SimpleHTTPServer 80 &")
    server_1.waitOutput()
    server_2.waitOutput()
    server_3.waitOutput()
    server_1.sendCmd("nohup python -m SimpleHTTPServer 3000 &")
    server_2.sendCmd("nohup python -m SimpleHTTPServer 3000 &")
    server_3.sendCmd("nohup python -m SimpleHTTPServer 3000 &")
    os.system("ovs-vsctl -- --id=@sflow create sflow agent=lo target=\"127.0.0.1\" sampling=16 polling=10 -- set bridge s1 sflow=@sflow")
    collector = os.environ.get('COLLECTOR', '127.0.0.1')
    (ifname, agent) = getIfInfo(collector)
    sendTopology(net, agent, collector)
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()

