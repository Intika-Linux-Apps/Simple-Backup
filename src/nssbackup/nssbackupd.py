#    NSsbackup - the actual backup service
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

from gettext import gettext as _
import os
import os.path
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import socket
import datetime
import re
import subprocess
import optparse

from nssbackup import Infos
from nssbackup.util import log
from nssbackup.util import getResource
from nssbackup.util import dbus_support
from nssbackup.util import state
import nssbackup.managers.FileAccessManager as FAM
from nssbackup.managers.ConfigManager import getUserConfDir
from nssbackup.managers.ConfigManager import ConfigManager
from nssbackup.managers.ConfigManager import ConfigurationFileHandler
from nssbackup.managers.ConfigManager import ConfigStaticData
from nssbackup.managers.BackupManager import BackupManager

    
class NSsbackupd(object):
    """This class is intended to be a wrapper of nssbackup instances. 
    It manages :
    - the full backup process : creation of instances of the BackupManager
      with the corresponding config file 
    - the logging of exception not handled by BackupManager
    - the removal of lockfiles
    - the sending of emails
    
    """
    
    __confFilesRE = "^nssbackup-(.+?)\.conf$"

    def __init__(self, notifiers, configfile):
        """Default constructor. Basic initializations are done here.

        :param notifiers: instances of notifiers that should be used
        :param configfile: use this configuration file
        
        :type notifiers: list
        
        :note: The configuration managers are retrieved very early
               to ensure that specific logger instances are created.
        
        """
        self.__errors            = []
        
#        self.__super_user        = False
#        self.__check_for_superuser()
        
        # collection of all config managers
        self.__confm            = []

        # the name of the currently processed profile
        self.__profilename        = None
        self.__retrieve_confm(configfile)

        # here the logger created for the default profile is used
        self.logger            = log.LogFactory.getLogger(self.__profilename)

        # the currently used instance of the BackupManager
        self.__bm                = None
        self.__state             = state.NSsbackupState()
        
        self.__notifiers = notifiers
        self.__register_notifiers()
        self.__initialize_notifiers()

    def __register_notifiers(self):
        """Registers the given notifiers as observers.

        :todo: should we give the `state` as parameter to notfier's constructor?

        """
        for notifier in self.__notifiers:
            self.__state.attach(notifier)

    def __initialize_notifiers(self):
        """Initializes the given notifiers.

        """
        for notifier in self.__notifiers:
            notifier.initialize()

    def __terminate_notifiers(self):
        """Unregisters the given notifiers from state subject.

        """
        for notifier in self.__notifiers:
            notifier.exit()
            self.__state.detach(notifier)

    def __check_for_superuser(self):
        """Checks whether the application was invoked with super-user rights.
        If so, the member variable 'self.__super_user' is set.
        
        :todo: Here should no distinction between user/superuser be necessary!
        
        """
        if os.getuid() == 0:
            self.__super_user = True
            
    def __retrieve_confm(self, force_conffile):
        """Factory method that retrieves the appropriate configuration managers
        for the existing profiles. Super-user rights are taken into account.
        The created configuration managers are stored in member variable
        'self.__confm'.
        
        :todo: Place the path names in class `ConfigStaticData`.
        
        """
        self.__confm = []

        # default profile config file and the config directory is determined
        conffile_hdl = ConfigurationFileHandler()
        if force_conffile is None:
            conffile = conffile_hdl.get_conffile()
        else:
            conffile = force_conffile
        confdir = conffile_hdl.get_profilesdir(conffile)

        print "ConfigFile to use: `%s`, dir: `%s`" % (conffile, confdir)
        # create config manager for the default profile and set as current
        if os.path.exists( conffile ):
            confm = ConfigManager( conffile )
            self.__profilename = confm.getProfileName()
            # store the created ConfigManager in a collection
            self.__confm.append( confm )
        else:
            errmsg = _("Critical Error: No configuration file for the default "\
                       "profile was found!\n\nNow continue processing "\
                       "remaining profiles.")
            self.__errors.append(errmsg)

        # Now search for alternate configuration files
        # They are located in (configdir)/nssbackup.d/
        
