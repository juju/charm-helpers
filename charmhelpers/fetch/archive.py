import os
import urllib2
import tarfile
import zipfile
from charmhelpers.fetch import (
    BaseFetchHandler,
    UnhandledSource
)
from charmhelpers.core import (
    host,
    hookenv
)


class UrlArchiveFetchHandler(BaseFetchHandler):
    """Handler for archives via generic URLs"""
    def can_handle(self, source):
        url_parts = self.parse_url(source)
        if url_parts.scheme not in ('http', 'https', 'ftp', 'file'):
            return "Wrong source type"
        if get_archive_handler(self.base_url(source)):
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
        return extract(dest_file)

class ArchiveError(Exception):
    pass

def get_archive_handler(archive_name):
    if os.path.isfile(archive_name):
        if tarfile.is_tarfile(archive_name):
            return extract_tarfile
        elif zipfile.is_zipfile(archive_name):
            return extract_zipfile
    else:
        # look at the file name
        for ext in ('.tar.gz', '.tgz', 'tar.bz2', '.tbz2', '.tbz'):
            if archive_name.endswith(ext):
                return extract_tarfile
        for ext in ('.zip','.jar'):
            if archive_name.endswith(ext):
                return extract_zipfile

def archive_dest_default(archive_name):
    return os.path.join(hookenv.charm_dir(), "archives", archive_name)


def extract(archive_name, destpath=None):
    handler = get_archive_handler(archive_name)
    if handler:
        if not destpath:
            destpath = archive_dest_default(archive_name)
        if not os.path.isdir(destpath):
            host.mkdir(destpath)
        get_archive_handler(archive_name)(archive_name, destpath)
    else:
        raise ArchiveError("No handler for archive")


def extract_archive(archive_class, archive_name, destpath):
    archive = archive_class(archive_name)
    archive.extract_all(destpath)


def extract_tarfile(archive_name, destpath):
    "Unpack a tar archive, optionally compressed"
    extract_archive(tarfile.TarFile, archive_name, destpath)


def extract_zipfile(archive_name, destpath):
    "Unpack a zip file"
    extract_archive(zipfile.ZipFile, archive_name, destpath)
