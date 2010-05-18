#	NSsbackup - snapshot handling
#
#   Copyright (c)2007-2008: Ouattara Oumar Aziz <wattazoum@gmail.com>
#   Copyright (c)2008-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
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
:mod:`BackupManager` --- backup handler class
====================================================================

.. module:: BackupManager
   :synopsis: Defines a backup handler class
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

from gettext import gettext as _
import os
import grp
import datetime
import re
import socket
import gobject
import types

from FuseFAM import FuseFAM
from SnapshotManager import SnapshotManager
from UpgradeManager import UpgradeManager
from ConfigManager import ConfigManager
import FileAccessManager as FAM
import nssbackup.util as Util
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.log import LogFactory
from nssbackup.util import exceptions

from nssbackup.util.tar import SnapshotFile


class PyNotifyMixin(object):
	"""Mix-in class that provides the displaying of notifications using the
	pynotify module. The notifications use the icon 'nssbackup32x32.png'.
	
	:todo: This is not the right place for the definition!
	:todo: It would be more general if we give the icon to use as parameter!
	
	"""
	def __init__(self, logger):
		"""Default constructor.
		
		:param logger: Instance of logger to be used.
		
		:todo: The notification domain should be retrieved from a central place!
		
		"""
		self.__logger = logger

		# internal flag whether the notification module is usable
		self.__pynotif_avail = False
		
		# the pynotify module is stored in this variable
		self.__pynotif_mod   = None
		
		# the current notification
		self.__notif = None
		
		# trying to initialize the notification module
		try:
			import pynotify
			self.__pynotif_mod = pynotify
			if self.__pynotif_mod.init("NSsbackup"):
				self.__pynotif_avail = True
				self.__logger.debug("Module 'pynotify' was sucessfully initialized.")
			else:
				self.__pynotif_avail = False	# yes, this is insane!
				self.__logger.warning(_("Initialization of module 'pynotify' failed."))
		except ImportError, exc:
			self.__pynotif_avail = False
			self.__logger.warning(_("Import of module 'pynotify' failed with error: %s.") % str(exc))
		
	def _notify_info(self, profilename, message):
		"""Shows up a pop-up window to inform the user. The notification
		supports mark-up.		

 		:param message: The message (body) that should be displayed.
 		:type message:  String
 		
		"""
		if self.__pynotif_avail:
			if self.__notif is None:
				self.__notif = self.__get_notification(profilename, message)
			else:
				self.__update_notification(profilename, message)
				
			if isinstance(self.__notif, self.__pynotif_mod.Notification):
				try:
					self.__notif.set_urgency(self.__pynotif_mod.URGENCY_LOW)
					self.__notif.show()
				except gobject.GError, exc:
					# Connection to notification-daemon failed 
					self.logger.warning(_("Connection to notification-daemon "\
										"failed: %s.") % str(exc))

	def _notify_warning(self, profilename, message):
		"""Shows up a pop-up window to inform the user. The notification
		supports mark-up.		

 		:param message: The message (body) that should be displayed.
 		:type message:  String
 		
		"""
		self.__notify_new(profilename, message, mode="warning")

	def _notify_error(self, profilename, message):
		"""Shows up a pop-up window to inform the user that an error occured.
		Such error notifications are emphasized and must be closed manual. The
		notifications support mark-up.

 		:param message: The message (body) that should be displayed.
 		:type message:  String
 		
		"""
		self.__notify_new(profilename, message, mode="critical")
				
	def __notify_new(self, profilename, message, mode):
		"""Shows up a *new* pop-up window to inform the user that an error occured.
		Such error notifications are emphasized and must be closed manual. The
		notifications support mark-up.

 		:param message: The message (body) that should be displayed.
 		:type message:  String
 		
		"""
		if self.__pynotif_avail:
			notif = self.__get_notification(profilename, message)
			if isinstance(notif, self.__pynotif_mod.Notification):
				try:
					notif.set_timeout(self.__pynotif_mod.EXPIRES_NEVER)
					if mode == "critical":
						notif.set_urgency(self.__pynotif_mod.URGENCY_CRITICAL)
					else:
						notif.set_urgency(self.__pynotif_mod.URGENCY_NORMAL)
					notif.show()
				except gobject.GError, exc:
					# Connection to notification-daemon failed 
					self.logger.warning(_("Connection to notification-daemon "\
										"failed: %s.") % str(exc))

	def __get_notification(self, profilename, message):
		"""Returns a notification object but does not display it. The
 		notification supports mark-up. If notifications aren't supported
 		the method returns None.
 		
 		:param message: The message (body) that should be displayed.
 		:type message:  String
 		
 		:return: The created notification object or None
 		:rtype: Notification or None
		
		:todo: Replace single '<' characters by '&lt;' in a more reliable way!
		:todo: The header and the icon should be given as parameter to make
			   this mix-in class more generic!
			   
		"""
		notif = None
		if self.__pynotif_avail:
			message = message.replace("<", "&lt;")
			ico = Util.get_resource_file("nssbackup32x32.png")
			try:
				notif = self.__pynotif_mod.Notification(
								"NSsbackup [%s]" % profilename, message, ico)
			except gobject.GError, exc:
				# Connection to notification-daemon failed 
				self.logger.warning(_("Connection to notification-daemon "\
									"failed: %s.") % str(exc))
				notif = None
		return notif

	def __update_notification(self, profilename, message):
		""" 		
 		:param message: The message (body) that should be displayed.
 		:type message:  String
 		
		:todo: Replace single '<' characters by '&lt;' in a more reliable way!
		:todo: The header and the icon should be given as parameter to make
			   this mix-in class more generic!
			   
		"""
		if self.__pynotif_avail:
			message = message.replace("<", "&lt;")
			ico = Util.get_resource_file("nssbackup32x32.png")
			try:
				self.__notif.update(
								"NSsbackup [%s]" % profilename, message, ico)
			except gobject.GError, exc:
				# Connection to notification-daemon failed 
				self.logger.warning(_("Connection to notification-daemon "\
									"failed: %s.") % str(exc))
				self.__notif = None
				
				
