import sys
import mock


sys.modules['yum'] = mock.MagicMock()
sys.modules['sriov_netplan_shim'] = mock.MagicMock()
sys.modules['sriov_netplan_shim.pci'] = mock.MagicMock()
with mock.patch('charmhelpers.deprecate') as ch_deprecate:
    def mock_deprecate(warning, date=None, log=None):
        def mock_wrap(f):
            def wrapped_f(*args, **kwargs):
                return f(*args, **kwargs)
            return wrapped_f
        return mock_wrap
    ch_deprecate.side_effect = mock_deprecate
    import charmhelpers.contrib.openstack.utils as openstack  # noqa: F401
