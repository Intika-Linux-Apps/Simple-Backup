#    Simple Backup - handling of preferences
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
:mod:`nssbackup.util.prefs` -- handling of preferences
======================================================

.. module:: prefs
   :synopsis: Handling of preferences applied to all profiles (in contrast to profile settings)
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""


import gconf


from nssbackup.util import structs


FS_BACKEND_GIO = "gio"
FS_BACKEND_FUSE = "fuse"

PREFS_FS_BACKEND = "/apps/sbackup/global-preferences/fs_backend"


_PREFS_DEFAULTS = { PREFS_FS_BACKEND : FS_BACKEND_GIO }
_PREFS_TYPES = { PREFS_FS_BACKEND : gconf.VALUE_STRING }


class Preferences(object):
    __metaclass__ = structs.Singleton

    def __init__(self):
        self._client = gconf.client_get_default ()

    def get(self, key):
        _type = _PREFS_TYPES[key]

        _value = self._get_value(key)
        if _value is None:
            self._set_value(key, _PREFS_DEFAULTS[key])
            _value = self._get_value(key)

        return _value

    def _get_value(self, key):
        _type = _PREFS_TYPES[key]
        _value = None

        if _type == gconf.VALUE_STRING:
            _value = self._client.get_string(key)
            try:
                _value = _value.lower()
            except AttributeError:
                pass

        return _value

    def _set_value(self, key, value):
        _type = _PREFS_TYPES[key]

        if _type == gconf.VALUE_STRING:
            self._client.set_string(key, value)
