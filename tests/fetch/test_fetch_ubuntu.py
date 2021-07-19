import six
import subprocess
import io
import os

from tests.helpers import patch_open
from testtools import TestCase
from mock import (
    patch,
    MagicMock,
    call,
    sentinel,
)
from charmhelpers.fetch import ubuntu as fetch

if six.PY3:
    builtin_open = 'builtins.open'
else:
    builtin_open = '__builtin__.open'

# mocked return of openstack.get_distrib_codename()
FAKE_CODENAME = 'precise'

url = 'deb ' + fetch.CLOUD_ARCHIVE_URL
UCA_SOURCES = [
    ('cloud:precise-folsom/proposed', url + ' precise-proposed/folsom main'),
    ('cloud:precise-folsom', url + ' precise-updates/folsom main'),
    ('cloud:precise-folsom/updates', url + ' precise-updates/folsom main'),
    ('cloud:precise-grizzly/proposed', url + ' precise-proposed/grizzly main'),
    ('cloud:precise-grizzly', url + ' precise-updates/grizzly main'),
    ('cloud:precise-grizzly/updates', url + ' precise-updates/grizzly main'),
    ('cloud:precise-havana/proposed', url + ' precise-proposed/havana main'),
    ('cloud:precise-havana', url + ' precise-updates/havana main'),
    ('cloud:precise-havana/updates', url + ' precise-updates/havana main'),
    ('cloud:precise-icehouse/proposed',
     url + ' precise-proposed/icehouse main'),
    ('cloud:precise-icehouse', url + ' precise-updates/icehouse main'),
    ('cloud:precise-icehouse/updates', url + ' precise-updates/icehouse main'),
]

PGP_KEY_ASCII_ARMOR = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: SKS 1.1.5
Comment: Hostname: keyserver.ubuntu.com

