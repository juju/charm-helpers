"""Juju GUI charm utilities."""

__all__ = [
    'AGENT',
    'APACHE',
    'API_PORT',
    'CURRENT_DIR',
    'HAPROXY',
    'IMPROV',
    'JUJU_DIR',
    'JUJU_GUI_DIR',
    'JUJU_GUI_SITE',
    'JUJU_PEM',
    'WEB_PORT',
    'bzr_checkout',
    'chain',
    'cmd_log',
    'fetch_api',
    'fetch_gui',
    'find_missing_packages',
    'first_path_in_dir',
    'get_api_address',
    'get_npm_cache_archive_url',
    'get_release_file_url',
    'get_staging_dependencies',
    'get_zookeeper_address',
    'legacy_juju',
    'log_hook',
    'merge',
    'parse_source',
    'prime_npm_cache',
    'render_to_file',
    'save_or_create_certificates',
    'setup_apache',
    'setup_gui',
    'start_agent',
    'start_gui',
    'start_improv',
    'write_apache_config',
]

from contextlib import contextmanager
import errno
import json
import os
import logging
import shutil
from subprocess import CalledProcessError
import tempfile
from urlparse import urlparse

import apt
import tempita

from launchpadlib.launchpad import Launchpad
from shelltoolbox import (
    Serializer,
    apt_get_install,
    command,
    environ,
    install_extra_repositories,
    run,
    script_name,
    search_file,
    su,
)
from charmhelpers.core.host import (
    service_start,
)
from charmhelpers.core.hookenv import (
    log,
    config,
    unit_get,
)


AGENT = 'juju-api-agent'
APACHE = 'apache2'
IMPROV = 'juju-api-improv'
HAPROXY = 'haproxy'

API_PORT = 8080
WEB_PORT = 8000

CURRENT_DIR = os.getcwd()
JUJU_DIR = os.path.join(CURRENT_DIR, 'juju')
JUJU_GUI_DIR = os.path.join(CURRENT_DIR, 'juju-gui')
JUJU_GUI_SITE = '/etc/apache2/sites-available/juju-gui'
JUJU_GUI_PORTS = '/etc/apache2/ports.conf'
JUJU_PEM = 'juju.includes-private-key.pem'
BUILD_REPOSITORIES = ('ppa:chris-lea/node.js-legacy',)
DEB_BUILD_DEPENDENCIES = (
    'bzr', 'imagemagick', 'make', 'nodejs', 'npm',
)
DEB_STAGE_DEPENDENCIES = (
    'zookeeper',
)


# Store the configuration from on invocation to the next.
config_json = Serializer('/tmp/config.json')
# Bazaar checkout command.
bzr_checkout = command('bzr', 'co', '--lightweight')
# Whether or not the charm is deployed using juju-core.
# If juju-core has been used to deploy the charm, an agent.conf file must
# be present in the charm parent directory.
legacy_juju = lambda: not os.path.exists(
    os.path.join(CURRENT_DIR, '..', 'agent.conf'))


def _get_build_dependencies():
    """Install deb dependencies for building."""
    log('Installing build dependencies.')
    cmd_log(install_extra_repositories(*BUILD_REPOSITORIES))
    cmd_log(apt_get_install(*DEB_BUILD_DEPENDENCIES))


def get_api_address(unit_dir):
    """Return the Juju API address stored in the uniter agent.conf file."""
    import yaml  # python-yaml is only installed if juju-core is used.
    # XXX 2013-03-27 frankban bug=1161443:
        # currently the uniter agent.conf file does not include the API
        # address. For now retrieve it from the machine agent file.
    base_dir = os.path.abspath(os.path.join(unit_dir, '..'))
    for dirname in os.listdir(base_dir):
        if dirname.startswith('machine-'):
            agent_conf = os.path.join(base_dir, dirname, 'agent.conf')
            break
    else:
        raise IOError('Juju agent configuration file not found.')
    contents = yaml.load(open(agent_conf))
    return contents['apiinfo']['addrs'][0]


def get_staging_dependencies():
    """Install deb dependencies for the stage (improv) environment."""
    log('Installing stage dependencies.')
    cmd_log(apt_get_install(*DEB_STAGE_DEPENDENCIES))


