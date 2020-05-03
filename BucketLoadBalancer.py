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
    virtual_ip = "10.0.0.10"  # The virtual server IP
    # Hosts 5 and 6 are servers.
    H5_mac = "00:00:00:00:00:05"          # Host 5's mac
    H5_ip = "10.0.0.5"                    # Host 5's IP
    H6_mac = "00:00:00:00:00:06"          # Host 6's mac
    H6_ip = "10.0.0.6"                    # Host 6's IP
    group_table_id = 50
    rt = 'http://127.0.0.1:8008'
    current_server = ""  # Stores the current server's IP
    ip_to_port = {"10.0.0.1": 1,
                  "10.0.0.2": 2,
                  "10.0.0.3": 3,
                  "10.0.0.4": 4,
                  "10.0.0.5": 5,
                  "10.0.0.6": 6}
    ip_to_mac = {"10.0.0.1": "00:00:00:00:00:01",
                 "10.0.0.2": "00:00:00:00:00:02",
                 "10.0.0.3": "00:00:00:00:00:03",
                 "10.0.0.4": "00:00:00:00:00:04",
                 "10.0.0.5": "00:00:00:00:00:05",
                 "10.0.0.6": "00:00:00:00:00:06"}
    port_to_mac = {1: "00:00:00:00:00:01",
                   2: "00:00:00:00:00:02",
                   3: "00:00:00:00:00:03",
                   4: "00:00:00:00:00:04",
                   5: "00:00:00:00:00:05",
                   6: "00:00:00:00:00:06"}
    port_to_ip = { 1: "10.0.0.1",
                   2: "10.0.0.2",
                   3: "10.0.0.3",
                   4: "10.0.0.4",
                   5: "10.0.0.5",
                   6: "10.0.0.6"}

    def __init__(self, *args, **kwargs):
        super(SimpleLoadBalancer, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.current_server = self.H5_ip
        self.SendElephantFlowMonitor()
        self.monitor_thread = hub.spawn(self.ElephantFlowMonitor)
        self.logger.info("--------------------------------------------------------------")
        self.logger.info("%s: STARTUP", datetime.datetime.now().strftime('%H:%M:%S.%f'))
        self.logger.info("--------------------------------------------------------------")

    def SendElephantFlowMonitor(self):
        flowUdp = {'keys': 'link:outputifindex,ipsource,ipdestination,ipprotocol,udpsourceport,udpdestinationport',
                   'value': 'bytes'}
        # flowTcp = {'keys':'link:inputifindex,ipsource,ipdestination,ipprotocol,tcpsourceport,tcpdestinationport','value':'bytes'}
        requests.put(self.rt + '/flow/pair/json', data=json.dumps(flowUdp))
        # requests.put(self.rt+'/flow/pair/json',data=json.dumps(flowTcp))

        threshold = {'metric': 'pair', 'value': 1, 'byFlow': True, 'timeout': 1}
        requests.put(self.rt + '/threshold/elephant/json', data=json.dumps(threshold))


    def ElephantFlowMonitor(self):
        eventurl = self.rt + '/events/json?thresholdID=elephant&maxEvents=10&timeout=60'
        eventID = -1
        while True:
            try:
                r = requests.get(eventurl + "&eventID=" + str(eventID), timeout=0.005)
            except:
                hub.sleep(0.5)
                continue
            if r.status_code != 200: break
            events = r.json()
            if len(events) == 0:
                continue

            eventID = events[0]["eventID"]
            events.reverse()
            for e in events:
                print("{}: Elephant flow detected {}".format(datetime.datetime.now().strftime('%H:%M:%S.%f'), e['flowKey']))

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
        for host in range(1, 5):
            match = parser.OFPMatch(
                in_port=host,
                eth_type=ether_types.ETH_TYPE_IP)
            actions = [parser.OFPActionGroup(group_id=self.group_table_id)]
            self.add_flow(datapath, 10, match, actions)

            for server in range(5,7):
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
            self.logger.info("%s: Got Packet In: %s from: %s", datetime.datetime.now().strftime('%H:%M:%S.%f'),
                             "ETH_TYPE_ARP", pkt.get_protocol(arp.arp).src_ip)
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
        if dstIp != self.H5_ip and dstIp != self.H6_ip:
            srcMac = self.ip_to_mac[self.current_server]
            self.logger.info("%s: Sending ARP reply to HOST", datetime.datetime.now().strftime('%H:%M:%S.%f'))
        else:
            srcMac = self.ip_to_mac[srcIp]
            self.logger.info("%s: Sending ARP reply to SERVER", datetime.datetime.now().strftime('%H:%M:%S.%f'))

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
            #in_port=in_port,
            match=match,
            actions=actions,
            data=p.data
        )
        datapath.send_msg(out)  # Send out ARP reply
        self.logger.info("%s: ARP reply send", datetime.datetime.now().strftime('%H:%M:%S.%f'))

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

        #LB_WEIGHT1 = 50  # percentage
        #LB_WEIGHT2 = 50  # percentage

        #watch_port = 0
        #watch_port = ofproto_v1_5.OFPP_ANY
        #watch_group = 0
        #watch_group = ofproto_v1_5.OFPQ_ALL

        actions1 = [parser.OFPActionSetField(ipv4_dst=self.H5_ip),
                    parser.OFPActionSetField(eth_dst=self.H5_mac),
                    parser.OFPActionOutput(self.ip_to_port[self.H5_ip])]
        actions2 = [parser.OFPActionSetField(ipv4_dst=self.H6_ip),
                    parser.OFPActionSetField(eth_dst=self.H6_mac),
                    parser.OFPActionOutput(self.ip_to_port[self.H6_ip])]
        
        command_bucket_id=ofproto.OFPG_BUCKET_ALL
        
        #buckets = [parser.OFPBucket(LB_WEIGHT1, watch_port, watch_group, actions1),
        #           parser.OFPBucket(LB_WEIGHT2, watch_port, watch_group, actions2)]
        buckets = [parser.OFPBucket(bucket_id=self.group_table_id, actions=actions1, properties=None),
                   parser.OFPBucket(bucket_id=self.group_table_id+1, actions=actions2, properties=None)]

        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                 ofproto.OFPGT_SELECT, self.group_table_id, command_bucket_id, buckets)
        datapath.send_msg(req)

