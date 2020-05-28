from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet.packet import Packet
from ryu.ofproto import ofproto_v1_3, ofproto_v1_5
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import tcp, udp, icmp
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from operator import attrgetter
from ryu.lib import hub
import datetime
import requests
import json
import re
import random


""" 
    TOPOLOGY:
            h1 --- *            * --- h5 (server)
                   |            |
            h2 --- * --- s1 --- * --- h6 (server)
                   |              
            h3 --- *            
                   |
            h4 --- *
"""

class SimpleLoadBalancer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_5.OFP_VERSION]
    virtual_ip = "10.0.0.100"  # The virtual server IP
    # Hosts 5 and 6 are servers.
    H11_mac = "00:00:00:00:00:0B"          # Host 5's mac
    H11_ip = "10.0.0.11"                    # Host 5's IP
    H12_mac = "00:00:00:00:00:0C"          # Host 6's mac
    H12_ip = "10.0.0.12"                    # Host 6's IP
    H13_mac = "00:00:00:00:00:0D"  # Host 6's mac
    H13_ip = "10.0.0.13"  # Host 6's IP
    group_table_id = 50
    rt = 'http://127.0.0.1:8008'
    ip_to_port = {"10.0.0.1": 1,
                  "10.0.0.2": 2,
                  "10.0.0.3": 3,
                  "10.0.0.4": 4,
                  "10.0.0.5": 5,
                  "10.0.0.6": 6,
                  "10.0.0.7": 7,
                  "10.0.0.8": 8,
                  "10.0.0.9": 9,
                  "10.0.0.10": 10,
                  "10.0.0.11": 11,
                  "10.0.0.12": 12,
                  "10.0.0.13": 13}
    ip_to_mac = {"10.0.0.1": "00:00:00:00:00:01",
                 "10.0.0.2": "00:00:00:00:00:02",
                 "10.0.0.3": "00:00:00:00:00:03",
                 "10.0.0.4": "00:00:00:00:00:04",
                 "10.0.0.5": "00:00:00:00:00:05",
                 "10.0.0.6": "00:00:00:00:00:06",
                 "10.0.0.7": "00:00:00:00:00:07",
                 "10.0.0.8": "00:00:00:00:00:08",
                 "10.0.0.9": "00:00:00:00:00:09",
                 "10.0.0.10": "00:00:00:00:00:0A",
                 "10.0.0.11": "00:00:00:00:00:0B",
                 "10.0.0.12": "00:00:00:00:00:0C",
                 "10.0.0.13": "00:00:00:00:00:0D"}
    port_to_mac = {1: "00:00:00:00:00:01",
                   2: "00:00:00:00:00:02",
                   3: "00:00:00:00:00:03",
                   4: "00:00:00:00:00:04",
                   5: "00:00:00:00:00:05",
                   6: "00:00:00:00:00:06",
                   7: "00:00:00:00:00:07",
                   8: "00:00:00:00:00:08",
                   9: "00:00:00:00:00:09",
                   10: "00:00:00:00:00:0A",
                   11: "00:00:00:00:00:0B",
                   12: "00:00:00:00:00:0C",
                   13: "00:00:00:00:00:0D"}
    port_to_ip = { 1: "10.0.0.1",
                   2: "10.0.0.2",
                   3: "10.0.0.3",
                   4: "10.0.0.4",
                   5: "10.0.0.5",
                   6: "10.0.0.6",
                   7: "10.0.0.7",
                   8: "10.0.0.8",
                   9: "10.0.0.9",
                   10: "10.0.0.10",
                   11: "10.0.0.11",
                   12: "10.0.0.12",
                   13: "10.0.0.13"}
    loadBalancingAlgorithm = "random" # 'random' / 'roundRobin' / 'leastBandwidth' / 'none'

    def __init__(self, *args, **kwargs):
        super(SimpleLoadBalancer, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.elephant_flows = {}
        self.SendElephantFlowMonitor()
        if self.loadBalancingAlgorithm != 'none':
            self.monitor_thread = hub.spawn(self.ElephantFlowMonitor)
        self.logger.info("--------------------------------------------------------------")
        self.logger.info("%s: STARTUP", datetime.datetime.now().strftime('%H:%M:%S.%f'))
        self.logger.info("%s: Selected Load Balancing algorithm: %s", datetime.datetime.now().strftime('%H:%M:%S.%f'), self.loadBalancingAlgorithm)
        self.logger.info("--------------------------------------------------------------")

    def SendElephantFlowMonitor(self):
        flowTcp = {'keys':'link:inputifindex,ipsource,ipdestination,ipprotocol,tcpsourceport,tcpdestinationport','value':'bytes'}
        requests.put(self.rt+'/flow/pair/json',data=json.dumps(flowTcp))

        threshold = {'metric': 'pair', 'value': 1000000/8, 'byFlow': True, 'timeout': 1}
        requests.put(self.rt + '/threshold/elephant/json', data=json.dumps(threshold))


    def ElephantFlowMonitor(self):
        eventurl = self.rt + '/events/json?thresholdID=elephant&maxEvents=10&timeout=60'
        eventID = -1
        while True:
            try:
                r = requests.get(eventurl + "&eventID=" + str(eventID), timeout=0.01)
            except:
                hub.sleep(1)
                continue
            if r.status_code != 200: break
            events = r.json()
            if len(events) == 0:
                continue

            eventID = events[0]["eventID"]
            events.reverse()
            for e in events:
                try:
                    datapath = self.datapaths[1]
                except:
                    continue
                priority = 20

                [server_ip, host_ip] = re.findall('10\.0\.0\.[0-9]', str(e['flowKey']))
                if host_ip in self.elephant_flows.keys():
                    continue
                else:
                    self.logger.info("{}: Elephant flow ( 1Mbps ) detected {}".format(
                        datetime.datetime.now().strftime('%H:%M:%S.%f'), e['flowKey']))
                    self.elephant_flows[host_ip] = 1

                # server_ip = H11_ip
                server_ip = getServerIp(self.loadBalancingAlgorithm)

                self.logger.info("{}: Elephant flow redirecting to: {}".format(
                    datetime.datetime.now().strftime('%H:%M:%S.%f'), server_ip))

                in_port = self.ip_to_port[server_ip]
                eth_type = ether_types.ETH_TYPE_IP
                ip_proto = 0x06
                tcp_port = 80
                parser = datapath.ofproto_parser

                # Elephant flow ( 1Mbps ) detected s1-h5,10.0.0.5,10.0.0.2,6,80,44714
                # Flow from server to host
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=eth_type,
                    ipv4_src=server_ip,
                    ipv4_dst=host_ip,
                    ip_proto=ip_proto,
                    tcp_src=tcp_port)
                actions = [parser.OFPActionSetField(ipv4_src=self.virtual_ip),
                           parser.OFPActionOutput(self.ip_to_port[host_ip])]
                self.add_flow(datapath, priority, match, actions)

                # Reverse flow host to server
                in_port = self.ip_to_port[host_ip]
                match1 = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=eth_type,
                    eth_dst=self.ip_to_mac[self.H11_ip],
                    ipv4_src=host_ip,
                    ipv4_dst=self.virtual_ip,
                    ip_proto=ip_proto,
                    tcp_dst=tcp_port)
                match2 = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=eth_type,
                    eth_dst=self.ip_to_mac[self.H12_ip],
                    ipv4_src=host_ip,
                    ipv4_dst=self.virtual_ip,
                    ip_proto=ip_proto,
                    tcp_dst=tcp_port)
                match3 = parser.OFPMatch(
                    in_port=in_port,
                    eth_type=eth_type,
                    eth_dst=self.ip_to_mac[self.H13_ip],
                    ipv4_src=host_ip,
                    ipv4_dst=self.virtual_ip,
                    ip_proto=ip_proto,
                    tcp_dst=tcp_port)
                actions = [parser.OFPActionSetField(ipv4_dst=server_ip),
                           parser.OFPActionSetField(eth_dst=self.ip_to_mac[server_ip]),
                           parser.OFPActionOutput(self.ip_to_port[server_ip])]
                self.add_flow(datapath, priority, match1, actions)
                self.add_flow(datapath, priority, match2, actions)
                self.add_flow(datapath, priority, match3, actions)

                self.logger.info("{}: Instaled new flows for elephant flow".format(
                    datetime.datetime.now().strftime('%H:%M:%S.%f')))


    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info("%s: Register datapath: %s", datetime.datetime.now().strftime('%H:%M:%S.%f'),
                                 datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info("%s: Unregister datapath: %s", datetime.datetime.now().strftime('%H:%M:%S.%f'),
                                 datapath.id)
                del self.datapaths[datapath.id]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        self.send_group_mod(datapath)
        for host in range(1, 11):
            match = parser.OFPMatch(
                in_port=host,
                eth_type=ether_types.ETH_TYPE_IP)
            actions = [parser.OFPActionGroup(group_id=self.group_table_id)]
            self.add_flow(datapath, 10, match, actions)

            for server in range(11,14):
                match = parser.OFPMatch(
                    in_port=server,
                    eth_type=ether_types.ETH_TYPE_IP,
                    eth_dst=self.port_to_mac[host],
                    ipv4_src=self.port_to_ip[server])
                actions = [parser.OFPActionSetField(ipv4_src=self.virtual_ip),
                           parser.OFPActionOutput(host)]
                self.add_flow(datapath, 10, match, actions)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        etherFrame = pkt.get_protocol(ethernet.ethernet)

        # If the packet is an ARP packet, create new flow table
        # entries and send an ARP response.
        if etherFrame.ethertype == ether_types.ETH_TYPE_ARP:
            self.arp_response(dp, pkt, etherFrame, ofp_parser, ofp, in_port)
            return
        else:
            self.logger.warning("Got Packet In which is not ARP!")
            self.logger.info("%s: Got Packet In: %s", datetime.datetime.now().strftime('%H:%M:%S.%f'),
                             etherFrame.ethertype)
            return

    # Sends an ARP response to the contacting host with the
    # real MAC address of a server.
    def arp_response(self, datapath, packet, etherFrame, ofp_parser, ofp, in_port):
        arpPacket = packet.get_protocol(arp.arp)
        dstIp = arpPacket.src_ip
        srcIp = arpPacket.dst_ip
        dstMac = etherFrame.src

        # If the ARP request isn't from one of the two servers,
        # choose the target/source MAC address from one of the servers;
        # else the target MAC address is set to the one corresponding
        # to the target host's IP.
        if dstIp != self.H11_ip and dstIp != self.H12_ip and dstIp != self.H13_ip:
            srcMac = self.ip_to_mac[self.H11_ip]
            #self.logger.info("%s: Sending ARP reply to HOST", datetime.datetime.now().strftime('%H:%M:%S.%f'))
        else:
            srcMac = self.ip_to_mac[srcIp]
            #self.logger.info("%s: Sending ARP reply to SERVER", datetime.datetime.now().strftime('%H:%M:%S.%f'))

        e = ethernet.ethernet(dstMac, srcMac, ether_types.ETH_TYPE_ARP)
        a = arp.arp(1, 0x0800, 6, 4, 2, srcMac, srcIp, dstMac, dstIp)
        p = Packet()
        p.add_protocol(e)
        p.add_protocol(a)
        p.serialize()

        # ARP action list
        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_IN_PORT)]
        match = ofp_parser.OFPMatch(in_port=in_port)
        # ARP output message
        out = ofp_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofp.OFP_NO_BUFFER,
            match=match,
            actions=actions,
            data=p.data
        )
        datapath.send_msg(out)  # Send out ARP reply
        #self.logger.info("%s: ARP reply send", datetime.datetime.now().strftime('%H:%M:%S.%f'))

    # Sets up the flow table in the switch to map IP addresses correctly.
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def send_group_mod(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        actions1 = [parser.OFPActionSetField(ipv4_dst=self.H11_ip),
                    parser.OFPActionSetField(eth_dst=self.H11_mac),
                    parser.OFPActionOutput(self.ip_to_port[self.H11_ip])]
        actions2 = [parser.OFPActionSetField(ipv4_dst=self.H12_ip),
                    parser.OFPActionSetField(eth_dst=self.H12_mac),
                    parser.OFPActionOutput(self.ip_to_port[self.H12_ip])]
        actions3 = [parser.OFPActionSetField(ipv4_dst=self.H13_ip),
                    parser.OFPActionSetField(eth_dst=self.H13_mac),
                    parser.OFPActionOutput(self.ip_to_port[self.H13_ip])]

        command_bucket_id=ofproto.OFPG_BUCKET_ALL
        
        buckets = [parser.OFPBucket(bucket_id=1, actions=actions1, properties=None),
                   parser.OFPBucket(bucket_id=2, actions=actions2, properties=None),
                   parser.OFPBucket(bucket_id=3, actions=actions3, properties=None)]

        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                 ofproto.OFPGT_SELECT, self.group_table_id, command_bucket_id, buckets)
        datapath.send_msg(req)


previousServer = "10.0.0.13"
def getServerIp(loadBalancingAlgorithm):
    global previousServer

    if loadBalancingAlgorithm == 'random':
        return random.choice(["10.0.0.11", "10.0.0.12", "10.0.0.13"])

    elif loadBalancingAlgorithm == 'roundRobin':
        if previousServer == "10.0.0.11":
            previousServer = "10.0.0.12"
            return "10.0.0.12"
        elif previousServer == "10.0.0.12":
            previousServer = "10.0.0.13"
            return "10.0.0.13"
        else:
            previousServer = "10.0.0.11"
            return "10.0.0.11"

    elif loadBalancingAlgorithm == 'leastBandwidth':
        #TODO
        return "10.0.0.11"