def first_path_in_dir(directory):
    """Return the full path of the first file/dir in *directory*."""
    return os.path.join(directory, os.listdir(directory)[0])


def _get_by_attr(collection, attr, value):
    """Return the first item in collection having attr == value.

    Return None if the item is not found.
    """
    for item in collection:
        if getattr(item, attr) == value:
            return item


def get_release_file_url(project, series_name, release_version):
    """Return the URL of the release file hosted in Launchpad.

    The returned URL points to a release file for the given project, series
    name and release version.
    The argument *project* is a project object as returned by launchpadlib.
    The arguments *series_name* and *release_version* are strings. If
    *release_version* is None, the URL of the latest release will be returned.
    """
    series = _get_by_attr(project.series, 'name', series_name)
    if series is None:
        raise ValueError('%r: series not found' % series_name)
    # Releases are returned by Launchpad in reverse date order.
    releases = list(series.releases)
    if not releases:
        raise ValueError('%r: series does not contain releases' % series_name)
    if release_version is not None:
        release = _get_by_attr(releases, 'version', release_version)
        if release is None:
            raise ValueError('%r: release not found' % release_version)
        releases = [release]
    for release in releases:
        for file_ in release.files:
            if str(file_).endswith('.tgz'):
                return file_.file_link
    raise ValueError('%r: file not found' % release_version)


def get_zookeeper_address(agent_file_path):
    """Retrieve the Zookeeper address contained in the given *agent_file_path*.

    The *agent_file_path* is a path to a file containing a line similar to the
    following::

        env JUJU_ZOOKEEPER="address"
    """
    line = search_file('JUJU_ZOOKEEPER', agent_file_path).strip()
    return line.split('=')[1].strip('"')


@contextmanager
def log_hook():
    """Log when a hook starts and stops its execution.

    Also log to stdout possible CalledProcessError exceptions raised executing
    the hook.
    """
    script = script_name()
    log(">>> Entering {}".format(script))
    try:
        yield
    except CalledProcessError as err:
        log('Exception caught:')
        log(err.output)
        raise
    finally:
        log("<<< Exiting {}".format(script))


def parse_source(source):
    """Parse the ``juju-gui-source`` option.

    Return a tuple of two elements representing info on how to deploy Juju GUI.
    Examples:
       - ('stable', None): latest stable release;
       - ('stable', '0.1.0'): stable release v0.1.0;
       - ('trunk', None): latest trunk release;
       - ('trunk', '0.1.0+build.1'): trunk release v0.1.0 bzr revision 1;
       - ('branch', 'lp:juju-gui'): release is made from a branch;
       - ('url', 'http://example.com/gui'): release from a downloaded file.
    """
    if source.startswith('url:'):
        source = source[4:]
        # Support file paths, including relative paths.
        if urlparse(source).scheme == '':
            if not source.startswith('/'):
                source = os.path.join(os.path.abspath(CURRENT_DIR), source)
            source = "file://%s" % source
        return 'url', source
    if source in ('stable', 'trunk'):
        return source, None
    if source.startswith('lp:') or source.startswith('http://'):
        return 'branch', source
    if 'build' in source:
        return 'trunk', source
    return 'stable', source


def render_to_file(template_name, context, destination):
    """Render the given *template_name* into *destination* using *context*.

    The tempita template language is used to render contents
    (see http://pythonpaste.org/tempita/).
    The argument *template_name* is the name or path of the template file:
    it may be either a path relative to ``../config`` or an absolute path.
    The argument *destination* is a file path.
    The argument *context* is a dict-like object.
    """
    template_path = os.path.abspath(template_name)
    template = tempita.Template.from_filename(template_path)
    with open(destination, 'w') as stream:
        stream.write(template.substitute(context))


results_log = None


def _setupLogging():
    global results_log
    if results_log is not None:
        return
    cfg = config()
    logging.basicConfig(
        filename=cfg['command-log-file'],
        level=logging.INFO,
        format="%(asctime)s: %(name)s@%(levelname)s %(message)s")
    results_log = logging.getLogger('juju-gui')


