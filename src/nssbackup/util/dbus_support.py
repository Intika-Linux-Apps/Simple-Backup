"""

if you want to launch it automatically, add in
'peer@ayida:/usr/share/dbus-1/services$':

[D-BUS Service]
Name=org.launchpad.nssbackupService
Exec=/home/peer/programming/python/nssb/local_modified/0.2/src/nssbackup_dbus_service.py

"""

DBUS_SERVICE    = "org.launchpad.nssbackupService"
DBUS_OBJ_PATH   = "/org/launchpad/nssbackupService/nssbackupdDbusObject"
DBUS_INTERFACE  = "org.launchpad.nssbackupService.nssbackupdDbusInterface"
DBUS_EXCEPTION  = "org.launchpad.nssbackupdDbusException"

# this is for providing methods by the GUI service
DBUS_GUI_SERVICE    = "org.launchpad.nssbackupGuiService"
DBUS_GUI_OBJ_PATH   = "/org/launchpad/nssbackupService/nssbackupdDbusGuiObject"
DBUS_GUI_INTERFACE  = "org.launchpad.nssbackupService.nssbackupdDbusGuiInterface"
DBUS_GUI_EXCEPTION  = "org.launchpad.nssbackupdDbusGuiException"