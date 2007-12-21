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

# Author: Aigars Mahinovs <aigarius@debian.org>

from gettext import gettext as _
import os , grp
import datetime
import time
import re
import socket
from FuseFAM import FuseFAM
from SnapshotManager import SnapshotManager
from ConfigManager import ConfigManager
from UpgradeManager import UpgradeManager
import FileAccessManager as FAM
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.log import getLogger
from nssbackup.util.exceptions import *

class BackupManager :
	"""
	"""
	
	config = None
	__um = UpgradeManager()
	__snpman = None
	
	__fusefam = None
	# The whole snapshot path
	__actualSnapshot = None
	
	__lockfile = None
	
	__includeInSnp = None
	
	def __init__(self, configfile = None):
		"""
		The BackupManager Constructor.
		If the config file is not given, BackupManager will try to set the configuration to default
		@param configfile : The config file
		"""
		global config
		if configfile :
			self.config = ConfigManager(configfile)
			if not self.config.has_option("log", "file") :
				getLogger()
		else :
			self.config = ConfigManager()
		
		self.__fusefam = FuseFAM(self.config)
		getLogger().info(_("BackupManager created "))
		
	def makeBackup(self ):
		"""
		Runs the whole backup process 
		"""
		global __actualSnapshot, __snpman
		
		try:
			import pynotify
			if pynotify.init("nssbackup"):
				n = pynotify.Notification("nssbackup", _("Starting backup Session"))
				n.show()
			else:
				getLogger().warning(_("there was a problem initializing the pynotify module"))
		except Exception, e:
			getLogger().warning(str(e))
		
		
		getLogger().info(_("Starting backup"))
		
		# set the lockfile
		self.__setlockfile()
		
		getLogger().info(_("Initializing FUSE FILE ACCESS MANAGER !"))
		self.__fusefam.initialize()
		
		self.__snpman = SnapshotManager(self.config.get("general","target"))
		
		# Set the admin group to the process
		if os.geteuid() == 0 :
			try :
				# The uid is still root and the gid is admin
				os.setgid( grp.getgrnam("admin").gr_gid )
			except Exception, e: 
				getLogger().warning(_("Failed to set the gid to 'admin' one :") + str(e) )

		# Check the target dir
		self.__checkTarget()

		# purge
		purge = None
		if self.config.has_option("general", "purge"):
			purge = self.config.get("general", "purge")
		if purge :
			self.__snpman.purge(purge)
		
		# Upgrade Target 
		try :
			self.__um.upgradeAll( self.config.get("general","target")  )
		except SBException, e:
			getLogger().warning(str(e))
		
		# Get the snapshots list
		listing = self.__snpman.getSnapshots()
		
		# Is Inc or Full ? 
		(name, base, prev) = self.__isIncOrFull(listing)
		
		# Create snapshot
		self.__actualSnapshot = Snapshot(name)
		getLogger().info(_("Starting snapshot %(name)s ") % {'name' :str(self.__actualSnapshot)})
		
		# Set the base file
		if base :
			getLogger().info(_("Setting Base to '%(value)s' ") % {'value' : str(base)})
			self.__actualSnapshot.setBase(base.getName())
		del base
  
		# Backup list of installed packages (Debian only part)
		try:
			getLogger().info(_("Setting packages File "))
			command = "dpkg --get-selections"
			s = os.popen( command )
			pkg = s.read()
			s.close()
			self.__actualSnapshot.setPackages(pkg)
		except Exception, e:
			getLogger().warning(_("Problem when setting the packages : ") + str(e))
		
		
		# set Excludes
		getLogger().info(_("Setting Excludes File "))
		if self.config.has_option( "exclude", "regex" ):
			gexclude = str(self.config.get( "exclude", "regex" )).split(",")
		else :
			gexclude = ""
		self.__actualSnapshot.setExcludes(gexclude)

		# Reduce the priority, so not to interfere with other processes
		os.nice(20)
		
		self.__fillSnapshot(prev)
		
		if os.getuid() != 0 :
			try:
				import pynotify
				if pynotify.init("nssbackup"):
					n = pynotify.Notification("nssbackup", _("File list ready , Committing to disk"))
					n.show()
				else:
					getLogger().warning(_("there was a problem initializing the pynotify module"))
			except Exception, e:
				getLogger().warning(str(e))
				
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
		global fullsize
		
		# -----------------------------------------------------------------
		# sub routines 
		
		def isexcludedbyconf(_file2):
			"""
			This will decide whether or not a file is to be excluded (by the configuration)
			This will not dicide for the incremental exclusion.
			@return: True if the file has to be excluded, false if not
			@note: param to be defined (rexclude, excludelist) , excludelist is a dictionary
			"""
			# excude target
			if _file2.rstrip(os.sep) == self.config.get("general","target").rstrip(os.sep) :
				getLogger().info(_("Target '%s' directory is excluded") % self.config.get("general","target") )
				return True
			
			# return true if the file doesn't exist
			if not os.path.exists(_file2):
				getLogger().warning(_("'%(file)s' doesn't exist, it has to be exclude ") % { 'file' : _file2 })
				return True
			
			# get the stats, If not possible , the file has to be exclude , return True
			try: s = os.lstat( _file2 )
			except Exception, e :
				getLogger().warning(_("Problem with '%(file)s' : %(error)s ") % {'file':_file2, 'error':str(e) } )
				return True
			
			# refuse a file if we don't have read access
			try : 
				fd = os.open(_file2, os.R_OK)
				os.close(fd)
			except OSError, e:
				getLogger().warning(_("We don't have read access to '%(file)s', it has to be exclude : %(error)s ") % {'file':_file2, 'error':str(e) }  )
				return True		
			
			#if the file is too big
			if self.config.has_option("exclude","maxsize") and s.st_size > int(self.config.get("exclude","maxsize")) > 0 :
				getLogger().info(_("'%(file)s' size is higher than the specified one ( %(filesize)s > %(maxsize)s), it has to be exclude ") % {'file':_file2,'filesize':str(s.st_size), 'maxsize': str(self.config.get("exclude","maxsize"))} )
				return True
			
			# if the file matches an exclude regexp, return true
			for r in rexclude:
				if r.search( _file2 ):
					return True
					
			# if the file is in exclude list, return true
			if excludelist.has_key(_file2) :
				return True
			
			#all tests passed
			return False
		
		def isexcludedbyinc(_file3):
			"""
			Check if a file is to be exclude because of incremental policies.
			Don't check if the file was exclude by conf ( it's mandatory the check that before)
			@return: True if the file has to be excluded, the props if not
			"""
			# file is a path of a file or dir to include 
			#isstored =  searchInStored( _file3 )
			if self.__actualSnapshot.isfull() :
				s = os.lstat(_file3)
				props = str(s.st_mode)+str(s.st_uid)+str(s.st_gid)+str(s.st_size)+str(s.st_mtime)
				return props
			
			isstored = self.__snpman.isAlreadyStored(self.__actualSnapshot.getBaseSnapshot(),_file3)
			s = os.lstat(_file3)
			props = str(s.st_mode)+str(s.st_uid)+str(s.st_gid)+str(s.st_size)+str(s.st_mtime)
			if not isstored :
				# file wasn't inside
				return props
			else :
				# file was inside so isstored is a list [existingprops, sonSBdict]the existing properties.
				if isstored != props :
					# then the file has changed
					return props
			
			return True
			
		def addtobackup(_file, props):
			"""
			Add a file to the backup list. This file could be a dir so we need to list the file inside
			"""
			global fullsize
			# add _file and then check if it's a dir to add the contents , We won't follow links
			if not os.path.islink(_file.rstrip(os.sep)) :
				if not os.path.isdir(_file) :
					# don't add dirs 
					self.__actualSnapshot.addFile(_file, props)
					fullsize += os.lstat(_file).st_size
				else :
					# file is dir , search in the content
					try :
						for contents in FAM.listdir(_file) :
							# contents is a path of a file or dir to include 
							contents = os.path.normpath( os.sep.join([_file,contents]) )
							# in dirconfig, directories always end with an os.sep and files not.
							if os.path.isdir(contents) :
								if not contents.endswith(os.sep) :
									contents = contents + os.sep
								# we don't check dir prop as the content seems to 
								# change without modifying the parent dir
								if not isexcludedbyconf( contents ) :
									addtobackup( contents, None )
								else : getLogger().debug("Excluding '%s' (directory is excluded by conf )" % contents)
							else :
								# found a file
								contents.rstrip(os.sep)							
								if not isexcludedbyconf( contents ) :
									cprops = isexcludedbyinc(contents)
									if cprops != True and type(cprops) == str: 
										addtobackup( contents, cprops )
									else :
										getLogger().debug("Excluding '%s' (File didn't change )" % contents)
								else : 
									getLogger().debug("Excluding '%s' (file is excluded by conf )" % contents)
					except OSError, e :
						getLogger().warning(_("got an error with '%(file)s' : %(error)s") % {'file':_file, 'error' : str(e)})
						if self.__actualSnapshot.getFilesList().has_key(_file) :
							del self.__actualSnapshot.getFilesList()[_file]
									
		# End of Subroutines
		# -----------------------------------------------------------------
		
		# regexp to be used for excluding files from flist
		getLogger().debug("getting exclude list for actual snapshot")
		if self.__actualSnapshot.getExcludes() :
			rexclude = [ re.compile(p) for p in self.__actualSnapshot.getExcludes() if len(p)>0]
		else :
			rexclude = []
		
		# Use this for getting the size limit 
		fullsize = 0L
		
		# set the list to backup and to exclude
		getLogger().debug("set the list to backup and to exclude")
		if self.config.has_section( "dirconfig" ):
			if not len(self.config.items("dirconfig")) :
				includelist, excludelist = {},{}
				getLogger().warning(_("No directory to backup !"))
			else :
				includelist, excludelist = {},{}
				for k,v in self.config.items("dirconfig") :
					if int(v) == 1 :
						includelist[k] = 1 
					elif int(v) == 0 :
						excludelist[k] = 0
				# add the default excluded ones
				excludelist.update([("",0), ("/dev/",0), ("/proc/",0), ("/sys/",0), ("/tmp/",0),(self.config.get("general","target"),0)])
		else :
			includelist, excludelist = {},{}
			getLogger().warning(_("No directories to backup !"))	
		
		# We have now every thing we need , the rexclude, excludelist, includelist and already stored 
		getLogger().debug("We have now every thing we need, starting the creation of the Flist " )
		for incl in includelist.iterkeys() :
			# incl is a path of a file or dir to include 
			if not isexcludedbyconf( incl ) :
				if os.path.isdir(incl):
					addtobackup( incl, None )
				else :
					props = isexcludedbyinc(incl)
					if props != True and type(props) == str: 
						addtobackup( incl, props )
					else :
						getLogger().debug("Excluding '%s' (File didn't change )" % incl)
			else :
				getLogger().debug("Excluding '%s' (File excluded by conf)" % incl)

				
		# check for the available size
		getLogger().debug("Free size required is '%s' " % str(fullsize))
		vstat = os.statvfs( self.__actualSnapshot.getPath() )
		if (vstat.f_bavail * vstat.f_bsize) <= fullsize:
			raise SBException(_("Not enough free space on the target directory for the planned backup (%(freespace)d <= %(neededspace)d)") % { 'freespace':(vstat.f_bavail * vstat.f_bsize), 'neededspace': self.__fullsize})
	
	
	def __setlockfile(self):
		"Set the lockfile "
		global __lockfile
		if self.config.has_option("general", "lockfile") :
			self.__lockfile = self.config.get("general", "lockfile")
		else :
			getLogger().debug("no lockfile in config, the default will be used ")
			self.__lockfile = "/var/lock/nssbackup.lock"
		
		# Create the lockfile so none disturbs us
		if FAM.exists(self.__lockfile) :
			# the lockfile exists, is it valid ?
			last_sb_pid = FAM.readfile(self.__lockfile)
			if (last_sb_pid and os.path.lexists("/proc/"+last_sb_pid) and "nssbackupd" in str(open("/proc/"+last_sb_pid+"/cmdline").read()) ) :
				raise SBException(_("Another NSsbackup daemon already running (pid = %s )!") % last_sb_pid )
			else :
				FAM.delete(self.__lockfile)
		
		lock = FAM.writetofile(self.__lockfile, str(os.getpid()) )
		getLogger().debug("Created lockfile at '%s' with info '%s'"% (self.__lockfile, str(os.getpid()) ) )

	def __endSBsession(self):
		"""
		End nssbackup session :
		- copy the log file into the snapshot dir
		- remove the lockfile
		"""
		
		FAM.delete(self.__lockfile)
		getLogger().info(_("Session of backup is finished (%s is removed) ") % self.__lockfile)
		
		if self.config.has_option("log","file") and FAM.exists(self.config.get("log","file")):
			FAM.copyfile(self.config.get("log","file"), self.__actualSnapshot.getPath()+"/nssbackup.log")
		elif FAM.exists("nssbackup.log") : 
			FAM.copyfile(os.path.abspath("nssbackup.log"), self.__actualSnapshot.getPath()+"/nssbackup.log")
		else :
			getLogger().warning(_("I didn't find the logfile to copy into snapshot"))
			
		getLogger().info(_("Terminating FUSE FILE ACCESS MANAGER !"))
		self.__fusefam.terminate()
		if os.getuid() != 0 :
			try:
				import pynotify
				if pynotify.init("nssbackup"):
					n = pynotify.Notification("nssbackup", _("Ending Backup Session"))
					n.show()
				else:
					getLogger().warning(_("there was a problem initializing the pynotify module"))
			except Exception, e:
				getLogger().warning(str(e))
			

	def __checkTarget(self):
		"""
		"""
		# Check if the mandatory target option exists
		if not self.config.has_option("general","target") :
			raise SBException (_("Option 'target' is missing, aborting."))
		
		# Check if the target dir exists or create it
		if not FAM.exists(self.config.get("general","target")) :
			getLogger().info(_("Creating the target dir '%s'") % self.config.get("general","target"))
			FAM.makedir(self.config.get("general","target"))
		
		# Try to write inside so that we don't work for nothing
		try :
			FAM.writetofile(self.config.get("general","target")+"/test", "testWritable")
			FAM.delete(self.config.get("general","target")+"/test")
		except Exception, e :
			getLogger().error(_("Target not writable : ") + str(e))
			raise e
	
	def __isIncOrFull(self, listing ):
		"""
		@param listing: a list of snapshot
		@return: a tuple (name, base, prev)
		""" 
		r = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})[\:\.](\d{2})[\:\.](\d{2})\.\d+\..*?\.(.+)$")
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
				getLogger().debug("Last (%s) was a full backup" % listing[0].getName())
				d = listing[0].getDate()
				if ( datetime.date.today() - datetime.date(d["year"],d["month"],d["day"]) ).days < self.config.get("general","maxincrement") :
			    	# Less then maxincrement days passed since that -> make an increment
					increment = True
					try:
						prev = base.getFilesList()
					except Exception, e:
						getLogger().warning(str(e))
						increment = False  # Last backup is somehow damaged	
				else:
					getLogger().info("Last full backup is old -> make a full backup")
					increment = False      # Too old -> make full backup
			else: # Last backup was an increment - lets search for the last full one
				getLogger().debug(" Last backup (%s) was an increment - lets search for the last full one" % listing[0].getName())
				for i in listing :
					try: 
						for a,b in i.getFilesList().items() :
							if not prev.has_key(a) : # We always keep the newer incremental file info
								prev[a]=b
					except Exception, e :  # One of the incremental backups is bad -> make a new full one
						getLogger().warning(_("One of the incremental backups (%(bad_one)s) is bad -> make a new full one : %(error_cause)s ") % {'bad_one' : i.getName(), 'error_cause' : str(e)})
						increment = False
						break
					
					if i.isfull():
						d = i.getDate()
						age = (datetime.date.today() - datetime.date(d["year"],d["month"],d["day"]) ).days
						if  age < int(self.config.get("general","maxincrement")) :
							# Last full backup is fresh -> make an increment
							getLogger().info("Last full backup is fresh (%d days old )-> make an increment" % age )
							increment = True
						else: # Last full backup is old -> make a full backup
							getLogger().info("Last full backup is old -> make a full backup")
							increment = False
						break
				else:
					getLogger().info(" No full backup found -> lets make a full backup to be safe")
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
		global __config
		if self.__config : return self.__config
		else :
			self.__config = ConfigManager()

	def getActualSnapshot(self):
		"""
		get the actual snapshot
		"""
		return self.__actualSnapshot

