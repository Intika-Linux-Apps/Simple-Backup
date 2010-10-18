#   Simple Backup - upgrade handling
#
#   Copyright (c)2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#   Copyright (c)2007-2008: Ouattara Oumar Aziz <wattazoum@gmail.com>
#   Copyright (c)2007: Aigars Mahinovs <aigarius@debian.org>
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
"""
:mod:`UpgradeManager` --- handles upgrades of snapshots
=======================================================

.. module:: UpgradeManager
   :synopsis: handles upgrades of snapshots
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>
.. moduleauthor:: Aigars Mahinovs <aigarius@debian.org>

"""


from gettext import gettext as _

import time
import datetime
import cPickle as pickle

from sbackup.pkginfo import Infos

from sbackup.fs_backend import fam
from sbackup.ar_backend import tar

from sbackup.core import SnapshotManager
from sbackup.core import snapshot as snapshot_    # due to parameters named `snapshot`

from sbackup import util
from sbackup.util import structs
from sbackup.util import log
from sbackup.util import local_file_utils
from sbackup.util.exceptions import SBException


class UpgradeManager(object):
    """
    The UpgradeManager class
    """

    __possibleVersion = ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5"]

    statusMessage = None
    substatusMessage = None
    statusNumber = None

    def __init__(self):
        """
        """
        self.logger = log.LogFactory.getLogger()
        self._fop = fam.get_file_operations_facade_instance()

    def getStatus(self):
        """
        @return: [statusNumber,statusMessage,substatusMessage]
        """
        return [self.statusNumber, self.statusMessage, self.substatusMessage]

    def upgradeSnapshot(self, snapshot, version = "1.5"):
        """Upgrades a snapshot to a certain version. Default version
        is the highest/latest version available.
        
        :param snapshot: the snapshot to upgrade
        :param version: default is 1.5
        
        """

        if version not in self.__possibleVersion :
            raise SBException("Version should be in '%s' , got '%s' " % (str(self.__possibleVersion), str(version)))
        else :
            if snapshot.getVersion() >= version  :
                self.logger.debug("Nothing to do : version of snapshot is already higher than given version (%s >= %s )" % (snapshot.getVersion() , version))
                return
            else :
                self.logger.info("Upgrading snapshot '%s' to version '%s'" % (str(snapshot), str(version)))
                while snapshot.getVersion() < version :
                    if snapshot.getVersion() < "1.2" :
                        if ":" in snapshot.getName():
                            newname = snapshot.getName().replace(":", ".")
                            self.logger.info("Renaming directory: '" + snapshot.getName() + "' to '" + newname + "'")
                            self._fop.rename(snapshot.getPath(), newname)
                            snapshot = snapshot_.Snapshot(self._fop.get_dirname(snapshot.getPath()) + self._fop.pathsep + newname)
                        self.__upgrade_v12(snapshot)
                    elif snapshot.getVersion() < "1.3":
                        self.__upgrade_v13(snapshot)
                    elif snapshot.getVersion() < "1.4":
                        self.__upgrade_v14(snapshot)
                    elif snapshot.getVersion() < "1.5":
                        self.__upgrade_v15(snapshot)
                self.statusMessage = None
                self.substatusMessage = None
                self.statusNumber = None

