from __future__ import print_function

import os
from unittest import mock
from shutil import rmtree
import unittest

from pysftpserver.urlrequesthook import UrlRequestHook
from pysftpserver.server import (SSH2_FILEXFER_ATTR_ACMODTIME,
                                 SSH2_FILEXFER_ATTR_PERMISSIONS,
                                 SSH2_FILEXFER_ATTR_SIZE, SSH2_FXF_CREAT,
                                 SSH2_FXF_READ, SSH2_FXF_WRITE, SSH2_FXP_CLOSE,
                                 SSH2_FXP_FSETSTAT, SSH2_FXP_FSTAT,
                                 SSH2_FXP_INIT, SSH2_FXP_LSTAT, SSH2_FXP_MKDIR,
                                 SSH2_FXP_OPEN, SSH2_FXP_OPENDIR,
                                 SSH2_FXP_READ, SSH2_FXP_READDIR,
                                 SSH2_FXP_READLINK, SSH2_FXP_REALPATH,
                                 SSH2_FXP_REMOVE, SSH2_FXP_RENAME,
                                 SSH2_FXP_RMDIR, SSH2_FXP_SETSTAT,
                                 SSH2_FXP_STAT, SSH2_FXP_SYMLINK,
                                 SSH2_FXP_WRITE, SFTPServer)
from pysftpserver.storage import SFTPServerStorage
from pysftpserver.tests.utils import (get_sftphandle, sftpcmd, sftpint,
                                      sftpint64, sftpstring, t_path)


