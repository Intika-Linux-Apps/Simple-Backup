#    NSsbackup - the actual backup service
#
#   Copyright (c)2008-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#   Copyright (c)2007-2008: Ouattara Oumar Aziz <wattazoum@gmail.com>
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

import traceback
import sys
import smtplib
import socket
import datetime
import optparse
import time

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


from nssbackup.pkginfo import Infos

from nssbackup.core.ConfigManager import ConfigManager, get_profiles
from nssbackup.core.ConfigManager import ConfigurationFileHandler
from nssbackup.core.profile_handler import BackupProfileHandler

from nssbackup.util import enable_backup_cancel_signal, enable_termsignal
from nssbackup.util import get_resource_file
from nssbackup.util import local_file_utils
from nssbackup.util import exceptions
from nssbackup.util import constants
from nssbackup.util import system
from nssbackup.util import notifier
from nssbackup.util import lock
from nssbackup.util import log


def except_hook(etype, evalue, etb):
    _logger = log.LogFactory.getLogger()
    _lines = traceback.format_exception(etype, evalue, etb)
    _lines = "".join(_lines)
    _logger.error("Uncaught exception: %s" % evalue)
    _logger.error(_lines)


sys.excepthook = except_hook
#TODO: move the following into GIO backend: should be executed in case of enabled gio backend only!
system.set_dbus_session_bus_from_session()
system.launch_dbus_if_required()


