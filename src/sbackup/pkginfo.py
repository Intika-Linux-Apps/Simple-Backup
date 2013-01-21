# This Python file uses the following encoding: utf-8
#
#   Simple Backup - package info
#
#   Copyright (c)2010,2013: Jean-Peer Lorenz <peer.loz@gmx.net>
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

from sbackup import util


class Infos(object):
    """Collects general informations about SBackup.
    
    `name` The application's full name
    `version` Full current version
    `description` some description
    
    @todo: Remove the smtpfrom info from here.
    
    """
    NAME = "Simple Backup Suite"
    VERSION = util.get_version_number()
    DESCRIPTION = _("This is a user friendly backup solution for common desktop needs. If you want to help by submitting bugs, by translating or anything else please visit our website.")
    WEBSITE = "https://launchpad.net/sbackup/"
    COPYRIGHT = "2005-2013 The Simple Backup authors"
    AUTHORS = [_("Maintainers:"),
               "Jean-Peer Lorenz <peer.loz@gmx.net>",
               "Oumar Aziz Ouattara <wattazoum@gmail.com>",
               "",
               _("Former maintainers:"),
               "Aigars Mahinovs",
               "Jonh Wendell",
               "",
               _("Contributors:"),
               "Martin Schaaf",
               "Florian Achleitner",
               "Andreas Sliwka",
               "Rogach (platon7pronko)",
               "Felix Griewald (tiiunder)",
               "Marc Deslauriers",
               "Thibault Godouet",
               "Anton Feenstra",
               "Derek Ditch",
               "Bernd Wurst",
               "Simon Déziel",
               "drakosha",
               "bytebybyte",
               "Marcel Stimberg",
               "Oliver Gerlich"
              ]
    TRANSLATORS = "\n".join([_("translator-credits"),
                             "",
                             "Japanese translation: Thanks to Hajime Mizuno"
                            ])


#TODO: remove snapshot version from here!
    SNPCURVERSION = "1.5"

#TODO: remove hostname and mailsuffix from here!
    hostname = socket.gethostname()
    if "." in hostname:
        mailsuffix = hostname
    else:
        mailsuffix = hostname + ".ext"
    SMTPFROM = _("SBackup Daemon <%(login)s@%(hostname)s>") % {
                    'login' : os.getenv("USERNAME"), 'hostname': mailsuffix }

