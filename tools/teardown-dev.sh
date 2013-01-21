#! /bin/bash

################################################################################
#
# Helper script clean up a source code branch
#
#   Copyright (c)2012: Jean-Peer Lorenz <peer.loz@gmx.net>
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
# Usage:
#   execute this script from the root directory of the branch
#   using the command './tools/teardown-dev.sh'
#
################################################################################

STARTPWD=$PWD

echo "-------------------------------------------------------"
echo "Teardown environment development"
echo "-------------------------------------------------------"

#
# check directory
#
METAFILE="METAINFO"
if [ ! -e $METAFILE ]; then
	echo "ERROR: file '"$METAFILE"' not found!"
	echo "Please make sure you are executing this script from the root directory of the branch."; echo
else
	echo -n "Found file '"$METAFILE"' contains:"
	#
	# grab name and current version
	#
	VERSION=$(grep "^VERSION=" $METAFILE|cut -d "=" -f 2 -)
	PKGNAME=$(grep "^PKGNAME=" $METAFILE|cut -d "=" -f 2 -)
	echo -n "    PKGNAME = "$PKGNAME; echo "    VERSION = "$VERSION


        devpath=$STARTPWD"/src"
        binpath=$STARTPWD"/scripts"
        datapath=$STARTPWD"/data"
        iconpath=$STARTPWD"/data/icons"
        uipath=$STARTPWD"/data/ui"
        localedir=$STARTPWD"/po/locale"


	echo "Removing installed languages from '$localedir'"
	if [ -e $localedir ]; then rm -rf $localedir; fi
	echo "Remove file 'metainfo' from source directory"
	if [ -e src/sbackup/metainfo ]; then rm src/sbackup/metainfo; fi
	if [ -e src/sbackup/metainfo.tmp ]; then rm src/sbackup/metainfo.tmp; fi
	echo "Remove file 'resources' from source directory"
	if [ -e src/sbackup/resources ]; then rm src/sbackup/resources; fi
	echo "Remove softlink sbackup-run -> sbackup"
        rm -f $binpath/sbackup
	
	#TODO: how to restore PYTHONPATH?
fi
exit 0


