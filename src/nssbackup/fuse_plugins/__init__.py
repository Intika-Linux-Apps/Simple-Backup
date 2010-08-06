#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# Authors :
#    Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>


from gettext import gettext as _

import inspect
import os
import sys
import glob
import tempfile
import subprocess


import nssbackup
from nssbackup.util import local_file_utils
from nssbackup.util import log
from nssbackup.util import exceptions


class pluginFAM(object):
    """
    The fuseFAM plugin interface
    @author: Oumar Aziz Ouattara <wattazoum@gmail.com>
    """

    def __init__(self):
        self.logger = log.LogFactory.getLogger()

    def match_scheme(self, remoteSource):
        raise exceptions.SBException("'match_scheme' Not implemented for this plugin")

    def match_scheme_full(self, remoteSource):
        """
        Try to match the scheme of the remoteSource.
        @param remoteSource: The remote path
        @return: True if the scheme matches the one for this 
        @rtype: boolean
        """
        raise exceptions.SBException("'match_scheme_full' Not implemented for this plugin")

    def mount(self, source, mountbase):
        """
        Mount the source intor the mountbase dir . This method should create a mount point to mount the source. 
        The name of the mount point should be very expressive so that we avoid collision with other mount points
        This method will return a tuple (baseRemoteSource, mountpoint, pathinside) where
        - baseRemoteSource is the substring that represent the mount source (usually at the start of the source). The match_scheme_full method should be able to match it
        - mountpoint is the mount point of this baseRemoteSource.
        - pathinside is the path inside the remote source 
        [Use case]
        The mount function is called once with "sch://server/path/to/dir" and the plugin mounts "sch://server" to "/mnt/sch_server". 
        Then the return value would be ("sch://server","/mnt/sch_server","path/to/dir")
        @param source: The remote path
        @param mountbase: The mount points base dir
        @return: The tuple (baseRemoteSource, mountpoint, pathinside)
        @rtype: tuple
        """
        raise exceptions.SBException("'mount' Not implemented for this plugin")

    def umount(self, mounteddir):
        """
        Default behaviour is to unmount with fuse
        """
        if os.path.ismount(mounteddir):
            self.logger.debug("Unmounting `%s`" % mounteddir)
            # Create output and error log file
            outptr, outFile = tempfile.mkstemp(prefix = "fuseUmount_output_")
            errptr, errFile = tempfile.mkstemp(prefix = "fuseUmount_error_")

            # Call the subprocess using convenience method using lazy umount
            retval = subprocess.call(["fusermount", "-u", "-z", mounteddir], 0, None, None, outptr, errptr)

            # Close log handles
            os.close(errptr)
            os.close(outptr)
            outStr, errStr = local_file_utils.readfile(outFile), local_file_utils.readfile(errFile)
            local_file_utils.delete(outFile)
            local_file_utils.delete(errFile)

            self.logger.debug("fusermount output:\n%s\n%s" % (outStr, errStr))

            if retval != 0 :
                raise exceptions.SBException("Unable to unmount `%s`: %s" % (mounteddir, errStr))
            else:
                self.logger.info("Successfully unmounted: `%s`" % mounteddir)
        else:
            self.logger.warning("Unable to unmount `%s`: not mounted" % mounteddir)

    def checkifmounted (self, source, mountbase):
        """
        Should check if the source is mounted.
        Note : you should use os.path.ismount(path) method for that, after determining the name of the mount point.
        @return: True if it is, False if not
        """
        raise exceptions.SBException("'Check if mounted' Not implemented for this plugin")

    def getdoc(self):
        """
        This method should give a little documentation about the schema used for this plugin.
        @return: The schema doc (eg. return 'example : sch://user:password@server/dir')
        """
        raise exceptions.SBException("Help not implemented for this plugin")


class PluginManager(object):
    """
    """
    def __init__(self):
        self.logger = log.LogFactory.getLogger()

        # This should be a dictionary of plugins
        self.__pluginList = None

    def getPlugins(self):
        """Searches for plugins in the plugin directory and loads them.
        
        @return : The plugins dictionary list {'name':class}.
        @note: Look at FuseFAM to know how it's used.
        """

        if self.__pluginList is not None:
            return self.__pluginList

        else:
            self.__pluginList = dict()
            tmp = inspect.getabsfile(inspect.getmodule(self))
            plugins_dir = os.path.dirname(tmp)
            if os.path.isdir(plugins_dir):
                if plugins_dir not in sys.path:
                    sys.path.append(plugins_dir)

                for _file in glob.glob('%s/*FuseFAM.py' % plugins_dir):
                    try:
                        module_filename = os.path.basename(_file)
                        module_name, mod_ext = os.path.splitext(module_filename)  # IGNORE:W0612
                        plugin = __import__(module_name, '', module_filename)
                        for symbol_name in dir(plugin):
                            symbol = getattr(plugin, symbol_name)
                            if inspect.isclass(symbol) and symbol != pluginFAM and \
                                issubclass(symbol, pluginFAM):
                                #symbol.enabled = symbol.name in plugin_names
                                self.__pluginList[symbol_name] = symbol
                    except Exception, error:
                        self.logger.warning(_("Unable to import plugin `%(plugin_name)s`: %(error_cause)s ")\
                                            % { 'plugin_name' : module_name,
                                                'error_cause' : str(error) })
                        continue
            return self.__pluginList
