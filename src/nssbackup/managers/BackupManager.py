#	NSsbackup - snapshot handling
#
#   Copyright (c)2007-2008: Ouattara Oumar Aziz <wattazoum@gmail.com>
#   Copyright (c)2008-2009: Jean-Peer Lorenz <peer.loz@gmx.net>
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
import os , grp, signal
import datetime
import re
import socket
import gobject

from FuseFAM import FuseFAM
from SnapshotManager import SnapshotManager
from UpgradeManager import UpgradeManager
import FileAccessManager as FAM
import nssbackup.util as Util
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.log import LogFactory
from nssbackup.util import exceptions


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
			else:
				self.__pynotif_avail = False	# yes, this is insane!
				self.__logger.warning(_("there was a problem initializing the "\
									    "pynotify module"))
		except ImportError, exc:
			self.__pynotif_avail = False
			self.__logger.warning(str(exc))
		

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
					self.logger.warning("Connection to notification-daemon "\
										"failed: " + str(exc))

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
					self.logger.warning("Connection to notification-daemon "\
										"failed: " + str(exc))

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
			ico = Util.getResource("nssbackup32x32.png")
			try:
				notif = self.__pynotif_mod.Notification(
								"NSsbackup [%s]" % profilename, message, ico)
			except gobject.GError, exc:
				# Connection to notification-daemon failed 
				self.logger.warning("Connection to notification-daemon "\
									"failed: " + str(exc))
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
			ico = Util.getResource("nssbackup32x32.png")
			try:
				self.__notif.update(
								"NSsbackup [%s]" % profilename, message, ico)
			except gobject.GError, exc:
				# Connection to notification-daemon failed 
				self.logger.warning("Connection to notification-daemon "\
									"failed: " + str(exc))
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
		
		self.__fusefam 		= None
		# The whole snapshot path
		self.__actualSnapshot = None
		self.fullsize 		= 0L
		
		self.__lockfile 	= None
		
		self.__includeInSnp = None
		
		self.__fusefam		= FuseFAM(self.config)
		
		PyNotifyMixin.__init__(self, self.logger)
		self.logger.info(_("BackupManager created "))
		
	def makeBackup(self ):
		"""Runs the whole backup process.
		
		"""
		_msg = _("Starting backup Session")
		self._notify_info(self.__profilename, _msg)
		self.logger.info(_msg)
		
		# set the lockfile
		self.__setlockfile()
		
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
		(snppath, base, prev) = self.__retrieve_basic_infos()
		
		# Create a new snapshot
		self.__actualSnapshot = Snapshot(snppath)
		self.logger.info(_("Starting snapshot %(name)s ")
						 % {'name' :str(self.__actualSnapshot)})
		
		# Set the base file
		if base :
			if self.__actualSnapshot.isfull():
				self.logger.info("Base is not set for full snapshot")
			else:
				self.logger.info(_("Setting Base to '%(value)s' ") % {'value' : str(base)})
				self.__actualSnapshot.setBase(base.getName())
		del base

		# Backup list of installed packages
		self.__packagecmd = "dpkg --get-selections"
		if self.config.has_option( "general", "packagecmd" ):
			self.__packagecmd = self.config.get("general", "packagecmd" )
		if self.__packagecmd:
			try:
				self.logger.info(_("Setting packages File "))
				s = os.popen( self.__packagecmd )
				pkg = s.read()
				s.close()
				self.__actualSnapshot.setPackages(pkg)
			except Exception, e:
				self.logger.warning(_("Problem when setting the packages : ") + str(e))
		
		# set Excludes
		self.logger.info(_("Setting Excludes File "))
		if self.config.has_option( "exclude", "regex" ):
			gexclude = str(self.config.get( "exclude", "regex" )).split(",")
		else :
			gexclude = ""
		self.__actualSnapshot.setExcludes(gexclude)
		
		# set format
		self.logger.info(_("Setting compression format "))
		if self.config.has_option( "general", "format" ):
			self.__actualSnapshot.setFormat(self.config.get("general","format"))
			
		# set splited size
		self.logger.info(_("Setting split size"))
		if self.config.has_option( "general", "splitsize" ):
			self.__actualSnapshot.setSplitedSize(int(self.config.get("general","splitsize")))
		
		# set followlinks
		self.__followlinks = False
		if self.config.has_option( "general", "followlinks" ) and self.config.get("general","followlinks") == "1":
			self.logger.info(_("Setting follow symbolic links"))
			self.__followlinks = True
			self.__actualSnapshot.setFollowLinks(self.__followlinks)
			
		# Reduce the priority, so not to interfere with other processes
		os.nice(20)
		
		self.__fillSnapshot(prev)
					
		self._notify_info(self.__profilename, _("File list ready, committing to disk"))
				
		self.__actualSnapshot.commit()
		
		# End session
		self.endSBsession()
		
	def __fillSnapshot(self, prev):
		"""Fill the snapshot with informations.
		-> Get the list of already stored files in successive snapshots.
		-> for each file to store:  get the stats :
			-> if the file match an exclude criteria (regex or explicitely in exclude ) : pass
			-> if not :
				-> search in the existing stored files :
					-> if not inside, add to the tobackuplist
					-> if inside :
						-> if not changed : pass , don't backup it
						-> if changed : add to the tobackuplist				
		@param prev :
		"""		
		# sub routines 		
		def handler(signum, frame):
			print 'Signal handler called with signal', signum
			raise OSError("Couldn't open device!")

		# Set the signal handler 
		signal.signal(signal.SIGALRM, handler)
				
		def isexcludedbyconf(_file2):
			"""
			This will decide whether or not a file is to be excluded (by the configuration)
			This will not dicide for the incremental exclusion.
			@return: True if the file has to be excluded, false if not
			@note: param to be defined (rexclude, excludelist) , excludelist is a dictionary
			"""
			# excude target
			if _file2.rstrip(os.sep) == self.config.get("general","target").rstrip(os.sep) :
				self.logger.info(_("Target '%s' directory is excluded") % self.config.get("general","target") )
				return True
			
			# return true if the file doesn't exist
			if not os.path.exists(_file2):
				self.logger.warning(_("'%(file)s' doesn't exist, it has to be exclude ") % { 'file' : _file2 })
				return True
			
			# get the stats, If not possible , the file has to be exclude , return True
			try: s = os.lstat( _file2 )
			except Exception, e :
				self.logger.warning(_("Problem with '%(file)s' : %(error)s ") % {'file':_file2, 'error':str(e) } )
				return True
			
			# refuse a file if we don't have read access
			try : 
				signal.alarm(5)
				# This open() may hang indefinitely (LP Bug 184713)
				fd = os.open(_file2, os.R_OK)  
				os.close(fd)
			except OSError, e:
				self.logger.warning(_("We don't have read access to '%(file)s', it has to be exclude : %(error)s ") % {'file':_file2, 'error':str(e) }  )
				return True
			finally :
				signal.alarm(0)          # Disable the alarm
			
			#if the file is too big
			if self.config.has_option("exclude","maxsize") and s.st_size > int(self.config.get("exclude","maxsize")) > 0 :
				self.logger.info(_("'%(file)s' size is higher than the specified one ( %(filesize)s > %(maxsize)s), it has to be exclude ") % {'file':_file2,'filesize':str(s.st_size), 'maxsize': str(self.config.get("exclude","maxsize"))} )
				return True
			
			# if the file matches an exclude regexp, return true
			for r in rexclude:
				if r.search( _file2 ):
					return True
					
			# if the file is in exclude list, return true
			if self.__actualSnapshot.getExcludeFlist().hasFile(_file2) :
				return True
			
			#all tests passed
			return False
			
		def checkForExclude( path, forceExclusion=False ):
			"""
			check for file to exclude into path and add them to the ExcludeFlist
			We will enter in the directories , only when needed. Otherwise we will use a wildcard
			@param path: The path to check for
			"""
			if isexcludedbyconf( path ) :
				# add to exclude list
				if not self.__actualSnapshot.getIncludeFlist().hasFile(path):
					self.__actualSnapshot.addToExcludeFlist(path)
			else :
				# add _file and then check if it's a dir to add the contents , We won't follow links by default
				stop = False
				if os.path.islink(path.rstrip(os.sep)) :
					# we got a link, always backup links, then tar will follow it if 
					# followlinks is set
					self.logger.debug("backing up the link '%s' ! " % path)
					if not self.__followlinks:
						stop = True
				if not stop :
					# if it's a directory
					if os.path.isdir(path):
						#enter inside
						# we remove the dir as an effective file of the exclude list
						# This will prevent full exclusion of that directory
						if self.__actualSnapshot.getExcludeFlist().hasFile(path):
							self.__actualSnapshot.getExcludeFlist()[path][0] = None
						try :
							for contents in FAM.listdir(path) :
								# contents is a path of a file or dir to include 
								contents = os.path.normpath( os.sep.join([path,contents]) )
								# if the file is included precisely, don't force exclusion
								checkForExclude(contents,not self.__actualSnapshot.getIncludeFlist().hasFile(path))
							
						except OSError, e :
							self.logger.warning(_("got an error with '%(file)s' : %(error)s") % {'file':path, 'error' : str(e)})
							# Add to exclude file list
							self.__actualSnapshot.addToExcludeFlist(path)
					else:
						self.fullsize += os.lstat(path).st_size
					
		# End of Subroutines
		########################################################################
		
		# Use this for getting the size limit 
		self.fullsize = 0L
		
		# regexp to be used for excluding files from flist
		self.logger.debug("getting exclude list for actual snapshot")
		rexclude = []
		if self.__actualSnapshot.getExcludes() :
			for p in self.__actualSnapshot.getExcludes():
				if Util.is_empty_regexp(p):
					self.logger.warning(_("Empty regular expression found. "\
										"Skipped."))
				else:
					if Util.is_valid_regexp(p):
						p_compiled = re.compile(p)
						rexclude.append(p_compiled)
					else:
						self.logger.warning(_("Invalid regular expression ('%s')"\
										" found. Skipped.") % p )
							
		# set the list to backup (includes) and to exclude
		self.logger.debug("set the list to backup and to exclude")
		if self.config.has_section( "dirconfig" ):
			if not len(self.config.items("dirconfig")) :
				self.logger.warning(_("No directory to backup !"))
			else :
				for k,v in self.config.items("dirconfig") :
					if int(v) == 1 :
						self.__actualSnapshot.addToIncludeFlist(k)
					elif int(v) == 0 :
						self.__actualSnapshot.addToExcludeFlist(k)
				# add the default excluded ones
				for excl in ["", "/dev/*", "/proc/*", "/sys/*", "/tmp/*",self.config.get("general","target")] :
					self.__actualSnapshot.addToExcludeFlist(excl)
		else :
			self.logger.warning(_("No directories to backup !"))	
		
		# We have now every thing we need , the rexclude, excludelist, includelist and already stored 
		self.logger.debug("We have now every thing we need, starting the creation of the complete exclude list " )
		
		for incl in self.__actualSnapshot.getIncludeFlist().getEffectiveFileList():
			# check into incl for file to exclude
			checkForExclude(incl)
				
		# check for the available size
		mb = self.fullsize / (1024*1024)
		kb = ( self.fullsize % (1024*1024) ) / 1024
		b = ( self.fullsize % (1024*1024) ) % 1024
		neededspace = "%d MiB %d KiB %d" % (mb,kb,b)
		self.logger.debug("Maximum free size required is '%s' " % neededspace)
		vstat = os.statvfs( self.__actualSnapshot.getPath() )
		if (vstat.f_bavail * vstat.f_bsize) <= self.fullsize:
			raise exceptions.SBException(_("Not enough free space in the target directory for the planned backup (%(freespace)d <= %(neededspace)s)") % { 'freespace':(vstat.f_bavail * vstat.f_bsize), 'neededspace': neededspace})
	
	def __setlockfile(self):
		"""Set the lockfile.
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
			if (last_sb_pid and os.path.lexists("/proc/"+last_sb_pid) and "nssbackupd" in str(open("/proc/"+last_sb_pid+"/cmdline").read()) ) :
				raise exceptions.SBException(_("Another NSsbackup daemon already running (pid = %s )!") % last_sb_pid )
			else :
				FAM.delete(self.__lockfile)
		
		FAM.writetofile(self.__lockfile, str(os.getpid()))
		self.logger.debug("Created lockfile at '%s' with info '%s'"\
						  % (self.__lockfile, str(os.getpid()) ))
		
	def __unsetlockfile(self):
		"""Remove lockfile.
		"""
		FAM.delete(self.__lockfile)
		self.logger.info(_("Session of backup is finished (%s is removed) ")\
														% self.__lockfile)

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
			
		self.logger.info(_("Terminating FUSE FILE ACCESS MANAGER!"))
		self.__fusefam.terminate()

		self._notify_info(self.__profilename, _("Ending Backup Session."))

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
		3. the value `prev` that is currently unused
		
		:param listing: a list of snapshots
		
		:return: the determined `snppath`, `base` and  `prev`
		:rtype: a tuple
		
		"""
		# Get the list of snapshots that matches the latest snapshot format
		listing = self.__snpman.get_snapshots()

		prev = {}
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
			
		return (tdir, base, prev)

	def getActualSnapshot(self):
		"""Apparently unused at the moment!
		
		get the actual snapshot
		"""
		return self.__actualSnapshot
