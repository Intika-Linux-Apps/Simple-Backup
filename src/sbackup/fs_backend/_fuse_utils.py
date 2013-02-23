#   Simple Backup - file access management using FUSE
#
#   Copyright (c)2010,2013: Jean-Peer Lorenz <peer.loz@gmx.net>
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
:mod:`sbackup.util.fuse_utils` -- file access management using FUSE
========================================================================

.. module:: fuse_utils
   :synopsis: public entry point to file access management using FUSE
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

from gettext import gettext as _
import types

from sbackup.util import local_file_utils
from sbackup.util import exceptions
from sbackup.util import interfaces
from sbackup.util import structs
from sbackup.util import pathparse
from sbackup.util import exceptions

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

    pathsep = local_file_utils.PATHSEP

    def __init__(self):
        interfaces.IOperations.__init__(self)
        
    @classmethod
    def chmod_no_rwx_grp_oth(cls, path):
        local_file_utils.chmod_no_rwx_grp_oth(path)

    @classmethod
    def path_exists(cls, path):
        return local_file_utils.path_exists(path)

    @classmethod
    def rename(cls, src, dst):
        local_file_utils.rename(src, dst)

    @classmethod
    def readfile(cls, path):
        return local_file_utils.readfile(path)

    @classmethod
    def normpath(cls, *args):
        return local_file_utils.normpath(*args)

    @classmethod
    def joinpath(cls, *args):
        return pathparse.joinpath(*args)

    @classmethod
    def get_dirname(cls, path):
        return local_file_utils.get_dirname(path)

    @classmethod
    def get_basename(cls, path):
        return local_file_utils.get_basename(path)

    @classmethod
    def openfile_for_write(cls, path):
        return local_file_utils.openfile(path, write = True)

    @classmethod
    def openfile_for_read(cls, path):
        return local_file_utils.openfile(path, write = False)

    @classmethod
    def openfile_for_append(cls, path):
        return local_file_utils.openfile_for_append(path)

    @classmethod
    def pickleload(cls, path):
        return local_file_utils.pickleload(path)

    @classmethod
    def pickledump(cls, datas, path):
        local_file_utils.pickledump(datas, path)

    @classmethod
    def delete(cls, uri):
        local_file_utils.delete(uri)

    @classmethod
    def force_delete(cls, path):
        local_file_utils.force_delete(path)

    @classmethod
    def copyfile(cls, src, dest):
        local_file_utils.copyfile(src, dest)

    @classmethod
    def listdir(cls, path):
        return local_file_utils.listdir(path)

    @classmethod
    def listdir_fullpath(cls, path) :
        return local_file_utils.listdir_fullpath(path)

    @classmethod
    def makedir(cls, target):
        local_file_utils.makedir(target)

    @classmethod
    def makedirs(cls, target) :
        local_file_utils.makedirs(target) #, 0750)

    @classmethod
    def writetofile(cls, path, content) :
        """
        Write a String to a file. You don't have to open and close the file.
        - File = path to the file
        - StringToWrite = String to write into the file.
        """
        local_file_utils.writetofile(path, content)

    @classmethod
    def force_move(cls, src, dst):
        local_file_utils.force_move(src, dst)

    @classmethod
    def is_link(cls, path):
        return local_file_utils.is_link(path)

    @classmethod
    def test_dir_access(cls, path):
        try:
            local_file_utils.listdir(path)
        except Exception, error:
            raise exceptions.FileAccessException(\
                    "Unable to list directory content: %s" % error)

    @classmethod
    def is_dir(cls, path):
        return local_file_utils.is_dir(path)

    @classmethod
    def close_stream(cls, file_desc):
        try:
            file_desc.close()
        except IOError, error:
            raise exceptions.FileAlreadyClosedError(_("Error while closing stream: %s") % error)

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
