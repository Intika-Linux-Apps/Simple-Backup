#   Simple Backup - Target file access management using Fuse plugins
#
#   Copyright (c)2009-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#   Copyright (c)2007-2009: Ouattara Oumar Aziz <wattazoum@gmail.com>
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
import os
import time
import uuid


from sbackup.core import ConfigManager
from sbackup.fuse_plugins import PluginManager
from sbackup.util.exceptions import SBException
from sbackup.util import exceptions
from sbackup.util import interfaces
from sbackup.util import local_file_utils
from sbackup.util import log
from sbackup.util import pathparse


class  FuseTargetHandler(interfaces.ITargetHandler):
    """
    The Fuse File access Manager
    """

    def __init__(self):
        """
        Constructor
        @param configManager: 
        """
        interfaces.ITargetHandler.__init__(self)

        self._logger = log.LogFactory.getLogger()

        # destination/target specific instances
        self._dest = None
        self._eff_path = None
        self._configuration = None
        self._initialize_callback = None
        self._terminate_callback = None
        self._is_initialized = False

        ## This is the base directory where all mountpoints of remote sites will be located
        _defaults = ConfigManager.get_default_config_obj()
        self.__mountdir = _defaults.get_mountdir()

        ## the list of all mounted dirs , should be filled by initialize.
        # It's a dict with key = remoteSource and value = mountpoint
        self.__mountedDirs = {}

    def set_use_mainloop(self, use):
        pass

    def set_destination(self, path):
        _dest_obj = pathparse.UriParser()
        _dest_obj.set_and_parse_uri(uri = path)
        self._dest = _dest_obj
        if self._dest.is_local():
            self._eff_path = self._dest.uri

    def get_destination(self):
        _path = self._dest.uri
        return _path

    def set_initialize_callback(self, func):
        self._logger.debug("set_initialize_callback: %s" % (str(func)))
        self._initialize_callback = func

    def set_terminate_callback(self, func):
        self._logger.debug("set_terminate_callback: %s" % (str(func)))
        self._terminate_callback = func

    def set_configuration_ref(self, configuration):
        self._configuration = configuration
        self.__mountdir = self._configuration.get_mountdir()

    def is_initialized(self):
        return self._is_initialized

    def initialize(self):
        """Test existence of path after initialization.
        
        Get the list of dir to mount and mount them. If the keep alive tag is set , it creates a Thread that will keep the mounted dir alive.
        @param keepAlive: Optional int that is used to determine the loop time (number of seconds) to keep the mount pint alive
        
        @todo: For later releases: The distinction between local and remote
               sites must be improved!               
        """
        self._logger.info(_("Initializing FUSE File Access Manager."))
        if self._is_initialized is True:
            raise AssertionError("FUSE File Access Manager is initialized.")

        self._eff_path = None
        self.__check_mountdir()
        self._mount_config_destination()
        self._is_initialized = True

    def __check_mountdir(self):
        """check if the mount dir is valid
        :todo: Do not create dir here? Use makedirs?
        """
        if not os.path.exists(self.__mountdir) :
            os.mkdir(self.__mountdir)
        else:
            if not os.path.isdir(self.__mountdir) :
                raise SBException("The mount base dir should be a directory")

    def terminate(self):
        """
        Unmount all mounted directories.
        """
        self._logger.info(_("Terminating FUSE File Access Manager."))
        error = None
