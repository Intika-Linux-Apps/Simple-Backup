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

"""
@todo: Remove wildcard imports!
"""

import inspect
import os
import sys
import glob
from gettext import gettext as _
import nssbackup, subprocess
from tempfile import *
from nssbackup.util.file_handling import *
from nssbackup.util.log import LogFactory
from nssbackup.util.exceptions import SBException


class pluginFAM(object):
    """
    The fuseFAM plugin interface
    @author: Oumar Aziz Ouattara <wattazoum@gmail.com>
    @version: 1.0
    """

    def __init__(self):
        self.logger = LogFactory.getLogger()

    def match_scheme(self, remoteSource):
        raise SBException("'match_scheme_full' Not implemented for this plugin")

    def match_scheme_full(self, remoteSource):
        """
        Try to match the scheme of the remoteSource.
        @param remoteSource: The remote path
        @return: True if the scheme matches the one for this 
        @rtype: boolean
        """
        raise SBException("'match_scheme_full' Not implemented for this plugin")

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
        raise SBException("'mount' Not implemented for this plugin")

    def umount(self, mounteddir):
        """
        Default behaviour is to unmount with fuse
        """
        if os.path.ismount(mounteddir):
            self.logger.debug("Unmounting `%s`" % mounteddir)
            # Create output and error log file
            outptr, outFile = mkstemp(prefix = "fuseUmount_output_")
            errptr, errFile = mkstemp(prefix = "fuseUmount_error_")

            # Call the subprocess using convenience method using lazy umount
            retval = subprocess.call(["fusermount", "-u", "-z", mounteddir], 0, None, None, outptr, errptr)

            # Close log handles
            os.close(errptr)
            os.close(outptr)
            outStr, errStr = readfile(outFile), readfile(errFile)
            delete(outFile)
            delete(errFile)

            self.logger.debug("fusermount output:\n%s\n%s" % (outStr, errStr))

            if retval != 0 :
                raise SBException("Unable to unmount `%s`: %s" % (mounteddir, errStr))
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
        raise SBException("'Check if mounted' Not implemented for this plugin")

    def getdoc(self):
        """
        This method should give a little documentation about the schema used for this plugin.
        @return: The schema doc (eg. return 'example : sch://user:password@server/dir')
        """
        raise SBException("Help not implemented for this plugin")


class PluginManager(object):
    """
    """
    # This should be a dictionary of plugins
    __pluginList = None

    def __init__(self):
        self.logger = LogFactory.getLogger()

    def getPlugins(self):
        """Searches for plugins in the plugin directory and loads them.
        
        @return : The plugins dictionary list {'name':class}.
        @note: Look at FuseFAM to know how it's used.
        """

        if self.__pluginList : return self.__pluginList
        else :
            self.__pluginList = dict()
            tmp = inspect.getabsfile(inspect.getmodule(self))
            plugins_dir = os.path.dirname(tmp)
            if os.path.isdir(plugins_dir):
                if plugins_dir not in sys.path:
                    sys.path.append(plugins_dir)

                for file in glob.glob('%s/*FuseFAM.py' % plugins_dir):
                    try:
                        module_filename = os.path.basename(file)
                        module_name, _ = os.path.splitext(module_filename)
                        plugin = __import__(module_name, '', module_filename)
                        for symbol_name in dir(plugin):
                            symbol = getattr(plugin, symbol_name)
                            if inspect.isclass(symbol) and symbol != pluginFAM and \
                                issubclass(symbol, pluginFAM):
                                #symbol.enabled = symbol.name in plugin_names
                                self.__pluginList[symbol_name] = symbol
                    except Exception, e:
                        from gettext import gettext as _
                        self.logger.warning(_("Could not import plugin %(plugin_name)s ! Cause : %(error_cause)s ") % {'plugin_name':file, 'error_cause': str(e)})
                        continue
            return self.__pluginList
