#    Simple Backup - Indicator application (status icon)
#                    targeting Ubuntu 10.04+
#
#   Copyright (c)2009-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
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


import sys
import os
import os.path


import gobject

import dbus
import dbus.service
import dbus.mainloop.glib


import pygtk
pygtk.require('2.0')

import gtk
#import gtk.gdk
import pynotify

import appindicator

from gettext import gettext as _

from nssbackup import util
from nssbackup.util import dbus_support
from nssbackup.util.log import LogFactory


_QUIT_TIMEOUT = 11000   # timeout in ms before quitting the indicator app


class PyNotifyMixin(object):
    """Mix-in class that provides the displaying of notifications using the
    pynotify module. The notifications use the icon 'nssbackup32x32.png'.
    
    :todo: This is not the right place for the definition!
    :todo: It would be more general if we give the icon to use as parameter!
    
    """
    def __init__(self, logger, trayicon = None):
        """Default constructor.
        
        :param logger: Instance of logger to be used.
        
        :todo: The notification domain should be retrieved from a central place!
        
        """
        self.__logger = logger
        self.__trayicon = trayicon

        # internal flag whether the notification module is usable
        self.__pynotif_avail = False

        # the pynotify module is stored in this variable
        self.__pynotif_mod = None

        # the current notification
        self.__notif = None

        # trying to initialize the notification module
        try:
            import pynotify
            self.__pynotif_mod = pynotify
            if self.__pynotif_mod.init("NSsbackup"):
                self.__pynotif_avail = True
            else:
                self.__pynotif_avail = False    # yes, this is insane!
                self.__logger.warning(_("there was a problem initializing the "\
                                        "pynotify module"))
        except ImportError, exc:
            self.__pynotif_avail = False
            self.__logger.warning(str(exc))


    def _notify_info(self, profilename, message):
        """Shows up a pop-up window to inform the user. The notification
        supports mark-up.        

         :param message: The message (body) that should be displayed.
         :type message:  String
         
        """
        if self.__pynotif_avail:
            if self.__notif is None:
                self.__notif = self.__get_notification(profilename, message)
            else:
                self.__update_notification(profilename, message)

            if isinstance(self.__notif, self.__pynotif_mod.Notification):
                try:
                    if self.__trayicon is not None:
                        self.__notif.attach_to_status_icon(self.__trayicon)
                    self.__notif.set_urgency(self.__pynotif_mod.URGENCY_LOW)
                    self.__notif.show()
                except gobject.GError, exc:
                    # Connection to notification-daemon failed 
                    self.logger.warning("Connection to notification-daemon "\
                                        "failed: " + str(exc))

    def _notify_warning(self, profilename, message):
        """Shows up a pop-up window to inform the user. The notification
        supports mark-up.        

         :param message: The message (body) that should be displayed.
         :type message:  String
         
        """
        self.__notify_new(profilename, message, mode = "warning")

    def _notify_error(self, profilename, message):
        """Shows up a pop-up window to inform the user that an error occured.
        Such error notifications are emphasized and must be closed manual. The
        notifications support mark-up.

         :param message: The message (body) that should be displayed.
         :type message:  String
         
        """
        self.__notify_new(profilename, message, mode = "critical")

    def __notify_new(self, profilename, message, mode):
        """Shows up a *new* pop-up window to inform the user that an error occured.
        Such error notifications are emphasized and must be closed manual. The
        notifications support mark-up.

         :param message: The message (body) that should be displayed.
         :type message:  String
         
        """
        if self.__pynotif_avail:
            notif = self.__get_notification(profilename, message)
            if isinstance(notif, self.__pynotif_mod.Notification):
                try:
                    notif.set_timeout(self.__pynotif_mod.EXPIRES_NEVER)
                    if self.__trayicon is not None:
                        notif.attach_to_status_icon(self.__trayicon)

                    if mode == "critical":
                        notif.set_urgency(self.__pynotif_mod.URGENCY_CRITICAL)
                    else:
                        notif.set_urgency(self.__pynotif_mod.URGENCY_NORMAL)
                    notif.show()
                except gobject.GError, exc:
                    # Connection to notification-daemon failed 
                    self.logger.warning("Connection to notification-daemon "\
                                        "failed: " + str(exc))

    def __get_notification(self, profilename, message):
        """Returns a notification object but does not display it. The
        notification supports mark-up. If notifications aren't supported
        the method returns None.
         
        :param message: The message (body) that should be displayed.
        :type message:  String
         
        :return: The created notification object or None
        :rtype: Notification or None
        
        :todo: Replace single '<' characters by '&lt;' in a more reliable way!\
               See function `gobject.markup_escape_text` for this.
        :todo: The header and the icon should be given as parameter to make
               this mix-in class more generic!
               
        """
        notif = None
        if self.__pynotif_avail:
            message = message.replace("<", "&lt;")
            ico = util.get_resource_file("nssbackup32x32.png")
            try:
                notif = self.__pynotif_mod.Notification(
                                "NSsbackup [%s]" % profilename, message, ico)
            except gobject.GError, exc:
                # Connection to notification-daemon failed 
                self.logger.warning("Connection to notification-daemon "\
                                    "failed: " + str(exc))
                notif = None
        return notif

    def __update_notification(self, profilename, message):
        """         
        :param message: The message (body) that should be displayed.
        :type message:  String
         
        :todo: Replace single '<' characters by '&lt;' in a more reliable way!
        :todo: The header and the icon should be given as parameter to make
               this mix-in class more generic!
               
        """
        if self.__pynotif_avail:
            message = message.replace("<", "&lt;")
            ico = util.get_resource_file("nssbackup32x32.png")
            try:
                self.__notif.update(
                                "NSsbackup [%s]" % profilename, message, ico)
            except gobject.GError, exc:
                # Connection to notification-daemon failed 
                self.logger.warning("Connection to notification-daemon "\
                                    "failed: " + str(exc))
                self.__notif = None


