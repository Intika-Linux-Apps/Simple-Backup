################################################################################
#
# Helper script that retrieves name and version of the package
# Intended for use with the release script and other tools.
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
# Usage:
#   include this script into your help script
#   using the 'source' command.
#
################################################################################

#
# name of package and current version are taken from file 'METAINFO'
#
METAFILE="METAINFO"
if [ ! -e $METAFILE ]; then
  echo "ERROR: file '"$METAFILE"' not found!"
  echo "Please execute this script from the root directory of the branch."; echo
  exit 1
#else
#  echo "Found file '"$METAFILE"' contains:"; cat $METAFILE; echo; echo
fi

VERFULL=$(grep "^VERSION=" $METAFILE|cut -d "=" -f 2 -)
VERNUM=$(echo $VERFULL|cut -d "~" -f 1 -)
VERPOST=$(echo $VERFULL|cut -d "~" -f 2 -)
VERNUMMAJOR=$(echo $VERNUM|cut -d "." -f 1,2 -)
VERNUMMINOR=$(echo $VERNUM|cut -d "." -f 3 -)

PKGNAME=$(grep "^PKGNAME=" $METAFILE|cut -d "=" -f 2 -)