class SBackupProc(object):
    """This class is intended to be a wrapper of the process of backups of
    multiple profiles.
    
    It manages :
    - the full backup process : creation of instances of the BackupProfileHandler
      with the corresponding config file 
    - the logging of exception not handled by BackupProfileHandler
    - the removal of lockfiles
    - the sending of emails
    
    """

    def __init__(self, notifiers, configfile, dbus_connection = None,
                 use_indicator = False, full_snapshot = False):
        """Default constructor. Basic initializations are done here.

        :param notifiers: instances of notifiers that should be used
        :param configfile: use this configuration file
        :param dbus_connection: DBus connection (connected and registerd)
        
        :type notifiers: list
        
        :note: The configuration managers are retrieved very early
               to ensure that specific logger instances are created.
               
        :todo: Collect options (configfile, use_indicator...) in class/struct!
        
        """
        self.__dbus_conn = dbus_connection
        self.__use_indicator = use_indicator
        self.__full_snp = full_snapshot

        self.__exitcode = constants.EXCODE_GENERAL_ERROR
        self.__errors = []

        # collection of all config managers
        self.__confm = []
        # the name of the currently processed profile
        self.__profilename = None
        self.__retrieve_confm(configfile)

        # here the logger created for the default profile is used
        self.logger = log.LogFactory.getLogger(self.__profilename)
        self.logger.debug("%s %s" % (Infos.NAME, Infos.VERSION))

        # the currently used instance of the BackupProfileHandler
        self.__bprofilehdl = None
        self.__state = notifier.SBackupState()

        self.__notifiers = notifiers
        self.__register_notifiers()
        self.__initialize_notifiers()

    def __register_notifiers(self):
        """Registers the given notifiers as observers.

        :todo: should we give the `state` as parameter to notfier's constructor?

        """
        for _notifier in self.__notifiers:
            self.__state.attach(_notifier)

    def __initialize_notifiers(self):
        """Initializes the given notifiers.

        """
        for _notifier in self.__notifiers:
            _notifier.initialize()

    def __terminate_notifiers(self):
        """Unregisters the given notifiers from state subject.

        """
        for _notifier in self.__notifiers:
            _notifier.publish_exit()
            self.__state.detach(_notifier)

    def __sendEmail(self):
        """Checks if the sent of emails is set in the config file 
        then send an email with the report
        
        :todo: Transfer this functionality to a specialized class!
        
        """
        if self.__bprofilehdl.config.has_option("report", "from") :
            _from = self.__bprofilehdl.config.get("report", "from")
        else :
            hostname = socket.gethostname()
            if "." in hostname :
                mailsuffix = hostname
            else :
                mailsuffix = hostname + ".ext"
            _from = _("NSsbackup Daemon <%(login)s@%(hostname)s>")\
                    % {'login' : str(system.get_user_from_env()), 'hostname': mailsuffix}

        _to = self.__bprofilehdl.config.get("report", "to")
        _title = _("[NSsbackup] [%(profile)s] Report of %(date)s")\
                    % { 'profile':self.__profilename,
                        'date': datetime.datetime.now() }
        logf = self.__bprofilehdl.config.get_current_logfile()
        if logf is None:
            _content = _("No log file specified.")
        else:
            if local_file_utils.path_exists(logf):
                _content = local_file_utils.readfile(logf)
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
                               filename = "nssbackup.log")
        msg.attach(msg_content)

        # getting the connection
        if self.__bprofilehdl.config.has_option("report", "smtpserver") :
            if self.__bprofilehdl.config.has_option("report", "smtpport") :
                server.connect(self.__bprofilehdl.config.get("report", "smtpserver"),
                               self.__bprofilehdl.config.get("report", "smtpport"))
            else :
                server.connect(self.__bprofilehdl.config.get("report", "smtpserver"))
        if self.__bprofilehdl.config.has_option("report", "smtptls") and\
                    self.__bprofilehdl.config.get("report", "smtptls") == 1 :
            if self.__bprofilehdl.config.has_option("report", "smtpcert") and\
                    self.__bprofilehdl.config.has_option("report", "smtpkey") :
                server.starttls(self.__bprofilehdl.config.get("report", "smtpkey"),
                                self.__bprofilehdl.config.get("report", "smtpcert"))
            else :
                server.starttls()
        if self.__bprofilehdl.config.has_option("report", "smtpuser") and\
                self.__bprofilehdl.config.has_option("report", "smtppassword") :
            server.login(self.__bprofilehdl.config.get("report", "smtpuser"),
                         self.__bprofilehdl.config.get("report", "smtppassword"))

        # send and close connection
        server.sendmail(_from, _to, msg.as_string())
        server.close()

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
            # conffile given on commandline is treated as default profile's config
            conffile = force_conffile
        confdir = conffile_hdl.get_profilesdir(conffile)

        # create config manager for the default profile and set as current
        if local_file_utils.path_exists(conffile):
            confm = ConfigManager(conffile)
            self.__profilename = confm.getProfileName()
            self.__confm.append(confm)      # store the created ConfigManager in a collection
        else:
            errmsg = _("Critical Error: No configuration file for the default profile was found!\n\nNow continue processing remaining profiles.")
            self.__errors.append(errmsg)

        if force_conffile is None:
            # search for alternate configuration files only if no config file was given
            for _prof in get_profiles(confdir).values():
                _prof_path = _prof[0]
                _prof_enable = _prof[1]

                if _prof_enable:
                    confm = ConfigManager(_prof_path)
                    self.__confm.append(confm)

    def run(self):
        """Actual main method to make backups using NSsbackup
        
        - launch BackupProfileHandler with the user configuration file
        - catches all exceptions thrown and logs them
        """
        self.__notify_init_errors()

        for confm in self.__confm:
            try:
                self.__profilename = confm.getProfileName()
                self.logger = log.LogFactory.getLogger(self.__profilename)

                self.__bprofilehdl = BackupProfileHandler(confm, self.__state, self.__dbus_conn,
                                          self.__use_indicator, self.__full_snp)

                self.__write_errors_to_log()

                self.__bprofilehdl.prepare()
                self.__bprofilehdl.process()
                self.__exitcode = self.__bprofilehdl.finish()
                self.__bprofilehdl = None

            except exceptions.BackupCanceledError:
                self.__on_backup_canceled()

            except Exception, error:
                self.__on_error(error)

            self.__on_finish()

        self.__terminate_notifiers()
        return self.__exitcode

    def __on_backup_canceled(self):
        self.logger.warning(_("Backup was canceled by user."))
        self.__state.set_state('backup-canceled')
        if self.__bprofilehdl is not None:
            self.__exitcode = self.__bprofilehdl.finish()

    def __on_error(self, error):
        """Handles errors that occurs during backup process.
        """
        if self.logger.isEnabledFor(10):
            self.logger.exception(_("An error occurred during the backup:\n%s") % (str(error)))
        else:
            self.logger.error(_("An error occurred during the backup: %s") % (str(error)))
        self.__exitcode = constants.EXCODE_BACKUP_ERROR
        self.__state.set_recent_error(error)
        self.__state.set_state('error')
        if self.__bprofilehdl is not None:
            self.__exitcode = self.__bprofilehdl.finish(error)

    def __on_finish(self):
        """Method that is finally called after backup process.
        """
        try:
            if self.__bprofilehdl and self.__bprofilehdl.config:
                # send the mail
                if self.__bprofilehdl.config.has_section("report") and self.__bprofilehdl.config.has_option("report", "to") :
                    self.__sendEmail()
        except Exception, error:
            self.__exitcode = constants.EXCODE_MAIL_ERROR
            self.logger.exception("Error when sending email:\n%s" % error)

    def __notify_init_errors(self):
        """Errors that occurred during the initialization process were stored
        in an error list. This error list is showed to the user by this method.
        """
        if len(self.__errors) > 0:
            for errmsg in self.__errors:
                self.__state.set_recent_error(errmsg)
                self.__state.set_state('error')

    def __write_errors_to_log(self):
        """Errors that occurred during the initialization process
        were stored in an error list. The full list of errors is
        added to the current log.
        
        """
        if len(self.__errors) > 0:
            self.logger.info(_("The following error(s) occurred before:"))
            for errmsg in self.__errors:
                self.logger.error(errmsg.replace("\n", " "))