class SBackupdIndicator(PyNotifyMixin):
    """This class is the graphical frontend.
    """

    def __init__(self, sbackupd_dbus_obj):
        if not isinstance(sbackupd_dbus_obj, dbus_support.DBusClientConnection):
            raise TypeError("Given sbackupd_dbus_obj of type DBusClientConnection expected.")

        self.logger = LogFactory.getLogger()

        self._sbackupd_dbus_obj = sbackupd_dbus_obj
        print "INFO: in constructor: id: %s" % self._sbackupd_dbus_obj._id
        self.__connect_signal_handlers()

        ico = util.get_resource_file("nssbackup32x32.png")
        self.notification = pynotify.Notification(" ", " ", ico)

        self.__exit = False
        self._blocking_factor = 20
        self._blocksize = 512
        self._total_size = "??"

        self.__error_present = False
        self.__warning_present = False

        self.ind = appindicator.Indicator ("example-simple-client",
                                      "sbackup-normal-mono",
                                      appindicator.CATEGORY_APPLICATION_STATUS)

        self.ind.set_status (appindicator.STATUS_ACTIVE)
        self.ind.set_attention_icon ("system-restart-panel")

        # create a menu
        self.menu = gtk.Menu()

        self.menuitem_title = gtk.MenuItem("Simple Backup")
#        self.menuitem_done.connect('activate', self.on_about_clicked)
        self.menuitem_title.set_sensitive(False)
        self.menu.append(self.menuitem_title)
        self.menuitem_title.show()

        self.menuitem_done = gtk.MenuItem("Processed:\nunknown\nRemaining time: unknown")
        self.menuitem_done.connect('activate', self.on_about_clicked)
        self.menu.append(self.menuitem_done)
        self.menuitem_done.show()

        self.ind.set_menu(self.menu)

        PyNotifyMixin.__init__(self, logger = self.logger, trayicon = None)
        print "INFO: in constructor: id: %s" % self._sbackupd_dbus_obj._id

    def __connect_signal_handlers(self):
        """Binds the signals to their corresponding handler methods.
        
        """
        signal_handlers = {
                'nssbackup_event_signal'  : self._event_signal_handler,
                'nssbackup_error_signal'    : self._error_signal_handler,
                'nssbackup_exit_signal'     : self._exit_signal_handler,
                'nssbackup_progress_signal' : self._progress_signal_handler
                          }

        for _key in signal_handlers:
            _val = signal_handlers[_key]
            print "K: %s; V: %s" % (_key, _val)
            self._sbackupd_dbus_obj.connect_to_signal(_key, _val)

    def _event_signal_handler(self, event, urgency, profile):
        """
        
        """
        if event == 'start':
            msg = _("Starting backup Session")

        elif event == 'commit':
            msg = _("File list ready , Committing to disk")

        elif event == 'finish':
            msg = _("Ending Backup Session")
            self.ind.set_icon ("audacious-panel")

        elif event == 'needupgrade':
            msg = _("There are snapshots with old snapshot format."\
                    " Please upgrade these if you want to use them.")
        else:
            msg = _("Unknown event received")
        print (msg)
        self._notify(urgency, profile, msg)

    def _notify(self, urgency, profile, message):
        """
        """
        if urgency == 'info':
            self._notify_info(profile, message)

        elif urgency == 'warning':
            self.__warning_present = True
            self._notify_warning(profile, message)
        else:
            raise ValueError("Unknown urgency!")

    def _error_signal_handler(self, profile, error):
        self.__error_present = True
#        self.trayicon.set_from_file(util.get_resource_file("nssbackup-tray-mono-err.png"))

        self.ind.set_status (appindicator.STATUS_ATTENTION)

        msg = _("An error occurred: ") + error
        print (msg)
        self.err_msg(msg)
        self.__error_present = False

        self.ind.set_status (appindicator.STATUS_ACTIVE)

