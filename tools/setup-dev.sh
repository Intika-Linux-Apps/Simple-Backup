#! /bin/bash

################################################################################
#
# Helper script to setup environment for running sbackup from
# within a source code branch
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
#   using the command './tools/setup-dev.sh'
#	Exit development environment using 'exit'
#
################################################################################


STARTPWD=$PWD

echo "-------------------------------------------------------"
echo "Setting environment development"
echo "-------------------------------------------------------"

#TODO: use code snippet from metainfo.sh!
#METAINFO=$STARTPWD"/tools/metainfo.sh"
#source $METAINFO

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

	#
	# add path of current branch to PYTHONPATH
	# idea: wrapper script to bend pythonpath for testing/developing!
	export PYTHONPATH=$devpath":"$PYTHONPATH

	#
	# build languages (po -> mo) in tree; will be removed when cleaning tree
	# note: ${langfull/\/*\//} is explained on man bash under "Parameter Expansion
	#
	echo "Installing languages in '$localedir'"
	for langfull in $STARTPWD/po/*.po; do langshort=${langfull/\/*\//}; lang=${langshort%.po}; echo -n "$lang "; install -d "$localedir/$lang/LC_MESSAGES/"; msgfmt "$langfull" -o "$localedir/$lang/LC_MESSAGES/sbackup.mo"; done

	# fill templates
	echo; echo "Create file 'metainfo' within source directory"
	sed s+@version@+$VERSION+ src/sbackup/metainfo.in > src/sbackup/metainfo.tmp
	sed s+@pkgname@+$PKGNAME+ src/sbackup/metainfo.tmp > src/sbackup/metainfo
	echo "Create file 'resources' within source directory"
	echo "$localedir" > src/sbackup/resources
	echo "$binpath" >> src/sbackup/resources
	echo "$datapath" >> src/sbackup/resources
	echo "$iconpath" >> src/sbackup/resources
	echo "$uipath" >> src/sbackup/resources

	# create softlink sbackup-run -> sbackup
	ln -sf $binpath/sbackup-run $binpath/sbackup

	#
	# change directory into 'scripts' directory
	#
	cd $STARTPWD"/scripts"

	# modify and show a distinct prompt in development environment
	export PROMPT_COMMAND="echo -n '=SBACKUP DEVELOPMENT= '"

	/bin/bash

	# when finished, clean up everything
	cd $STARTPWD
	./tools/teardown-dev.sh

fi