mI0EUCEyTAEEAMuUxyfiegCCwn4J/c0nw5PUTSJdn5FqiUTq6iMfij65xf1vl0g/Mxqw0gfg
AJIsCDvO9N9dloLAwF6FUBMg5My7WyhRPTAKF505TKJboyX3Pp4J1fU1LV8QFVOp87vUh1Rz
B6GU7cSglhnbL85gmbJTllkzkb3h4Yw7W+edjcQ/ABEBAAG0K0xhdW5jaHBhZCBQUEEgZm9y
IFVidW50dSBDbG91ZCBBcmNoaXZlIFRlYW2IuAQTAQIAIgUCUCEyTAIbAwYLCQgHAwIGFQgC
CQoLBBYCAwECHgECF4AACgkQimhEop9oEE7kJAP/eTBgq3Mhbvo0d8elMOuqZx3nmU7gSyPh
ep0zYIRZ5TJWl/7PRtvp0CJA6N6ZywYTQ/4ANHhpibcHZkh8K0AzUvsGXnJRSFoJeqyDbD91
EhoO+4ZfHs2HvRBQEDZILMa2OyuB497E5Mmyua3HDEOrG2cVLllsUZzpTFCx8NgeMHk=
=jLBm
-----END PGP PUBLIC KEY BLOCK-----"""

PGP_KEY_BIN_PGP = b'\x98\x8d\x04P!2L\x01\x04\x00\xcb\x94\xc7\'\xe2z\x00\x82\xc2~\t\xfd\xcd\'\xc3\x93\xd4M"]\x9f\x91j\x89D\xea\xea#\x1f\x8a>\xb9\xc5\xfdo\x97H?3\x1a\xb0\xd2\x07\xe0\x00\x92,\x08;\xce\xf4\xdf]\x96\x82\xc0\xc0^\x85P\x13 \xe4\xcc\xbb[(Q=0\n\x17\x9d9L\xa2[\xa3%\xf7>\x9e\t\xd5\xf55-_\x10\x15S\xa9\xf3\xbb\xd4\x87Ts\x07\xa1\x94\xed\xc4\xa0\x96\x19\xdb/\xce`\x99\xb2S\x96Y3\x91\xbd\xe1\xe1\x8c;[\xe7\x9d\x8d\xc4?\x00\x11\x01\x00\x01\xb4+Launchpad PPA for Ubuntu Cloud Archive Team\x88\xb8\x04\x13\x01\x02\x00"\x05\x02P!2L\x02\x1b\x03\x06\x0b\t\x08\x07\x03\x02\x06\x15\x08\x02\t\n\x0b\x04\x16\x02\x03\x01\x02\x1e\x01\x02\x17\x80\x00\n\t\x10\x8ahD\xa2\x9fh\x10N\xe4$\x03\xffy0`\xabs!n\xfa4w\xc7\xa50\xeb\xaag\x1d\xe7\x99N\xe0K#\xe1z\x9d3`\x84Y\xe52V\x97\xfe\xcfF\xdb\xe9\xd0"@\xe8\xde\x99\xcb\x06\x13C\xfe\x004xi\x89\xb7\x07fH|+@3R\xfb\x06^rQHZ\tz\xac\x83l?u\x12\x1a\x0e\xfb\x86_\x1e\xcd\x87\xbd\x10P\x106H,\xc6\xb6;+\x81\xe3\xde\xc4\xe4\xc9\xb2\xb9\xad\xc7\x0cC\xab\x1bg\x15.YlQ\x9c\xe9LP\xb1\xf0\xd8\x1e0y'  # noqa

# a keyid can be retrieved by the ASCII armor-encoded key using this:
# cat testkey.asc | gpg --with-colons --import-options import-show --dry-run
# --import
PGP_KEY_ID = '8a6844a29f68104e'

FAKE_APT_CACHE = {
    # an installed package
    'vim': {
        'current_ver': '2:7.3.547-6ubuntu5'
    },
    # a uninstalled installation candidate
    'emacs': {
    }
}


def fake_apt_cache(in_memory=True, progress=None):
    def _get(package):
        pkg = MagicMock()
        if package not in FAKE_APT_CACHE:
            raise KeyError
        pkg.name = package
        if 'current_ver' in FAKE_APT_CACHE[package]:
            pkg.current_ver.ver_str = FAKE_APT_CACHE[package]['current_ver']
        else:
            pkg.current_ver = None
        return pkg
    cache = MagicMock()
    cache.__getitem__.side_effect = _get
    return cache


class FetchTest(TestCase):

    def setUp(self):
        super(FetchTest, self).setUp()
        self.patch(fetch, 'get_apt_dpkg_env', lambda: {})

    @patch("charmhelpers.fetch.ubuntu.log")
    @patch.object(fetch, 'apt_cache')
    def test_filter_packages_missing_ubuntu(self, cache, log):
        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim', 'emacs'])
        self.assertEquals(result, ['emacs'])

    @patch("charmhelpers.fetch.ubuntu.log")
    @patch.object(fetch, 'apt_cache')
    def test_filter_packages_none_missing_ubuntu(self, cache, log):
        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim'])
        self.assertEquals(result, [])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'apt_cache')
    def test_filter_packages_not_available_ubuntu(self, cache, log):
        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim', 'joe'])
        self.assertEquals(result, ['joe'])
        log.assert_called_with('Package joe has no installation candidate.',
                               level='WARNING')

    @patch('charmhelpers.fetch.ubuntu.filter_installed_packages')
    def test_filter_missing_packages(self, filter_installed_packages):
        filter_installed_packages.return_value = ['pkga']
        self.assertEqual(['pkgb'],
                         fetch.filter_missing_packages(['pkga', 'pkgb']))

    @patch.object(fetch, 'log', lambda *args, **kwargs: None)
    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    def test_import_apt_key_radix(self, dearmor_gpg_key,
                                  w_keyfile):
        def dearmor_side_effect(key_asc):
            return {
                PGP_KEY_ASCII_ARMOR: PGP_KEY_BIN_PGP,
            }[key_asc]
        dearmor_gpg_key.side_effect = dearmor_side_effect

        with patch('subprocess.check_output') as _subp_check_output:
            curl_cmd = ['curl', ('https://keyserver.ubuntu.com'
                                 '/pks/lookup?op=get&options=mr'
                                 '&exact=on&search=0x{}').format(PGP_KEY_ID)]

            def check_output_side_effect(command, env):
                return {
                    ' '.join(curl_cmd): PGP_KEY_ASCII_ARMOR,
                }[' '.join(command)]
            _subp_check_output.side_effect = check_output_side_effect

            fetch.import_key(PGP_KEY_ID)
            _subp_check_output.assert_called_with(curl_cmd, env=None)
        w_keyfile.assert_called_once_with(key_name=PGP_KEY_ID,
                                          key_material=PGP_KEY_BIN_PGP)

    @patch.object(fetch, 'log', lambda *args, **kwargs: None)
    @patch.object(os, 'getenv')
    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    def test_import_apt_key_radix_https_proxy(self, dearmor_gpg_key,
                                              w_keyfile, getenv):
        def dearmor_side_effect(key_asc):
            return {
                PGP_KEY_ASCII_ARMOR: PGP_KEY_BIN_PGP,
            }[key_asc]
        dearmor_gpg_key.side_effect = dearmor_side_effect

        def get_env_side_effect(var):
            return {
                'HTTPS_PROXY': 'http://squid.internal:3128',
                'JUJU_CHARM_HTTPS_PROXY': None,
            }[var]
        getenv.side_effect = get_env_side_effect

        with patch('subprocess.check_output') as _subp_check_output:
            proxy_settings = {
                'HTTPS_PROXY': 'http://squid.internal:3128',
                'https_proxy': 'http://squid.internal:3128',
            }
            curl_cmd = ['curl', ('https://keyserver.ubuntu.com'
                                 '/pks/lookup?op=get&options=mr'
                                 '&exact=on&search=0x{}').format(PGP_KEY_ID)]

            def check_output_side_effect(command, env):
                return {
                    ' '.join(curl_cmd): PGP_KEY_ASCII_ARMOR,
                }[' '.join(command)]
            _subp_check_output.side_effect = check_output_side_effect

            fetch.import_key(PGP_KEY_ID)
            _subp_check_output.assert_called_with(curl_cmd, env=proxy_settings)
        w_keyfile.assert_called_once_with(key_name=PGP_KEY_ID,
                                          key_material=PGP_KEY_BIN_PGP)

    @patch.object(fetch, 'log', lambda *args, **kwargs: None)
    @patch.object(os, 'getenv')
    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    def test_import_apt_key_radix_charm_https_proxy(self, dearmor_gpg_key,
                                                    w_keyfile, getenv):
        def dearmor_side_effect(key_asc):
            return {
                PGP_KEY_ASCII_ARMOR: PGP_KEY_BIN_PGP,
            }[key_asc]
        dearmor_gpg_key.side_effect = dearmor_side_effect

        def get_env_side_effect(var):
            return {
                'HTTPS_PROXY': None,
                'JUJU_CHARM_HTTPS_PROXY': 'http://squid.internal:3128',
            }[var]
        getenv.side_effect = get_env_side_effect

        with patch('subprocess.check_output') as _subp_check_output:
            proxy_settings = {
                'HTTPS_PROXY': 'http://squid.internal:3128',
                'https_proxy': 'http://squid.internal:3128',
            }
            curl_cmd = ['curl', ('https://keyserver.ubuntu.com'
                                 '/pks/lookup?op=get&options=mr'
                                 '&exact=on&search=0x{}').format(PGP_KEY_ID)]

            def check_output_side_effect(command, env):
                return {
                    ' '.join(curl_cmd): PGP_KEY_ASCII_ARMOR,
                }[' '.join(command)]
            _subp_check_output.side_effect = check_output_side_effect

            fetch.import_key(PGP_KEY_ID)
            _subp_check_output.assert_called_with(curl_cmd, env=proxy_settings)
        w_keyfile.assert_called_once_with(key_name=PGP_KEY_ID,
                                          key_material=PGP_KEY_BIN_PGP)

    @patch.object(fetch, 'log', lambda *args, **kwargs: None)
    @patch.object(fetch, '_dearmor_gpg_key')
    @patch('subprocess.check_output')
    def test_import_bad_apt_key(self, check_output, dearmor_gpg_key):
        """Ensure error when importing apt key fails"""
        errmsg = ('Invalid GPG key material. Check your network setup'
                  ' (MTU, routing, DNS) and/or proxy server settings'
                  ' as well as destination keyserver status.')
        bad_keyid = 'foo'

        curl_cmd = ['curl', ('https://keyserver.ubuntu.com'
                             '/pks/lookup?op=get&options=mr'
                             '&exact=on&search=0x{}').format(bad_keyid)]

        def check_output_side_effect(command, env):
            return {
                ' '.join(curl_cmd): 'foobar',
            }[' '.join(command)]
        check_output.side_effect = check_output_side_effect

        def dearmor_side_effect(key_asc):
            raise fetch.GPGKeyError(errmsg)
        dearmor_gpg_key.side_effect = dearmor_side_effect
        try:
            fetch.import_key(bad_keyid)
            assert False
        except fetch.GPGKeyError as e:
            self.assertEqual(str(e), errmsg)

    @patch('charmhelpers.fetch.ubuntu.log')
    def test_add_source_none_ubuntu(self, log):
        fetch.add_source(source=None)
        self.assertTrue(log.called)

    @patch('subprocess.check_call')
    def test_add_source_ppa(self, check_call):
        source = "ppa:test-ppa"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source], env={})

    @patch("charmhelpers.fetch.ubuntu.log")
    @patch('subprocess.check_call')
    @patch('time.sleep')
    def test_add_source_ppa_retries_30_times(self, sleep, check_call, log):
        self.call_count = 0

        def side_effect(*args, **kwargs):
            """Raise an 3 times, then return 0 """
            self.call_count += 1
            if self.call_count <= fetch.CMD_RETRY_COUNT:
                raise subprocess.CalledProcessError(
                    returncode=1, cmd="some add-apt-repository command")
            else:
                return 0
        check_call.side_effect = side_effect

        source = "ppa:test-ppa"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source], env={})
        sleep.assert_called_with(10)
        self.assertTrue(fetch.CMD_RETRY_COUNT, sleep.call_count)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_http_ubuntu(self, check_call, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source], env={})

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_https(self, check_call, log):
        source = "https://example.com"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source], env={})

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_deb(self, check_call, log):
        """add-apt-repository behaves differently when using the deb prefix.

        $ add-apt-repository --yes \
            "http://special.example.com/ubuntu precise-special main"
        $ grep special /etc/apt/sources.list
        deb http://special.example.com/ubuntu precise precise-special main
        deb-src http://special.example.com/ubuntu precise precise-special main

        $ add-apt-repository --yes \
            "deb http://special.example.com/ubuntu precise-special main"
        $ grep special /etc/apt/sources.list
        deb http://special.example.com/ubuntu precise precise-special main
        deb-src http://special.example.com/ubuntu precise precise-special main
        deb http://special.example.com/ubuntu precise-special main
        deb-src http://special.example.com/ubuntu precise-special main
        """
        source = "deb http://archive.ubuntu.com/ubuntu raring-backports main"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source], env={})

    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_id(self, check_call, check_output, log,
                                        dearmor_gpg_key,
                                        w_keyfile):
        def dearmor_side_effect(key_asc):
            return {
                PGP_KEY_ASCII_ARMOR: PGP_KEY_BIN_PGP,
            }[key_asc]
        dearmor_gpg_key.side_effect = dearmor_side_effect

        curl_cmd = ['curl', ('https://keyserver.ubuntu.com'
                             '/pks/lookup?op=get&options=mr'
                             '&exact=on&search=0x{}').format(PGP_KEY_ID)]

        def check_output_side_effect(command, env):
            return {
                ' '.join(curl_cmd): PGP_KEY_ASCII_ARMOR,
            }[' '.join(command)]
        check_output.side_effect = check_output_side_effect
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        check_call.return_value = 0  # Successful exit code
        fetch.add_source(source=source, key=PGP_KEY_ID)
        check_call.assert_any_call(
            ['add-apt-repository', '--yes', source], env={}),
        check_output.assert_has_calls([
            call(['curl', ('https://keyserver.ubuntu.com'
                           '/pks/lookup?op=get&options=mr'
                           '&exact=on&search=0x{}').format(PGP_KEY_ID)],
                 env=None),
        ])

    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_add_source_https_and_key_id(self, check_call, check_output, log,
                                         dearmor_gpg_key,
                                         w_keyfile):
        def dearmor_side_effect(key_asc):
            return {
                PGP_KEY_ASCII_ARMOR: PGP_KEY_BIN_PGP,
            }[key_asc]
        dearmor_gpg_key.side_effect = dearmor_side_effect

        curl_cmd = ['curl', ('https://keyserver.ubuntu.com'
                             '/pks/lookup?op=get&options=mr'
                             '&exact=on&search=0x{}').format(PGP_KEY_ID)]

        def check_output_side_effect(command, env):
            return {
                ' '.join(curl_cmd): PGP_KEY_ASCII_ARMOR,
            }[' '.join(command)]
        check_output.side_effect = check_output_side_effect

        check_call.return_value = 0

        source = "https://USER:PASS@private-ppa.launchpad.net/project/awesome"
        fetch.add_source(source=source, key=PGP_KEY_ID)
        check_call.assert_any_call(
            ['add-apt-repository', '--yes', source], env={}),
        check_output.assert_has_calls([
            call(['curl', ('https://keyserver.ubuntu.com'
                           '/pks/lookup?op=get&options=mr'
                           '&exact=on&search=0x{}').format(PGP_KEY_ID)],
                 env=None),
        ])

    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'get_distrib_codename')
    @patch('subprocess.check_call')
    @patch('subprocess.Popen')
    def test_add_source_http_and_key_gpg1(self, popen, check_call,
                                          get_distrib_codename, log,
                                          dearmor_gpg_key,
                                          w_keyfile):

        def check_call_side_effect(*args, **kwargs):
            # Make sure the gpg key has already been added before the
            # add-apt-repository call, as the update could fail otherwise.
            popen.assert_called_with(
                ['gpg', '--with-colons', '--with-fingerprint'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE)
            return 0

        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = PGP_KEY_ASCII_ARMOR
        key_bytes = PGP_KEY_ASCII_ARMOR.encode('utf-8')
        get_distrib_codename.return_value = 'trusty'
        check_call.side_effect = check_call_side_effect

        expected_key = '35F77D63B5CEC106C577ED856E85A86E4652B4E6'
        if six.PY3:
            popen.return_value.communicate.return_value = [b"""
