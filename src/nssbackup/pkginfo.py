#	NSsbackup - package info
#
#   Copyright (c)2010: Jean-Peer Lorenz <peer.loz@gmx.net>
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
#


import os
import socket
from gettext import gettext as _

from nssbackup import util


class Infos(object):
	"""Collects general informations about NSsbackup.
	
	`name` The application's full name
	`version` Full current version
	`description` some description
	
	@todo: Remove the smtpfrom info from here.
	
	"""
	
	NAME = "(Not So) Simple Backup Suite"
	
	VERSION = util.get_version_number()
	
	DESCRIPTION = _("This is a user friendly backup solution for common desktop needs. If you want to help by submitting bugs, by translating or anything else please visit our website.")
	
	WEBSITE = "https://launchpad.net/nssbackup/"

	SNPCURVERSION = "1.5"
	
	COPYRIGHT = "2007-2010 NSsbackup Development team"
	
	AUTHORS = ["Oumar Aziz Ouattara <wattazoum@gmail.com>",
			   "Jean-Peer Lorenz <peer.loz@gmx.net>",
			   "Aigars Mahinovs <aigarius@debian.org>",
			   "Mathias Houngbo <mathias.houngbo@gmail.com>"
			  ]
	TRANSLATORS = _("translator-credits")
	
	#
	hostname = socket.gethostname()
	if "." in hostname:
		mailsuffix = hostname
	else:
		mailsuffix = hostname + ".ext"
	SMTPFROM = _("NSsbackup Daemon <%(login)s@%(hostname)s>") % {
					'login' : os.getenv("USERNAME"), 'hostname': mailsuffix }