#    def downgradeSnapshot(self, snapshot, version = "1.5"):
#        """Currently unused!
#        
#        The downgrade feature will be certainly used for exporting
#        snapshots, so that it would be possible to use it with a
#        previous version of sbackup.
#        
#        :param snapshot: the snapshot to downgrade 
#        :param version: The version to which one the snapshot will be downgraded
#
#        """
#        self.logger.info("Downgrading snapshot '%s' to version '%s'" % (str(snapshot), str(version)))
#        if version not in self.__possibleVersion :
#            raise SBException("Version should be in '%s' , got '%s' " % (str(self.__possibleVersion), str(version)))
#        else :
#            if snapshot.getVersion() <= version  :
#                self.logger.info("Nothing to do : version of snapshot is already higher than given version (%s <= %s )" % (snapshot.getVersion() , version))
#            while snapshot.getVersion() > version :
#                if snapshot.getVersion() > "1.4" :
#                    self.__downgrade_v14(snapshot)
#                elif snapshot.getVersion() > "1.3" :
#                    self.__downgrade_v13(snapshot)
#                elif snapshot.getVersion() > "1.2" :
#                    self.__downgrade_v12(snapshot)
#                else :
#                    raise SBException("Downgrade to version '%s' isn't supported " % str(version))

    def need_upgrade(self, target_path):
        """Checks if there is something to upgrade. If there are snapshots
        that should be upgraded True is returned otherwise False.
        
        """
        res = False
        self.logger.info("Checking for snapshots stored in old formats")
        snpman = SnapshotManager.SnapshotManager(target_path)
        snps = snpman.get_snapshots_allformats()
        for csnp in snps:
            if csnp.getVersion() != Infos.SNPCURVERSION:
                res = True
                break
        return res

    def upgradeAll(self, target):
        """Upgrades all valid snapshots in a certain directory.
         
        :param target: The directory containing the snapshots
                
        """
        self.logger.info("Upgrading All valid snapshot in '%s'" % target)
        snapman = SnapshotManager.SnapshotManager(target)
        snapshots = snapman.get_snapshots_allformats()
        for s in snapshots :
            if s.getVersion() < Infos.SNPCURVERSION:
                self.upgradeSnapshot(s)

    def __stamp(self, snppath):
        _fpath = self._fop.joinpath(snppath, "upgrade")
        self._fop.writetofile(_fpath, "Upgrade in progress.")

    def __unstamp(self, snppath):
        _fpath = self._fop.joinpath(snppath, "upgrade")
        try:
            self._fop.force_delete(_fpath)
        except (OSError, IOError), error:
            self.logger.warning(_("Unable to remove upgrade stamp: %s") % error)

    def __upgrade_v12(self, snapshot):
        """Private method that actually processes the upgrade to
        version 1.2.
         
        """
        self.statusMessage = _("Upgrading from v1.0 to v1.2: %s") % str(snapshot)
        self.logger.info(self.statusMessage)
        self.__stamp(snapshot.getPath())
        i = self._fop.openfile_for_read(self._fop.joinpath(snapshot.getPath(), "tree"))
        bfiles = pickle.load(i)
        n = self._fop.openfile_for_write(self._fop.joinpath(snapshot.getPath(), "flist"))
        p = self._fop.openfile_for_write(self._fop.joinpath(snapshot.getPath(), "fprops"))
        for item in bfiles:
            n.write(str(item[0]) + "\n")
            p.write(str(item[1]) + str(item[2]) + str(item[3]) + str(item[4]) + str(item[5]) + "\n")
        p.close()
        n.close()
        i.close()
        self._fop.writetofile(self._fop.joinpath(snapshot.getPath(), "ver"), "1.2\n")
        snapshot.setVersion("1.2")
        self.__unstamp(snapshot.getPath())
        self.statusNumber = 0.40

    def __upgrade_v13(self, snapshot):
        self.statusMessage = _("Upgrading to v1.3: %s") % str(snapshot)
        self.logger.info(self.statusMessage)
        self.__stamp(snapshot.getPath())
        flist = self._fop.readfile(self._fop.joinpath(snapshot.getPath(), "flist")).split("\n")
        fprops = self._fop.readfile(self._fop.joinpath(snapshot.getPath(), "fprops")).split("\n")
        if len(flist) == len(fprops) :
            if len(flist) > 1:
                l = self._fop.openfile_for_write(self._fop.joinpath(snapshot.getPath(), "flist.v13"))
                p = self._fop.openfile_for_write(self._fop.joinpath(snapshot.getPath(), "fprops.v13"))
                for a, b in zip(flist, fprops):
                    l.write(a + "\000")
                    p.write(b + "\000")
                l.close()
                p.close()
                self._fop.rename(self._fop.joinpath(snapshot.getPath(), "flist"), "flist.old")
                self._fop.rename(self._fop.joinpath(snapshot.getPath(), "flist.v13"), "flist")
                self._fop.rename(self._fop.joinpath(snapshot.getPath() , "fprops"), "fprops.old")
                self._fop.rename(self._fop.joinpath(snapshot.getPath() , "fprops.v13"), "fprops")
                self._fop.writetofile(self._fop.joinpath(snapshot.getPath(), "ver"), "1.3\n")
                snapshot.setVersion("1.3")
        else:
            self._fop.delete(self._fop.joinpath(snapshot.getPath(), "ver"))
            raise SBException ("Damaged backup metainfo - disabling %s" % snapshot.getPath())
        self.__unstamp(snapshot.getPath())
        self.statusNumber = 0.60

    def __upgrade_v14(self, snapshot):
        self.statusMessage = _("Upgrading to v1.4: %s") % str(snapshot)
        self.logger.info(self.statusMessage)
        self.__stamp(snapshot.getPath())

        self._fop.delete(self._fop.joinpath(snapshot.getPath(), "ver"))

        if not self._fop.path_exists(self._fop.joinpath(snapshot.getPath(), "flist"))\
           or not self._fop.path_exists(self._fop.joinpath(snapshot.getPath(), "fprops"))\
           or not self._fop.path_exists(self._fop.joinpath(snapshot.getPath() , "files.tgz"))\
           or not self._fop.path_exists(self._fop.joinpath(snapshot.getPath() , "excludes")):
            raise SBException("Snapshot is invalid! One of the essential files does not exist.")
        self._fop.writetofile(self._fop.joinpath(snapshot.getPath(), "ver"), "1.4\n")
        snapshot.setVersion("1.4")
        self.__unstamp(snapshot.getPath())
        self.statusNumber = 0.80

    def __upgrade_v15(self, snapshot):
        self.statusMessage = _("Upgrading to v1.5: %s") % str(snapshot)
        self.logger.info(self.statusMessage)
        self.__stamp(snapshot.getPath())
        self.statusNumber = 0.80
        self._fop.delete(self._fop.joinpath(snapshot.getPath(), "ver"))

        if not self._fop.path_exists(self._fop.joinpath(snapshot.getPath(), "flist")):
            raise SBException("Snapshot is invalid! The essential file 'flist' does not exist.")
        if not self._fop.path_exists(self._fop.joinpath(snapshot.getPath(), "fprops")):
            raise SBException("Snapshot is invalid! The essential file 'fprops' does not exist.")
        if not self._fop.path_exists(self._fop.joinpath(snapshot.getPath(), "files.tgz")):
            raise SBException("Snapshot is invalid! The essential file 'files.tgz' does not exist.")
        if not self._fop.path_exists(self._fop.joinpath(snapshot.getPath() , "excludes")):
            raise SBException("Snapshot is invalid! The essential file 'excludes' does not exist.")

        self.logger.info("renaming file.tgz to file.tar.gz")
        self._fop.rename(self._fop.joinpath(snapshot.getPath(), "files.tgz"), "files.tar.gz")
        self.statusNumber = 0.82
        #TODO:
        self.logger.info("Creating includes.list")
        flist = self._fop.joinpath(snapshot.getPath(), "flist")
        fprops = self._fop.joinpath(snapshot.getPath() , "fprops")

        f1 = self._fop.openfile_for_read(flist)
        f2 = self._fop.openfile_for_read(fprops)

        isEmpty = True

        for f, p in util.readlineNULSep(f1, f2):
            if f :
                if p is not None and p != str(None) :
                    if isEmpty:
                        isEmpty = False
                    snapshot.addToIncludeFlist(f)
        # commit include.list
        fi = self._fop.openfile_for_write(snapshot.getIncludeFListFile())
        for f in snapshot.getIncludeFlist().getEffectiveFileList() :
            fi.write(str(f) + "\n")
        fi.close()

        self.statusNumber = 0.85
        self.logger.info("Creating empty excludes.list")
        f1 = self._fop.openfile_for_write(snapshot.getExcludeFListFile())
        f1.close()

        self.statusNumber = 0.87
        self.logger.info("Creating 'format' file")
        # hardcoded format: gzip without splitting is supported by 1.4 only 
        formatInfos = "%s\n%s" % ("gzip", 0)
        self._fop.writetofile(self._fop.joinpath(snapshot.getPath(), "format"), formatInfos)

        self.statusNumber = 0.90
        self.logger.info("Creating the SNAR file")
        if self._fop.path_exists(snapshot.getSnarFile()) :
            self.logger.warning(_("The SNAR file already exist for snapshot '%s'. It is not overwritten.") % str(snapshot))
        else :
            snarfileinfo = snapshot.getSnapshotFileInfos(writeFlag = True)
            if not isEmpty :
                date = snapshot.getDate()
                datet = datetime.datetime(date['year'], date['month'], date['day'], date['hour'], date['minute'], date['second'])
                snarfileinfo.setHeader(datet)

                #header created, let's now add the directories from includes.list
                last_parentdir = None
                for f in snapshot.getIncludeFlist().getEffectiveFileList() :
                    if f :

                        parentdir = self._fop.get_dirname(f)
                        if parentdir == last_parentdir :