pub:-:1024:1:6E85A86E4652B4E6:2009-01-18:::-:Launchpad PPA for Landscape:
fpr:::::::::35F77D63B5CEC106C577ED856E85A86E4652B4E6:
            """, b'']
        else:
            popen.return_value.communicate.return_value = ["""
pub:-:1024:1:6E85A86E4652B4E6:2009-01-18:::-:Launchpad PPA for Landscape:
fpr:::::::::35F77D63B5CEC106C577ED856E85A86E4652B4E6:
            """, '']

        dearmor_gpg_key.return_value = PGP_KEY_BIN_PGP

        fetch.add_source(source=source, key=key)
        popen.assert_called_with(
            ['gpg', '--with-colons', '--with-fingerprint'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)
        dearmor_gpg_key.assert_called_with(key_bytes)
        w_keyfile.assert_called_with(key_name=expected_key,
                                     key_material=PGP_KEY_BIN_PGP)
        check_call.assert_any_call(
            ['add-apt-repository', '--yes', source], env={}),

    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'get_distrib_codename')
    @patch('subprocess.check_call')
    @patch('subprocess.Popen')
    def test_add_source_http_and_key_gpg2(self, popen, check_call,
                                          get_distrib_codename, log,
                                          dearmor_gpg_key,
                                          w_keyfile):

        def check_call_side_effect(*args, **kwargs):
            # Make sure the gpg key has already been added before the
            # add-apt-repository call, as the update could fail otherwise.
            popen.assert_called_with(
                ['gpg', '--with-colons', '--with-fingerprint'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE)
            return 0

        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = PGP_KEY_ASCII_ARMOR
        key_bytes = PGP_KEY_ASCII_ARMOR.encode('utf-8')
        get_distrib_codename.return_value = 'bionic'
        check_call.side_effect = check_call_side_effect

        expected_key = '35F77D63B5CEC106C577ED856E85A86E4652B4E6'

        if six.PY3:
            popen.return_value.communicate.return_value = [b"""
