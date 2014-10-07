import os
from charmhelpers.fetch import (
    BaseFetchHandler,
    UnhandledSource
)
from charmhelpers.core.host import mkdir

try:
    from git import Repo
except ImportError:
    from charmhelpers.fetch import apt_install
    apt_install("python-git")
    from git import Repo


class GitUrlFetchHandler(BaseFetchHandler):
    """Handler for git branches via generic and github URLs"""
    def can_handle(self, source):
        url_parts = self.parse_url(source)
        if url_parts.scheme not in ('git'):
            return False
        else:
            return True

    def branch(self, source, dest):
        url_parts = self.parse_url(source)
        # If we use lp:branchname scheme we need to load plugins
        if not self.can_handle(source):
            raise UnhandledSource("Cannot handle {}".format(source))
        try:
            repo = Repo(source)
            if repo.bare:
                raise UnhandledSource("Source is bare {}".format(source))
            repo.open(dest)
        except Exception as e:
            raise e

    def install(self, source):
        url_parts = self.parse_url(source)
        branch_name = url_parts.path.strip("/").split("/")[-1]
        dest_dir = os.path.join(os.environ.get('CHARM_DIR'), "fetched",
                                branch_name)
        if not os.path.exists(dest_dir):
            mkdir(dest_dir, perms=0755)
        try:
            self.branch(source, dest_dir)
        except OSError as e:
            raise UnhandledSource(e.strerror)
        return dest_dir
