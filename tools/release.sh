#! /bin/bash

################################################################################
#
# Helper script that ease the building of release tarballs
# and deb packages:
#
# * the tarballs and packages are stored in a directory named 'packaging'
#   that is located in the parent directory of this branch
#
# * no files are written/modified within the actual branch
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
#   using the command './tools/release.sh tarball|source|binary'
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
echo "Packaging tool for "$APP
echo "-------------------------------------------------------"; echo

case "$1" in
    tarball)
        echo "Building release tarball."
    ;;
    source)
        echo "Building release tarball and source package."
    ;;
    binary)
        echo "Building release tarball and binary packages."
        echo "Publishing debs in local ppa."
    ;;
    *)
        echo "ERROR: Called with unknown or missing argument $1" >&2
        echo "Usage:"
        echo "'./tools/release.sh tarball' - builds release tarball"
        echo "'./tools/release.sh source'  - builds tarball and source package"
        echo "'./tools/release.sh binary'  - builds tarball, source and binary package"
        echo "                               and publishs debs in local ppa."
        echo
        exit 1
    ;;
esac

#
# building of pathnames
# the working directory (root of branch) is set as source
#
PRE=$STARTPWD
SRC=$PRE

REL_DESTAPPDIR="$APP-$VERFULL"

REL_PACKDIR="../packaging"
REL_LOCALPPA="$REL_PACKDIR/localppa"
REL_TARBALLDIR="$REL_PACKDIR/tarballs"
REL_DEBIANDIR="debian"

#
# directories where packages of *all* versions are stored
#
PACKDIR="$PRE/$REL_PACKDIR"
LOCALPPA="$PRE/$REL_LOCALPPA"
TARBALLDIR="$PRE/$REL_TARBALLDIR"

#
# directories for this particular version
#
DESTDIR=$PACKDIR"/"$VERFULL
EXPORTDESTDIR=$DESTDIR"/"$REL_DESTAPPDIR
DEBIANDIR="$EXPORTDESTDIR/$REL_DEBIANDIR"

TAREXT=".tar.gz"
TARNAME=$APP"_"$VERFULL
ORIGTARNAME="$TARNAME.orig"
TARNAME="$TARNAME$TAREXT"
ORIGTARNAME="$ORIGTARNAME$TAREXT"

echo "Make sure your debian/CHANGELOG is up-to-date!"; echo

echo "Summary of parameters"
echo "  package: "$APP
echo "  building version: "$VERFULL
echo "    major: "$VERNUMMAJOR
echo "    minor: "$VERNUMMINOR
echo "    post:  "$VERPOST; echo
echo "  source path: $SRC"
echo "  packaging path: $PACKDIR"
echo "  destination: "$DESTDIR
echo "  export path: $EXPORTDESTDIR"
echo "  tarball path: $TARBALLDIR"
echo "  local ppa: "$LOCALPPA
echo "  tar names: $TARNAME and $ORIGTARNAME"

echo; echo "creating directories"
if [ -d $PACKDIR ]; then
  echo "  packaging dir exists"
else
  echo "  packaging dir created"
  mkdir -p $PACKDIR
fi
if [ -d $LOCALPPA ]; then
  echo "  local ppa dir exists"
else
  echo "  local ppa dir created"
  mkdir -p $LOCALPPA
fi
if [ -d $TARBALLDIR ]; then
  echo "  tarball dir exists"
else
  echo "  tarball dir created"
  mkdir -p $TARBALLDIR
fi

echo; echo "cleaning of destination directory $DESTDIR"
if [ -d $DESTDIR ]; then
  rm -rf $DESTDIR
fi
mkdir -p $DESTDIR

cd $DESTDIR
echo; echo "Working directory changed to: $PWD"

##############################################################################
echo; echo "exporting sources"; echo "from "$SRC; echo "to "$EXPORTDESTDIR
cp -rf $SRC $EXPORTDESTDIR

echo; echo "clean exported sources"
find $DESTDIR -name '*.pyc' -exec rm -f '{}' \;
find $DESTDIR -name '*~' -exec rm -f '{}' \;
find $DESTDIR -name '*.bak' -exec rm -f '{}' \;
rm -rf "$EXPORTDESTDIR/.bzr"
rm -rf "$EXPORTDESTDIR/.bzrignore"
rm -rf "$EXPORTDESTDIR/.pydevproject"
rm -rf "$EXPORTDESTDIR/.project"
rm -rf "$EXPORTDESTDIR/.settings"
rm -rf "$EXPORTDESTDIR/setup.py"
rm -rf "$EXPORTDESTDIR/src/nssbackup/resources"
rm -rf "$EXPORTDESTDIR/src/nssbackup/metainfo"

# 'tests', 'tools', and 'doc' are removed; later re-add 'doc' when build
rm -rf "$EXPORTDESTDIR/tests"
rm -rf "$EXPORTDESTDIR/doc"
rm -rf "$EXPORTDESTDIR/tools"

# clean Debian dir
rm -rf "$DEBIANDIR/.bzr"
rm -rf "$DEBIANDIR/.bzrignore"
rm -rf "$DEBIANDIR/.pydevproject"
rm -rf "$DEBIANDIR/.project"
rm -rf "$DEBIANDIR/.settings"

#echo "Debian: $DEBIANDIR"
#echo "Destdir: $DESTDIR"

# remove the Debian specific directory temporarely from the exported source
mv -f "$DEBIANDIR" "$DESTDIR"

##############################################################################
echo; echo "creating tarballs "
tar -czf $TARNAME $REL_DESTAPPDIR
cp $TARNAME $ORIGTARNAME
#tar -czf $ORIGTARNAME $REL_DESTAPPDIR

mv -f $TARNAME $TARBALLDIR
echo "Release tarball '$TARNAME' created in '$TARBALLDIR'"

#
# ensure we are in $DESTDIR
# we move the Debian directory back into the exported source in order
# to build the deb packages
#
mv -f $REL_DEBIANDIR $EXPORTDESTDIR

cd $EXPORTDESTDIR
echo; echo "Working directory changed to "$PWD

case "$1" in
    tarball)
#        echo; echo "Removing source folder "$EXPORTDESTDIR
#        rm -rf $EXPORTDESTDIR
    ;;

    source)
        echo; echo "building source package"
        debuild -S --lintian-opts --color always

#        echo; echo "Removing source folder "$EXPORTDESTDIR
#        rm -rf $EXPORTDESTDIR
    ;;

    binary)
        echo; echo "building binary packages"
        debuild --lintian-opts --color always

#        echo; echo "Removing source folder "$EXPORTDESTDIR
#        rm -rf $EXPORTDESTDIR

        echo; echo "Publishing debs in local repository "$LOCALPPA
        cd $DESTDIR
        cp -f *.deb $LOCALPPA
        cd $LOCALPPA
        dpkg-scanpackages ./ /dev/null | gzip > Packages.gz
    ;;

    *)
        echo; echo "called with unknown or missing argument: $1" >&2
        echo "Please use 'tarball', 'binary', or 'source' as parameter."
        exit 1
    ;;
esac

echo; echo "Removing source folder "$EXPORTDESTDIR
rm -rf $EXPORTDESTDIR

cd $STARTPWD
echo; echo "Working directory changed to "$PWD
echo; echo "Finished!"
exit 0

