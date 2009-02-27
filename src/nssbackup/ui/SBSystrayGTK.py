#!/usr/bin/env python

usage = """Usage:
python example-service.py &
python example-client.py
python example-async-client.py
python example-client.py --exit-service
"""

# Copyright (C) 2004-2006 Red Hat Inc. <http://www.redhat.com/>
# Copyright (C) 2005-2007 Collabora Ltd. <http://www.collabora.co.uk/>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

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
import pynotify

from gettext import gettext as _

from nssbackup.util import dbus_support
import nssbackup.util as Util
from nssbackup.util.log import LogFactory



class SBackupdGuiDBusObject(dbus.service.Object):

    def __init__(self, session_bus, object_path, systray_gui_obj):
        dbus.service.Object.__init__(self, session_bus, object_path)
        self._session_bus   = session_bus
        self._systray_gui   = systray_gui_obj
    
    @dbus.service.method(dbus_support.DBUS_GUI_INTERFACE,
                         in_signature='s', out_signature='as')
    def HelloWorld(self, hello_message):
        """Take care: the reply might timeout!
        """
        print (str(hello_message))
#        self._systray_gui.err_msg(hello_message)
        gobject.idle_add(self._systray_gui.err_msg, hello_message)
        return ["Hello", " from sbackup_client_systray.py", "with unique name",
                self._session_bus.get_unique_name()]

#    @dbus.service.method(dbus_support.DBUS_GUI_INTERFACE,
#                         in_signature='', out_signature='')
#    def RaiseException(self):
#        raise DemoException('The RaiseException method does what you might '
#                            'expect')

    @dbus.service.method(dbus_support.DBUS_GUI_INTERFACE,
                         in_signature='', out_signature='(ss)')
    def GetTuple(self):
        return ("Hello Tuple", " from example-service.py")

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature='', out_signature='a{ss}')
    def GetDict(self):
        return {"first": "Hello Dict", "second": " from example-service.py"}

    @dbus.service.method(dbus_support.DBUS_GUI_INTERFACE,
                         in_signature='', out_signature='')
    def Exit(self):
        print "SBackupdGuiDBusService: Exit was called."
#        if self._systray_gui:
#            self._systray_gui.quit()


class SBackupdGuiDBusService(object):
    """
    :todo: We need a listener to the `Exit` signal!
    
    """
    def __init__(self, systray_gui_obj):
        print "CONSTRUCTOR 'SBackupdGuiDBusService'"
        self._session_bus   = None
        self._dbus_service  = None
        self._export_obj    = None
        self._initialize_dbus_service(systray_gui_obj)
                        
    def _initialize_dbus_service(self, systray_gui_obj):
        print "SBackupdGuiDBusService._initialize_dbus_service"
        if systray_gui_obj is None:
            raise ValueError("ERR: The systray gui object must not be None!")
        
        self._session_bus = dbus.SessionBus()
        self._dbus_service = dbus.service.BusName(\
                                      dbus_support.DBUS_GUI_SERVICE,
                                      self._session_bus)
        self._export_obj = SBackupdGuiDBusObject(self._session_bus,
                                      dbus_support.DBUS_GUI_OBJ_PATH,
                                      systray_gui_obj)

    def get_exported_dbus_obj(self):
        if self._export_obj is None:
            raise ValueError("Exported object must be not None!")
        return self._export_obj


class PyNotifyMixin(object):
    """Mix-in class that provides the displaying of notifications using the
    pynotify module. The notifications use the icon 'nssbackup32x32.png'.
    
    :todo: This is not the right place for the definition!
    :todo: It would be more general if we give the icon to use as parameter!
    
    """
    def __init__(self, logger, trayicon=None):
        """Default constructor.
        
        :param logger: Instance of logger to be used.
        
        :todo: The notification domain should be retrieved from a central place!
        
        """
        self.__logger = logger
        self.__trayicon = trayicon

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
        self.__notify_new(profilename, message, mode="warning")

    def _notify_error(self, profilename, message):
        """Shows up a pop-up window to inform the user that an error occured.
        Such error notifications are emphasized and must be closed manual. The
        notifications support mark-up.

         :param message: The message (body) that should be displayed.
         :type message:  String
         
        """
        self.__notify_new(profilename, message, mode="critical")
                     
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
            ico = Util.getResource("nssbackup32x32.png")
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
            ico = Util.getResource("nssbackup32x32.png")
            try:
                self.__notif.update(
                                "NSsbackup [%s]" % profilename, message, ico)
            except gobject.GError, exc:
                 # Connection to notification-daemon failed 
                 self.logger.warning("Connection to notification-daemon "\
                                    "failed: " + str(exc))
                 self.__notif = None


