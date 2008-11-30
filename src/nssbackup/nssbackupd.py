
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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import socket
import datetime
import re
from gettext import gettext as _
from nssbackup.util.log import LogFactory
import nssbackup.managers.FileAccessManager as FAM
from nssbackup.managers.ConfigManager import getUserConfDir
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
	
	logger = LogFactory.getLogger()
	
	__confFilesRE = "^nssbackup-(.+?)\.conf$"

	def __init__(self):
		"""
		Initialisation
		"""
		self.__bm = None
		self.__profileName = None

	def __sendEmail(self):
		"""
		Checks if the sent of emails is set in the config file 
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
			_from = _("NSsbackup Daemon <%(login)s@%(hostname)s>") % {'login' : os.getenv("USERNAME"), 'hostname': mailsuffix}
		
		_to = self.__bm.config.get("report","to")
		_title = _("[NSsbackup] [%(profile)s] Report of %(date)s") % {'profile':self.__profileName, 'date': datetime.datetime.now()}
		if self.__bm.config.has_option("log","file") :
			_content = FAM.readfile(self.__bm.config.get("log","file"))
		else :
			if FAM.exists("nssbackup.log") :
				_content = FAM.readfile("nssbackup.log")
			else :
				_content = _("I didn't find the log file. Please set it up in nssbackup.conf ")
		
		server = smtplib.SMTP()
		msg = MIMEMultipart()
		
		msg['Subject'] = _title
		msg['From'] = _from
		msg['To'] = _to
		msg.preamble = _title
		
		msg_content = MIMEText(_content)
		# Set the filename parameter
		msg_content.add_header('Content-Disposition', 'attachment', filename="nssbackup.log")
		msg.attach(msg_content)
		
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
		server.sendmail(_from, _to, msg.as_string())
		server.close()
	
		
	def run(self):
		"""
		Method used to run nssbackupd
		- checks for the user who called it
		- if it's root, it makes a loop to run sbackup for all users that asked for it.
	 	- if it's another user, launch BackupManager with the user configuration file
		- catches all exceptions thrown and logs them (with stacktrace)
		"""
		
		global __bm
		
		try :
			
			if os.getuid() == 0 : 
				# --------------
				# we are root
				try :
					self.__profileName = _("Default Profile")
					if os.path.exists("/etc/nssbackup.conf") :
						# first launch the default config 
						self.__bm = BackupManager("/etc/nssbackup.conf")
					else :
						self.__bm = BackupManager()
					# do the backup
					self.__bm.makeBackup()
				except Exception, e:
					self.__onError(e)
				finally:
					self.__onFinish()
				
				# Now search for alternate configuration files
				# They are located in /etc/nssbackup.d/
				if os.path.exists("/etc/nssbackup.d") and os.path.isdir("/etc/nssbackup.d") :
					# The path exists, search  inside
					r = re.compile(self.__confFilesRE)
					
					for cf in os.listdir("/etc/nssbackup.d") :
						if os.path.isfile("/etc/nssbackup.d/"+cf) :
							m = r.match(cf)
							if m : 
								try:
									self.__profileName = m.group(1) 
									self.__bm = BackupManager("/etc/nssbackup.d/"+cf)
									self.__bm.makeBackup()
								except Exception, e:
									self.__onError(e)
								finally:
									self.__onFinish()
				
				# ---------------------
			else :  
				# ---------------------
				# we are others
				try:
					self.__profileName = _("Default Profile")
					if os.path.exists(getUserConfDir()+ "nssbackup.conf") :
						self.__bm = BackupManager(getUserConfDir()+ "nssbackup.conf")
					else :
						self.__bm = BackupManager()
					# do the backup
					self.__bm.makeBackup()
				except Exception, e:
					self.__onError(e)
				finally:
					self.__onFinish()
				
				# Now search for alternate configuration files
				# They are located in getUserConfDir()+"/nssbackup.d"
				if os.path.exists(getUserConfDir()+"/nssbackup.d") and os.path.isdir(getUserConfDir()+"/nssbackup.d") :
					# The path exists, search  inside
					r = re.compile(self.__confFilesRE)
					
					for cf in os.listdir(getUserConfDir()+"/nssbackup.d") :
						if os.path.isfile(getUserConfDir()+"/nssbackup.d/"+cf) :
							m = r.match(cf)
							if m : 
								try:
									self.__profileName = m.group(1)
									self.__bm = BackupManager(getUserConfDir()+"/nssbackup.d/"+cf)
									self.__bm.makeBackup()
								except Exception, e:
									self.__onError(e)
								finally:
									self.__onFinish()
								
				# ----------------
			
		except Exception, e :
			self.logger.error(str(e))
			self.logger.error(traceback.format_exc())
			try:
				import pynotify
				if pynotify.init("NSsbackup"):
					n = pynotify.Notification("NSsbackup", "CRASH [%s]: '%s'" % (self.__profileName, str(e)))
					n.show()
				else:
					self.logger.warning(_("there was a problem initializing the pynotify module"))
			except Exception, e1:
				self.logger.warning(str(e1))

	def __onError(self, e):
		"""
		"""
		self.logger.error(str(e))
		self.logger.error(traceback.format_exc())
		
		try:
			import pynotify
			if pynotify.init("NSsbackup"):
				n = pynotify.Notification("NSsbackup", "CRASH [%s]: '%s'" % (self.__profileName, str(e)))
				n.show()
			else:
				self.logger.warning(_("there was a problem initializing the pynotify module"))
		except Exception, e1:
			self.logger.warning(str(e1))
		
		if self.__bm and self.__bm.config :
			# remove any left lockfile
			if self.__bm.config.has_option("general","lockfile") and FAM.exists(self.__bm.config.get("general","lockfile")) :
				self.logger.info(_("Session of backup is finished (lockfile is removed) "))
				FAM.delete(self.__bm.config.get("general","lockfile"))
			
			# put the logfile in the snapshotdir
			logfile = None
			if self.__bm.config.has_option("log","file") and FAM.exists(self.__bm.config.get("log","file")) :
				logfile = self.__bm.config.get("log","file")
			elif FAM.exists("nssbackup.log") :
				logfile =os.path.abspath("nssbackup.log")
			# check for the avaibility of the snapshot
			snp = self.__bm.getActualSnapshot()
			if snp and logfile :
				import shutil
				shutil.copy(logfile, snp.getPath())
			else :
				self.logger.error(_("Couldn't copy the logfile into the snapshot directory"))

	def __onFinish(self):
		if self.__bm and self.__bm.config :
			# send the mail
			if self.__bm.config.has_section("report") and self.__bm.config.has_option("report","to") :
				self.__sendEmail()
