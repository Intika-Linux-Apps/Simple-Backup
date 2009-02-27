"""

if you want to launch it automatically, add in
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
            
    def emit_info_signal(self, event, profile):
        """Used for sending a generic information event over the signal dbus.
        
        :param event: the actually processed event
        :param profile: name of the current profile

        """
        ret_val = self._remote_obj.emit_nssbackup_info_signal(event, profile,
                        dbus_interface=DBUS_INTERFACE)
        print "Returned value: %s" % ret_val
        return ret_val

#    def emit_commit_signal(self, profile):
#        """Used for sending a commit signal over the signal dbus.
#        
#        :param profile: name of the current profile
#        
#        """
#        ret_val = self._remote_obj.emit_nssbackup_commit_signal(profile,
#                        dbus_interface=DBUS_INTERFACE)
#            
#        print "Returned value: %s" % ret_val
#        return ret_val
#
#    def emit_finish_signal(self, profile):
#        """Used for sending a finish signal over the signal dbus.
#        
#        :param profile: name of the current profile
#        
#        """
#        ret_val = self._remote_obj.emit_nssbackup_finished_signal(profile,
#                        dbus_interface=DBUS_INTERFACE)
#
#        print "Returned value: %s" % ret_val
#        return ret_val

    def emit_warning_signal(self, event, profile):
        """Used for sending an warning signal over the signal dbus.
        
        :param profile: name of the current profile
        :param error: error message to be passed
        
        """
        ret_val = self._remote_obj.emit_nssbackup_warning_signal(event, profile,
                        dbus_interface=DBUS_INTERFACE)
            
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
        print "OBSERVER UPDATE"
        self.__state = subject.get_state()
        self.__profilename = subject.get_profilename()
        self.__recent_error = subject.get_recent_error()
        
        print "STATE: `%s`" % self.__state
        self.__attempt_notify()

    def __attempt_notify(self):
        state = self.__state
        print "NOTIFY STATE: %s" % state
        
        ret_val = None
        if self.__dbus is not None:
            if state in ('start', 'commit', 'finish'):
                ret_val = self.__dbus.emit_info_signal(state,
                                                       self.__profilename)

            elif state == 'needupgrade':
                ret_val = self.__dbus.emit_warning_signal(state,
                                                          self.__profilename)
                
#            if state == 'start':
#                ret_val = self.__dbus.emit_start_signal(self.__profilename)
#                
#            if state == 'commit':
#                ret_val = self.__dbus.emit_commit_signal(self.__profilename)
#                
#            elif state == 'finish':
#                ret_val = self.__dbus.emit_finish_signal(self.__profilename)

            elif state == 'error':
                ret_val = self.__dbus.emit_error_signal(self.__profilename,
                                                       str(self.__recent_error))
    
            else:
                print "STATE UNSUPPORTED (%s)" % state
                
        print "Returned value: %s" % ret_val
        return ret_val
