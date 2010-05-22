#	NSsbackup - the actual backup service
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
:mod:`nssbackupd` --- the actual backup service
================================================

.. module:: nssbackupd
   :synopsis: Defines the actual backup service
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

import os
import os.path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import socket
import datetime
import re
from gettext import gettext as _

# project imports
from nssbackup.pkginfo import Infos
from nssbackup.util import log
from nssbackup.util import exceptions
import nssbackup.managers.FileAccessManager as FAM
from nssbackup.managers.ConfigManager import getUserConfDir
from nssbackup.managers.ConfigManager import ConfigManager
from nssbackup.managers.BackupManager import BackupManager
from nssbackup.managers.BackupManager import PyNotifyMixin


class NSsbackupd(PyNotifyMixin) :
	"""This class is intended to be a wrapper of nssbackup instances. 
	It manages :
	- the full backup process : creation of instances of the BackupManager
	  with the corresponding config file 
	- the logging of exception not handled by BackupManager
	- the removal of lockfiles
	- the sending of emails
	
	"""
	
	__confFilesRE = "^nssbackup-(.+?)\.conf$"

	def __init__(self):
		"""Default constructor. Basic initializations are done here.

		:note: Retrieve the configuration manager very early to ensure that 
			   an appropriate logger instances are created.
		
		"""
		self.__errors			= []
		self.__super_user		= False
		self.__check_for_superuser()
				
		# collection of all config managers
		self.__confm			= []
		# the name of the currently processed profile
		self.__profileName		= None
		self.__retrieve_confm()

		# here the logger created for the default profile is used
		self.logger			= log.LogFactory.getLogger(self.__profileName)
		self.logger.debug("%s %s" % (Infos.NAME, Infos.VERSION))

		# the currently used instance of the BackupManager
		self.__bm				= None

		PyNotifyMixin.__init__(self, self.logger)

	def __check_for_superuser(self):
		"""Checks whether the application was invoked with super-user rights.
		If so, the member variable 'self.__super_user' is set.
		"""
		if os.getuid() == 0:
			self.__super_user = True
		
	def __sendEmail(self):
		"""Checks if the sent of emails is set in the config file 
		then send an email with the report
		"""
		if self.__bm.config.has_option("report","from") :
			_from =self.__bm.config.get("report","from")
		else :
			hostname = socket.gethostname()
			if "." in hostname :
				mailsuffix = hostname
			else :
				mailsuffix = hostname + ".ext"
			_from = _("NSsbackup Daemon <%(login)s@%(hostname)s>")\
					% {'login' : os.getenv("USERNAME"), 'hostname': mailsuffix}
		
		_to = self.__bm.config.get("report","to")
		_title = _("[NSsbackup] [%(profile)s] Report of %(date)s")\
					% { 'profile':self.__profileName,
					    'date': datetime.datetime.now() }
		logf = self.__bm.config.get_current_logfile()
		if logf is None:
			_content = _("No log file specified.")
		else:
			if FAM.exists( logf ):
				_content = FAM.readfile( logf )
			else :
				_content = _("Unable to find log file.")
		
		server = smtplib.SMTP()
		msg = MIMEMultipart()
		
		msg['Subject'] = _title
		msg['From'] = _from
		msg['To'] = _to
		msg.preamble = _title
		
		msg_content = MIMEText(_content)
		# Set the filename parameter
		msg_content.add_header('Content-Disposition', 'attachment',
							   filename="nssbackup.log")
		msg.attach(msg_content)
		
		# getting the connection
		if self.__bm.config.has_option("report","smtpserver") :
			if self.__bm.config.has_option("report","smtpport") :
				server.connect(self.__bm.config.get("report","smtpserver"),
							   self.__bm.config.get("report","smtpport"))
			else : 
				server.connect(self.__bm.config.get("report","smtpserver"))
		if self.__bm.config.has_option("report","smtptls") and\
					self.__bm.config.get("report","smtptls") == 1 : 
			if self.__bm.config.has_option("report","smtpcert") and\
					self.__bm.config.has_option("report","smtpkey") :
				server.starttls(self.__bm.config.get("report","smtpkey"),
							    self.__bm.config.get("report","smtpcert"))
			else :
				server.starttls()
		if self.__bm.config.has_option("report","smtpuser") and\
				self.__bm.config.has_option("report","smtppassword") : 
			server.login(self.__bm.config.get("report","smtpuser"),
						 self.__bm.config.get("report","smtppassword"))
		
		# send and close connection
		server.sendmail(_from, _to, msg.as_string())
		server.close()
	
	def __retrieve_confm(self):
		"""Factory method that retrieves the appropriate configuration managers
		for the existing profiles. Super-user rights are taken into account.
		The created configuration managers are stored in member variable
		'self.__confm'.
		"""
		self.__confm = []

		# default profile config file and the config directory is determined
		if self.__super_user:
			conffile = "/etc/nssbackup.conf"
			confdir  = "/etc/nssbackup.d"
		else:
			conffile = os.path.join( getUserConfDir(), "nssbackup.conf" )
			confdir  = os.path.join( getUserConfDir(), "nssbackup.d" )

		# create config manager for the default profile and set as current
		if os.path.exists( conffile ):
			confm = ConfigManager( conffile )
			self.__profileName = confm.getProfileName()
			# store the created ConfigManager in a collection
			self.__confm.append( confm )
		else:
			errmsg = _("Critical Error: No configuration file for the default profile was found!\n\nNow continue processing remaining profiles.")
			self.__errors.append(errmsg)

		# Now search for alternate configuration files
		# They are located in (configdir)/nssbackup.d/
		if os.path.exists(confdir) and os.path.isdir(confdir):
			cregex = re.compile(self.__confFilesRE)
			cfiles = os.listdir( confdir )
			for cfil in cfiles:
				cfil_fullpath = os.path.join( confdir, cfil )
				if os.path.isfile( cfil_fullpath ):
					mres = cregex.match( cfil )
					if mres:	# if filename matches, create manager and add it
						confm = ConfigManager( cfil_fullpath )
						self.__confm.append( confm )

	def run(self):
		"""Actual main method to make backups using NSsbackup
		
		- launch BackupManager with the user configuration file
		- catches all exceptions thrown and logs them (with stacktrace)
		"""
		self.__notify_init_errors()
		
		for confm in self.__confm:
			try:
				self.__profileName 	= confm.getProfileName()
				self.logger			= log.LogFactory.getLogger(self.__profileName)
				self.__bm 			= BackupManager( confm )
				self.__log_errlist()
				self.__bm.makeBackup()
				self.__bm.endSBsession()				
			except exceptions.InstanceRunningError, exc:
				self.__on_already_running(exc)
			except Exception, exc:
				self.__onError(exc)
				
			self.__onFinish()

	def __on_already_running(self, error):
		"""Handler for the case a backup process is already running.
		Fuse is not initialized yet.
		"""
		try:
			_msg = "Backup is not being started.\n%s" % (str(error))
			self.logger.warning(_msg)
			self._notify_warning(self.__profileName, _msg)
		except Exception, exc:
			self.logger.exception("Exception in error handling code:\n%s" % str(exc))

	def __onError(self, e):
		"""Handles errors that occurs during backup process.
		"""
		try:
			n_body = _("An error occured during the backup:\n%s") % (str(e))
			self.logger.exception(n_body)
			self._notify_error(self.__profileName, n_body)
			if self.__bm:
				self.__bm.endSBsession()
		except Exception, exc:
			self.logger.exception("Exception in error handling code:\n%s" % str(exc))
		
	def __onFinish(self):
		"""Method that is finally called after backup process.
		"""
		if self.__bm and self.__bm.config:
			# send the mail
			if self.__bm.config.has_section("report") and self.__bm.config.has_option("report","to") :
				self.__sendEmail()
				
	def __notify_init_errors(self):
		"""Errors that occurred during the initialization process were stored
		in an error list. This error list is showed to the user by this method.
		"""
		if len(self.__errors) > 0:
			for errmsg in self.__errors:
				self._notify_error(self.__profileName, errmsg)

	def __log_errlist(self):
		"""Errors that occurred during the initialization process were stored
		in an error list. This error list is added to the current log.
		"""
		if len(self.__errors) > 0:
			self.logger.info(_("The following error(s) occurred before:"))
			for errmsg in self.__errors:
				self.logger.error(errmsg.replace("\n", " "))
	
def main(argv):
	"""Public function that process the backups.
	"""
	sbd = NSsbackupd()
	sbd.run()
	log.shutdown_logging()
