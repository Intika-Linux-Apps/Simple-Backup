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

"""
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
# backup the links 
backuplinks=1
# follow symlinks
followlinks=1

# For the split functionality :
# this should be an integer.
# It represent the size in KiB (1024 B) of each archive
# (splitsize <= 0: unlimited)
splitsize = 0

# Set the package manager command to backup the package list
packagecmd = <whatever command that will be launched>

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
"""

import os.path
import re
import ConfigParser
import smtplib
import types
from gettext import gettext as _
from optparse import OptionParser

from nssbackup import Infos
from nssbackup.util.log import LogFactory
import FileAccessManager as FAM
import nssbackup.util as Util
from nssbackup.util.exceptions import SBException
from nssbackup.util.exceptions import NonValidOptionException
from nssbackup.util.exceptions import NotValidSectionException


def getUserConfDir():
	"""Get the user config dir using the XDG specification.
	
	:todo: Use the constants defined in `ConfigManagerStaticData`!
	"""
	if os.getuid() == 0 :
		confdir = "/etc/"
	else :
		confdir = os.sep.join([os.getenv("XDG_CONFIG_DIR", 
				os.path.normpath(os.sep.join([os.getenv("HOME"),".config"]))),
						"nssbackup/"])
	if not os.path.exists(confdir) :
		os.makedirs(confdir)
		
	return confdir

def get_default_conffile_fullpath():
	"""Returns the full path (incl. filename) o the default config file.
	"""
	conffile = os.path.join(getUserConfDir(),
							ConfigManagerStaticData.get_default_conffile())
	return conffile

def getUserDatasDir():
	"""Get the user datas dir using the XDG specification.
	:todo: Use the constants defined in `ConfigManagerStaticData`!	
	
	"""
	datadir = os.sep.join([os.getenv("XDG_DATA_HOME", 
				os.path.normpath(os.sep.join( [os.getenv("HOME"),".local","share"] )) ),
					"nssbackup/"]) 
	if not os.path.exists(datadir) :
		os.makedirs(datadir)
	return datadir

def getUserTempDir():
	"""Returns the user's temporary directory. Currently always
	the directory `/tmp` is used.
	
	:return: full path to the NSsbackup tempdir
	
	:todo: Review the use of '/tmp' as tempdir as solution for several\
		   different distributions?
	:todo: Put the definition of used paths into `ConfigManagerStaticData`!
		   
	"""
	if os.getuid() == 0 :
		tempdir = os.path.join( "/tmp", "nssbackup/" ) 
	else:
		tempdir = os.path.join(getUserDatasDir(), "tmp/")

	if not os.path.exists(tempdir) :
		os.mkdir(tempdir)
		
	return tempdir

def get_profilename(conffile):
	"""Retrieves the name of the profile corresponding to given
	configuration file and returns them.
	"""
	# find the profile 
	cfile = os.path.basename(conffile)

	if cfile == ConfigManagerStaticData.get_default_conffile():
		profilename = ConfigManagerStaticData.get_default_profilename()
	else :
		m = ConfigManagerStaticData.get_profilename_re().match(cfile)
		if not m:
			profilename = ConfigManagerStaticData.get_unknown_profilename()
		else :
			profilename = m.group(1)
			
	return profilename

def is_default_profile(conffile):
	"""Checks whether the given configuration file corresponds to the
	default profile.
	
	@param conffile: full path to configuration file to check
	@return: True if the file corresponds to the default profile, otherwise False.
	@rtype: Boolean
	
	"""
	is_default = False
	cfile = os.path.basename(conffile)
	
	if cfile == ConfigManagerStaticData.get_default_conffile():
		is_default = True
	
	return is_default

def get_logfile_name(conffile):
	"""Determines the profilename from the given pathname `conffile`
	and returns an appropriate logfile name.
	
	The given `conffile` may not exist.
	 	
	"""
	profilename = get_profilename(conffile)
	if profilename == ConfigManagerStaticData.get_default_profilename():
		logfname = ConfigManagerStaticData.get_default_logfile()
	else:
		logfname = ConfigManagerStaticData.get_profile_logfile(profilename)
	return logfname