class ServerTest(unittest.TestCase):

    def setUp(self):
        os.chdir(t_path())
        self.home = 'home'
        if not os.path.isdir(self.home):
            os.mkdir(self.home)
        self.server = SFTPServer(
            SFTPServerStorage(self.home),
            hook=UrlRequestHook('test_url'),
            logfile=t_path('log'),
            raise_on_error=True
        )

    def tearDown(self):
        os.chdir(t_path())
        rmtree(self.home)

    @classmethod
    def tearDownClass(cls):
        os.unlink(t_path('log'))  # comment me to see the log!
        rmtree(t_path('home'), ignore_errors=True)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_init(self, mock_request):
        self.server.input_queue = sftpcmd(
            SSH2_FXP_INIT, sftpint(2), sftpint(0))
        self.server.process()
        mock_request.assert_called_once_with(
            'POST', 'test_url/init', data={'method': 'init'})

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_realpath(self, mock_request):
        """Additionally tests multiple urls and no path."""
        self.server.hook = UrlRequestHook(
            'test_url',
            urls_mapping={
                'realpath': ['test_url_1', 'test_url_2']},
            paths_mapping={
                'realpath': ''})
        filename = b'services'
        flags = SSH2_FXF_CREAT | SSH2_FXF_WRITE
        perm = 0o100600
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(flags),
            sftpint(SSH2_FILEXFER_ATTR_PERMISSIONS),
            sftpint(perm),
        )
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_REALPATH,
                                          sftpstring(filename))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.call(
                'POST', 'test_url_1/',
                data={'method': 'realpath', 'filename': filename}),
            mock.call(
                'POST', 'test_url_2/',
                data={'method': 'realpath', 'filename': filename}),
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_stat(self, mock_request):
        """Additionally tests multiple urls."""
        self.server.hook = UrlRequestHook(
            'test_url',
            urls_mapping={
                'stat': ['test_url_1', 'test_url_2']})
        filename = b'services'
        with open('/etc/services') as f:
            with open(filename, 'a') as f_bis:
                f_bis.write(f.read())
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_STAT, sftpstring(filename))
        self.server.process()
        mock_request.assert_has_calls([
            mock.call(
                'POST', 'test_url_1/stat',
                data={'method': 'stat', 'filename': filename}),
            mock.call(
                'POST', 'test_url_2/stat',
                data={'method': 'stat', 'filename': filename}),
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_lstat(self, mock_request):
        """Additionally tests skipping mapping for different server action."""
        self.server.hook = UrlRequestHook(
            'test_url',
            urls_mapping={
                'open': ['test_url_1', 'test_url_2']})
        linkname = b'link'
        os.symlink('foo', linkname)
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_LSTAT, sftpstring(linkname))
        self.server.process()
        mock_request.assert_called_once_with(
            'POST', 'test_url/lstat',
            data={'method': 'lstat', 'filename': linkname})
        os.unlink(linkname)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_fstat(self, mock_request):
        filename = b'services'
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(SSH2_FXF_CREAT),
            sftpint(0)
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_FSTAT, sftpstring(handle))
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.call(
                'POST', 'test_url/fstat',
                data={'method': 'fstat', 'filename': filename}),
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_setstat(self, mock_request):
        filename = b'services'
        attrs = {
            b'size': 10**2,
            b'perm': 0o100600,
            b'atime': 1415626110,
            b'mtime': 1415626120,
        }
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(SSH2_FXF_CREAT | SSH2_FXF_WRITE),
            sftpint(0)
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        etc_services = open('/etc/services', 'rb').read()
        self.server.input_queue = sftpcmd(
            SSH2_FXP_WRITE,
            sftpstring(handle),
            sftpint64(0),
            sftpstring(etc_services)
        )
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(
            SSH2_FXP_SETSTAT,
            sftpstring(filename),
            sftpint(
                SSH2_FILEXFER_ATTR_SIZE |
                SSH2_FILEXFER_ATTR_PERMISSIONS |
                SSH2_FILEXFER_ATTR_ACMODTIME
            ),
            sftpint64(attrs[b'size']),
            sftpint(attrs[b'perm']),
            sftpint(attrs[b'atime']),
            sftpint(attrs[b'mtime']),
        )
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.ANY,  # write
            mock.call(
                'POST', 'test_url/setstat',
                data={
                    'method': 'setstat', 'filename': filename,
                    'attrs': attrs}),
            mock.ANY,  # close
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_fsetstat(self, mock_request):
        filename = b'services'
        attrs = {
            b'size': 10**2,
            b'perm': 0o100600,
            b'atime': 1415626110,
            b'mtime': 1415626120,
        }
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(SSH2_FXF_CREAT | SSH2_FXF_WRITE),
            sftpint(0)
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        etc_services = open('/etc/services', 'rb').read()
        self.server.input_queue = sftpcmd(
            SSH2_FXP_WRITE,
            sftpstring(handle),
            sftpint64(0),
            sftpstring(etc_services)
        )
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(
            SSH2_FXP_FSETSTAT,
            sftpstring(handle),
            sftpint(
                SSH2_FILEXFER_ATTR_SIZE |
                SSH2_FILEXFER_ATTR_PERMISSIONS |
                SSH2_FILEXFER_ATTR_ACMODTIME
            ),
            sftpint64(attrs[b'size']),
            sftpint(attrs[b'perm']),
            sftpint(attrs[b'atime']),
            sftpint(attrs[b'mtime']),
        )
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.ANY,  # write
            mock.call(
                'POST', 'test_url/fsetstat',
                data={
                    'method': 'fsetstat', 'filename': filename,
                    'attrs': attrs}),
            mock.ANY,  # close
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_opendir(self, mock_request):
        """Additionally tests single url and multiple paths."""
        self.server.hook = UrlRequestHook(
            'test_url',
            paths_mapping={
                'opendir': ['test_path_1', 'test_path_2', 'test_path_3']})
        dirname = b'foo'
        os.mkdir(dirname)
        self.server.input_queue = sftpcmd(SSH2_FXP_OPENDIR,
                                          sftpstring(dirname))
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.call(
                'POST', 'test_url/test_path_1',
                data={'method': 'opendir', 'filename': dirname}),
            mock.call(
                'POST', 'test_url/test_path_2',
                data={'method': 'opendir', 'filename': dirname}),
            mock.call(
                'POST', 'test_url/test_path_3',
                data={'method': 'opendir', 'filename': dirname}),
            mock.ANY,  # close
        ])
        rmtree(dirname)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_readdir(self, mock_request):
        dirname = b'foo'
        os.mkdir(dirname)
        self.server.input_queue = sftpcmd(SSH2_FXP_OPENDIR,
                                          sftpstring(dirname))
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_READDIR, sftpstring(handle))
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # opendir
            mock.call(
                'POST', 'test_url/readdir',
                data={'method': 'readdir', 'filename': dirname}),
            mock.ANY,  # close
        ])
        os.rmdir(dirname)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_close(self, mock_request):
        filename = b'services'
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(SSH2_FXF_CREAT | SSH2_FXF_WRITE),
            sftpint(0),
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.call(
                'POST', 'test_url/close',
                data={'method': 'close', 'filename': filename}),
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_open(self, mock_request):
        filename = b'services'
        flags = SSH2_FXF_CREAT | SSH2_FXF_WRITE
        perm = 0o100600
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(flags),
            sftpint(SSH2_FILEXFER_ATTR_PERMISSIONS),
            sftpint(perm),
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.call(
                'POST', 'test_url/open',
                data={
                    'method': 'open', 'filename': filename,
                    'flags': self.server.get_explicit_flags(flags),
                    'attrs': {b'perm': perm}}),
            mock.ANY,  # close
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_read(self, mock_request):
        filename = b'services'
        read_offset = 2
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(SSH2_FXF_CREAT | SSH2_FXF_WRITE | SSH2_FXF_READ),
            sftpint(SSH2_FILEXFER_ATTR_PERMISSIONS),
            sftpint(0o644),
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        chunk = open('/etc/services', 'rb').read()
        size = (os.lstat('/etc/services').st_size)
        self.server.input_queue = sftpcmd(
            SSH2_FXP_WRITE,
            sftpstring(handle),
            sftpint64(0),
            sftpstring(chunk),
        )
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(
            SSH2_FXP_READ,
            sftpstring(handle),
            sftpint64(read_offset),
            sftpint(size),
        )
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.ANY,  # write
            mock.call(
                'POST', 'test_url/read',
                data={
                    'method': 'read', 'filename': filename,
                    'offset': read_offset, 'size': size}),
            mock.ANY,  # close
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_write(self, mock_request):
        filename = b'services'
        write_offset = 5
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(SSH2_FXF_CREAT | SSH2_FXF_WRITE | SSH2_FXF_READ),
            sftpint(SSH2_FILEXFER_ATTR_PERMISSIONS),
            sftpint(0o644),
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        chunk = open('/etc/services', 'rb').read()
        self.server.input_queue = sftpcmd(
            SSH2_FXP_WRITE,
            sftpstring(handle),
            sftpint64(write_offset),
            sftpstring(chunk),
        )
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.call(
                'POST', 'test_url/write',
                data={
                    'method': 'write', 'filename': filename,
                    'offset': write_offset, 'chunk': chunk}),
            mock.ANY,  # close
        ])
        os.unlink(filename)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_mkdir(self, mock_request):
        """Additionally tests no path."""
        self.server.hook = UrlRequestHook(
            'test_url',
            paths_mapping={
                'mkdir': ''})
        dirname = b'foo'
        # sftpint(0) means no attrs
        self.server.input_queue = sftpcmd(
            SSH2_FXP_MKDIR, sftpstring(dirname), sftpint(0))
        self.server.process()
        mock_request.assert_called_once_with(
            'POST', 'test_url/',
            data={'method': 'mkdir', 'filename': dirname, 'attrs': dict()})
        os.rmdir(dirname)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_rmdir(self, mock_request):
        dirname = b'foo'
        # sftpint(0) means no attrs
        self.server.input_queue = sftpcmd(
            SSH2_FXP_MKDIR, sftpstring(dirname), sftpint(0))
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_RMDIR, sftpstring(dirname))
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # mkdir
            mock.call(
                'POST', 'test_url/rmdir',
                data={'method': 'rmdir', 'filename': dirname}),
        ])

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_rm(self, mock_request):
        filename = b'services'
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(filename),
            sftpint(SSH2_FXF_CREAT | SSH2_FXF_WRITE),
            sftpint(SSH2_FILEXFER_ATTR_PERMISSIONS),
            sftpint(0o644)
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(
            SSH2_FXP_REMOVE,
            sftpstring(filename),
            sftpint(0)
        )
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.ANY,  # close
            mock.call(
                'POST', 'test_url/rm',
                data={'method': 'rm', 'filename': filename}),
        ])

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_rename(self, mock_request):
        oldpath = b'services'
        newpath = b'other_services'
        self.server.input_queue = sftpcmd(
            SSH2_FXP_OPEN,
            sftpstring(oldpath),
            sftpint(SSH2_FXF_CREAT | SSH2_FXF_WRITE),
            sftpint(SSH2_FILEXFER_ATTR_PERMISSIONS),
            sftpint(0o644)
        )
        self.server.process()
        handle = get_sftphandle(self.server.output_queue)
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(SSH2_FXP_CLOSE, sftpstring(handle))
        self.server.process()
        self.server.output_queue = b''
        self.server.input_queue = sftpcmd(
            SSH2_FXP_RENAME,
            sftpstring(oldpath),
            sftpstring(newpath),
        )
        self.server.process()
        mock_request.assert_has_calls([
            mock.ANY,  # open
            mock.ANY,  # close
            mock.call(
                'POST', 'test_url/rename',
                data={
                    'method': 'rename', 'oldpath': oldpath,
                    'newpath': newpath}),
        ])
        os.unlink(newpath)

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_symlink(self, mock_request):
        """Additionally tests GET method."""
        self.server.hook = UrlRequestHook('test_url', request_method='GET')
        linkpath = b'ugly'
        targetpath = b'ugliest'
        self.server.input_queue = sftpcmd(
            SSH2_FXP_SYMLINK, sftpstring(linkpath), sftpstring(targetpath),
            sftpint(0))
        self.server.process()
        mock_request.assert_called_once_with(
            'GET', 'test_url/symlink',
            data={
                'method': 'symlink', 'linkpath': linkpath,
                'targetpath': targetpath})

    @mock.patch('pysftpserver.urlrequesthook.request')
    def test_readlink(self, mock_request):
        """Additionally tests multiple urls and multiple paths."""
        self.server.hook = UrlRequestHook(
            'test_url',
            urls_mapping={
                'readlink': ['test_url_1', 'test_url_2']},
            paths_mapping={
                'readlink': ['test_path_1', 'test_path_2']})
        linkpath = b'ugly'
        targetpath = b'ugliest'
        os.symlink(linkpath, targetpath)
        self.server.input_queue = sftpcmd(
            SSH2_FXP_READLINK, sftpstring(targetpath), sftpint(0))
        self.server.process()
        mock_request.assert_has_calls([
            mock.call(
                'POST', 'test_url_1/test_path_1',
                data={'method': 'readlink', 'filename': targetpath}),
            mock.call(
                'POST', 'test_url_1/test_path_2',
                data={'method': 'readlink', 'filename': targetpath}),
            mock.call(
                'POST', 'test_url_2/test_path_1',
                data={'method': 'readlink', 'filename': targetpath}),
            mock.call(
                'POST', 'test_url_2/test_path_2',
                data={'method': 'readlink', 'filename': targetpath}),
        ])


if __name__ == '__main__':
    unittest.main()
