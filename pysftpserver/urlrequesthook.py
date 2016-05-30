"""This module defines a subclass of SftpHook whose methods perform a HTTP
request (e.g. to communicate with a web API)."""

from collections import Iterable
import logging
import os

from requests import request

from pysftpserver.hook import SftpHook


logger = logging.getLogger('url_request_hook_log')
logger.setLevel(logging.DEBUG)


class UrlRequestHook(SftpHook):
    """A SftpHook whose methods send a request to a specific url, containing
    the called method name and attributes.

    In principle, each method of the hook may call a different set of urls,
    which is obtained combinig a list of base urls with a list of optional
    paths (in all possible ways), according to the following logic:
        - a list of base urls for a given method is searched in the
        urls_mapping dict using the method name as a key, if nothing is found
        it defaults to a list containing only the url provided at init time.
        - a list of optional paths for a given method is searched in the
        paths_mapping dict using the method name as a key, if nothing is found
        it defaults to a list containing only the method name.

    Notes:
    The url attribute and the mapping dicts values can be either lists of
    strings or strings, in the latter case an iterable is created at runtime.
    In case optional paths were not desired for one or more methods, the
    paths_mapping dict should map those method names to empty strings.

    Optional Args:
        logfile (str/bytes): The path of the log file.

    Attributes:
        request_url (str/bytes): The base url to send the request to.
        request_method (str/bytes): The request method to use.
        urls_mapping (dict): Map hook method names with custom base urls.
        paths_mapping (dict): Map hook method names with optional paths.
    """
    urls_mapping = dict()
    paths_mapping = dict()

    def __init__(self, request_url, request_method='POST', logfile=None, *args,
                 **kwargs):
        self.request_url = request_url
        self.request_method = request_method
        if logfile:
            log_handler = logging.FileHandler(logfile)
            log_handler.setLevel(logging.DEBUG)
            log_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s: %(message)s')
            log_handler.setFormatter(log_formatter)
            logger.addHandler(log_handler)
        super().__init__(*args, **kwargs)

    @staticmethod
    def force_to_iterable(value):
        """Force value to iterable according to the following logic:
            - if value is a string (str or bytes), it is returned inside a
                single element tuple;
            - if value is an iterable, it is returned unchanged;
            - if value is neither a string or an iterable, TypeError is raised.

        Note:
            This static method is used to make urls_mapping and paths_mapping
            attributes flexible enough to contain single urls (str or bytes)
            as well as iterables of urls.

        Args:
            value (str or Iterable): The value to force to iterable.

        Returns:
            (Iterable): The output iterable.
        """
        if isinstance(value, (str, bytes)):
            return (value,)
        if isinstance(value, Iterable):
            return value
        raise TypeError('Provided value should be a string or an iterable.')

    def get_urls(self, method_name):
        """Build a set of urls to call for a given method name, combining
        values from urls_mapping and paths_mapping.

        Args:
            method_name (str): The value to use as key in urls_mapping and
                paths_mapping to obtain base urls and optional paths
                respectively.

        Returns:
            (set): A set of urls.
        """
        base_urls = self.force_to_iterable(
            self.urls_mapping.get(method_name, self.request_url))
        paths = self.force_to_iterable(
            self.paths_mapping.get(method_name, method_name))
        return set(os.path.join(u, p) for u in base_urls for p in paths)

    def generate_response(self, method_name, data=None):
        """Generate responses by sending requests to the urls associated to a
        given hook method.

        Args:
            method_name (str): The name of the hook method used to get urls.

        Optional Args:
            data (dict): Added data to send along with the request.

        Yields:
            (Response): An instance of requests Response.
        """
        if data is None:
            data = {}
        data['method'] = method_name
        urls = self.get_urls(method_name)
        for url in urls:
            logger.info('"{}" executed. Sending request to {}.'.format(
                method_name, url))
            yield request(self.method, url, data=data)

    def init(self):
        return list(self.generate_response('init'))

    def realpath(self, filename):
        data = {'filename': filename}
        return list(self.generate_response('realpath', data))

    def stat(self, filename):
        data = {'filename': filename}
        return list(self.generate_response('stat', data))

    def lstat(self, filename):
        data = {'filename': filename}
        return list(self.generate_response('lstat', data))

    def fstat(self, handle_id):
        filename, is_dir = self.server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename}
        return list(self.generate_response('fstat', data))

    def setstat(self, filename, attrs):
        data = {'filename': filename, 'attrs': attrs}
        return list(self.generate_response('setstat', data))

    def fsetstat(self, handle_id, attrs):
        filename, is_dir = self.server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename, 'attrs': attrs}
        return list(self.generate_response('fsetstat', data))

    def opendir(self, filename):
        data = {'filename': filename}
        return list(self.generate_response('opendir', data))

    def readdir(self, handle_id):
        filename, is_dir = self.server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename}
        return list(self.generate_response('readdir', data))

    def close(self, handle_id):
        filename, is_dir = self.server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename}
        return list(self.generate_response('close', data))

    def open(self, filename, flags, attrs):
        data = {'filename': filename, 'attrs': attrs,
                'flags': self.server.get_explicit_flags(flags)}
        return list(self.generate_response('open', data))

    def read(self, handle_id, offset, size):
        filename, is_dir = self.server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename, 'offset': offset, 'size': size}
        return list(self.generate_response('read', data))

    def write(self, handle_id, offset, chunk):
        filename, is_dir = self.server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename, 'offset': offset, 'chunk': chunk}
        return list(self.generate_response('write', data))

    def mkdir(self, filename, attrs):
        data = {'filename': filename, 'attrs': attrs}
        return list(self.generate_response('mkdir', data))

    def rmdir(self, filename):
        data = {'filename': filename}
        return list(self.generate_response('rmdir', data))

    def rm(self, filename):
        data = {'filename': filename}
        return list(self.generate_response('rm', data))

    def rename(self, oldpath, newpath):
        data = {'oldpath': oldpath, 'newpath': newpath}
        return list(self.generate_response('rename', data))

    def symlink(self, linkpath, targetpath):
        data = {'linkpath': linkpath, 'targetpath': targetpath}
        return list(self.generate_response('symlink', data))

    def readlink(self, filename):
        data = {'filename': filename}
        return list(self.generate_response('readlink', data))
