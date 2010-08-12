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

"""

import os
import time
import types
import dbus

from nssbackup import dbus_service

from nssbackup.util import log
from nssbackup.util import notifier
from nssbackup.util import structs
from nssbackup.util import constants
from nssbackup.util import system
from nssbackup.util import exceptions
from nssbackup.util import get_resource_file


#DBUS_CONNECT_TIMEOUT_TOTAL_SECONDS = 15 # for given number of trials
#DBUS_CONNECT_MAX_TRIALS = 3
DBUS_COMMUNICATE_PAUSE_SECONDS = 0.5  # seconds

KWARG_DBUS_INTERFACE = "dbus_interface"


class _DBusConnection(object):
    """Abstract base class that provides functionality for sending signals
    and calling methods over the dbus.    
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
        self._backup_obj = None
        self._connection_obj = None
        self._connected = False
        self._dbus_id = None

        self.__clear()

    def __clear(self):
        self._id = ""
        self._system_bus = None
        self._backup_obj = None
        self._connection_obj = None
        self._connected = False
        self._dbus_id = None

    def get_is_connected(self):
        return self._connected

#    def __do_connect(self, service, path, silent = False):
#        """Private helper method for connecting to service (i.e. importing the
#        remote object via DBus).
#        """
#        remote_obj = None
#        timeout = DBUS_CONNECT_TIMEOUT_TOTAL_SECONDS
#        max_trials = DBUS_CONNECT_MAX_TRIALS
#        dur = timeout / max_trials
#
#        trials = 0          # trials performed
#        connecting = True
#        while connecting:
#            try:
#                trials += 1
#                self._logger.debug("Trying to connect to `%s` (trial no. %s)" % (service,
#                                                                    trials))
#                remote_obj = self._system_bus.get_object(service, path)
#                connecting = False
#                if not silent:
#                    self._logger.info("successfully connected to `%s` provided by `%s`" % (path, service))
#            except dbus.DBusException, error:
#                if not silent:
#                    self._logger.error("Error while getting service:\n%s" % (str(error)))
#                if trials == max_trials:
#                    self._logger.debug("Number of max. trials reached - timeout!")
#                    connecting = False
#                    remote_obj = None
#                else:
#                    self._logger.debug("Waiting %s sec. before re-connecting" % dur)
#                    time.sleep(dur)
#        return remote_obj

    def __do_connect(self, service, path, silent = False):
        """Private helper method for connecting to service (i.e. importing the
        remote object via DBus).
        """
        remote_obj = None
        try:
            self._logger.debug("Trying to connect to `%s`" % service)
            remote_obj = self._system_bus.get_object(service, path)
            if not silent:
                self._logger.info("successfully connected to `%s` provided by `%s`" % (path, service))
        except dbus.DBusException, error:
            if not silent:
                self._logger.error("Error while getting service:\n%s" % (str(error)))
            remote_obj = None
        return remote_obj

    def connect(self, silent = True):
        """Connects passively to DBus service and registers this connection at the service.
        The service id is stored for later checks of the validity of the connection.
        
        Remote objects are set to None in case of failure. 
        """
        self.test_validity()
        if self._connected is True:
            if not silent:
                self._logger.info("Connection is already established.")
        else:
            _failure = False
            try:
                self._system_bus = dbus.SystemBus()
                self._backup_obj = self.__do_connect(constants.DBUS_SERVICE,
                                                     constants.DBUS_OBJ_PATH,
                                                     silent)
                self._connection_obj = self.__do_connect(constants.DBUS_SERVICE,
                                                     constants.DBUS_CONNECTION_OBJ_PATH,
                                                     silent)

                if (self._connection_obj is not None) and (self._backup_obj is not None):
                    pid = os.getpid()
                    self._id = self._connection_obj.register_connection(self._name, str(pid))
                    self._dbus_id = self._connection_obj.get_id()
                    self._logger.debug("Registered with id: %s" % self._id)
                    self._connected = True
                else:
                    _failure = True
                    error = "Unable to get remote object"

            except dbus.DBusException, error:
                _failure = True

            if _failure is True:
                self.__clear()
                if not silent:
                    self._logger.error("Error while connecting to DBus service: %s" % error)
            else:
                self.test_validity()