# TODO: replace this with 'get_profiles' from ConfigManager.py
        if os.path.exists(confdir) and os.path.isdir(confdir):
            cregex = re.compile(self.__confFilesRE)
            cfiles = os.listdir( confdir )
            for cfil in cfiles:
                cfil_fullpath = os.path.join( confdir, cfil )
                if os.path.isfile( cfil_fullpath ):
                    mres = cregex.match( cfil )
                    if mres:    # if filename matches, create manager and add it
                        confm = ConfigManager( cfil_fullpath )
                        self.__confm.append( confm )


    def run(self):
        """Actual main method to make backups using NSsbackup
        
        - checks for the user who called it
        - if it's root, it makes a loop to run sbackup for all users that asked for it.
         - if it's another user, launch BackupManager with the user configuration file
        - catches all exceptions thrown and logs them (with stacktrace)

        :todo: Add a commandline option and a config option whether to use dbus!
        
        """
        
        self.__notify_errlist()

        for confm in self.__confm:
            try:
                self.__profilename     = confm.getProfileName()
                self.logger            = log.LogFactory.getLogger(self.__profilename)
                
                self.__state.set_profilename(self.__profilename)

                self.__bm              = BackupManager(confm, self.__state)
                self.__log_errlist()
                self.__bm.makeBackup()
            except Exception, exc:
                self.__on_error(exc)
            finally:
                self.__onFinish()

        self.__terminate_notifiers()

    def __on_error(self, error):
        """Handles errors that occurs during backup process.
        
        """
        self.logger.error(str(error))
        self.logger.error(traceback.format_exc())

        try:
            self.__state.set_recent_error(error)
            self.__state.set_state('error')
        except Exception, err2:
            self.logger.warning(str(err2))
        
        if self.__bm:
            self.__bm.endSBsession()

    def __onFinish(self):
        """Method that is finally called after backup process.
        """
        if self.__bm and self.__bm.config :
            # send the mail
            if self.__bm.config.has_section("report") and\
               self.__bm.config.has_option("report","to") :
                self.__sendEmail()
                
    def __notify_errlist(self):
        """Errors that occured during the initialization process were stored
        in an error list. This error list is showed to the user by this method.
        """
        if len(self.__errors) > 0:
            for errmsg in self.__errors:
                self.__state.set_recent_error(errmsg)
                self.__state.set_state('error')
                
    def __log_errlist(self):
        """Errors that occurred during the initialization process
        were stored in an error list. The full list of errors is
        added to the current log.
        
        """
        if len(self.__errors) > 0:
            self.logger.info(_("The following error(s) occurred before:"))
            for errmsg in self.__errors:
                self.logger.error(errmsg.replace("\n", " "))
                
    def __sendEmail(self):
        """Checks if the sent of emails is set in the config file 
        then send an email with the report
        
        :todo: Transfer this functionality to a specialized class!
        
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
                    % { 'profile':self.__profilename,
                        'date': datetime.datetime.now() }
        logf = self.__bm.config.get_logfile()
        if FAM.exists( logf ):
            _content = FAM.readfile( logf )
        else :
            _content = _("I didn't find the log file. Please set it up in "\
                         "nssbackup.conf ")
        
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
                
                

class NSsbackupApp(object):
    """The application that processes the backup.
    
    :todo: Implement a base class providing common commandline parsing etc.!
    
    """
    
    def __init__(self, argv):
        self.__argv = argv
        self.__use_dbus = True
        self.__use_tray = True
        self.__configfile = None
        
        self.__backupdaemon = None
        self.__notifiers = []
        
    def create_notifiers(self):
        if self.__use_dbus:
            dbus_notifier = dbus_support.DBusNotifier()
            self.__notifiers.append(dbus_notifier)

    def launch_services(self):
        if self.__use_dbus == True:
            self._launch_service()
            
        if self.__use_tray == True:
            self._launch_traygui()

    def _launch_service(self):
        print "Now launching DBus service"
        dbus_launcher = getResource('nssbackup_service')
        pid = subprocess.Popen([dbus_launcher]).pid
        print "pid: %s" % pid

    def _launch_traygui(self):
        print "Now launching tray gui"
        tray_gui = getResource('nssbackup_traygui')
        pid = subprocess.Popen([tray_gui]).pid
        print "pid: %s" % pid
        
    def parse_cmdline(self):
        """Parses the given commandline options and sets specific
        attributes. It must be considered that the DBus service can
        be used without the tray GUI but in contrast the tray GUI
        cannot be used without the DBus service.
        
        The method uses the commandline arguments given to class'
        constructor.
        
        :todo: An option '--dry-run' would be nice!
        
        """
        usage = "Usage: %prog [options] (use -h or --help for more infos)"
        version="%prog " + Infos.VERSION
        prog = "nssbackupd"
        
        parser = optparse.OptionParser(usage=usage, version=version, prog=prog)
        parser.add_option("-n", "--no-tray-gui",
                  action="store_false", dest="use_tray", default=True,
                  help="don't use the graphical user interface in system tray")

        parser.add_option("-d", "--dont-use-dbus",
                  action="store_false", dest="use_dbus", default=True,
                  help="don't launch the DBus service and "\
                       "don't use it (implies --no-tray-gui)")

        parser.add_option("-c", "--config-file", dest="configfile",
                          metavar="FILE", default=None,
                          help="set the configuration file to use")
        
        (options, args) = parser.parse_args(self.__argv[1:])
        if len(args) > 0:
            parser.error("You must not provide any non-option argument")

        print "options: %s\nargs: %s" % (options, args)

        if options.configfile:
# TODO: Add check for existence here?            
            self.__configfile = options.configfile
        
        self.__use_dbus = options.use_dbus
        if self.__use_dbus == True: 
            self.__use_tray = options.use_tray
        else:
            self.__use_tray = False

    def run(self):
        """Runs the whole backup process including launching of
        external applications and services...
        
        """
        retcode = 0
        try:
            self.parse_cmdline()
            print "DBus: %s, Tray: %s, Config: %s" % (self.__use_dbus,
                                                      self.__use_tray,
                                                      self.__configfile)
            self.launch_services()
            self.create_notifiers()
            
            self.__backupdaemon = NSsbackupd(self.__notifiers,
                                             self.__configfile)
#            self.__backupdaemon.run()

        except SystemExit, exc:
            print "SystemExit catched `%s`" % (exc.code)
            retcode = exc.code
            
        print "Now shutting down logging"
        log.shutdown_logging()
        
        return retcode
        

def main(argv):
    """Public function that processes the backups.
    
    :todo: Should be give the DBus conenction as parameter? No, because it\
           cannot be determined whether the dbus should be used at this\
           time!
           
    """
    sbackup_app = NSsbackupApp(argv)
    excode = sbackup_app.run()
    return excode