class BackupManager(PyNotifyMixin):
	"""Class that handles a *single* backup process defined by given
	configuration (profile).
	
	:todo: The BackupManager should not does any GUI related tasks!
	
	"""	
	def __init__(self, configmanager):
		"""The BackupManager Constructor.

		:param configmanager : The current configuration manager
		
		:note: Make sure to call for the appropriate logger before\
			   instantiating this class!
			   
		"""
		self.config			= configmanager
		self.logger			= LogFactory.getLogger()
		self.__profilename	= self.config.getProfileName()
		
		self.__um			= UpgradeManager()
		self.__snpman		= None
		
		# The whole snapshot path
		self.__actualSnapshot = None
		
		self.__lockfile 	= None
		
		self.__includeInSnp = None
		
		self.__fusefam		= FuseFAM(self.config)
		
		PyNotifyMixin.__init__(self, self.logger)
		self.logger.debug("Instance of BackupManager created.")
		
	def makeBackup(self ):
		"""Runs the whole backup process:
		
		1. create lock and initialize file systems
		3. check pre-conditions
		4. test for upgrades (but don't perform)
		5. purge snapshots (if configured)
		6. open new snapshot containing common metadata (full or incr.
			depending on existing one, base, settings etc.)
		7. fill new snapshot (with packages list, include lists, exclude lists,
			size prediction)
		8. commit new snapshot to disk (creates the actual tar archive and
			writes everything into the snapshot directory).
		9. release lock
		"""
		self.__setlockfile()

		_msg = _("Backup process is being started.")
		self._notify_info(self.__profilename, _msg)
		self.logger.info(_msg)
		
		try:
			self.__fusefam.initialize()
		except exceptions.FuseFAMException:
			self.__fusefam.terminate()
			raise
		
		self.__snpman = SnapshotManager(self.config.get("general","target"))
		
		# Set the admin group to the process
		if os.geteuid() == 0 :
			try :
				# The uid is still root and the gid is admin
				os.setgid( grp.getgrnam("admin").gr_gid )				
			except (KeyError, OSError), exc: 
				self.logger.warning(_("Failed to set the gid to 'admin' one :") + str(exc))

		# Check the target dir
		self.__checkTarget()
		
		# Upgrade Target
		# But we should not upgrade without user's agreement!
		# Solution 1: add an option: AutoAupgrade = True/False
		#          2: start with a new and full dump and inform the user that
		#			  there are snapshots in older versions 
		needupgrade = False
		try:
			needupgrade = self.__um.need_upgrade(self.config.get("general",
																  "target"))
		except exceptions.SBException, exc:
			self.logger.warning(str(exc))

		if needupgrade:
			_msg = "There are snapshots with old snapshot format."\
				   " Please upgrade them if you want to use them."
			self._notify_warning(self.__profilename, _msg)
			self.logger.warning(_msg)
		
		# purge
		purge = None
		if self.config.has_option("general", "purge"):
			purge = self.config.get("general", "purge")
		if purge :
			self.__snpman.purge(purge)
				
		# get basic informations about new snapshot
		(snppath, base) = self.__retrieve_basic_infos()
		
		# Create a new snapshot
		self.__actualSnapshot = Snapshot(snppath)
		self.logger.info(_("Starting snapshot %(name)s ")
						 % {'name' :str(self.__actualSnapshot)})
		
		# Set the base file
		if base :
			if self.__actualSnapshot.isfull():
				self.logger.debug("Base is not being set for this full snapshot.")
			else:
				self.logger.info(_("Setting Base to '%(value)s' ") % {'value' : str(base)})
				self.__actualSnapshot.setBase(base.getName())
		del base

		# Backup list of installed packages
		_packagecmd = "dpkg --get-selections"
		if self.config.has_option("general", "packagecmd"):
			_packagecmd = self.config.get("general", "packagecmd")
		if _packagecmd:
			try:
				self.logger.info(_("Setting packages File."))
				s = os.popen( _packagecmd )
				pkg = s.read()
				s.close()
				self.__actualSnapshot.setPackages(pkg)
			except Exception, _exc:
				self.logger.warning(_("Problem when setting the packages: ") + str(_exc))
		
		# set Excludes
