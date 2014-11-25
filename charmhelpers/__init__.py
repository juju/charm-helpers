# Bootstrap charm-helpers, installing its dependencies if necessary using
# only standard libraries.
try:
    import six  # flake8: noqa
except ImportError:
    import subprocess
    import sys
    if sys.version_info.major == 2:
        subprocess.check_call(['apt-get', 'install', '-y', 'python-six'])
    else:
        subprocess.check_call(['apt-get', 'install', '-y', 'python3-six'])
    import six  # flake8: noqa