#        print "Mount dirs: %s" % str(self.__mountedDirs)

        if self._is_initialized is True:
            try:
                plugin_manager = PluginManager()
                for src, dir in self.__mountedDirs.iteritems() :
                    self._logger.debug("Mounted dirs - %s - %s" % (src, dir))
                    if src is not os.sep :
                        _umounted = False
                        for p_name, p_class in plugin_manager.getPlugins().iteritems():
                            #we got the plugin
                            self._logger.debug("Trying `%s` plugin to match `%s`" % (p_name, src))
                            plugin = p_class()
                            if plugin.match_scheme(src):
                                self._logger.debug("Unmounting with `%s` plugin" % p_name)
                                plugin.umount(dir)
                                _umounted = True
                                self._remove_mountdir(dir)
                                break
                        if not _umounted:
                            self._logger.warning("Unable to terminate FUSE `%s`" % dir)
            except SBException, error:
                self._logger.error("Error in terminate. Overwriting previous errors.")
                if self._initialize_callback is None:
                    raise

        else:
            self._logger.warning("FUSE File Access Manager is not initialized. Nothing to do.")

        self._eff_path = None

        if self._terminate_callback is not None:
            self._logger.debug("Calling additional callback in gio_fam: %s" % self._terminate_callback)
            self._terminate_callback(error)

        self._is_initialized = False
#        print "End of fuse_fam.terminate"

        self._is_initialized = False

    def __mount_uri(self, uri):
        """Mounts an arbitrary uri and returns effective path. It uses the __mountdir param to know
        where to mount. It also fills the __mountedDirs dict. The configuration is not modified.
        
        @return: effective path of given uri or None if local path was given
        """
        self.__check_mountdir()

        plugin_manager = PluginManager()
        for p_name, p_class in plugin_manager.getPlugins().iteritems():
            try :
                #we got the plugin
                plugin = p_class()
                if plugin.match_scheme_full(uri):
                    self._logger.debug("Processing with plugin '%s' to mount '%s'" % (p_name, uri))
                    rsource, mpoint, pathinside = plugin.mount(uri, self.__mountdir)

                    if rsource != os.sep:   # remote
                        self.__mountedDirs[rsource] = mpoint
#                        print "Mount dirs: %s" % str(self.__mountedDirs)
                        return os.sep.join([mpoint, pathinside])
                    else:
                        # The plugin used was localFuseFAM
                        return None

            except Exception, error:
                _msg = "Unable to mount target destination `%s` using plugin `%s`: %s" % (uri, p_name, error)
                self._logger.error(_msg)
                raise exceptions.FuseFAMException(_msg)

        _msg = "Unable to mount `%s`: schema not supported by plugins." % uri
        self._logger.error(_msg)
        raise exceptions.FuseFAMException(_msg)

    def _mount_config_destination(self):
        """Mounts the destination specified in configuration and modifies the target value
        in configuration accordingly.
        """
        error = None
        try:
            _dest = self.get_destination()
            _eff_path = self.__mount_uri(_dest)

            if _eff_path is not None: # None means local path was mounted            
                if self._configuration is not None:
                    self._logger.debug("Modify value of target in referenced configuration to `%s`" % _eff_path)
                    self._configuration.set("general", "target", _eff_path)
                    self._logger.debug("\n%s" % str(self._configuration))
                else:
                    self._logger.debug("No configuration set. Value of target is not modified.")

            if _eff_path is None:
                self._eff_path = _dest
            else:
                self._eff_path = _eff_path

            if self._eff_path is None:
                raise exceptions.FileAccessException("Unable to mount target")

        except SBException, error:
            self._logger.error("Error in mount callback function. Overwriting previous errors.")
            if self._initialize_callback is None:
                raise

        if self._initialize_callback is not None:
            self._logger.debug("Calling additional callback in gio_fam._mount_cb: %s" % self._initialize_callback)
            self._initialize_callback(error)

        if error is None:
            self._is_initialized = True
#        print "End of fuse_fam._mount_config_destination"


    def _remove_mountdir(self, mountpoint):
        """Removes previously created mountpoint in secure manner.
        """
        if os.path.exists(mountpoint):
            if os.path.ismount(mountpoint):
                self._logger.warning("Unable to remove mountpoint that is busy. Unmount before removing.")
            else:
                _listdir = os.listdir(mountpoint)
                if len(_listdir) == 0:
                    try:
                        os.rmdir(mountpoint)
                        self._logger.debug("Mountpoint `%s` successfully removed." % mountpoint)
                    except (IOError, OSError), error:
                        self._logger.error("Unable to remove mountpoint `%s`: %s" % (mountpoint, error))
                else:
                    self._logger.warning("Unable to remove mountpoint: directory is not empty.")
        else:
            self._logger.warning("Unable to remove mountpoint `%s`: does not exist" % mountpoint)

