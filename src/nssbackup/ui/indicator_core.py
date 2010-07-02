#    Simple Backup - Indicator application (status icon)
#                    core implementation
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


import os
import time

from gettext import gettext as _

import gobject
import dbus.mainloop.glib
import gtk


from nssbackup.pkginfo import Infos
from nssbackup import util
from nssbackup.util import dbus_support
from nssbackup.util.log import LogFactory
from nssbackup.util import constants
from nssbackup.util import system
from nssbackup.util import lock
from nssbackup.util import exceptions
from nssbackup.ui import misc


class INotifyMixin(object):
    """Mix-in class that provides the displaying of notifications using the
    pynotify module. The notifications use the icon 'nssbackup32x32.png'.
    
    :todo: It would be more general if we give the icon to use as parameter!    
    """
    def __init__(self, logger, iconfile, trayicon = None):
        pass

    def _notify_info(self, profilename, message):
        """Shows up a pop-up window to inform the user. The notification
        supports mark-up.        

         :param message: The message (body) that should be displayed.
         :type message:  String
         
        """
        raise NotImplementedError

    def _notify_warning(self, profilename, message):
        """Shows up a pop-up window to inform the user. The notification
        supports mark-up.        

         :param message: The message (body) that should be displayed.
         :type message:  String
         
        """
        raise NotImplementedError

    def _notify_error(self, profilename, message):
        """Shows up a pop-up window to inform the user that an error occured.
        Such error notifications are emphasized and must be closed manual. The
        notifications support mark-up.

         :param message: The message (body) that should be displayed.
         :type message:  String
         
        """
        raise NotImplementedError