def get_profiles(prfdir):
	"""Get the configuration profiles list
	 
	@return: a dictionarity of { name: [path_to_conffile, enable] } 
	"""
	profiles = dict()
	if not os.path.exists(prfdir) or not os.path.isdir(prfdir) :
		pass
	else:
		for conff in os.listdir(prfdir) :
			mobj = ConfigManagerStaticData.get_profilename_re().match(conff)
			if mobj: 
				name = mobj.group(1)
				path = os.path.join(prfdir, mobj.group(0))
				enable = (mobj.group(2) is None)
				profiles[name] = [path, enable]
	
	return profiles


class ConfigManager(ConfigParser.ConfigParser):
	"""nssbackup config manager
	
	The configuration manager is responsible for the following:
	 
	* creates a logger instance with specified log level and log file target
	
	@todo: The configuration manager should not create the logger itself!
		   This should be done outside of the configuration after reading and
		   parsing the config file.
		   
	@todo: When a configuration is loaded from disk/file this configuration
			is checked for every required option. Non-existing options are
			then filled with reasonable default values.
			Default values should never be set from the GUI nor should
			default values are taken as 'implicitly' given in any method
			that requires such setting.
			This is not implemented yet.
			
	@todo: Use the RawConfigParser instead of ConfigParser! And maybe the \
			parser should be a member of NSsbackup config!
	"""
	__servicefile 		 = Util.getResource("nssbackup", isFile = True)
	
	def __init__(self, configfile = None):
		"""Default constructor.
		
		@param configfile: Full path to the used configuration file.
		
		@todo: remove command-line parsing from here; \
				this class should only take a filename as parameter.
		"""
		ConfigParser.ConfigParser.__init__(self)

		# configuration object which is set to valid default values
		self.__default_config = _DefaultConfiguration() # is a dummy
		self.__create_default_config_obj()
		
		self.__dirconfig	= {}
		
		self.__logfile_dir		= ""
		self.conffile 			= None
		self.logger 			= None
		self.__profileName 		= None

		self.valid_options 		= {}
		self.filename_from_argv = None
		self.argv_options 		= {}
		
		self.setValidOpts(ConfigManagerStaticData.get_our_options())
		
		# command line preempt default option location
		self.__parseCmdLine()
