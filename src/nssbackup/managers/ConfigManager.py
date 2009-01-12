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
#
# Authors: Ouattara Oumar Aziz <wattazoum@gmail.com>
#		   Jean-Peer Lorenz <peer.loz@gmx.net>

import os
import os.path
import re
import ConfigParser
import smtplib
from gettext import gettext as _
from optparse import OptionParser

from nssbackup.util.log import LogFactory
import FileAccessManager as FAM
import nssbackup.util as Util
from nssbackup.util.exceptions import SBException
from nssbackup.util.exceptions import NonValidOptionException
from nssbackup.util.exceptions import NotValidSectionException


def getUserConfDir():
	"""
	Get the user config dir using the XDG specification
	"""
	if os.getuid() == 0 :
		confdir = "/etc/"
	else :
		confdir = os.sep.join([os.getenv("XDG_CONFIG_DIR", 
					os.path.normpath(os.sep.join( [os.getenv("HOME"),".config"] )) ),
						"nssbackup/"])
	if not os.path.exists(confdir) :
		os.makedirs(confdir)
	
	return confdir

def getUserDatasDir():
	"""
	Get the user datas dir using the XDG specification
	"""
	datadir = os.sep.join([os.getenv("XDG_DATA_HOME", 
				os.path.normpath(os.sep.join( [os.getenv("HOME"),".local","share"] )) ),
					"nssbackup/"]) 
	if not os.path.exists(datadir) :
		os.makedirs(datadir)
	return datadir

def getUserTempDir():
	"""Returns the user's temporary directory. It is always the directory
	'/tmp' used.
	
	@return: full path to the NSsbackup tempdir
	
	@todo: Review the use of '/tmp' as tempdir as solution for several different distributions?
	"""
	tempdir = os.path.join( "/tmp", "nssbackup/" ) 
	if not os.path.exists(tempdir) :
		os.mkdir(tempdir)
	return tempdir