# TODO: improve handling of Regex containing ',' (delimiter); currently this will crash
		self.logger.info(_("Setting Excludes File."))
		if self.config.has_option("exclude", "regex"):
			gexclude = str(self.config.get("exclude", "regex")).split(",")
		else :
			gexclude = ""
		self.__actualSnapshot.setExcludes(gexclude)
		
		# set format
		self.logger.info(_("Setting compression format."))
		if self.config.has_option("general", "format"):
			self.__actualSnapshot.setFormat(self.config.get("general","format"))
			
		# set splited size
		self.logger.info(_("Setting split size."))
		if self.config.has_option("general", "splitsize"):
			self.__actualSnapshot.setSplitedSize(int(self.config.get("general","splitsize")))
		
		# set followlinks
		self.__actualSnapshot.setFollowLinks(self.config.get_followlinks())
		if self.__actualSnapshot.isFollowLinks():
			self.logger.info(_("Option 'Follow symbolic links' is enabled."))
		else:
			self.logger.info(_("Option 'Follow symbolic links' is disabled."))

		os.nice(20)					# Reduce the priority, so not to interfere with other processes
		self.__fillSnapshot()					
		self._notify_info(self.__profilename, _("File list ready, committing to disk."))				
		self.__actualSnapshot.commit()
		
	def __fillSnapshot(self):
		"""Fill snapshot's include and exclude lists and retrieve some information
		about the snapshot (uncompressed size, file count).
		"""
		_collector = self.__create_collector_obj()
		_collector.collect_files()
		_stats = _collector.get_stats()		
		_snpsize = _stats.get_size_payload() + _stats.get_size_overhead(size_per_item=512)		

		vstat = os.statvfs(self.__actualSnapshot.getPath())
		_freespace = vstat.f_bavail * vstat.f_bsize
		
		_snpsize_hr = Util.get_humanreadable_size_str(size_in_bytes=_snpsize, binary_prefixes=True)
		_freespace_hr = Util.get_humanreadable_size_str(size_in_bytes=_freespace, binary_prefixes=True)
		self.logger.info(_("Maximum free size required is '%s'.") % _snpsize_hr)
		self.logger.info(_("Available disk size is '%s'.") % _freespace_hr)
		self.logger.info(_("Number of directories: %s.") % _stats.get_count_dirs())
		self.logger.info(_("Number of symlinks: %s.") % _stats.get_count_symlinks())
		self.logger.info(_("Total number of files: %s.") % _stats.get_count_files_total())
		self.logger.info(_("Number of files included in snapshot: %s.") % _stats.get_count_files_incl())
		self.logger.info(_("Number of new files (also included): %s.") % _stats.get_count_files_new())
		self.logger.info(_("Number of files skipped in incremental snapshot: %s.") % _stats.get_count_files_skip())
		self.logger.info(_("Number of items forced to be excluded: %s.") % _stats.get_count_items_excl_forced())
		self.logger.info(_("Number of items to be excluded by config: %s.") % _stats.get_count_items_excl_config())
		
		if _freespace <= _snpsize:
			raise exceptions.SBException(_("Not enough free space in the target directory for the "\
										   "planned backup (%(freespace)s <= %(neededspace)s).")\
										   % { 'freespace' : _freespace_hr, 'neededspace' : _snpsize_hr})

	def __create_collector_obj(self):
		"""Factory method that returns instance of `FileCollector`.
		"""
		_config = FileCollectorConfigFacade(self.config)
		_collect = FileCollector(self.__actualSnapshot, _config)
		if not self.__actualSnapshot.isfull():
			_base = self.__actualSnapshot.getBaseSnapshot()
			_basesnar = _base.getSnapshotFileInfos().get_snapfile_obj()
			_collect.set_parent_snapshot(_basesnar)
		return _collect
				
	def __setlockfile(self):
		"""Set the lockfile.
		
		@todo: Lock file should be created and removed in daemon!
		"""
		if self.config.has_option("general", "lockfile") :
			self.__lockfile = self.config.get("general", "lockfile")
		else :
			self.logger.debug("no lockfile in config, the default will be used ")
			self.__lockfile = "/var/lock/nssbackup.lock"
		
		# Create the lockfile so none disturbs us
		if FAM.exists(self.__lockfile) :
			# the lockfile exists, is it valid ?
			last_sb_pid = FAM.readfile(self.__lockfile)
			if (last_sb_pid and os.path.lexists("/proc/"+last_sb_pid) and\
				"nssbackupd" in str(open("/proc/"+last_sb_pid+"/cmdline").read())):
					raise exceptions.InstanceRunningError(\
					_("Another instance of '(not so) Simple Backup' is already running (process id: %s).")\
					  % last_sb_pid )
			else:
				self.logger.info(_("Invalid lock file found. Is being removed."))
				self.__unsetlockfile()
		
		FAM.writetofile(self.__lockfile, str(os.getpid()))
		self.logger.debug("Created lockfile at '%s' with info '%s'."\
						  % (self.__lockfile, str(os.getpid()) ))
		
	def __unsetlockfile(self):
		"""Remove lockfile.
		"""
		try:
			FAM.delete(self.__lockfile)
			self.logger.debug("Lock file '%s' removed."	% self.__lockfile)
		except OSError, _exc:
			self.logger.error(_("Unable to remove lock file: %s" % str(_exc)))
			
	def __copylogfile(self):
		# destination for copying the logfile
		if self.__actualSnapshot:
			logf_src = self.config.get_logfile()
			logf_name = os.path.basename(logf_src)
			logf_target = os.path.join( self.__actualSnapshot.getPath(),
									    logf_name )
			if FAM.exists(logf_src):
				try:
					Util.nssb_copy( self.config.get("log","file"), logf_target )
				except exceptions.ChmodNotSupportedError:
					self.logger.warning(_("Unable to change permissions for "\
										  "file '%s'.") % logf_target )
			else :
				self.logger.warning(_("Unable to find logfile to copy into snapshot."))
		else:
			self.logger.warning(_("No snapshot to copy logfile."))
		
	def endSBsession(self):
		"""End nssbackup session :
		
		- copy the log file into the snapshot dir
		- remove the lockfile
		
		If this method is called it is unsure whether the backup was
		successful or not.
		"""
		self.__unsetlockfile()
		self.__copylogfile()			
		self.__fusefam.terminate()
		
		_msg = _("Backup process finished.")
		self._notify_info(self.__profilename, _msg)
		self.logger.info(_msg)

	def __checkTarget(self):
		"""
		"""
		# Check if the mandatory target option exists
		if not self.config.has_option("general","target") :
			raise exceptions.SBException (_("Option 'target' is missing, aborting."))
		
		# Check if the target dir exists or create it
		if not FAM.exists(self.config.get("general","target")) :
			self.logger.info(_("Creating the target dir '%s'") % self.config.get("general","target"))
			FAM.makedir(self.config.get("general","target"))
		
		# Try to write inside so that we don't work for nothing
		_testfile = os.path.join(self.config.get("general","target"), "test")
		try :
			
			FAM.writetofile(_testfile, "testWritable")
			FAM.delete(_testfile)
		except Exception, e :
			self.logger.error(_("Target not writeable: ") + str(e))
			raise e
	
	def __retrieve_basic_infos(self):
		"""Retrieves basic informations about the snapshot that is going
		to be created. This informations include:
		1. the path of the new snapshot
		2. the base of the new snapshot
		
		:param listing: a list of snapshots
		
		:return: the determined `snppath` and `base`
		:rtype: a tuple
		
		"""
		# Get the list of snapshots that matches the latest snapshot format
		listing = self.__snpman.get_snapshots()

		base = None
		if len(listing) == 0 :
			#no snapshots
			increment = False
		else:
			# we got some snaphots 
			# we search for the last full 
			base = listing[0]
			if listing[0].isfull() :  # Last backup was full backup
				self.logger.debug("Last (%s) was a full backup" % listing[0].getName())
				d = listing[0].getDate()
				if ( datetime.date.today() - datetime.date(d["year"],d["month"],d["day"]) ).days < self.config.get("general","maxincrement") :
					# Less than maxincrement days passed since that -> make an increment
					increment = True
				else:
					self.logger.info("Last full backup is old -> make a full backup")
					increment = False      # Too old -> make full backup
			else: # Last backup was an increment - lets search for the last full one
				self.logger.debug(" Last backup (%s) was an increment - lets search for the last full one" % listing[0].getName())
				for i in listing :
					if i.isfull():
						d = i.getDate()
						age = (datetime.date.today() - datetime.date(d["year"],d["month"],d["day"]) ).days
						if  age < int(self.config.get("general","maxincrement")) :
							# Last full backup is fresh -> make an increment
							self.logger.info("Last full backup is fresh (%d days old )-> make an increment" % age )
							increment = True
						else: # Last full backup is old -> make a full backup
							self.logger.info("Last full backup is old -> make a full backup")
							increment = False
						break
				else:
					self.logger.info("No full backup found -> lets make a full backup to be safe")
					increment = False
		
		# Determine and create backup target directory
		hostname = socket.gethostname()
		snpname = "%s.%s" % (datetime.datetime.now().isoformat("_").replace( ":", "." ),
							 hostname)
		if increment:
			snpname = "%s.inc" % snpname
		else:
			snpname = "%s.ful" % snpname
		
		tdir = os.path.join(self.config.get("general","target"), snpname)
			
		return (tdir, base)

	def getActualSnapshot(self):
		"""Apparently unused at the moment!
		
		get the actual snapshot
		"""
		return self.__actualSnapshot


