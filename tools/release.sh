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

#TODO: check version in METAINFO against version in changelog when preparing releases

export GZIP="-9"

startpwd=$PWD

#
# grab current version
#
changelog=$startpwd"/debian/changelog"
metainfofile=$startpwd"/tools/metainfo.sh"
source $metainfofile
appname=$PKGNAME

version_pack=$(grep --max-count=1 "^$PKGNAME ($VERFULL" $changelog|cut -d "(" -f 2 -|cut -d ")" -f 1 -)

echo "-------------------------------------------------------"
echo "Packaging tool for "$appname
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
        echo "'./tools/release.sh source-with-orig' - builds source package"
        echo "'./tools/release.sh source-no-orig'   - builds source package"
        echo "'./tools/release.sh update'           - updates source package"
        echo "'./tools/release.sh binary'           - builds source and binary"
        echo "                                        package and publishs debs"
        echo "                                        in local ppa."
        echo "'./tools/release.sh print-paths'      - shows used paths and exits"
        echo
        exit 1
    ;;
esac

#
# building of pathnames
# the working directory (root of branch) is set as source
#
pre=$startpwd
SRC=$pre

REL_PACKDIR="../packaging"
REL_LOCALPPA="$REL_PACKDIR/localppa"
REL_TARBALLDIR="$REL_PACKDIR/tarballs"
REL_DEBIANDIR="debian"

#
# directories where packages of *all* versions are stored
#
PACKDIR="$pre/$REL_PACKDIR"
LOCALPPA="$pre/$REL_LOCALPPA"
TARBALLDIR="$pre/$REL_TARBALLDIR"
TAREXT=".tar.gz"

#
# directories for this particular version
#
# tarball uses directories not tied to a particular distribution (e.g. lucid)
# no orig-tar when building a release tarball
if test "$1" = "tarball"; then
    REL_DESTAPPDIR="$appname-$VERFULL"
    destdir=$PACKDIR"/"$VERFULL
    TARNAME=$appname"_"$VERFULL
else
    REL_DESTAPPDIR="$appname-$version_pack"
    destdir=$PACKDIR"/"$version_pack
    TARNAME=$appname"_"$version_pack
    ORIGTARNAME="$TARNAME.orig$TAREXT"
fi

TARNAME="$TARNAME$TAREXT"

exportdestdir=$destdir"/"$REL_DESTAPPDIR
DEBIANDIR="$exportdestdir/$REL_DEBIANDIR"


echo "Make sure your debian/CHANGELOG is up-to-date!"; echo

echo "Changelog: $changelog"
echo "==============================================================================="
head $changelog
echo "==============================================================================="; echo

echo "Summary of parameters"
echo "  From Metafile:"
echo "    VERFULL: "$VERFULL
#echo "    VERNUM: "$VERNUM
#echo "    VERPOST: "$VERPOST
#echo "    VERNUMMAJOR: "$VERNUMMAJOR
#echo "    VERNUMMINOR: "$VERNUMMINOR
echo "    PKGNAME: "$PKGNAME
echo
echo "  package: "$appname
echo "  building version: "$version_pack
echo "    full : "$VERFULL
#echo "    major: "$VERNUMMAJOR
#echo "    minor: "$VERNUMMINOR
#echo "    post : "$VERPOST; echo
echo "  source path: $SRC"
echo "  packaging path: $PACKDIR"
echo "  destination: "$destdir
echo "  export path: $exportdestdir"
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

echo; echo "cleaning of destination directory $destdir"
if [ -d $destdir ]; then
  rm -rf $destdir
fi
mkdir -p $destdir

cd $destdir
echo; echo "Working directory changed to: $PWD"

##############################################################################
echo; echo "exporting sources"; echo "from "$SRC; echo "to "$exportdestdir
cp -rf $SRC $exportdestdir

echo; echo "clean exported sources"
find $destdir -name '*.pyc' -exec rm -f '{}' \;
find $destdir -name '*.pyo' -exec rm -f '{}' \;
find $destdir -name '*~' -exec rm -f '{}' \;
find $destdir -name '*.bak' -exec rm -f '{}' \;
rm -rf "$exportdestdir/.bzr"
rm -rf "$exportdestdir/.bzrignore"
rm -rf "$exportdestdir/.pydevproject"
rm -rf "$exportdestdir/.project"
rm -rf "$exportdestdir/.settings"
rm -rf "$exportdestdir/setup.py"
rm -rf "$exportdestdir/src/sbackup/resources"
rm -rf "$exportdestdir/src/sbackup/metainfo"
rm -rf "$exportdestdir/data/desktop/sbackup-config-su.desktop"
rm -rf "$exportdestdir/data/desktop/sbackup-config.desktop"
rm -rf "$exportdestdir/data/desktop/sbackup-restore-su.desktop"
rm -rf "$exportdestdir/data/desktop/sbackup-restore.desktop"

