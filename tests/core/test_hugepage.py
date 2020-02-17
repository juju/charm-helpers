from testtools import TestCase
from mock import patch
from charmhelpers.core import hugepage
import yaml

TO_PATCH = [
    'fstab',
    'add_group',
    'add_user_to_group',
    'sysctl',
    'fstab_mount',
    'mkdir',
    'check_output',
]


class Group(object):
    def __init__(self):
        self.gr_gid = '1010'


class HugepageTests(TestCase):

    def setUp(self):
        super(HugepageTests, self).setUp()
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))

    def _patch(self, method):
        _m = patch('charmhelpers.core.hugepage.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_hugepage_support(self):
        self.add_group.return_value = Group()
        self.fstab.Fstab().get_entry_by_attr.return_value = 'old fstab entry'
        self.fstab.Fstab().Entry.return_value = 'new fstab entry'
        hugepage.hugepage_support('nova')
        sysctl_expect = ("""
vm.hugetlb_shm_group: '1010'
vm.max_map_count: 65536
vm.nr_hugepages: 256
""".lstrip())
        self.sysctl.create.assert_called_with(sysctl_expect,
                                              '/etc/sysctl.d/10-hugepage.conf')
        self.mkdir.assert_called_with('/run/hugepages/kvm', owner='root',
                                      group='root', perms=0o755, force=False)
        self.fstab.Fstab().remove_entry.assert_called_with('old fstab entry')
        self.fstab.Fstab().Entry.assert_called_with(
            'nodev', '/run/hugepages/kvm', 'hugetlbfs',
            'mode=1770,gid=1010,pagesize=2MB', 0, 0)
        self.fstab.Fstab().add_entry.assert_called_with('new fstab entry')
        self.fstab_mount.assert_called_with('/run/hugepages/kvm')

    def test_hugepage_support_new_mnt(self):
        self.add_group.return_value = Group()
        self.fstab.Fstab().get_entry_by_attr.return_value = None
        self.fstab.Fstab().Entry.return_value = 'new fstab entry'
        hugepage.hugepage_support('nova')
        self.assertEqual(self.fstab.Fstab().remove_entry.call_args_list, [])

    def test_hugepage_support_no_automount(self):
        self.add_group.return_value = Group()
        self.fstab.Fstab().get_entry_by_attr.return_value = None
        self.fstab.Fstab().Entry.return_value = 'new fstab entry'
        hugepage.hugepage_support('nova', mount=False)
        self.assertEqual(self.fstab_mount.call_args_list, [])

    def test_hugepage_support_nodefaults(self):
        self.add_group.return_value = Group()
        self.fstab.Fstab().get_entry_by_attr.return_value = 'old fstab entry'
        self.fstab.Fstab().Entry.return_value = 'new fstab entry'
        hugepage.hugepage_support(
            'nova', group='neutron', nr_hugepages=512, max_map_count=70000,
            mnt_point='/hugepages', pagesize='1G', mount=False)
        sysctl_expect = {
            'vm.hugetlb_shm_group': '1010',
            'vm.max_map_count': 70000,
            'vm.nr_hugepages': 512,
        }
        sysctl_setting_arg = self.sysctl.create.call_args_list[0][0][0]
        self.assertEqual(yaml.safe_load(sysctl_setting_arg), sysctl_expect)
        self.mkdir.assert_called_with('/hugepages', owner='root',
                                      group='root', perms=0o755, force=False)
        self.fstab.Fstab().remove_entry.assert_called_with('old fstab entry')
        self.fstab.Fstab().Entry.assert_called_with(
            'nodev', '/hugepages', 'hugetlbfs',
            'mode=1770,gid=1010,pagesize=1G', 0, 0)
        self.fstab.Fstab().add_entry.assert_called_with('new fstab entry')

    def test_hugepage_support_set_shmmax(self):
        self.add_group.return_value = Group()
        self.fstab.Fstab().get_entry_by_attr.return_value = None
        self.fstab.Fstab().Entry.return_value = 'new fstab entry'
        self.check_output.return_value = 2000
        hugepage.hugepage_support('nova', mount=False, set_shmmax=True)
        sysctl_expect = {
            'kernel.shmmax': 536870912,
            'vm.hugetlb_shm_group': '1010',
            'vm.max_map_count': 65536,
            'vm.nr_hugepages': 256
        }
        sysctl_setting_arg = self.sysctl.create.call_args_list[0][0][0]
        self.assertEqual(yaml.safe_load(sysctl_setting_arg), sysctl_expect)

    def test_hugepage_support_auto_increase_max_map_count(self):
        self.add_group.return_value = Group()
        hugepage.hugepage_support(
            'nova', group='neutron', nr_hugepages=512, max_map_count=200,
            mnt_point='/hugepages', pagesize='1G', mount=False)
        sysctl_expect = {
            'vm.hugetlb_shm_group': '1010',
            'vm.max_map_count': 1024,
            'vm.nr_hugepages': 512,
        }
        sysctl_setting_arg = self.sysctl.create.call_args_list[0][0][0]
        self.assertEqual(yaml.safe_load(sysctl_setting_arg), sysctl_expect)
