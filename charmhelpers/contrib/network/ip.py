import glob
import sys

from functools import partial

from charmhelpers.fetch import apt_install
from charmhelpers.core.hookenv import (
    WARNING,
    ERROR,
    log
)

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


def _validate_cidr(network):
    try:
        netaddr.IPNetwork(network)
    except (netaddr.core.AddrFormatError, ValueError):
        raise ValueError("Network (%s) is not in CIDR presentation format" %
                         network)


def get_address_in_network(network, fallback=None, fatal=False):
    """
    Get an IPv4 or IPv6 address within the network from the host.

    :param network (str): CIDR presentation format. For example,
        '192.168.1.0/24'.
    :param fallback (str): If no address is found, return fallback.
    :param fatal (boolean): If no address is found, fallback is not
        set and fatal is True then exit(1).

    """

    def not_found_error_out():
        log("No IP address found in network: %s" % network,
            level=ERROR)
        sys.exit(1)

    if network is None:
        if fallback is not None:
            return fallback
        else:
            if fatal:
                not_found_error_out()

    _validate_cidr(network)
    network = netaddr.IPNetwork(network)
    for iface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(iface)
        if network.version == 4 and netifaces.AF_INET in addresses:
            addr = addresses[netifaces.AF_INET][0]['addr']
            netmask = addresses[netifaces.AF_INET][0]['netmask']
            cidr = netaddr.IPNetwork("%s/%s" % (addr, netmask))
            if cidr in network:
                return str(cidr.ip)
        if network.version == 6 and netifaces.AF_INET6 in addresses:
            for addr in addresses[netifaces.AF_INET6]:
                if not addr['addr'].startswith('fe80'):
                    cidr = netaddr.IPNetwork("%s/%s" % (addr['addr'],
                                                        addr['netmask']))
                    if cidr in network:
                        return str(cidr.ip)

    if fallback is not None:
        return fallback

    if fatal:
        not_found_error_out()

    return None


def is_ipv6(address):
    '''Determine whether provided address is IPv6 or not'''
    try:
        address = netaddr.IPAddress(address)
    except netaddr.AddrFormatError:
        # probably a hostname - so not an address at all!
        return False
    else:
        return address.version == 6


def is_address_in_network(network, address):
    """
    Determine whether the provided address is within a network range.

    :param network (str): CIDR presentation format. For example,
        '192.168.1.0/24'.
    :param address: An individual IPv4 or IPv6 address without a net
        mask or subnet prefix. For example, '192.168.1.1'.
    :returns boolean: Flag indicating whether address is in network.
    """
    try:
        network = netaddr.IPNetwork(network)
    except (netaddr.core.AddrFormatError, ValueError):
        raise ValueError("Network (%s) is not in CIDR presentation format" %
                         network)
    try:
        address = netaddr.IPAddress(address)
    except (netaddr.core.AddrFormatError, ValueError):
        raise ValueError("Address (%s) is not in correct presentation format" %
                         address)
    if address in network:
        return True
    else:
        return False


def _get_for_address(address, key):
    """Retrieve an attribute of or the physical interface that
    the IP address provided could be bound to.

    :param address (str): An individual IPv4 or IPv6 address without a net
        mask or subnet prefix. For example, '192.168.1.1'.
    :param key: 'iface' for the physical interface name or an attribute
        of the configured interface, for example 'netmask'.
    :returns str: Requested attribute or None if address is not bindable.
    """
    address = netaddr.IPAddress(address)
    for iface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(iface)
        if address.version == 4 and netifaces.AF_INET in addresses:
            addr = addresses[netifaces.AF_INET][0]['addr']
            netmask = addresses[netifaces.AF_INET][0]['netmask']
            cidr = netaddr.IPNetwork("%s/%s" % (addr, netmask))
            if address in cidr:
                if key == 'iface':
                    return iface
                else:
                    return addresses[netifaces.AF_INET][0][key]
        if address.version == 6 and netifaces.AF_INET6 in addresses:
            for addr in addresses[netifaces.AF_INET6]:
                if not addr['addr'].startswith('fe80'):
                    cidr = netaddr.IPNetwork("%s/%s" % (addr['addr'],
                                                        addr['netmask']))
                    if address in cidr:
                        if key == 'iface':
                            return iface
                        else:
                            return addr[key]
    return None


get_iface_for_address = partial(_get_for_address, key='iface')

get_netmask_for_address = partial(_get_for_address, key='netmask')


def format_ipv6_addr(address):
    """
    IPv6 needs to be wrapped with [] in url link to parse correctly.
    """
    if is_ipv6(address):
        address = "[%s]" % address
    else:
        log("Not a valid ipv6 address: %s" % address, level=WARNING)
        address = None

    return address


