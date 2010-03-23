#! /bin/bash

################################################################################
#
# Helper script that backups the current branch:
#
# * the backups are named with version and date
# * if the application 7za is available, it is used for compression
#   (results in 50% smaller archives than using tar+gzip)
# * otherwise tar+gzip is used
# * the archives are stored in a directory named 'archives' that is
#   located in the parent directory of this branch
#
# * no files are written or modified within the actual branch
#
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
#   execute this script from the root directory of the branch
#   using the command './tools/backup.sh'
#
################################################################################

STARTPWD=$PWD

#
# grab current version
#
METAINFO=$STARTPWD"/tools/metainfo.sh"
source $METAINFO
APP=$PKGNAME

echo "-------------------------------------------------------"
echo "Backup tool for "$APP" development"
echo "-------------------------------------------------------"; echo

EXCLUDES="--exclude='*.pyc'"
DATE_TIME=`date "+%Y.%m.%d-%H.%M.%S"`
DESTDIR=$STARTPWD"/../archives"

#
# determination of source directory and archive name
# if no folder named with major version number is found
# try the application's name (trunk)
#
SOURCE="../"$VERNUMMAJOR
ARNAME=$APP

if [ -d $SOURCE ]; then
  ARNAME=$ARNAME"-"$VERNUMMAJOR
else
  echo $SOURCE" does not exist."
  SOURCE="../"$APP
  echo "Now trying trunk: "$SOURCE
  if [ -d $SOURCE ]; then
    ARNAME=$ARNAME"-trunk"
  else
    echo "ERROR: "$SOURCE" does not exist."
    exit 1
  fi
fi

#
# determination of archive type/compression to use
#
COMPRAPP="7za"
echo "Checking for external compression application"
if type $COMPRAPP >/dev/null 2>&1 ; then
  echo "  "$COMPRAPP" is installed."
  EXT="7z"
else 
  echo "  "$COMPRAPP" is not installed."
  COMPRAPP="gzip"
  EXT="tar.gz"
fi

#
# the final path to the archive
#
ARPATH=$DESTDIR"/"$ARNAME"_"$DATE_TIME.$EXT

echo; echo "Summary of used parameters:"
echo "  Backing up: "$ARNAME
echo "  Command: "$COMPRAPP
echo "  Source: "$SOURCE
echo "  Target: "$ARPATH

echo; echo "Checking directories"
if [ -d $SOURCE ]; then
  echo "  Source exists."
else
  echo "ERROR: Source does not exist."
  exit 1
fi
if [ -d $DESTDIR ]; then
  echo "  Target exists."
else
  echo "  Target created."
  mkdir -p $DESTDIR
fi

echo; echo "Creating backup: "$ARPATH

case "$COMPRAPP" in
    7za)
        echo "  using 7z."; echo
        tar c $EXCLUDES $SOURCE | 7za a -si -bd $ARPATH
    ;;

    gzip)
        echo "  using gzip."; echo
        tar cjf $ARPATH $EXCLUDES $SOURCE
    ;;

    *)
        echo "ERROR: unknown application: "$COMPRAPP
        exit 1
    ;;
esac

echo; echo "Finished!"
exit 0