# TODO: remove command-line parsing; class should only take a filename as param

		# use the given conf-file only if no was given on cmdline
		if not self.conffile and configfile:
			self.conffile = configfile

		_conffile_used = False	# helper to print out an informative message

		# if a conf-file is set, evaluate this one and overwrite default values
		if self.conffile:
			self.read(self.conffile)
			_conffile_used = True
		else:
			self._set_defaultprofile_values_to_default()
			
		self.__create_logger()
			
		if self.valid_options:
			self.validateConfigFileOpts()

		if _conffile_used:
			self.logger.info("ConfigManager created from config file '%s'."\
							  % self.conffile)
		else :
			self.logger.info("ConfigManager created with default values. "\
							 "Config file set to '%s'." % self.conffile)
			
	def __str__(self):
		retval = []
		for section, sec_data in self._sections.iteritems():
			retval.append("[%s]" % section)
			[retval.append("%s = %s" % (o, repr(v)))
				for o, v in sec_data.items() if o != '__name__']
		return "\n".join(retval)
			
	def __init_sections(self):
		"""Initializes the sections of the configuration.
		
		@todo: Use the 'our_options' from ConfigManagerStaticData class for \
				initialisation.
				
		@todo: Should we remove *unknown* sections?
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

	def _set_defaultprofile_values_to_default(self):
		"""Makes this configuration the default profile by pointing it to
		the default configuration file and sets according default values
		for the configuration. It distinguishes between users and super-users.
		"""
		self.conffile = get_default_conffile_fullpath()
		self.set_values_to_default()

	def __create_default_config_obj(self):
		"""Creates an object containing the default configuration and stores it
		in the according instance variable. Differences between normal users
		and privileged users (i.e. admins) is taken into account.
		"""
		if os.geteuid() == 0:
			self.__default_config = _DefaultConfigurationForAdmins()
		else:
			self.__default_config = _DefaultConfigurationForUsers()

	def __get_default_config_obj(self):
		"""Private accessor method that returns the default configuration
		object. Use this method rather direct access to the instance
		variable in order to ensure the object exists.
		"""
		if self.__default_config is None:
			raise ValueError("No default configuration object was created yet.")
		if not isinstance(self.__default_config, _DefaultConfiguration):
			raise TypeError("Given configuration is not of type \
							'DefaultConfiguration'. Got '%s' instead." \
							% type(self.__default_config))
		return self.__default_config

	def set_values_to_default(self):
		"""Sets default values for this configuration. It is distinguished
		between normal users and super-users. The path to the current
		configuration file (i.e. the current profile) is not touched.
		
		@note: This method's purpose is to provide reasonable values when
				creating a fresh configuration and restoring of these
				'recommended' (or predefined) defaults on existing configs.
		"""
		defaults = self.__get_default_config_obj()
		self.__init_sections()		
		# General
		self.set("general", "maxincrement", str(defaults.get_max_increment()))
		self.set("general", "format", defaults.get_compress_format())
		self.set("general", "splitsize", str(defaults.get_split_size()))

		# dirconfig and excludes
		self.__set_dirconfig(defaults.get_dir_config())
		self.__set_regex_excludes(defaults.get_regex_excludes())

		# other exclude reasons
		self.set("exclude", "maxsize", str(defaults.get_max_filesize()))		
		followlinks = "0"
		if defaults.get_follow_links() is True:
			followlinks = "1"
		self.set("general", "followlinks", followlinks)
		
		# target (= destination)
		self.set_target_to_default()

		# schedule
		schedule = defaults.get_schedule()
		if schedule[1] != "":
			is_cron = 0
			if schedule[0] is True:
				is_cron = 1
			self.setSchedule(is_cron, schedule[1])

		# Purging
		self.set("general", "purge", defaults.get_purge())

		# Section log
		self.set("log", "level", str(defaults.get_loglevel()))
		self.set_logdir(defaults.get_logdir())
		self.set_logfile()
		if not FAM.exists(self.get("log","file")) :
			FAM.createfile(self.get("log","file"))

		# report settings
		self.__clear_report_section()
		# LP Bug #153605
# TODO: we should not set a default 'from' since the value is not usable
# for 99% of the users (despite LP Bug #153605)
		self.set("report", "from", defaults.get_report_smtpfrom())
		
		# remaining administrative settings
		self.set("general", "mountdir", defaults.get_mountdir())
		self.set("general", "lockfile", defaults.get_lockfile())
		self.set("places", "prefix", defaults.get_prefix())
				
	def set_target_to_default(self):
		"""The destination (target) option is set to the default value
		valid for the current user.
		"""
		self.set("general", "target", self.get_target_default())
		
	def get_target_default(self):
		"""Wrapper method that return the default target path for
		the current user. No values of this configuration (actually
		configuration manager) are touched. 
		"""
		defaults = self.__get_default_config_obj()
		target = defaults.get_target()
		return target
				
	def optionxform(self, option):
		"""Default behaviour of ConfigParser is to set the option
		keys to lowercase. By overiding this method, we make it
		case sensitive. that's really important for dirconfig paths. 
		"""
		return str(option)

	def has_option(self, section, option):
		"""Checks this configuration for a given option comprising of
		section name and option name.
		
		@rtype: Boolean
		"""
		if section == "dirconfig" and \
				not ConfigParser.ConfigParser.has_option(self,section, option):
			if option == "remote" :
				return ConfigParser.ConfigParser.has_option(self, section,
															option)
			#search through remote option to get the option
			if ConfigParser.ConfigParser.has_option(self, "dirconfig",
															'remote'):
				remotes = self.get("dirconfig", "remote")
				if type(remotes) == str :
					remotes = eval(remotes)
				if type(remotes) != dict :
					raise SBException(_("Couldn't evaluate '%(parameter)s' as "\
							"a dictionary (value got = '%(value)r' )") \
							% {'parameter': remotes,'value': type(remotes)})
				if not remotes.has_key(option) :
					# then it wasn't for us , fall back on the parent
					return ConfigParser.ConfigParser.has_option(self, section,
																option)
				else :
					# we have this key
					return True
			else : 
				return ConfigParser.ConfigParser.has_option(self, section,
															option)
		else :
			#fall back in parent behaviour
			return ConfigParser.ConfigParser.has_option(self, section, option)
		
	def get(self, section, option):
		"""Returns a given option value from this config.
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
		"""Set an option just like a configParser but in case of
		the 'remote' option in 'dirconfig'. In this case, value
		must be a dict with the value you want to set, e.g.
		value = {'ssh://test/': 1, 'ssh://test/test': 0}
		You can set one at a time, the value will be append to
		the 'remote' dict.
		"""
		if section == "dirconfig" and option == "remote" :
			if type(value) != dict :
				raise SBException(_("You must provide a dictionary."))
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
		"""Remove an option, but it's different for remote.
		If option = "remote" then the whole remote option will be removed.
		If option is in remote dict, section ='dirconfig' and
		option='ssh://test/me' then the entry in the remote dict will be removed.
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
			
	def __clear_dirconfig(self):
		"""The internal variable containing the directory configuration
		(i.e. what directories are being included resp. excluded) is
		cleared. The according config section remains but is empty then.
		"""
		_section = "dirconfig"
		self.__dirconfig.clear()
		if self.has_section(_section):
			self.remove_section(_section)
		if not self.has_section(_section):
			self.add_section(_section)

	def __set_dirconfig(self, dirconf):
		"""The configuration item 'dirconfig' (Directory configuration) is
		set to the value of the given dictionary. Previous values are
		overwritten.
		
		@param dirconf:  new value
	
		@type dirconf:	  Dictionary
		
		@return: None
		
		@raise TypeError: If the given parameter is not of dictionary type

		"""
		_section = "dirconfig"
		if not isinstance(dirconf, types.DictionaryType):
			raise TypeError("Given parameter must be a Dictionary. "\
						    "Got %s instead." % (type(dirconf)))
		
		self.__clear_dirconfig()
		self.__dirconfig.update(dirconf)
		for a, b in self.__dirconfig.iteritems() :
			self.set(_section, a, b)
			
	def __set_regex_excludes(self, aregex):
		"""Helper method that sets the excludes defined by Regular
		Expressions.
		"""
		_section = "exclude"
		_option = "regex"
		if not isinstance(aregex, types.StringTypes):
			raise TypeError("Given parameter must be of string type. "\
						    "Got %s instead." % (type(aregex)))
		self.set(_section, _option, aregex)

	def setValidOpts(self, valid_options, parse_cmdline = False):
		self.valid_options = valid_options
		if parse_cmdline :
			self.__parseCmdLine()

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
			raise SBException(_("The config file '%s' couldn't be read!")\
								% self.conffile )
		return retValue

	def __parseCmdLine(self):
		"""
		@todo: Remove this from the ConfigurationManager. A better place
				for command line parsing is	the application class which
				in turn gives the parameters to the objects it creates.
		"""
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
		self.logger.debug("Validating config file.")
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
	
	def setSchedule(self, isCron, value):
		"""Set the backup Schedule.
		
		@param isCron : 0 for Anacron use , 1 for Cron use
		@param value : a string containing the value to set for Cron/Anacron. \
						Valid values for Anacron are: \
							daily/monthly/hourly/weekly
						Valid values for Cron:
							cronline to add at /etc/cron.d/nssbackup.
							
		"""
		anacronValues = ["daily","monthly","hourly","weekly"]
		if type(isCron) != int or not (isCron in [0,1]) : 
			raise NonValidOptionException("isCron must be 0 or 1")
		if isCron == 0 :
			# an Anacron entry was given (simple scheduling)
			if value not in anacronValues :
				raise NonValidOptionException("Valid values for anacron are: "\
						"%s, got '%s' instead." % (str(anacronValues), value))
			else :
				if self.has_option("schedule", "cron"):
# in some cases a logger is not yet available
#					self.logger.debug("Removing Cron config to set Anacron config.")
					self.remove_option("schedule", "cron")
#				self.logger.debug("Setting Anacron config to: %s" % value)
				self.set("schedule", "anacron", value)
		elif isCron == 1:
			# a Cron entry was given (precise scheduling)
			if self.has_option("schedule", "anacron"):
#				self.logger.debug("Removing Anacron config to set Cron config.")
				self.remove_option("schedule", "anacron")
#			self.logger.debug("Setting cron config to: %s" % value)
			self.set("schedule", "cron", value)
	
	def get_schedule_and_probe(self):
		"""Retrieves the current schedule state from configuration settings
		and from filesystem.

		@return: (isCron, value) a tuple where isCron = 0 if Anacron is used \
				 and isCron = 1 Cron is used. If no schedule setup has been \
				 found, 'None' is returned.
				 
		"""
		_value = None
		if not self.has_section("schedule") \
				or (not self.has_option("schedule", "cron") \
				and not self.has_option("schedule", "anacron")):
			
			# no entry in configuration found, look at Cron/Anacron directly
			self.logger.warning("Config file doesn't have schedule infos, "\
								"probing from filesystem.")
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
				_value = FAM.readfile("/etc/cron.d/nssbackup")
				self.logger.debug("Custom Cron has been found: %s" % _value)
				return (1, _value)
			# none has been found
			return None
		
		else:
			# scheduling is stored in configuration file
			if self.has_option("schedule", "cron"):
				_value = self.get("schedule", "cron")
				self.logger.debug("Schedule type Cron found in Config: %s" % _value)
				return (1, _value)
			elif self.has_option("schedule", "anacron"):
				_value = self.get("schedule", "anacron")
				self.logger.debug("Schedule type Anacron found in Config: %s" % _value)
				return (0, _value)
			else:
				return None
			
	def get_schedule(self):
		"""Returns the scheduling information that are currently
		set in this configuration regardless of filesystem state.
		"""
		# scheduling is stored in configuration file
		ret_val = None
		if self.has_option("schedule", "cron"):
			_value = self.get("schedule", "cron")
			self.logger.debug("Schedule type Cron found in Config: %s" % _value)
			ret_val = (1, _value)
		elif self.has_option("schedule", "anacron"):
			_value = self.get("schedule", "anacron")
			self.logger.debug("Schedule type Anacron found in Config: %s" % _value)
			ret_val = (0, _value)
		else:
			ret_val = None	
		return ret_val
	
	def remove_schedule(self):
		"""Removes all options stored in section 'schedule'. The section
		itself remains. Existing entries in crontab etc. are not touched.
		
		@return: Flag, whether something was removed or not. True is returned
					in the case that any schedule information was found by
					'getSchedule'.
					
		The return of this flag is somewhat a hack to force the GUI to enable
		the Save button for the rare case that:
		* the user wants to remove the schedule (i.e. sets it to 'Never')
		* no schedule information is stored in the configuration file
		* a script is linked in Anacron directories or in 'etc/cron.d/' which
		  is found when probing the filesystem for schedules.		  
		  
		"""
		_something_removed = False
		if self.get_schedule_and_probe() is not None:
			_something_removed = True
			for _option in self.options("schedule"):
				self.logger.debug("Removing ('schedule','%s') "\
								"from configuration." % _option)
				self.remove_option("schedule", _option)			
		return _something_removed

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
		self.__profileName = get_profilename(self.conffile)
		return self.__profileName
	
	def is_default_profile(self):
		"""Checks whether this configuration is the default configuration
		(i.e. default profile).
		
		@return: True if this is the default profile, False otherwise.
		
		"""
		if not self.conffile: 
			raise SBException(_("The config file is not set yet into this "\
							    "ConfigManager"))
		is_default = is_default_profile(self.conffile)
		return is_default
		
	def getProfiles(self):
		"""Returns the list of defined backup profiles. Both, active and
		disabled profiles are retrieved.
		 
		@return: a dictionary of {profilename: [path_to_conffile, enabled]} 
		
		"""
		prfDir = getUserConfDir()+"nssbackup.d/"
		
		self.logger.debug("Getting profiles from '%s'" % prfDir)
		_prfls = get_profiles(prfDir)
		# debug output of found profiles
		for _prfk in _prfls.keys():
			self.logger.debug("Found profile '%s' (active = %s)" % (_prfk,
															_prfls[_prfk][1]))
		# end of debug output
		return _prfls
	
	def set_logdir(self, logdir):
		"""Sets the given directory as current log directory for use with
		log files.		
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
		logfname = get_logfile_name(self.conffile)
		logf = os.path.join(self.__logfile_dir, logfname)
		return logf
		
	def __clear_report_section(self):
		"""Any options present in the report section are removed. The section
		itself is not removed. 
		"""
		_section = "report"
		self.remove_section(_section)
		if not self.has_section(_section):
			self.add_section(_section)
		
	def saveConf(self,configfile = None):
		"""Saves the configuration (i.e. writes it into the specified file
		and sets scheduling in the case this is the default profile).
		 
		@param configfile: The config file in which to write the configuration.
							Default is in the default location
							 
		@todo: What happens if the config file is 'Save as ...' in order to
				store a configuration aside but the scheduling is different
				from the *original* configuration that is used by nssbackupd?
		"""
		if configfile:
			fld = FAM.openfile(configfile, True)
		else :
			fld = FAM.openfile(self.conffile, True)
		self.write(fld)
		fld.close()		
		self.__write_schedule()
	
	def __write_schedule(self):
		"""Write the schedule from the configuration file. Scheduling is only
		written for admin default profiles.
		
		"""
		if os.geteuid() != 0 :
			self.logger.warning("Not implemented for non root users yet.")
			return
		
		if self.is_default_profile():
			self.__erase_services()
			
			if not self.has_section("schedule") \
					or (not self.has_option("schedule", "anacron") and not self.has_option("schedule", "cron")) :
				return
			
			else:
				if self.has_option("schedule", "cron") :
					self.logger.debug("Saving Cron entries")
					execline = "if [ -x '"+Util.getResource("nssbackup")+"' ]; then "+Util.getResource("nssbackup")+"; fi;"
					FAM.writetofile("/etc/cron.d/nssbackup",
							ConfigManagerStaticData.get_cronheader() + self.get("schedule", "cron") + "\troot\t"+ execline)
					
				if self.has_option("schedule", "anacron") :
					self.logger.debug("Saving Anacron entries")
					if self.get("schedule", "anacron") == "hourly" :
						os.symlink(self.__servicefile,"/etc/cron.hourly/nssbackup")
					elif self.get("schedule", "anacron") == "daily" :
						os.symlink(self.__servicefile,"/etc/cron.daily/nssbackup")
					elif self.get("schedule", "anacron") == "weekly" :
						os.symlink(self.__servicefile,"/etc/cron.weekly/nssbackup")
					elif self.get("schedule", "anacron") == "monthly" :
						os.symlink(self.__servicefile,"/etc/cron.monthly/nssbackup")
					else : 
						self.logger.warning("'%s' is not a valid value" \
											% self.get("schedule", "anacron"))
					return
		else:
			self.logger.warning("Not implemented for non-default profiles yet.")
			return
			
	def __erase_services(self):
		"""Removes Cron and Anacron service from /etc/cron.*
		 
		"""
		listserv = ["/etc/cron.hourly/nssbackup",
					"/etc/cron.daily/nssbackup",
					"/etc/cron.weekly/nssbackup",
					"/etc/cron.monthly/nssbackup",
					"/etc/cron.d/nssbackup"]
		for serv in listserv:
			if os.path.exists(serv):
				self.logger.debug("Unlinking '%s'" % serv )
				os.unlink(serv)
	
	def testMail(self):
		"""Test the mail settings
		
		@return: True if succeded
		@raise SBException: the error message why it didn't run
		
		@todo: Not the right place for this kind of functionality?!?
		
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
		"""Compares this configuration and the given configuration.

		@param config : a configManager instance
		@return: True if the config are equals, False otherwise
		@rtype: boolean
		
		"""
		if not (isinstance(config, ConfigManager) or config is None):
			raise SBException("Can't compare a ConfigManager with type '%s'"\
							% str(type(config)))
		if config is None:
			return False
		
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
		
		
class ConfigManagerStaticData(object):
	"""Any static data related to configurations are stored here.
	
	@todo: Refactor this class into a class containing a default
			configuration, one containing name definitions, and one
			containing path and file names.
	
	"""	
	__cronheader = "SHELL=/bin/bash \n"\
		"PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n\n"

	__default_profilename = _("Default Profile")
	__unknown_profilename = _("Unknown Profile")
	
	# these variables should be read-only
	__logfile_basename 	= "nssbackup"
	__logfile_ext		= "log"

	__superuser_confdir = "/etc"
	__user_confdir_template = ".config/nssbackup"
	__default_config_file = "nssbackup.conf"

	__profiles_dir = "nssbackup.d"
	
	__profilename_re = re.compile('^nssbackup-(.+?).conf(-disable)?$')
	
	# configuration's existing sections and options
	__our_options = {
	 'general' 		: { 'mountdir'		: str,
				        'target'  		: str ,
				   		'lockfile' 		: str ,
				   		'maxincrement' 	: int ,
				   		'format' 		: str,
				   		'splitsize' 	: int,
				   		'purge' 		: str,
				   		'run4others' 	: int,
				   		'followlinks' 	: int,
						'packagecmd'	: str},
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
	
	__loglevels = {	'10' : ("Debug",	0),
					'20' : ("Info",		1),
					'30' : ("Warning",	2),
					'40' : ("Error",	3)}
	
	__simple_schedule_freqs = 	{	"hourly"	: 0,
									"daily"		: 1,
									"weekly"	: 2,
									"monthly"	: 3
								}
	
	__cformats = ['none', 'gzip', 'bzip2']
	
	__splitsize =	{	0		: _('Unlimited'),
						100		: _('100 MiB'),
						250		: _('250 MiB'),
						650 	: _('650 MiB'),
						2048 	: _('2 GiB (FAT16)'),
						4096	: _('4 GiB (FAT32)'),
						-1		: _('Custom')
					}
	__known_ftypes =	{	"mp3"	: _("MP3 Music"),
							"avi"	: _("AVI Video"),
							"mpeg"	: _("MPEG Video"),
							"mpg"	: _("MPEG Video"),
							"mkv"	: _("Matrjoshka Video"),
							"ogg"	: _("OGG Multimedia container"),
							"iso"	: _("CD Images")
						}

	def __init__(self):
		pass
	
	@classmethod
	def get_simple_schedule_frequencies(cls):
		"""Returns a dictionary of schedule frequencies and IDs.
		"""
		return cls.__simple_schedule_freqs

	@classmethod
	def get_cronheader(cls):
		"""Returns the static cron header.
		"""
		return cls.__cronheader
		
	@classmethod
	def get_default_logfile(cls):
		"""Returns the name of the logfile for the default profile.		
		"""
		logfname = "%s.%s" % (cls.__logfile_basename,
							  cls.__logfile_ext)
		return logfname

	@classmethod
	def get_valid_loglevels(cls):
		"""Returns a dictionary of valid log levels (a number) and
		corresponding log level name.
		"""
		return cls.__loglevels
	
	@classmethod
	def get_profile_logfile(cls, profilename):
		"""Returns the name of the logfile for a certain profile
		named `profilename`.		
		"""
		logfname = "%s-%s.%s" % (cls.__logfile_basename,
								 profilename,
								 cls.__logfile_ext)
		return logfname

	@classmethod
	def get_profiles_dir(cls):
		"""Returns the name (only basename, no path) of the directory where
		profile configurations are stored.		
		"""
		return cls.__profiles_dir

	@classmethod
	def get_profilename_re(cls):
		return cls.__profilename_re

	@classmethod		
	def get_default_profilename(cls):
		return cls.__default_profilename

	@classmethod		
	def get_unknown_profilename(cls):
		return cls.__unknown_profilename
	
	@classmethod
	def get_superuser_confdir(cls):
		return cls.__superuser_confdir
			
	@classmethod
	def get_user_confdir_template(cls):
		return cls.__user_confdir_template

	@classmethod		
	def get_default_conffile(cls):
		return cls.__default_config_file
	
	@classmethod		
	def get_our_options(cls):
		return cls.__our_options
	
	@classmethod
	def get_splitsize_dict(cls):
		return cls.__splitsize
	
	@classmethod
	def get_known_ftypes_dict(cls):
		return cls.__known_ftypes

	@classmethod
	def get_compr_formats(cls):
		return cls.__cformats

class Configuration(object):
	"""Encapsulates a configuration, that is a set of backup profile related
	settings.

	Configuration values are stored in their natural type and format instead
	of the type and format that is used for storage of the configuration
	(i.e. Boolean values get the value True/False, not '0/1' or 'yes/no').
	The transformation of the actual configuration values to data that is
	written to disk is done in the ConfigManager.
	
	@note: This is an early attempt to refactor the configuration thing:
			* there are objects that represent the actual profile settings
			* there are certain global preferences that are valid for
				each profile (e.g. prefix, mountdir, etc.)
			* there is a Manager class that is responsible for handling
				of several profile configurations
			* there is an object that forms an interface between the actual
				configuration and their storage on disk, reading, evaluating
				and so on (probably derived from ConfigParser)
	"""
	
	def __init__(self):
		self._maxinc = 0
		self._cformat = ""
		self._follow_links = False
		self._splitsize = 0
		
		self._dirconf = {}
		self._regex_excludes = ""
		self._max_filesize = 0

		self._purge = ""
		self._target = ""

		# administrative settings
		self._mountdir = ""
		self._lockfile = ""
		self._prefix = ""
		
		self._logdir = ""
		self._loglevel = 0
		
# TODO: Collect report related settings in separate class.
		self._report_smtpfrom = ""
		
		self._schedule = [False, ""]	# isCron = False, frequency = ""

	# access methods
	def get_report_smtpfrom(self):
		return self._report_smtpfrom
		
	def get_schedule(self):
		return self._schedule
	
	def get_regex_excludes(self):
		return self._regex_excludes
	
	def get_max_filesize(self):
		return self._max_filesize
	
	def get_max_increment(self):
		return self._maxinc
	
	def get_compress_format(self):
		return self._cformat
	
	def get_follow_links(self):
		if not isinstance(self._follow_links, types.BooleanType):
			raise TypeError("Boolean value for 'followlinks' expected. "\
							"Found '%s' instead." % type(self._follow_links))
		return self._follow_links
	
	def get_split_size(self):
		return self._splitsize
	
	def get_dir_config(self):
		return self._dirconf
	
	def get_mountdir(self):
		return self._mountdir
	
	def get_purge(self):
		return self._purge
	
	def get_target(self):
		return self._target
	
	def get_lockfile(self):
		return self._lockfile
	
	def get_prefix(self):
		return self._prefix
	
	def get_logdir(self):
		return self._logdir
	
	def get_loglevel(self):
		return self._loglevel
	

class _DefaultConfiguration(Configuration):
	"""Abstract base class for a default configuration. A default
	configuration is basically a configuration however the settings
	are predefined (and read-only in the best case).
	
	@todo: Change this: the default configuration should not be a derived
			class rather an instance of a regular configuration which gets
			its content from a default config file (in share). Doing so,
			would be more flexible? What is with /home/$username?
	
	"""
	
	def __init__(self):
#		super(DefaultConfiguration, self).__init__() # don't use this form
		Configuration.__init__(self)
		
		self._regex_excludes = "\.mp3,\.avi,\.mpeg,\.mkv,\.ogg,\.iso,"\
		                   "/home/[^/]+?/\.thumbnails/,/home/[^/]+?/\.Trash,"\
		                   "/home/[^/]+?/\..+/[cC]ache"

		self._maxinc = 7
		self._cformat = 'gzip'
		self._follow_links = False
		self._splitsize = 0
		self._max_filesize = 104857600		# in bytes = 100 MB * 1024 * 1024

		self._loglevel = 20
		self._report_smtpfrom = Infos.SMTPFROM
		
		self._prefix = '/usr'		
		self._purge = "30"
		

class _DefaultConfigurationForAdmins(_DefaultConfiguration):
	"""Derived default configuration that specializes it for
	privileged users. Only settings that are unique for
	admins are defined here.
	
	@todo: Change this: the default configuration should not be a derived
			class rather an instance of a regular configuration which gets
			its content from a default config file (in share). Doing so,
			would be more flexible? What is with /home/$username?
	
	"""
	
	def __init__(self):
		_DefaultConfiguration.__init__(self)
				
		self._mountdir = "/mnt/nssbackup"
		self._target = "/var/backup"
		self._lockfile = "/var/lock/nssbackup.lock"

		self._dirconf = { '/etc/'			: '1',
							'/var/'			: '1',
							'/home/'		: '1',
							'/var/cache/'	: '0',
							'/var/tmp/'		: '0',
							'/var/spool/'	: '0',
							'/usr/local/'	: '1',
							'/media/'		: '0' }
		
		self._logdir = "/var/log"
		
		self._schedule = [False, "daily"]


class _DefaultConfigurationForUsers(_DefaultConfiguration):
	"""Derived default configuration that specializes it for
	normal users. Only settings that are unique for normal users
	are defined here.
	
	@todo: Change this: the default configuration should not be a derived
			class rather an instance of a regular configuration which gets
			its content from a default config file (in share). Doing so,
			would be more flexible? What is with /home/$username?
	
	"""
	
	def __init__(self):
		_DefaultConfiguration.__init__(self)

		self._mountdir = os.path.join(getUserDatasDir(), "mountdir")
		self._target = os.path.join(getUserDatasDir(), "backups")
		self._lockfile = os.path.join(getUserDatasDir(), "nssbackup.lock")
				
		self._dirconf = {	os.getenv("HOME")+os.sep		: '1' }
		
		self._logdir = getUserDatasDir()

		self._schedule = [False, ""]	# no scheduling