class SBackupdSystrayGui(PyNotifyMixin):
    """This class is the graphical frontend.
    """

    def __init__(self, sbackupd_dbus_obj):
        if sbackupd_dbus_obj is None:
            raise ValueError("Given remote sbackupd_dbus_obj must be not None!")
        
        self.logger            = LogFactory.getLogger()        
        
        self._sbackupd_dbus_obj = sbackupd_dbus_obj
        self.__connect_signal_handlers()
        
        ico = Util.getResource("nssbackup32x32.png")
        self.notification   = pynotify.Notification(" ", " ", ico)
        
#        print "DIR notif:"
#        print dir(self.notification)
        
        self.trayicon     = gtk.StatusIcon()
        self.window         = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.menu           = gtk.Menu()
#        self._mainloop = None
        self._blocking_factor = 20
        self._blocksize = 512
        self._total_size = "??"
        
        self.__error_present = False
        
        super(SBackupdSystrayGui, self).__init__(self.logger, self.trayicon)
        
    def __connect_signal_handlers(self):
        """Binds the signals to their corresponding handler methods.
        
        """
        signal_handlers = {
                'nssbackup_started_signal'  : self._started_signal_handler,
                'nssbackup_finished_signal' : self._finished_signal_handler,
                'nssbackup_error_signal'    : self._error_signal_handler,
                'nssbackup_exit_signal'     : self._exit_signal_handler,
                'nssbackup_progress_signal' : self._progress_signal_handler
                          }
        
        for _key in signal_handlers:
            _val = signal_handlers[_key]
            print "K: %s; V: %s" % (_key, _val)
            self._sbackupd_dbus_obj.connect_to_signal(_key, _val,
                            dbus_interface=dbus_support.DBUS_INTERFACE)
        
    def _started_signal_handler(self, profile):
        msg = _("Starting backup Session")
        print (msg)
        self._notify_info(profile, msg)

    def _finished_signal_handler(self, profile):
        msg = _("Ending Backup Session")
        print (msg)
        self._notify_info(profile, msg)

    def _error_signal_handler(self, profile, error):
        self.__error_present = True
        msg = _("An error occurred: ") + error
        print (msg)
        self._notify_error(profile, msg)

    def _exit_signal_handler(self):
        print "GUI: Received EXITSIGNAL"
        if not self.__error_present:
            self.quit()
        
    def _progress_signal_handler(self, checkpoint):
        try:
            self._checkpoint = int(checkpoint)
            _done = self._checkpoint * self._blocking_factor * self._blocksize
        except:
            _done = checkpoint
        _msg = "Simple Backup\nBackup in progress: %s byte of %s byte" % (_done, self._total_size)
        self.trayicon.set_tooltip(_msg)
    
    def delete_cb(self, widget, event, data = None):
        if data:
            data.set_blinking(True)
        return False
    
    def quit(self):
#        gobject.idle_add(self.on_exit)
        gobject.timeout_add(5000, self.on_exit)
    
    def quit_cb(self, widget, data = None):
        if data:
            data.set_visible(False)
            self.quit()
            
    def popup_menu_cb(self, widget, button, time, data = None):
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, None, 3, time)
            
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
            about.set_logo(gtk.gdk.pixbuf_new_from_file("/home/peer/programming/python/sbackup/sbackup-mod/sbackup.png"))
            about.run()
            about.destroy()
        except:
            print "ERR: exception while showing AboutDialog."
        self._notify_error("TESTPROFILE", "Hello from About...")
            
    def on_popup_new_clicked(self, widget, data = None):
        self.err_msg("<tt>Hello from the menu.</tt>")
        
    def on_init_timer(self, *args):
        print "on_init_timer was called."
        print "but did nothing."
        return False

    def on_exit(self, *args):
        print "on_exit was called."
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
        
