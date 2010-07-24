#    Simple Backup - Target file access management using GIO/GVFS
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


from gettext import gettext as _
import types

from nssbackup.util import local_file_utils
from nssbackup.util import exceptions
from nssbackup.util import interfaces

from nssbackup.util import log
from nssbackup.util import pathparse

from nssbackup.fs_backend import _gio_utils as gio_utils
from nssbackup.fs_backend._gio_utils import GioOperations


class GioTargetHandler(interfaces.ITargetHandler):

    def __init__(self):
        """
        Constructor
        :param configuration:
         
        only mounted path is Target (currently)        
        """
        interfaces.ITargetHandler.__init__(self)

        self._logger = log.LogFactory.getLogger()

        # destination/target specific instances
        self._dest = None
        self._dest_mount_hdl = gio_utils.GioMountHandler()
        self._use_mainloop = False
        self._configuration = None
        self._in_progress = False  # must be set to False when start mount process (lock)
        self._initialize_callback = None
        self._terminate_callback = None
        self._is_initialized = False

    def set_use_mainloop(self, use):
        if not isinstance(use, types.BooleanType):
            raise TypeError("Expected boolean type")
        self._use_mainloop = use

    def set_initialize_callback(self, func):
        self._logger.debug("set_initialize_callback: %s" % (str(func)))
        self._initialize_callback = func

    def set_terminate_callback(self, func):
        self._logger.debug("set_terminate_callback: %s" % (str(func)))
        self._terminate_callback = func

    def set_destination(self, path):
        _dest_obj = pathparse.UriParser()
        _dest_obj.set_and_parse_uri(uri = path)
        self._dest = _dest_obj
        self._dest_mount_hdl.set_uri(self._dest) # actually a UriParser

    def get_destination(self):
        _path = self._dest.uri
        return _path

    def is_local(self):
        _loc = self._dest.is_local()
        return _loc

    def set_configuration_ref(self, configuration):
        self._configuration = configuration

    def initialize(self):
        self._logger.info(_("Initializing GIO File Access Manager."))
        if self._dest is None:
            raise TypeError("No destination given")

#TODO: skip initialization or raise exception?        
        if self._is_initialized is True:
            raise AssertionError("GIO File Access Manager is already initialized.")

        self._mount_destination()

    def is_initialized(self):
        return self._is_initialized

    def terminate(self):
        self._logger.info(_("Terminating GIO File Access Manager."))
        if self._in_progress is not False:
            raise AssertionError("Another mount process is still in progress")
        self._in_progress = True

        if self._is_initialized is True:
            # set `use_mainloop` again for the case it was changed in the meantime
            self._dest_mount_hdl.use_own_mainloop(self._use_mainloop)
            try:
                self._dest_mount_hdl.umount()
            except exceptions.RemoteUmountFailedError, error:
                self._logger.error("Unable to umount `%s`: %s" % (self._dest.query_display_name(), error))

        else:
            self._logger.warning("GIO File Access Manager is not initialized. Nothing to do.")
            self._logger.debug("Calling callbacks anyway")
            self._umount_cb(None)

    def _mount_destination(self):
        """Mounts the destination specified in configuration and modifies the target value
        in configuration accordingly.
        """
        if self._in_progress is not False:
            raise AssertionError("Another mount process is still in progress")

        self._in_progress = True  # set lock

        self._dest_mount_hdl.use_own_mainloop(self._use_mainloop)
        self._dest_mount_hdl.set_callbacks(mount = self._mount_cb,
                                                      umount = self._umount_cb)
        self._dest_mount_hdl.mount()

    def _mount_cb(self, error):
        """Callback method that gets called when mounting is finished.
        Takes errors occurred during the mount process as parameter.
        """
#        print ">>> gio_fam._mount_cb"
        try:
            if error is None:
                _eff_path = self.get_eff_path()

                if _eff_path is None:
                    raise exceptions.FileAccessException("Unable to mount target")

# test existence separate to enable umounting if path does not exist
#                if self.dest_eff_path_exists() is False:
#                    raise exceptions.FileAccessException("Destination path `%s` does not exist" % _eff_path)

                if self._configuration is not None:
                    self._logger.debug("Modify value of target in referenced configuration to `%s`" % _eff_path)
                    self._configuration.set("general", "target", _eff_path)
                    self._logger.debug("\n%s" % str(self._configuration))
                else:
                    self._logger.debug("No configuration set. Value of target is not modified.")

        except exceptions.FileAccessException, error:
            self._logger.error("Error in mount callback function: %s" % error)
            if self._initialize_callback is None:
                raise
        finally:
            self._in_progress = False # release lock

        if self._initialize_callback is not None:
            self._logger.debug("Calling additional callback in gio_fam._mount_cb: %s" % self._initialize_callback)
            self._initialize_callback(error)

        if error is None:
            self._is_initialized = True
#        print "End of gio_fam._mount_cb"

    def _umount_cb(self, error):
#        print ">>> gio_fam._umount_cb"
        self._in_progress = False # release lock
        if self._terminate_callback is not None:
            self._logger.debug("Calling additional callback in gio_fam: %s" % self._terminate_callback)
            self._terminate_callback(error)

        self._is_initialized = False
#        print "End of gio_fam._umount_cb"

    def get_eff_path(self):
        _eff_path = self._dest_mount_hdl.get_eff_path()
        return _eff_path

    def query_dest_fs_info(self):
        (_size, _free) = self._dest_mount_hdl.query_fs_info()
        return (_size, _free)

    def query_dest_display_name(self):
        return self._dest.query_display_name()

    def dest_eff_path_exists(self):
        """The effective path denotes the local mountpoint of the actual remote or local target.
        It is required in order to give it to TAR as parameter (tar does not support gio).
        It is checked using GIO and native access functions.
        """
        _res = False
        _effpath = self.get_eff_path()

        _res_gio = GioOperations.path_exists(_effpath)
        _res_nat = local_file_utils.path_exists(_effpath)

        if (_res_gio is True) and (_res_nat is True):
            _res = True

        return _res

    def test_destination(self):
        self._dest_mount_hdl.test_path()

#    def dest_listdir(self):
##        _fop = gio_utils.GioOperations()
#
#        _deffpath = self._config.get_destination_eff_path()
#        _lsd = _local_fop.listdir(_deffpath)
#        _res = []
#        for _dir in _lsd:
#            _res.append(_local_fop.normpath(_deffpath, _dir))
#
#        return _res