def cmd_log(results):
    global results_log
    if not results:
        return
    if results_log is None:
        _setupLogging()
    # Since 'results' may be multi-line output, start it on a separate line
    # from the logger timestamp, etc.
    results_log.info('\n' + results)


def start_improv(staging_env, ssl_cert_path,
                 config_path='/etc/init/juju-api-improv.conf'):
    """Start a simulated juju environment using ``improv.py``."""
    log('Setting up staging start up script.')
    context = {
        'juju_dir': JUJU_DIR,
        'keys': ssl_cert_path,
        'port': API_PORT,
        'staging_env': staging_env,
    }
    render_to_file('config/juju-api-improv.conf.template', context, config_path)
    log('Starting the staging backend.')
    with su('root'):
        service_start(IMPROV)


def start_agent(
        ssl_cert_path, config_path='/etc/init/juju-api-agent.conf',
        read_only=False):
    """Start the Juju agent and connect to the current environment."""
    # Retrieve the Zookeeper address from the start up script.
    unit_dir = os.path.realpath(os.path.join(CURRENT_DIR, '..'))
    agent_file = '/etc/init/juju-{0}.conf'.format(os.path.basename(unit_dir))
    zookeeper = get_zookeeper_address(agent_file)
    log('Setting up API agent start up script.')
    context = {
        'juju_dir': JUJU_DIR,
        'keys': ssl_cert_path,
        'port': API_PORT,
        'zookeeper': zookeeper,
        'read_only': read_only
    }
    render_to_file('config/juju-api-agent.conf.template', context, config_path)
    log('Starting API agent.')
    with su('root'):
        service_start(AGENT)


def start_gui(
        console_enabled, login_help, readonly, in_staging, ssl_cert_path,
        charmworld_url, serve_tests, haproxy_path='/etc/haproxy/haproxy.cfg',
        config_js_path=None, secure=True, sandbox=False):
    """Set up and start the Juju GUI server."""
    with su('root'):
        run('chown', '-R', 'ubuntu:', JUJU_GUI_DIR)
    # XXX 2013-02-05 frankban bug=1116320:
        # External insecure resources are still loaded when testing in the
        # debug environment. For now, switch to the production environment if
        # the charm is configured to serve tests.
    if in_staging and not serve_tests:
        build_dirname = 'build-debug'
    else:
        build_dirname = 'build-prod'
    build_dir = os.path.join(JUJU_GUI_DIR, build_dirname)
    log('Generating the Juju GUI configuration file.')
    is_legacy_juju = legacy_juju()
    user, password = None, None
    if (is_legacy_juju and in_staging) or sandbox:
        user, password = 'admin', 'admin'
    else:
        user, password = None, None

    api_backend = 'python' if is_legacy_juju else 'go'
    if secure:
        protocol = 'wss'
    else:
        log('Running in insecure mode! Port 80 will serve unencrypted.')
        protocol = 'ws'

    context = {
        'raw_protocol': protocol,
        'address': unit_get('public-address'),
        'console_enabled': json.dumps(console_enabled),
        'login_help': json.dumps(login_help),
        'password': json.dumps(password),
        'api_backend': json.dumps(api_backend),
        'readonly': json.dumps(readonly),
        'user': json.dumps(user),
        'protocol': json.dumps(protocol),
        'sandbox': json.dumps(sandbox),
        'charmworld_url': json.dumps(charmworld_url),
    }
    if config_js_path is None:
        config_js_path = os.path.join(
            build_dir, 'juju-ui', 'assets', 'config.js')
    render_to_file('config/config.js.template', context, config_js_path)

    write_apache_config(build_dir, serve_tests)

    log('Generating haproxy configuration file.')
    if is_legacy_juju:
        # The PyJuju API agent is listening on localhost.
        api_address = '127.0.0.1:{0}'.format(API_PORT)
    else:
        # Retrieve the juju-core API server address.
        api_address = get_api_address(os.path.join(CURRENT_DIR, '..'))
    context = {
        'api_address': api_address,
        'api_pem': JUJU_PEM,
        'legacy_juju': is_legacy_juju,
        'ssl_cert_path': ssl_cert_path,
        # In PyJuju environments, use the same certificate for both HTTPS and
        # WebSocket connections. In juju-core the system already has the proper
        # certificate installed.
        'web_pem': JUJU_PEM,
        'web_port': WEB_PORT,
        'secure': secure
    }
    render_to_file('config/haproxy.cfg.template', context, haproxy_path)
    log('Starting Juju GUI.')