#    def _notify_backup_started(self):
#        print "backup_started_notify"
#        self.notification.close()
#        self.notification.update("Simple Backup",
#                                 "Backup in progress...",
#        "file:///home/peer/programming/python/sbackup/sbackup-mod/sbackup.png")
#        self.notification.set_urgency(pynotify.URGENCY_CRITICAL)
#        self.notification.set_timeout(5000) # 10 seconds
#        self.notification.attach_to_status_icon(self.trayicon)
#        print "before notify show"
#        self.notification.show()
#        print "after notify show"
#
#    def _notify_backup_finished(self, excode = None):
#        print "backup_finished_notify"
#        if excode is None:
#            msg = "Backup finished!"
#        else:
#            msg = "Backup finished with exitcode %s!" % excode
#        self.notification.close()
#        self.notification.update("Simple Backup",
#                                 msg,
#        "file:///home/peer/programming/python/sbackup/sbackup-mod/sbackup.png")
#        self.notification.set_urgency(pynotify.URGENCY_CRITICAL)
#        self.notification.set_timeout(5000) # 10 seconds
#        self.notification.attach_to_status_icon(self.trayicon)
#        print "before notify show"
#        self.notification.show()
#        print "after notify show"
#        
#    def show_notif(self, a_msg):
#        self.notification.close()
#        self.notification.update("Simple Backup",
#                                 a_msg,
#        "file:///home/peer/programming/python/sbackup/sbackup-mod/sbackup.png")
#        self.notification.set_urgency(pynotify.URGENCY_CRITICAL)
#        self.notification.set_timeout(5000) # 10 seconds
#        self.notification.attach_to_status_icon(self.trayicon)
#        self.notification.show()
    
        
    def backup_finished(self, exitstate):
        print "Backup is finished!"
#        self._notify_backup_finished(exitstate)
        gobject.timeout_add(5000, self.on_exit)

        
    def _init_ctrls(self):
        menuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        menuItem.connect('activate', self.on_about_clicked, self.trayicon)
        self.menu.append(menuItem)

        menuItem = gtk.ImageMenuItem(gtk.STOCK_NEW)
        menuItem.connect('activate', self.on_popup_new_clicked, self.trayicon)
        self.menu.append(menuItem)
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate', self.quit_cb, self.trayicon)
        self.menu.append(menuItem)        

        self.trayicon.set_from_file(Util.getResource("nssbackup-tray.png"))
#        self.trayicon.set_from_file("sbackup.png")

        self.trayicon.set_tooltip("Simple Backup Frontend")
        self.trayicon.connect('popup-menu', self.popup_menu_cb, self.menu)
        self.trayicon.set_blinking(False)
        

    def _create_custom_events(self):
        pass
#        gobject.timeout_add(1000, self.on_init_timer)

        
    def main(self):
        self._init_ctrls()
        self._create_custom_events()
        self.trayicon.set_visible(True)

        self.mainloop = gobject.MainLoop()
        self.mainloop.run()

        print "back from gtk.main"
        self.menu.destroy()


class SBackupdGuiApp(object):
    """GUI for listen to the backup daemon. It launches a DBus service. 
    """
    
    def __init__(self, remote_sbackupd_dbus_obj):
        self._sbackup_dbus_obj = remote_sbackupd_dbus_obj
        
        self._systray_gui   = SBackupdSystrayGui(self._sbackup_dbus_obj)
        self._dbus_service  = SBackupdGuiDBusService(self._systray_gui)
        
    def main(self):
        self._systray_gui.main()
        

def main(args):
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    pynotify_avail = True
    dbus_avail = True
    gtk_avail = True

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
    
    try:
        session_bus = dbus.SessionBus()
        remote_sbackupd_obj  = session_bus.get_object(dbus_support.DBUS_SERVICE,
                                             dbus_support.DBUS_OBJ_PATH)
        
    except dbus.DBusException, exc:
        print "ERR: %s" % exc
        dbus_avail = False
        
    if dbus_avail:
        print "INFO: DBus is available."
    else:
        print "INFO: NO DBus available!"
    
    if gtk_avail:
        print "GTK is available."
    else:
        print "No Desktop environment available!"
        
    if gtk_avail and dbus_avail and pynotify_avail:
        sbdgui = SBackupdGuiApp( remote_sbackupd_obj )
        sbdgui.main()
