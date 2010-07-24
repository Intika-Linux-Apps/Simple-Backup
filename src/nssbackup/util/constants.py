#    Simple Backup - definition of common constants
#
#   Copyright (c)2010: Jean-Peer Lorenz <peer.loz@gmx.net>
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

#TODO: Add module dbus_constants?

# values in milliseconds if not stated otherwise in variable name


import signal


ONE_SECOND = 1
ONE_SECOND_IN_MILLISEC = 1000

TIMEOUT_RETRY_TARGET_CHECK_SECONDS = 60
INTERVAL_RETRY_TARGET_CHECK_SECONDS = 5

INDICATOR_LAUNCH_PAUSE_SECONDS = 5
TIMEOUT_INDICATOR_QUIT_SECONDS = 11 # timeout before quitting the indicator app

DBUS_CHECK_INTERVAL_SECONDS = 5
DBUS_RECONNECT_INTERVAL_SECONDS = 5
AUTOEXIT_TIMEOUT_SECONDS = 10
AUTOEXIT_CHECK_INTERVAL_SECONDS = 10


INTERVAL_UNREGISTER_DEAD_CONN = 300000  # milliseconds
DBUS_SERVICE_QUIT_PAUSE = 500


# settings
RETRY_UNKNOWN = -1
RETRY_TRUE = 1
RETRY_FALSE = 0
PID_UNKNOWN = -1
SPACE_REQUIRED_UNKNOWN = -1
FREE_SPACE_UNKNOWN = -1
SIZE_FILESYSTEM_UNKNOWN = -1
TARGET_UNKNOWN = ""
PROFILE_UNKNOWN = ""

# TAR
TAR_BLOCKSIZE = 512     # block size in Bytes, fixed in Tar 
TAR_BLOCKING_FACTOR = 20
TAR_RECORDSIZE = TAR_BLOCKING_FACTOR * TAR_BLOCKSIZE


##TODO: Keep copy of this used in `sbackup-terminate` up-to-date!
BACKUP_CANCEL_SIG = signal.SIGUSR1


# Name definitions
DBUSSERVICE_FILE = "sbackup-dbusservice"
INDICATORAPP_FILE = "sbackup-indicator"
INDICATORAPP_NAME = "Simple Backup Indicator Application"

DBUS_NOTIFIER_NAME = "Simple Backup DBus Notifier"

TERMINATE_FILE = "sbackup-terminate"
BACKUP_COMMAND = "nssbackupd"
BACKUP_PROCESS_NAME = "Simple Backup Process"


# icon filenames
DEFAULT_ICON_FILENAME = "nssbackup.png"
NOTIFICATION_ICON_FILENAME = "nssbackup32x32.png"
CONFIG_ICON_FILENAME = "nssbackup-conf.png"
RESTORE_ICON_FILENAME = "nssbackup-restore.png"

# icon names (must be registered before using)
INDICATOR_ATTENTION_ICON = "sbackup-attention"
INDICATOR_ACTIVE_ICON = "sbackup-panel"
INDICATOR_SUCCESS_ICON = "sbackup-success"


# default values for environment variable if not set
# see: http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
ENVVAR_XDG_DATA_DIRS = "XDG_DATA_DIRS"
DEFAULT_XDG_DATA_DIRS = "/usr/local/share/:/usr/share/"


# used in module `util`
RSRC_FILE = "resources"
LOCALE_DIR = "locale"
LOCALE_DOMAIN = "nssbackup"

NOTIFICATION_DOMAIN = "nssbackup"


# dbus constants - keep copies of these up-to-date in `sbackup-progress`
#                  and `org.sbackupteam.SimpleBackup.conf` and `Makefile`
#                  configuration file name = dbus service!
DBUS_SERVICE = "org.sbackupteam.SimpleBackup"
DBUS_OBJ_PATH = "/SBackupProcess"
DBUS_CONNECTION_OBJ_PATH = "/SBackupConnection"
DBUS_INTERFACE = "org.sbackupteam.SimpleBackup.SBackupDbusInterface"
DBUS_EXCEPTION = "org.sbackupteam.SBackupDbusException"



# Global path definitions
LOCKFILE_BACKUP_FULL_PATH = "/var/lock/sbackup/sbackup.lock"
LOCKFILE_INDICATOR_FULL_PATH = "/var/lock/sbackup/sbackup-indicator.lock"


# Exit codes
EXCODE_SUCCESS = 0
EXCODE_GENERAL_ERROR = 1
EXCODE_INSTANCE_ALREADY_RUNNING = 3
EXCODE_KEYBOARD_INTERRUPT = 39
EXCODE_MAIL_ERROR = 38
EXCODE_BACKUP_ERROR = 38
