import os
import re
import stat

from subprocess import (
    check_call,
    check_output,
    CalledProcessError,
    Popen,
    PIPE,
)


def is_block_device(path):
    '''
    Confirm device at path is a valid block device node.

    :returns: boolean: True if path is a block device, False if not.
    '''
    return stat.S_ISBLK(os.stat(path).st_mode)


def zap_disk(block_device):
    '''
    Clear a block device of partition table. Relies on sgdisk, which is
    installed as pat of the 'gdisk' package in Ubuntu.

    :param block_device: str: Full path of block device to clean.
    '''
    check_call(['sgdisk', '--zap-all', block_device])


##################################################
# loopback device helpers.
##################################################
def loopback_devices():
    '''
    Parse through 'losetup -a' output to determine currently mapped
    loopback devices. Output is expected to look like:

        /dev/loop0: [0807]:961814 (/tmp/my.img)

    :returns: dict: a dict mapping {loopback_dev: backing_file}
    '''
    loopbacks = {}
    cmd = ['losetup', '-a']
    devs = [d.strip().split(' ') for d in
            check_output(cmd).splitlines() if d != '']
    for dev, _, f in devs:
        loopbacks[dev.replace(':', '')] = re.search('\((\S+)\)', f).groups()[0]
    return loopbacks

def create_loopback(file_path):
    '''
    Create a loopback device for a given backing file.

    :returns: str: Full path to new loopback device (eg, /dev/loop0)
    '''
    cmd = ['losetup', '--find', file_path]
    return check_output(cmd).strip()

def ensure_loopback_device(path, size):
    '''
    Ensure a loopback device exists for a given backing file path and size.
    If it a loopback device is not mapped to file, a new one will be created.

    TODO: Confirm size of found loopback device.

    :returns: str: Full path to the ensured loopback device (eg, /dev/loop0)
    '''
    for d, f in loopback_devices().iteritems():
        if f == path:
            return d

    if not os.path.exists(path):
        cmd = ['truncate', '--size', size, path]
        check_call(cmd)

    return create_loopback(path)



##################################################
# LVM helpers.
##################################################
def deactivate_lvm_volume_group(block_device):
    '''
    Deactivate any volume gruop associated with an LVM physical volume.

    :param block_device: str: Full path to LVM physical volume
    '''
    vg = list_lvm_volume_group(block_device)
    if vg:
        cmd = ['vgchange', '-an', vg]
        check_call(cmd)


def is_lvm_physical_volume(block_device):
    '''
    Determine whether a block device is initialized as an LVM PV.

    :param block_device: str: Full path of block device to inspect.

    :returns: boolean: True if block device is a PV, False if not.
    '''
    try:
        check_output(['pvdisplay', block_device])
        return True
    except CalledProcessError:
        return False


def remove_lvm_physical_volume(block_device):
    '''
    Remove LVM PV signatures from a given block device.

    :param block_device: str: Full path of block device to scrub.
    '''
    p = Popen(['pvremove', '-ff', block_device],
                         stdin=PIPE)
    p.communicate(input='y\n')


def list_lvm_volume_group(block_device):
    '''
    List LVM volume group associated with a given block device.

    Assumes block device is a valid LVM PV.

    :param block_device: str: Full path of block device to inspect.

    :returns: str: Name of volume group associated with block device or None
    '''
    vg = None
    pvd = check_output(['pvdisplay', block_device]).splitlines()
    for l in pvd:
        if l.strip().startswith('VG Name'):
            vg = ' '.join(l.split()).split(' ').pop()
    return vg


def create_lvm_physical_volume(block_device):
    '''
    Initialize a block device as an LVM physical volume.

    :param block_device: str: Full path of block device to initialize.

    '''
    check_call(['pvcreate', block_device])


def create_lvm_volume_group(volume_group, block_device):
    '''
    Create an LVM volume group backed by a given block device.

    Assumes block device has already been initialized as an LVM PV.

    :param volume_group: str: Name of volume group to create.
    :block_device: str: Full path of PV-initialized block device.
    '''
    check_call(['vgcreate', volume_group, block_device])