#                            self.logger.debug("[LastParentDir] already processed '%s'" % parentdir)
                            continue
                        last_parentdir = parentdir


                        _time = str(int(time.mktime(datet.timetuple())))
                        result = ["0", _time, _time]

                        if snarfileinfo.hasPath(parentdir) :
#                            self.logger.debug("[SNARFileInfo] already processed '%s'" % parentdir)
                            continue

#                        self.logger.debug("processing '%s'" % parentdir)

                        if self._fop.path_exists(parentdir) :
                            result.append(str(local_file_utils.stat_device(parentdir)))
                            result.append(str(local_file_utils.stat_inode(parentdir)))
                        else :
                            result.extend(['0', '0'])

                        result.append(parentdir)

#                        fname = self._fop.get_basename(f)
                        dumpdirs = list()

                        #get the parent dir content
                        cSBdict = snapshot.getIncludeFlist().getSon(parentdir)
                        for k, v in dict.iteritems(cSBdict):
                            # determine if it's a dir or a file
                            if self._fop.path_exists(self._fop.joinpath(parentdir, k)) :
                                if self._fop.is_dir(self._fop.joinpath(parentdir , k)) :
                                    control = tar.Dumpdir.DIRECTORY
                                else :
                                    control = tar.Dumpdir.INCLUDED
                            else :
                                if v and type(v) is list and len(v) == 2 and type(v[1]) == structs.SBdict:
                                    # this is a dirrectory
                                    control = tar.Dumpdir.DIRECTORY
                                else :
                                    control = tar.Dumpdir.INCLUDED

                            dumpdirs.append(tar.Dumpdir(control + k))

                        result.append(dumpdirs)

                        snarfileinfo.addRecord(result)

        self.statusNumber = 0.97
        self.logger.info("Creating 'ver' file")
        self._fop.writetofile(self._fop.joinpath(snapshot.getPath(), "ver"), "1.5\n")
        snapshot.setVersion("1.5")
        if self._fop.path_exists(self._fop.joinpath(snapshot.getPath(), "ver")):
            self.logger.debug("'ver' file created.")
        self.__unstamp(snapshot.getPath())
        self.statusNumber = 1.00

