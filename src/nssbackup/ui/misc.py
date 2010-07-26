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

from gettext import gettext as _

import gtk
import gobject
import pango
import types
import traceback


from nssbackup.pkginfo import Infos
from nssbackup.util import constants
from nssbackup.util import system
from nssbackup.util import log
from nssbackup import util


MODEL_COLUMN_INDEX_VALUE = 0
MODEL_COLUMN_INDEX_KEY = 1


def set_model(widget, values):
    """
    sorted by dictionary keys
    """
    if not isinstance(values, types.DictionaryType):
        raise TypeError

    # query types
    _entry = values.popitem()
    values[_entry[0]] = _entry[1]    # re-add removed pair
    _keytype = type(_entry[0])
    _valtype = type(_entry[1])

    # ensure all dictionary entries are of same type
    for _entry in values:
        if not isinstance(_entry, _keytype):
            raise TypeError
        if not isinstance(values[_entry], _valtype):
            raise TypeError

    _model = gtk.ListStore(_valtype, _keytype)
    _keys = values.keys()
    _keys.sort()

    for _key in _keys:
        _model.append([values[_key], _key])

    widget.set_model(_model)
    _cell = gtk.CellRendererText()
    widget.pack_start(_cell, True)
    widget.add_attribute(_cell, 'text', MODEL_COLUMN_INDEX_VALUE)
    return _model


def open_uri(uri, timestamp = 0):
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