# 'tests', 'tools', and 'doc' are removed
#FIXME: re-add 'doc' in later releases
rm -rf "$exportdestdir/tests"
rm -rf "$exportdestdir/doc"
rm -rf "$exportdestdir/tools"

# clean Debian dir
rm -rf "$DEBIANDIR/.bzr"
rm -rf "$DEBIANDIR/.bzrignore"
rm -rf "$DEBIANDIR/.pydevproject"
rm -rf "$DEBIANDIR/.project"
rm -rf "$DEBIANDIR/.settings"

# remove the Debian specific directory temporarely from the exported source
mv -f "$DEBIANDIR" "$destdir"

case "$1" in
    tarball)
        echo; echo "creating tarball"
        tar -czf $TARNAME $REL_DESTAPPDIR
        mv -f $TARNAME $TARBALLDIR
        echo "Release tarball '$TARNAME' created in '$TARBALLDIR'"
        echo; echo "cleaning of destination directory $destdir"
        rm -rf $destdir
        cd $TARBALLDIR
        md5sum "$TARNAME" > "$TARNAME.md5"
        md5sum -c "$TARNAME.md5"
        gpg --armor --sign --detach-sig $TARNAME
    ;;

    source-with-orig)
        echo; echo "building source package"
        if test "$version_pack" = ""; then
            echo "Version not found in changelog: $version_pack"; exit 1; fi

        tar -czf $ORIGTARNAME $REL_DESTAPPDIR

        # we move the Debian directory back into the exported source in order
        # to build the deb packages
        mv -f $REL_DEBIANDIR $exportdestdir

        cd $exportdestdir
        echo; echo "Working directory changed to "$PWD

        debuild -S --lintian-opts --color always
    ;;

    source-no-orig)
        echo; echo "building source package"
        if test "$version_pack" = ""; then
            echo "Version not found in changelog: $version_pack"; exit 1; fi

        rm -f "$ORIGTARNAME"

        # we move the Debian directory back into the exported source in order
        # to build the deb packages
        mv -f $REL_DEBIANDIR $exportdestdir

        cd $exportdestdir
        echo; echo "Working directory changed to "$PWD

        debuild -S --lintian-opts --color always
    ;;
    
    update)
        echo; echo "updating source package"
        if test "$version_pack" = ""; then
            echo "Version not found in changelog: $version_pack"; exit 1; fi

        cp "$TARBALLDIR/$ORIGTARNAME" .
        echo ".orig tarball '$ORIGTARNAME' copied from '$TARBALLDIR'"

        # we move the Debian directory back into the exported source in order
        # to build the deb packages
        mv -f $REL_DEBIANDIR $exportdestdir

        cd $exportdestdir
        echo; echo "Working directory changed to "$PWD

        debuild -S -sd --lintian-opts --color always
    ;;
    

    binary)
        echo; echo "building binary packages"
        rm -f "$ORIGTARNAME"
        
        # we move the Debian directory back into the exported source in order
        # to build the deb packages
        mv -f $REL_DEBIANDIR $exportdestdir

        cd $exportdestdir
        echo; echo "Working directory changed to "$PWD

        debuild --lintian-opts --color always

        if [ $? -eq 0 ]; then
            echo; echo "Publishing debs in local repository "$LOCALPPA
            cd $destdir
            cp -f *.deb $LOCALPPA
            cd $LOCALPPA
            dpkg-scanpackages ./ /dev/null | gzip > Packages.gz
        fi
    ;;

    *)
        echo; echo "called with unknown or missing argument: $1" >&2
        echo "Please use 'tarball', 'binary', or 'source' as parameter."
        exit 1
    ;;
esac

echo; echo "Removing source folder "$exportdestdir
rm -rf $exportdestdir

cd $startpwd
echo; echo "Working directory changed to "$PWD
echo; echo "Finished!"
exit 0

