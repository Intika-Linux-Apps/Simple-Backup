#   Simple Backup - general observer-notfifier implementation
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


from sbackup.util import constants


# Handling of states and information provided by Dbus objects is
# not ideal. Improve!


class Subject(object):
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if not observer in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, modifier = None):
        for observer in self._observers:
            if modifier != observer:
                observer.update(self)



class Observer(object):
    def update(self, subject):
        raise NotImplementedError("Abstract method must be overridden in "\
                                  "derived class!")


class SBackupState(Subject):
    """Represents a single state and according data within
    the backup process. Whenever interesting data changes
    one can change the state and it is published to registered
    observers.
    
    :todo: Add type checking in setter methods!
    
    """
    def __init__(self):
        Subject.__init__(self)

        self.__state = 'unknown'
        self.__urgency = 'info'
        self.__profilename = constants.PROFILE_UNKNOWN
        self.__space_required = constants.SPACE_REQUIRED_UNKNOWN
        self.__is_full = -1
        self.__target = constants.TARGET_UNKNOWN
        self.__recent_error = 'None'
        self.clear_backup_properties()

    def clear_backup_properties(self):
        self.__profilename = constants.PROFILE_UNKNOWN
        self.__space_required = constants.SPACE_REQUIRED_UNKNOWN
        self.__is_full = -1
        self.__target = constants.TARGET_UNKNOWN

    def set_state(self, state):
        """Observers are only notified, if the state has changed.
        
        """
        self.__state = state
        self.notify()

    def get_state(self):
        return self.__state

    def set_urgency(self, urgency):
        """The urgency is used to distinguish several types of events.
        There are following urgencies:
        
        -critical
        -error
        -warning
        -info.
        
        """
        self.__urgency = urgency

    def get_urgency(self):
        return self.__urgency

    def set_profilename(self, profilename):
        self.__profilename = profilename

    def get_profilename(self):
        return self.__profilename

    def set_recent_error(self, recent_error):
        self.__recent_error = recent_error

    def get_recent_error(self):
        return self.__recent_error

    def set_is_full(self, is_full):
        self.__is_full = is_full

    def set_target(self, target):
        self.__target = target

    def get_target(self):
        return self.__target

    def set_space_required(self, space):
        self.__space_required = space

    def get_space_required(self):
        return self.__space_required
