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


import sys
import os
import os.path
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import socket
import datetime
import time
import re
from gettext import gettext as _
import dbus

from nssbackup.util import log
from nssbackup.util import dbus_support
import nssbackup.managers.FileAccessManager as FAM
from nssbackup.managers.ConfigManager import getUserConfDir
from nssbackup.managers.ConfigManager import ConfigManager
from nssbackup.managers.BackupManager import BackupManager
from nssbackup.util import exceptions


class DBusConnection(object):
    """This class provides functionality for sending signals
    and calling methods over the dbus.
    
    The sender needs a dbus connection.
    
    The Dbus connection is only created on demand. In the case the user
    don't want to use it, no connection is created.
    """
    def __init__(self, logger):
        """Default constructor.
        
        :param logger: Instance of logger to be used.
        
        """
        self.__logger = logger
        
        self._session_bus   = None
        self._remote_obj    = None
        self._remote_gui    = None
        self._dbus_present  = False
        self._gui_present = False

    def __do_connect(self, service, path):
        remote_obj = None
        timeout = 30        # seconds
        max_trials = 10     # number of max. trials
        dur = timeout/max_trials
        
        trials = 0          # done trials
        connecting = True
        while connecting:
            try:
                trials += 1
                print "Trying to connect to `%s` (trial no. %s)" % (service,
                                                                    trials)
                remote_obj  = self._session_bus.get_object(service, path)
                connecting = False
                print "successfully connected to `%s`" % service
            except dbus.DBusException, exc:
                print "\nError while getting service:\n%s" % (str(exc))
                if trials == max_trials:
                    print "Number of max. trials reached - timeout!"
                    connecting = False
                    remote_obj = None
                else:
                    print "Waiting %s sec. before re-connecting" % dur
                    time.sleep(dur)
        return remote_obj
        
    def connect(self):
        """
        :todo: Implement check whether the service is already running!
        
        """
        self._session_bus = dbus.SessionBus()
        
        self._remote_obj  = self.__do_connect(dbus_support.DBUS_SERVICE,
                                              dbus_support.DBUS_OBJ_PATH)
        if self._remote_obj is not None:
            self._dbus_present = True

        # now for the gui service
        self._remote_gui  = self.__do_connect(dbus_support.DBUS_GUI_SERVICE,
                                              dbus_support.DBUS_GUI_OBJ_PATH)
        if self._remote_gui is not None:
            self._gui_present = True

        print "Dbus service available: %s" % self._dbus_present
        print "GUI service available: %s" % self._gui_present
        
    def handle_reply(self, msg):
        print msg
    
    def handle_error(self, e):
        print str(e)
    
    def emit_start_signal(self, profile):
        """Used for sending a start signal over the signal dbus.
        
        :param profile: name of the current profile
        
        """
        ret_val = self._remote_obj.emit_nssbackup_started_signal(profile,
                        dbus_interface=dbus_support.DBUS_INTERFACE)
            
        print "Returned value: %s" % ret_val
        return ret_val

    def emit_finish_signal(self, profile):
        """Used for sending a finish signal over the signal dbus.
        
        :param profile: name of the current profile
        
        """
        ret_val = self._remote_obj.emit_nssbackup_finished_signal(profile,
                        dbus_interface=dbus_support.DBUS_INTERFACE)

        print "Returned value: %s" % ret_val
        return ret_val

    def emit_error_signal(self, profile, error):
        """Used for sending an error signal over the signal dbus.
        
        :param profile: name of the current profile
        :param error: error message to be passed
        
        """
        ret_val = self._remote_obj.emit_nssbackup_error_signal(profile, error,
                        dbus_interface=dbus_support.DBUS_INTERFACE)
            
        print "Returned value: %s" % ret_val
        return ret_val

    def call_method(self, msg):
        """Used for calling a method on the GUI Dbus.
        
        """
        print "call_method - msg: %s" % msg
        ret_val = self._remote_gui.HelloWorld(msg,
                        dbus_interface=dbus_support.DBUS_GUI_INTERFACE)
        print "returned: %s" % ret_val

    def _notify_info(self, profilename, message):
        raise exceptions.NotSupportedError("Not yet implemented!")

    def _notify_warning(self, profilename, message):
        raise exceptions.NotSupportedError("Not yet implemented!")

    def _notify_error(self, profilename, message):
        raise exceptions.NotSupportedError("Not yet implemented!")
    
    def exit(self):
        print "Sending 'Exit'"

