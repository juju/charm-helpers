from os import stat
from stat import S_ISBLK

from subprocess import (
    check_call,
    check_output,
    call
)


def is_block_device(path):
    '''
    Confirm device at path is a valid block device node.

    :returns: boolean: True if path is a block device, False if not.
    '''
    return S_ISBLK(stat(path).st_mode)


def zap_disk(block_device):
    '''
    Clear a block device of partition table. Relies on sgdisk, which is
    installed as pat of the 'gdisk' package in Ubuntu.

    :param block_device: str: Full path of block device to clean.
    '''
    # sometimes sgdisk exits non-zero; this is OK, dd will clean up
    call(['sgdisk', '--zap-all', '--mbrtogpt',
          '--clear', block_device])
    dev_end = check_output(['blockdev', '--getsz', block_device])
    gpt_end = int(dev_end.split()[0]) - 100
    check_call(['dd', 'if=/dev/zero', 'of=%s'%(block_device),
                'bs=1M', 'count=1'])
    check_call(['dd', 'if=/dev/zero', 'of=%s'%(block_device),
                'bs=512', 'count=100', 'seek=%s'%(gpt_end)])
