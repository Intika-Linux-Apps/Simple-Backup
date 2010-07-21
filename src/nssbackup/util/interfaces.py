#    Simple Backup - interface definitions
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

    def dest_eff_path_exists(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "dest_eff_path_exists"))

    def query_dest_display_name(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "query_dest_display_name"))

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

    def is_local(self):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "is_local"))

    def set_use_mainloop(self, use):
        raise NotImplementedError(_get_notimplemented_msg("ITargetHandler", "set_use_mainloop"))

#    def dest_listdir(self):


class IOperations(object):

    def __init__(self):
        pass

    @classmethod
    def path_exists(cls, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "path_exists"))

    def path_writeable(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "path_writeable"))

    def chmod(self, path, mode):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "chmod"))

    def copy(self, src, dst):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "copy"))

    def copy_no_permissions(self, src, dst):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "copy_no_permissions"))

    def delete(self, uri):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "delete"))

    def force_delete(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "force_delete"))

    def makedir(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "makedir"))

    def makedirs(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "makedirs"))

    @classmethod
    def normpath(cls, *args):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "normpath"))

    def openfile(self, uri, write = False):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "openfile"))

    def get_dirname(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "get_dirname"))

    def get_basename(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "get_basename"))

    def pickleload(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "pickleload"))

    def pickledump(self, datas, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "pickledump"))

    def rename(self, src, dst):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "rename"))

    def readfile(self, uri):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "readfile"))

    def writetofile(self, path, content):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "writetofile"))

    def copyfile(self, src, dest):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "copyfile"))

    def listdir(self, target) :
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "listdir"))

    def listdir_fullpath(self, target) :
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "listdir_fullpath"))

    def createfile(self, filepath):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "createfile"))

    def force_move(self, src, dst):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "force_move"))

    def is_link(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "is_link"))

    def get_link(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "get_link"))

    def get_link_abs(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "get_link_abs"))

    def is_dir(self, path):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "is_dir"))

    def rename_errors_ignored(self, src, dst):
        raise NotImplementedError(_get_notimplemented_msg("IOperations", "rename_errors_ignored"))
