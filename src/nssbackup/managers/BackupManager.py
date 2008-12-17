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

# Author: Oumar Aziz OUATTARA <wattazoum at gmail dot com>

from gettext import gettext as _
import os , grp, signal
import datetime
import re
import socket
from FuseFAM import FuseFAM
from SnapshotManager import SnapshotManager
from ConfigManager import ConfigManager
from UpgradeManager import UpgradeManager
import FileAccessManager as FAM
import nssbackup.util as Util
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.log import LogFactory
from nssbackup.util import exceptions

try:
	import pynotify
except Exception, e:
	LogFactory.getLogger().warning(str(e))
	pynotify = False
				
class BackupManager :
	"""
	"""
	
	def __init__(self, configfile = None):
		"""
		The BackupManager Constructor.
		If the config file is not given, BackupManager will try to set the configuration to default
		@param configfile : The config file
		"""
		#-------------------------------
		self.config = None
		self.__um = UpgradeManager()
		self.__snpman = None
		
		self.__fusefam = None
		# The whole snapshot path
		self.__actualSnapshot = None
		
		self.__lockfile = None
		
		self.__includeInSnp = None
		#-----------------------------------
		
		if configfile :
			self.config = ConfigManager(configfile)
		else :
			self.config = ConfigManager()
		
		self.logger = LogFactory.getLogger()
		
		self.__fusefam = FuseFAM(self.config)
		
		self.__pynotif_avail = False
		try:
			import pynotify
			if pynotify.init("NSsbackup"):
				self.__pynotif_avail = True
			else:
				self.logger.warning(_("there was a problem initializing the pynotify module"))
		except Exception, e:
			self.logger.warning(str(e))
			
		self.logger.info(_("BackupManager created "))
		
	def makeBackup(self ):
		"""
		Runs the whole backup process 
		"""
		global __actualSnapshot, __snpman
		
		if self.__pynotif_avail:
			n = pynotify.Notification("NSsbackup", _("Starting backup Session"))
			n.show()
		
		self.logger.info(_("Starting backup"))
		
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
			except Exception, e: 
				self.logger.warning(_("Failed to set the gid to 'admin' one :") + str(e) )

		# Check the target dir
		self.__checkTarget()
		
		# Upgrade Target 
		try :
			self.__um.upgradeAll( self.config.get("general","target")  )
		except exceptions.SBException, e:
			self.logger.warning(str(e))
		
		# purge
		purge = None
		if self.config.has_option("general", "purge"):
			purge = self.config.get("general", "purge")
		if purge :
			self.__snpman.purge(purge)
		
		# Get the snapshots list
		listing = self.__snpman.getSnapshots()
		
		# Is Inc or Full ? 
		(name, base, prev) = self.__isIncOrFull(listing)
		
		# Create snapshot
		self.__actualSnapshot = Snapshot(name)
		self.logger.info(_("Starting snapshot %(name)s ") % {'name' :str(self.__actualSnapshot)})
		
		# Set the base file
		if base :
			self.logger.info(_("Setting Base to '%(value)s' ") % {'value' : str(base)})
			self.__actualSnapshot.setBase(base.getName())
		del base

		# Backup list of installed packages (Debian only part)
		try:
			self.logger.info(_("Setting packages File "))
			command = "dpkg --get-selections"
			s = os.popen( command )
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
			
		# Reduce the priority, so not to interfere with other processes
		os.nice(20)
		
		self.__fillSnapshot(prev)
					
		if self.__pynotif_avail:
			n = pynotify.Notification("NSsbackup", _("File list ready , Committing to disk"))
			n.show()
				
		self.__actualSnapshot.commit()
		
		# End session
		self.__endSBsession()
		
	def __fillSnapshot(self, prev):
		"""
		Fill the snapshot with informations.
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
				
		# -----------------------------------------------------------------
		# sub routines 
		
		def handler(signum, frame):
			print 'Signal handler called with signal', signum
			raise OSError, "Couldn't open device!"

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
				# add _file and then check if it's a dir to add the contents , We won't follow links
				if not os.path.islink(path.rstrip(os.sep)) :
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
				else :
					# we got a link
					if backuplinks :
						self.logger.debug("backing up the link '%s' ! " % path)
					else :
						self.logger.debug("Excluding link '%s' ! " % path)
						self.__actualSnapshot.addToExcludeFlist(path)
						self.fullsize += os.lstat(path).st_size
			

		# End of Subroutines
		# -----------------------------------------------------------------
		
		backuplinks=None
		if self.config.has_option("general","backuplinks") and str(self.config.get("general","backuplinks")) == "1" :
			backuplinks=True
		
		
		# Use this for getting the size limit 
		self.fullsize = 0L
		
		# regexp to be used for excluding files from flist
		self.logger.debug("getting exclude list for actual snapshot")
		rexclude = []
		if self.__actualSnapshot.getExcludes() :
			for p in self.__actualSnapshot.getExcludes():
				if Util.is_empty_regexp(p):
					self.logger.error(_("Empty regular expression found. "\
										"Skipped."))
				else:
					if Util.is_valid_regexp(p):
						p_compiled = re.compile(p)
						rexclude.append(p_compiled)
					else:
						self.logger.error(_("Invalid regular expression ('%s')"\
										" found. Skipped.") % p )
							
		# set the list to backup and to exclude
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
		neededspace = "%d Mb %d Kb %d" % (mb,kb,b)
		self.logger.debug("Maximum free size required is '%s' " % neededspace)
		vstat = os.statvfs( self.__actualSnapshot.getPath() )
		if (vstat.f_bavail * vstat.f_bsize) <= self.fullsize:
			raise exceptions.SBException(_("Not enough free space on the target directory for the planned backup (%(freespace)d <= %(neededspace)s)") % { 'freespace':(vstat.f_bavail * vstat.f_bsize), 'neededspace': neededspace})
	
	
	def __setlockfile(self):
		"Set the lockfile "
		global __lockfile
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
		
		FAM.writetofile(self.__lockfile, str(os.getpid()) )
		self.logger.debug("Created lockfile at '%s' with info '%s'"% (self.__lockfile, str(os.getpid()) ) )

	def __endSBsession(self):
		"""
		End nssbackup session :
		- copy the log file into the snapshot dir
		- remove the lockfile
		"""
		
		FAM.delete(self.__lockfile)
		self.logger.info(_("Session of backup is finished (%s is removed) ") % self.__lockfile)
		
		if self.config.has_option("log","file") and FAM.exists(self.config.get("log","file")):
			FAM.copyfile(self.config.get("log","file"), self.__actualSnapshot.getPath()+"/nssbackup.log")
		elif FAM.exists("nssbackup.log") : 
			FAM.copyfile(os.path.abspath("nssbackup.log"), self.__actualSnapshot.getPath()+"/nssbackup.log")
		else :
			self.logger.warning(_("I didn't find the logfile to copy into snapshot"))
			
		self.logger.info(_("Terminating FUSE FILE ACCESS MANAGER !"))
		self.__fusefam.terminate()

		if self.__pynotif_avail:
			n = pynotify.Notification("NSsbackup", _("Ending Backup Session"))
			n.show()
			

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
		try :
			FAM.writetofile(self.config.get("general","target")+"/test", "testWritable")
			FAM.delete(self.config.get("general","target")+"/test")
		except Exception, e :
			self.logger.error(_("Target not writable : ") + str(e))
			raise e
	
	def __isIncOrFull(self, listing ):
		"""
		@param listing: a list of snapshot
		@return: a tuple (name, base, prev)
		""" 
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
					self.logger.info(" No full backup found -> lets make a full backup to be safe")
					increment = False            # No full backup found 8) -> lets make a full backup to be safe
		
		# Determine and create backup target directory
		hostname = socket.gethostname()
		
		tdir = self.config.get("general","target") + "/" + datetime.datetime.now().isoformat("_").replace( ":", "." ) + "." + hostname + "."
		if increment:
			tdir = tdir + "inc"
		else:
			tdir = tdir + "ful"
			
		return (tdir, base, prev)
	
	
	def getConfig(self) :
		"""
		get the config for the instance of nssbackup 
		(/etc/nssbackup.conf if root  or ~/.nssbackup/nssbackup.conf if normal user)
		"""
		if self.config:
			return self.config
		else :
			self.config = ConfigManager()

	def getActualSnapshot(self):
		"""
		get the actual snapshot
		"""
		return self.__actualSnapshot

