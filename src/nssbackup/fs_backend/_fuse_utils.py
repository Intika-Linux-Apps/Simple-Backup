#    Simple Backup - file access management using FUSE
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
:mod:`nssbackup.util.fuse_utils` -- file access management using FUSE
========================================================================

.. module:: fuse_utils
   :synopsis: public entry point to file access management using FUSE
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

from gettext import gettext as _
import types

from nssbackup.util import local_file_utils
from nssbackup.util import interfaces
from nssbackup.util import structs
from nssbackup.util import pathparse


#TODO: move available services into FUSE plugin manager and retrieve them dynamically
REMOTE_SERVICE_SFTP = 101
REMOTE_SERVICE_FTP = 102
REMOTE_SERVICE_SSH = 104


REMOTE_SERVICES_AVAIL = { REMOTE_SERVICE_SFTP : _("SFTP"),
                          REMOTE_SERVICE_SSH : _("SSH"),
                          REMOTE_SERVICE_FTP : _("FTP")
                        }
REMOTE_SERVICE_TO_URI_SCHEME = { REMOTE_SERVICE_FTP : pathparse.URI_SCHEME_FTP,
                                 REMOTE_SERVICE_SFTP : pathparse.URI_SCHEME_SFTP,
                                 REMOTE_SERVICE_SSH : pathparse.URI_SCHEME_SSH
                               }
URI_SCHEME_TO_REMOTE_SERVICE = { REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_FTP] : REMOTE_SERVICE_FTP,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_SFTP] : REMOTE_SERVICE_SFTP,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_SSH] : REMOTE_SERVICE_SSH
                               }


class FuseOperations(interfaces.IOperations):
    """Collects simple operations
    """
    __metaclass__ = structs.Singleton

    def __init__(self):
        interfaces.IOperations.__init__(self)
        self.pathsep = local_file_utils.pathsep

    @classmethod
    def path_exists(cls, path):
        return local_file_utils.path_exists(path)

    def path_writeable(self, path):
        return local_file_utils.path_writeable(path)

    def rename(self, src, dst):
        local_file_utils.rename(src, dst)

    def chmod(self, path, mode):
        local_file_utils.chmod(path, mode)

    def copy(self, src, dst):
        local_file_utils.copy(src, dst)

    def copy_no_permissions(self, src, dst):
        local_file_utils.copy_no_permissions(src, dst)

    def readfile(self, path):
        return local_file_utils.readfile(path)

    @classmethod
    def normpath(cls, *args):
        return local_file_utils.normpath(*args)

    def get_dirname(self, path):
        return local_file_utils.get_dirname(path)

    def get_basename(self, path):
        return local_file_utils.get_basename(path)

    def openfile(self, uri, write = False):
        return local_file_utils.openfile(uri, write)

    def pickleload(self, path):
        return local_file_utils.pickleload(path)

    def pickledump(self, datas, path):
        local_file_utils.pickledump(datas, path)

    def delete(self, uri):
        local_file_utils.delete(uri)

    def force_delete(self, path):
        local_file_utils.force_delete(path)

    def copyfile(self, src, dest):
        local_file_utils.copyfile(src, dest)

    def listdir(self, path):
        return local_file_utils.listdir(path)

    def listdir_fullpath(self, path) :
        return local_file_utils.listdir_fullpath(path)

    def makedir(self, target):
        local_file_utils.makedir(target)

    def makedirs(self, target) :
        local_file_utils.makedirs(target) #, 0750)

    def createfile(self, filepath):
        local_file_utils.createfile(filepath)

    def writetofile(self, path, content) :
        """
        Write a String to a file. You don't have to open and close the file.
        - File = path to the file
        - StringToWrite = String to write into the file.
        """
        local_file_utils.writetofile(path, content)

    def force_move(self, src, dst):
        local_file_utils.force_move(src, dst)

    def is_link(self, path):
        return local_file_utils.is_link(path)

    def get_link(self, path):
        return local_file_utils.get_link(path)

    def get_link_abs(self, path):
        return local_file_utils.get_link_abs(path)

    def is_dir(self, path):
        return local_file_utils.is_dir(path)

    def rename_errors_ignored(self, src, dst):
        local_file_utils.rename_errors_ignored(src, dst)


def get_scheme_from_service(service):
    if not isinstance(service, types.IntType):
        raise TypeError
    if service not in REMOTE_SERVICES_AVAIL:
        raise ValueError("Given remote service not supported")
    if service not in REMOTE_SERVICE_TO_URI_SCHEME:
        raise ValueError("Given remote service not supported")

    _scheme = REMOTE_SERVICE_TO_URI_SCHEME[service]
    return _scheme


def get_service_from_scheme(scheme):
#    _uri_scheme = self.__uri.uri_scheme
    try:
        _service = URI_SCHEME_TO_REMOTE_SERVICE[scheme]
    except KeyError:
        _service = None
    return _service
