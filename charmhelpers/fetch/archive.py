import os
import urllib2
from charmhelpers.fetch import (
    BaseFetchHandler,
    UnhandledSource
)
from charmhelpers import fileutils


class UrlArchiveFetchHandler(BaseFetchHandler):
    """Handler for archives via generic URLs"""
    def can_handle(self, source):
        url_parts = self.parse_url(source)
        if url_parts.scheme not in ('http', 'https', 'ftp', 'file'):
            return "Wrong source type"
        if fileutils.get_archive_handler(self.base_url(source)):
            return True
        return False

    def download(self, source, dest):
        # propogate all exceptions
        # URLError, OSError, etc
        response = urllib2.urlopen(source)
        with open(dest, 'w') as dest_file:
            dest_file.write(response.read())

    def install(self, source):
        url_parts = self.parse_url(source)
        dest_dir = os.path.join(os.environ.get('CHARM_DIR'), 'fetched')
        dest_file = os.path.join(dest_dir, os.path.basename(url_parts.path))
        try:
            self.download(source, dest_file)
        except urllib2.URLError as e:
            return UnhandledSource(e.reason)
        except OSError as e:
            return UnhandledSource(e.strerror)
        finally:
            if os.path.isfile(dest_file):
                os.unlink(dest_file)
        return fileutils.extract(dest_file)
