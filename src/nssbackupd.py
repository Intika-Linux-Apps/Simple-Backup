#!/usr/bin/env python

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
# Authors :
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum at gmail dot com>

import sys
import gettext
import subprocess
import time

from nssbackup.nssbackupd import main
from nssbackup.util import getResource

# i18n init
application = 'nssbackup'
locale_dir = getResource('locale')

gettext.bindtextdomain(application, locale_dir)
gettext.textdomain(application)

print "Now launching DBus service"
dbus_launcher = getResource('nssbackup_service')
pid = subprocess.Popen([dbus_launcher]).pid
print "pid: %s" % pid

print "Now launching tray gui"
tray_gui = getResource('nssbackup_traygui')
pid = subprocess.Popen([tray_gui]).pid
print "pid: %s" % pid

print "Now launching backup daemon (main func)"
main(sys.argv)
