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
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>

import subprocess
import os
import tempfile
from gettext import gettext as _

from nssbackup.util.log import LogFactory
from nssbackup.plugins import PluginManager
from nssbackup.util.exceptions import SBException
from nssbackup.util import exceptions
from nssbackup.managers.ConfigManager import getUserDatasDir
import FileAccessManager as FAM


class FuseFAM(object):
	"""
	The Fuse File access Manager
	"""
	
	def __init__(self, configManager=None):
		"""
		Constructor
		@param configManager: 
		"""
		self.logger = LogFactory.getLogger()
		
		## This is the base directory where all
		#  mountpoints of remote sites will be located
		self.__mountdir = None
		
		## the config manager from which to get the dir list to be mounted.
		self.__config = None
		
		## the list of all mounted dirs , should be filled by initialize.
		# It's a dict with key = remoteSource and value = mountpoint
		self.__mountedDirs = {}
		
		self.__config = configManager
		#sets the default mount dir 
		if self.__config and self.__config.has_option("general","mountdir") :
			self.__mountdir = self.__config.get("general","mountdir")
		else : 
			# set the defaults 
			if os.getuid() == 0 :
				self.__mountdir = "/mnt/nssbackup/"
			else : 
				self.__mountdir = getUserDatasDir()+"mountdir"

	
	def getMountedDirs(self):
		return self.__mountedDirs
	
	def mount(self,remotedir ):
		"""
		@return: the mounted dir
		"""
		global  __mountDirs
		if not os.path.exists(self.__mountdir):
			os.mkdir(self.__mountdir)
		
		plugin_manager = PluginManager()
		for p_name, p_class in plugin_manager.getPlugins().iteritems():
			try :
				#we got the plugin
				plugin = p_class()
				if plugin.matchScheme(remotedir):
					self.logger.debug("Processing with plugin '%s' to mount '%s'" % (p_name,remotedir))
					rsource,mpoint,pathinside = plugin.mount(remotedir, self.__mountdir)
					self.__mountedDirs[rsource] = mpoint
					return os.sep.join([mpoint,pathinside])
			except Exception, e :
				raise SBException("ERROR when trying to use plugin '%s' to mount '%s', disabling it ! Cause : %s"% (p_name,remotedir,str(e)))
		raise SBException("No plugin could deal with that schema '%s', disabling it" % remotedir)
	
	def __mount(self, remotedir):
		"""
		This will check if the remotedir is really remote and it will mount it if needed . 
		It will use the __mountdir param to know where to mount. It will also fill the __mountedDirs dict.
		And change the configManager to add the changes
		@param remotedir:
		@raise SBException:   
		"""
		global __config, __mountDirs
		plugin_manager = PluginManager()
		for p_name, p_class in plugin_manager.getPlugins().iteritems():
			try :
				#we got the plugin
				plugin = p_class()
				if plugin.matchScheme(remotedir):
					self.logger.debug("Processing with plugin '%s' to mount '%s'" % (p_name,remotedir))
					rsource,mpoint,pathinside = plugin.mount(remotedir, self.__mountdir)
					self.__mountedDirs[rsource] = mpoint
					if rsource != os.sep :
						#change the value in configManager
						if self.__config.has_option("general","target") and self.__config.get("general","target") == remotedir :
							self.logger.debug("change the value of target in configManager")
							self.__config.set("general","target",os.sep.join([mpoint,pathinside]))
							return 
						if self.__config.has_option("dirconfig",remotedir) :
							self.logger.debug("change the value of dirconfig option in configManager")
							self.__config.set("dirconfig",os.sep.join([mpoint,pathinside]),str(self.__config.get("dirconfig",remotedir)))
							self.__config.remove_option("dirconfig",remotedir)
							return 
					else :
						# The plugin used was localFuseFAM
						return True
			except Exception, e :
				self.logger.warning("ERROR when trying to use plugin '%s' to mount '%s', disabling it ! Cause : %s"% (p_name,remotedir,str(e)))
				if self.__config.has_option("dirconfig",remotedir) :
					self.logger.debug("Removing '%s' from configManager" % remotedir)
					self.__config.remove_option("dirconfig",remotedir)
				elif self.__config.has_option("general","target") and self.__config.get("general","target") == remotedir :
					self.logger.error("ERROR when trying to use plugin '%s' to mount target destination '%s' ! Cause : %s"% (p_name,remotedir,str(e)))
					raise SBException("We are unable to mount the target dir !")
				return False
		self.logger.warning("No plugin could deal with that schema '%s', disabling it" % remotedir)
		self.__config.remove_option("dirconfig",remotedir)
		
	def __umount(self, mounteddir):
		"""
		Unmount a mounted dir that should be in __mountedDirs dict
		@param mounteddir:
		
		@todo: Should we use lazy unmount (fusermount -z)?
		"""
		if not os.path.ismount(mounteddir) :
			# mountpoint is not mounted 
			return
		# Create output log file
		outptr,outFile = tempfile.mkstemp(prefix="fuseUmount_output_")
		# Create error log file
		errptr, errFile = tempfile.mkstemp(prefix="fuseUmount_error_")
		# Call the subprocess using convenience method
		retval = subprocess.call(["fusermount","-u",mounteddir], 0, None, None, outptr, errptr)
		# Close log handles
		os.close(errptr)
		os.close(outptr)
		outStr, errStr = FAM.readfile(outFile), FAM.readfile(errFile)
		FAM.delete(outFile)
		FAM.delete(errFile)
		self.logger.debug("fusermount output: %s\n%s" % (outStr, errStr))
		if retval != 0 :
			raise SBException("Couldn't unmount '%s' : %s" %  (mounteddir,errStr))
		
		
	def __keepAlive(self):
		"""
		Launch a command on the mounted dirs to keep the mount alive
		"""
		pass
	
	def initialize(self,keepAlive = False):
		"""
		Get the list of dir to mount and mount them. If the keep alive tag is set , it creates a Thread that will keep the mounted dir alive.
		@param keepAlive: Optional int that is used to determine the loop time (number of seconds) to keep the mount pint alive
		
		@todo: For later releases: The distinction between local and remote
			   sites must be improved in some way!  
		"""
		self.logger.info(_("Initializing FUSE File Access Manager."))
		global __mountdir
		if not self.__config : 
			raise SBException("Can't launch initialize without a configManager.")
		
		#sets the default mount dir 
		if self.__config.has_option("general","mountdir") :
			self.__mountdir = self.__config.get("general","mountdir")
		else : 
			# set the defaults 
			if os.getuid() == 0 :
				self.__mountdir = "/mnt/nssbackup/"
			else : 
				self.__mountdir = getUserDatasDir() + "mountdir"
		
		# check if the mount dir is valid
		if not os.path.exists(self.__mountdir) : 
			os.mkdir(self.__mountdir)
		else : 
			if not os.path.isdir(self.__mountdir) :
				raise SBException("The mount base dir should be a directory")
		
		#start the mount process
		#  mount target
		if self.__config.has_option("general","target"):
			if self.__config.get("general","target").startswith(os.sep) :   # this assumes absolute paths
				if not os.path.exists(self.__config.get("general","target")) :
					raise exceptions.FuseFAMException(_("Target directory '%(target)s' does not exist.")\
										% {"target" : self.__config.get("general","target")} )
			else: # this means remote target
				self.__mount(self.__config.get("general","target"))

		#mount dirs from dirconfig if needed
		if self.__config.has_section("dirconfig") and self.__config.has_option("dirconfig", "remote") :
			remotes = self.__config.get("dirconfig", "remote")
			if type(remotes) == str :
				remotes = eval(remotes)
			if type(remotes) != dict :
				raise SBException("Couldn't eval '%s' as a dict (value got = '%r' )"% (remotes,type(remotes)))
			self.logger.debug("remotes : '%s'" % remotes)
			for source,flag in remotes.iteritems() :
				#TODO : check for multiple mount
				mounted = False
				for rsource, mountpoint in self.__mountedDirs.iteritems() :
					if source.startswith(rsource) :
						self.logger.debug("'%s' is already in mounted scope" % source)
						mounted = True
						#change the reference in config manager
						self.logger.debug("change the value of dirconfig option in configManager")
						#we don't touch config for localfiles
						if rsource != os.sep :
							if not mountpoint.endswith(os.sep) :
								mountpoint = mountpoint+os.sep
							self.__config.set("dirconfig",source.replace(rsource, mountpoint,1), flag)
							self.__config.remove_option("dirconfig",source)
							break
				if not mounted :
					self.__mount(source)
		self.__config.remove_option("dirconfig","remote")
		
		#remove non needed entry in mountDirs