fpr:::::::::35F77D63B5CEC106C577ED856E85A86E4652B4E6:
uid:-::::1232306042::52FE92E6867B4C099AA1A1877A804A965F41A98C::ppa::::::::::0:
            """, b'']
        else:
            # python2 on a distro with gpg2 (unlikely, but possible)
            popen.return_value.communicate.return_value = ["""
fpr:::::::::35F77D63B5CEC106C577ED856E85A86E4652B4E6:
uid:-::::1232306042::52FE92E6867B4C099AA1A1877A804A965F41A98C::ppa::::::::::0:
            """, '']

        dearmor_gpg_key.return_value = PGP_KEY_BIN_PGP

        fetch.add_source(source=source, key=key)
        popen.assert_called_with(
            ['gpg', '--with-colons', '--with-fingerprint'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)
        dearmor_gpg_key.assert_called_with(key_bytes)
        w_keyfile.assert_called_with(key_name=expected_key,
                                     key_material=PGP_KEY_BIN_PGP)
        check_call.assert_any_call(
            ['add-apt-repository', '--yes', source], env={}),

    def test_add_source_cloud_invalid_pocket(self):
        source = "cloud:havana-updates"
        self.assertRaises(fetch.SourceConfigError,
                          fetch.add_source, source)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    @patch.object(fetch, 'get_distrib_codename')
    def test_add_source_cloud_pocket_style(self, get_distrib_codename,
                                           apt_install,
                                           filter_pkg, log):
        source = "cloud:precise-updates/havana"
        get_distrib_codename.return_value = 'precise'
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')

        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    @patch.object(fetch, 'get_distrib_codename')
    def test_add_source_cloud_os_style(self, get_distrib_codename, apt_install,
                                       filter_pkg, log):
        source = "cloud:precise-havana"
        get_distrib_codename.return_value = 'precise'
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    def test_add_source_cloud_distroless_style(self, apt_install,
                                               filter_pkg, log):
        source = "cloud:havana"
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'get_distrib_codename')
    @patch('platform.machine')
    def test_add_source_proposed_x86_64(self, _machine,
                                        get_distrib_codename, log):
        source = "proposed"
        result = ('# Proposed\n'
                  'deb http://archive.ubuntu.com/ubuntu precise-proposed'
                  ' main universe multiverse restricted\n')
        get_distrib_codename.return_value = 'precise'
        _machine.return_value = 'x86_64'
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'get_distrib_codename')
    @patch('platform.machine')
    def test_add_source_proposed_ppc64le(self, _machine,
                                         get_distrib_codename, log):
        source = "proposed"
        result = (
            "# Proposed\n"
            "deb http://ports.ubuntu.com/ubuntu-ports precise-proposed main "
            "universe multiverse restricted\n")
        get_distrib_codename.return_value = 'precise'
        _machine.return_value = 'ppc64le'
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)

    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_id_ubuntu(self, check_call, check_output,
                                               log, dearmor_gpg_key,
                                               w_keyfile):
        def dearmor_side_effect(key_asc):
            return {
                PGP_KEY_ASCII_ARMOR: PGP_KEY_BIN_PGP,
            }[key_asc]
        dearmor_gpg_key.side_effect = dearmor_side_effect

        curl_cmd = ['curl', ('https://keyserver.ubuntu.com'
                             '/pks/lookup?op=get&options=mr'
                             '&exact=on&search=0x{}').format(PGP_KEY_ID)]

        def check_output_side_effect(command, env):
            return {
                ' '.join(curl_cmd): PGP_KEY_ASCII_ARMOR,
            }[' '.join(command)]
        check_output.side_effect = check_output_side_effect
        check_call.return_value = 0
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key_id = PGP_KEY_ID
        fetch.add_source(source=source, key=key_id)
        check_call.assert_any_call(
            ['add-apt-repository', '--yes', source], env={}),
        check_output.assert_has_calls([
            call(['curl', ('https://keyserver.ubuntu.com'
                           '/pks/lookup?op=get&options=mr'
                           '&exact=on&search=0x{}').format(PGP_KEY_ID)],
                 env=None),
        ])

    @patch.object(fetch, '_write_apt_gpg_keyfile')
    @patch.object(fetch, '_dearmor_gpg_key')
    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    def test_add_source_https_and_key_id_ubuntu(self, check_call, check_output,
                                                log, dearmor_gpg_key,
                                                w_keyfile):
        def dearmor_side_effect(key_asc):
            return {
                PGP_KEY_ASCII_ARMOR: PGP_KEY_BIN_PGP,
            }[key_asc]
        dearmor_gpg_key.side_effect = dearmor_side_effect

        curl_cmd = ['curl', ('https://keyserver.ubuntu.com'
                             '/pks/lookup?op=get&options=mr'
                             '&exact=on&search=0x{}').format(PGP_KEY_ID)]

        def check_output_side_effect(command, env):
            return {
                ' '.join(curl_cmd): PGP_KEY_ASCII_ARMOR,
            }[' '.join(command)]
        check_output.side_effect = check_output_side_effect
        check_call.return_value = 0

        source = "https://USER:PASS@private-ppa.launchpad.net/project/awesome"
        fetch.add_source(source=source, key=PGP_KEY_ID)
        check_call.assert_any_call(
            ['add-apt-repository', '--yes', source], env={}),
        check_output.assert_has_calls([
            call(['curl', ('https://keyserver.ubuntu.com'
                           '/pks/lookup?op=get&options=mr'
                           '&exact=on&search=0x{}').format(PGP_KEY_ID)],
                 env=None),
        ])

    @patch('charmhelpers.fetch.ubuntu.log')
    def test_configure_bad_install_source(self, log):
        try:
            fetch.add_source('foo', fail_invalid=True)
            self.fail("Calling add_source('foo') should fail")
        except fetch.SourceConfigError as e:
            self.assertEqual(str(e), "Unknown source: 'foo'")

    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_configure_install_source_uca_staging(self, _lsb):
        """Test configuring installation source from UCA staging sources"""
        _lsb.return_value = FAKE_CODENAME
        # staging pockets are configured as PPAs
        with patch('subprocess.check_call') as _subp:
            src = 'cloud:precise-folsom/staging'
            fetch.add_source(src)
            cmd = ['add-apt-repository', '-y',
                   'ppa:ubuntu-cloud-archive/folsom-staging']
            _subp.assert_called_with(cmd, env={})

    @patch(builtin_open)
    @patch('charmhelpers.fetch.ubuntu.apt_install')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    @patch('charmhelpers.fetch.ubuntu.filter_installed_packages')
    def test_configure_install_source_uca_repos(
            self, _fip, _lsb, _install, _open):
        """Test configuring installation source from UCA sources"""
        _lsb.return_value = FAKE_CODENAME
        _file = MagicMock(spec=io.FileIO)
        _open.return_value = _file
        _fip.side_effect = lambda x: x
        for src, url in UCA_SOURCES:
            actual_url = "# Ubuntu Cloud Archive\n{}\n".format(url)
            fetch.add_source(src)
            _install.assert_called_with(['ubuntu-cloud-keyring'],
                                        fatal=True)
            _open.assert_called_with(
                '/etc/apt/sources.list.d/cloud-archive.list',
                'w'
            )
            _file.__enter__().write.assert_called_with(actual_url)

    def test_configure_install_source_bad_uca(self):
        """Test configuring installation source from bad UCA source"""
        try:
            fetch.add_source('cloud:foo-bar', fail_invalid=True)
            self.fail("add_source('cloud:foo-bar') should fail")
        except fetch.SourceConfigError as e:
            _e = ('Invalid Cloud Archive release specified: foo-bar'
                  ' on this Ubuntuversion')
            self.assertTrue(str(e).startswith(_e))

    @patch('charmhelpers.fetch.ubuntu.log')
    def test_add_unparsable_source(self, log_):
        source = "propsed"  # Minor typo
        fetch.add_source(source=source)
        self.assertEqual(1, log_.call_count)

    @patch('charmhelpers.fetch.ubuntu.log')
    def test_add_distro_source(self, log):
        source = "distro"
        # distro is a noop but test validate no exception is thrown
        fetch.add_source(source=source)

    @patch('charmhelpers.fetch.ubuntu._add_cloud_pocket')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_add_bare_openstack_is_distro(
            self, mock_get_distrib_codename, mock_add_cloud_pocket):
        mock_get_distrib_codename.return_value = 'focal'
        fetch.add_source('ussuri')
        mock_add_cloud_pocket.assert_not_called()

    @patch('charmhelpers.fetch.ubuntu._add_cloud_pocket')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_add_bare_openstack_is_cloud_pocket(
            self, mock_get_distrib_codename, mock_add_cloud_pocket):
        mock_get_distrib_codename.return_value = 'bionic'
        fetch.add_source('ussuri')
        mock_add_cloud_pocket.assert_called_once_with("bionic-ussuri")

    @patch('charmhelpers.fetch.ubuntu._add_cloud_pocket')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_add_bare_openstack_impossible_version(
            self, mock_get_distrib_codename, mock_add_cloud_pocket):
        mock_get_distrib_codename.return_value = 'xenial'
        try:
            fetch.add_source('ussuri')
            self.fail("add_source('ussuri') on xenial should fail")
        except fetch.SourceConfigError:
            pass
        mock_add_cloud_pocket.assert_not_called()

    @patch('charmhelpers.fetch.ubuntu._add_cloud_pocket')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_add_bare_openstack_impossible_ubuntu(
            self, mock_get_distrib_codename, mock_add_cloud_pocket):
        mock_get_distrib_codename.return_value = 'bambam'
        try:
            fetch.add_source('ussuri')
            self.fail("add_source('ussuri') on bambam should fail")
        except fetch.SourceConfigError:
            pass
        mock_add_cloud_pocket.assert_not_called()

    @patch('charmhelpers.fetch.ubuntu._add_proposed')
    @patch('charmhelpers.fetch.ubuntu._add_cloud_pocket')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_add_bare_openstack_proposed_is_distro_proposed(
            self, mock_get_distrib_codename, mock_add_cloud_pocket,
            mock_add_proposed):
        mock_get_distrib_codename.return_value = 'focal'
        fetch.add_source('ussuri/proposed')
        mock_add_cloud_pocket.assert_not_called()
        mock_add_proposed.assert_called_once_with()

    @patch('charmhelpers.fetch.ubuntu._add_proposed')
    @patch('charmhelpers.fetch.ubuntu._add_cloud_pocket')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_add_bare_openstack_proposed_is_cloud_pocket(
            self, mock_get_distrib_codename, mock_add_cloud_pocket,
            mock_add_proposed):
        mock_get_distrib_codename.return_value = 'bionic'
        fetch.add_source('ussuri/proposed')
        mock_add_cloud_pocket.assert_called_once_with("bionic-ussuri/proposed")
        mock_add_proposed.assert_not_called()

    @patch('charmhelpers.fetch.ubuntu._add_proposed')
    @patch('charmhelpers.fetch.ubuntu._add_cloud_pocket')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_add_bare_openstack_proposed_impossible_version(
            self, mock_get_distrib_codename, mock_add_cloud_pocket,
            mock_add_proposed):
        mock_get_distrib_codename.return_value = 'xenial'
        try:
            fetch.add_source('ussuri/proposed')
            self.fail("add_source('ussuri/proposed') on xenial should fail")
        except fetch.SourceConfigError:
            pass
        mock_add_cloud_pocket.assert_not_called()
        mock_add_proposed.assert_not_called()

    @patch('charmhelpers.fetch.ubuntu._add_proposed')
    @patch('charmhelpers.fetch.ubuntu._add_cloud_pocket')
    @patch('charmhelpers.fetch.ubuntu.get_distrib_codename')
    def test_add_bare_openstack_proposed_impossible_ubuntu(
            self, mock_get_distrib_codename, mock_add_cloud_pocket,
            mock_add_proposed):
        mock_get_distrib_codename.return_value = 'bambam'
        try:
            fetch.add_source('ussuri/proposed')
            self.fail("add_source('ussuri/proposed') on bambam should fail")
        except fetch.SourceConfigError:
            pass
        mock_add_cloud_pocket.assert_not_called()
        mock_add_proposed.assert_not_called()


class AptTests(TestCase):

    def setUp(self):
        super(AptTests, self).setUp()
        self.patch(fetch, 'get_apt_dpkg_env', lambda: {})

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_upgrade_non_fatal(self, log, mock_call):
        options = ['--foo', '--bar']
        fetch.apt_upgrade(options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'upgrade'],
            env={})

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_upgrade_fatal(self, log, mock_call):
        options = ['--foo', '--bar']
        fetch.apt_upgrade(options, fatal=True)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'upgrade'],
            env={})

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_dist_upgrade_fatal(self, log, mock_call):
        options = ['--foo', '--bar']
        fetch.apt_upgrade(options, fatal=True, dist=True)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'dist-upgrade'],
            env={})

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages(self, log, mock_call):
        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo', 'bar'],
            env={})

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_without_options(self, log, mock_call):
        packages = ['foo', 'bar']

        fetch.apt_install(packages)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--option=Dpkg::Options::=--force-confold',
             'install', 'foo', 'bar'],
            env={})

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_as_string(self, log, mock_call):
        packages = 'foo bar'
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo bar'],
            env={})

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_with_possible_errors(self, log,
                                                        check_call):
        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options, fatal=True)

        check_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo', 'bar'],
            env={})

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_as_string_fatal(self, log, mock_call):
        packages = 'irrelevant names'
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_fatal(self, log, mock_call):
        packages = ['irrelevant', 'names']
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_as_string_nofatal(self, log, mock_call):
        packages = 'foo bar'

        fetch.apt_purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-get', '--assume-yes', 'purge', 'foo bar'],
            env={})

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_nofatal(self, log, mock_call):
        packages = ['foo', 'bar']

        fetch.apt_purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-get', '--assume-yes', 'purge', 'foo', 'bar'],
            env={})

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_as_string_fatal(self, log, mock_call):
        packages = 'irrelevant names'
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_mark, packages, sentinel.mark,
                          fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_fatal(self, log, mock_call):
        packages = ['irrelevant', 'names']
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_mark, packages, sentinel.mark,
                          fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_as_string_nofatal(self, log, mock_call):
        packages = 'foo bar'

        fetch.apt_mark(packages, sentinel.mark)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo bar'],
            universal_newlines=True)

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_nofatal(self, log, mock_call):
        packages = ['foo', 'bar']

        fetch.apt_mark(packages, sentinel.mark)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo', 'bar'],
            universal_newlines=True)

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_nofatal_abortonfatal(self, log, mock_call):
        packages = ['foo', 'bar']

        fetch.apt_mark(packages, sentinel.mark, fatal=True)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo', 'bar'],
            universal_newlines=True)

    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_hold(self, apt_mark):
        fetch.apt_hold(sentinel.packages)
        apt_mark.assert_called_once_with(sentinel.packages, 'hold',
                                         fatal=False)

    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_hold_fatal(self, apt_mark):
        fetch.apt_hold(sentinel.packages, fatal=sentinel.fatal)
        apt_mark.assert_called_once_with(sentinel.packages, 'hold',
                                         fatal=sentinel.fatal)

    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_unhold(self, apt_mark):
        fetch.apt_unhold(sentinel.packages)
        apt_mark.assert_called_once_with(sentinel.packages, 'unhold',
                                         fatal=False)

    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_unhold_fatal(self, apt_mark):
        fetch.apt_unhold(sentinel.packages, fatal=sentinel.fatal)
        apt_mark.assert_called_once_with(sentinel.packages, 'unhold',
                                         fatal=sentinel.fatal)

    @patch('subprocess.check_call')
    def test_apt_update_fatal(self, check_call):
        fetch.apt_update(fatal=True)
        check_call.assert_called_with(
            ['apt-get', 'update'],
            env={})

    @patch('subprocess.call')
    def test_apt_update_nonfatal(self, call):
        fetch.apt_update()
        call.assert_called_with(
            ['apt-get', 'update'],
            env={})

    @patch('subprocess.check_call')
    @patch('time.sleep')
    def test_run_apt_command_retries_if_fatal(self, check_call, sleep):
        """The _run_apt_command function retries the command if it can't get
        the APT lock."""
        self.called = False

        def side_effect(*args, **kwargs):
            """
            First, raise an exception (can't acquire lock), then return 0
            (the lock is grabbed).
            """
            if not self.called:
                self.called = True
                raise subprocess.CalledProcessError(
                    returncode=100, cmd="some command")
            else:
                return 0

        check_call.side_effect = side_effect
        check_call.return_value = 0

        from charmhelpers.fetch.ubuntu import _run_apt_command
        _run_apt_command(["some", "command"], fatal=True)
        self.assertTrue(sleep.called)

    @patch.object(fetch, 'apt_cache')
    def test_get_upstream_version(self, cache):
        cache.side_effect = fake_apt_cache
        self.assertEqual(fetch.get_upstream_version('vim'), '7.3.547')
        self.assertEqual(fetch.get_upstream_version('emacs'), None)
        self.assertEqual(fetch.get_upstream_version('unknown'), None)

    @patch('charmhelpers.fetch.ubuntu._run_apt_command')
    def test_apt_autoremove_fatal(self, run_apt_command):
        fetch.apt_autoremove(purge=True, fatal=True)
        run_apt_command.assert_called_with(
            ['apt-get', '--assume-yes', 'autoremove', '--purge'],
            True
        )

    @patch('charmhelpers.fetch.ubuntu._run_apt_command')
    def test_apt_autoremove_nonfatal(self, run_apt_command):
        fetch.apt_autoremove(purge=False, fatal=False)
        run_apt_command.assert_called_with(
            ['apt-get', '--assume-yes', 'autoremove'],
            False
        )


class TestAptDpkgEnv(TestCase):

    @patch.object(fetch, 'get_system_env')
    def test_get_apt_dpkg_env(self, mock_get_system_env):
        mock_get_system_env.return_value = '/a/path'
        self.assertEquals(
            fetch.get_apt_dpkg_env(),
            {'DEBIAN_FRONTEND': 'noninteractive', 'PATH': '/a/path'})
