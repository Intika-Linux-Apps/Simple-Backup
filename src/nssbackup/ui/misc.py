#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# Authors :
#   Jean-Peer Lorenz <peer.loz@gmx.net>

"""Module containing commonly used helper classes and functions related to UI
"""

import gtk

def open_uri(uri, timestamp=0):
	"""Convenience function for opening a given URI with the default
	application.
	"""
	# The function 'show_uri()' is available in PyGTK 2.14 and above.
	if gtk.pygtk_version >= (2, 14, 0):
		gtk.show_uri(gtk.gdk.screen_get_default(), uri, timestamp)
	else:
		try:
			import gnome
			gnome.url_show(uri)
		except ImportError:
			pass