#    def __downgrade_v12 (self, snapshot):
#        self.logger.info("Downgrading to v1.2: %s" % str(snapshot))
#        flist = self._fop.readfile(snapshot.getPath() + self._fop.pathsep + "flist").split("\000")
#        fprops = self._fop.readfile(snapshot.getPath() + self._fop.pathsep + "fprops").split("\000")
#
#        if len(flist) == len(fprops) :
#            if len(flist) > 1:
#                l = self._fop.openfile(snapshot.getPath() + self._fop.pathsep + "flist.v12", True)
#                p = self._fop.openfile(snapshot.getPath() + self._fop.pathsep + "fprops.v12", True)
#                for a, b in zip(flist, fprops):
#                    l.write(a + "\n")
#                    p.write(b + "\n")
#                l.close()
#                p.close()
#                self._fop.rename(snapshot.getPath() + self._fop.pathsep + "flist", "flist.old")
#                self._fop.rename(snapshot.getPath() + self._fop.pathsep + "flist.v12", "flist")
#                self._fop.rename(snapshot.getPath() + self._fop.pathsep + "fprops", "fprops.old")
#                self._fop.rename(snapshot.getPath() + self._fop.pathsep + "fprops.v12", "fprops")
#                self._fop.writetofile(snapshot.getPath() + self._fop.pathsep + "ver", "1.3\n")
#        else:
#            self._fop.delete(snapshot.getPath() + self._fop.pathsep + "ver")
#            raise SBException ("Damaged backup metainfo - disabling %s" % snapshot.getPath())
#        self._fop.delete(snapshot.getPath() + self._fop.pathsep + "ver")
#        self._fop.writetofile(snapshot.getPath() + self._fop.pathsep + "ver", "1.2\n")
#        snapshot.setVersion("1.2")
#
#    def __downgrade_v13(self, snapshot):
#        self.logger.info("Downgrading to v1.3: %s" % str(snapshot))
#        self._fop.delete(snapshot.getPath() + self._fop.pathsep + "ver")
#        self._fop.writetofile(snapshot.getPath() + self._fop.pathsep + "ver", "1.3\n")
#        snapshot.setVersion("1.3")
#
#    def __downgrade_v14(self, snapshot):
#        if snapshot.getFormat() != "gzip" :
#            raise SBException (_("Cannot downgrade other format than 'gzip' to 1.4"))
#
#        self.logger.info("Downgrading to v1.4: %s" % str(snapshot))
#        self._fop.delete(snapshot.getPath() + self._fop.pathsep + "ver")
#
#        self.logger.debug("renaming file.tar.gz to file.tgz")
#        self._fop.rename(snapshot.getPath() + self._fop.pathsep + "files.tar.gz", snapshot.getPath() + self._fop.pathsep + "files.tgz")
#
#        self.logger.debug("removing 'format' file .")
#        self._fop.writetofile(snapshot.getPath() + self._fop.pathsep + "format", snapshot.getFormat())
#
#        self._fop.writetofile(snapshot.getPath() + self._fop.pathsep + "ver", "1.4\n")
#        snapshot.setVersion("1.4")
