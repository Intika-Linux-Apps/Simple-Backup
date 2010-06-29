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

"""

import os
import uuid
import optparse

import gobject

import dbus.service
import dbus.mainloop.glib

from nssbackup.pkginfo import Infos
from nssbackup.util import log
from nssbackup.util import constants
from nssbackup.util.system import drop_privileges
from nssbackup.util.system import pid_exists


#TODO: Further split of object's responsibility: sender object/receiver 
#TODO: Add module dbus_constants?
__START = "start"
__STOP = "stop"
__RESTART = "restart"
__valid_args = [__START, __STOP, __RESTART]


class SBDbusException(dbus.DBusException):
    _dbus_error_name = constants.DBUS_EXCEPTION


class SBackupdDBusObject(dbus.service.Object):

    def __init__(self, system_bus, object_path):
        dbus.service.Object.__init__(self, system_bus, object_path)
        self._system_bus = system_bus

        self.__backup_pid = constants.PID_UNKNOWN
        self.__retry_target_check = constants.RETRY_UNKNOWN
        self.__target = constants.TARGET_UNKNOWN
        self.__profilename = constants.PROFILE_UNKNOWN
        self.__space_required = constants.SPACE_REQUIRED_UNKNOWN

    @dbus.service.signal(constants.DBUS_INTERFACE)
    def progress_signal(self, checkpoint):
        pass

    @dbus.service.signal(constants.DBUS_INTERFACE)
    def event_signal(self, event, urgency):
        pass

    @dbus.service.signal(constants.DBUS_INTERFACE)
    def error_signal(self, error):
        pass

    @dbus.service.signal(constants.DBUS_INTERFACE)
    def targetnotfound_signal(self):
        pass

    @dbus.service.signal(constants.DBUS_INTERFACE)
    def alreadyrunning_signal(self):
        pass

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 'ss', out_signature = 'b')
    def emit_event_signal(self, event, urgency):
        self.event_signal(event, urgency)
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 's', out_signature = 'b')
    def emit_error_signal(self, error):
        self.error_signal(error)
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 'b')
    def emit_targetnotfound_signal(self):
        self.targetnotfound_signal()
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 'b')
    def emit_alreadyrunning_signal(self):
        self.alreadyrunning_signal()
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 'n', out_signature = 'b')
    def set_retry_target_check(self, retry):
        """
        Valid values are:  -1 unknown
                            0 False (do not retry)
                            1 True (retry)
        """
        self.__retry_target_check = retry
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 'n')
    def get_retry_target_check(self):
        return self.__retry_target_check

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 'i', out_signature = 'b')
    def set_backup_pid(self, pid):
        """
        """
        self.__backup_pid = pid
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 'i')
    def get_backup_pid(self):
        """
        """
        return self.__backup_pid

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 's', out_signature = 'b')
    def set_target(self, target):
        """
        """
        self.__target = target
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 's', out_signature = 'b')
    def set_profilename(self, profilename):
        """
        """
        self.__profilename = profilename
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 'x', out_signature = 'b')
    def set_space_required(self, space):
        """
        """
        self.__space_required = space
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 's')
    def get_target(self):
        return self.__target

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 's')
    def get_profilename(self):
        return self.__profilename

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 'x')
    def get_space_required(self):
        return self.__space_required

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 's', out_signature = 'b')
    def emit_progress_signal(self, checkpoint):
        self.progress_signal(checkpoint)
        return True


class SBackupDbusConnectionObject(dbus.service.Object):

    def __init__(self, system_bus, object_path, mainloop, keep_alive = False):
        dbus.service.Object.__init__(self, system_bus, object_path)
        self.__logger = log.LogFactory.getLogger()
        self._system_bus = system_bus
        self._mainloop = mainloop
        self._listeners = {}
        self._keep_alive = keep_alive
        self._id = None

        self._set_id()
        self._initialize_timer()

    def _set_id(self):
        pid = str(os.getpid())
        oid = str(id(self))
        uid = str(uuid.uuid4())
        self._id = "%s:%s:%s" % (pid, oid, uid)

    def _initialize_timer(self):
        gobject.timeout_add(constants.INTERVAL_UNREGISTER_DEAD_CONN,
                            self._unregister_dead_connections)

    def _unregister_dead_connections(self):
        self.__logger.debug("Check for dead connections")
        for _client in self._listeners.keys():
            pid = self._listeners[_client][1]
            if not pid_exists(pid):
                self.__logger.info("connected client process does not exist. Removed.")
                self.unregister_connection(connection_id = _client)
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 'ss', out_signature = 's')
    def register_connection(self, name, pid):
        """
        """
        _res = ""
        self.__logger.debug("Register connection: %s (pid=%s)" % (name, pid))
        _id = str(uuid.uuid4())
        if self._listeners.has_key(_id):
            raise SBDbusException("The generated id is already in use. This is a bug :( Please report the issue to the developers.")
        else:
            self._listeners[_id] = (name, pid)
            _res = _id
        self.__logger.debug("INFO: My connections: %s" % str(self._listeners))
        return _res

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = 's', out_signature = 'b')
    def unregister_connection(self, connection_id):
        """
        @todo: Add some kind of regular insanity check, e.g. by checking PIDs given
               when registering whether the listeners are still running.
        """
        _res = False
        self.__logger.debug("Unregister listener with id: %s" % connection_id)

        if not self._listeners.has_key(connection_id):
            raise SBDbusException("The given id is not registered.")
        else:
            del self._listeners[connection_id]
            _res = True
        if len(self._listeners) == 0:
            self.__logger.debug("Last listener was unregistered.")
            if self._keep_alive:
                self.__logger.info("But SBackupdDBusObject is kept alive.")
            else:
                self.__logger.info("SBackupdDBusObject is being terminated.")
                gobject.timeout_add(constants.DBUS_SERVICE_QUIT_PAUSE, self.quit)
        return _res

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = '')
    def quit(self):
        if self._mainloop:
            self._mainloop.quit()

    @dbus.service.signal(constants.DBUS_INTERFACE)
    def exit_signal(self):
        pass

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 'b')
    def emit_exit_signal(self):
        self.exit_signal()
        return True

    @dbus.service.method(constants.DBUS_INTERFACE,
                         in_signature = '', out_signature = 's')
    def get_id(self):
        return self._id


class SBackupDBusService(object):
    """This is the DBUS service that provide basic signals.
    
    """
    def __init__(self, keep_alive = False):
        self._system_bus = None
        self._dbus_service = None
        self._remote_obj = None
        self._connection = None
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
                                      constants.DBUS_SERVICE,
                                      self._system_bus)
        self._remote_obj = SBackupdDBusObject(self._system_bus,
                                      constants.DBUS_OBJ_PATH)
        self._connection = SBackupDbusConnectionObject(self._system_bus,
                                      constants.DBUS_CONNECTION_OBJ_PATH,
                                      self._mainloop,
                                      keep_alive = self._keep_alive)

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
        if service == constants.DBUS_SERVICE:
            res = True
            break
    return res


def __launch_service(keep_alive = False):
    sbak_service = SBackupDBusService(keep_alive = keep_alive)
    sbak_service.main()


def __stop_service():
    try:
        _system_bus = dbus.SystemBus()
        remote_obj = _system_bus.get_object(constants.DBUS_SERVICE,
                                            constants.DBUS_CONNECTION_OBJ_PATH)
    except dbus.DBusException:
        remote_obj = None

    if remote_obj is not None:
        remote_obj.quit(dbus_interface = constants.DBUS_INTERFACE)


def parse_cmdline(argv):
    usage = "Usage: %prog " + __START + "|" + __STOP + "|" + __RESTART + " [options] (use -h or --help for more infos)"
    version = "%prog " + Infos.VERSION
    prog = constants.DBUSSERVICE_FILE

    parser = optparse.OptionParser(usage = usage, version = version, prog = prog)
    parser.add_option("--keep-alive",
              action = "store_true", dest = "keep_alive", default = False,
              help = "don't terminate DBus service after last client was unregistered")

    (options, args) = parser.parse_args(argv[1:])
    if len(args) != 1:
        parser.error("No command given")
    cmd = args[0]
    if cmd not in __valid_args:
        parser.error("Unknown command given")
    if cmd == "stop" and options.keep_alive:
        parser.error("Unable to stop the service and to keep it alive")

    return (cmd, options)


def run(args):
    try:
        _cmd, _options = parse_cmdline(argv = args)
        drop_privileges()
        os.nice(5)

        dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)

        _running = is_running()
        if _cmd == "start":
            if _running:
                print "Simple Backup DBus service is already running"
            else:
                __launch_service(keep_alive = _options.keep_alive)
        elif _cmd == "stop":
            if _running:
                __stop_service()
            else:
                print "Simple Backup DBus service is not running"
        elif _cmd == "restart":
            if _running:
                __stop_service()
            __launch_service(keep_alive = _options.keep_alive)

        exitcode = constants.EXCODE_SUCCESS

    except dbus.DBusException, error:
        print "Error in Simple Backup DBus service:\n%s" % str(error)
        exitcode = constants.EXCODE_GENERAL_ERROR
    return exitcode
