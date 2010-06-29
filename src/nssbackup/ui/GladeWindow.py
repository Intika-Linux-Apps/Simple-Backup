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
#    Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum at gmail dot com>
#   Jean-Peer Lorenz <peer.loz@gmx.net>
#   
#   The code is based on code originally written by Dave Reed (12/15/2002)


import os
import os.path

import gtk
import gtk.glade
import gobject

import nssbackup.ui.misc

def search_file(filename, search_path):
    """Given a search path, find file
    """
    file_found = False
    paths = search_path.split(os.pathsep)
    _result = None
    for _path in paths:
        _search = os.path.join(_path, filename)
        if os.path.exists(_search):
            file_found = True
            break
    if file_found:
        _result = os.path.abspath(_search)
    return _result


class GladeWindow(object):
    '''A base class for displaying a GUI developed with Glade; create
    a subclass and add any callbacks and other code; the derived class
    __init__ method needs to call GladeWindow.__init__; callbacks that
    start with on_ are automatically connected'''

    def __init__(self, gladefile, widget_list, handlers, root, parent = None,
                  pull_down_dict = None):

        '''
        __init__(self, filename, top_window, widget_list, pull_down_dict=None):

        filename: filename of the .glade file
        top_window: the glade name of the top level widget (this will then
           be accessible as self.top_window)
        widget_list: a list of glade names; the dictionary self.widgets
           will be created that maps these name to the actual widget object
        pull_down_dict: a dictionary that maps combo names to a tuple of
            strings to put in the combo
            
        @todo: JPL: I don't want to change too much in this release but for\
               later releases: Create the XML external and give it to the\
               widget classes to avoid multiple instantiations!
        '''
        nssbackup.ui.misc.set_default_environment()

#TODO: Needs improvement - not so good style!
        try:
            search_path = GladeWindow.search_path
        except:
            search_path = './'

        fname = search_file(gladefile, search_path)
        self.xml = gtk.glade.XML(fname, root = root, domain = 'nssbackup')

        # connect callbacks
        self.cb_dict = {}
        for f in handlers:
            self.cb_dict[f] = getattr(self, f)
        self.xml.signal_autoconnect(self.cb_dict)

        self.widgets = {}
        for widget in widget_list:
            self.widgets[widget] = self.xml.get_widget(widget)

        if pull_down_dict is not None:
            for widget, lst in pull_down_dict.items():
                self.widgets[widget].set_popdown_strings(lst)

        # set attribute for top_window so it can be accessed as self.top_window
        self.top_window = None

        # window to show when this one is hidden
# TODO: What is this for? Should be handled outside this class!
        self.prev_window = None

        # initialize callback func
        self.cb_func = None

        self.parent = parent


    def set_search_path(cls, path):

        '''set the search path for looking for the .glade files'''

        cls.search_path = path

    set_search_path = classmethod(set_search_path)

    def set_top_window(self, top_window):

        '''set_top_window(self, top_window):

        notebook pages that are in containers need to be able to change
        their top window, especially so the dialog is set_transient_for
        the actual main window
        '''
        self.top_window = top_window

    def set_callback_function(self, cb_func, *cb_args, **cb_kwargs):

        '''set_callback_function(cb_func, *cb_args, **cb_kwargs):

        stores the cb_func and its cb_args and cb_kwargs
        '''
        self.cb_func = cb_func
        self.cb_args = cb_args
        self.cb_kwargs = cb_kwargs

    def show(self, center = 1, prev_window = None, *args):

        '''show(self, center=1, prev_window=None, *args):

        display the top_window widget
        '''

        if prev_window is not None:
            self.prev_window = prev_window
        if center:
            self.top_window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        else:
            self.top_window.set_position(gtk.WIN_POS_NONE)
        self.top_window.show()

    def hide(self):
        '''hide(self):

        hides the current window, shows self.prev_window
        if self.cb_func is not None, it is called with its cb_args
        and cb_kwargs
        '''

        self.top_window.hide()
        if self.prev_window is not None:
            self.prev_window.show()
        if self.cb_func is not None:
            self.cb_func(*self.cb_args, **self.cb_kwargs)
        if self.prev_window is None:
            gtk.main_quit()

    def _show_errmessage(self, message_str, boxtitle = "",
                               headline_str = "", secmsg_str = ""):
        """Shows a complex error message using markup.
        
        @attention: gtk.MessageDialog is not fully thread-safe so it is
                    put in a critical section, here!
        """
        gtk.gdk.threads_enter()
        dialog = gtk.MessageDialog(
                    flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    type = gtk.MESSAGE_ERROR,
                    buttons = gtk.BUTTONS_CLOSE)
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

        # show the message box and destroy it afterwards
        dialog.run()
        dialog.destroy()
        gtk.gdk.threads_leave()


class ProgressbarMixin(object):
    """Extends a class by functionality for showing some action using
    a pulsing progressbar.
    """

    def __init__(self, progressbar, hide_when_stopped = True):
        """Default constructor. The progressbar that should be used must be
        given as parameter. If the optional parameter 'hide_when_stopped' is
        set, the progressbar is only showed if it is active and will be
        hidden afterwards.
        
        @param progressbar: a progressbar object
        @type progressbar: GtkProgressBar
        @param hide_when_stopped: if true, the progressbar is hidden when
                                  not active
        @type hide_when_stopped: Boolean
        
        @return: None
        """
        self._progressbar = progressbar
        self.__pulsetimer_id = None
        self.__hide_when_stopped = hide_when_stopped

    def _init_pulse(self):
        """Convenience method for initializing the progressbar during
        the application's startup.
        """
        self.__pulsetimer_id = None
        if self.__hide_when_stopped:
            self._progressbar.hide()
        self._progressbar.set_text("")
        self._progressbar.set_fraction(0.0)

    def _start_pulse(self):
        """Calling this method shows up the progressbar and starts
        the pulsing.
        
        @attention: The progressbar can be started only once. Stop it before
                    restarting!
        @raise AssertionError: if another pulse timer is already running
        
        @return: None
        """
        if self.__pulsetimer_id is not None:
            raise AssertionError("Another pulse timer is already running!")
        self._progressbar.set_text("")
        self._progressbar.set_fraction(0.0)
        if self.__hide_when_stopped:
            self._progressbar.show()
        self.__pulsetimer_id = gobject.timeout_add(100, self.__pulse)

    def _stop_pulse(self):
        """Calling this method stops the progressbar.

        @attention: The progressbar can not be stopped if it is not running.
                    Start it before stopping!
        @raise AssertionError: if no pulse timer is running
        
        @return: False
        @rtype:  Boolean
        """
        if self.__pulsetimer_id is None:
            raise AssertionError("Nothing to stop - no pulse timer is running!")
        gobject.source_remove(self.__pulsetimer_id)
        self.__pulsetimer_id = None
        if self.__hide_when_stopped:
            self._progressbar.hide()
        self._progressbar.set_text("")
        self._progressbar.set_fraction(0.0)
        return False

    def __pulse(self):
        """Private helper method that actually performs the pulsing.
        
        @return: True
        @rtype:  Boolean        
        """
        self._progressbar.pulse()
        return True