def write_apache_config(build_dir, serve_tests=False):
    log('Generating the apache site configuration file.')
    context = {
        'port': WEB_PORT,
        'serve_tests': serve_tests,
        'server_root': build_dir,
        'tests_root': os.path.join(JUJU_GUI_DIR, 'test', ''),
    }
    render_to_file('config/apache-ports.template', context, JUJU_GUI_PORTS)
    render_to_file('config/apache-site.template', context, JUJU_GUI_SITE)


def get_npm_cache_archive_url(Launchpad=Launchpad):
    """Figure out the URL of the most recent NPM cache archive on Launchpad."""
    launchpad = Launchpad.login_anonymously('Juju GUI charm', 'production')
    project = launchpad.projects['juju-gui']
    # Find the URL of the most recently created NPM cache archive.
    npm_cache_url = get_release_file_url(project, 'npm-cache', None)
    return npm_cache_url


def prime_npm_cache(npm_cache_url):
    """Download NPM cache archive and prime the NPM cache with it."""
    # Download the cache archive and then uncompress it into the NPM cache.
    npm_cache_archive = os.path.join(CURRENT_DIR, 'npm-cache.tgz')
    cmd_log(run('curl', '-L', '-o', npm_cache_archive, npm_cache_url))
    npm_cache_dir = os.path.expanduser('~/.npm')
    # The NPM cache directory probably does not exist, so make it if not.
    try:
        os.mkdir(npm_cache_dir)
    except OSError, e:
        # If the directory already exists then ignore the error.
        if e.errno != errno.EEXIST:  # File exists.
            raise
    uncompress = command('tar', '-x', '-z', '-C', npm_cache_dir, '-f')
    cmd_log(uncompress(npm_cache_archive))


def fetch_gui(juju_gui_source, logpath):
    """Retrieve the Juju GUI release/branch."""
    # Retrieve a Juju GUI release.
    origin, version_or_branch = parse_source(juju_gui_source)
    if origin == 'branch':
        # Make sure we have the dependencies necessary for us to actually make
        # a build.
        _get_build_dependencies()
        # Create a release starting from a branch.
        juju_gui_source_dir = os.path.join(CURRENT_DIR, 'juju-gui-source')
        log('Retrieving Juju GUI source checkout from %s.' % version_or_branch)
        cmd_log(run('rm', '-rf', juju_gui_source_dir))
        cmd_log(bzr_checkout(version_or_branch, juju_gui_source_dir))
        log('Preparing a Juju GUI release.')
        logdir = os.path.dirname(logpath)
        fd, name = tempfile.mkstemp(prefix='make-distfile-', dir=logdir)
        log('Output from "make distfile" sent to %s' % name)
        with environ(NO_BZR='1'):
            run('make', '-C', juju_gui_source_dir, 'distfile',
                stdout=fd, stderr=fd)
        release_tarball = first_path_in_dir(
            os.path.join(juju_gui_source_dir, 'releases'))
    else:
        log('Retrieving Juju GUI release.')
        if origin == 'url':
            file_url = version_or_branch
        else:
            # Retrieve a release from Launchpad.
            launchpad = Launchpad.login_anonymously(
                'Juju GUI charm', 'production')
            project = launchpad.projects['juju-gui']
            file_url = get_release_file_url(project, origin, version_or_branch)
        log('Downloading release file from %s.' % file_url)
        release_tarball = os.path.join(CURRENT_DIR, 'release.tgz')
        cmd_log(run('curl', '-L', '-o', release_tarball, file_url))
    return release_tarball


def fetch_api(juju_api_branch):
    """Retrieve the Juju branch."""
    # Retrieve Juju API source checkout.
    log('Retrieving Juju API source checkout.')
    cmd_log(run('rm', '-rf', JUJU_DIR))
    cmd_log(bzr_checkout(juju_api_branch, JUJU_DIR))