class ConfigManager(ConfigParser.ConfigParser):
	"""nssbackup config manager
	
	The configuration manager is responsible for the following:
	 
	* creates a logger instance with specified log level and log file target
	
	
	Format of the configuration file used by NSsbackup:
	
	[general]
	mountdir = /mnt/nssbackup
	target=/var/backup
	#target=ssh://user:pass@example.com/home/user/backup/
	
	# Where to put a lockfile (Leave the default)
	lockfile=/var/lock/nssbackup.lock
	
	# Maximal interval between two full backups (in days)
	maxincrement = 21
	
	# Backup format:

	# none : use a tar - All files are stored in a non compressed tar archive
	# gzip : use a tar.gz - All files are stored in the files.tar.gz
	# bzip2 :use a tar.bz2 - All files are stored in the files.tar.bz2
	format = gzip
	backuplinks=1
	
	# For the split functionality :
	# this should be an integer . It represent the size in KB of each archive (0 => unlimited)
	splitsize = 0
	
	[log]
	level = 20
	file = nssbackup.log
	
	[report]
	from =
	to = 
	smtpserver =
	smtpport = 
	smtptls =
	
	
	[dirconfig]
	# In this section you describe, what directories to backup and what to skip 
	# More precise commands override wider ones, for example:
	# /var=1  # This means that the whole /var directory is to be backuped
	# /var/cache=0 # This means the /var/cache and its subdirectories are not
	#              # to  be backuped
	# In this case all /var, except /var/cache will be backuped
	# It works the othe way around too
	# by default nothing is backuped
	
	/etc/=1
	/home/=1
	/usr/local/=1
	/var/=1
	/var/cache/=0
	/var/tmp/=0
	/proc/=0
	/dev/=0
	/sys/=0
	/tmp/=0
	/var/tmp/=0
	
	[schedule]
	anacron = daily
	cron = 
	
	[exclude]
	
	# Comma-separated list of regular expressions to exclude from backup
	# use this to exclude certain types of files or directories
	#
	# Note: If any of these expressions matches within the whole pathname
	#	of the file, it will NOT be backuped. Keep this list as specific 
	#	and as short as possible.
	
	regex=\.mp3,\.avi,\.mpeg,\.mpg,\.mkv,\.ogg,\.ogm,\.tmp,/home/[^/]+?/\.thumbnails/,/home/[^/]+?/\.Trash,/home/[^/]+?/\..+/[cC]ache
	
	# Do not backup files bigger then this (in bytes)
	
	maxsize=100000000
	
	@todo: The configuration manager should not create the logger itself!
		   This should be done outside of the configuration after reading and
		   parsing the config file.
	"""
	
	cronheader = "SHELL=/bin/bash \nPATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n\n"
	
	servicefile 		 = Util.getResource("nssbackup")
	default_profile_name = _("Default Profile")
	unknown_profile_name = _("Unknown Profile")
	
	# these variables should be read-only
	__logfile_basename 	= "nssbackup"
	__logfile_ext		= "log"

	
	prfRE = re.compile('^nssbackup-(.+?).conf(-disable)?$')
	
	# Default values, constants and the like
	our_options = {
	 'general' 		: { 'mountdir'		: str,
				        'target'  		: str ,
				   		'lockfile' 		: str ,
				   		'maxincrement' 	: int ,
				   		'format' 		: str,
				   		'splitsize' 	: int,
				   		'purge' 		: str,
				   		'run4others' 	: int,
				   		'backuplinks' 	: int },
	 'log' 			: {'level' : int , 'file' : str },
	 'report' 		: {'from' :str, 'to' : str,'smtpserver' : str,
				 	   'smtpport' : int, 'smtpuser' : str,
				 	   'smtppassword' : str, 'smtptls' : int,
				       'smtpcert': str, 'smtpkey': str },
	 'dirconfig'	: { '*' : str },
	 'exclude' 		: { 'regex' : list, 'maxsize' : int },
	 'places' 		: { 'prefix' : str },
	 'schedule' 	: {'anacron' : str , 'cron' : str }
	}
	
	def __init__(self, configfile = None):
		"""Default constructor.
		
		@param configfile: Full path to the used configuration file. 
		"""
		ConfigParser.ConfigParser.__init__(self)

		self.regex		= r"\.mp3,\.avi,\.mpeg,\.mkv,\.ogg,\.iso,"\
		                   "/home/[^/]+?/\.thumbnails/,/home/[^/]+?/\.Trash,"\
		                   "/home/[^/]+?/\..+/[cC]ache"
		                   
		self.dirconfig	= { '/etc/'			: '1',
							'/var/'			: '1',
							'/home/'		: '1',
							'/var/cache/'	: '0',
							'/var/tmp/'		: '0',
							'/var/spool/'	: '0',
							'/usr/local/'	: '1',
							'/media/'		: '0'
						  }
		
		self.mountdir			= "/mnt/nssbackup"
		self.target				= "/var/backup"
		self.maxincrement		= str(7)
		self.prefix				= "/usr"
		self.lockfile			= "/var/lock/nssbackup.lock"
		
		self.__logfile_dir		= "/var/log"
		
		self.format				= "gzip"
		
		self.conffile 			= None
		self.logger 			= None
		self.__profileName 		= None

		self.valid_options 		= {}
		self.filename_from_argv = None
		self.argv_options 		= {}
		
		self.setValidOpts( self.our_options )
		
		# command line preempt default option location
		self.parseCmdLine()
