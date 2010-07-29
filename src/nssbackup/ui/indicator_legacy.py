#    Simple Backup - Indicator application (status icon)
#                    legacy implementation
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

import sys
import gtk


from nssbackup import util
from nssbackup.util.log import LogFactory
from nssbackup.util import constants

from nssbackup.ui import indicator_core
from nssbackup.ui.indicator_core import PyNotifyMixin, SBackupdIndicatorHandler, SBackupdIndicatorBase
from nssbackup.ui import misc


sys.excepthook = misc.except_hook


class SBackupdIndicatorLegacy(SBackupdIndicatorBase, PyNotifyMixin):
    """Graphical front-end in status tray.
    """

    def __init__(self, indicator_hdl):
        if not isinstance(indicator_hdl, SBackupdIndicatorHandler):
            raise TypeError("Parameter of type `SBackupdIndicatorHandler` expected.")

        SBackupdIndicatorBase.__init__(self, indicator_hdl)

        self.logger = LogFactory.getLogger()
        self._indicator = gtk.StatusIcon()

        PyNotifyMixin.__init__(self, logger = self.logger,
                               iconfile = util.get_resource_file(constants.NOTIFICATION_ICON_FILENAME),
                               trayicon = self._indicator)

        self.__init_ctrls()

    def _notify_info(self, profilename, message):
        PyNotifyMixin._notify_info(self, profilename, message)

    def _notify_warning(self, profilename, message):
        PyNotifyMixin._notify_warning(self, profilename, message)

    def _notify_error(self, profilename, message):
        PyNotifyMixin._notify_error(self, profilename, message)

    def __init_ctrls(self):
        self._build_menu()
        self._show_showdialogs_menuitem()
        self._indicator.set_from_file(util.get_resource_file(constants.DEFAULT_ICON_FILENAME))
        self._indicator.connect('popup-menu', self.on_popup_menu)
        self._indicator.set_blinking(False)
        self._indicator.set_visible(True)

    def on_popup_menu(self, widget, button, timestamp): #IGNORE:W0613
        if button == 3:
            if self._menu is not None:
                self._menu.show_all()
                self._menu.popup(None, None, None, button, timestamp)

    def set_status_to_normal(self):
        pass

    def set_status_to_attention(self):
        pass

    def set_status_to_finished(self):
        pass


def main(options):
    exitcode = indicator_core.main(options, SBackupdIndicatorLegacy)
    return exitcode
