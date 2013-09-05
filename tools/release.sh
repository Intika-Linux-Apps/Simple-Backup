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
#   Copyright (c)2010,2013 Jean-Peer Lorenz <peer.loz@gmx.net>
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

set -e

export GZIP="-9"

startpwd=$PWD

#
# grab current version
#
metainfofile=$startpwd"/tools/metainfo.sh"
source $metainfofile
appname=$PKGNAME


echo "-------------------------------------------------------"
echo "Packaging tool for "$appname
echo "-------------------------------------------------------"; echo

case "$1" in
    snapshot)
        echo "Builds snapshot tarball."
    ;;
    tarball)
        echo "Builds release tarball."
    ;;
    source-with-orig)
        echo "Builds source package."
        echo "Using this option you can create an intitial release within a"
        echo "source version. In this case the .orig tar is uploaded."
    ;;
    update)
        echo "Builds an updated source package."
        echo "An .orig tarball from the tarball directory is used."
        echo "Using this option you can create an updated release within the"
        echo "same source version. The .orig tar is not uploaded in that"
        echo "case but the existing .orig tar from the initial release is"
        echo "used."
    ;;
    publish)
        echo "publishes debs in local ppa."
    ;;
    binary-from-orig)
        echo "Builds binary packages."
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
REL_DESTAPPDIR="$appname-$VERFULL"
destdir=$PACKDIR"/"$VERFULL
TARNAME=$appname"_"$VERFULL

bzrrev=`bzr log -r-1|grep revno| cut -d " " -f 2`
echo "Latest bzr revision: "$bzrrev

if test "$1" = "snapshot"; then
    TARNAME="$TARNAME~r$bzrrev"
fi

if test "$2" = ""; then
    echo "No suffix for tarball given"
else
    echo "Suffix for tarball given: "$2
    TARNAME="$TARNAME~$2"
fi

ORIGTARNAME="$TARNAME.orig$TAREXT"
TARNAME="$TARNAME$TAREXT"

exportdestdir=$destdir"/"$REL_DESTAPPDIR
DEBIANDIR="$exportdestdir/$REL_DEBIANDIR"


echo "Make sure your debian/CHANGELOG is up-to-date!"; echo

echo "Summary of parameters"
echo "  From Metafile:"
echo "    VERFULL: "$VERFULL
echo "    PKGNAME: "$PKGNAME
echo
echo "  package: "$appname
echo "  building version: "$version_pack
echo "    full : "$VERFULL
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

# check status of current branch
echo
bzrstat=`bzr status`
#bzrstat=""
if test "$bzrstat" == ""; then
    echo "bzr status seems okay...go ahead"
else
    echo "There are uncommitted changes"
    echo $bzrstat
    echo; echo "Please commit first!"
    exit 1
fi

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


case "$1" in
    tarball)
        echo; echo "creating tarball"
        
        tar -czf $TARNAME $REL_DESTAPPDIR
        mv -f $TARNAME $TARBALLDIR
        echo "Release tarball '$TARNAME' created in '$TARBALLDIR'"
        echo; echo "cleaning of destination directory $destdir"
        rm -rf $destdir
        cd $TARBALLDIR
		#FIXME: replace md5 with sha256
        md5sum "$TARNAME" > "$TARNAME.md5"
        md5sum -c "$TARNAME.md5"
        

		cp "$TARNAME" "$ORIGTARNAME"
        md5sum "$ORIGTARNAME" > "$ORIGTARNAME.md5"
        md5sum -c "$ORIGTARNAME.md5"
        gpg --armor --sign --detach-sig $ORIGTARNAME
        gpg --armor --sign --detach-sig $TARNAME
    ;;

    snapshot)
        echo; echo "creating snapshot tarball"
        
        tar -czf $TARNAME $REL_DESTAPPDIR
        mv -f $TARNAME $TARBALLDIR
        echo "Snapshot tarball '$TARNAME' created in '$TARBALLDIR'"
        echo; echo "cleaning of destination directory $destdir"
        rm -rf $destdir
    ;;


    source-with-orig)
		#TODO: test this chunk of code
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

    update)
		#TODO: test this chunk of code
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
    

    publish)
        if [ $? -eq 0 ]; then
            echo; echo "Publishing debs in local repository "$LOCALPPA
            cd $destdir
            cp -f *.deb $LOCALPPA
            cd $LOCALPPA
            dpkg-scanpackages ./ /dev/null | gzip > Packages.gz
        fi
    ;;

    binary-from-orig)
    #FIXME
        echo; echo "building binary packages from orig-tar"
        ls -lah
        echo "Removing destination folder "$exportdestdir
  	    rm -rf $exportdestdir

        if [ ! -f $TARBALLDIR/$ORIGTARNAME ]
        then            
	        echo "ERROR: orig-tarball ($TARBALLDIR/$ORIGTARNAME) not found. Please run 'release.sh tarball' first."
            exit 1
        fi
        ls -lah
        # original tarball is required in packaging dir
        cp $TARBALLDIR/$ORIGTARNAME $destdir/$ORIGTARNAME
        ls -lah
        tar xaf $destdir/$ORIGTARNAME
        ls -lah
        mv sbackup-* $exportdestdir
        ls -lah
        
        cd $exportdestdir
        echo; echo "Working directory changed to "$PWD
        ls -lah
        ls -lah ..

    	if [ "$2" == "--no-signing" ]; then
    	    DEBUILD_OPTS="-us -uc"; fi
    	DEBUILD_CMD="debuild $DEBUILD_OPTS --lintian-opts --color always"
    	echo "Running: "$DEBUILD_CMD
    	$DEBUILD_CMD

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

