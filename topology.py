#!/usr/bin/python
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.node import CPULimitedHost
from mininet.node import OVSSwitch
import os, sys, fnmatch
import signal
from requests import put
import re
import socket
import fcntl
import array
import struct
import sys
import time
import random
import csv
from openpyxl import Workbook

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

    host_1 = net.addHost('h1', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_2 = net.addHost('h2', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_3 = net.addHost('h3', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_4 = net.addHost('h4', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_5 = net.addHost('h5', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_6 = net.addHost('h6', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_7 = net.addHost('h7', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_8 = net.addHost('h8', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_9 = net.addHost('h9', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    host_10 = net.addHost('h10', cpu=0.1, loss=0.01, max_queue_size=1000, use_htb=True)
    server_1 = net.addHost('h11', cpu=0.25, max_queue_size=3000, use_htb=True)
    server_2 = net.addHost('h12', cpu=0.25, max_queue_size=3000, use_htb=True)
    server_3 = net.addHost('h13', cpu=0.25, max_queue_size=3000, use_htb=True)
    server_4 = net.addHost('h14', cpu=0.25, max_queue_size=3000, use_htb=True)
    switch = net.addSwitch('s1', cls=OVSSwitch, protocols='OpenFlow15')

    net.addLink(switch, host_1, bw=1, delay='25ms')
    net.addLink(switch, host_2, bw=1, delay='25ms')
    net.addLink(switch, host_3, bw=1, delay='25ms')
    net.addLink(switch, host_4, bw=1, delay='25ms')
    net.addLink(switch, host_5, bw=1, delay='25ms')
    net.addLink(switch, host_6, bw=1, delay='25ms')
    net.addLink(switch, host_7, bw=1, delay='25ms')
    net.addLink(switch, host_8, bw=1, delay='25ms')
    net.addLink(switch, host_9, bw=1, delay='25ms')
    net.addLink(switch, host_10, bw=1, delay='25ms')
    net.addLink(switch, server_1, bw=4, delay='10ms')
    net.addLink(switch, server_2, bw=4, delay='20ms')
    net.addLink(switch, server_3, bw=4, delay='50ms')
    net.addLink(switch, server_4, bw=4, delay='30ms')

    net.start()

    hosts = net.hosts[:10]
    servers = net.hosts[10:]

    os.system("ovs-vsctl -- --id=@sflow create sflow agent=lo target=\"127.0.0.1\" sampling=16 polling=10 -- set bridge s1 sflow=@sflow")
    collector = os.environ.get('COLLECTOR', '127.0.0.1')
    (ifname, agent) = getIfInfo(collector)
    sendTopology(net, agent, collector)
    
    for server in servers:
        server.sendCmd('python -m SimpleHTTPServer 80 >/dev/null 2>&1&')
        server.waitOutput()
        server.sendCmd('python -m SimpleHTTPServer 5000 >/dev/null 2>&1&')
        server.waitOutput()
        server.sendCmd('tcpdump -i {}-eth0 -n -e -w {}.pcap &'.format(server.name, server.name))
        server.waitOutput()
        #server.sendCmd('nc -lk 5000 > /dev/null 2>&1&')
        #server.waitOutput()
    for host in hosts:
        #host.sendCmd('iperf -s -p5000 -i1 > /dev/null 2>&1 &')
        #host.waitOutput()
        host.sendCmd('tcpdump -i {}-eth0 -n -e -w {}.pcap &'.format(host.name, host.name))
        host.waitOutput()

    print("*** TEST START ***")
    time.sleep(0.1)
    '''print("*** OPENLOAD START ***")
    
    for host in hosts[:3]:
        host.sendCmd("openload -f {}_openload.csv 10.0.0.100:80 >> /dev/null 2>&1 &".format(host.name))
        host.waitOutput()
    
    print("*** file transfer START ***")
    for host in hosts[4:]:
        #host.sendCmd("while true; do curl 10.0.0.100:5000/file_{}MB --output /dev/null --connect-timeout 2 --max-time 15 >> {}_curl.log 2>&1; done &".format(
            #random.choice(['1','3','5','7','9']), host.name))
        host.sendCmd("while true; do wget 10.0.0.100:5000/file_{}MB -O /dev/null --timeout=0.2 --tries=1 --wait=0.1 >>/dev/null 2>&1; done &".format(random.choice(['1','3','5','7','9'])))
        #host.sendCmd("while true; do nc -N 10.0.0.100 5000 < file_{}MB > /dev/null 2>&1; done &".format(random.choice(['1','3','5','7','9'])))
        host.waitOutput()
    '''        
    '''for server in servers:
        server.sendCmd("while true; do iperf -c 10.0.0.$(( $RANDOM % 7 + 4)) -p5000 -t$(( $RANDOM % 8 + 6)) >> /dev/null 2>&1; done &")
        server.waitOutput()
        time.sleep(0.2)
        server.sendCmd("while true; do iperf -c 10.0.0.$(( $RANDOM % 7 + 4)) -p5000 -t$(( $RANDOM % 8 + 6)) >> /dev/null 2>&1; done &")
        server.waitOutput()
        time.sleep(0.2)
        server.sendCmd("while true; do iperf -c 10.0.0.$(( $RANDOM % 7 + 4)) -p5000 -t$(( $RANDOM % 8 + 6)) >> /dev/null 2>&1; done &")
        server.waitOutput()
        time.sleep(0.2)'''

    CLI(net)
    #time.sleep(200)
    #print("*** TEST STOP ***")
    net.stop()
    
    print("*** CSV TO XLSX CONVERTION ***")
    wb = Workbook()
    for filename in fnmatch.filter(os.listdir('.'), '*.csv'):
        ws = wb.create_sheet(filename)
        wb.active = ws
        with open(filename, 'r') as f:
            for row in csv.reader(f):
                ws.append(row)

    wb.save('results_{}_{}.xlsx'.format(sys.argv[1],sys.argv[2]))
    
    print("*** DONE ***")
    #CLI(net)

if __name__ == '__main__':
    main()