#                if self._connected:
#                    if not silent:
#                        self._logger.info("Successfully connected to Dbus service with id: %s" % self._dbus_id)
#                else:
#                    self._logger.warning("Unable to connect to Dbus service")

    def test_validity(self):
        """Tests whether connection is valid, i.e. exists and is the same connection as originally
        connected to. If connection is `invalid` everything is cleared and external callers (that use
        this instance) are required to call `connect` again. Moreover, it is required to re-connect any
        signal handlers. (This method does not return the result of the test due to CQS. Call
        `get_is_connected` instead.)
        """
        valid = False
        failure = False
        dbus_id = None

        if self._connection_obj is not None:
            try:
                dbus_id = self._connection_obj.get_id()
            except dbus.DBusException, error:
                self._logger.error("Unable to get service while testing availibility: %s" % (str(error)))
                dbus_id = None
                failure = True

        if self._backup_obj is not None:
            try:
                self._backup_obj.get_backup_pid()
            except dbus.DBusException, error:
                self._logger.error("Unable to get service while testing availibility: %s" % (str(error)))
                failure = True

        if (failure is False) and (dbus_id is not None)\
           and (self._id is not None) and (dbus_id == self._dbus_id):
            valid = True
        else:
            valid = False

        if valid is False:
            self.__clear()

    def quit(self):
        res = True
        if self._connected is True:
            if self._id != "":
                if self._connection_obj is not None:
                    try:
                        res = bool(self._connection_obj.unregister_connection(self._id))
                    except dbus.DBusException, error:
                        self._logger.warning("Unable to unregister connection: %s" % (str(error)))
                        res = False

                    if res is True:
                        self._logger.debug("Connection was successfully unregistered.")
                    else:
                        self._logger.warning("Unable to unregister connection (failed).")
#            else:
#                print "WARN: Unable to unregister connection (no client id)."
# avoid warning when calling this method as singleton
        self.__clear()
        return res