class PyNotifyMixin(INotifyMixin):
    """Mix-in class that provides the displaying of notifications using the
    pynotify module. The notifications use the icon 'nssbackup32x32.png'.
    
    :todo: It would be more general if we give the icon to use as parameter!    
    """
    def __init__(self, logger, iconfile, trayicon = None):
        """Default constructor.
        
        :param logger: Instance of logger to be used.
        
        :todo: The notification domain should be retrieved from a central place!
        
        """
        INotifyMixin.__init__(self, logger, iconfile, trayicon)
        self.__logger = logger
        self.__trayicon = trayicon
        self.__iconfile = iconfile

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
            if self.__pynotif_mod.init(constants.NOTIFICATION_DOMAIN):
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
         
        :note: Comply with Ubuntu Notification Guidelines (no actions, no permanent notifications) 
        """
        if self.__pynotif_avail:
            notif = self.__get_notification(profilename, message)
            if isinstance(notif, self.__pynotif_mod.Notification):
                try:
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
            title = self.__get_notification_title(profilename)

            try:
                notif = self.__pynotif_mod.Notification(title, message, self.__iconfile)
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
            title = self.__get_notification_title(profilename)

            try:
                self.__notif.update(title, message, self.__iconfile)
            except gobject.GError, exc:
                # Connection to notification-daemon failed 
                self.logger.warning("Connection to notification-daemon "\
                                    "failed: " + str(exc))
                self.__notif = None

    def __get_notification_title(self, profilename):
        title = Infos.NAME
        if profilename != "":
            title += "\n[%s]" % profilename
        return title


class SBackupdIndicatorBase(INotifyMixin):

    def __init__(self, indicator_hdl):
        if not isinstance(indicator_hdl, SBackupdIndicatorHandler):
            raise TypeError("Parameter of type `SBackupdIndicatorHandler` expected.")
        self.logger = LogFactory.getLogger()
        INotifyMixin.__init__(self, logger = self.logger, iconfile = None, trayicon = None)

        self._indicator_hdl = indicator_hdl
        self._mainloop = gobject.MainLoop()

        self._indicator = None

        self._exit = False
#TODO: Collect required named dialogs in dictionary.
        self._targetnotfound_dialog = None
        self._cancel_dialog = None
        self._current_dialogs = []
        self._menu = gtk.Menu()
        self._menuitems = {}

        self._connect_dbus_signal_handlers()
        self._init_dbus_check_timer()
        self._init_autoexitcheck_timer()

    def _notify_info(self, profilename, message):
        raise NotImplementedError

    def _notify_warning(self, profilename, message):
        raise NotImplementedError

    def _notify_error(self, profilename, message):
        raise NotImplementedError

    def _init_autoexitcheck_timer(self):
        if self._indicator_hdl.get_keep_alive() is False:
            gobject.timeout_add_seconds(constants.AUTOEXIT_CHECK_INTERVAL_SECONDS,
                                self._autoexitcheck)

    def _init_autoexit_timer(self):
        gobject.timeout_add_seconds(constants.AUTOEXIT_TIMEOUT_SECONDS,
                            self._autoexit)

    def _init_dbus_check_timer(self):
        gobject.timeout_add_seconds(constants.DBUS_CHECK_INTERVAL_SECONDS, self._dbus_check)

    def _init_dbus_reconnect_timer(self):
        gobject.timeout_add_seconds(constants.DBUS_RECONNECT_INTERVAL_SECONDS, self._dbus_reconnect)


    def _build_menu(self):
        _status_msg = self._indicator_hdl.get_unknown_menu_label()
        _menuitems = ({ "name"      : "title",
                        "title"     : "Simple Backup",
                        "type"      : "MenuItem",
                        "sensitive" : True,
                        "handler"   : { "activate" : self.on_about_clicked }},

                      { "name"      : "show_windows",
                        "title"     : _("Show message windows"),
                        "type"      : "MenuItem",
                        "sensitive" : True,
                        "handler"   : { "activate" : self.on_showdialogs_clicked }},

                      { "name"      : "separator_1",
                        "title"     : None,
                        "type"      : "SeparatorMenuItem",
                        "sensitive" : None,
                        "handler"   : None },

                      { "name"      : "profile",
                        "title"     : _status_msg["profile"],
                        "type"      : "MenuItem",
                        "sensitive" : False,
                        "handler"   : None },

                      { "name"      : "size_of_backup",
                        "title"     : _status_msg["size_of_backup"],
                        "type"      : "MenuItem",
                        "sensitive" : False,
                        "handler"   : None },

                      { "name"      : "progress",
                        "title"     : _status_msg["progress"],
                        "type"      : "MenuItem",
                        "sensitive" : False,
                        "handler"   : None },

                      { "name"      : "remaining_time",
                        "title"     : _status_msg["remaining_time"],
                        "type"      : "MenuItem",
                        "sensitive" : False,
                        "handler"   : None },

                      { "name"      : "separator_2",
                        "title"     : None,
                        "type"      : "SeparatorMenuItem",
                        "sensitive" : None,
                        "handler"   : None },

                      { "name"      : "cancel",
                        "title"     : _("Cancel Backup"),
                        "type"      : "MenuItem",
                        "sensitive" : False,
                        "handler"   : { "activate" : self.on_cancel_clicked }}
                     )

        for _item in _menuitems:
            if _item["type"] == "MenuItem":
                _menuitem = gtk.MenuItem(_item["title"])

                if _item["handler"] is not None:
                    for _signal in _item["handler"]:
                        _menuitem.connect(_signal, _item["handler"][_signal])

                _menuitem.set_sensitive(_item["sensitive"])
                self._menu.append(_menuitem)
                self._menuitems[_item["name"]] = _menuitem

            elif _item["type"] == "SeparatorMenuItem":
                _sep = gtk.SeparatorMenuItem()
                self._menu.append(_sep)
                self._menuitems[_item["name"]] = _sep

            else:
                raise ValueError("Unknown item type '%s'." % _item["type"])


    def _set_menuitems_status(self, func, *args):
        _status_msg = func(*args)
        for _item in _status_msg:
            _label = _status_msg[_item]
            self._menuitems[_item].set_label(_label)

    def _set_menuitems_status_finished(self):
        self._set_menuitems_status(self._indicator_hdl.get_finished_menu_label)

    def _set_menuitems_status_unknown(self):
        self._set_menuitems_status(self._indicator_hdl.get_unknown_menu_label)

    def _set_menuitems_status_canceled(self):
        self._set_menuitems_status(self._indicator_hdl.get_canceled_menu_label)

    def _set_menuitems_status_progress(self, checkpoint):
        self._set_menuitems_status(self._indicator_hdl.get_progress_menu_label, checkpoint)

    def _connect_dbus_signal_handlers(self):
        """Binds DBus signals to their corresponding handler methods.        
        """
        self._indicator_hdl.connect_dbus_event_signal(self.dbus_event_signal_hdl)
        self._indicator_hdl.connect_dbus_error_signal(self.dbus_error_signal_hdl)
        self._indicator_hdl.connect_dbus_progress_signal(self.dbus_progress_signal_hdl)
        self._indicator_hdl.connect_dbus_targetnotfound_signal(self.dbus_targetnotfound_signal_hdl)
        self._indicator_hdl.connect_dbus_alreadyrunning_signal(self.dbus_alreadyrunning_signal_hdl)
        self._indicator_hdl.connect_dbus_exit_signal(self.dbus_exit_signal_hdl)

    def _dbus_check(self):
        _res = True
        if self._exit is False:
            self._indicator_hdl.test_dbus_validity()
            if not self._indicator_hdl.is_dbus_valid():
                self._notify_info(profilename = "", message = _("Connection to D-Bus service lost."))

                self._set_menuitems_status_unknown()
                self._menuitems["cancel"].set_sensitive(False)

                self._indicator_hdl.dbus_reconnect()
                self._indicator_hdl.test_dbus_validity()
                if self._indicator_hdl.is_dbus_valid():    # re-connection successful?                    
                    self._connect_dbus_signal_handlers()
#TODO: get new values here!
                else:
                    self._init_dbus_reconnect_timer()
                    _res = False
        return _res

    def _dbus_reconnect(self):
        _res = True
        if self._exit is False:    # do not re-connect when quit was already called
            self._indicator_hdl.test_dbus_validity()
            if self._indicator_hdl.is_dbus_valid():
                _res = False    # already re-connected
            else:
                self._indicator_hdl.dbus_reconnect()
                self._indicator_hdl.test_dbus_validity()
                if self._indicator_hdl.is_dbus_valid():
                    self.logger.info("re-connection was successful")
                    self._connect_dbus_signal_handlers()
                    # get new values here
                    self._init_dbus_check_timer()
                    _res = False
        return _res

    def _autoexitcheck(self):
        """
        Conditions for autoexit:
        * no dbus avail
        * no backup in progress
        * timeout
        """
        assert self._indicator_hdl.get_keep_alive() is False
        _res = True
        self._indicator_hdl.test_dbus_validity()
        if self._indicator_hdl.is_dbus_valid() is False:
            _running = system.proc_exists(processname = constants.BACKUP_COMMAND)
            if _running is False:
                _res = False
                self._init_autoexit_timer()
        return _res

    def _autoexit(self):
        """
        Conditions for autoexit:
        * no dbus avail
        * no backup in progress
        * timeout
        """
        assert self._indicator_hdl.get_keep_alive() is False
        _res = False
        self._indicator_hdl.test_dbus_validity()
        _running = system.proc_exists(processname = constants.BACKUP_COMMAND)
        if (self._indicator_hdl.is_dbus_valid() is False) and (_running is False):
            if (not self._indicator_hdl.is_error_present()) and\
               (not self._indicator_hdl.is_warning_present()):
                self._notify_info(profilename = "",
                                  message = _("No backup in progress and connection to D-Bus service lost. Simple Backup Indicator is being terminated."))
                gobject.idle_add(self._on_exit)
            else:
                _res = True
        else:
            self._init_autoexitcheck_timer()
        return _res

    def _set_cancel_sensitive(self, sensitive):
        self._menuitems["cancel"].set_sensitive(sensitive)

    def _show_showdialogs_menuitem(self):
        if len(self._current_dialogs) > 0:
            self._menuitems["show_windows"].show()
            self._menuitems["show_windows"].set_sensitive(True)
        else:
            self._menuitems["show_windows"].hide()
            self._menuitems["show_windows"].set_sensitive(False)

    def dbus_event_signal_hdl(self, event, urgency):
        """Method which handles event signals over D-Bus. 
        
        :todo: Implement methods for setting 'finished status' etc. (set menu, disable cancel, hide show
               messages, set icon...
        """
        msg = ""

        if event == 'prepare':
            self._set_menuitems_status_unknown()
            self._set_cancel_sensitive(sensitive = False)

        elif event == 'start':
            msg = _("Starting backup Session")
            self.set_status_to_normal()
            self._set_cancel_sensitive(sensitive = True)
            self._indicator_hdl.backup_started()

        elif event == 'commit':
            self._set_cancel_sensitive(sensitive = True)

        elif event == 'finish':
            msg = _("Ending Backup Session")

            if self._cancel_dialog is not None:
                self._cancel_dialog.destroy()
            self._set_menuitems_status_finished()
            self._set_cancel_sensitive(sensitive = False)
            self.set_status_to_finished()

        elif event == 'backup-canceled':
            self._set_menuitems_status_canceled()
            self._set_cancel_sensitive(sensitive = False)

        elif event == 'needupgrade':
            msg = _("There are snapshots with old snapshot format."\
                    " Please upgrade these if you want to use them.")
        else:
            self.logger.warning(_("Unknown D-Bus event `%s` received.") % (event))

        if msg != "":
            profile = self._indicator_hdl.get_profilename()
            self._notify(urgency, profile, msg)

    def set_status_to_normal(self):
        raise NotImplementedError

    def set_status_to_attention(self):
        raise NotImplementedError

    def set_status_to_finished(self):
        raise NotImplementedError

    def _add_dialog_to_showlist(self, dialog):
        if not isinstance(dialog, gtk.Window):
            raise TypeError("GTK window expected.")
        if dialog not in self._current_dialogs:
#            raise ValueError("Given dialog is already stored.")
            self._current_dialogs.append(dialog)
        self._show_showdialogs_menuitem()

    def _remove_dialog_from_showlist(self, dialog):
        if not isinstance(dialog, gtk.Window):
            raise TypeError("GTK window expected.")
        if dialog in self._current_dialogs:
            self._current_dialogs.remove(dialog)
        self._show_showdialogs_menuitem()

    def dbus_targetnotfound_signal_hdl(self):
        self.set_status_to_attention()
        msg = self._indicator_hdl.prepare_targetnotfound_handling()

        assert self._targetnotfound_dialog is None
        self._targetnotfound_dialog = misc.msgdialog_standalone(message_str = "",
                                                                 msgtype = gtk.MESSAGE_ERROR,
                                                                 boxtitle = Infos.NAME,
                                                                 buttons = gtk.BUTTONS_NONE,
                                                                 sticky = True)
        self._targetnotfound_dialog.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                 _("Try again"), gtk.RESPONSE_OK)

        gobject.timeout_add_seconds(constants.TIMEOUT_RETRY_TARGET_CHECK_SECONDS,
                                    self._targetnotfound_dialog_destroy)
        gobject.timeout_add_seconds(constants.ONE_SECOND,
                                    self._targetnotfound_timer, msg,
                                    constants.ONE_SECOND)

        msg = msg % self._indicator_hdl.get_targetnotfound_clock()

        self._targetnotfound_dialog.set_markup(msg)
        self._add_dialog_to_showlist(dialog = self._targetnotfound_dialog)
        result = self._targetnotfound_dialog.run()
        self._targetnotfound_dialog.destroy()
        self._remove_dialog_from_showlist(dialog = self._targetnotfound_dialog)
        self._targetnotfound_dialog = None

        if result == gtk.RESPONSE_OK:
            retry = constants.RETRY_TRUE
        else:
            retry = constants.RETRY_FALSE

        self._indicator_hdl.finish_targetnotfound_handling(retry)
        self.set_status_to_normal()

    def _targetnotfound_timer(self, msg, interval):
        self._indicator_hdl.decrease_targetnotfound_clock(interval)
        msg = msg % self._indicator_hdl.get_targetnotfound_clock()
        if self._targetnotfound_dialog is not None:
            self._targetnotfound_dialog.set_markup(msg)
        return self._indicator_hdl.get_targetnotfound_run_timer()

    def _targetnotfound_dialog_destroy(self):
        self._indicator_hdl.disable_targetnotfound_run_timer()
        if self._targetnotfound_dialog is not None:
            self._targetnotfound_dialog.destroy()
        return False

    def _notify(self, urgency, profile, message):
        if urgency == 'info':
            self._notify_info(profile, message)

        elif urgency == 'warning':
            self._notify_info(profile, message)
#            self.__indicator_hdl.set_warning_present(is_present = True)
#            self._notify_warning(profile, message)
        else:
            raise ValueError("Unknown urgency!")

    def dbus_error_signal_hdl(self, error):
        self.set_status_to_attention()
        msg = self._indicator_hdl.get_error_msg(error)
        self._show_errormsg(headline = msg[0], message = msg[1])
        self._indicator_hdl.set_error_present(is_present = False)
        self.set_status_to_normal()

    def dbus_progress_signal_hdl(self, checkpoint):
        self._set_menuitems_status_progress(checkpoint)

    def dbus_alreadyrunning_signal_hdl(self):
        self._notify_info(profilename = "",
                          message = _("Attempt of starting another instance of Simple Backup while this one is already running."))

    def on_showdialogs_clicked(self, *args): #IGNORE:W0613
        self.logger.debug("Show message windows")
        for dialog in self._current_dialogs:
            try:
                dialog.set_keep_above(True)
                dialog.present()
                dialog.set_keep_above(False)
            except AttributeError, error:
                self.logger.warning("Unable to present window: %s" % error)

    def on_about_clicked(self, *args): #IGNORE:W0613
        misc.show_about_dialog()

    def on_cancel_clicked(self, *args): #IGNORE:W0613
        """
        :note: We call another method indirectly from here in order NOT to block further
               handling of GUI events (namely 'click on show windows').
        """
        self._set_cancel_sensitive(sensitive = False)
        assert self._cancel_dialog is None
        gobject.idle_add(self._cancel_handler)

    def _cancel_handler(self):
        self._cancel_dialog = misc.msgdialog_standalone(message_str = \
                                    _("Do you really want to cancel the backup process of profile '%s'?") % \
                                    self._indicator_hdl.get_profilename(),
                                    msgtype = gtk.MESSAGE_QUESTION, boxtitle = Infos.NAME,
                                    buttons = gtk.BUTTONS_YES_NO,
                                    headline_str = _("Cancel running backup process?"))
        self._add_dialog_to_showlist(self._cancel_dialog)
        result = self._cancel_dialog.run()
        self._cancel_dialog.destroy()
        self._remove_dialog_from_showlist(self._cancel_dialog)
        self._cancel_dialog = None

        res = True
        if result == gtk.RESPONSE_YES:
            res = self._indicator_hdl.cancel_backup()
            self._set_cancel_sensitive(sensitive = False)
        else:
            self._set_cancel_sensitive(sensitive = True)

        if res is False:
            self._set_cancel_sensitive(sensitive = True)
            self._notify_info(profilename = self._indicator_hdl.get_profilename(),
                              message = _("Unable to cancel backup process."))

    def _show_errormsg(self, headline, message):
        errmsg = misc.errdialog_standalone(message_str = message,
                                          boxtitle = Infos.NAME,
                                          headline_str = headline,
                                          secmsg_str = "")
        self._add_dialog_to_showlist(dialog = errmsg)
        errmsg.run()
        errmsg.destroy()
        self._remove_dialog_from_showlist(dialog = errmsg)
        return False

    def dbus_exit_signal_hdl(self):
        """Handler for D-Bus exit signal.
        """
        self._on_exit()

    def _on_exit(self):
        """Internal method that is called on any exit request. Do not call `__terminate` directly.
        """
        if self._indicator_hdl.get_keep_alive() is True:
            self.logger.debug("Termination of indicator was requested though it is kept alive")
        else:
            self._exit = True
            if (not self._indicator_hdl.is_error_present()) and\
               (not self._indicator_hdl.is_warning_present()):
                gobject.timeout_add_seconds(constants.TIMEOUT_INDICATOR_QUIT_SECONDS, self._terminate)
            else:
                self.logger.debug("still errors present, not calling `__terminate`")

    def _terminate(self):
        """Internal method that actually quits the indicator.
        """
        self._mainloop.quit()
        return False

    def main(self):
        """The main method.
        """
        self._mainloop.run()
        self._menu.destroy()


class SBackupdIndicatorHandler(object):
    def __init__(self, sbackupd_dbus_obj, options):
        if not isinstance(sbackupd_dbus_obj, dbus_support.DBusClientFacade):
            raise TypeError("Given sbackupd_dbus_obj of type `DBusClientFacade` expected.")

        self.logger = LogFactory.getLogger()
        self.__options = options

        self._sbackupd_dbus_obj = sbackupd_dbus_obj

        self._space_required = constants.SPACE_REQUIRED_UNKNOWN
        self._target = constants.TARGET_UNKNOWN
        self._profile = constants.PROFILE_UNKNOWN

        self.__error_present = False
        self.__warning_present = False

        self._menuitem_status_tmpl = {"profile"        : _("Profile: %s"),
                                      "size_of_backup" : _("Size of backup: %s"),
                                      "progress"       : _("%.1f%% processed"),
                                      "remaining_time" : _("Remaining time: %s")}

        self._targetnotfound_run_timer = False
        self._targetnotfound_clock = 0
        self._starttime_backup = None
        self._time_est_total = 0

    def get_keep_alive(self):
        return self.__options.keep_alive

    def test_dbus_validity(self):
        self._sbackupd_dbus_obj.test_validity()

    def is_dbus_valid(self):
        _valid = self._sbackupd_dbus_obj.get_is_connected()
        return _valid

    def dbus_reconnect(self):
        self._sbackupd_dbus_obj.connect(silent = True)

    def connect_dbus_event_signal(self, handler):
        self._sbackupd_dbus_obj.connect_to_event_signal(handler)

    def connect_dbus_error_signal(self, handler):
        self._sbackupd_dbus_obj.connect_to_error_signal(handler)

    def connect_dbus_progress_signal(self, handler):
        self._sbackupd_dbus_obj.connect_to_progress_signal(handler)

    def connect_dbus_targetnotfound_signal(self, handler):
        self._sbackupd_dbus_obj.connect_to_targetnotfound_signal(handler)

    def connect_dbus_alreadyrunning_signal(self, handler):
        self._sbackupd_dbus_obj.connect_to_alreadyrunning_signal(handler)

    def connect_dbus_exit_signal(self, handler):
        self._sbackupd_dbus_obj.connect_to_exit_signal(handler)

    def __update_properties(self):
        self._profile = self._sbackupd_dbus_obj.get_profilename()
        self._target = self._sbackupd_dbus_obj.get_target()
        self._space_required = self._sbackupd_dbus_obj.get_space_required()

    def cancel_backup(self):
        """
        :todo: Return result of the cancellation!
        """
        res = True
        pid = self._sbackupd_dbus_obj.get_backup_pid()
        self.logger.info("PID of backup process being canceled: %s" % pid)
        if pid != constants.PID_UNKNOWN:
            term_script = util.get_resource_file(constants.TERMINATE_FILE)
            _ret = system.exec_command_returncode([term_script, str(pid)])
            if _ret != 0:
                self.logger.info("Unable to send signal to process %s" % pid)
                self.logger.info("Sending signal using gksu to process %s" % pid)
                descr = _("Cancel Backup")
                _ret = system.exec_command_returncode(["gksu", "--description", descr, term_script, str(pid)])
                if _ret != 0:
                    self.logger.warning(_("Sending signal using gksu to process %s failed") % pid)
                    res = False
        else:
            res = False
        return res

    def set_warning_present(self, is_present):
        self.__warning_present = is_present

    def set_error_present(self, is_present):
        self.__error_present = is_present

    def is_error_present(self):
        return self.__error_present

    def is_warning_present(self):
        return self.__warning_present

    def __set_retry_target_check(self, retry):
        if retry not in (constants.RETRY_UNKNOWN, constants.RETRY_FALSE,
                         constants.RETRY_TRUE):
            raise ValueError("Invalid value for retry target check.")
        self._sbackupd_dbus_obj.set_retry_target_check(retry)

    def enable_targetnotfound_run_timer(self):
        self._targetnotfound_run_timer = True

    def disable_targetnotfound_run_timer(self):
        self._targetnotfound_run_timer = False

    def get_targetnotfound_run_timer(self):
        return self._targetnotfound_run_timer

    def get_targetnotfound_error_msg(self):
        target = self._sbackupd_dbus_obj.get_target()
        msg = _("<b>Unable to find specified target directory</b>\n\nThe specified target directory '%s' was not found.\n\n") % target
        msg = msg + _("You can try to use the specified target again or cancel the profile execution. The profile execution is canceled automatically in %s seconds.")
        return msg

    def prepare_targetnotfound_handling(self):
        self.__update_properties()
        self.set_error_present(is_present = True)
        self.__set_retry_target_check(constants.RETRY_UNKNOWN)
        msg = self.get_targetnotfound_error_msg()

        self.enable_targetnotfound_run_timer()

        self._targetnotfound_clock = constants.TIMEOUT_RETRY_TARGET_CHECK_SECONDS
        return msg

    def finish_targetnotfound_handling(self, retry):
        self.__set_retry_target_check(retry)
        self.set_error_present(is_present = False)

    def decrease_targetnotfound_clock(self, interval):
        self._targetnotfound_clock -= interval

    def get_targetnotfound_clock(self):
        return self._targetnotfound_clock

    def get_profilename(self):
        if self._profile == constants.PROFILE_UNKNOWN:
            _res = _("unknown")
        else:
            _res = self._profile
        return _res

    def get_progress_menu_label(self, checkpoint):
        self.__update_properties()
        checkpoint = int(checkpoint)
        space_str = self.__get_space_required_str()

        # values valid?
        if (self._space_required > 0) and (checkpoint >= 0):
            _done = (checkpoint - 1) * constants.TAR_RECORDSIZE
            _percent = (float(_done) / float(self._space_required)) * 100.0

            _time_passed = time.time() - self._starttime_backup
            _time_est_total = (_time_passed / _percent) * 100.0
            _time_est_remain = _time_est_total - _time_passed

            if _time_est_remain < 60:
                _time_str = _("less than 1 minute")
            elif _time_est_remain < 120:
                _time_str = _("about 2 minutes")
            elif _time_est_remain < 180:
                _time_str = _("about 3 minutes")
            elif _time_est_remain < 240:
                _time_str = _("about 4 minutes")
            elif _time_est_remain < 300:
                _time_str = _("about 5 minutes")
            else:
                _time_str = _("about %.0f minutes") % (round((_time_est_remain / 60)))

            menu_msg = {"profile"        : self._menuitem_status_tmpl["profile"] % self.get_profilename(),
                        "size_of_backup" : self._menuitem_status_tmpl["size_of_backup"] % space_str,
                        "progress"       : self._menuitem_status_tmpl["progress"] % _percent,
                        "remaining_time" : self._menuitem_status_tmpl["remaining_time"] % _time_str}

        else: # values invalid, but something is in progress
            menu_msg = {"profile"        : self._menuitem_status_tmpl["profile"] % self.get_profilename(),
                        "size_of_backup" : self._menuitem_status_tmpl["size_of_backup"] % space_str,
                        "progress"       : _("In progress"),
                        "remaining_time" : self._menuitem_status_tmpl["remaining_time"] % _("unknown")}
        return menu_msg

    def get_finished_menu_label(self):
        self.__update_properties()
        space_str = self.__get_space_required_str()
        menu_msg = {"profile"        : self._menuitem_status_tmpl["profile"] % self.get_profilename(),
                    "size_of_backup" : self._menuitem_status_tmpl["size_of_backup"] % space_str,
                    "progress"       : self._menuitem_status_tmpl["progress"] % 100,
                    "remaining_time" : self._menuitem_status_tmpl["remaining_time"] % _("finished")}
        return menu_msg

    def get_unknown_menu_label(self):
        self.__update_properties()
        space_str = self.__get_space_required_str()
        menu_msg = {"profile"        : self._menuitem_status_tmpl["profile"] % self.get_profilename(),
                    "size_of_backup" : self._menuitem_status_tmpl["size_of_backup"] % space_str,
                    "progress"       : _("Progress: unknown"),
                    "remaining_time" : self._menuitem_status_tmpl["remaining_time"] % _("unknown")}
        return menu_msg

    def get_canceled_menu_label(self):
        self.__update_properties()
        space_str = self.__get_space_required_str()
        menu_msg = {"profile"        : self._menuitem_status_tmpl["profile"] % self.get_profilename(),
                    "size_of_backup" : self._menuitem_status_tmpl["size_of_backup"] % space_str,
                    "progress"       : _("Progress: canceled"),
                    "remaining_time" : self._menuitem_status_tmpl["remaining_time"] % _("finished")}
        return menu_msg

    def __get_space_required_str(self):
        if self._space_required > 0:
            space_str = util.get_humanreadable_size_str(size_in_bytes = self._space_required,
                                                        binary_prefixes = True)
        else:
            space_str = _("unknown")
        return space_str

    def get_error_msg(self, error):
        """Returns tuple of error message:
        1. Headline
        2. actual error message
        3. additional info
        """
        self.__update_properties()
        self.set_error_present(is_present = True)
        msg = (_("An error occurred"), error, "")
        return msg

    def backup_started(self):
        self.__update_properties()
        self._starttime_backup = time.time()
        self._time_est_total = 0


class SBackupdIndicatorApp(object):
    """GUI for listen to the backup daemon. It uses DBus service. 
    """
    def __init__(self, options):
        self.__options = options
        self.__indicator_gui = None
        self.__indicator_hdl = None
        self.__dbus = dbus_support.DBusClientFacade(constants.INDICATORAPP_NAME)
        self.__lock = lock.ApplicationLock(lockfile = constants.LOCKFILE_INDICATOR_FULL_PATH,
                                           processname = constants.INDICATORAPP_FILE, pid = os.getpid())

    def main(self, indicator_class):
        exitcode = constants.EXCODE_SUCCESS
        try:
            self.__lock.lock()
            self.__dbus.connect()    # establish D-Bus connection

            self.__indicator_hdl = SBackupdIndicatorHandler(self.__dbus, self.__options)
            self.__indicator_gui = indicator_class(self.__indicator_hdl)
            self.__indicator_gui.main()


        except exceptions.InstanceRunningError:
            exitcode = constants.EXCODE_INSTANCE_ALREADY_RUNNING
            print _("Another `Simple Backup Indicator` is already running.")

        except SystemExit, error:
            exitcode = error.code

        except KeyboardInterrupt:
            exitcode = constants.EXCODE_KEYBOARD_INTERRUPT

        finally:
            self.__dbus.quit()   # we connect here and we quit here
            self.__lock.unlock()

        return exitcode


def main(options, indicator_class):
    exitcode = constants.EXCODE_GENERAL_ERROR

    dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)
    gtk_avail = True
    try:
        gtk.init_check()
    except RuntimeError, error:
        gtk_avail = False
        print "Initialization of GTK+ failed: %s" % error

    if gtk_avail:
        sbdgui = SBackupdIndicatorApp(options)
        exitcode = sbdgui.main(indicator_class)

    return exitcode
