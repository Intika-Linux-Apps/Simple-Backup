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
#   using the command './tools/release.sh tarball|source-with-orig|
#                                         source-no-orig|update|binary|
#                                         print-paths'
#
################################################################################

STARTPWD=$PWD

#
# grab current version
#
changelog=$STARTPWD"/debian/changelog"
METAINFO=$STARTPWD"/tools/metainfo.sh"
source $METAINFO
APP=$PKGNAME
version_pack=$(grep "^$PKGNAME ($VERFULL" $changelog|cut -d "(" -f 2 -|cut -d ")" -f 1 -)

echo "-------------------------------------------------------"
echo "Packaging tool for "$APP
echo "-------------------------------------------------------"; echo

case "$1" in
    tarball)
        echo "Builds release tarball."
    ;;
    source-with-orig)
        echo "Builds source package."
        echo "Using this option you can create an intitial release within a"
        echo "source version. In this case the .orig tar is uploaded."
    ;;
    source-no-orig)
        echo "Builds source package."
        echo "Using this option you can create an (updated) release within the"
        echo "same source version. The .orig tar is not created."
    ;;
    update)
        echo "Builds an updated source package."
        echo "An .orig tarball from the tarball directory is used."
        echo "Using this option you can create an updated release within the"
        echo "same source version. The .orig tar is not uploaded in that"
        echo "case but the existing .orig tar from the initial release is"
        echo "used."
    ;;
    binary)
        echo "Builds binary packages and publishes debs in local ppa."
    ;;
    print-paths)
        echo "Outputs paths being used and exits."
    ;;
    *)
        echo "ERROR: Called with unknown or missing argument $1" >&2
        echo "Usage:"
        echo "'./tools/release.sh tarball'          - builds release tarball"
        echo "'./tools/release.sh source_with_orig' - builds source package"
        echo "'./tools/release.sh source_no_orig'   - builds source package"
        echo "'./tools/release.sh update'           - updates source package"
        echo "'./tools/release.sh binary'           - builds source and binary"
        echo "                                        package and publishs debs"
        echo "                                        in local ppa."
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

REL_DESTAPPDIR="$APP-$version_pack"

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
DESTDIR=$PACKDIR"/"$version_pack
EXPORTDESTDIR=$DESTDIR"/"$REL_DESTAPPDIR
DEBIANDIR="$EXPORTDESTDIR/$REL_DEBIANDIR"

TAREXT=".tar.gz"
TARNAME=$APP"_"$version_pack
ORIGTARNAME="$TARNAME.orig"
TARNAME="$TARNAME$TAREXT"
ORIGTARNAME="$ORIGTARNAME$TAREXT"

echo "Make sure your debian/CHANGELOG is up-to-date!"; echo

echo "Summary of parameters"
echo "  package: "$APP
echo "  building version: "$version_pack
echo "    full : "$VERFULL
echo "    major: "$VERNUMMAJOR
echo "    minor: "$VERNUMMINOR
echo "    post : "$VERPOST; echo
echo "  source path: $SRC"
echo "  packaging path: $PACKDIR"
echo "  destination: "$DESTDIR
echo "  export path: $EXPORTDESTDIR"
echo "  tarball path: $TARBALLDIR"
echo "  local ppa: "$LOCALPPA
echo "  tar names: $TARNAME and $ORIGTARNAME"

case "$1" in
    print-paths)
      exit 0
    ;;
esac

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
rm -rf "$EXPORTDESTDIR/datas/nssbackup-config-su.desktop"
rm -rf "$EXPORTDESTDIR/datas/nssbackup-config.desktop"
rm -rf "$EXPORTDESTDIR/datas/nssbackup-restore-su.desktop"
rm -rf "$EXPORTDESTDIR/datas/nssbackup-restore.desktop"

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

# remove the Debian specific directory temporarely from the exported source
mv -f "$DEBIANDIR" "$DESTDIR"

case "$1" in
    tarball)
        echo; echo "creating tarball"
        tar -czf $TARNAME $REL_DESTAPPDIR
        mv -f $TARNAME $TARBALLDIR
        echo "Release tarball '$TARNAME' created in '$TARBALLDIR'"
    ;;

    source-with-orig)
        echo; echo "building source package"
        tar -czf $ORIGTARNAME $REL_DESTAPPDIR

        # we move the Debian directory back into the exported source in order
        # to build the deb packages
        mv -f $REL_DEBIANDIR $EXPORTDESTDIR

        cd $EXPORTDESTDIR
        echo; echo "Working directory changed to "$PWD

        debuild -S --lintian-opts --color always
    ;;

    source-no-orig)
        echo; echo "building source package"
        rm -f "$ORIGTARNAME"

        # we move the Debian directory back into the exported source in order
        # to build the deb packages
        mv -f $REL_DEBIANDIR $EXPORTDESTDIR

        cd $EXPORTDESTDIR
        echo; echo "Working directory changed to "$PWD

        debuild -S -sd --lintian-opts --color always
    ;;
    
    update)
        echo; echo "updating source package"
        cp "$TARBALLDIR/$ORIGTARNAME" .
        echo ".orig tarball '$ORIGTARNAME' copied from '$TARBALLDIR'"

        # we move the Debian directory back into the exported source in order
        # to build the deb packages
        mv -f $REL_DEBIANDIR $EXPORTDESTDIR

        cd $EXPORTDESTDIR
        echo; echo "Working directory changed to "$PWD

        debuild -S -sd --lintian-opts --color always
    ;;
    

    binary)
        echo; echo "building binary packages"
        tar -czf $ORIGTARNAME $REL_DESTAPPDIR

        # we move the Debian directory back into the exported source in order
        # to build the deb packages
        mv -f $REL_DEBIANDIR $EXPORTDESTDIR

        cd $EXPORTDESTDIR
        echo; echo "Working directory changed to "$PWD

        debuild --lintian-opts --color always

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