# TODO: remove command-line parsing from here; this class should only take a filenam eas parameter

		# use the given conf-file only if no was given on cmdline
		if not self.conffile and configfile:
			self.conffile = configfile

		_conffile_used = False	# helper to print out an informative message

		# if a conf-file is set, evaluate this one and overwrite default values
		if self.conffile:
			self.read(self.conffile)
			_conffile_used = True
		else:
			self._set_defaults()
			
		self.__create_logger()
			
		if self.valid_options:
			self.validateConfigFileOpts()

		if _conffile_used:
			self.logger.info("ConfigManager created from config file '%s'." % self.conffile)
		else :
			self.logger.info("ConfigManager created with default values. Config file set to '%s'.")
			

	def initSection(self):
		"""Init the config sections.
		"""
		if not self.has_section("general"):
			self.add_section("general")
		if not self.has_section("dirconfig"):
			self.add_section("dirconfig")
		if not self.has_section("exclude"):
			self.add_section("exclude")
		if not self.has_section("log"):
			self.add_section("log")
		if not self.has_section("report"):
			self.add_section("report")
		if not self.has_section("places"):
			self.add_section("places")
		if not self.has_section("schedule"):
			self.add_section("schedule")

	def _set_defaults(self):
		"""Sets default values for this configuration. It distinguishes between
		users and super-users.
		"""
		if os.geteuid() == 0 :
			self.__set_defaults_for_root()
		else :
			self.__set_defaults_for_users()
	
	def __set_defaults_for_root(self):
		"""Set the default config for root user.
		"""
		self.initSection()
		self.conffile = "/etc/nssbackup.conf"

		# Section general
		self.set("general", "mountdir", self.mountdir )
		self.set("general", "target", self.target )
		self.set("general", "lockfile", self.lockfile )
		self.set("general", "maxincrement", self.maxincrement )
		self.set("general", "format", self.format )
		self.set("general", "purge", "log")
		
		# Section log
		self.set("log", "level", "20" )
		self.set_logfile()
		
		# Section dirconfig
		for a,b in self.dirconfig.iteritems() :
			self.set("dirconfig", a, b) 
		
		# Section exclude
		
		# Section places
		self.set("places", "prefix", self.prefix)
		
		if not FAM.exists(self.get("log","file")) :
			FAM.createfile(self.get("log","file"))
	
	def __set_defaults_for_users(self):
		"""Set the default config for normal users.
		"""
		self.initSection()		
		self.conffile = getUserConfDir() + "nssbackup.conf"

		# Section general
		self.set("general", "mountdir",  getUserDatasDir()+"mountdir" )
		self.set("general", "target", getUserDatasDir()+"backups" )
		self.set("general", "lockfile", getUserDatasDir()+"nssbackup.lock" )
		self.set("general", "maxincrement", self.maxincrement )
		self.set("general", "format", self.format )
		self.set("general", "purge", "log")
		
		# Section log
		self.set("log", "level", "20" )
		self.set_logdir(getUserDatasDir())
		self.set_logfile()
		
		# Section dirconfig
		self.set("dirconfig",os.getenv("HOME")+os.sep,"1")
		
		# Section exclude
		
		# Section places
		self.set("places", "prefix", self.prefix)
		
		if not FAM.exists(self.get("log","file")) :
			FAM.createfile(self.get("log","file"))
		
	def optionxform(self, option):
		"""
		Default behaviour of ConfigParser is to set the option keys to lowercase. 
		by overiding this method, we make it case sensitive. that's really important for dirconfig pathes 
		"""
		return str( option )
	           
	def has_option(self, section, option) :
		if section == "dirconfig" and not ConfigParser.ConfigParser.has_option(self,section, option) :
			if option == "remote" :
				return ConfigParser.ConfigParser.has_option(self, section, option)
			#search through remote option to get the option
			if ConfigParser.ConfigParser.has_option(self, "dirconfig", 'remote') :
				remotes = self.get("dirconfig", "remote")
				if type(remotes) == str :
					remotes = eval(remotes)
				if type(remotes) != dict :
					raise SBException(_("Couldn't evaluate '%(parameter)s' as a dictionary (value got = '%(value)r' )") % {'parameter': remotes,'value': type(remotes)})
				if not remotes.has_key(option) :
					# then it wasn't for us , fall back on the parent
					return ConfigParser.ConfigParser.has_option(self, section, option)
				else :
					# we have this key
					return True
			else : 
				return ConfigParser.ConfigParser.has_option(self, section, option)
		else :
			#fall back in parent behaviour
			return ConfigParser.ConfigParser.has_option(self, section, option)
		
	def get(self, section, option):
		"""
		"""
		# if we have (dirconfig,opt), if opt=remote
		if section == "dirconfig" and not option == 'remote' and self.has_option(section, option) and not ConfigParser.ConfigParser.has_option(self,section, option):
			#search through remote option to get the option
			remotes = ConfigParser.ConfigParser.get(self, "dirconfig", "remote",True)
			if type(remotes) == str :
				remotes = eval(remotes)
			if type(remotes) != dict :
				raise SBException(_("Couldn't evaluate '%(parameter)s' as a dictionary (value got = '%(value)r' )") % {'parameter': remotes,'value': type(remotes)})
			# we have that key
			return remotes[option]
		elif section == "dirconfig" and option == 'remote' and ConfigParser.ConfigParser.has_option(self,section, option):
			remotes = ConfigParser.ConfigParser.get(self, "dirconfig", "remote",True)
			if type(remotes) == str :
				remotes = eval(remotes)
			if type(remotes) != dict :
				raise SBException(_("Couldn't evaluate '%(parameter)s' as a dictionary (value got = '%(value)r' )") % {'parameter': remotes,'value': type(remotes)})
			return remotes
		else :
			#fall back in parent behaviour
			return ConfigParser.ConfigParser.get(self, section, option,True)
		
	def set(self,section, option, value):
		"""
		Set an option just like a configParser but in case of the 'remote' option in 'dirconfig'.
		In this case, value must be a dict with the value you want to set.
		eg. value = {'ssh://test/': 1, 'ssh://test/test': 0}
		You can set one at a time, the value will be append to the 'remote' dict
		"""
		if section == "dirconfig" and option == "remote" :
			if type(value) != dict :
				raise SBException(_("You must provide a dictionary"))
			if not self.has_option(section, option) :
				ConfigParser.ConfigParser.set(self, section, option, value)
			else :
				remotes = ConfigParser.ConfigParser.get(self, section, option,True)
				if type(remotes) == str :
					remotes = eval(remotes)
				if type(remotes) != dict :
					raise SBException("Couldn't eval '%s' as a dict (value got = '%r' )"% (remotes, type(remotes)))
				for rsource, flag in value.iteritems() :
					remotes[rsource] = flag
				ConfigParser.ConfigParser.set(self, section, option, remotes)
		else :
			#fall back in normal bahaviour
			ConfigParser.ConfigParser.set(self, section, option, value)
			
	def remove_option(self,section, option):
		"""
		remove an option, but it's different for remote. if option = "remote" then the whole remote option will be removed.
		If option is in remote dict, section ='dirconfig' and option='ssh://test/me' . then the entry in the remote dict will be removed.
		"""
		if section == "dirconfig" and not ConfigParser.ConfigParser.has_option(self,section, option) :
			#search through remote option to get the option
			if not self.has_option("dirconfig", "remote"):
				#fall back in parent behaviour
				ConfigParser.ConfigParser.remove_option(self, section, option)
			else :
				self.logger.debug("search through remote option to get the option")
				remotes = self.get("dirconfig", "remote")
				if type(remotes) == str :
					remotes = eval(remotes)
				if type(remotes) != dict :
					raise SBException("Couldn't eval '%s' as a dict (value got = '%r' )"% (remotes, type(remotes)))
				if not remotes.has_key(option) :
					# then it wasn't for us , fall back on the parent
					ConfigParser.ConfigParser.remove_option(self, section, option)
				else :
					# we have that key
					remotes.pop(option)
					self.logger.debug("remote is now '%r'" %remotes)
					ConfigParser.ConfigParser.set(self, section, "remote", remotes)
		else :
			#fall back in parent behaviour
			ConfigParser.ConfigParser.remove_option(self, section, option)
			
	
	def setValidOpts(self, valid_options, parse_cmdline = False):
		self.valid_options = valid_options
		if parse_cmdline :
			self.parseCmdLine()

	def __create_logger(self):
		"""Initializes logger with profile name as identifier
		and use the specified file as log file.
		"""
		if self.has_section("log") and self.has_option("log", "file"):
			logf = self.get("log", "file")
			self.__logfile_dir = os.path.dirname(logf)
			
			if self.has_option("log", "level") :
				self.logger = LogFactory.getLogger(self.getProfileName(), logf,
												   self.getint("log","level"))
			else :
				self.logger = LogFactory.getLogger(self.getProfileName(), logf)

			self.logger.debug("Log output for [%s] is directed to file '%s'" % (self.getProfileName(), logf))
				
		# if no file is specified, use the logger's default (no log file)
		else:
