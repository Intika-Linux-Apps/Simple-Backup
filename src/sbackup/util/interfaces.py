#   Simple Backup - interface definitions
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


def _get_notimplemented_msg(klass, method):
    _res = "Method `%s` is abstract in class `%s` but is not overridden" % (method, klass)
    return _res


class ITargetHandler(object):

    def __init__(self):
        pass

    def initialize(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "initialize"))

    def is_initialized(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "is_initialized"))

    def terminate(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "terminate"))

    def dest_path_exists(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "dest_path_exists"))

    def query_dest_display_name(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "query_dest_display_name"))

    def query_mount_uri(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "query_mount_uri"))

    def query_dest_fs_info(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "query_dest_fs_info"))

    def test_destination(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "test_destination"))

    def set_initialize_callback(self, func):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "set_initialize_callback"))

    def set_terminate_callback(self, func):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "set_terminate_callback"))

    def set_destination(self, path):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "set_destination"))

    def get_destination(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "get_destination"))

    def set_configuration_ref(self, configuration):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "set_configuration_ref"))

    def get_eff_path(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "get_eff_path"))

    def get_eff_fullpath(self, *args):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "get_eff_fullpath"))

    def get_snapshot_path(self, snpname):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "get_snapshot_path"))

    def is_local(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "is_local"))

    def get_supports_publish(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "get_supports_publish"))

    def get_use_iopipe(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "get_use_iopipe"))

    def set_use_mainloop(self, use):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "set_use_mainloop"))


class IOperations(object):

    def __init__(self):
        pass

    @classmethod
    def path_exists(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "path_exists"))

    @classmethod
    def delete(cls, uri):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "delete"))

    @classmethod
    def force_delete(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "force_delete"))

    @classmethod
    def makedir(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "makedir"))

    @classmethod
    def makedirs(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "makedirs"))

    @classmethod
    def normpath(cls, *args):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "normpath"))

    @classmethod
    def openfile_for_write(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "openfile_for_write"))

    @classmethod
    def openfile_for_read(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "openfile_for_read"))

    @classmethod
    def openfile_for_append(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "openfile_for_append"))

    @classmethod
    def get_dirname(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "get_dirname"))

    @classmethod
    def get_basename(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "get_basename"))

    @classmethod
    def pickleload(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "pickleload"))

    @classmethod
    def pickledump(cls, datas, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "pickledump"))

    @classmethod
    def rename(cls, src, dst):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "rename"))

    @classmethod
    def readfile(cls, uri):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "readfile"))

    @classmethod
    def writetofile(cls, path, content):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "writetofile"))

    @classmethod
    def copyfile(cls, src, dest):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "copyfile"))

    @classmethod
    def listdir(cls, target) :
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "listdir"))

    @classmethod
    def listdir_fullpath(cls, target) :
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "listdir_fullpath"))

    @classmethod
    def force_move(cls, src, dst):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "force_move"))

    @classmethod
    def is_link(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "is_link"))

    @classmethod
    def is_dir(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "is_dir"))

    @classmethod
    def close_stream(cls, file_desc):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "close_stream"))
