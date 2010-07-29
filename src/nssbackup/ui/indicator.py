#    Simple Backup - Indicator application (status icon)
#                    targeting Ubuntu 10.04+
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
import appindicator


from nssbackup import util
from nssbackup.util.log import LogFactory
from nssbackup.util import constants

from nssbackup.ui import indicator_core
from nssbackup.ui.indicator_core import PyNotifyMixin, SBackupdIndicatorHandler, SBackupdIndicatorBase
from nssbackup.ui import misc


sys.excepthook = misc.except_hook


class SBackupdIndicator(SBackupdIndicatorBase, PyNotifyMixin):
    """Graphical front-end in status tray.
    """

    def __init__(self, indicator_hdl):
        if not isinstance(indicator_hdl, SBackupdIndicatorHandler):
            raise TypeError("Parameter of type `SBackupdIndicatorHandler` expected.")

        SBackupdIndicatorBase.__init__(self, indicator_hdl)

        self.logger = LogFactory.getLogger()
        self._indicator = appindicator.Indicator(constants.INDICATORAPP_NAME,
                                                 constants.INDICATOR_ACTIVE_ICON,
                                                 appindicator.CATEGORY_APPLICATION_STATUS)

        PyNotifyMixin.__init__(self, logger = self.logger,
                               iconfile = util.get_resource_file(constants.NOTIFICATION_ICON_FILENAME),
                               trayicon = None)

        self.__init_ctrls()

    def _notify_info(self, profilename, message):
        PyNotifyMixin._notify_info(self, profilename, message)

    def _notify_warning(self, profilename, message):
        PyNotifyMixin._notify_warning(self, profilename, message)

    def _notify_error(self, profilename, message):
        PyNotifyMixin._notify_error(self, profilename, message)

    def __init_ctrls(self):
        self._indicator.set_status(appindicator.STATUS_ACTIVE)
        self._indicator.set_attention_icon(constants.INDICATOR_ATTENTION_ICON)

        self._build_menu()
# TODO: Add option to dictionary: show item initially.
        self._indicator.set_menu(self._menu)
        for _item in self._menuitems:
            self._menuitems[_item].show()
        self._show_showdialogs_menuitem()

    def set_status_to_normal(self):
        self._indicator.set_icon(constants.INDICATOR_ACTIVE_ICON)
        self._indicator.set_status(appindicator.STATUS_ACTIVE)

    def set_status_to_attention(self):
        self._indicator.set_status (appindicator.STATUS_ATTENTION)

    def set_status_to_finished(self):
        self._indicator.set_icon(constants.INDICATOR_SUCCESS_ICON)


def main(options):
    exitcode = indicator_core.main(options, SBackupdIndicator)
    return exitcode
