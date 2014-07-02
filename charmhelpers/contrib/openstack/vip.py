
from charmhelpers.fetch import apt_install


try:
    import netifaces
except ImportError:
    apt_install('python-netifaces')
    import netifaces

try:
    import netaddr
except ImportError:
    apt_install('python-netaddr')
    import netaddr


class VIPConfiguration():
    
    def __init__(self, configuration):
        self.vip = []
        for vip in configuration.split():
            self.vips.append(netaddr.IPAddress(vip))

    def getVIP(self, network):
        ''' Determine the VIP for the provided network        
        :network str: CIDR presented network, e.g. 192.168.1.1/24
        :returns str: IP address of VIP in provided network or None
        '''
        network = netaddr.IPNetwork(network)
        for vip in self.vips:
            if vip in network:
                return str(vip)
        return None

    def getNIC(self, address):
        ''' Determine the physical network interface that an address could be bound to'''