class DBusProviderFacade(_DBusConnection):
    """This class provides functionality for sending signals
    and calling methods over the dbus.
     
    The Dbus connection is only created on demand. In the case the user
    don't want to use it, no connection is created.
    
    The Provider is the only class that is able to send an Exit signal over the
    dbus. 
    
    :todo: Singleton!
    """
    __metaclass__ = structs.Singleton

    def __init__(self, name):
        """Default constructor.
        
        """
        _DBusConnection.__init__(self, name)

    def _launch_dbusservice(self):
        """Launches the DBus service and establishes a placeholder
        connection in order to keep the service alive as long as this
        application is running. Call `finalize` to close the
        connection properly when terminating the application.
        """
        dbus_launcher = get_resource_file(constants.DBUSSERVICE_FILE)
        system.exec_command_async(args = [dbus_launcher, "start"])
        time.sleep(DBUS_COMMUNICATE_PAUSE_SECONDS)

    def ensure_connectivity(self):
        """Tests whether a connection is established and if not tries to connect.
        If necessary, the service is being launched.  
        """
        self.test_validity()
        if self.get_is_connected() is False:
            self.connect()
            if self.get_is_connected() is False:
                raise exceptions.DBusException("Unable to launch DBus service")

        assert self._connected is True
        assert self._backup_obj is not None
        assert self._connection_obj is not None


    def connect(self, silent = False):
        """Connects actively to DBus service and registers this connection at the service.
        If necessary, the service is being launched. The service id is stored for later
        checks of the validity of the connection.        
        """
        if dbus_service.is_running() is False:
            self._launch_dbusservice()
        _DBusConnection.connect(self)

    def __call_remote(self, func, *args, **kwargs):
        """Helper method for setter and signal emitter.
        """
        if not kwargs.has_key(KWARG_DBUS_INTERFACE):
            kwargs[KWARG_DBUS_INTERFACE] = constants.DBUS_INTERFACE
        res = False
        # we can not re-connect from this method since this would make given callable func invalid
        if self.get_is_connected() is True:
            try:
                res = func(*args, **kwargs)
            except dbus.DBusException, error:
                self._logger.error("Error while DBus operation in `__call_remote`: %s\n(%s(%s, %s))" % \
                                   (error, str(func), str(args), str(kwargs)))
                res = False
        res = bool(res)
        return res

    def emit_event_signal(self, event, urgency):
        """Used for sending a generic event over the signal dbus.
        This includes informations and warnings.
        
        :param event: the actually processed event
        :param urgency: how urgent the message is
        """
        if not isinstance(event, types.StringTypes):
            raise TypeError("Parameter `event` of string type expected. Got %s instead." % str(type(event)))
        if not isinstance(urgency, types.StringTypes):
            raise TypeError("Parameter `urgency` of string type expected. Got %s instead." % str(type(urgency)))
        self.ensure_connectivity()
        res = self.__call_remote(self._backup_obj.emit_event_signal, event, urgency)
        assert isinstance(res, types.BooleanType)
        return res

    def emit_error_signal(self, error):
        """Used for sending an error signal over the signal dbus.
        
        :param profile: name of the current profile
        :param error: error message to be passed
        
        """
        if not isinstance(error, types.StringTypes):
            raise TypeError("Parameter of string type expected. Got %s instead." % str(type(error)))
        self.ensure_connectivity()
        res = self.__call_remote(self._backup_obj.emit_error_signal, error)
        assert isinstance(res, types.BooleanType)
        return res

    def emit_targetnotfound_signal(self):
        self.ensure_connectivity()
        res = self.__call_remote(self._backup_obj.emit_targetnotfound_signal)
        assert isinstance(res, types.BooleanType)
        return res

    def set_backup_pid(self, pid):
        if not isinstance(pid, types.IntType):
            raise TypeError("Parameter of integer type expected. Got %s instead." % str(type(pid)))
        self.ensure_connectivity()
        res = self.__call_remote(self._backup_obj.set_backup_pid, pid)
        assert isinstance(res, types.BooleanType)
        return res

    def set_target(self, target):
        if not isinstance(target, types.StringTypes):
            raise TypeError("Parameter of string type expected. Got %s instead." % str(type(target)))
        self.ensure_connectivity()
        res = self.__call_remote(self._backup_obj.set_target, target)
        assert isinstance(res, types.BooleanType)
        return res

    def set_profilename(self, profilename):
        if not isinstance(profilename, types.StringTypes):
            raise TypeError("Parameter of string type expected. Got %s instead." % str(type(profilename)))
        self.ensure_connectivity()
        res = self.__call_remote(self._backup_obj.set_profilename, profilename)
        assert isinstance(res, types.BooleanType)
        return res

    def set_space_required(self, space):
        if not isinstance(space, (types.IntType, types.LongType)):
            raise TypeError("Parameter of string type expected. Got %s instead." % str(type(space)))
        space = long(space)
        self.ensure_connectivity()
        res = self.__call_remote(self._backup_obj.set_space_required, space)
        assert isinstance(res, types.BooleanType)
        return res

    def get_retry_target_check(self):
        """This method is an exception from intended strict separation of setter/getter
        methods into Provider/Client objects.
        
        Keep this method passive!
        
        :todo: Improve design of dbus service related code.
        """
        retval = constants.RETRY_UNKNOWN
        self.test_validity()
        if self.get_is_connected() is True:
            try:
                retval = self._backup_obj.get_retry_target_check(dbus_interface = constants.DBUS_INTERFACE)
            except dbus.DBusException, error:
                self._logger.error("Error while dbus operation in `get_retry_target_check`: %s" % error)
                retval = constants.RETRY_UNKNOWN
        return retval

    def exit(self):
        """
        """
        self.ensure_connectivity()
        self.__call_remote(self._connection_obj.emit_exit_signal)
        res = self.quit()
        return res