class FileCollectorStats(object):
	"""Provides statistical information about files collected by `FileCollector` objects.
	These information encompass:
	* size of files being backuped
	* number of files being backuped.
	"""
	
	def __init__(self, followlinks = False):
		self.__followlinks = False
		self.set_followlinks(followlinks)
		# uncompressed size of snapshot (cummulative)
		self.__size_in_bytes = 0L
		
		self.__ndirs  = 0L
		self.__nfiles = 0L
		self.__nsymlinks = 0L

		# for incremental counting (in case of full snapshot only `__nfile_incl` is used)
		self.__nfiles_incl = 0L
		self.__nfiles_skip = 0L
		self.__nfiles_new = 0L

		self.__nexcl_forced = 0L
		self.__nexcl_config = 0L

	def set_followlinks(self, followlinks):
		if not isinstance(followlinks, types.BooleanType):
			raise TypeError("Expected parameter of boolean type. "\
							"Got %s instead." % type(followlinks))
		self.__followlinks = followlinks
		
	def get_size_payload(self):
		"""Returns the cumulated size of files being backuped in bytes.
		Additional overhead due to storage etc. is not considered.
		"""
		return self.__size_in_bytes

	def get_size_overhead(self, size_per_item):
		"""Returns the cumulated size of overhead produced by files being backuped.
		The overhead is calculated based on the number of files and their overhead
		per file given as parameter.
		"""
		if not isinstance(size_per_item, types.IntType):
			raise TypeError("Expected parameter of integer type. "\
							"Got %s instead." % type(size_per_item))
		_overhead = (self.__ndirs + self.__nfiles_incl) * size_per_item
		if not self.__followlinks:
			_overhead += self.__nsymlinks * size_per_item
		return _overhead
	
	def get_count_files_total(self):
		"""Returns the number of files.
		"""
		return self.__nfiles

	def get_count_files_incl(self):
		"""Returns the number of files.
		"""
		return self.__nfiles_incl

	def get_count_files_skip(self):
		"""Returns the number of files.
		"""
		return self.__nfiles_skip

	def get_count_files_new(self):
		"""Returns the number of new included files.
		"""
		return self.__nfiles_new

	def get_count_dirs(self):
		"""Returns the number of files.
		"""
		return self.__ndirs

	def get_count_symlinks(self):
		"""Returns the number of files.
		"""
		return self.__nsymlinks

	def get_count_items_excl_forced(self):
		"""Returns the number of files.
		"""
		return self.__nexcl_forced

	def get_count_items_excl_config(self):
		"""Returns the number of files.
		"""
		return self.__nexcl_config
	
	def clear(self):
		"""Clears collected data.
		"""
		self.__size_in_bytes = 0L		
		self.__ndirs  = 0L
		self.__nfiles = 0L
		self.__nsymlinks = 0L
		self.__nfiles_incl = 0L
		self.__nfiles_skip = 0L
		self.__nexcl_forced = 0L
		self.__nexcl_config = 0L
		self.__nfiles_new = 0L

	def add_size(self, value):
		"""The given value is added to the cumulated file size.
		"""
		self.__size_in_bytes += value
		
	def count_file(self):
		"""The file counter is increased by 1.
		"""
		self.__nfiles += 1

	def count_incl_file(self):
		self.__nfiles_incl += 1

	def count_new_file(self):
		self.__nfiles_new += 1
		
	def count_skip_file(self):
		self.__nfiles_skip += 1

	def count_dir(self):
		"""The file counter is increased by 1.
		"""
		self.__ndirs += 1
		
	def count_symlink(self):
		self.__nsymlinks += 1
		
	def count_excl_forced(self):
		self.__nexcl_forced += 1
	
	def count_excl_config(self):
		self.__nexcl_config += 1

		
