"""This module defines a subclass of SftpHook whose methods perform a HTTP
request (e.g. to communicate with a web API)."""

from collections import Iterable
import logging
from six import string_types
import os

from requests import request

from pysftpserver.hook import SftpHook


class UrlRequestHook(SftpHook):
    """A SftpHook whose methods send a request to a specific url, containing
    the called method name and attributes.

    In principle, each method of the hook may call a different set of urls,
    which is obtained combining a list of base urls with a list of optional
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
        request_auth (see notes): The request method to use.
        urls_mapping (dict): Map hook method names with custom base urls.
        paths_mapping (dict): Map hook method names with optional paths.

    Notes:
    - request_auth: this is passed as it is to the request, for further
      reference see "Custom Authentication" section of
      http://docs.python-requests.org/en/master/user/advanced/
    """

    def __init__(self, request_url, request_method='POST', request_auth=None,
                 logfile=None, urls_mapping=None, paths_mapping=None,
                 extra_data=None, *args, **kwargs):
        self.request_url = request_url
        self.request_method = request_method
        self.request_auth = request_auth
        self.urls_mapping = urls_mapping or dict()
        self.paths_mapping = paths_mapping or dict()
        self.extra_data = extra_data if extra_data else {}
        if logfile:
            log_handler = logging.FileHandler(logfile)
            log_handler.setLevel(logging.DEBUG)
            log_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s: %(message)s')
            log_handler.setFormatter(log_formatter)
            self.logger = logging.getLogger('url_request_hook_log')
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(log_handler)
        else:
            self.logger = None
        super(UrlRequestHook, self).__init__(*args, **kwargs)

    def get_urls(self, method_name):
        """Build a set of urls to call for a given method name, combining
        values from urls_mapping and paths_mapping.

        Args:
            method_name (str): The value to use as key in urls_mapping and
                paths_mapping to obtain base urls and optional paths
                respectively.

        Returns:
            (tuple): A tuple of urls.
        """
        base_urls_value = self.urls_mapping.get(method_name, self.request_url)
        base_urls = (
            isinstance(base_urls_value, string_types) and [base_urls_value] or
            base_urls_value)
        paths_value = self.paths_mapping.get(method_name, method_name)
        paths = (
            isinstance(paths_value, string_types) and [paths_value] or
            paths_value)
        return (os.path.join(u, p) for u in base_urls for p in paths)

    def send_requests(self, method_name, data=None):
        """Generate responses by sending requests to the urls associated to a
        given hook method.

        Args:
            method_name (str): The name of the hook method used to get urls.

        Optional Args:
            data (dict): Data to send along with the request.

        Yields:
            (Response): An instance of requests Response.
        """
        data = data if data else {}
        data.update(self.extra_data)
        data['method'] = method_name
        urls = self.get_urls(method_name)
        for url in urls:
            if self.logger:
                self.logger.info(
                    '"{}" executed. Sending request to {}.'.format(
                        method_name, url))
            try:
                yield request(self.request_method, url, data=data,
                              auth=self.request_auth)
            except Exception as e:
                self.logger.error(
                    'Exception while sending request to {} ({}).'.format(
                        url, e))
                yield

    def init(self, server):
        return list(self.send_requests('init'))

    def realpath(self, server, filename):
        data = {'filename': filename}
        return list(self.send_requests('realpath', data))

    def stat(self, server, filename):
        data = {'filename': filename}
        return list(self.send_requests('stat', data))

    def lstat(self, server, filename):
        data = {'filename': filename}
        return list(self.send_requests('lstat', data))

    def fstat(self, server, handle_id):
        filename, is_dir = server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename}
        return list(self.send_requests('fstat', data))

    def setstat(self, server, filename, attrs):
        data = {'filename': filename, 'attrs': attrs}
        return list(self.send_requests('setstat', data))

    def fsetstat(self, server, handle_id, attrs):
        filename, is_dir = server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename, 'attrs': attrs}
        return list(self.send_requests('fsetstat', data))

    def opendir(self, server, filename):
        data = {'filename': filename}
        return list(self.send_requests('opendir', data))

    def readdir(self, server, handle_id):
        filename, is_dir = server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename}
        return list(self.send_requests('readdir', data))

    def close(self, server, handle_id):
        filename, is_dir = server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename}
        return list(self.send_requests('close', data))

    def open(self, server, filename, flags, attrs):
        data = {'filename': filename, 'attrs': attrs, 'flags': flags}
        return list(self.send_requests('open', data))

    def read(self, server, handle_id, offset, size):
        filename, is_dir = server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename, 'offset': offset, 'size': size}
        return list(self.send_requests('read', data))

    def write(self, server, handle_id, offset):
        filename, is_dir = server.get_filename_from_handle_id(handle_id)
        data = {'filename': filename, 'offset': offset}
        return list(self.send_requests('write', data))

    def mkdir(self, server, filename, attrs):
        data = {'filename': filename, 'attrs': attrs}
        return list(self.send_requests('mkdir', data))

    def rmdir(self, server, filename):
        data = {'filename': filename}
        return list(self.send_requests('rmdir', data))

    def rm(self, server, filename):
        data = {'filename': filename}
        return list(self.send_requests('rm', data))

    def rename(self, server, oldpath, newpath):
        data = {'oldpath': oldpath, 'newpath': newpath}
        return list(self.send_requests('rename', data))

    def symlink(self, server, linkpath, targetpath):
        data = {'linkpath': linkpath, 'targetpath': targetpath}
        return list(self.send_requests('symlink', data))

    def readlink(self, server, filename):
        data = {'filename': filename}
        return list(self.send_requests('readlink', data))
