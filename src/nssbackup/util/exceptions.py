#    NSsbackup - custom exceptions
#
#   Copyright (c)2007-2008: Ouattara Oumar Aziz <wattazoum@gmail.com>
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
:mod:`exceptions` -- custom exceptions
======================================

.. module:: util.exceptions
   :synopsis: Defines custom exceptions
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

class SigTerminatedError(Exception) :
    """This Exception is thrown if the backup process receives a
    SIGTERM/SIGKILL signal.
    """

class SBException(Exception):
    """This class will help us distinguish Exception that we must
    handle (exceptions created by ourself) and exceptions due to 
    programming errors (Python Exceptions).
    """

class InstanceRunningError(SBException) :
    """This Exception is thrown if another application instance is
    already running.
    """

class ApplicationLockError(SBException) :
    """This Exception is thrown if another application instance is
    already running.
    """

class BackupCanceledError(SBException) :
    """This Exception is thrown if the backup process is canceled from
    the indicator gui.
    """

class NotValidSnapshotException(SBException) :
    """
    This Exception is thrown by Snapshot validation.
    """

class NotValidSnapshotNameException(NotValidSnapshotException):
    """Exception launched when the name of a snapshot is not valid
    
    """


class NotValidSectionException(SBException) :
    """This Exception is thrown by Config Section validation.
    
    """

class NonValidOptionException(SBException):
    """Thrown when a config option is not Valid

    """

class CorruptedSBdictException(SBException):
    """Thrown when a SBdict is corrupted

    """

class FuseFAMException(SBException):
    """Thrown when a Fuse mount fails

    """

class TimeoutError(SBException):
    """Thrown when an IO operation times out.
    """

class RebaseSnpException(SBException):
    """Thrown for rebase exception
    
    """

class RebaseFullSnpForbidden(RebaseSnpException):
    """Thrown when trying to rebase a full snapshot

    """

class RemoveFullSnpForbidden(RebaseSnpException):
    """Thrown when trying to remove a full snapshot.
    :todo: Check whether this exception is unused and can be removed!
    
    """

class ChmodNotSupportedError(SBException):
    """Thrown when a destination does not support file modes (e.g. some
    ftp servers or FAT filesystems).
    
    """

class NotSupportedError(Exception):
    """Thrown when trying to call a stub.

    """

class NotifyException(SBException) :
    """This Exception is thrown by notifiers and listeners.

    """

class DBusException(SBException) :
    """This Exception is thrown when problems with DBus occurs.

    """