#        if self._remote_obj:
#            self._remote_obj.Exit(dbus_interface=\
#                                  dbus_support.DBUS_INTERFACE)
#        if self._remote_gui:
#            self._remote_gui.Exit(dbus_interface=\
#                                  dbus_support.DBUS_GUI_INTERFACE)
#        return 
    
        if self._remote_obj:
            # first send an `Exit` signal out
            self._remote_obj.emit_nssbackup_exit_signal(dbus_interface=\
                                                    dbus_support.DBUS_INTERFACE)
            time.sleep(2)
            # and then exit the service itself
            self._remote_obj.Exit(dbus_interface=\
                                  dbus_support.DBUS_INTERFACE)
            
        
    
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

    def __init__(self):
        """Default constructor. Basic initializations are done here.

        :note: The configuration managers are retrieved very early
               to ensure that specific logger instances are created.
        
        """
        self.__recent_error = None
        self.__errors            = []
        
        self.__super_user        = False
        self.__check_for_superuser()
        
        # collection of all config managers
        self.__confm            = []
        # the name of the currently processed profile
        self.__profilename        = None
        self.__retrieve_confm()

        # here the logger created for the default profile is used
        self.logger            = log.LogFactory.getLogger(self.__profilename)

        # the currently used instance of the BackupManager
        self.__bm                = None

        self._dbus = None
        
        
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
    
    def __retrieve_confm(self):
        """Factory method that retrieves the appropriate configuration managers
        for the existing profiles. Super-user rights are taken into account.
        The created configuration managers are stored in member variable
        'self.__confm'.
        
        :todo: Place the path names in class `ConfigStaticData`.
        
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

    def __setup_dbus(self):
        self._dbus = DBusConnection(self.logger)
        self._dbus.connect()

    def run(self):
        """Actual main method to make backups using NSsbackup
        
        - checks for the user who called it
        - if it's root, it makes a loop to run sbackup for all users that asked for it.
         - if it's another user, launch BackupManager with the user configuration file
        - catches all exceptions thrown and logs them (with stacktrace)
        """
        # if config == use_dbus...
        self.__setup_dbus()

#        self._dbus.exit()
#        sys.exit(1)
        
        print "DAEMON - now everything is prepared for doing a backup"
#        print "Emitting signal now..."
#        self._dbus.emit_signal("Hello")

#        for i in range(0, 2):
#            print '.'
#            time.sleep(1)

#        not suitable for user interaction!
#        self._dbus.call_method("This is a message call from 'sbackup_sender.py':\n"\
#                         "We finished.")
#        print "We finished!"
            
#        self.__notify_errlist()
#        
        for confm in self.__confm:
            try:
                self.__profilename     = confm.getProfileName()
                self.logger            = log.LogFactory.getLogger(self.__profilename)
                self.__bm              = BackupManager( confm )
                self.__log_errlist()
                self.__attempt_notify(event='start')
                self.__bm.makeBackup()
                self.__attempt_notify(event='finish')
            except Exception, exc:
                self.__on_error(exc)
            finally:
                self.__onFinish()

        self._dbus.exit()

    def __on_error(self, error):
        """Handles errors that occurs during backup process.
        
        """
        self.__recent_error = error
        self.logger.error(str(error))
        self.logger.error(traceback.format_exc())

        try:
            self.__attempt_notify('error')
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
                self.__recent_error = errmsg
                self.__attempt_notify('error')
#                self._notify_error(self.__profilename, errmsg)

    def __log_errlist(self):
        """Errors that occurred during the initialization process
        were stored in an error list. The full list of errors is
        added to the current log.
        
        """
        if len(self.__errors) > 0:
            self.logger.info(_("The following error(s) occurred before:"))
            for errmsg in self.__errors:
                self.logger.error(errmsg.replace("\n", " "))
                
    def __attempt_notify(self, event):
        print "EVENT: %s" % event
        ret_val = None
        if self._dbus is not None:
            if event == 'start':
                ret_val = self._dbus.emit_start_signal(self.__profilename)
                
            elif event == 'finish':
                ret_val = self._dbus.emit_finish_signal(self.__profilename)

            elif event == 'error':
                ret_val = self._dbus.emit_error_signal(self.__profilename,
                                                       str(self.__recent_error))
    
            else:
                print "EVENT UNSUPPORTED (%s)" % event
                
        print "Returned value: %s" % ret_val
        return ret_val


def main(argv):
    """Public function that process the backups.
    
    :todo: Should be give the DBus conenction as parameter? No, because it\
           cannot be determined whether the dbus should be used at this\
           time!
           
    """
    sbd = NSsbackupd()
    sbd.run()
    log.shutdown_logging()
