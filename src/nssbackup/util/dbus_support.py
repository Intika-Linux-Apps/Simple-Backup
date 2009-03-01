#    NSsbackup - support of DBus functionality
#
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
:mod:`dbus_support` --- support of DBus functionality
====================================================================

.. module:: dbus_support
   :synopsis: Provides support of DBus functionality
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>


If you want to launch it automatically, add a service file in
'peer@ayida:/usr/share/dbus-1/services$':

[D-BUS Service]
Name=org.launchpad.nssbackupService
Exec=/home/peer/programming/python/nssb/local_modified/0.2/src/nssbackup_dbus_service.py

"""

import time
import dbus

from nssbackup.util import exceptions
from nssbackup.util import log
from nssbackup.util import notifier


DBUS_SERVICE    = "org.launchpad.nssbackupService"
DBUS_OBJ_PATH   = "/org/launchpad/nssbackupService/nssbackupdDbusObject"
DBUS_INTERFACE  = "org.launchpad.nssbackupService.nssbackupdDbusInterface"
DBUS_EXCEPTION  = "org.launchpad.nssbackupdDbusException"

# this is for providing methods by the GUI service
DBUS_GUI_SERVICE    = "org.launchpad.nssbackupGuiService"
DBUS_GUI_OBJ_PATH   = "/org/launchpad/nssbackupService/nssbackupdDbusGuiObject"
DBUS_GUI_INTERFACE  = "org.launchpad.nssbackupService.nssbackupdDbusGuiInterface"
DBUS_GUI_EXCEPTION  = "org.launchpad.nssbackupdDbusGuiException"


class DBusConnection(object):
    """This class provides functionality for sending signals
    and calling methods over the dbus.
    
    The sender needs a dbus connection.
    
    The Dbus connection is only created on demand. In the case the user
    don't want to use it, no connection is created.
    
    """
    def __init__(self):
        """Default constructor.
        
        :param logger: Instance of logger to be used.
        
        """
        self.__logger = log.LogFactory.getLogger()
        # maybe it is better to retrieve the logger on demand?

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
        
        self._remote_obj  = self.__do_connect(DBUS_SERVICE,
                                              DBUS_OBJ_PATH)
        if self._remote_obj is not None:
            self._dbus_present = True

        # now for the gui service
        self._remote_gui  = self.__do_connect(DBUS_GUI_SERVICE,
                                              DBUS_GUI_OBJ_PATH)
        if self._remote_gui is not None:
            self._gui_present = True

        print "Dbus service available: %s" % self._dbus_present
        print "GUI service available: %s" % self._gui_present
            
    def emit_event_signal(self, event, urgency, profile):
        """Used for sending a generic event over the signal dbus.
        This includes informations and warnings.
        
        :param event: the actually processed event
        :param urgency: how urgent the message is
        :param profile: name of the current profile

        """
        ret_val = self._remote_obj.emit_nssbackup_event_signal(event, urgency,
                                        profile, dbus_interface=DBUS_INTERFACE)
        print "Returned value: %s" % ret_val
        return ret_val

    def emit_error_signal(self, profile, error):
        """Used for sending an error signal over the signal dbus.
        
        :param profile: name of the current profile
        :param error: error message to be passed
        
        """
        ret_val = self._remote_obj.emit_nssbackup_error_signal(profile, error,
                        dbus_interface=DBUS_INTERFACE)
            
        print "Returned value: %s" % ret_val
        return ret_val

    def call_method(self, msg):
        """Used for calling a method on the GUI Dbus.
        
        """
        print "call_method - msg: %s" % msg
        ret_val = self._remote_gui.HelloWorld(msg,
                        dbus_interface=DBUS_GUI_INTERFACE)
        print "returned: %s" % ret_val
    
    def exit(self):
        """
        :todo: Remove the `time.sleep` statement!
        
        """
        print "Sending 'Exit'"
    
        if self._remote_obj:
            # first send an `Exit` signal out
            self._remote_obj.emit_nssbackup_exit_signal(dbus_interface=\
                                                    DBUS_INTERFACE)
            time.sleep(2)
            # and then exit the service itself
            self._remote_obj.Exit(dbus_interface=\
                                  DBUS_INTERFACE)


class DBusNotifier(notifier.Observer):
    """Sends notifications as signals over the DBus.
    
    """
    def __init__(self):
        super(DBusNotifier, self).__init__()

        self.__state = None
        self.__urgency = None
        self.__profilename = None
        self.__recent_error = None

        self.__logger = log.LogFactory.getLogger()
        self.__dbus = None
        
    def initialize(self):
        self.__setup_dbus()
        
    def exit(self):
        self.__dbus.exit()
        
    def __setup_dbus(self):
        self.__dbus = DBusConnection()
        self.__dbus.connect()
        
    def update(self, subject):
        """Interface method for observer objects that is called by the
        observed subject. In the case of the `DBusNotifier` were
        notifications send over the bus.
         
        """
        print "OBSERVER UPDATE"
        self.__state = subject.get_state()
        self.__urgency = subject.get_urgency()
        self.__profilename = subject.get_profilename()
        self.__recent_error = subject.get_recent_error()
        
        self.__attempt_notify()

    def __attempt_notify(self):
        """Private helper method that actually tries to notify over
        the DBus about several events. This method decides what
        signals are send over the bus.
        
        :return: the value returned by the signal (usually True)
        
        """
        state = self.__state
        urgency = self.__urgency
        print "ATTEMPT NOTIFY - STATE: `%s` - Urgency: `%s`" % (state, urgency)
        
        ret_val = None
        if self.__dbus is not None:
            if state in ('start',
                         'commit',
                         'finish',
                         'needupgrade'):
                ret_val = self.__dbus.emit_event_signal(state, urgency,
                                                        self.__profilename)

            elif state == 'error':
                ret_val = self.__dbus.emit_error_signal(self.__profilename,
                                                        str(self.__recent_error))
    
            else:
                raise ValueError("STATE UNSUPPORTED (%s)" % state)
                
        print "Returned value: %s" % ret_val
        return ret_val
