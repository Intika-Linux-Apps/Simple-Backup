#   Copyright (c)2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#
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

#TODO: both notify-script can be combined into a single Python script!?

_APPLICATION = "nssbackup"
_APPLICATION_LONG = "(Not So) Simple Backup"
_ICON = "nssbackup32x32.png"

__START = "start"
__FINISH = "finish"
__ERROR = "error"
__valid_args = [__START, __FINISH, __ERROR]


import gettext
from gettext import gettext as _

import os
import sys
from optparse import OptionParser
import logging

import gtk


def parse_commandline():
    usage = "usage: %prog [OPTIONS] "+__START+"|"+__FINISH+"|"+__ERROR+\
            "\nTry `%prog --help' for more information."
    
    parser = OptionParser(usage)
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="show debug messages")

    parser.add_option("--pythonpath", dest="pythonpath",
                      action="store", type="string",
                  help="append PATH to the module search path", metavar="PATH")
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.error("incorrect number of arguments")
        parser.print_help()
    if args[0] not in __valid_args:
        parser.error("invalid argument")
        parser.print_help()
    return (args[0], options)


class PyNotify(object):
    """Mix-in class that provides the displaying of notifications using the
    pynotify module.
    """
    
    def __init__(self, logger, domain, icon):
        """Default constructor.
        
        :param logger: Instance of logger to be used.
        :todo: The notification domain should be retrieved from a central place!
        """
        self.__logger = logger
        self.__icon = icon

        # internal flag whether the notification module is usable
        self.__pynotif_avail = False
        
        # the pynotify module is stored in this variable
        self.__pynotif_mod   = None
        
        # the current notification
        self.__notif = None
        
        # trying to initialize the notification module
        try:
            import pynotify
            self.__pynotif_mod = pynotify
            if self.__pynotif_mod.init(domain):
                self.__pynotif_avail = True
                self.__logger.debug("Module 'pynotify' was sucessfully initialized.")
            else:
                self.__pynotif_avail = False    # yes, this is insane!
                self.__logger.warning(_("Initialization of module 'pynotify' failed."))
        except ImportError, exc:
            self.__pynotif_avail = False
            self.__logger.warning(_("Import of module 'pynotify' failed with error: %s.") % str(exc))

    def _notify_info(self, summary, message):
        """Shows up a pop-up window to inform the user. The notification
        supports mark-up.

         :param message: The message (body) that should be displayed.
         :type message:  String
        """
        if self.__pynotif_avail:
            if self.__notif is None:
                self.__notif = self.__get_notification(summary, message)
            else:
                self.__update_notification(message)
                
            if isinstance(self.__notif, self.__pynotif_mod.Notification):
                try:
                    self.__notif.set_urgency(self.__pynotif_mod.URGENCY_LOW)
                    _res = self.__notif.show()
                    if not _res:
                        self.logger.warning(_("Unable to send notification."))
                except gobject.GError, exc:
                    # Connection to notification-daemon failed 
                    self.logger.warning(_("Connection to notification-daemon failed: %s.") % str(exc))

    def _notify_warning(self, summary, message):
        """Shows up a pop-up window to inform the user. The notification
        supports mark-up.

         :param message: The message (body) that should be displayed.
         :type message:  String
        """
        self.__notify_new(summary, message, mode="warning")

    def _notify_error(self, summary, message):
        """Shows up a pop-up window to inform the user that an error occured.
        Such error notifications are emphasized and must be closed manual. The
        notifications support mark-up.

         :param message: The message (body) that should be displayed.
         :type message:  String
        """
        self.__notify_new(summary, message, mode="critical")
                
    def __notify_new(self, summary, message, mode):
        """Shows up a *new* pop-up window to inform the user that an error occured.
        Such error notifications are emphasized and must be closed manual. The
        notifications support mark-up.

         :param message: The message (body) that should be displayed.
         :type message:  String
        """
        if self.__pynotif_avail:
            notif = self.__get_notification(summary, message)
            if isinstance(notif, self.__pynotif_mod.Notification):
                try:
                    notif.set_timeout(self.__pynotif_mod.EXPIRES_NEVER)
                    if mode == "critical":
                        notif.set_urgency(self.__pynotif_mod.URGENCY_CRITICAL)
                    else:
                        notif.set_urgency(self.__pynotif_mod.URGENCY_NORMAL)
                    _res = notif.show()
                    if not _res:
                        self.logger.warning(_("Unable to send notification."))
                except gobject.GError, exc:
                    # Connection to notification-daemon failed 
                    self.logger.warning(_("Connection to notification-daemon failed: %s.") % str(exc))

    def __get_notification(self, summary, message):
        """Returns a notification object but does not display it. The
         notification supports mark-up. If notifications aren't supported
         the method returns None.
         
         :param message: The message (body) that should be displayed.
         :type message:  String
         
         :return: The created notification object or None
         :rtype: Notification or None
        
        :todo: Replace single '<' characters by '&lt;' in a more reliable way!
        """
        notif = None
        if self.__pynotif_avail:
            message = message.replace("<", "&lt;")
            try:
                notif = self.__pynotif_mod.Notification(summary, message, self.__icon)
            except gobject.GError, exc:
                # Connection to notification-daemon failed 
                self.logger.warning(_("Connection to notification-daemon failed: %s.") % str(exc))
                notif = None
        return notif

    def __update_notification(self, summary, message):
        """
         :param message: The message (body) that should be displayed.
         :type message:  String
         
        :todo: Replace single '<' characters by '&lt;' in a more reliable way!
        """
        if self.__pynotif_avail:
            message = message.replace("<", "&lt;")
            try:
                self.__notif.update(summary, message, self.__icon)
            except gobject.GError, exc:
                # Connection to notification-daemon failed 
                self.logger.warning(_("Connection to notification-daemon failed: %s.") % str(exc))
                self.__notif = None


def main(argument, options):
    if argument == __START:
        _msg = _("Backup process is being started.")
    elif argument == __FINISH:
        _msg = _("Backup process finished.")
    elif argument == __ERROR:
        _msg = _("An error occured during the backup.")
    else:
        raise ValueError("Unknown argument given.")
    
    _level = logging.ERROR
    if options.verbose is True:
        _level = logging.DEBUG
    
    logging.basicConfig(level=_level)
    logger = logging.getLogger()

    notifyd = PyNotify(logger=logger, domain=_APPLICATION_LONG, icon=get_resource_file(_ICON))
    
    if argument == __ERROR:
        notifyd._notify_error(_APPLICATION_LONG, _msg)
    else:
        notifyd._notify_info(_APPLICATION_LONG, _msg)


if __name__ == "__main__":
    excode = 0
    (arg, options) = parse_commandline()

    if options.pythonpath is not None:
        sys.path.append(options.pythonpath)

    from nssbackup.util import get_resource_dir
    from nssbackup.util import get_resource_file

    # i18n init
    locale_dir = get_resource_dir('locale')

    gettext.bindtextdomain(_APPLICATION, locale_dir)
    gettext.textdomain(_APPLICATION)

    try:
        main(arg, options)
    except Exception, error:
        print "Error in nssbackup-notify: %s" % str(error)
        excode = 3

    sys.exit(excode)
