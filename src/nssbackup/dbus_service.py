#    Simple Backup - DBus System Service
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
#
# This code is based on examples published by
#   Red Hat Inc. <http://www.redhat.com/>
#   Collabora Ltd. <http://www.collabora.co.uk/>
#
"""
:mod:`nssbackup.dbus_service` -- DBus System Service
====================================================

.. module:: dbus_service
   :synopsis: Provides DBus System Service.
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

If you want to launch it automatically, add a service file in
'/usr/share/dbus-1/services':

[D-BUS Service]
Name=org.launchpad.nssbackupService
Exec=/home/username/programming/python/nssb/local_modified/0.2/src/nssbackup_dbus_service.py

"""

import uuid
import optparse

import gobject

import dbus.service
import dbus.mainloop.glib

from nssbackup.pkginfo import Infos
from nssbackup.util import dbus_support
from nssbackup.util.system import drop_privileges
from nssbackup.util.system import pid_exists


_UNREGISTER_DEAD_CONN_FREQ = 300000     # milliseconds


class SBDbusException(dbus.DBusException):
    _dbus_error_name = dbus_support.DBUS_EXCEPTION

#TODO: Use distinct objects!

class SBackupdDBusObject(dbus.service.Object):

    def __init__(self, system_bus, object_path, mainloop, keep_alive = False):
        dbus.service.Object.__init__(self, system_bus, object_path)
        self._system_bus = system_bus
        self._mainloop = mainloop
        self._listeners = {}
        self._keep_alive = keep_alive
        self._initialize_timer()

    def _initialize_timer(self):
        gobject.timeout_add(_UNREGISTER_DEAD_CONN_FREQ,
                            self._unregister_dead_connections)

    def _unregister_dead_connections(self):
        print "INFO: Check for dead connections"
        for _client in self._listeners.keys():
            pid = self._listeners[_client][1]
            if not pid_exists(pid):
                print "INFO: connected client process does not exist. Removed."
                self.unregister_connection(id = _client)
#            else:
#                print "INFO: connected client process still exists."
        return True

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = 'ss', out_signature = 's')
    def register_connection(self, name, pid):
        """
        @todo: Take the PID here as parameter. Generate the id here (do not use
                object id).
        """
        _res = ""
        print "Register connection: %s (pid=%s)" % (name, pid)
        id = str(uuid.uuid4())
        if self._listeners.has_key(id):
            raise SBDbusException("The generated id is already in use. This is a bug :( Please report the issue to the developers.")
        else:
            self._listeners[id] = (name, pid)
            _res = id
        print "INFO: My connections: %s" % str(self._listeners)
        return _res

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = 's', out_signature = 'b')
    def unregister_connection(self, id):
        """
        @todo: Add some kind of regular insanity check, e.g. by checking PIDs given
               when registering whether the listeners are still running.
        """
        _res = False
        print "Unregister listener with id: %s" % id

        if not self._listeners.has_key(id):
            raise SBDbusException("The given id is not registered.")
        else:
            del self._listeners[id]
            _res = True
        print "INFO: My connections: %s" % str(self._listeners)
        if len(self._listeners) == 0:
            print "Last listener was unregistered."
            if self._keep_alive:
                print "But NsSBackupdDBusObject is kept alive."
            else:
                print "NsSBackupdDBusObject is being terminated."
#                gobject.idle_add(self.Exit)
                gobject.timeout_add(500, self.Exit)
        return _res

#    @dbus.service.method(dbus_support.DBUS_INTERFACE,
#                         in_signature = '', out_signature = '')
#    def RaiseException(self):
#        raise SBDbusException('The RaiseException method does what you might '
#                            'expect')

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = '', out_signature = '(ss)')
    def GetTuple(self):
        return ("Hello Tuple", " from example-service.py")

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = '', out_signature = 'a{ss}')
    def GetDict(self):
        return {"first": "Hello Dict", "second": " from example-service.py"}

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = '', out_signature = '')
    def Exit(self):
        print "Exit of BackupDBusObject was called."
        if self._mainloop:
            self._mainloop.quit()

    @dbus.service.signal(dbus_support.DBUS_INTERFACE)
    def nssbackup_exit_signal(self):
        print "The 'ExitSignal' is emitted."

    @dbus.service.signal(dbus_support.DBUS_INTERFACE)
    def nssbackup_progress_signal(self, checkpoint):
