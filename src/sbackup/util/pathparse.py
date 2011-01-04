#   Simple Backup - pathname manipulation on string basis
#
#   Copyright (c)2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
"""
:mod:`sbackup.util.pathparse` -- pathname manipulation on string basis
========================================================================

.. module:: pathparse
   :synopsis: pathname manipulation on string basis without file access
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""


import urlparse
import urllib
import datetime
import types


from sbackup.util import log
from sbackup.util import system
from sbackup.util import exceptions


#TODO: Do we need to implement this module per backend?


# uri schemes are used in legacy configuration files
# we distinct between those two because of ssh/sftp
# we use ssh and sftp separate: leave the decision to the users
URI_SCHEME_LOCAL_FILE = 'file'
URI_SCHEME_FTP = 'ftp'
URI_SCHEME_SFTP = 'sftp'
URI_SCHEME_SSH = 'ssh'
# davs support currently disabled due to umount issues
#URI_SCHEME_DAVS = 'davs'
URI_SCHEME_NFS = 'nfs'
URI_SCHEME_SMB = 'smb'


VALID_URI_SCHEMES = [ URI_SCHEME_LOCAL_FILE, URI_SCHEME_FTP, URI_SCHEME_SFTP,
                      URI_SCHEME_SSH, URI_SCHEME_NFS,
                      URI_SCHEME_SMB
#                      URI_SCHEME_DAVS
                    ]

# effective uri schemes are used for actual mount process of remote hosts
URI_SCHEME_EFF_LOCAL_FILE = URI_SCHEME_LOCAL_FILE
URI_SCHEME_EFF_FTP = URI_SCHEME_FTP
#URI_SCHEME_EFF_DAVS = URI_SCHEME_DAVS

URI_SCHEME_EFF_SFTP = URI_SCHEME_SFTP
URI_SCHEME_EFF_SSH = URI_SCHEME_SSH
URI_SCHEME_EFF_NFS = URI_SCHEME_NFS
URI_SCHEME_EFF_SMB = URI_SCHEME_SMB


VALID_EFF_URI_SCHEMES = [ URI_SCHEME_EFF_LOCAL_FILE, URI_SCHEME_EFF_FTP, URI_SCHEME_EFF_SFTP,
                          URI_SCHEME_EFF_SSH, URI_SCHEME_EFF_NFS,
                          URI_SCHEME_EFF_SMB
#                          URI_SCHEME_EFF_DAVS
                        ]

URI_SCHEME_TO_EFF_URI_SCHEME = { URI_SCHEME_LOCAL_FILE : URI_SCHEME_EFF_LOCAL_FILE,
                                 URI_SCHEME_FTP : URI_SCHEME_EFF_FTP,
                                 URI_SCHEME_SFTP : URI_SCHEME_EFF_SFTP,
                                 URI_SCHEME_SSH : URI_SCHEME_EFF_SSH,
                                 URI_SCHEME_NFS : URI_SCHEME_EFF_NFS,
                                 URI_SCHEME_SMB : URI_SCHEME_EFF_SMB
#                                 URI_SCHEME_DAVS : URI_SCHEME_EFF_DAVS
                               }


class UriParser(object):
    def __init__(self):
        # the full destination uri i.e. uri scheme + server + path/directory as originally given
        self.__uri = ""
        self.__uri_scheme = "file"
        self.__eff_scheme = ""
        self.__hostname = ""
        self.__path = ""
        self.__port = None
        self.__username = None
        self.__password = None
        self.__clear()

    @property
    def uri(self):
        return self.__uri

    @property
    def uri_scheme(self):
        """Get current URI scheme retrieved from given URI. This is not the effective scheme."""
        return self.__uri_scheme

    @property
    def hostname(self):
        return self.__hostname

    @property
    def path(self):
        return self.__path

    @property
    def port(self):
        _port = self.__port
        if _port is None:
            _port = ""
        return str(_port)

    @property
    def username(self):
        _user = self.__username
        if _user is None:
            _user = ""
        return _user

    @property
    def password(self):
        _pass = self.__password
        if _pass is None:
            _pass = ""
        return _pass

    def __clear(self):
        self.__uri = ""
        self.__uri_scheme = "file"
        self.__eff_scheme = ""
        self.__hostname = ""
        self.__path = ""
        self.__port = None
        self.__username = None
        self.__password = None

    def __str__(self):
        if self.__password is None:
            _pass = "None"
        else:
            _pass = "*" * len(self.__password)
        _res = [ #"URI: `%s`" % self.__uri,
                 "Display name: %s" % self.query_display_name(),
                 "URI scheme: %s" % self.__uri_scheme,
                 "eff. scheme: %s" % self.__eff_scheme,
                 "Hostname: `%s`" % self.__hostname,
                 "Path: `%s`" % self.__path,
                 "Port: %s" % self.__port,
                 "Username: `%s`" % self.__username,
                 "Password: `%s`" % _pass
               ]
        _res_str = "\n".join(_res)
        return _res_str

    def set_and_parse_uri(self, uri):
        _logger = log.LogFactory.getLogger()
#        contains password in plain text
#        _logger.debug("set and parse uri: %s" % uri)
        self.__clear()
        splituri = urlparse.urlsplit(uri)
        self.__uri = splituri.geturl()  # gets normalized URI
        splituri = urlparse.urlsplit(self.__uri)

#        print "\nSplit uri:\n"
#        print "url: %s" % splituri.geturl()
#        print "scheme: %s" % splituri.scheme        #IGNORE:E1103
#        print "netloc: %s" % splituri.netloc        #IGNORE:E1103
#        print "path: %s" % splituri.path            #IGNORE:E1103
#        print "query: %s" % splituri.query          #IGNORE:E1103
#        print "fragment: %s" % splituri.fragment    #IGNORE:E1103
#        print "username: %s" % splituri.username
#        print "password: ????"
#        print "hostname: %s" % splituri.hostname
#        print "port: %s" % splituri.port
#        print "-------------------------"

        assert splituri.fragment == "" #IGNORE:E1103
        assert splituri.query == "" #IGNORE:E1103

        if splituri.port is not None:
            self.__port = splituri.port

        if splituri.username is not None:
            self.__username = urllib.unquote(splituri.username)

        if splituri.password is not None:
            self.__password = urllib.unquote(splituri.password)

        if splituri.hostname is None:
            self.__hostname = ""
        else:
            self.__hostname = splituri.hostname

        self.__path = splituri.path #IGNORE:E1103
#        self.__uri_scheme = splituri.scheme #IGNORE:E1103
        if splituri.scheme == "" and self.__uri.startswith("/"):    #IGNORE:E1103
            self.__uri_scheme = "file"
        else:
            self.__uri_scheme = splituri.scheme                     #IGNORE:E1103

        self.__eff_scheme = _get_eff_uri_scheme(self.__uri_scheme)
        _logger.debug("UriParser:\n%s" % self)

    def __construct_display_name(self):
        if self.is_local():
            _res = self.__path
        else:
            _user = ""
            _host = ""
            if self.__username is not None:
                _user = "%s@" % self.__username
            if self.__hostname is not None:
                _host = "%s" % self.__hostname
            _res = "%s://%s%s%s" % (self.__uri_scheme, _user, _host, self.__path)
        return _res

    def query_mount_uri(self):
        """
        Include user in uri being mounted to maintain compliance with Nautilus mounts.
        """
        _logger = log.LogFactory.getLogger()
        _host = ""
        if self.__hostname is not None:
            _host = "%s" % self.__hostname.rstrip("/")

        _user = ""
        if self.__username is not None:
            _user = "%s@" % urllib.quote(self.__username, "")

        _path = self.__path.strip("/")
        if _path != "":
            _path = "/%s" % _path

        _port = ""
        if self.__port is not None:
            _port = ":%s" % self.__port

        _res = "%s://%s%s%s%s" % (self.__eff_scheme, _user, _host, _port, _path)
        _logger.debug("get_mount_uri: %s" % _res)
        return _res

    def is_local(self):
        _local = False
        if self.__eff_scheme == "":
            raise ValueError("Effective scheme not set")
        if self.__eff_scheme == URI_SCHEME_EFF_LOCAL_FILE:
            _local = True
        return _local

    def query_display_name(self):
        return self.__construct_display_name()


def construct_remote_uri_from_tupel(scheme, hostname, port, path, username, password):
    _logger = log.LogFactory.getLogger()
    if not isinstance(scheme, types.StringTypes):
        raise TypeError
    if not isinstance(hostname, types.StringTypes):
        raise TypeError
    if not isinstance(port, types.StringTypes):
        raise TypeError
    if not isinstance(path, types.StringTypes):
        raise TypeError
    if not isinstance(username, types.StringTypes):
        raise TypeError
    if not isinstance(password, types.StringTypes):
        raise TypeError

    if scheme not in VALID_URI_SCHEMES:
        raise ValueError

    # Within the user and password field, any ":", "@", or "/" must be encoded.
    _host = hostname.rstrip("/")
    _user = urllib.quote(username, "")
    _pass = ""
    _port = ""
    _path = path.strip("/")

    if _path != "":
        _path = "/%s" % _path

    if password != "":
        _pass = urllib.quote(password, "")
        _pass = ":%s" % _pass

    if _user != "" or _pass != "":
        _host = "@%s" % hostname

    if port != "":
        _port = ":%s" % port

    _res = "%s://%s%s%s%s%s" % (scheme, _user, _pass, _host, _port, _path)
    _logger.debug("construct_from_remote_tupel: %s" % _res)
    return _res


#def _get_eff_uri_scheme(uri, uri_scheme):
def _get_eff_uri_scheme(uri_scheme):
    """
    :todo: can we construct the eff. scheme manually? aparently ssh is just hardlinked to sftp. 
    """
# following does not work as expected!
#    _gfileobj = _GIOFILE(uri)
#    _uri_scheme = _gfileobj.get_uri_scheme()
#    _has = _gfileobj.has_uri_scheme(_uri_scheme)
#    if _has != True:
#        raise ValueError("URI scheme `%s` not supported by backend" % _uri_scheme)

    if uri_scheme not in VALID_URI_SCHEMES:
        raise exceptions.FileAccessException("URI scheme `%s` not supported by Simple Backup" % uri_scheme)

    _eff_scheme = URI_SCHEME_TO_EFF_URI_SCHEME[uri_scheme]

    if _eff_scheme not in VALID_EFF_URI_SCHEMES:
        raise exceptions.FileAccessException("Eff. URI scheme `%s` not supported by Simple Backup"\
                                             % _eff_scheme)

    return _eff_scheme


def append_time_to_filename(filename, filetype = ""):
    if not isinstance(filename, types.StringTypes):
        raise TypeError("Expected string. Got %s instead." % type(filename))
    if not isinstance(filetype, types.StringTypes):
        raise TypeError("Expected string as file type. Got %s instead." % type(filetype))
    if filetype != "" and not filetype.startswith("."):
        raise ValueError("Given file type must start with dot (.xyz).")

    _time = datetime.datetime.now().isoformat("_").replace(":", ".")
    _res = append_str_to_filename(filename, _time, filetype)
    return _res


def append_str_to_filename(filename, str_to_append, filetype = ""):
    """If a file type (i.e. file extension) is specified, the string
    to append is put in front of the file type extension.
    
    Example: string to append = 123
             filename = basename.log
             result without specifying a filetype = basename.log.123 
             result with specifying filetype '.log' = basename.123.log 
             
    """
    if not isinstance(filename, types.StringTypes):
        raise TypeError("Expected string as filename. Got %s instead." % type(filename))
    if not isinstance(str_to_append, types.StringTypes):
        raise TypeError("Expected string to append. Got %s instead." % type(str_to_append))
    if not isinstance(filetype, types.StringTypes):
        raise TypeError("Expected string as file type. Got %s instead." % type(filetype))
    if filetype != "" and not filetype.startswith("."):
        raise ValueError("Given file type must start with dot (.xyz).")

    _filen = filename
    _ext = ""
    if filetype != "":
        if filename.endswith(filetype):
            _filen = filename.rstrip(filetype)
    _res = "%s.%s%s" % (_filen, str_to_append, filetype)
    return _res


def remove_trailing_sep(path):
    spath = path.rstrip(system.PATHSEP)
    return spath


def remove_leading_sep(path):
    spath = path.lstrip(system.PATHSEP)
    return spath


def ensure_leading_sep(path):
    spath = "%s%s" % (system.PATHSEP, remove_leading_sep(path))
    return spath


def joinpath(*args):
    """Concatenates given paths (i.e. concatenates them and removes trailing
    separators).
    """
    if len(args) == 0:
        _path = system.PATHSEP
    else:
        _path = ""
        for _arg in args:
            _path = "%s%s%s" % (_path, system.PATHSEP, remove_leading_sep(_arg))

        if not args[0].startswith(system.PATHSEP):
            _path = remove_leading_sep(_path)

        _path = remove_trailing_sep(_path)
    return _path