class DBusClientFacade(_DBusConnection):
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

    def connect_to_event_signal(self, handler):
#TODO: raise an exception here when not connected to remote object?
        self.test_validity()
        if self.get_is_connected() is True:
            self._backup_obj.connect_to_signal('event_signal', handler,
                                               dbus_interface = constants.DBUS_INTERFACE)

    def connect_to_error_signal(self, handler):
        self.test_validity()
        if self.get_is_connected() is True:
            self._backup_obj.connect_to_signal('error_signal', handler,
                                               dbus_interface = constants.DBUS_INTERFACE)

    def connect_to_progress_signal(self, handler):
        self.test_validity()
        if self.get_is_connected() is True:
            self._backup_obj.connect_to_signal('progress_signal', handler,
                                               dbus_interface = constants.DBUS_INTERFACE)

    def connect_to_targetnotfound_signal(self, handler):
        self.test_validity()
        if self.get_is_connected() is True:
            self._backup_obj.connect_to_signal('targetnotfound_signal', handler,
                                               dbus_interface = constants.DBUS_INTERFACE)

    def connect_to_alreadyrunning_signal(self, handler):
        self.test_validity()
        if self.get_is_connected() is True:
            self._backup_obj.connect_to_signal('alreadyrunning_signal', handler,
                                               dbus_interface = constants.DBUS_INTERFACE)

    def connect_to_exit_signal(self, handler):
        signal = "exit_signal"
        self.test_validity()
        if self.get_is_connected() is True:
            self._connection_obj.connect_to_signal(signal, handler,
                                                   dbus_interface = constants.DBUS_INTERFACE)

    def get_backup_pid(self):
        retval = constants.PID_UNKNOWN
        self.test_validity()
        if self.get_is_connected() is True:
            try:
                retval = self._backup_obj.get_backup_pid(dbus_interface = constants.DBUS_INTERFACE)
            except dbus.DBusException, error:
                self._logger.error("Error while dbus operation in `get_backup_pid`: %s" % error)
                retval = constants.PID_UNKNOWN
        return retval

    def get_target(self):
        retval = constants.TARGET_UNKNOWN
        self.test_validity()
        if self.get_is_connected() is True:
            try:
                retval = self._backup_obj.get_target(dbus_interface = constants.DBUS_INTERFACE)
            except dbus.DBusException, error:
                self._logger.error("Error while dbus operation in `get_target`: %s" % error)
                retval = constants.TARGET_UNKNOWN
        return retval

    def get_profilename(self):
        retval = constants.PROFILE_UNKNOWN
        self.test_validity()
        if self.get_is_connected() is True:
            try:
                retval = self._backup_obj.get_profilename(dbus_interface = constants.DBUS_INTERFACE)
            except dbus.DBusException, error:
                self._logger.error("Error while dbus operation in `get_profilename`: %s" % error)
                retval = constants.PROFILE_UNKNOWN
        return retval

    def get_space_required(self):
        retval = constants.SPACE_REQUIRED_UNKNOWN
        self.test_validity()
        if self.get_is_connected() is True:
            try:
                retval = self._backup_obj.get_space_required(dbus_interface = constants.DBUS_INTERFACE)
            except dbus.DBusException, error:
                self._logger.error("Error while dbus operation in `get_space_required`: %s" % error)
                retval = constants.SPACE_REQUIRED_UNKNOWN
        return retval

    def set_retry_target_check(self, retry):
        """This method is an exception from intended strict separation of setter/getter
        methods into Provider/Client objects.
        :todo: Improve design of dbus service related code.
        """
        res = False
        self.test_validity()
        if self.get_is_connected() is True:
            try:
                res = self._backup_obj.set_retry_target_check(retry,
                                                              dbus_interface = constants.DBUS_INTERFACE)
            except dbus.DBusException, error:
                self._logger.error("Error while setting value for `retry_target_check`: %s" % error)
                res = False
        else:
            self._logger.warning("Unable to set value for `retry_target_check`: No connection available.")
        res = bool(res)
        return res

    def emit_alreadyrunning_signal(self):
        res = False
        self.test_validity()
        if self.get_is_connected() is True:
            try:
                res = self._backup_obj.emit_alreadyrunning_signal(dbus_interface = constants.DBUS_INTERFACE)
            except dbus.DBusException, error:
                self._logger.error("Error while emitting `alreadyrunning_signal`: %s" % error)
                res = False
        else:
            self._logger.warning("Unable to emit `alreadyrunning_signal`: No connection available.")
        res = bool(res)
        return res



