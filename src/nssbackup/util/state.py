#    NSsbackup - state of backup process
#
#   Copyright (c)2009: Jean-Peer Lorenz <peer.loz@gmx.net>
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
:mod:`state` --- state of backup process
====================================================================

.. module:: state
   :synopsis: Defines a class representing the state of the backup process
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""


from nssbackup.util import notifier


class NSsbackupState(notifier.Subject):
    """Represents a single state and according data within
    the backup process. Whenever interesting data changes
    one can change the state and it is published to registered
    observers.
    
    :todo: We could add an urgency etc.!
    
    """
    def __init__(self):
        super(NSsbackupState, self).__init__()
        self.__state = 'unknown'
        self.__profilename = None
        self.__recent_error = None

    def set_state(self, state):
        """Observers are only notified, if the state was changed.
        
        """
        self.__state = state
        self.notify()
        
    def get_state(self):
        return self.__state
    
    def set_profilename(self, profilename):
        self.__profilename = profilename
        
    def get_profilename(self):
        return self.__profilename

    def set_recent_error(self, recent_error):
        self.__recent_error = recent_error
        
    def get_recent_error(self):
        return self.__recent_error
