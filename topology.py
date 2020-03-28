from mininet.topo import Topo


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

        server_1.sendCmd("python -m SimpleHTTPServer 80 >& /tmp/http.log &")
        server_2.sendCmd("python -m SimpleHTTPServer 80 >& /tmp/http.log &")


topos = {'mytopo': (lambda: MyTopo())}
