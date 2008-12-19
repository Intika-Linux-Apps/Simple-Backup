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

import gobject

import dbus
import dbus.service
import dbus.mainloop.glib

from nssbackup.util import nssbackup_dbus_support


class DemoException(dbus.DBusException):
    _dbus_error_name = nssbackup_dbus_support.DBUS_EXCEPTION


class NsSBackupdDBusObject(dbus.service.Object):

    def __init__(self, session_bus, object_path, mainloop):
        dbus.service.Object.__init__(self, session_bus, object_path)
        self._session_bus   = session_bus
        self._mainloop      = mainloop
    
    @dbus.service.method(nssbackup_dbus_support.DBUS_INTERFACE,
                         in_signature='s', out_signature='as')
    def HelloWorld(self, hello_message):
        print (str(hello_message))
        return ["Hello", " from example-service.py", "with unique name",
                self._session_bus.get_unique_name()]

    @dbus.service.method(nssbackup_dbus_support.DBUS_INTERFACE,
                         in_signature='', out_signature='')
    def RaiseException(self):
        raise DemoException('The RaiseException method does what you might '
                            'expect')

    @dbus.service.method(nssbackup_dbus_support.DBUS_INTERFACE,
                         in_signature='', out_signature='(ss)')
    def GetTuple(self):
        return ("Hello Tuple", " from example-service.py")

    @dbus.service.method(nssbackup_dbus_support.DBUS_INTERFACE,
                         in_signature='', out_signature='a{ss}')
    def GetDict(self):
        return {"first": "Hello Dict", "second": " from example-service.py"}

    @dbus.service.method(nssbackup_dbus_support.DBUS_INTERFACE,
                         in_signature='', out_signature='')
    def Exit(self):
        print "Exit was called."
        if self._mainloop:
            self._mainloop.quit()


    @dbus.service.signal(nssbackup_dbus_support.DBUS_INTERFACE)
    def ProgressSignal(self, checkpoint):
        # The signal is emitted when this method exits
        # You can have code here if you wish
#        pass
        print "The 'ProgressSignal' is emitted."
            
    @dbus.service.signal(nssbackup_dbus_support.DBUS_INTERFACE)
    def HelloSignal(self, message):
        # The signal is emitted when this method exits
        # You can have code here if you wish
        print "The actual HelloSignal - passed message: %s" % message


    @dbus.service.method(nssbackup_dbus_support.DBUS_INTERFACE,
                         in_signature='s', out_signature='s')
    def emitSignal(self, msg):
        # you emit signals by calling the signal's skeleton method
        print "This is the 'emitSignal' method"
        self.HelloSignal(msg)
        return 'Signal emitted'

    @dbus.service.method(nssbackup_dbus_support.DBUS_INTERFACE,
                         in_signature='s', out_signature='b')
    def emit_progress_signal(self, checkpoint):
        # you emit signals by calling the signal's skeleton method
        print "This is the 'emit_progress_signal' method"
        self.ProgressSignal(checkpoint)
        return True


class NsSBackupDBusService(object):
    def __init__(self):
        self._session_bus   = None
        self._dbus_service  = None
        self._remote_obj    = None
        self._mainloop      = None
        
    def _initialize_mainloop(self):
        self._mainloop = gobject.MainLoop()
                
    def _initialize_dbus_service(self):
        if self._mainloop is None:
            raise AssertionError("ERR: Mainloop must be initialized before "\
                                 "starting the dbus service.")
        
        self._session_bus = dbus.SessionBus()
        self._dbus_service = dbus.service.BusName(\
                                      nssbackup_dbus_support.DBUS_SERVICE,
                                      self._session_bus)
        self._remote_obj = NsSBackupdDBusObject(self._session_bus,
                                      nssbackup_dbus_support.DBUS_OBJ_PATH,
                                      self._mainloop)
        print "finished '_initialize_dbus_service'"
    
    def main(self):
        self._initialize_mainloop()
        self._initialize_dbus_service()
        self._mainloop.run()
        
                
if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    sbak_service = NsSBackupDBusService()
    sbak_service.main()
