#!/usr/bin/env python

#   Copyright (c)2007-2009: Ouattara Oumar Aziz <wattazoum@gmail.com>
#   Copyright (c)2008-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#
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


import gettext
import sys
import gtk
import gtk.glade

from nssbackup.util import get_resource_dir


#----------------------------------------------------------------------

if __name__ == '__main__':
    # i18n init
    application = 'nssbackup'
    locale_dir = get_resource_dir('locale')

    gettext.bindtextdomain(application, locale_dir)
    gettext.textdomain(application)

    gtk.glade.bindtextdomain(application, locale_dir)
    gtk.glade.textdomain(application)

    from nssbackup.ui.SBRestoreGTK import main
    main(sys.argv)
