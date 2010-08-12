#   Simple Backup - file access management
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
:mod:`sbackup.util.fam` -- file access management
===================================================

.. module:: fam
   :synopsis: public entry point to file access management
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""


from sbackup.util import prefs


_PREFS = prefs.Preferences()
FS_BACKEND = _PREFS.get(key = prefs.PREFS_FS_BACKEND)


# factory methods
def get_fam_target_handler_facade_instance():
    _fam = None

    if FS_BACKEND == prefs.FS_BACKEND_GIO:
        from sbackup.fs_backend import _gio_fam
        _fam = _gio_fam.GioTargetHandler()

    elif FS_BACKEND == prefs.FS_BACKEND_FUSE:
        from sbackup.fs_backend import _fuse_fam
        _fam = _fuse_fam.FuseTargetHandler()

    else:
        raise ValueError("Given filesystem backend `%s` is not supported" % FS_BACKEND)

    return _fam


def get_file_operations_facade_instance():
    _op = None

    if FS_BACKEND == prefs.FS_BACKEND_GIO:
        from sbackup.fs_backend import _gio_utils
        _op = _gio_utils.GioOperations()

    elif FS_BACKEND == prefs.FS_BACKEND_FUSE:
        from sbackup.fs_backend import _fuse_utils
        _op = _fuse_utils.FuseOperations()

    else:
        raise ValueError("Given filesystem backend `%s` is not supported" % FS_BACKEND)

    return _op


def get_remote_services_avail():
    _res = None

    if FS_BACKEND == prefs.FS_BACKEND_GIO:
        from sbackup.fs_backend import _gio_utils
        _res = _gio_utils.REMOTE_SERVICES_AVAIL

    elif FS_BACKEND == prefs.FS_BACKEND_FUSE:
        from sbackup.fs_backend import _fuse_utils
        _res = _fuse_utils.REMOTE_SERVICES_AVAIL

    else:
        raise ValueError("Given filesystem backend `%s` is not supported" % FS_BACKEND)

    return _res

def get_default_remote_service():
    _res = None

    if FS_BACKEND == prefs.FS_BACKEND_GIO:
        from sbackup.fs_backend import _gio_utils
        _res = _gio_utils.REMOTE_SERVICE_SFTP

    elif FS_BACKEND == prefs.FS_BACKEND_FUSE:
        from sbackup.fs_backend import _fuse_utils
        _res = _fuse_utils.REMOTE_SERVICE_SFTP

    else:
        raise ValueError("Given filesystem backend `%s` is not supported" % FS_BACKEND)

    return _res

def get_scheme_from_service(service):
    _res = None

    if FS_BACKEND == prefs.FS_BACKEND_GIO:
        from sbackup.fs_backend import _gio_utils
        _res = _gio_utils.get_scheme_from_service(service)

    elif FS_BACKEND == prefs.FS_BACKEND_FUSE:
        from sbackup.fs_backend import _fuse_utils
        _res = _fuse_utils.get_scheme_from_service(service)

    else:
        raise ValueError("Given filesystem backend `%s` is not supported" % FS_BACKEND)

    return _res


def get_service_from_scheme(scheme):
    _res = None

    if FS_BACKEND == prefs.FS_BACKEND_GIO:
        from sbackup.fs_backend import _gio_utils
        _res = _gio_utils.get_service_from_scheme(scheme)

    elif FS_BACKEND == prefs.FS_BACKEND_FUSE:
        from sbackup.fs_backend import _fuse_utils
        _res = _fuse_utils.get_service_from_scheme(scheme)

    else:
        raise ValueError("Given filesystem backend `%s` is not supported" % FS_BACKEND)

    return _res
