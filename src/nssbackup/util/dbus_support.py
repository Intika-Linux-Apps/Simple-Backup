#    NSsbackup - support of DBus functionality
#
#   Copyright (c)2008-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
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

import os
import time
import dbus

from nssbackup.util import log
from nssbackup.util import notifier


DBUS_EXCEPTION = "org.launchpad.nssbackupdDbusException"
DBUS_SERVICE = "org.launchpad.nssbackupService"
DBUS_OBJ_PATH = "/nssbackupdDbusObject"
DBUS_INTERFACE = "org.launchpad.nssbackupService.nssbackupdDbusInterface"




class _DBusConnection(object):
    """This class provides functionality for sending signals
    and calling methods over the dbus.
    
    The sender needs a dbus connection.
    
    The Dbus connection is only created on demand. In the case the user
    don't want to use it, no connection is created.
    
    """
    def __init__(self, name):
        """Default constructor.
        
        :param logger: Instance of logger to be used.
        
        """
        self._logger = log.LogFactory.getLogger()
#TODO: maybe it is better to retrieve the logger on demand?

        self._name = name
        self._id = ""

        self._system_bus = None
        self._remote_obj = None
        self._dbus_present = False

#    def __del__(self):
#        self.quit()

    def is_dbus_present(self):
        return self._dbus_present

    def __do_connect(self, service, path):
        remote_obj = None
        timeout = 30        # seconds
        max_trials = 10     # number of max. trials
        dur = timeout / max_trials

        trials = 0          # done trials
        connecting = True
        while connecting:
            try:
                trials += 1
                print "Trying to connect to `%s` (trial no. %s)" % (service,
                                                                    trials)
                remote_obj = self._system_bus.get_object(service, path)
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
        """
        self._system_bus = dbus.SystemBus()

        self._remote_obj = self.__do_connect(DBUS_SERVICE,
                                             DBUS_OBJ_PATH)
        if self._remote_obj is not None:
            pid = os.getpid()
            self._id = self._remote_obj.register_connection(self._name, str(pid))
            print "INFO: Registered with id: %s" % self._id
            self._dbus_present = True
        print "INFO: Dbus service available: %s" % self._dbus_present

    def quit(self):
        """
        """
        if self._remote_obj:
            if self._id != "":
                if self._remote_obj.unregister_connection(self._id):
                    self._id = ""
                    print "INFO: Connection was successfully unregistered."
                else:
                    print "WARN: Unable to unregister connection (failed)."
            else:
                print "WARN: Unable to unregister connection (no client id)."


class DBusProviderConnection(_DBusConnection):
    """This class provides functionality for sending signals
    and calling methods over the dbus.
    
    The sender needs a dbus connection.
    
    The Dbus connection is only created on demand. In the case the user
    don't want to use it, no connection is created.
    
    """
    def __init__(self, name):
        """Default constructor.
        
        """
        _DBusConnection.__init__(self, name)

    def emit_event_signal(self, event, urgency, profile):
        """Used for sending a generic event over the signal dbus.
        This includes informations and warnings.
        
        :param event: the actually processed event
        :param urgency: how urgent the message is
        :param profile: name of the current profile

        """
        ret_val = self._remote_obj.emit_nssbackup_event_signal(event, urgency,
                                        profile, dbus_interface = DBUS_INTERFACE)
        print "Returned value: %s" % ret_val
        return ret_val

    def emit_error_signal(self, profile, error):
        """Used for sending an error signal over the signal dbus.
        
        :param profile: name of the current profile
        :param error: error message to be passed
        
        """
        ret_val = self._remote_obj.emit_nssbackup_error_signal(profile, error,
                        dbus_interface = DBUS_INTERFACE)

        print "Returned value: %s" % ret_val
        return ret_val

    def exit(self):
        """
        :todo: Remove the `time.sleep` statement!
        
        """
        print "Sending 'Exit'"

        if self._remote_obj:
            # first send an `Exit` signal out
            self._remote_obj.emit_nssbackup_exit_signal(dbus_interface = \
                                                    DBUS_INTERFACE)
            time.sleep(2)
#            # and then exit the service itself
#            self._remote_obj.Exit(dbus_interface = \
#                                  DBUS_INTERFACE)
            self.quit()


class DBusClientConnection(_DBusConnection):
    """This class provides functionality for sending signals
    and calling methods over the dbus.
    
    The sender needs a dbus connection.
    
    The Dbus connection is only created on demand. In the case the user
    don't want to use it, no connection is created.
    
    """
    def __init__(self, name):
        """Default constructor.
        
        """
        _DBusConnection.__init__(self, name)

    def connect_to_signal(self, signal, handler):
        self._remote_obj.connect_to_signal(signal, handler,
                            dbus_interface = DBUS_INTERFACE)



class DBusNotifier(notifier.Observer):
    """Sends notifications as signals over the DBus.
    It uses an instance of DBusConnection for signaling.
    
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
        self.__dbus = DBusProviderConnection("Simple Backup DBus Notifier")
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