class FileCollectorParentSnapshotFacade(object):
	"""Class that provides simplified access to attributes of the parent
	snapshot (the base). The class is designed for use with `FileCollector`.
	"""
	
	def __init__(self):
		self.__logger = LogFactory.getLogger()
		# snapshot file (snar) of current snapshot's parent (base snapshot)
		# only set if the current one is incremental
		self.__base_snar 		= None
		self.__base_backup_time	= None
		self.__base_snardict 	= None
		
	def set_base_snar(self, basesnar):
		"""Sets the snapshot file (snar) of the base (parent) snapshot.
		
		@note: This implies that the current snapshot is incremental.
		
		"""
		if not isinstance(basesnar, SnapshotFile):
			raise TypeError("Expected parameter of type 'SnapshotFile'. "\
							"Got %s instead." % type(basesnar))
		self.__base_snar = basesnar
		self.__set_base_backup_time(basesnar.get_time_of_backup())
		self.__set_base_snardict(basesnar.get_dict_format2())

	def __set_base_backup_time(self, backup_time):
		"""Sets the time the parent backup was created. The time is
		measured in seconds since beginning of the epoch (unix style).
		"""
		if not isinstance(backup_time, types.FloatType):
			raise TypeError("Expected parameter of floar type. "\
							"Got %s instead." % type(backup_time))
		self.__logger.debug("Backup time of parent snapshot: %s" % backup_time)
		self.__base_backup_time = backup_time		

	def __set_base_snardict(self, snardict):
		"""Sets the dictonary containing the parent snapshot file (snar file).
		"""
		if not isinstance(snardict, types.DictionaryType):
			raise TypeError("Expected parameter of dictionary type. "\
							"Got %s instead." % type(snardict))
		self.__base_snardict = snardict

	def get_base_snardict(self):
		"""Returns the dictonary containing the parent snapshot file (snar file).
		"""
		return self.__base_snardict
	
	def get_base_backup_time(self):
		"""Returns the time the parent backup was created.
		"""
		return self.__base_backup_time
	
	
class FileCollector(object):
	"""Responsible for the process of collecting files that are being backuped.
	The collecting process comprises of:
	
	* check the files are readable/accessable
	* apply exclusion rules (Regex) defined by user to the list of files
	* calculate the required space for the backup
	* prepare include and exclude file lists used by the backup process.
	"""
	
	def __init__(self, snapshot, configuration):
		self.__logger			= LogFactory.getLogger()

		# current snapshot (the new one)
		self.__snapshot 		= None
		# flag whether the current snapshot is full or incremental
		self.__isfull 			= True
		
		self.__parent			= FileCollectorParentSnapshotFacade()
		self.__collect_stats 	= FileCollectorStats()		
		self.__configuration	= None
		
		# stats of last processed file
		self.__exists_func		= None
		self.__stat_func		= None
		self.__fstats 			= None
		self.__fislink			= None
		self.__fisdir			= None
		# list of Regular Expressions defining exclusion rules
		self.__excl_regex 		= []