# TODO: Raise an assertion exception if no log section was found ?!
			self.logger = LogFactory.getLogger(self.getProfileName())
			self.logger.debug("Log output for [%s] is not directed to any file" % (self.getProfileName()))

	def read(self, filename=None ):
		"""Reads the configuration file and returns its content. Moreover it
		sets up a logger with appropriate log file and log level. This method
		overwrites the 'read' method from base class.
		
		@param filename: Full path of configuration file.
		@type filename:  String
		
		@return: The read configuration
		@rtype:  Same type as the base class returns
		"""
		if filename:
			self.conffile = filename
		retValue = ConfigParser.ConfigParser.read(self, self.conffile)
		
		if len(retValue) == 0 :
			raise SBException(_("The config file '%s' couldn't be read !")\
								% self.conffile )
		return retValue

	def parseCmdLine(self):
		usage = "Usage: %prog [options] (use -h for more infos)"
		parser = OptionParser(usage, version="%prog 0.2")
		parser.add_option("-c", "--config-file", dest="config",
						metavar="FILE", help="set the config file to use")
		
		(options, args) = parser.parse_args()
		if len(args) > 0:
			parser.error("You must not provide any non-option argument")
		if options.config :
			self.conffile = options.config

	def validateConfigFileOpts(self):
		self.logger.debug("Validating config file")
		if (self.valid_options is None):
			return
		for section in self.sections():
			try:
				for key in self.options(section):
					if (not self.valid_options.has_key(section)):
						raise NotValidSectionException (_("section [%(section)s] in '%(configfile)s' should not exist, aborting") % {'section': section, 'configfile' :self.conffile})
					if (self.valid_options[section].has_key(key) or self.valid_options[section].has_key('*')):
						continue
					raise NonValidOptionException ("key '%s' in section '%s' in file '%s' is not known, a typo possibly?" % (key, section, self.conffile))
			except SBException, e:
				self.logger.error(str(e))
				raise e
		return True

	def allOpts(self):
		retVal = []
		for section in self.sections():
			for key in self.options(section):
				value = self.get(section, key, raw = True)
				retVal.append( (key,value))
		return retVal

	def __str__(self):
		retVal = []
		for section, sec_data in self._sections.iteritems():
			retVal.append("[%s]" % section)
			[retVal.append("%s = %s" % (o, repr(v)))
				for o, v in sec_data.items() if o != '__name__']
		return "\n".join(retVal)
	
	def setSchedule(self, isCron, value):
		"""Set the backup Schedule
		@param isCron : 0 for anacron schedule , 1 for Cron
		@param value : daily/monthly/hourly/weekly for anacron, or the cronline to add at /etc/cron.d/nssbackup for cron  
		"""
		anacronValues = ["daily","monthly","hourly","weekly"]
		if type(isCron) != int or not (isCron in [0,1]) : 
			raise NonValidOptionException("isCron must be 0 or 1")
		if isCron == 0 :
			if value not in anacronValues :
				raise NonValidOptionException("Valid values for anacron are : %s , I recieved '%s'" % (str(anacronValues),value))
			else :
				if self.has_option("schedule", "cron") :
					self.logger.debug("Removing Cron config ")
					self.remove_option("schedule", "cron")
				self.logger.debug("Setting anacron to :"+ value)
				self.set("schedule", "anacron", value)
		elif isCron == 1 :
			if self.has_option("schedule", "anacron") :
				self.logger.debug("Removing anaCron config ")
				self.remove_option("schedule", "anacron")
			self.logger.debug("Setting cron to :"+ value)
			self.set("schedule", "cron", value)
	
	def getSchedule(self):
		"""
		get the actual schedule state
		@return: (isCron, value) a tuple where isCron = 0 if anacron is set and 1 \
		if cron is set . If None has been found , 'None' is return
		"""
		if not self.has_section("schedule") or (not self.has_option("schedule", "cron") and not self.has_option("schedule", "anacron")) :
			self.logger.warning("Config file doesn't have schedule infos, probing from filesystem ")
			#hourly
			if os.path.exists("/etc/cron.hourly/nssbackup"):
				self.logger.debug("Anacron hourly has been found")
				return (0, "hourly")
			# daily
			elif os.path.exists("/etc/cron.daily/nssbackup"):
				self.logger.debug("Anacron daily has been found")
				return (0, "daily")
			# weekly
			elif os.path.exists("/etc/cron.weekly/nssbackup"):
				self.logger.debug("Anacron weekly has been found")
				return (0, "weekly")
			# monthly
			elif os.path.exists("/etc/cron.monthly/nssbackup"):
				self.logger.debug("Anacron monthly has been found")
				return (0, "monthly")
			if os.path.exists("/etc/cron.d/nssbackup"):
				self.logger.debug("Cron has been found")
				return (1, FAM.readfile("/etc/cron.d/nssbackup"))
			# none has been found
			return None
		else :
			if self.has_option("schedule", "cron") : 
				return (1, self.get("schedule", "cron"))
			elif self.has_option("schedule", "anacron") :
				return (0, self.get("schedule", "anacron"))
			else :
				return None
	
	def getProfileName(self):
		"""Returns the current profile name for the current ConfigManager.
		
		@return: the current profile name if the config file name match the
				 naming convention or Unknow otherwise
		@raise SBException: if the configfile isn't set
		
		@todo: Implement Command-Query Separation Principle (CQS)!
		"""
		if self.__profileName : 
			return self.__profileName
		
		if not self.conffile: 
			raise SBException(_("The config file is not set yet into this "\
							    "ConfigManager"))		
		# find the profile 
		cfile = os.path.basename(self.conffile)

		if cfile == "nssbackup.conf" :
			self.__profileName = self.default_profile_name
		else :
			m = self.prfRE.match(cfile)
			if not m:
				self.__profileName = self.unknown_profile_name
			else :
				self.__profileName = m.group(1)
				
		return self.__profileName
	
	def getProfiles(self):
		"""Get the configuration profiles list
		 
		@return: a dictionarity of { name: [path_to_conffile, enable] } 
		"""
		prfDir = getUserConfDir()+"nssbackup.d/"
		
		self.logger.debug("Getting profiles from '%s'" % prfDir)
		
		if not os.path.exists(prfDir) or not os.path.isdir(prfDir) :
			return dict()
		
		profiles = dict()
		
		for cf in os.listdir(prfDir) :
			m = self.prfRE.match(cf)
			if m : 
				self.logger.debug("Found %s "% m.group(0))
				name, path, enable = m.group(1), prfDir+m.group(0), (m.group(2) is None)
				profiles[name] = [path,enable]
		
		return profiles
	
	def set_logdir(self, logdir):
		"""The given directory is set for use with log files.
		"""
		self.__logfile_dir = logdir
		
	def get_logdir(self):
		"""Returns the currently set directory for log files.
		"""
		return self.__logfile_dir

	def set_logfile(self):
		"""Retrieves the path to log file and writes it into the configuration.
		"""
		logf = self.get_logfile()
		if not self.has_section("log") :
			self.add_section("log")
		self.set("log", "file", logf )
		
	def get_logfile(self):
		"""Builds the full path to log file for this configuration and
		returns it. The log file for the default profile is named
		'nssbackup.log', log files for other profiles are extended by
		the profile's name to keep them unique and avoid problems while logging.
		"""
		self.getProfileName()
		if self.__profileName == self.default_profile_name:
			logfname = "%s.%s" % (self.__logfile_basename, self.__logfile_ext)
		else:
			logfname = "%s-%s.%s" % (self.__logfile_basename, self.__profileName,
									 self.__logfile_ext)
		logf = os.path.join(self.__logfile_dir, logfname)
		return logf
		
	def setLogSection(self, level=20 , filen = None ):
		"""CURRENTLY NOT USED ANYWHERE!
		
		Log section is :
		[Log]
		# level is in ( 10, 20( default ), 30, 40, 50 ) 
		level = 20
		file = /var/log/nssbackup.log
		@param level : 10 = DEBUG, 20 = INFO, 50 = ERROR
		@param file : The logfile to use
		"""
		if not self.has_section("log") :
			self.add_section("log")
		self.set("log", "level", level)
		if filen is not None :
			self.set("log", "file", filen )
	
	def getLogSection (self):
		"""CURRENTLY NOT USED ANYWHERE!
		
		Get the log section
		@return: a tuple (level, file) , (None, None) is return if none has been found
		"""
		filen, level = None, None
		if self.has_section("log") :
			if self.has_option("log", "level") :
				level = self.get("log", "level")
			else:
				level = None
			
			if self.has_option("log", "file") :
				filen = self.get("log", "file")
			else:
				filen = None
		else : 
			filen, level = None, None
		
		return ( level, filen )
	
	def setReportSection(self, to, smtpserver, smtpport, _from=None , smtpuser = None, smtppassword = None,
						  smtptls = None, smtpcert = None, smtpkey = None ):
		"""
		Sets the report section
		@param to :
		@param smtpserver :
		@param smtpport :
		@param _from : (= None)
		@param smtpuser : (= None)
		@param smtppassword :(= None)
		@param smtptls : (= None) 1 to activate TLS or SSL
		@param smtpcert : (= None)  
		@param smtpkey : (= None)
		"""
		if not self.has_section("report") :
			self.add_section("report")
		
		self.set("report", "to", to)
		self.set("report", "smtpserver", smtpserver)
		self.set("report", "smtpport", smtpport)
		
		if _from : self.set("report", "from", _from)
		if smtptls : self.set("report", "smtptls", smtptls)
		if smtpuser and smtppassword : 
			self.set("report", "smtpuser", smtpuser)
			self.set("report", "smtppassword", smtppassword)
		if smtpcert and smtpkey :
			self.set("report", "smtpcert", smtpcert)
			self.set("report", "smtpkey", smtpkey)
		
	def removeReportSection(self):
		self.remove_section("report")
		
	def saveConf(self,configfile=None):
		"""
		Save the configuration 
		@param configfile: The config file in which to write the configuration. Default is in the default location 
		"""
		if configfile :
			fd = FAM.openfile(configfile, True)
		else :
			fd = FAM.openfile(self.conffile, True)
		self.write(fd)
		fd.close()
		
		self.writeSchedule()
	
	def writeSchedule(self):
		"""
		Write the schedule from the configuration file
		"""
		
		if not self.has_section("schedule") or (not self.has_option("schedule", "anacron") and not self.has_option("schedule", "cron")) :
			return
		elif os.geteuid() != 0 :
				self.logger.warning("Not implemented for non root users yet")
				return
		else :
			if self.has_option("schedule", "cron") :
				self.logger.debug("Saving Cron entries")
				self.erase_services()
				execline = "if [ -x '"+Util.getResource("nssbackup")+"' ]; then "+Util.getResource("nssbackup")+"; fi;"
				FAM.writetofile("/etc/cron.d/nssbackup", self.cronheader + self.get("schedule", "cron") + "\troot\t"+ execline)
				
			if self.has_option("schedule", "anacron") :
				self.logger.debug("Saving Cron entries")
				if self.get("schedule", "anacron") == "hourly" :
					self.erase_services()
					os.symlink(self.servicefile,"/etc/cron.hourly/nssbackup")
				elif self.get("schedule", "anacron") == "daily" :
					self.erase_services()
					os.symlink(self.servicefile,"/etc/cron.daily/nssbackup")
				elif self.get("schedule", "anacron") == "weekly" :
					self.erase_services()
					os.symlink(self.servicefile,"/etc/cron.weekly/nssbackup")
				elif self.get("schedule", "anacron") == "monthly" :
					self.erase_services()
					os.symlink(self.servicefile,"/etc/cron.monthly/nssbackup")
				else : 
					self.logger.warning("'%s' is not a valid value" % self.get("schedule", "anacron"))

	def erase_services(self):
			listServ = ["/etc/cron.hourly/nssbackup", "/etc/cron.daily/nssbackup", 
					"/etc/cron.weekly/nssbackup", "/etc/cron.monthly/nssbackup", "/etc/cron.d/nssbackup"]
			for l in listServ : 
				if os.path.exists(l) :
					self.logger.debug("Unlinking '%s'" % l )
					os.unlink(l)
	
	def testMail(self):
		"""
		Test the mail settings
		@return: True if succeded
		@raise SBException: catch this to get the error message of why it didn't run
		"""
		if not self.has_option("report", "to"):
			raise SBException (_("Set the reciever of this mail"))
		if not self.has_option("report","smtpserver") :
			raise SBException (_("Set the SMTP server"))
		if (self.has_option("report","smtpuser") and not self.has_option("report","smtppassword") ) \
			or (not self.has_option("report","smtpuser") and self.has_option("report","smtppassword") ) :
			raise SBException (_("When setting a username (resp password), password (resp username) is mandatory"))
		if not self.has_option("report", "smtptls") and (self.has_option("report", "smtpcert") or self.has_option("report","smtpkey)") ) :
			raise SBException (_("Choose the SSL option (smtptls=1) to be able to use Cert and Key"))
		if self.has_option("report", "smtptls") and ((self.has_option("report","smtpcert") and not self.has_option("report","smtpkey") ) \
			or (not self.has_option("report","smtpcert") and self.has_option("report","smtpkey") ) ):
			raise SBException (_("When setting a ssl certificate (resp key), key (resp certificate) is mandatory"))
		
		try :
			server = smtplib.SMTP()
			
			# getting the connection
			if self.has_option("report","smtpport") :
				server.connect(self.get("report","smtpserver"), self.get("report","smtpport"))
			else : 
				server.connect(self.get("report","smtpserver"))
			
			if self.has_option("report","smtptls") and self.get("report","smtptls") == 1 : 
				if self.has_option("report","smtpcert") and self.has_option("report","smtpkey") :
					server.starttls(self.get("report","smtpkey"), self.get("report","smtpcert"))
				else :
					server.starttls()
			if self.has_option("report","smtpuser") and self.has_option("report","smtppassword") : 
				server.login(self.get("report","smtpuser"), self.get("report","smtppassword"))
			
			server.helo()
			server.close()
			return True
		except Exception, e:
			raise SBException(e)
		
	def isConfigEquals(self,config):
		"""
		a function to compare two configuration manager.
		@param config : a configManager instance
		@return: True if the config are equals, False otherwise
		@rtype: boolean
		"""
		if not isinstance(config, ConfigManager) :
			raise SBException("Can't compare a ConfigManager with type '%s'"% str(type(config)))
		
		for s in self.sections() :
			if not config.has_section(s) :
				return False
			else :
				for o in self.options(s) :
					if not config.has_option(s, o):
						return False
					else :
						if type(self.get(s, o)) != type(config.get(s, o)) :
							if type(self.get(s, o)) is not str :
								self.set(s,o, repr(self.get(s, o)))
							if type(config.get(s, o)) is not str :
								config.set(s,o, repr(config.get(s, o)))
						if not self.get(s, o) == config.get(s, o) :
							return False
				for o in config.options(s) :
					if not self.has_option(s, o):
						return False
					else :
						if type(self.get(s, o)) != type(config.get(s, o)) :
							if type(self.get(s, o)) is not str :
								self.set(s,o, repr(self.get(s, o)))
							if type(config.get(s, o)) is not str :
								config.set(s,o, repr(config.get(s, o)))
						if not self.get(s, o) == config.get(s, o) :
							return False
		return True
		
		
class ConfigStaticDatas(object):
	"""
	Config Datas storage
	"""
	def __init__(self):
		pass
	
	loglevels = {'20' : ("Info",1) ,'10' : ("Debug", 0), '30' : ("Warning", 2), '50' : ("Error", 3)}
	timefreqs = {"never":0, "hourly": 1,"daily": 2,"weekly": 3,"monthly": 4,"custom":5}
	cformat = {'none':0, 'gzip':1, 'bzip2':2}
	
	splitSize = {'Unlimited':0,'100 MB': 100,'250 MB':250,'650 MB': 650,'2 GB (FAT16)':2000,'2 GB (FAT16)': 4000, 'Custom': -1}
