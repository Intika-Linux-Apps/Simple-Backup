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

from nssbackup.util import nssbackup_dbus_support
import nssbackup.util as Util


class SBackupdSystrayGui(object):
    """This class is the graphical frontend.
    """
        
    def __init__(self, sbackupd_dbus_obj):
        if sbackupd_dbus_obj is None:
            raise ValueError("Given remote sbackupd_dbus_obj must be not None!")
        self._sbackupd_dbus_obj = sbackupd_dbus_obj
        self.__connect_signal_handlers()
        
        self.notification   = pynotify.Notification(" ",
                                                    " ",
        "file:///home/peer/programming/python/sbackup/sbackup-mod/sbackup.png")
        
        print "DIR notif:"
        print dir(self.notification)
        
        self.trayicon     = gtk.StatusIcon()
        self.window         = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.menu           = gtk.Menu()
        self.sbackupdamon = None
        self.mainloop = None
        self._blocking_factor = 20
        self._blocksize = 512
        self._total_size = "??"
        
    def __connect_signal_handlers(self):
        signal_handlers = { 'HelloSignal'   : self._hello_signal_handler,
                            'ExitSignal'    : self._exit_signal_handler,
                            'ProgressSignal': self._progress_signal_handler
                          }

        for _key in signal_handlers:
            _val = signal_handlers[_key]
            print "K: %s; V: %s" % (_key, _val)
            self._sbackupd_dbus_obj.connect_to_signal(_key, _val,
                            dbus_interface=nssbackup_dbus_support.DBUS_INTERFACE)
        
    def _hello_signal_handler(self, hello_string):
        msg = "Received signal (by connecting using remote object) and it says: " + hello_string
        print (msg)
        self.show_notif( msg )      

    def _exit_signal_handler(self, param):
        print "Received EXITSIGNAL"
        
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
        gobject.idle_add(self.on_exit)
    
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
        self.show_notif("Hello from About...")
            
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
        
    def _notify_backup_started(self):
        print "backup_started_notify"
        self.notification.close()
        self.notification.update("Simple Backup",
                                 "Backup in progress...",
        "file:///home/peer/programming/python/sbackup/sbackup-mod/sbackup.png")
        self.notification.set_urgency(pynotify.URGENCY_CRITICAL)
        self.notification.set_timeout(5000) # 10 seconds
        self.notification.attach_to_status_icon(self.trayicon)
        print "before notify show"
        self.notification.show()
        print "after notify show"

    def _notify_backup_finished(self, excode = None):
        print "backup_finished_notify"
        if excode is None:
            msg = "Backup finished!"
        else:
            msg = "Backup finished with exitcode %s!" % excode
        self.notification.close()
        self.notification.update("Simple Backup",
                                 msg,
        "file:///home/peer/programming/python/sbackup/sbackup-mod/sbackup.png")
        self.notification.set_urgency(pynotify.URGENCY_CRITICAL)
        self.notification.set_timeout(5000) # 10 seconds
        self.notification.attach_to_status_icon(self.trayicon)
        print "before notify show"
        self.notification.show()
        print "after notify show"
        
    def show_notif(self, a_msg):
        self.notification.close()
        self.notification.update("Simple Backup",
                                 a_msg,
        "file:///home/peer/programming/python/sbackup/sbackup-mod/sbackup.png")
        self.notification.set_urgency(pynotify.URGENCY_CRITICAL)
        self.notification.set_timeout(5000) # 10 seconds
        self.notification.attach_to_status_icon(self.trayicon)
        self.notification.show()
    
        
    def backup_finished(self, exitstate):
        print "Backup is finished!"
        self._notify_backup_finished(exitstate)
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
#        pass
        gobject.timeout_add(1000, self.on_init_timer)

        
    def main(self):
        self._init_ctrls()
        self._create_custom_events()
        self.trayicon.set_visible(True)

        self.mainloop = gobject.MainLoop()
        self.mainloop.run()

        print "back from gtk.main"
        self.menu.destroy()


class SBackupdGuiApp(object):
    
    def __init__(self, remote_sbackupd_dbus_obj):
        self._sbackup_dbus_obj = remote_sbackupd_dbus_obj
        
        self._systray_gui   = SBackupdSystrayGui(self._sbackup_dbus_obj)
#        self._dbus_service  = SBackupdGuiDBusService(self._systray_gui)
        
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
        remote_sbackupd_obj  = session_bus.get_object(nssbackup_dbus_support.DBUS_SERVICE,
                                             nssbackup_dbus_support.DBUS_OBJ_PATH)
        
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