# TODO: put list of compiled regex into `Snapshot` (i.e. compile them when setting the excludes). 
		
		self.set_snapshot(snapshot)
		self.set_configuration(configuration)

	def set_snapshot(self, snapshot):
		"""Sets the given snapshot as the currently processed snapshot.
		"""
		if not isinstance(snapshot, Snapshot):
			raise TypeError("Expected parameter of type 'Snapshot'. "\
							"Got %s instead." % type(snapshot))
		self.__snapshot = snapshot
		self.__set_isfull(isfull=snapshot.isfull())
		self.__collect_stats.set_followlinks(followlinks=snapshot.isFollowLinks())

	def set_configuration(self, configuration):
		"""Sets the given object of type `FileCollectorConfigFacade`.
		"""
		if not isinstance(configuration, FileCollectorConfigFacade):
			raise TypeError("Expected parameter of type 'FileCollectorConfigFacade'. "\
							"Got %s instead." % type(configuration))
		self.__configuration = configuration
		
	def set_parent_snapshot(self, parent):
		"""Sets the snapshot file (snar) of the base (parent) snapshot.
		
		@note: This implies that the current snapshot is incremental.
		
		"""
		if not isinstance(parent, SnapshotFile):
			raise TypeError("Expected parameter of type 'SnapshotFile'. "\
							"Got %s instead." % type(parent))
		self.__set_isfull(isfull=False)
		self.__parent.set_base_snar(parent)
		
	def get_stats(self):
		"""Returns the collector stats object.
		"""
		return self.__collect_stats
		
	def __prepare_collecting(self):
		"""The actual process of collecting is prepared (i.e. stats are cleared etc.).
		
		@note: Depending on setting `Follow links` are functions for testing file existance and
			   retrieval of file stats selected here.
		"""
		if self.__snapshot.isFollowLinks():
			self.__exists_func = os.path.exists
			self.__stat_func = os.stat
		else:
			self.__exists_func = os.path.lexists
			self.__stat_func = os.lstat
		self.__collect_stats.clear()

	def __set_isfull(self, isfull):
		"""Sets attribute `__isfull` to the given boolean value.
		
		Attribute `__isfull` is introduced because of performance concerns
		since the snapshot derives this information from its name on every
		request again.  
		"""
		if not isinstance(isfull, types.BooleanType):
			raise TypeError("Expected parameter of boolean type. "\
							"Got %s instead." % type(isfull))
		self.__isfull = isfull
		# test of post-condition: isfull must be equal to the value in the snapshot
		if self.__isfull != self.__snapshot.isfull():
			raise AssertionError("Values of attribute 'isfull' are "\
								 "inconsistent. Found value in snapshot: %s."\
								 % self.__snapshot.isfull())

	def __is_not_accessable(self, path):
		"""Tests whether the given `path` can be accessed (i.e. exists and is readable).
		"""
		# return true if the file doesn't exist
		try:
			if not self.__exists_func(path):
				self.__logger.warning(_("File '%(file)s' does not exist.") % {'file' : path})
				return True
		except OSError:
			return True
		
		# get the stats, If not possible, the file has to be exclude, return True
		try:
			self.__fstats = self.__stat_func(path)
			self.__fisdir = FAM.is_dir(path)
			self.__fislink = FAM.is_link(path)
		except Exception, _exc:	#IGNORE:W0703
			self.__logger.warning(_("File '%(file)s' is not accessable with error '%(error)s'.")\
									% {'file' : path, 'error' : str(_exc)})
			self.__fstats = None
			self.__fisdir = None
			self.__fislink = None
			return True

		# refuse a file if we don't have read access
		# The open() statement may hang indefinitely (LP Bug 184713)
		# taken from: http://docs.python.org/library/signal.html#example
		_res = False
		try:
			Util.set_timeout_alarm(timeout=5)
			fdscr = os.open(path, os.R_OK)  
			os.close(fdscr)
		except exceptions.TimeoutError, _exc:
			self.__logger.warning(_("File '%(file)s' cannot be opened for read access. Operation timed out.")\
									% {'file' : path})
			_res = True
		except Exception, _exc:	#IGNORE:W0703
			self.__logger.warning(_("File '%(file)s' cannot be opened for read access with error '%(error)s'.")\
									% {'file': path, 'error' : str(_exc)})
			_res = True

		Util.set_timeout_alarm(timeout=0)
			# when file does not exist, the `open` fails and variable `fdscr` is not defined here
#			try:
#				os.close(fdscr)
#			except OSError:
#				pass	
		return _res

	def __is_excluded_by_default(self, path):
		"""Tests whether the given `path` is excluded by default. Currently the
		path is excluded by default in the case it is the target directory. 
		"""
		if path == self.__configuration.get_target_dir():
			self.__logger.info(_("File '%(file)s' is backup's target directory.") % {'file' : path})
			return True			
		return False
	
	def __is_circular_symlink(self, path):
		if self.__fislink:
			if self.__snapshot.isFollowLinks():
				ln_target = FAM.get_link_abs(path)	
				if path.startswith(ln_target):
					self.__logger.info(_("Symbolic link '%(path)s' -> '%(ln_target)s' is a circular symlink.")\
								% {'path' : path, 'ln_target' : ln_target})
					return True		
		#test passed
		return False

	def _is_excluded_by_config(self, path):
		"""Decides whether or not a file is to be excluded by the configuration.
		It is not decided for the incremental exclusion.

		Currently, following configuration options are tested:
		* file size
		* regular expressions
		* list of explicitely defined exclusions.
				
		@return: True if the file has to be excluded, false if not
		"""
		#if the file is too big
		if self.__configuration.is_maxsize_enable():
			if self.__fstats.st_size > self.__configuration.get_maxsize_limit():
				self.__logger.info(_("File '%(file)s' exceeds maximum file size ( %(filesize)s > %(maxsize)s).")\
									% {'file' : path, 'filesize' : str(self.__fstats.st_size),
									   'maxsize' : str(self.__configuration.get_maxsize_limit())})
				return True
		
		# if the file matches an exclude regexp, return true
