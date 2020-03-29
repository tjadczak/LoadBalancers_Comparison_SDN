from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet.packet import Packet
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import tcp, udp, icmp
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from operator import attrgetter
from ryu.lib import hub
import datetime

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
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    virtual_ip = "10.0.0.10"  # The virtual server IP
    # Hosts 5 and 6 are servers.
    H5_mac = "00:00:00:00:00:05"          # Host 5's mac
    H5_ip = "10.0.0.5"                    # Host 5's IP
    H6_mac = "00:00:00:00:00:06"          # Host 6's mac
    H6_ip = "10.0.0.6"                    # Host 6's IP
    next_server = ""  # Stores the IP of the  next server to use in round robin manner
    current_server = ""  # Stores the current server's IP
    ip_to_port = {H5_ip: 5, H6_ip: 6}
    ip_to_mac = {"10.0.0.1": "00:00:00:00:00:01",
                 "10.0.0.2": "00:00:00:00:00:02",
                 "10.0.0.3": "00:00:00:00:00:03",
                 "10.0.0.4": "00:00:00:00:00:04"}

    def __init__(self, *args, **kwargs):
        super(SimpleLoadBalancer, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)
        self.time_interval = 1
        self.mac_to_port = {}
        self.next_server = self.H5_ip
        self.current_server = self.H5_ip

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            self.logger.info("---------------------------------------------------")
            self.logger.info(datetime.datetime.now().strftime("%H:%M:%S"))
            self.logger.info("---------------------------------------------------")
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(self.time_interval)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        self.logger.info('        datapath ' ' in-port ' 'packets    bytes')
        self.logger.info('---------------- ' '-------- ' '--------- --------')
        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match['in_port'])):
            self.logger.info('%016x %8x %8d %8d',
                             ev.msg.datapath.id,
                             stat.match['in_port'],
                             stat.packet_count, stat.byte_count)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        self.logger.info('datapath         port     '
                         'rx-pkts  rx-bytes rx-error '
                         'tx-pkts  tx-bytes tx-error')
        self.logger.info('---------------- -------- '
                         '-------- -------- -------- '
                         '-------- -------- --------')
        for stat in sorted(body, key=attrgetter('port_no')):
            self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
                             ev.msg.datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                             stat.tx_packets, stat.tx_bytes, stat.tx_errors)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        mod = parser.OFPFlowMod(datapath=datapath, priority=0,
                                match=match, instructions=inst)
        datapath.send_msg(mod)


    '''@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.error("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
            return

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # get Datapath ID to identify OpenFlow switches.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # analyse the received packets using the packet library.
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src

        # get the received port number from packet_in message.
        in_port = msg.match['in_port']
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        # if the destination mac address is already learned,
        # decide which port to output the packet, otherwise FLOOD.
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # construct action list.
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time.
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)

        # construct packet_out message and send it.
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=in_port,
                                  actions=actions,
                                  data=msg.data)
        datapath.send_msg(out)'''

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        etherFrame = pkt.get_protocol(ethernet.ethernet)

        print(etherFrame)

        # If the packet is an ARP packet, create new flow table
        # entries and send an ARP response.
        if etherFrame.ethertype == ether_types.ETH_TYPE_ARP:
            self.add_flow(dp, pkt, ofp_parser, ofp, in_port)
            self.arp_response(dp, pkt, etherFrame, ofp_parser, ofp, in_port)
            self.current_server = self.next_server
            return
        else:
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
            if self.next_server == self.H5_ip:
                srcMac = self.H5_mac
                self.next_server = self.H6_ip
            else:
                srcMac = self.H6_mac
                self.next_server = self.H5_ip
        else:
            srcMac = self.ip_to_mac[srcIp]

        e = ethernet.ethernet(dstMac, srcMac, ether_types.ETH_TYPE_ARP)
        a = arp.arp(1, 0x0800, 6, 4, 2, srcMac, srcIp, dstMac, dstIp)
        p = Packet()
        p.add_protocol(e)
        p.add_protocol(a)
        p.serialize()

        # ARP action list
        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_IN_PORT)]
        # ARP output message
        out = ofp_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofp.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=p.data
        )
        datapath.send_msg(out)  # Send out ARP reply

    def create_match(self, ofp_parser, in_port, ipv4_dst, eth_type,
                     ipv4_src=None, ip_proto=None, tcp_src=None, tcp_dst=None):
        if tcp_src:
            match = ofp_parser.OFPMatch(in_port=in_port,
                                        ipv4_dst=ipv4_dst,
                                        eth_type=eth_type,
                                        ip_proto=ip_proto,
                                        tcp_src=tcp_src)
        elif tcp_dst:
            match = ofp_parser.OFPMatch(in_port=in_port,
                                        ipv4_dst=ipv4_dst,
                                        ipv4_src=ipv4_src,
                                        eth_type=eth_type,
                                        ip_proto=ip_proto,
                                        tcp_dst=tcp_dst)
        else:
            match = ofp_parser.OFPMatch(in_port=in_port,
                                        ipv4_dst=ipv4_dst,
                                        eth_type=eth_type,)

        return match

    # Sets up the flow table in the switch to map IP addresses correctly.
    def add_flow(self, datapath, packet, ofp_parser, ofp, in_port):
        srcIp = packet.get_protocol(arp.arp).src_ip

        # Don't push forwarding rules if an ARP request is received from a server.
        if srcIp == self.H5_ip or srcIp == self.H6_ip:
            return

        srcTcp = None
        dstTcp = None
        ipProto = None
        if packet.get_protocol(tcp.tcp):
            srcTcp = packet.get_protocol(tcp.tcp).src_port
            dstTcp = packet.get_protocol(tcp.tcp).src_port
            ipProto = 0x06
            print(srcTcp)

        # Generate flow from host to server.
        '''match = ofp_parser.OFPMatch(in_port=in_port,
                                    ipv4_dst=self.virtual_ip,
                                    eth_type=0x0800,
                                    ip_proto=0x06,
                                    tcp_src=srcTcp)'''
        match = self.create_match(ofp_parser, in_port, self.virtual_ip, 0x0800, ip_proto=ipProto, tcp_src=srcTcp)
        actions = [ofp_parser.OFPActionSetField(ipv4_dst=self.current_server),
                   ofp_parser.OFPActionOutput(self.ip_to_port[self.current_server])]
        inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]

        mod = ofp_parser.OFPFlowMod(
            datapath=datapath,
            priority=1,
            match=match,
            instructions=inst)

        datapath.send_msg(mod)

        # Generate reverse flow from server to host.
        '''match = ofp_parser.OFPMatch(in_port=self.ip_to_port[self.current_server],
                                    ipv4_src=self.current_server,
                                    ipv4_dst=srcIp,
                                    eth_type=0x0800,
                                    ip_proto=0x06,
                                    tcp_dst=srcTcp)'''

        match = self.create_match(ofp_parser, self.ip_to_port[self.current_server], srcIp, 0x0800,
                                  ipv4_src=self.current_server, ip_proto=ipProto, tcp_dst=dstTcp)
        actions = [ofp_parser.OFPActionSetField(ipv4_src=self.virtual_ip),
                   ofp_parser.OFPActionOutput(in_port)]
        inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]

        mod = ofp_parser.OFPFlowMod(
            datapath=datapath,
            priority=1,
            match=match,
            instructions=inst)

        datapath.send_msg(mod)
