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
		getLogger().info("BackupManager created ")
		
	def makeBackup(self ):
		"""
		Runs the whole backup process 
		"""
		global __actualSnapshot, __snpman
		
		try:
			import pynotify
			if pynotify.init("nssbackup"):
				n = pynotify.Notification("nssbackup", "Starting Backup Session")
				n.show()
			else:
				getLogger().warning("there was a problem initializing the pynotify module")
		except Exception, e:
			getLogger().warning(str(e))
		
		
		getLogger().info("Starting backup")
		
		# set the lockfile
		self.__setlockfile()
		
		getLogger().info("Initializing FUSE FILE ACCESS MANAGER !")
		self.__fusefam.initialize()
		
		self.__snpman = SnapshotManager(self.config.get("general","target"))
		
		# Set the admin group to the process
		if os.geteuid() == 0 :
			try :
				# The uid is still root and the gid is admin
				os.setgid( grp.getgrnam("admin").gr_gid )
			except Exception, e: 
				getLogger().warning("Failed to set the gid to 'admin' one :" + str(e) )

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
		(name, base, prev, increment) = self.__isIncOrFull(listing)
		
		# We don't need listing anymore (let's free some memory )
		del listing
		
		# Create snapshot
		self.__actualSnapshot = Snapshot(name)
		getLogger().info("Starting snapshot %s " % str(self.__actualSnapshot))
		
		# Set the base file
		if base :
			getLogger().info("Setting Base to '%s' " % str(base))
			self.__actualSnapshot.setBase(base.getName())
		del base
  
		# Backup list of installed packages (Debian only part)
		try:
			getLogger().info("Setting packages File ")
			command = "dpkg --get-selections"
			s = os.popen( command )
			pkg = s.read()
			s.close()
			self.__actualSnapshot.setPackages(pkg)
		except Exception, e:
			getLogger().warning("Problem when setting the packages : " + str(e))
		
		
		# set Excludes
		getLogger().info("Setting Excludes File ")
		if self.config.has_option( "exclude", "regex" ):
			gexclude = str(self.config.get( "exclude", "regex" )).split(",")
		self.__actualSnapshot.setExcludes(gexclude)

		# Reduce the priority, so not to interfere with other processes
		os.nice(20)
		
		self.__fillSnapshot(prev, increment)
		
		if os.getuid() != 0 :
			try:
				import pynotify
				if pynotify.init("nssbackup"):
					n = pynotify.Notification("nssbackup", "File list ready , Committing to disk")
					n.show()
				else:
					getLogger().warning("there was a problem initializing the pynotify module")
			except Exception, e:
				getLogger().warning(str(e))
				
				
		self.__actualSnapshot.commit()
		
		# End session
		self.__endSBsession()
		
	def __fillSnapshot(self, prev, increment):
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
		@param increment: 
		"""
		global fullsize
		
		# -----------------------------------------------------------------
		# sub routines 
		
		def searchInStored(_file):
			"""
			search for a file in stored list
			@return: the properties if found , None if not
			"""
			for name,sbdict in alreadyStored.iteritems() :
				getLogger().debug("Searching for '%s' in '%s'" % (_file, name))
				if sbdict.has_key(_file) :
					getLogger().debug("found in '%s' " % name)
					return sbdict[_file]
			# not found
			return None 
		
		def isexcludedbyconf(_file):
			"""
			This will decide whether or not a file is to be excluded (by the configuration)
			This will not dicide for the incremental exclusion.
			@return: True if the file has to be excluded, false if not
			@note: param to be defined (rexclude, excludelist) , excludelist is a dictionary
			"""
			# excude target
			if _file == self.config.get("general","target") :
				getLogger().debug("target dir is excluded ")
				return True
			
			# return true if the file doesn't exist
			if not os.path.exists(_file):
				getLogger().debug("'%s' doesn't exist, it has to be exclude " % _file )
				return True
			
			# refuse a file if we don't have read access
			if not os.access(_file, os.R_OK):
				getLogger().debug("We don't have read access to '%s', it has to be exclude " % _file )
				return True
			
			# get the stats, If not possible , the file has to be exclude , return True
			try: s = os.lstat( _file )
			except Exception, e :
				getLogger().debug("Problem with '%s' : %s " % (_file, str(e) ) )
				return True
			
			#if the file is too big
			if self.config.has_option("exclude","maxsize") and s.st_size > int(self.config.get("exclude","maxsize")) > 0 :
				getLogger().debug("'%s' size is higher than the specified one ( %s > %s), it has to be exclude " % (_file,str(s.st_size), str(self.config.get("exclude","maxsize"))) )
				return True
			
			# if the file matches an exclude regexp, return true
			for r in rexclude:
				if r.search( _file ):
					return True
					
			# if the file is in exclude list, return true
			if excludelist.has_key(_file) :
				return True
			
			#all tests passed
			return False
		
		def isexcludedbyinc(_file):
			"""
			Check if a file is to be exclude because of incremental policies.
			Don't check if the file was exclude by conf ( it's mandatory the check that before)
			@return: True if the file has to be excluded, the props if not
			"""
			# file is a path of a file or dir to include 
			isstored =  searchInStored( incl )
			s = os.lstat(_file)
			props = str(s.st_mode)+str(s.st_uid)+str(s.st_gid)+str(s.st_size)+str(s.st_mtime)
			if not isstored :
				# file wasn't inside
				return props
			else :
				# file was inside so isstored is a list [existingprops, sonSBdict]the existing properties.
				if isstored[0] != props :
					# then the file has changed
					return props
			
			return True
			
		def addtobackup(_file, props):
			"""
			Add a file to the backup list. This file could be a dir so we need to list the file inside
			"""
			global fullsize
			# add _file and then check if it's a dir to add the contents , We won't follow links
			self.__actualSnapshot.addFile(_file, props)
			fullsize += os.lstat(_file).st_size
			if not os.path.islink(_file.rstrip(os.sep)) and os.path.isdir(_file) :
				try :
					for contents in FAM.listdir(_file) :
						# contents is a path of a file or dir to include 
						contents = os.path.normpath( os.sep.join([_file,contents]) )
						# in dirconfig, directories always end with an os.sep and files not.
						if os.path.isdir(contents) and not contents.endswith(os.sep) :
							contents = contents + os.sep
						elif not os.path.isdir(contents) :
							contents.rstrip(os.sep)
						
						if not isexcludedbyconf( contents ) :
							cprops = isexcludedbyinc(contents)
							if cprops != True and type(cprops) == str: 
								addtobackup( contents, cprops )
				except OSError, e :
					getLogger().warning("got an error with '%s' : %s" % (_file, str(e)))
					if self.__actualSnapshot.getFilesList().has_key(_file) :
						del self.__actualSnapshot.getFilesList()[_file]
								
		# End of Subroutines
		# -----------------------------------------------------------------
		
		# -> Get the list of already stored files in successive snapshots.
		if not self.__actualSnapshot.isfull() :
			alreadyStored = self.__snpman.getRevertState(self.__actualSnapshot.getBaseSnapshot(), os.sep )
		else :
			alreadyStored = {}
		
		# regexp to be used for excluding files from flist
		rexclude = [ re.compile(p) for p in self.__actualSnapshot.getExcludes() if len(p)>0]
		
		# Use this for getting the size limit 
		fullsize = 0L
		
		# set the list to backup and to exclude
		if self.config.has_section( "dirconfig" ):
			if not len(self.config.items("dirconfig")) :
				includelist, excludelist = {},{}
				getLogger().warning("No directories to backup !")
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
			getLogger().warning("No directories to backup !")	
		
		# We have now every thing we need , the rexclude, excludelist, includelist and already stored 
		for incl in includelist.iterkeys() :
			# incl is a path of a file or dir to include 
			if not isexcludedbyconf( incl ) :
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
			raise SBException("Not enough free space on the target directory for the planned backup (%d <= %d)" % ((vstat.f_bavail * vstat.f_bsize), self.__fullsize))
	
	
	def __setlockfile(self):
		"Set the lockfile "
		global __lockfile
		if self.config.has_option("general", "lockfile") :
			self.__lockfile = self.config.get("general", "lockfile")
		else :
			getLogger().info("no lockfile in config, default will be used ")
			self.__lockfile = "/var/lock/nssbackup.lock"
		
		# Create the lockfile so none disturbs us
		if FAM.exists(self.__lockfile) :
			# the lockfile exists, is it valid ?
			last_sb_pid = FAM.readfile(self.__lockfile)
			if (last_sb_pid and os.path.lexists("/proc/"+last_sb_pid) and "nssbackupd" in str(open("/proc/"+last_sb_pid+"/cmdline").read()) ) :
				raise SBException("Another Simple Backup daemon already running (pid = %s )!" % last_sb_pid )
			else :
				FAM.delete(self.__lockfile)
		
		lock = FAM.writetofile(self.__lockfile, str(os.getpid()) )
		getLogger().info("Created lockfile at '%s' with info '%s'"% (self.__lockfile, str(os.getpid()) ) )

	def __endSBsession(self):
		"""
		End nssbackup session :
		- copy the log file into the snapshot dir
		- remove the lockfile
		"""
		
		FAM.delete(self.__lockfile)
		getLogger().info("Session of backup is finished (%s is removed) " % self.__lockfile)
		
		if self.config.has_option("log","file") and FAM.exists(self.config.get("log","file")):
			FAM.copyfile(self.config.get("log","file"), self.__actualSnapshot.getPath()+"/nssbackup.log")
		elif FAM.exists("nssbackup.log") : 
			FAM.copyfile(os.path.abspath("nssbackup.log"), self.__actualSnapshot.getPath()+"/nssbackup.log")
		else :
			getLogger().warning("I didn't find the logfile to copy into snapshot")
			
		getLogger().info("Terminating FUSE FILE ACCESS MANAGER !")
		self.__fusefam.terminate()
		if os.getuid() != 0 :
			try:
				import pynotify
				if pynotify.init("nssbackup"):
					n = pynotify.Notification("nssbackup", "Ending Backup Session")
					n.show()
				else:
					getLogger().warning("there was a problem initializing the pynotify module")
			except Exception, e:
				getLogger().warning(str(e))
			

	def __checkTarget(self):
		"""
		"""
		# Check if the mandatory target option exists
		if not self.config.has_option("general","target") :
			raise SBException ("Option target is missing, aborting.")
		
		# Check if the target dir exists or create it
		if not FAM.exists(self.config.get("general","target")) :
			getLogger().info("Creating the target dir '%s'" % self.config.get("general","target"))
			FAM.makedir(self.config.get("general","target"))
		
		# Try to write inside so that we don't work for nothing
		try :
			FAM.writetofile(self.config.get("general","target")+"/test", "testWritable")
			FAM.delete(self.config.get("general","target")+"/test")
		except Exception, e :
			getLogger().error("Target not writable : " + str(e))
			raise e
	
	def __isIncOrFull(self, listing ):
		"""
		@param listing: a list of snapshot
		@return: a tuple (name, base, prev, increment)
		""" 
		r = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})[\:\.](\d{2})[\:\.](\d{2})\.\d+\..*?\.(.+)$")
		prev = {}
		base = None
		if len(listing) == 0 :
			increment = 0
		else:
			m = r.search( listing[0].getName() )
			if m.group( 7 ) == "ful":  # Last backup was full backup
				getLogger().debug("Last (%s) was a full backup" % listing[0].getName())
				if (datetime.date.today() - datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3)) ) ).days <= self.config.get("general","maxincrement") :
			    	    # Less then maxincrement days passed since that -> make an increment
					increment = time.mktime((int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4)),int(m.group(5)),int(m.group(6)),0,0,-1))
					base = listing[0]
					try:
						prev = base.getFilesList()
					except Exception, e:
						getLogger().warning(str(e))
						increment = 0  # Last backup is somehow damaged	
				else:
					increment = 0      # Too old -> make full backup
			else: # Last backup was an increment - lets search for the last full one
				getLogger().debug(" Last backup (%s) was an increment - lets search for the last full one" % listing[0].getName())
				r2 = re.compile(r"ful$")
				for i in listing :
					try: 
						for a,b in i.getFilesList().items() :
							if not prev.has_key(a) : # We always keep the newer incremental file info
								prev[a]=b
					except Exception, e :  # One of the incremental backups is bad -> make a new full one
						getLogger().warning("One of the incremental backups (%s) is bad -> make a new full one : %s " % (i.getName(), str(e)))
						increment = 0
						break
					
					if r2.search( i.getName() ):
						m = r.search( i.getName() )
						if (datetime.date.today() - datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3)) ) ).days <= self.config.get("general","maxincrement") :
							# Last full backup is fresh -> make an increment
							getLogger().debug("Last full backup is fresh (%d days old )-> make an increment" % (datetime.date.today() - datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3)) ) ).days)
							m = r.search( listing[0].getName() )
							increment = time.mktime((int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4)),int(m.group(5)),int(m.group(6)),0,0,-1))
							base = listing[0]
						else: # Last full backup is old -> make a full backup
							getLogger().debug("Last full backup is old -> make a full backup")
							increment = 0
						break
				else:
					getLogger().debug(" No full backup found 8) -> lets make a full backup to be safe")
					increment = 0            # No full backup found 8) -> lets make a full backup to be safe
		
		# Determine and create backup target directory
		hostname = socket.gethostname()
		
		tdir = self.config.get("general","target") + "/" + datetime.datetime.now().isoformat("_").replace( ":", "." ) + "." + hostname + "."
		if increment != 0:
			tdir = tdir + "inc"
		else:
			tdir = tdir + "ful"
			
		return (tdir, base, prev, increment)
	
	
	def getConfig(self) :
		"""
		get the config for the instance of nssbackup 
		(/etc/nssbackup.conf if root  or ~/.nssbackup/nssbackup.conf if normal user)
		"""
		global __config
		if self.__config : return self.__config
		else :
			self.__config = ConfigManager()
