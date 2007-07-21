#!/usr/bin/env python
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
import os
import traceback
import smtplib
import socket
import datetime
import gettext
from gettext import gettext as _
from nssbackup.util.log import getLogger
from nssbackup.util.exceptions import SBException
import nssbackup.managers.FileAccessManager as FAM
from nssbackup.managers.ConfigManager import ConfigManager, getUserConfDir
from nssbackup.managers.BackupManager import BackupManager

##
#This class is intended to be a wrapper of nssbackup instances . 
#It manages :
# - the full backup process : creation of instances of the BackupManager with the corresponding config file 
# - the logging of exception not handled by BackupManager
# - the removal of lockfiles
# - the sent of emails
#
# @author: Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>
# @version: 1.0
class NSsbackupd () :
	
	__bm = None

	##
	#Checks if the sent of emails is set in the config file 
	#then send an email with the 
	def __sendEmail(self):
		
		if self.__bm.config.has_option("report","from") :
			_from =self.__bm.config.get("report","from")
		else :
			_from = _("NSsbackup Daemon <%(login)s@%(hostname)s>") % {'login' : os.getlogin(), 'hostname': socket.gethostname()}
		
		_to = self.__bm.config.get("report","to")
		_title = _("[NSsbackup] Report of %(date)s") % {'date': datetime.datetime.now()}
		if self.__bm.config.has_option("log","file") :
			_content = FAM.readfile(self.__bm.config.get("log","file"))
		else :
			if FAM.exists("nssbackup.log") :
				_content = FAM.readfile("nssbackup.log")
			else :
				_content = _("I didn't find the log file. Please set it up in sbackup.conf ")
		
		server = smtplib.SMTP()
		
		# getting the connection
		if self.__bm.config.has_option("report","smtpserver") :
			if self.__bm.config.has_option("report","smtpport") :
				server.connect(self.__bm.config.get("report","smtpserver"), self.__bm.config.get("report","smtpport"))
			else : 
				server.connect(self.__bm.config.get("report","smtpserver"))
		if self.__bm.config.has_option("report","smtptls") and self.__bm.config.get("report","smtptls") == 1 : 
			if self.__bm.config.has_option("report","smtpcert") and self.__bm.config.has_option("report","smtpkey") :
				server.starttls(self.__bm.config.get("report","smtpkey"), self.__bm.config.get("report","smtpcert"))
			else :
				server.starttls()
		if self.__bm.config.has_option("report","smtpuser") and self.__bm.config.has_option("report","smtppassword") : 
			server.login(self.__bm.config.get("report","smtpuser"), self.__bm.config.get("report","smtppassword"))
		
		# send and close connection
		_subject = "SUBJECT : %s \r\n" % _title
		_header = "From : %s \r\nTo : %s \r\n" % (_from, _to)
		server.sendmail(_from, _to, _header+_subject+_content)
		server.close()
	
		
	##
	# Method used to run sbackupd
	# - checks for the user who called it
	# 	- if it's root, it makes a loop to run sbackup for all users that asked for it.
	# 	- if it's another user, launch BackupManager with the user configuration file
	# - catches all exceptions thrown and logs them (with stacktrace)
	#
	def run(self):

		global __bm
		
		try : 
			try :
				if os.getuid() == 0 : # we are root
					if os.path.exists("/etc/nssbackup.conf") :
						self.__bm = BackupManager("/etc/nssbackup.conf")
					else :
						self.__bm = BackupManager()
					# TODO Find other users if the option is specified
				else :  # we are others
					if os.path.exists(getUserConfDir()+ "nssbackup.conf") :
						self.__bm = BackupManager(getUserConfDir()+ "nssbackup.conf")
					else :
						self.__bm = BackupManager()
					
				# do the backup
				self.__bm.makeBackup()
				
			except Exception, e :
				if os.getuid() != 0 :
					try:
						import pynotify
						if pynotify.init("NSsbackup"):
							n = pynotify.Notification("NSsbackup", "CRASH : '%s'" % str(e))
							n.show()
						else:
							getLogger().warning(_("there was a problem initializing the pynotify module"))
					except Exception, e1:
						getLogger().warning(str(e1))
				getLogger().error(str(e))
				getLogger().error(traceback.format_exc())
				# remove any left lockfile
				if self.__bm and self.__bm.config.has_option("general","lockfile") and FAM.exists(self.__bm.config.get("general","lockfile")) :
					getLogger().info(_("Session of backup is finished (lockfile is removed) "))
					FAM.delete(self.__bm.config.get("general","lockfile"))
			finally :
				# send the mail
				if self.__bm.config.has_section("report") and self.__bm.config.has_option("report","to") :
					self.__sendEmail()
		except Exception, e :
			getLogger().error(str(e))
			getLogger().error(traceback.format_exc())

application = 'nssbackup'
gettext.install(application)
sbd = NSsbackupd()
sbd.run()