def label_set_autowrap(widget):
    """Make labels automatically re-wrap if their containers are resized.
    Accepts label or container widgets.    For this to work the label in the
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
    law, lah = layout.get_size() #IGNORE:W0612
    if lh_old != lah:
        widget.set_size_request(-1, lah / pango.SCALE)

def show_infodialog(message_str, parent, headline_str = "", secmsg_str = ""):
    """Creates und displays a modal dialog box. Main purpose is
    displaying of error messages.
    
    @param message_format: error message to show
    @type message_format: String
    
    """
    __show_msgdialog(message_str = message_str, msgtype = gtk.MESSAGE_INFO,
                    parent = parent, boxtitle = "",
                    headline_str = headline_str, secmsg_str = secmsg_str)

def show_warndialog(message_str, parent, headline_str = "", secmsg_str = ""):
    """Creates und displays a modal dialog box. Main purpose is
    displaying of error messages.
    
    @param message_format: error message to show
    @type message_format: String
    
    """
    __show_msgdialog(message_str = message_str, msgtype = gtk.MESSAGE_WARNING,
                    parent = parent, boxtitle = "",
                    headline_str = headline_str, secmsg_str = secmsg_str)

def show_errdialog(message_str, parent, headline_str = "", secmsg_str = ""):
    """Creates und displays a modal dialog box. Main purpose is
    displaying of error messages.
    
    @param message_format: error message to show
    @type message_format: String
    """
    __show_msgdialog(message_str = message_str, msgtype = gtk.MESSAGE_ERROR,
                    parent = parent, boxtitle = "",
                    headline_str = headline_str, secmsg_str = secmsg_str)

def show_errdialog_threaded(message_str, parent, headline_str = "", secmsg_str = ""):
    gtk.gdk.threads_enter()
    __show_msgdialog(message_str = message_str, msgtype = gtk.MESSAGE_ERROR,
                    parent = parent, boxtitle = "",
                    headline_str = headline_str, secmsg_str = secmsg_str)
    gtk.gdk.threads_leave()

def __show_msgdialog(message_str, msgtype, parent, boxtitle = "",
                    headline_str = "", secmsg_str = ""):
    """Creates und displays a modal dialog box. Main purpose is
    displaying of error messages.
    
    Do not use markup for the strings.
    
    @param message_format: error message to show
    @type message_format: String
    
    @todo: Add proper escaping before markup is applied to the headlline.
    """
    # in compliance with Gnome HIG a 'Close' button instead of 'OK' is used

    dialog = msgdialog(message_str = message_str, msgtype = msgtype, parent = parent, boxtitle = boxtitle,
                         buttons = gtk.BUTTONS_CLOSE, headline_str = headline_str, secmsg_str = secmsg_str)

    # the message box is showed
    dialog.run()
    dialog.destroy()

def msgdialog(message_str, msgtype, parent, boxtitle = "", buttons = gtk.BUTTONS_CLOSE,
                    headline_str = "", secmsg_str = ""):
    """Creates und displays a modal dialog box. Main purpose is
    displaying of error messages.
    
    Do not use markup for the strings.
    
    @param message_format: error message to show
    @type message_format: String
    
    @todo: Add proper escaping before markup is applied to the headlline.
    """
    # in compliance with Gnome HIG a 'Close' button instead of 'OK' is used

    dialog = gtk.MessageDialog(parent = parent, type = msgtype,
                flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                buttons = buttons)

    icon_file = util.get_resource_file(constants.DEFAULT_ICON_FILENAME)
    dialog.set_icon_from_file(icon_file)

    if boxtitle.strip() != "":
        dialog.set_title(boxtitle)

    _hdl = headline_str.strip(" \n\t")
    if _hdl != "":
        _hdl = "<b>%s</b>\n\n" % _hdl
    _msg = "%s%s" % (_hdl, message_str)
    dialog.set_markup(_msg)

    # an optional secondary message is added
    _sec = secmsg_str.strip(" \n\t")
    if _sec != "":
        _sec = "<small>%s</small>" % (_sec)
        dialog.format_secondary_markup(_sec)
    return dialog


def infodialog_standalone(message_str, boxtitle, headline_str = "", secmsg_str = "", sticky = True):
    return msgdialog_standalone(message_str = message_str, msgtype = gtk.MESSAGE_INFO,
                                  boxtitle = boxtitle, headline_str = headline_str, secmsg_str = secmsg_str,
                                  sticky = sticky)


def warndialog_standalone(message_str, boxtitle, headline_str = "", secmsg_str = "", sticky = True):
    return msgdialog_standalone(message_str = message_str, msgtype = gtk.MESSAGE_WARNING,
                                  boxtitle = boxtitle, headline_str = headline_str, secmsg_str = secmsg_str,
                                  sticky = sticky)


def errdialog_standalone(message_str, boxtitle, headline_str = "", secmsg_str = "", sticky = True):
    return msgdialog_standalone(message_str = message_str, msgtype = gtk.MESSAGE_ERROR, boxtitle = boxtitle,
                                  headline_str = headline_str, secmsg_str = secmsg_str, sticky = sticky)


def msgdialog_standalone(message_str, msgtype, boxtitle, buttons = gtk.BUTTONS_CLOSE,
                    headline_str = "", secmsg_str = "", sticky = True):
    """Creates and displays a standalone dialog box. Main purpose is
    displaying of error messages within the indicator application.
    
    Do not use markup for the strings.
    
    @param message_format: error message to show
    @type message_format: String
    
    @todo: Add proper escaping before markup is applied to the headlline.
    """
    # in compliance with Gnome HIG a 'Close' button instead of 'OK' is used

    assert boxtitle.strip() != ""

    dialog = msgdialog(message_str = message_str, msgtype = msgtype, parent = None, boxtitle = boxtitle,
                       buttons = buttons, headline_str = headline_str, secmsg_str = secmsg_str)

    dialog.set_property("skip-pager-hint", False)
    dialog.set_property("skip-taskbar-hint", False)

    if sticky is True:
        dialog.stick()
        dialog.set_urgency_hint(True)
#        dialog.set_keep_above(True) # be not to urgent

    return dialog


def show_about_dialog(set_transient_for = None):
    _icon_file = util.get_resource_file(constants.DEFAULT_ICON_FILENAME)
    about = gtk.AboutDialog()
    about.set_name(Infos.NAME)
    about.set_version(Infos.VERSION)
    about.set_comments(Infos.DESCRIPTION)
    if set_transient_for is not None:
        about.set_transient_for(set_transient_for)
    about.set_copyright(Infos.COPYRIGHT)
    about.set_translator_credits(Infos.TRANSLATORS)
    about.set_authors(Infos.AUTHORS)
    if not system.is_superuser():
        about.set_website(Infos.WEBSITE)
    about.set_logo(gtk.gdk.pixbuf_new_from_file(_icon_file))
    about.set_icon_from_file(_icon_file)
    about.run()
    about.destroy()


def set_watch_cursor(widget):
    watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
    try:
        widget.window.set_cursor(watch)
    except AttributeError, error:
        print "Ignored error when setting cursor: %s" % error


def unset_cursor(widget):
    try:
        widget.window.set_cursor(None)
    except AttributeError, error:
        print "Ignored error when un-setting cursor: %s" % error


def _common_except_hook(etype, evalue, etb):
    _logger = log.LogFactory.getLogger()
    _lines = traceback.format_exception(etype, evalue, etb)
    _lines = "".join(_lines)
    _lines.strip()
    _logger.error("Uncaught exception: %s" % evalue)
    _logger.error(_lines)
    _message_str = _("An uncaught error occurred. Close this message window and restart the application.\n\nPlease report this error on https://bugs.launchpad.net/nssbackup.\n\n%s") % (evalue)
    _headline_str = _("Sorry, this should not have happened")
    _secmsg_str = "%s" % _lines
    return (_headline_str, _message_str, _secmsg_str)


def except_hook(etype, evalue, etb):
    _headline_str, _message_str, _secmsg_str = _common_except_hook(etype, evalue, etb)
    show_errdialog(message_str = _message_str,
                     parent = None, headline_str = _headline_str,
                     secmsg_str = _secmsg_str)


def except_hook_threaded(etype, evalue, etb):
    _headline_str, _message_str, _secmsg_str = _common_except_hook(etype, evalue, etb)
    gobject.idle_add(show_errdialog_threaded, _message_str,
                     None, _headline_str,
                     _secmsg_str)