def setup_gui(release_tarball):
    """Set up Juju GUI."""
    # Uncompress the release tarball.
    log('Installing Juju GUI.')
    release_dir = os.path.join(CURRENT_DIR, 'release')
    cmd_log(run('rm', '-rf', release_dir))
    os.mkdir(release_dir)
    uncompress = command('tar', '-x', '-z', '-C', release_dir, '-f')
    cmd_log(uncompress(release_tarball))
    # Link the Juju GUI dir to the contents of the release tarball.
    cmd_log(run('ln', '-sf', first_path_in_dir(release_dir), JUJU_GUI_DIR))


def setup_apache():
    """Set up apache."""
    log('Setting up apache.')
    if not os.path.exists(JUJU_GUI_SITE):
        cmd_log(run('touch', JUJU_GUI_SITE))
        cmd_log(run('chown', 'ubuntu:', JUJU_GUI_SITE))
        cmd_log(
            run('ln', '-s', JUJU_GUI_SITE,
                '/etc/apache2/sites-enabled/juju-gui'))

    if not os.path.exists(JUJU_GUI_PORTS):
        cmd_log(run('touch', JUJU_GUI_PORTS))
        cmd_log(run('chown', 'ubuntu:', JUJU_GUI_PORTS))

    with su('root'):
        run('a2dissite', 'default')
        run('a2ensite', 'juju-gui')


def save_or_create_certificates(
        ssl_cert_path, ssl_cert_contents, ssl_key_contents):
    """Generate the SSL certificates.

    If both *ssl_cert_contents* and *ssl_key_contents* are provided, use them
    as certificates; otherwise, generate them.

    Also create a pem file, suitable for use in the haproxy configuration,
    concatenating the key and the certificate files.
    """
    crt_path = os.path.join(ssl_cert_path, 'juju.crt')
    key_path = os.path.join(ssl_cert_path, 'juju.key')
    if not os.path.exists(ssl_cert_path):
        os.makedirs(ssl_cert_path)
    if ssl_cert_contents and ssl_key_contents:
        # Save the provided certificates.
        with open(crt_path, 'w') as cert_file:
            cert_file.write(ssl_cert_contents)
        with open(key_path, 'w') as key_file:
            key_file.write(ssl_key_contents)
    else:
        # Generate certificates.
        # See http://superuser.com/questions/226192/openssl-without-prompt
        cmd_log(run(
            'openssl', 'req', '-new', '-newkey', 'rsa:4096',
            '-days', '365', '-nodes', '-x509', '-subj',
            # These are arbitrary test values for the certificate.
            '/C=GB/ST=Juju/L=GUI/O=Ubuntu/CN=juju.ubuntu.com',
            '-keyout', key_path, '-out', crt_path))
    # Generate the pem file.
    pem_path = os.path.join(ssl_cert_path, JUJU_PEM)
    if os.path.exists(pem_path):
        os.remove(pem_path)
    with open(pem_path, 'w') as pem_file:
        shutil.copyfileobj(open(key_path), pem_file)
        shutil.copyfileobj(open(crt_path), pem_file)


def find_missing_packages(*packages):
    """Given a list of packages, return the packages which are not installed.
    """
    cache = apt.Cache()
    missing = set()
    for pkg_name in packages:
        try:
            pkg = cache[pkg_name]
        except KeyError:
            missing.add(pkg_name)
            continue
        if pkg.is_installed:
            continue
        missing.add(pkg_name)
    return missing


## Backend support decorators

def chain(name):
    """Helper method to compose a set of mixin objects into a callable.

    Each method is called in the context of its mixin instance, and its
    argument is the Backend instance.
    """
    # Chain method calls through all implementing mixins.
    def method(self):
        for mixin in self.mixins:
            a_callable = getattr(type(mixin), name, None)
            if a_callable:
                a_callable(mixin, self)

    method.__name__ = name
    return method


def merge(name):
    """Helper to merge a property from a set of strategy objects
    into a unified set.
    """
    # Return merged property from every providing mixin as a set.
    @property
    def method(self):
        result = set()
        for mixin in self.mixins:
            segment = getattr(type(mixin), name, None)
            if segment and isinstance(segment, (list, tuple, set)):
                result |= set(segment)

        return result
    return method
