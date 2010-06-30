#    NSsbackup - lock file facilities
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
"""
:mod:`lock` --- lock file facilities
================================================

.. module:: lock
   :synopsis: Provides common lock file facilities
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

from gettext import gettext as _
import types
import os


from nssbackup.util import file_handling as fam
from nssbackup.util import system
from nssbackup.util import exceptions
from nssbackup.util import log


class ApplicationLock(object):

    def __init__(self, lockfile, processname, pid):
        if not isinstance(lockfile, types.StringTypes):
            raise TypeError("String for parameter `lockfile`expected")
        if not isinstance(processname, types.StringTypes):
            raise TypeError("String for parameter `processname`expected")
        if not isinstance(pid, types.IntType):
            raise TypeError("String for parameter `pid`expected")

        self.__lockfile = lockfile
        self.__processname = processname
        self.__pid = pid
        self.__logger = log.LogFactory.getLogger()

    def __prepare_lock_dir(self):
        _dir = os.path.dirname(self.__lockfile)
        if not fam.exists(_dir):
            try:
                os.mkdir(_dir)
                os.chmod(_dir, 0777)
            except (OSError, IOError), error:
                self.__logger.error("Unable to make lock directory: %s" % error)
                raise exceptions.ApplicationLockError

    def lock(self):
        """Sets a lock file. 
        In 0.3 following changes take effect:
        * use fixed location (users and superusers); ignore settings in configuration files
        * existence of directory `sbackup` with mode 777 is assumed (no sticky bit set) 
        """
        self.__prepare_lock_dir()

        if fam.exists(self.__lockfile):
            if self.__is_lock_valid() is True:
                raise exceptions.InstanceRunningError(\
                    _("Another application instance is already running."))
            else:
                self.__logger.info(_("Invalid lock file found. Is being removed."))
                self.__force_unsetlock()
        try:
            fam.writetofile(self.__lockfile, str(self.__pid))
            self.__logger.debug("Created lockfile `%s` with info `%s`." % (self.__lockfile, str(self.__pid)))
        except (OSError, IOError), error:
            self.__logger.error("Unable to create lock: %s" % error)
            raise exceptions.ApplicationLockError

    def __is_lock_valid(self):
        valid = False
        if fam.exists(self.__lockfile):
            # the lockfile exists, is it valid?
            try:
                last_pid = fam.readfile(self.__lockfile)
                last_pid = int(last_pid)
            except (OSError, IOError, ValueError), error:
                self.__logger.error("Error while reading lockfile: %s" % str(error))
                last_pid = None

            if last_pid is not None:
                if system.pid_exists(pid = str(last_pid), processname = self.__processname):
                    valid = True
        return valid

    def __is_lock_owned(self):
        owned = False
        if fam.exists(self.__lockfile):
            # the lockfile exists, is it valid?
            try:
                last_sb_pid = fam.readfile(self.__lockfile)
                last_sb_pid = int(last_sb_pid)
            except (OSError, IOError, ValueError), error:
                self.__logger.error("Error while reading lockfile: %s" % str(error))
                last_sb_pid = None

            if last_sb_pid is not None:
                if last_sb_pid == self.__pid:
                    owned = True
        return owned

    def unlock(self):
        """Remove lockfile.
        """
        if fam.exists(self.__lockfile):
            if self.__is_lock_owned():
                try:
                    fam.delete(self.__lockfile)
                    self.__logger.debug("Lock file '%s' removed." % self.__lockfile)
                except  (OSError, IOError), _exc:
                    self.__logger.error(_("Unable to remove lock file: %s") % str(_exc))
            else:
                self.__logger.debug("Unable to remove lock: not owned by this process.")
        else:
            self.__logger.warning(_("Unable to remove lock file: File not found."))

    def __force_unsetlock(self):
        """Remove lockfile.
        """
        if fam.exists(self.__lockfile):
            try:
                fam.delete(self.__lockfile)
                self.__logger.debug("Lock file '%s' removed." % self.__lockfile)
            except (OSError, IOError), _exc:
                self.__logger.error(_("Unable to remove lock file: %s") % str(_exc))
        else:
            self.__logger.info(_("Unable to remove lock file: File not found."))