#		try :
#			self.__mountedDirs.pop(os.sep)
#		except KeyError, e :
#			self.logger.warning("No local directory were found in config  ! This is either a bug or you're doing everything remotely : '%s'" % str(e))
#			
		self.logger.debug(str(self.__config))
		
	def terminate(self):
		"""
		Unmount all nssbackup mounted dir.
		"""
		self.logger.info(_("Terminating FUSE File Access Manager."))
		plugin_manager = PluginManager()
		for src, dir in self.__mountedDirs.iteritems() :
			if src is not os.sep :
				_umounted = False
				for p_name, p_class in plugin_manager.getPlugins().iteritems():
					#we got the plugin
					self.logger.debug("Trying '%s' plugin to match '%s' " % (p_name,src))
					plugin = p_class()
					if plugin.matchScheme(src):
						self.logger.debug("Unmounting with '%s' plugin " % p_name)
						plugin.umount(dir)
						os.rmdir(dir)
						_umounted = True
						break
				if not _umounted:
					self.logger.warning("Couldn't unmount %s " % dir)

	def testFusePlugins(self, remotedir):
		"""The given remote directory is applied to any found plugins to
		decide whether one of the plugins is able to handle this (remote)
		protocol. The tests cover:
		* checking of the adress scheme and the validity of the adress
		* mounting of the remote site
		* write and read access on the remote site.
		
		If no plugin is able to handle the given path, an exception is
		raised.
		
		@todo: Customize the raised exception to provided more informations!
		"""
		if remotedir.startswith(os.sep) :
			raise SBException("Nothing to do for localpath '%s'." %remotedir)
		# set the defaults 
		if os.getuid() == 0 :
			mountdir = "/mnt/nssbackup/"
		else : 
			mountdir = getUserDatasDir()+ "mountdir"
		
		# check if the mount dir is valid
		if not os.path.exists(mountdir) : 
			os.mkdir(mountdir)
			
		plugin_manager = PluginManager()
		_plugins = plugin_manager.getPlugins()
		_iterator = _plugins.iteritems()
		for p_name, p_class in _iterator:
			try :
				#we got the plugin
				self.logger.debug("Testing of plugin '%s'" % str( p_name ))
				plugin = p_class()
				if plugin.matchScheme(remotedir):
					self.logger.debug("Processing with plugin '%s' to mount '%s'" % (p_name, remotedir))
					rsource,mpoint,pathinside = plugin.mount(remotedir, mountdir)
					self.logger.debug("Mount Succeeded !")
					#write
					self.logger.debug("Testing Writability")
					test = "testFuseFam"
					testfile = os.path.join( mpoint, pathinside, test )
					os.mkdir(testfile)
					os.rmdir(testfile)
					# Unmount 
					self.logger.debug("Unmounting !")
					self.__umount(mpoint)
					if os.path.exists(mpoint):
						self.logger.debug("Removing mount dir")
						os.rmdir(mpoint)
					return True
			except Exception, e :
				raise SBException("Failed : %s "%str(e))
		raise SBException("No plugin could deal with that schema '%s'" % remotedir)
		
		