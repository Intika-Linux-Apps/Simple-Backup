#!/usr/bin/env python
#
#    Simple Backup - Launcher script for configuration GUI
#
#   Copyright (c)2008-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#   Copyright (c)2007-2009: Ouattara Oumar Aziz <wattazoum@gmail.com>
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


if __name__ == '__main__':

    import sys

    from nssbackup.util import system
    system.set_default_environment()
    system.set_display_from_session()
    system.set_gio_env_from_session()    

    from nssbackup.util import get_locale_dir, get_locale_domain
    application = get_locale_domain()
    locale_dir = get_locale_dir()

    import gettext
    gettext.bindtextdomain(application, locale_dir)
    gettext.textdomain(application)

    import gtk, gtk.glade
    gtk.glade.bindtextdomain(application, locale_dir)
    gtk.glade.textdomain(application)

    from nssbackup.ui.SBConfigGTK import main
    main(sys.argv)
