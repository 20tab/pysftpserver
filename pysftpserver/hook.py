"""The SftpHook interface allows to define custom reactions to SftpServer
actions."""


class SftpHook(object):
    """A collection of callbacks hooked to specific methods on the server.

    Each method is named according to the server method to which it is
    hooked.
    """

    def init(self, server):
        pass

    def realpath(self, server, filename):
        pass

    def stat(self, server, filename):
        pass

    def lstat(self, server, filename):
        pass

    def fstat(self, server, handle_id):
        pass

    def setstat(self, server, filename, attrs):
        pass

    def fsetstat(self, server, handle_id, attrs):
        pass

    def opendir(self, server, filename):
        pass

    def readdir(self, server, handle_id):
        pass

    def close(self, server, handle_id):
        pass

    def open(self, server, filename, flags, attrs):
        pass

    def read(self, server, handle_id, offset, size):
        pass

    def write(self, server, handle_id, offset):
        pass

    def mkdir(self, server, filename, attrs):
        pass

    def rmdir(self, server, filename):
        pass

    def rm(self, server, filename):
        pass

    def rename(self, server, oldpath, newpath):
        pass

    def symlink(self, server, linkpath, targetpath):
        pass

    def readlink(self, server, filename):
        pass