class DBusNotifier(notifier.Observer):
    """Sends notifications as signals over the DBus.
    It uses an instance of DBusConnection for signaling.
    
    """
    def __init__(self):
        notifier.Observer.__init__(self)

        self.__state = None
        self.__urgency = None
        self.__profilename = None
        self.__recent_error = None
        self.__target = None
        self.__space_required = None

        self.__logger = log.LogFactory.getLogger()
        self.__dbus = None

    def initialize(self):
        self.__setup_dbus()

    def publish_exit(self):
        """
        :todo: Rename into something better (e.g. publish_exit?)
        """
        try:
            self.__dbus.exit()
        except exceptions.DBusException:
            self.__logger.warning("Unable to publish exit over D-Bus")

    def __setup_dbus(self):
        self.__dbus = DBusProviderFacade(constants.DBUS_NOTIFIER_NAME)
        self.__dbus.connect()

    def update(self, subject):
        """Interface method for observer objects that is called by the
        observed subject. In the case of the `DBusNotifier` were
        notifications send over the bus.
         
        """
        self.__logger.debug("Observer update")
        self.__state = subject.get_state()
        self.__urgency = subject.get_urgency()
        self.__profilename = subject.get_profilename()
        self.__recent_error = subject.get_recent_error()
        self.__target = subject.get_target()
        self.__space_required = subject.get_space_required()

        self.__attempt_notify()

    def __attempt_notify(self):
        """Private helper method that actually tries to notify over
        the DBus about several events. This method decides what
        signals are send over the bus.
        
        :return: the value returned by the signal (usually True)
        
        :todo: Remove urgency!
        
        """
        state = self.__state
        urgency = self.__urgency
        self.__logger.debug("state: `%s` - urgency: `%s`" % (state, urgency))

        ret_val = False
        if self.__dbus is not None:
            try:
                # update all properties
                ret_val = self.__dbus.set_target(self.__target)
                ret_val = self.__dbus.set_profilename(self.__profilename)
                ret_val = self.__dbus.set_space_required(self.__space_required)

                if state in ('start',
                             'finish',
                             'prepare',
                             'commit',
                             'backup-canceled',
                             'needupgrade'):
                    ret_val = self.__dbus.emit_event_signal(state, urgency)

                elif state == 'error':
                    ret_val = self.__dbus.emit_error_signal(str(self.__recent_error))

                elif state == 'target-not-found':
                    ret_val = self.__dbus.emit_targetnotfound_signal()

                else:
                    raise ValueError("STATE UNSUPPORTED (%s)" % state)
            except exceptions.DBusException:
                self.__logger.warning("Unable to notifiy over D-Bus")
                ret_val = False

        return ret_val


def get_session_name():
    # a full DE is supposed
    session = ""
    gnome_found = False
    kde_found = False
    try:
        bus = dbus.SessionBus()
        bus.get_object('org.kde.ksmserver', '/KSMServer')
        session = "kde"
        kde_found = True
    except dbus.exceptions.DBusException, error:
        print "Unable to get KDE Session Manager: %s" % error
        kde_found = False

    try:
        bus = dbus.SessionBus()
        bus.get_object('org.gnome.SessionManager',
                                       '/org/gnome/SessionManager')
        session = "gnome"
        gnome_found = True
    except dbus.exceptions.DBusException, error:
        print "Unable to get Gnome Session Manager: %s" % error
        gnome_found = False

    if gnome_found and kde_found:
        raise AssertionError("Unable to get non-ambiguous desktop session: Gnome *and* KDE found")

    return session