class SBackupApp(object):
    """The application that processes the backup.
    
    :todo: Implement a base class providing common commandline parsing etc.!
    
    """

    def __init__(self, argv):
        self.__argv = argv
        self.__lock = lock.ApplicationLock(lockfile = constants.LOCKFILE_BACKUP_FULL_PATH,
                                           processname = constants.BACKUP_COMMAND, pid = system.get_pid())
        self.__options_given = None   # do not modify given options
        self.__use_indicator = True
        self.__dbus_avail = False
        self.__configfile = None

        self.__backupproc = None
        self.__notifiers = []
        # we establish a connection to ensure its presence for progress action
        self.__dbus_conn = None
        self.__exitcode = constants.EXCODE_GENERAL_ERROR

    def create_notifiers(self):
        """Creates notifiers used within the backup process. Note that these
        notifiers are not ready for use yet, they are initialized within
        the backup process. Purpose is to split between notifier creation and
        notifier use: the backup process has no information about the
        specific notifiers (type...)
        :note: import D-Bus related modules only if using D-Bus is enabled        
        """
        if self.__options_given.use_dbus and self.__dbus_avail:
            from nssbackup.util import dbus_support
            dbus_notifier = dbus_support.DBusNotifier()
            self.__notifiers.append(dbus_notifier)

    def launch_externals(self):
        if self.__options_given.use_dbus == True:
            self._launch_dbusservice()

        if (self.__use_indicator == True) and (self.__dbus_avail == True):
            try:
                self._launch_indicator()
            except exceptions.ResourceFileNotFoundError:
                self.__use_indicator = False

    def _launch_dbusservice(self):
        """Launches the DBus service and establishes a placeholder
        connection in order to keep the service alive as long as this
        application is running. Call `finalize` to close the
        connection properly when terminating the application.
        
        :note: import D-Bus related modules only if using D-Bus is enabled
        """
        from nssbackup.util import dbus_support
        self.__dbus_conn = dbus_support.DBusProviderFacade(constants.BACKUP_PROCESS_NAME)
        try:
            self.__dbus_conn.connect()
            self.__dbus_conn.set_backup_pid(pid = system.get_pid())
            self.__dbus_avail = True
        except exceptions.DBusException:
            print "Unable to launch DBus service"
            self.__dbus_conn = None
            self.__dbus_avail = False
            self.__use_indicator = False

    def _launch_indicator(self):
        """              
        environ: the Gnome-session environ is accessable for root and the
                 user who owns the session.
        :note: import D-Bus related modules only if using D-Bus is enabled                 
        """
        from nssbackup.util import dbus_support

        print "Now launching indicator application (status icon)."
        _path_to_app = get_resource_file(constants.INDICATORAPP_FILE)

        session = dbus_support.get_session_name()   # a full DE is supposed         
        if session == "":   # in empty environments, it might impossible to connect to D-Bus session server
            print "No DE found using D-Bus. Looking for process id."
            session = system.get_session_name()

        session_env = system.get_session_environment(session)

        if session_env is None:
            print "No desktop session found. Indicator application is not started."
        else:
            _cmd = [_path_to_app]
            if self.__options_given.legacy_appindicator is True:
                _cmd.append("--legacy")

            if not system.is_superuser():
                if system.get_user_from_uid() != session_env["USER"]:
                    _cmd = None
                    print "Unable to launch indicator application as current user.\n"\
                          "You must own current desktop session."

            if _cmd is None:
                print "Unable to launch indicator application"
            else:
                pid = system.exec_command_async(args = _cmd, env = session_env)
                print "Indicator application started (PID: %s)" % pid
                time.sleep(constants.INDICATOR_LAUNCH_PAUSE_SECONDS)


    def finalize(self):
        """Cleaning before terminating the application:
        * disconnects if DBus connection was established.
        """
        if (self.__dbus_avail) and (self.__dbus_conn is not None):
            self.__dbus_conn.quit()
        self.__lock.unlock()
        log.shutdown_logging()


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
        version = "%prog " + Infos.VERSION
        prog = constants.BACKUP_COMMAND

        parser = optparse.OptionParser(usage = usage, version = version, prog = prog)
        parser.add_option("--no-indicator",
                  action = "store_false", dest = "use_indicator", default = True,
                  help = "don't use the graphical indicator application (status icon)")

        parser.add_option("--no-dbus",
                  action = "store_false", dest = "use_dbus", default = True,
                  help = "don't launch the DBus service and "\
                       "don't use it (implies --no-indicator)")

        parser.add_option("--config-file", dest = "configfile",
                          metavar = "FILE", default = None,
                          help = "set the configuration file to use")

        parser.add_option("--legacy-indicator",
              action = "store_true", dest = "legacy_appindicator", default = False,
              help = "use legacy status icon instead of `libappindicator`")

        parser.add_option("--full",
              action = "store_true", dest = "full_snapshot", default = False,
              help = "create full snapshot")

        (options, args) = parser.parse_args(self.__argv[1:])
        if len(args) > 0:
            parser.error("You must not provide any non-option argument")

        if options.configfile:
            if not local_file_utils.path_exists(options.configfile):
                parser.error("Given configuration file does not exist")
            self.__configfile = options.configfile

        self.__options_given = options

        if self.__options_given.use_dbus == True:
            self.__use_indicator = options.use_indicator
        else:
            self.__use_indicator = False

    def __on_already_running(self, error):
        """Handler for the case a backup process is already running.
        Fuse is not initialized yet.
        :note: import D-Bus related modules only if using D-Bus is enabled        
        """
        print _("Backup is not being started.\n%s") % (str(error))
        if self.__options_given.use_dbus and self.__dbus_avail:
            from nssbackup.util import dbus_support
            conn = dbus_support.DBusClientFacade("Simple Backup Process (another instance)")
            conn.connect()
            conn.emit_alreadyrunning_signal()
            conn.quit()
        self.__exitcode = constants.EXCODE_INSTANCE_ALREADY_RUNNING

    def run(self):
        """Runs the whole backup process including launching of
        external applications and services...
        
        """
        try:
            enable_termsignal()
            enable_backup_cancel_signal()
            self.parse_cmdline()
            self.__lock.lock()

            self.launch_externals()
            self.create_notifiers()

            system.very_nice()
            system.set_grp("admin")

            self.__backupproc = SBackupProc(self.__notifiers,
                                              self.__configfile,
                                              self.__dbus_conn,
                                              self.__use_indicator,
                                              self.__options_given.full_snapshot)
            self.__exitcode = self.__backupproc.run()

        except exceptions.InstanceRunningError, error:
            self.__on_already_running(error)
        except SystemExit, exc:
            self.__exitcode = exc.code
        except KeyboardInterrupt:
            self.__exitcode = constants.EXCODE_KEYBOARD_INTERRUPT
        finally:
            self.finalize()

        return self.__exitcode


def main(argv):
    """Public function that process the backups.
    :note: DBus connection is not given as parameter here because it is not clear
           whether to use DBus or not at this time.           
    """
    sbackup_app = SBackupApp(argv)
    exitcode = sbackup_app.run()
    return exitcode