# TODO: Regex are applied to the full path. Add a choice to apply Regex only to files, directories etc.
		for _regex in self.__excl_regex:
			_regex_res = _regex.search(path)
			if _regex_res is not None:
				self.__logger.info(_("File '%(file)s' matches regular expression '%(regex)s'.")\
									% {'file' : path, 'regex' : str(_regex.pattern)})
				return True
				
		# if the file is in exclude list, return true
		if self.__snapshot.is_path_in_excl_filelist(path):
			self.__logger.info(_("File '%(file)s' found in defined exclude list.") % {'file' : path})
			return True		
		#all tests passed
		return False
	
	def _is_excluded_by_force(self, path):
		"""Private interface method which checks for forced exclusion of given `path` by
		calling the according test methods in turn. If this method returns True, the
		path *must* be excluded irrespectively it is explicitely included etc.

		@return: True if the file has to be excluded, false if not
		"""
		_res = False
		if self.__is_excluded_by_default(path) is True:
			_res = True
		elif self.__is_not_accessable(path) is True:
			_res = True
		elif self.__is_circular_symlink(path) is True:
			_res = True
		return _res
		
	def _check_for_excludes(self, path): #, force_exclusion=False):
		"""Checks given `path` for exclusion and adds it to the `ExcludeFlist` if
		required. Sub-directories are only entered in the case the `path` is not
		excluded.
		
		@param path: The path being checked for exclusion
		
		@note: Links are always backuped; TAR follows links (i.e. dereferences them = stores the actual
			   content) only if option `followlinks` is set. A link targeting a directory yields
			   'islink=True' and 'isdir=True'. 
		"""
		_excluded = False
		_stop_checking = False

		if self._is_excluded_by_force(path):
			# force exclusion e.g. path is defined in includes list but does not exist/is not accessable
			self.__snapshot.addToExcludeFlist(path)
			self.__collect_stats.count_excl_forced()
			_excluded = True
			
		elif self._is_excluded_by_config(path):
			if not self.__snapshot.is_subpath_in_incl_filelist(path):
				# add to exclude list, if not explicitly included; since paths can be nested,
				# it is checked for sub-paths instead of full paths
				self.__snapshot.addToExcludeFlist(path)
				self.__collect_stats.count_excl_config()
				_excluded = True

		if not _excluded:
			# path was not excluded, so do further tests (stats, enter dir...)			
			if self.__fislink:
				self.__logger.info(_("Symbolic link found: '%(path)s' -> '%(ln_target)s'.")\
								% {'path' : path, 'ln_target' : FAM.get_link(path)})
				self.__collect_stats.count_symlink()
				if not self.__snapshot.isFollowLinks():
					# if `followlinks` is *disabled*, just count the link and finish
					_stop_checking = True
					
			if not _stop_checking:	# i.e. `followlinks` is enabled
				if self.__fisdir:
					# if it's a directory, enter inside
					try:
						for _dir_item in FAM.listdir(path) :
							_dir_item = FAM.normpath(path, _dir_item)
							self._check_for_excludes(path=_dir_item)
						self.__collect_stats.count_dir()	# the directory `path`
					except OSError, _exc:
						self.__logger.warning(_("Error while checking directory '%(dir)s': %(error)s.")\
												% {'dir' : path, 'error' : str(_exc)})
						self.__snapshot.addToExcludeFlist(path)	# problems with `path` -> exclude it
						self.__collect_stats.count_excl_forced()
				else:
					# it's a file (may also a link target in case of enabled `followlinks` option)
					self.__collect_stats.count_file()
					self.__cumulate_size(path)
				
	def __cumulate_size(self, path):
		"""
		
		Files not contained in SNAR file are backuped in any case!
		(e.g. a directory was added to the includes)
		"""
#		self.__logger.debug("%s" % path)
		_incl_file = False		
		if self.__isfull:		# full snapshots do not have a base snar file
			_incl_file = True
		else:
			# we don't look at the access time since this was even modified during the last backup 
			ftime = max(self.__fstats.st_mtime,		 
						self.__fstats.st_ctime)			
			if path in self.__parent.get_base_snardict():
