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


import gettext, sys, os, traceback
from gettext import gettext as _
from nssbackup.util.log import LogFactory
from nssbackup.managers.UpgradeManager import UpgradeManager
import traceback
from nssbackup.util import get_resource_dir

if __name__ == "__main__" :
	# i18n init
	application = 'nssbackup'
	locale_dir = get_resource_dir('locale')
    
	gettext.bindtextdomain(application, locale_dir)
	gettext.textdomain(application)
	
	if not len(sys.argv) in [2]:
		print _("""
Simple Backup suit command line backup format upgrade
Usage: upgrade-backup backup-target-url
Note: backup-target-url must not include the snapshot subdirectory name, for example:

   /var/backup/

Use simple-restore-gnome for more ease of use.
""")
		sys.exit(1)
	
	try : 
		u = UpgradeManager()
		path = os.path.abspath(sys.argv[1])
		u.upgradeAll(path)
	except Exception, e :
			LogFactory.getLogger().error(str(e))
			LogFactory.getLogger().error(traceback.format_exc())
			