def get_iface_addr(iface='eth0', inet_type='AF_INET', inc_aliases=False, fatal=True, exc_list=None):
    """
    Return the assigned IP address for a given interface, if any, or [].
    """
    # Extract nic if passed /dev/ethX
    if '/' in iface:
        iface = iface.split('/')[-1]
    if not exc_list:
        exc_list = []
    try:
        inet_num = getattr(netifaces, inet_type)
    except AttributeError:
        raise Exception('Unknown inet type ' + str(inet_type))

    interfaces = netifaces.interfaces()
    if inc_aliases:
        ifaces = []
        for _iface in interfaces:
            if iface == _iface or _iface.split(':')[0] == iface:
                ifaces.append(_iface)
        if fatal and not ifaces:
            raise Exception("Invalid interface '%s'" % iface)
        ifaces.sort()
    else:
        if iface not in interfaces:
            if fatal:
                raise Exception("%s not found " % (iface))
            else:
                return []
        else:
            ifaces = [iface]

    addresses = []
    for netiface in ifaces:
        net_info = netifaces.ifaddresses(netiface)
        if inet_num in net_info:
            for entry in net_info[inet_num]:
                if 'addr' in entry and entry['addr'] not in exc_list:
                    addresses.append(entry['addr'])
    if fatal and not addresses:
        raise Exception("Interface '%s' doesn't have any %s addresses." % (iface, inet_type))
    return addresses

get_ipv4_addr = partial(get_iface_addr, inet_type='AF_INET')


def select_ipv6_global_dynamic_address(ipv6_addr_list):
    """
    Return global dynamic ipv6 address, which follows EUI-64 standards,
    it's generated from MAC address, so won't change after node reboot,
    by compring link scope ipv6 address, it could be identified, e.g:
      inet6 2001:db8:1:0:f816:3eff:feba:b633/64 scope global dynamic
      inet6 fe80::f816:3eff:feba:b633/64 scope link
    """

    if not ipv6_addr_list:
        raise Exception("No IPv6 addresses are found.")

    scope_link_suffix = []
    for ipv6_addr in ipv6_addr_list:
        if ipv6_addr.startswith('fe80'):
            scope_link_addr = ipv6_addr.split('%')[0]
            scope_link_suffix.append(scope_link_addr.split('::')[1])

    find_global_dynamic_addr = False
    for global_addr in ipv6_addr_list:
        for suffix in scope_link_suffix:
            if not global_addr.startswith('fe80') and \
                    global_addr.endswith(suffix):
                find_global_dynamic_addr = True
                return global_addr

    if not find_global_dynamic_addr:
        raise Exception("No global dynamic ipv6 address found.")


def get_ipv6_addr(iface='eth0', inc_aliases=False, fatal=True, exc_list=None, global_dynamic=True):
    """
    Return the assigned IPv6 address for a given interface, if any, or [].
    Default return global dynamic IPv6 address, if no global dynamic IPv6
    address is found, return the first one get from ipv6 address list.
    """
    addresses = get_iface_addr(iface=iface, inet_type='AF_INET6',
                               inc_aliases=inc_aliases, fatal=fatal,
                               exc_list=exc_list)
    if global_dynamic:
        try:
            g_dynamic_addr = select_ipv6_global_dynamic_address(addresses)
            if g_dynamic_addr:
                return [g_dynamic_addr]
        except Exception:
            log("No global dynamic IPv6 address found.", level=ERROR)

    remotly_addressable = []
    for address in addresses:
        if not address.startswith('fe80'):
            remotly_addressable.append(address)
    if fatal and not remotly_addressable:
        raise Exception("Interface '%s' doesn't have global ipv6 address." % iface)
    return remotly_addressable


def get_bridges(vnic_dir='/sys/devices/virtual/net'):
    """
    Return a list of bridges on the system or []
    """
    b_rgex = vnic_dir + '/*/bridge'
    return [x.replace(vnic_dir, '').split('/')[1] for x in glob.glob(b_rgex)]


def get_bridge_nics(bridge, vnic_dir='/sys/devices/virtual/net'):
    """
    Return a list of nics comprising a given bridge on the system or []
    """
    brif_rgex = "%s/%s/brif/*" % (vnic_dir, bridge)
    return [x.split('/')[-1] for x in glob.glob(brif_rgex)]


def is_bridge_member(nic):
    """
    Check if a given nic is a member of a bridge
    """
    for bridge in get_bridges():
        if nic in get_bridge_nics(bridge):
            return True
    return False