#        self.trayicon.set_from_file(util.get_resource_file("nssbackup-tray-mono.png"))

    def _exit_signal_handler(self):
        """
        @todo: Implement proper dialog and then quit if errors are present!
        """
        print "GUI: Received EXITSIGNAL in _exit_signal_handler"
        self.__exit = True
        if (not self.__error_present) and (not self.__warning_present):
            self.quit()

    def _progress_signal_handler(self, checkpoint):
        self._checkpoint = int(checkpoint)
        _done = (self._checkpoint - 1) * self._blocking_factor * self._blocksize
        _msg = "Processed: %s of %s" % (util.get_humanreadable_size_str(size_in_bytes = _done, binary_prefixes = True),
                                                   self._total_size)
        self.menuitem_done.set_label(_msg)

    def quit(self):
        print "SBackupIndicator quit"
        print "INFO: in quit: id: %s" % self._sbackupd_dbus_obj._id

#        gobject.idle_add(self.on_exit)
        gobject.timeout_add(_QUIT_TIMEOUT, self.on_exit)

    def on_about_clicked(self, *args):
        try:
            about = gtk.AboutDialog()
            about.set_name(_("Simple Backup Suite"))
            about.set_version("0.10.5-mod")
            about.set_comments(_("This is a user friendly backup solution for common desktop needs. The project was sponsored by Google during Google Summer of Code 2005 and mentored by Ubuntu."))
            about.set_copyright("Aigars Mahinovs <aigarius@debian.org>")
            about.set_translator_credits(_("translator-credits"))
            about.set_authors(["Aigars Mahinovs <aigarius@debian.org>",
                       "Jonh Wendell <wendell@bani.com.br>", "Oumar Aziz Ouattara <wattazoum@gmail.com>" ])
            about.set_website("http://sourceforge.net/projects/sbackup/")
#            about.set_logo(gtk.gdk.pixbuf_new_from_file("/home/peer/programming/python/sbackup/sbackup-mod/sbackup.png"))
            about.run()
            about.destroy()
        except Exception, error:
            print "ERR: exception while showing AboutDialog."
            print str(error)
            self._notify_error("TESTPROFILE", "Error in `About`:\n%s" % str(error))
#            
#    def on_popup_new_clicked(self, widget, data = None):
#        self.err_msg("<tt>Hello from the menu.</tt>")

    def on_exit(self, *args):
        print "SBackupIndicator on_exit was called."
        print "INFO: in on_exit: id: %s" % self._sbackupd_dbus_obj._id

        self.mainloop.quit()
        return False

    def err_msg(self, message):
        print "err_msg called."
        dialog = gtk.MessageDialog(parent = None,
                           type = gtk.MESSAGE_ERROR,
                           buttons = gtk.BUTTONS_OK,
                           flags = gtk.DIALOG_MODAL)
        dialog.set_markup(message)

        print "before dialog.run"
        result = dialog.run()
        print "after dialog.run; result: %s" % result
        dialog.destroy()
        print "leaving err_msg"
        return False


    def backup_finished(self, exitstate):
        print "Backup is finished!"
#        self._notify_backup_finished(exitstate)
        gobject.timeout_add(5000, self.on_exit)


#    def _init_ctrls(self):
#        menuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
#        menuItem.connect('activate', self.on_about_clicked, self.trayicon)
#        self.menu.append(menuItem)
#
#        menuItem = gtk.ImageMenuItem(gtk.STOCK_NEW)
#        menuItem.connect('activate', self.on_popup_new_clicked, self.trayicon)
#        self.menu.append(menuItem)
#        
#        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
#        menuItem.connect('activate', self.quit_cb, self.trayicon)
#        self.menu.append(menuItem)        
#
#        self.trayicon.set_from_file(Util.get_resource_file("nssbackup-tray-mono.png"))
##        self.trayicon.set_from_file("sbackup.png")
#
#        self.trayicon.set_tooltip("Simple Backup Frontend")
#        self.trayicon.connect('popup-menu', self.popup_menu_cb, self.menu)
#        self.trayicon.set_blinking(False)


    def main(self):
#        self._init_ctrls()

        self.mainloop = gobject.MainLoop()
#        print "SBSystrayGTK now running mainloop."
        self.mainloop.run()
        self.menu.destroy()


class SBackupdIndicatorApp(object):
    """GUI for listen to the backup daemon. It uses DBus service. 
    """
    def __init__(self):
        self._dbus = dbus_support.DBusClientConnection("Simple Backup Indicator Application")
        self._indicator_gui = None

    def main(self):
        # establish dbus connection
        self._dbus.connect()

        if self._dbus.is_dbus_present():
            self._indicator_gui = SBackupdIndicator(self._dbus)
            self._indicator_gui.main()

        else:
            print "No DBus service available."

        # we connect here and we quit here
        self._dbus.quit()


def main(args):
    _retc = 1
    pynotify_avail = True
    gtk_avail = True

    dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)

    try:
        pynotify.init('NSsbackup Notification')
    except:
        print sys.exc_info()
        pynotify_avail = False

    gtk_msg = "sucessfully initialized GTK+"
    try:
        gtk.init_check()
    except RuntimeError, exc:
        gtk_avail = False
        gtk_msg = "Initialization of GTK+ failed: %s" % exc
    print gtk_msg

    if gtk_avail:
        print "GTK is available."
    else:
        print "No Desktop environment available!"

#TODO: Move availability tests into App!
    if gtk_avail and pynotify_avail:
        sbdgui = SBackupdIndicatorApp()
        _retc = sbdgui.main()

    return _retc
