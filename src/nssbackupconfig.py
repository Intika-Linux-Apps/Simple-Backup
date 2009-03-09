#! /usr/bin/env python

#	NSsbackup - helper script for upgrading nssbackup
#
#   Copyright (c)2009: Jean-Peer Lorenz <peer.loz@gmx.net>
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
:mod:`nssbackupupgrade` --- helper script for upgrading nssbackup
==================================================================

.. module:: nssbackupupgrade
   :synopsis: helper script for upgrading nssbackup from older versions
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

This script provides necessary functionality when upgrading NSsbackup
to a new version. Purpose of this script is to be run from the Debian
`postinst` script after package update.

"""

import sys
import traceback
import os
import os.path
import pwd
import ConfigParser
import re

import nssbackup
from nssbackup.managers import ConfigManager 

# definition of error codes
NO_ERRORS = 0
NO_SUPERUSER = 1
UNKNOWN_ERROR = 9


class UpgradeLogOption(object):
	"""This class encapsulates the upgrading of the log options due
	to changes in log file naming in release 0.2.0-RC3. In prior
	releases the log file was named `nssbackup.log`. With release
	0.2.0-RC3 this has changed. From now the log file for the default
	profile is named `nssbackup.log` and log files for any other
	profiles are named `nssbackup-profilename.log`. This was
	neccessary due to problems with identical names of log files.
	
	"""
	
	class _Settings(object):
		"""Class containing constants for upgrading the log option.
		
		These constants cover
		- `__logindefs`: path to file ``login.defs``
		- `__uidmin_name`: name of entry for minimal uid
		- `__uidmax_name`: name of entry for maximal uid
		
		The constants are accessable using the defined classmethods.
		 
		"""
		__logindefs = "/etc/login.defs"
		__uidmin_name = "UID_MIN"
		__uidmax_name = "UID_MAX"
		
		def __init__(self):
			pass
			
		@classmethod
		def get_logindefs_path(cls):
			"""Returns the path to the file `login.defs`.
			
			"""
			return cls.__logindefs
	
		@classmethod
		def get_uidmin_name(cls):
			"""Returns the name of the entry for minimal uid.
			
			"""
			return cls.__uidmin_name
			
		@classmethod
		def get_uidmax_name(cls):
			"""Returns the name of the entry for maximal uid.
			
			"""
			return cls.__uidmax_name
	
	
	class _Config(ConfigParser.ConfigParser):
		"""A customized ConfigParser for reading and writing of NSsbackup
		configuration files.
		
		"""
		def __init__(self, configfile):
			"""Default constructor. Reads the given file into this
			parser.
			
			:param configfile: Full path to the current configuration file
			
			"""
			ConfigParser.ConfigParser.__init__(self)
			self._configfile = configfile
			try:
				fobj = file(self._configfile, "r")
			except IOError:
				print "Unable to open `%s` for reading." % str(self._configfile)
			else:
				self.readfp(fobj, self._configfile)
				fobj.close()
			
		def commit_to_disk(self):
			"""Writes the current configuration set to the disk. The
			configuration file given to the constructor is used.
			
			"""
			try:
				fobj = file(self._configfile, "wb")
			except IOError:
				print "Unable to open `%s` for writing." % str(self._configfile)
			else:
				ConfigParser.ConfigParser.write(self, fobj)
				fobj.close()
	
	
	def __init__(self):
		"""Constructor of the log option upgrader.
		
		"""
		self.__min_uid = 1000
		self.__max_uid = 60000
		self.__users = []
		self.__configdirs = []
		
		reexp_templ = "^%s[ \t]+(\d+)$"
		self.__reexp_min_uid = re.compile(reexp_templ
										   % self._Settings.get_uidmin_name(),
										   re.IGNORECASE)
		self.__reexp_max_uid = re.compile(reexp_templ
										   % self._Settings.get_uidmax_name(),
										   re.IGNORECASE)
		
	def __repr__(self):
		_repr = ["min uid: %s" % self.__min_uid,
		   		"max uid: %s" % self.__max_uid,
		 		"users: %s" % self.__users,
		 		"config dirs: %s" % self.__configdirs
			   ]
		return "\n".join(_repr)
		
	def _read_logindefs(self):
		"""Reads the lower and upper limit for user ids from
		the `login.defs` file.
		
		"""
		defspath = self._Settings.get_logindefs_path()
		if os.path.isfile(defspath) and os.access(defspath, os.F_OK and os.R_OK):
			eof = False
			try:
				defsfile = file(defspath, "r")
				while not eof:
					defsline = defsfile.readline()
					if defsline == "":
						eof = True
					else:
						defsline = defsline.strip()
						match = self.__reexp_min_uid.search(defsline)
						if match is not None:
						    self.__min_uid = int(match.group(1))
						    
						match = self.__reexp_max_uid.search(defsline)
						if match is not None:
						    self.__max_uid = int(match.group(1))
			except IOError:
				print "Error while reading definitions from '%s'. "\
					  "Using defaults." % (defspath)
			else:
				defsfile.close()
		else:
			print "Unable to read definitions from '%s'. "\
				  "Using defaults." % (defspath)
		
	def _retrieve_users(self):
		"""Retrieves all users from the password database that are
		apparently not system services (using the `uid_min` and
		`uid_max` for this). 
		
		"""
		self.__users = []
		allpw = pwd.getpwall()
		for cpw in allpw:
			try:
				uid = cpw.pw_uid
			except KeyError:
				continue
			if uid >= self.__min_uid and uid <= self.__max_uid:
				self.__users.append(cpw)
				
	def _make_configdir_list(self):
		"""Creates a list containing all basic configuration directories
		of the previously retrieved users. This includes in any case the
		default configuration directory `/etc`.
		
		:note: It is assumed that user configurations are stored in a\
			   directory like `~/.config/nssbackup`.
		
		:todo: Implement a better way for retrieval of user's confdirs e.g.\
		       by reading the users environ!
		       
		"""
		self.__configdirs = []
		# for the superuser
		self.__configdirs.append(ConfigManager.\
								 ConfigStaticData.get_superuser_confdir())
		
		# for the other users
		for user in self.__users:
			try:
				wdir = user.pw_dir
			except KeyError:
				continue
			wdir = os.path.join(wdir,
					ConfigManager.ConfigStaticData.get_user_confdir_template())
			self.__configdirs.append(wdir)	 
		
	def _modify_default_profile(self):
		"""Modifies the configuration file for the default profile.
		
		"""
		for cdir in self.__configdirs:
			cfile = os.path.join(cdir,
						ConfigManager.ConfigStaticData.get_default_conffile())
			self._modify_configfile(cfile)
			
	def _modify_other_profiles(self):
		"""Modifies the configuration files for the other profiles.
		
		"""
		for cdir in self.__configdirs:
			pdir = os.path.join(cdir,
							ConfigManager.ConfigStaticData.get_profiles_dir())
			# get the profile directory for current configuration directory
			if os.path.isdir(pdir) and\
			   os.access(pdir, os.F_OK and os.R_OK and os.W_OK):
				# and get the profiles from the profiles directory
				profiles = ConfigManager.get_profiles(pdir)
				for cprof in profiles:
					cconf = profiles[cprof][0]
					self._modify_configfile(cconf)
			
	def _modify_configfile(self, conffile):
		"""This method modifies a single configuration file, i.e.
		
		* it reads the existing value from the file
		* retrieves the new value under consideration of the profile name
		* writes the new value to the configuration file.
		
		Files that are not readable/writable are skipped.
		
		"""
		if os.path.isfile(conffile) and\
		   os.access(conffile, os.F_OK and os.R_OK and os.W_OK):
			print "checking file: %s" % conffile
			config = self._Config(conffile)			
			if config.has_section("log"):
				if config.has_option("log", "file"):
					logfile = config.get("log", "file")			   
					logdir = os.path.dirname(logfile)
					
					new_logfn = ConfigManager.get_logfile_name(conffile)
					new_log = os.path.join(logdir, new_logfn)
					
					if logfile == new_log:
						print "   nothing to do. skipped"
					else:
						print "   changing log file option"
						print "   from `%s`" % (logfile)
						print "   to   `%s`" % (new_log)						
						config.set("log", "file", str(new_log))
						config.commit_to_disk()
	
	def do_upgrade(self):
		"""Public method that actually processes the upgrade
		consisting of the following steps:
		
		1. Reading the login defaults for determination of non-system users
		2. Retrieve all users on the system
		3. Make a list of all configuration directories for these users
		4. modify the default profile configuration file
		5. modify the configuration files for any other profiles.
		
		An appropriate error code is returned.
		
		"""
		self._read_logindefs()
		self._retrieve_users()
		self._make_configdir_list()
		
		self._modify_default_profile()
		self._modify_other_profiles()

		retcode = NO_ERRORS		
		return retcode


class UpgradeApplication(object):
	"""The upgrade application class that instantiates several upgrade
	action classes and processes them. Due to this design one can simply
	add and execute further upgrade actions. 
	
	"""
	def __init__(self):
		"""Default constructor. Creates an `UpgradeLogOption` object.
		
		"""
		self.__logoption_upgrader = UpgradeLogOption()
	
	def main(self):
		"""Main method that actually does the upgrade process. It returns
		an appropriate error code. 
		
		"""
		print "-"*60
		print "NSsbackup %s upgrade tool" % nssbackup.Infos.VERSION
		print "-"*60
		
		if os.getuid() != 0:
			print "Upgrade script must be run with root privileges!"
			retcode = NO_SUPERUSER
		else:
			retcode = self.__logoption_upgrader.do_upgrade()
		
		return retcode


if __name__ == "__main__":
	try:
		_UPGRADER = UpgradeApplication()
		RETC = _UPGRADER.main()
	except:
		print "errors occurred:"
		traceback.print_exc()
		RETC = UNKNOWN_ERROR

	if RETC == NO_ERRORS:
		print "successful finished."
		
	sys.exit(RETC)