#				self.__logger.debug("%s: is in snapshot file." % path)
				if ftime > self.__parent.get_base_backup_time():
					self.__logger.debug("Delta=%s - %s: %s > %s" % ((ftime - self.__parent.get_base_backup_time()),
																	 path, ftime,
																	 self.__parent.get_base_backup_time()))
					_incl_file = True
					
			else:
				self.__logger.debug("%s: No yet included - included." % path)
				self.__collect_stats.count_new_file()
				_incl_file = True
				
		if _incl_file:
			self.__collect_stats.count_incl_file()
			self.__collect_stats.add_size(self.__fstats.st_size)
		else:
			self.__collect_stats.count_skip_file()
		
	def __prepare_excl_regex(self):
		"""Prepares (i.e. compiles) Regular Expressions used for excluding files from flist.
		"""
		self.__logger.debug("Prepare Regular Expressions used for file exclusion.")
		_rexclude = []
		_snp_excl = self.__snapshot.getExcludes()
		if _snp_excl:
			for _regex in _snp_excl:
				if Util.is_empty_regexp(_regex):
					self.__logger.warning(_("Empty regular expression found. "\
										"Skipped."))
				else:
					if Util.is_valid_regexp(_regex):
						_regex_c = re.compile(_regex)
						_rexclude.append(_regex_c)
					else:
						self.__logger.warning(_("Invalid regular expression ('%s')"\
										" found. Skipped.") % _regex)
		self.__excl_regex = _rexclude

	def __prepare_explicit_flists(self):
		"""Paths (i.e. directories and files) defined in the configuration are added
		to the corresponding include/exclude file lists. These lists represent the
		explicitely defined includes and excludes. Includes are stronger than excludes!
		
		The config GUI avoids the definition of a file as included and excluded at the same time.
		The `ConfigManager` returns the last defined entry in the case of multiple definitions
		in section `dirconfig`.		
		"""
		_config = self.__configuration
		if _config is None:
			raise ValueError("No configuration object set.")
		
		# set the list to backup (includes) and to exclude
		self.__logger.debug("Preparation of include and exclude lists.")
		if _config.has_dirconfig_entries() is False:
			self.__logger.warning(_("No directories to backup defined."))
		else:
			for _dir, _incl in _config.get_dirconfig():
				if int(_incl) == 1:
					self.__snapshot.addToIncludeFlist(_dir)
				elif int(_incl) == 0:
					self.__snapshot.addToExcludeFlist(_dir)
					
		# add the default excluded ones
# TODO: why add an empty string?
# TODO: put the default excludes into `ConfigManager`.
# TODO: Remove this hack and replace it by proper shell pattern expansion (glob).
		for _excl in ["", "/dev", "/proc", "/sys", "/tmp",
						  "/dev/", "/proc/", "/sys/", "/tmp/",
						  _config.get_target_dir(),
						  _config.get_target_dir().rstrip(os.sep)+os.sep]:
			self.__snapshot.disable_path_in_incl_filelist(_excl)

# TODO: Even better: Remove this inconsistency and don't use TAR's shell patterns. Prefer pure Regex exclusion.
		for _excl in ["", "/dev/*", "/proc/*", "/sys/*", "/tmp/*", _config.get_target_dir()]:
			self.__snapshot.addToExcludeFlist(_excl)
			
		# sanity check of the lists
		self.__snapshot.check_and_clean_flists()		
				
	def collect_files(self):
		"""Collects information about files that are included resp. excluded in
		the backup.
		"""
		self.__prepare_collecting()
		self.__prepare_excl_regex()
		self.__prepare_explicit_flists()			
		Util.enable_timeout_alarm()
		
		# We have now every thing we need , the rexclude, excludelist, includelist and already stored 
		self.__logger.debug("Creation of the complete exclude list.")
		
		# walk recursively into paths defined as includes (therefore don't call nested paths)
		for _incl in self.__snapshot.get_eff_incl_filelst_not_nested():
			_incl = FAM.normpath(_incl)
			self._check_for_excludes(_incl)


class FileCollectorConfigFacade(object):
	"""Provides a simplified and unified read-only access to configuration options required
	for file collection. Purpose is to de-couple class `ConfigManager` and `FileCollector`
	since only very little configuration settings are required in order to collect the files.
	"""
	def __init__(self, configuration):
		self.__configuration	= None
		self.__target_dir		= None
		
		self.__maxsize_enabled	= False
		self.__maxsize			= 0
		
		self.__dirconfig		= None
		self.__dirconfig_set	= False
		
		self.set_configuration(configuration)
		
	def set_configuration(self, configuration):
		"""Sets the given `configuration`. Corresponding attributes are
		set from this ConfigManager instance.
		"""
		if not isinstance(configuration, ConfigManager):
			raise TypeError("Expected parameter of type 'ConfigManager'. "\
							"Got %s instead." % type(configuration))
		self.__configuration = configuration
		self.__set_target_dir_from_config()
		self.__set_maxsize_limit_from_config()
		self.__set_dirconfig_from_config()
		
	def __set_target_dir_from_config(self):
		if self.__configuration is None:
			raise ValueError("No configuration set.")
		self.__target_dir = FAM.normpath(self.__configuration.get_backup_target())
		
	def __set_maxsize_limit_from_config(self):
		if self.__configuration is None:
			raise ValueError("No configuration set.")
		self.__maxsize_enabled = self.__configuration.has_maxsize_limit()
		self.__maxsize = self.__configuration.get_maxsize_limit()
		
	def __set_dirconfig_from_config(self):
		if self.__configuration is None:
			raise ValueError("No configuration set.")
		self.__dirconfig = self.__configuration.get_dirconfig()
		if self.__dirconfig is None:
			self.__dirconfig_set = False
		else:
			self.__dirconfig_set = True
		
	def is_maxsize_enable(self):
		return self.__maxsize_enabled
	
	def get_maxsize_limit(self):
		return self.__maxsize
	
	def get_target_dir(self):
		return self.__target_dir
	
	def get_dirconfig(self):
		"""Returns the directory configuration stored in a list of pairs (name, value).
		
		@rtype: List
		"""
		return self.__dirconfig
	
	def has_dirconfig_entries(self):
		"""Returns True if the `dirconfig` has any entries. Purpose is improvement of
		performance when checking for entries in the `dirconfig` and hiding implementation
		details about format/storage of the list.
		"""
		return self.__dirconfig_set