#        print "The 'ProgressSignal' is emitted."
        pass

    @dbus.service.signal(dbus_support.DBUS_INTERFACE)
    def nssbackup_event_signal(self, event, urgency, profile):
        print "nssbackup_event_signal - passed event: `%s` - urgency: `%s` - "\
              "profile: `%s`" % (event, urgency, profile)

    @dbus.service.signal(dbus_support.DBUS_INTERFACE)
    def nssbackup_error_signal(self, profile, error):
        print "nssbackup_error_signal - passed profile: %s - error: %s" % (profile, error)

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = '', out_signature = 'b')
    def emit_nssbackup_exit_signal(self):
        print "This is the 'emit_nssbackup_exit_signal' method"
        self.nssbackup_exit_signal()
        return True

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = 'sss', out_signature = 'b')
    def emit_nssbackup_event_signal(self, event, urgency, profile):
        print "This is the 'emit_nssbackup_event_signal' method"
        self.nssbackup_event_signal(event, urgency, profile)
        return True

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = 'ss', out_signature = 'b')
    def emit_nssbackup_error_signal(self, profile, error):
        print "This is the 'emit_nssbackup_error_signal' method"
        self.nssbackup_error_signal(profile, error)
        return True

    @dbus.service.method(dbus_support.DBUS_INTERFACE,
                         in_signature = 's', out_signature = 'b')
    def emit_progress_signal(self, checkpoint):
        # you emit signals by calling the signal's skeleton method
#        print "This is the 'emit_progress_signal' method"
        self.nssbackup_progress_signal(checkpoint)
        return True


class SBackupDBusService(object):
    """This is the DBUS service that provide basic signals.
    
    """
    def __init__(self, keep_alive = False):
        self._system_bus = None
        self._dbus_service = None
        self._remote_obj = None
        self._mainloop = None
        self._keep_alive = keep_alive

    def _initialize_mainloop(self):
        self._mainloop = gobject.MainLoop()

    def _initialize_dbus_service(self):
        if self._mainloop is None:
            raise AssertionError("ERR: Mainloop must be initialized before "\
                                 "starting the dbus service.")

        self._system_bus = dbus.SystemBus()
        self._dbus_service = dbus.service.BusName(\
                                      dbus_support.DBUS_SERVICE,
                                      self._system_bus)
        self._remote_obj = SBackupdDBusObject(self._system_bus,
                                      dbus_support.DBUS_OBJ_PATH,
                                      self._mainloop,
                                      keep_alive = self._keep_alive)
#TODO: use distinct objects!
#        self._connection_obj = SBackupdDBusObject(self._system_bus,
#                                      "/anotherObject",
#                                      self._mainloop)
        print "NSsbackup DBus service successfully launched"

    def main(self):
        self._initialize_mainloop()
        self._initialize_dbus_service()
        self._mainloop.run()


def is_running():
    """
    :todo: Retrieve the PID of the running service!
    """
    res = False
    bus = dbus.SystemBus()
    dbus_object = bus.get_object('org.freedesktop.DBus',
                                 '/org/freedesktop/DBus')
    dbus_iface = dbus.Interface(dbus_object, 'org.freedesktop.DBus')
    services = dbus_iface.ListNames()
    services.sort()
    for service in services:
        if service == dbus_support.DBUS_SERVICE:
            res = True
            break
    return res


def __launch_service(keep_alive = False):
    print "Launching Simple Backup DBus service"
    sbak_service = SBackupDBusService(keep_alive = keep_alive)
    sbak_service.main()


def parse_cmdline(argv):
    """
    """
    usage = "Usage: %prog [options] (use -h or --help for more infos)"
    version = "%prog " + Infos.VERSION
    prog = "sbackup-dbusservice"

    parser = optparse.OptionParser(usage = usage, version = version, prog = prog)
    parser.add_option("--keep-alive",
              action = "store_true", dest = "keep_alive", default = False,
              help = "don't terminate DBus service after last client was unregistered")

    (options, args) = parser.parse_args(argv[1:])
    if len(args) > 0:
        parser.error("You must not provide any non-option argument")

    return options


def run(args):
    try:
        _options = parse_cmdline(argv = args)
        drop_privileges()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)
        if not is_running():
            __launch_service(keep_alive = _options.keep_alive)
        else:
            print "Simple Backup DBus service is already running"
        _retc = 0
    except Exception, error:
        print "Error in Simple Backup DBus service:\n%s" % str(error)
        _retc = 1
    return _retc
