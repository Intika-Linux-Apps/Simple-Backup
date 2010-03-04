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

import os
import gtk
import pango


# default values for environment variable if not set
# see: http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
__ENVVAR_XDG_DATA_DIRS = "XDG_DATA_DIRS"
__DEFAULT_XDG_DATA_DIRS = "/usr/local/share/:/usr/share/"


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

def set_default_environment():
	"""Sets required environment variables to their specified default
	values if not defined. This can happen e.g. some root shells where
	no environment variable for the freedesktop.org base directories
	are defined.
	
	"""
	var = __ENVVAR_XDG_DATA_DIRS
	defval = __DEFAULT_XDG_DATA_DIRS
	val = os.getenv(var)
	if val is None:
		os.putenv(var, defval)
		
def label_set_autowrap(widget): 
	"""Make labels automatically re-wrap if their containers are resized.
	Accepts label or container widgets.	For this to work the label in the
	glade file must be set to wrap on words.
	
	from http://stackoverflow.com/questions/1893748/pygtk-dynamic-label-wrapping
	"""
	if isinstance(widget, gtk.Container):
		children = widget.get_children()
		for i in xrange(len(children)):
			label_set_autowrap(children[i])
	elif isinstance(widget, gtk.Label) and widget.get_line_wrap():
		widget.connect_after("size-allocate", _label_size_allocate)

def _label_size_allocate(widget, allocation):
	"""Callback which re-allocates the size of a label.

	from http://stackoverflow.com/questions/1893748/pygtk-dynamic-label-wrapping
	"""
	layout = widget.get_layout()
	lw_old, lh_old = layout.get_size()
	# fixed width labels
	if lw_old / pango.SCALE == allocation.width:
		return
	# set wrap width to the pango.Layout of the labels
	layout.set_width(allocation.width * pango.SCALE)
	
	# law is unused.
	law, lah = layout.get_size()# pylint: disable-msg=W0612
	if lh_old != lah:
		widget.set_size_request(-1, lah / pango.SCALE)
		
def show_errdialog(message_str, boxtitle = "",
					headline_str = "", secmsg_str = ""):
	"""Creates und displays a modal dialog box. Main purpose is
	displaying of error messages.
	
	@param message_format: error message to show
	@type message_format: String
	
	@todo: Should we use the button OK or CLOSE?
	@todo: Refactor this as function into UI.util module.
	"""
	dialog = gtk.MessageDialog(
				flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
				type = gtk.MESSAGE_ERROR,
				buttons=gtk.BUTTONS_CLOSE)
	if boxtitle.strip() != "":
		dialog.set_title( boxtitle )
		
	_hdl = headline_str.strip(" \n\t")
	if _hdl != "":
		_hdl = "<b>%s</b>\n\n" % _hdl
	_msg = "%s%s" % ( _hdl, message_str )
	dialog.set_markup(_msg)

	# an optional secondary message is added
	_sec = secmsg_str.strip(" \n\t")
	if _sec != "":
		_sec = "<small>%s</small>" % ( _sec )
		dialog.format_secondary_markup(_sec)
		
	# the message box is showed
	dialog.run()
	dialog.destroy()