#    def __keepAlive(self):
#        """
#        Launch a command on the mounted dirs to keep the mount alive
#        """
#        pass

#    def testFusePlugins(self, remotedir):
#        """The given remote directory is applied to any found plugins to
#        decide whether one of the plugins is able to handle this (remote)
#        protocol. The tests cover:
#        * checking of the adress scheme and the validity of the adress
#        * mounting of the remote site
#        * write and read access on the remote site.
#        
#        If no plugin is able to handle the given path, an exception is
#        raised.
#        
#        @todo: Customize the raised exception to provided more informations!
#        """
#        if remotedir.startswith(os.sep) :
#            raise SBException("Nothing to do for localpath '%s'." % remotedir)
#
##TODO: inconsistent path handling!
#        # set the defaults 
#        if os.getuid() == 0 :
#            mountdir = "/mnt/sbackup/"
#        else :
#            mountdir = self._configFileHandler.get_user_datadir() + "mountdir"
#
#        # check if the mount dir is valid
#        if not os.path.exists(mountdir) :
#            os.mkdir(mountdir)
#
#        plugin_manager = PluginManager()
#        _plugins = plugin_manager.getPlugins()
#        _iterator = _plugins.iteritems()
#        for p_name, p_class in _iterator:
#            #we got the plugin
#            self._logger.debug("Testing of plugin '%s'" % str(p_name))
#            plugin = p_class()
#            if plugin.match_scheme_full(remotedir):
#                self._logger.debug("Processing with plugin '%s' to mount '%s'" % (p_name, remotedir))
#                try:
#                    rsource, mpoint, pathinside = plugin.mount(remotedir, mountdir)
#                    self._logger.debug("Mount Succeeded !")
#
#                    self._logger.debug("Testing Writability")
#                    test = "testFuseFam"
#                    testfile = os.path.join(mpoint, pathinside, test)
#                    os.mkdir(testfile)
#                    os.rmdir(testfile)
#
#                    plugin.umount(mpoint)
#                    self._remove_mountdir(mpoint)
#
#                except Exception, error:
#                    raise SBException("Test failed with following output:\n\n%s " % error)
#
#                return True
#
#        raise SBException("No plugin could deal with that schema '%s'" % remotedir)

    def get_eff_path(self):
        _effpath = self._eff_path

        assert _effpath != ""
        assert _effpath is not None
        assert _effpath.startswith(local_file_utils.PATHSEP)

        return _effpath

    def query_dest_fs_info(self):
        (_size, _free) = local_file_utils.query_fs_info(self._eff_path)
        return (_size, _free)

    def query_dest_display_name(self):
        return self._dest.query_display_name()

    def query_mount_uri(self):
        return self.get_eff_path()

    def is_local(self):
        _loc = self._dest.is_local()
        return _loc

    def get_supports_publish(self):
        _res = True
        return _res

    def dest_eff_path_exists(self):
        """The effective path denotes the local mountpoint of the actual remote or local target.
        It is required in order to give it to TAR as parameter (tar does not support gio).
        It is checked using GIO and native access functions.
        """
        _effpath = self._eff_path
        _res = False

        assert _effpath != ""
        assert _effpath is not None
        assert _effpath.startswith(local_file_utils.PATHSEP)

        _res = local_file_utils.path_exists(_effpath)
        return _res

    def test_destination(self):
        _effpath = self._eff_path

        assert _effpath != ""
        assert _effpath is not None
        assert _effpath.startswith(local_file_utils.PATHSEP)

        dname = "%s-%s-%s.tmp" % ("sbackup-dir", time.time(), uuid.uuid4())
        tfilen = "%s-%s-%s.tmp" % ("sbackup", time.time(), uuid.uuid4())

        local_file_utils.test_path(_effpath, dname, tfilen)
