#    NSsbackup - snapshot handling
#
#   Copyright (c)2008-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#   Copyright (c)2007-2008: Ouattara Oumar Aziz <wattazoum@gmail.com>
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
:mod:`SnapshotManager` --- Snapshot handler class
====================================================================

.. module:: SnapshotManager
   :synopsis: Defines a snapshot handler class
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>

"""


from gettext import gettext as _
import traceback
import datetime
import time
import types


from nssbackup.pkginfo import Infos
from nssbackup.fs_backend import fam

from nssbackup.ar_backend import tar
from nssbackup.ar_backend.tar import SnapshotFile
from nssbackup.ar_backend.tar import Dumpdir
from nssbackup.ar_backend.tar import SnapshotFileWrapper
from nssbackup.ar_backend.tar import ProcSnapshotFile
from nssbackup.ar_backend.tar import get_dumpdir_from_list

import nssbackup.util as Util
from nssbackup.core.snapshot import Snapshot
from nssbackup.util.log import LogFactory
from nssbackup.util.exceptions import SBException
from nssbackup.util.exceptions import NotValidSnapshotException
from nssbackup.util.exceptions import NotValidSnapshotNameException
from nssbackup.util.exceptions import RebaseSnpException
from nssbackup.util.exceptions import RebaseFullSnpForbidden
from nssbackup.util.exceptions import RemoveSnapshotHasChildsError
from nssbackup.util.exceptions import NotSupportedError


_EXT_CORRUPT_SNP = ".corrupt"


class SnapshotManager(object):
    """Class responsible for handling and managing of several snapshots.
     
    :todo: Remove instance variables 'status' and implement an observer\
           pattern or progress function hooks! 
    
    :note: Rebasing of snapshots is currently disabled due to severe performance issues.
            Adapt to use FAM before re-enabling!
    """

    REBASEDIR = "rebasetmp"

    def __init__(self, target_eff_path):
        """Default constructor. Takes the path to the target backup
        directory as parameter.
        
        Use target handler (without config) here. Refactor!

        """
        if not isinstance(target_eff_path, types.StringTypes):
            raise TypeError("Effective target path of type string expected. Got %s instead"\
                            % type(target_eff_path))

        self.logger = LogFactory.getLogger()

        self._fop = fam.get_file_operations_facade_instance()
        # This is the current directory used by this SnapshotManager
        self.__target_eff_path = target_eff_path

        # The list of the snapshots is stored the first time it's used,
        # so we don't have to re-get it later
        self.__snapshots = None

        # helper variables for displaying status messages
        self.statusMessage = None
        self.substatusMessage = None
        self.statusNumber = None

#TODO: Wrap it.
        if not self.__target_eff_path.startswith(self._fop.pathsep):
            raise ValueError("Given effective path to target must be local")

    def getStatus(self):
        """
        :return: [statusNumber,statusMessage,substatusMessage]
        
        :todo: Remove/refactor this!

        """
        return [self.statusNumber, self.statusMessage, self.substatusMessage]

    def get_snapshot_allformats(self, name):
        """Returns a certain snapshot, specified by its name, from the stored
        snapshots. If the snapshot could not be found, an exception is raised.
        
        :param name: the snapshot that is to be returned
        
        """
        for snp in self.get_snapshots_allformats() :
            if snp.getName() == name :
                return snp
        raise SBException(_("Snapshot '%s' not found ") % name)

    def get_snapshots_allformats(self, fromDate = None, toDate = None, byDate = None,
                                 forceReload = False):
        """Returns a list with *all* found snapshots, according to the
        given parameters. All versions of snapshots were returned. The
        list is sorted from the latest snapshot to the earliest:
        
        - index 0  --- most recent snapshot 
        - index -1 --- oldest snapshot.
        
        :param fromDate: eg. 2007-02-17
        :param toDate:  2007-02-17
        :param byDate: 2007-02-17
        :param forceReload: True or false
        :return: list of snapshots 
        
        :todo: Re-factor this method using the CQS pattern and by simplifying!
        :todo: Separate into 'get_snapshots( force_reload=False )',\
               'get_snapshots_by_timespan' and 'get_snapshot_by_date'!
        :todo: Clarify whether to rename or to delete corrupt snapshots!
               
        """
        snapshots = []    # list of found snapshots

        if fromDate and toDate:
            for snp in self.get_snapshots_allformats():
                if fromDate <= snp.getName()[:10] <= toDate:
                    snapshots.append(snp)
        elif byDate:
            for snp in self.get_snapshots_allformats():
                if snp.getName().startswith(byDate):
                    snapshots.append(snp)
        else:
            if self.__snapshots and not forceReload:
                pass
            else:
                self._read_snps_from_disk_allformats()
            snapshots = self.__snapshots

        snapshots.sort(key = Snapshot.getName, reverse = True)
        return snapshots

    def _read_snps_from_disk_allformats(self):
        """Reads snapshots from the defined/set target directory and
        stores them in according class attribute.
        
        Unreadable snapshots are being renamed.
        """
        snapshots = []
        listing = self._fop.listdir_fullpath(self.__target_eff_path)

        for _snppath in listing :
            _snpname = self._fop.get_basename(_snppath)
            if _snpname.endswith(_EXT_CORRUPT_SNP):
                self.logger.info("Corrupt snapshot `%s` found. Skipped." % _snpname)
                continue
            try :
                snapshots.append(Snapshot(_snppath))
            except NotValidSnapshotException, error :
                if isinstance(error, NotValidSnapshotNameException) :
                    self.logger.warning(_("Invalid snapshot `%(name)s` found: Name of snapshot not valid.")\
                                        % { 'name': str(_snpname) })
                else: # rename only if name was valid but snapshot was invalid
                    self.logger.warning(_("Invalid snapshot `%(name)s` found: %(error_cause)s.")\
                                        % { 'name': str(_snpname), 'error_cause' :error })
                    self.logger.info("Invalid snapshot `%s` is being renamed." % _snpname)
                    if _snppath.endswith(".inc") or _snppath.endswith(".ful"):
                        _ren_snppath = "%s%s" % (_snppath[:-4], _EXT_CORRUPT_SNP)
                    else:
                        _ren_snppath = "%s%s" % (_snppath, _EXT_CORRUPT_SNP)
                    self._fop.rename(_snppath, _ren_snppath)

        snapshots.sort(key = Snapshot.getName, reverse = True)
        self.__snapshots = snapshots

    def get_snapshots(self, fromDate = None, toDate = None, byDate = None,
                      forceReload = False):
        """Returns a list with found snapshots that matches the current
        snapshot format, according to the given parameters. The list is
        sorted from the latest snapshot to the earliest:
        
        - index 0  --- most recent snapshot 
        - index -1 --- oldest snapshot.
        
        :param fromDate: eg. 2007-02-17
        :param toDate:  2007-02-17
        :param byDate: 2007-02-17
        :param forceReload: True or false
        :return: list of snapshots
        
        """
        snps = []
        snps_all = self.get_snapshots_allformats(fromDate, toDate, byDate,
                                                  forceReload)
        for csnp in snps_all:
            if csnp.getVersion() == Infos.SNPCURVERSION:
                snps.append(csnp)
        self.__snapshots = snps
        # debugging output
        if self.logger.isEnabledFor(5):
            self.logger.debug("[Snapshots Listing - current format]")
            for csnp in snps:
                self.logger.debug(str(csnp))
        ###
        return snps

    def exportSnapshot(self, snapshot, target, rebase = False):
        """There are two ways of exporting a snapshot. You can either
        copy the dir to the target or re-base the snapshot before copying it.
         
        :todo: Think about a plugins system that will be used to export on\
               TAPE, on DVD and so on.
           
        :attention: Not implemented yet!
        """
        raise NotSupportedError

    def rebaseSnapshot(self, torebase, newbase = None):
        """The re-base operation is the changing of the base of a
        snapshot. Basically, for 3 snapshots A, B and C that means,
        if we re-base C to A, we can now remove B without problems.
        The informations originally contained in C will be updated
        to keep the changes occurred in B inside C.
        
        Re-basing is done by doing many one-step re-base operation
        one after another.
        
        Re-base principle:
        snp1 -> snp2 -> snp3 -> snp4
        
        - re-base snp3 on snp1 (snp3 has the newer version of the file it contains)
        - remove snp3 "ver" file ( means the snapshot is being processed )
        - for each file in snp2 :
        - if included in snp3 -> pass
        - if not : push the file in snp3
        - when finished, checks and merge the includes.list and excludes.list
        - change the base file content to the new base
        - write the "ver" file
        
        If an error is encountered -> cancel Rebase ( we shouldn't
        loose the snapshot !)

        :raise SBException: if torebase is a full backup or newbase is ealier
        
        :todo: Remove status message from this non-gui class!
        
        """
        self.logger.info("Re-base of snapshot '%s' - new base: '%s'" % (torebase, newbase))

        # checks before processing 
        if torebase.isfull() :
            raise RebaseFullSnpForbidden(\
               _("No need to rebase a full snapshot '%s'") % torebase.getName())
        if not torebase.getBase():
            raise RebaseSnpException(_("'%(snapshotToRebase)s'  doesn't have 'base' file , it might have been broken ")\
                                         % {'snapshotToRebase':torebase.getName()})

        # check if the new base is earlier
        if newbase and torebase.getName() <= newbase.getName() :
            raise RebaseSnpException(_("Cannot rebase a snapshot on an earlier one : '%(snapshotToRebase)s' <= '%(NewBaseSnapshot)s' ")\
                    % { 'snapshotToRebase':torebase.getName(),
                        'NewBaseSnapshot': newbase.getName() })

        currentTorebase = torebase

        while currentTorebase.getBase():
            self.statusMessage = _("Rebasing '%(current)s' on '%(base)s'")\
                                    % {    "current": currentTorebase,
                                        "base" : currentTorebase.getBase()}
            self.logger.info(self.statusMessage)
            currentTorebase = self._rebaseOnLastSnp(currentTorebase)
            # re-basing finished?
            if newbase and currentTorebase.getBase():
# TODO: replace <= by is_older/is_younger!                
                if currentTorebase.getBase() <= newbase.getName():
                    break

    def __is_older(self, to_rebase, new_base):
        """Checks if the ??? is more recent than ???
        
        :todo: Not fully implemented and not used by now. Use it!
        """
        _res = True
        if to_rebase.getBaseSnapshot().getName() <= new_base.getName():
            pass

    def convertToFullSnp(self, snapshot):
        """Re-base a snapshot till the full one and then make it full.

        :param snapshot: the snapshot to make full
        :type snapshot: `Snapshot`

        """
        self.rebaseSnapshot(snapshot)

    def _pullSnpContent(self, snapshot, topullSnp):
        """Move the 'topullSnp' snapshot content to the 'snapshot' snapshot
        
        ====================
        Merging of snapshots
        ====================
        
        A) on directory level (records in SnapshotFiles)
        ================================================
        
        1. certain directory exists in both snapshots: the directory still
           exists in target/merged snapshot
        2. directory is contained in current snapshot but is not contained
           in origin snapshot: the directory exists in target/merged snapshot
        3. directory exists in origin snapshot, but does not exist in target
           snapshot: directory was removed or excluded and does not exist
           in merged snapshot
         
        B) on level of files within directories
        =======================================

        Files must be considerated if the parent directory which contains
        a certain file still exists in the target/merged snapshot. The
        same relations as on directory level hold for files.
        
        :param snapshot: the snapshot to push in
        :type snapshot: Snapshot
        :param topullSnp: The snapshot to pull
        :type topullSnp: Snapshot
        
        """
        # Details on implementation
        #
        # 1. create a temporary directory inside of the rebased snapshot
        # 2. merge the SNAR files, this gives a list of files/directories
        #    to be moved from the base snapshot (to pull snp) into the
        #    rebased snapshot; the snar header from the destination snapshot
        #    (i.e. the child) is used
        # 3. merge the include and exclude file lists
        #

        # Utilities functions everything should be done in temporary files #
        def makeTmpTAR():
            """
            How is the temporary archive created?
            
            1. the list of files which need to are extracted from the base
               snapshot is written to file
            2. these files are extracted from the base snapshot
            3. 
            
            @todo: Check available disk space prior.
            """
            # write temp flist created from the temporary partial snar file
            flist_name = self._fop.normpath(tmpdir, "flist.tmp")

            self.logger.info("Writing the temporary Files list to make the transfer")
#            print "  %s" % flist_name
#            print "Striping leading '/', separating entries with NULL"

            flistd = open(flist_name, 'w')
            for _fnam in _files_extract:
#                print _fnam
                flistd.write(_fnam.lstrip(self._fop.pathsep) + '\0')
            flistd.close()

            self.logger.info("Make a temporary tar file by transfering the "\
                             "files from base")
            tmptardir = self._fop.normpath(tmpdir, "tempTARdir")
            if self._fop.path_exists(tmptardir):
                self._fop.delete(tmptardir)
            self._fop.makedir(tmptardir)

            # extract files that are stored in temporary flist
            tar.extract2(topullSnp.getArchive(), flist_name,
                          tmptardir, additionalOpts = ["--no-recursion"])

            # uncompress the tar file so that we can append files to it
            archive = snapshot.getArchive()
            if not tar.getArchiveType(archive):
                raise SBException("Invalid archive file '%s'" % archive)
            else :
                arvtype = tar.getArchiveType(archive)
                if arvtype == "gzip" :
                    Util.launch("gunzip", [archive])
                    archive = archive[:-3]
                elif arvtype == "bzip2" :
                    Util.launch("bunzip2", [archive])
                    archive = archive[:-4]
                # else : the archive is already uncompressed

            # finally append them to the current
            # archive (resp. the temporary working copy)
            # we use the flist from above
            tar.appendToTarFile(desttar = archive, fileslist = flist_name,
                            workingdir = tmptardir + self._fop.pathsep, additionalOpts = None)

            # re-compress
            if arvtype == "gzip" :
                Util.launch("gzip", [archive])
            elif arvtype == "bzip2" :
                Util.launch("bzip2", [archive])

            self._fop.force_delete(tmptardir)

        def mergeIncludesList():
            destf_path = self._fop.normpath(tmpdir, "includes.list.tmp")

            srcfd = open(topullSnp.getIncludeFListFile())
            incl_topull = srcfd.readlines()
            srcfd.close()

            srcfd = open(snapshot.getIncludeFListFile())
            incl_snp = srcfd.readlines()
            srcfd.close()

            incl_dest = Util.list_union(incl_topull, incl_snp)

            destfd = open(destf_path, 'w')
            destfd.writelines(incl_dest)
            destfd.close()

        def mergeExcludesList():
            destf_path = self._fop.normpath(tmpdir, "excludes.list.tmp")

            srcfd = open(topullSnp.getExcludeFListFile())
            excl_topull = srcfd.readlines()
            srcfd.close()

            srcfd = open(snapshot.getExcludeFListFile())
            excl_snp = srcfd.readlines()
            srcfd.close()

            excl_dest = Util.list_union(excl_topull, excl_snp)

            destfd = open(destf_path, 'w')
            destfd.writelines(excl_dest)
            destfd.close()

        def movetoFinaldest():
            self.logger.debug("Move all temporary files to their final destination")
            # SNAR file
            _tmpname = self._fop.normpath(tmpdir, "snar.final.tmp")
            if self._fop.path_exists(snapshot.getSnarFile()) :
                self._fop.delete(snapshot.getSnarFile())
            self._fop.rename(_tmpname, snapshot.getSnarFile())

            # Includes.list
            if self._fop.path_exists(snapshot.getIncludeFListFile()) :
                self._fop.delete(snapshot.getIncludeFListFile())
            self._fop.rename(tmpdir + self._fop.pathsep + "includes.list.tmp",
                      snapshot.getIncludeFListFile())

            # Excludes.list
            if self._fop.path_exists(snapshot.getIncludeFListFile()) :
                self._fop.delete(snapshot.getExcludeFListFile())
            self._fop.rename(tmpdir + self._fop.pathsep + "excludes.list.tmp",
                      snapshot.getExcludeFListFile())

        # process:
        try :
            self.statusNumber = 0.00

            # create a temporary directory within the target snapshot
            tmpdir = self._fop.joinpath(snapshot.getPath(), self.REBASEDIR)
            if self._fop.path_exists(tmpdir):
                self._fop.force_delete(tmpdir) # to ensure we have write permissions
            self._fop.makedir(tmpdir)

            # specify full path to final (temporary) snar file
            _tmpfinal = self._fop.normpath(tmpdir, "snar.final.tmp")

            # create temporary SNAR file and copy the header, then merge
            finalsnar = self._copy_empty_snar(snapshot, _tmpfinal)
#            _snp_excl = snapshot.read_excludeflist_from_file()
#            print ">>> getExcludeFlist"
#            print "%s" % _snp_excl
#            assert isinstance(_snp_excl, set)
            _files_extract = self._merge_snarfiles(snapshot.getSnapshotFileInfos(),
                                            snapshot.read_excludeflist_from_file(),
                                            topullSnp.getSnapshotFileInfos(),
                                            finalsnar)

            self.statusNumber = 0.35
            mergeIncludesList()

            self.statusNumber = 0.45
            mergeExcludesList()

            self.statusNumber = 0.55
            makeTmpTAR()

            self.statusNumber = 0.75
            movetoFinaldest()

            # clean Temporary files 
            self.statusNumber = 0.85
            self._fop.delete(tmpdir)

            self.statusNumber = 0.95
            snapshot.commitverfile()
            self.statusNumber = 1.00

            self.statusNumber = None
            self.statusMessage = None
            self.substatusMessage = None
        except Exception, _exc:

            _msg = _("An error occurred when pulling snapshot '%s'.") % \
                    topullSnp.getName()
            self.logger.error(_msg)
            self.logger.error(str(_exc))
            self.logger.error(traceback.format_exc())

            self.__cancelPull(snapshot)
            raise _exc

    def _copy_empty_snar(self, snp_source, copydest):
        """Creates an empty SnapshotInfo-file with the name 'copydest'
        from the SnapshotInfo-file contained in given source snapshot. Empty
        means, that no content but the header is copied.
        
        @todo: Review the self-creation of header in the case no was found.
                Is this necessary at all?
        
        """
        self.logger.debug("Create temporary SNARFILE to prepare merging")
        if not isinstance(snp_source, Snapshot):
            raise TypeError("Given parameter 'snp_source' must be of Snapshot "\
                        "type! Got %s instead." % type(snp_source))
        if not isinstance(copydest, str):
            raise TypeError("Given parameter 'copydest' must be of string "\
                        "type! Got %s instead." % type(copydest))

        # create a temporary snar file for merge result 
        _tmpfinal = copydest
        # get snar header from current snapshots
#XXX: Why not use getHeader here???
        _snarf = open(snp_source.getSnarFile())
        _header = _snarf.readline()
        if len(_header) > 0:
            # the SNAR file isn't empty
            sepcnt = 0
            while sepcnt < 2:
                readchar = _snarf.read(1)
                if len(readchar) != 1:
                    _snarf.close()
                    raise SBException(_("The snarfile header is incomplete !"))
                if readchar == '\0':
                    sepcnt += 1
                _header += readchar
            _snarf.close()
            self.logger.debug("Current SNAR Header (NULL replaced by newline):"\
                              "\n%s" % (_header.replace("\x00", "\n")))
        else:
            # the SNAR file is empty
            self.logger.debug("SNAR file empty, create the header manually")
            _snarf.close()
            _date = snp_source.getDate()
            _datet = datetime.datetime(_date['year'], _date['month'],
                                       _date['day'], _date['hour'],
                                       _date['minute'], _date['second'])


        # create temporary SNAR file and copy the retrieved header into it
        finalsnar = ProcSnapshotFile(SnapshotFile(_tmpfinal, True))

        if _header:
            snpif = open(_tmpfinal, 'w')
            snpif.write(_header)
            snpif.close()
        else :
            finalsnar.setHeader(_datet)
            _header = finalsnar.getHeader()
        return finalsnar

    def _merge_snarfiles(self, target_snpfinfo, target_excludes,
                               src_snpfinfo, res_snpfinfo):
        """Covers all actions for merging 2 given snar files into a single
        one. This is quite TAR specific - think it over where to place it!
        
        :Parameters:
        - `target_snpfinfo`: the resulting snapshot
        - `target_excludes`: set of the excludes file list of resulting snapshot
        - `src_snpfinfo`: the snapshot that should be merged into the target
        - `res_snpfinfo`: the name of the resulting SNAR file  
        
        The method returns a list containing files that needs to be extracted
        from the archive that was merged in. 
        
        :todo: Do we need to consider the order of the snar files?
        :todo: Needs more refactoring! (CQS)
        
        """
        self.logger.info("Merging SNARFILEs to make the transfer")

        if not isinstance(target_snpfinfo, SnapshotFileWrapper):
            raise TypeError("Given parameter 'target_snpfinfo' must be of "\
                        "SnapshotFileWrapper "\
                        "type! Got %s instead." % type(target_snpfinfo))
        if not isinstance(target_excludes, set):
            raise TypeError("Given parameter 'target_excludes' must be of "\
                        "type Set! "\
                        "Got %s instead." % type(target_excludes))
        if not isinstance(src_snpfinfo, SnapshotFileWrapper):
            raise TypeError("Given parameter 'src_snpfinfo' must be of "\
                        "SnapshotFileWrapper "\
                        "type! Got %s instead." % type(src_snpfinfo))
        if not isinstance(res_snpfinfo, SnapshotFileWrapper):
            raise TypeError("Given parameter 'res_snpfinfo' must be of "\
                        "SnapshotFileWrapper "\
                        "type! Got %s instead." % type(res_snpfinfo))

#        print "Parent (base) snar file:\n%s" % src_snpfinfo
        # list for storage of files that need to be extracted from merge source
        files_to_extract = []

        for target_record in target_snpfinfo.iterRecords():
            _tmp_dumpdirs = []
#TODO: A similar method to getContent would be nice!
            _curdir = target_record[SnapshotFile.REC_DIRNAME]
            # get the content (dumpdir entries) for current directory
            _curcontent = target_snpfinfo.getContent(_curdir)
            for _dumpdir in _curcontent:
#                print "\n  now processing dumpdir: %s" % _dumpdir
                _ctrl = _dumpdir.getControl()
                _filen = _dumpdir.getFilename()
                _ddir_final = None
                _was_excluded = False
                if _ctrl == Dumpdir.UNCHANGED:
                    # Item was explicitly excluded and is therefore not included in child
#                    _filenfull = os.path.join(_curdir, _filen)
#                    print "Full path: %s" % (_filenfull)
                    if self._fop.joinpath(_curdir, _filen) in target_excludes:
                        self.logger.debug("Path '%s' was excluded. Not merged." % _filen)
                        _was_excluded = True
                    else:
                        # Item has not changed and is therefore not included in child (i.e. target) snapshot.
                        # look for the item in the parent (i.e. base/source) snapshot
                        _basedumpd = get_dumpdir_from_list(\
                                                src_snpfinfo.getContent(_curdir),
                                                _filen)
                        _base_ctrl = _basedumpd.getControl()

                        if _base_ctrl == Dumpdir.UNCHANGED:
                            _ddir_final = _dumpdir

                        elif _base_ctrl == Dumpdir.INCLUDED:
                            _ddir_final = _basedumpd
                            files_to_extract.append(self._fop.joinpath(_curdir,
                                                                 _filen))
                        else:
                            raise SBException("Found unexpected control code "\
                                              "('%s') in snapshot file '%s'."\
                                              % (_ctrl, target_snpfinfo.get_snapfile_path()))

                elif _ctrl == Dumpdir.DIRECTORY:
                    _ddir_final = _dumpdir

                elif _ctrl == Dumpdir.INCLUDED:
                    _ddir_final = _dumpdir
                else:
                    raise SBException("Found unexpected control code "\
                                      "('%s') in snapshot file '%s'."\
                                      % (_ctrl, target_snpfinfo.get_snpfile_Path()))

                if not _was_excluded:
                    _tmp_dumpdirs.append(_ddir_final)
            # end of loop over dumpdirs 
            _final_record = target_record[:SnapshotFile.REC_CONTENT]
            _final_record.append(_tmp_dumpdirs)
            # write to the SnarFile
            res_snpfinfo.addRecord(_final_record)
        return files_to_extract

    def _rebaseOnLastSnp(self, snapshot):
        """One step re-base: the given `snapshot` is re-based one-step
        back in history, i.e. on the base of its own base snapshot. This
        is the smallest possible re-base operation. If the base of the
        given `snapshot` was incremental its base is set as new base
        snapshot. If the father snapshot was a full dump, the re-based
        `snapshot` is made to a full one.
        
        Re-base principle:
            dependencies before re-basing:
            a)    snapshot (inc)
                        -> snpapshot's father (inc)
                                    -> snapshot's grand-father (inc or full)
            b)    snapshot (inc) -> snpapshot's father (full)

            after re-basing:
            a)    snapshot (inc) -> snapshot's grand-father (inc or full)
            b)    snapshot (full)
        
        
        :todo: Implement tests for this method!
        
        """
        if not snapshot.getBase():
            raise SBException(_("Base of snapshot '%s' is not set.")\
                                 % snapshot.getName())

        # get the base (father) and grand-father of processed snapshot
        basesnp = snapshot.getBaseSnapshot()
        newbase = basesnp.getBase()

        # process the merging
        self._pullSnpContent(snapshot, basesnp)
        # now the snapshot does not depend on the base any longer

#TODO: after merging snapshots: if the merged snapshot is full now, the base
#      file should be renamed in the merge routine?? No!

        # set the new base
        if newbase:
            snapshot.setBase(newbase)
            snapshot.commitbasefile()
        else:
            snapshot = self.__makeSnpFull(snapshot)
        return snapshot

    def __makeSnpFull(self, snapshot):
        """Make an inc snapshot to a full one.
                
        :param snapshot: the snapshot to be converted
        :type snapshot: `Snapshot`
        :return: the new full snapshot
        :rtype: Snapshot
                
        :todo: Is it really neccessary to create a new snapshot or is it enough to call `setPath`?
                -> It is necessary since paths to e.g. snar file have changed.
        
        :postcondition: The snapshot has the same childs as before.
        
        """
        if snapshot.isfull():
            self.logger.info(_("Snapshot '%s' is already Full, nothing to do (not changing it to full).") % snapshot.getName())
            res_snp = snapshot
        else:
            childs = self._retrieve_childsnps(snapshot)

            if childs:
                fulname = snapshot.getName()[:-3] + 'ful'
                for _snp in childs:
                    _snp.setBase(fulname)
                    _snp.commitbasefile()

            path = snapshot.getPath()
            self._fop.rename(self._fop.joinpath(path, 'base'), self._fop.joinpath(path, 'base.old'))
            self._fop.rename(path, path[:-3] + 'ful')
            res_snp = Snapshot(path[:-3] + 'ful')

            # post-condition check
            # all childs are preserved
            postcond_child_names = self._retrieve_childsnps_names(res_snp)

            if len(childs) != len(postcond_child_names):
                raise AssertionError("Renaming of base of child snapshots was "\
                                     "not successful.")
            for _chl in childs:
                if _chl.getName() not in postcond_child_names:
                    raise AssertionError("Renaming of base of child snapshots "\
                                         "was not successful.")

        return res_snp

    def __cancelPull(self, snapshot):
        """To be able to handle well the cancellation of a pull
        of a snapshot from another, we will need to not modify
        the snapshot till the last moment. This means, the infos
        we want to add in the SNAR file should be created as a
        temporary SNAR file. Same goes for the TAR file. So that
        to cancel, we will just have to remove those temporary
        files and restore the 'ver' file.
        
        """
        self.logger.info(_("Cancelling pull of snapshot '%s'") % snapshot.getName())
        path = self._fop.joinpath(snapshot.getPath(), self.REBASEDIR)
#        shutil.rmtree(path)
        self._fop.delete(path)

        if self._fop.path_exists(self._fop.joinpath(snapshot.getPath(), "files.tar")):
            format = snapshot.getFormat()
            if format == "gzip":
                Util.launch("gzip", [self._fop.joinpath(snapshot.getPath(), "files.tar")])
            elif format == "bzip2":
                Util.launch("bzip2", [self._fop.joinpath(snapshot.getPath(), "files.tar")])
        snapshot.commitverfile()

    def _retrieve_childsnps(self, snapshot):
        """Retrieves all snapshots that rely on the given parent
        `snapshot` and returns a list containing all child snapshots.
        
        """
        listing = self.get_snapshots(forceReload = True)
        child_snps = []
        for snp in listing :
            if snp.getBase() == snapshot.getName() :
                child_snps.append(snp)
        return child_snps

    def _retrieve_childsnps_names(self, snapshot):
        """Retrieves names of all snapshots that rely on the given parent
        `snapshot` and returns a list containing all child snapshot names.
        
        """
        listing = self._retrieve_childsnps(snapshot)
        child_snps = []
        for snp in listing:
            child_snps.append(snp.getName())
        return child_snps

    def _remove_standalone_snapshot(self, snapshot):
        if not self.is_standalone_snapshot(snapshot):
            raise RemoveSnapshotHasChildsError("The given snapshot '%s' is not stand-alone." % snapshot)
        self.logger.debug("Removing '%s'" % snapshot.getName())
        self._fop.delete(snapshot.getPath())
        self.get_snapshots(forceReload = True)

    def is_standalone_snapshot(self, snapshot):
        _res = False
        _childs = self._retrieve_childsnps(snapshot = snapshot)
        if len(_childs) == 0:
            _res = True
        return _res

    def removeSnapshot(self, snapshot):
        """Public method that removes a given snapshot safely. The removal
        of a snapshot is more complicated than just to remove the snapshot
        directory since a snapshots could be the base of other snapshots.
        We need to rebase all of these depending snapshots before removing
        the given snapshot.
        
        :param snapshot: the snapshot to be removed
        :type snapshot: `Snapshot`
        
        :todo: Refactor by using method `_retrieve_childsnps`!
        
        :note; Currently removal of freestanding snapshots is supported only.
        """
#        _this_snp_name = snapshot.getName()
#
#        self.logger.info(_("Deleting snapshot: '%(snp)s'.") % {'snp' : snapshot})
#        if snapshot.isfull():
#            self.__remove_full_snapshot(snapshot)
#        else:
#            # rebase all child snapshots to the base of this snapshot
#            listing = self.get_snapshots(forceReload = True)
#            for snp in listing:
#                if snp.getBase() == _this_snp_name:
#                    self.rebaseSnapshot(snp, snapshot.getBaseSnapshot())
#            self._remove_standalone_snapshot(snapshot)
#            listing = self.get_snapshots(forceReload = True)
        self._remove_standalone_snapshot(snapshot)

    def remove_snapshot_forced(self, snapshot):
        """Removes snapshot directory forcefully.
        """
        self.logger.debug("Removing '%s'" % snapshot.getName())
        self._fop.delete(snapshot.getPath())
        self.get_snapshots(forceReload = True)


    def __remove_full_snapshot(self, snapshot):
        """Method that removes the given full backup snapshot. The removal of
        a full anspshot is only possible if the full snapshot is not be the
        base of any other snapshot. To ensure this pre-condition 2 cases
        are thinkable.
        
        1. The snapshot is already stand-alone, i.e. isn't the base of any other.
        2. The snapshot must be merged with any of its child snapshots and the
           reference removed.
        """
        _ful_snp_name = snapshot.getName()
        self.logger.info("Deleting full snapshot '%(snp)s'."
                            % {'snp' : _ful_snp_name})
        if not snapshot.isfull():
            raise ValueError("Snapshot must be a full snapshot!")

        # rebase all childs of this snapshot
        listing = self.get_snapshots(forceReload = True)
        for snp in listing :
            if snp.getBase() == _ful_snp_name:
                self.logger.debug("Rebase child snapshot '%s'" % (snp))
                self.rebaseSnapshot(snp)

        # check if the full snapshot is no longer the base of any other
        listing = self.get_snapshots(forceReload = True)
        is_standalone = True
        for snp in listing:
            if snp.getBase() == _ful_snp_name:
                is_standalone = False
                break
        if is_standalone:
            self._remove_standalone_snapshot(snapshot)
        else:
            raise RemoveSnapshotHasChildsError("The removal of a full snapshot is "\
                "not possible as long as this is the base of other snapshots.")

    def compareSnapshots(self, snap1, snap2):
        """Compare 2 snapshots and return and SBdict with the
        differences between their files. The format is
        {"file" : ("propsnap1|propsnap2",sonsbdict)}.
        
        """
        raise NotSupportedError

    def getSnpHistory(self, snapshot):
        """
        gets the list of preceding snapshots till the last full one
        :param snapshot : the given snapshot
        :return: a list of Snapshots starting from the most recent one to the full one
        :note: you'll need to reverse this list to make a revert 
        """
        if not snapshot :
            raise SBException("Please provide a snapshot to process")

        result = []
        # add the first snapshot
        result.append(snapshot)
        current = snapshot
        while (current.getBaseSnapshot()) :
            current = current.getBaseSnapshot()
            result.append(current)

        # Just for DEBUG
        if self.logger.isEnabledFor(10) :
            # get the history 
            history = "\n[%s history]" % snapshot.getName()
            for snp in result :
                history += "\n- %s" % snp.getName()
            self.logger.debug(history)

        return result

    def purge(self, purge, no_purge_snp):
        """Public method that processes purging of archive directory.
        
        :param mode: for the moment, only "log" and "simple" are supported
        :param no_purge: name of snapshot not being purged 
        
        :todo: We should try to remove the snapshots from fresh to old to avoid multiple re-base operations!
        
        """
        self.get_snapshots(forceReload = True)
        if purge == "log":
            self.logger.warning(_("Logarithmic purge is currently disabled. Please specify a cutoff purge interval in your configuration instead."))
#            self._do_log_purge()
        else:
            self._do_cutoff_purge(purge, no_purge_snp)
        self.get_snapshots(forceReload = True)

    def _do_log_purge(self):
        """Does a logarithmic purge...
        
        """

        def purgeinterval(_from, _to):
            """
            :todo: Unify the formatting of snapshot timestamps!
            """
            f, t = datetime.date.fromtimestamp(_from), datetime.date.fromtimestamp(_to)
            _fromD = '%04d-%02d-%02d' % (f.year, f.month, f.day)
            _toD = '%04d-%02d-%02d' % (t.year, t.month, t.day)
            self.logger.debug("Purging from %s to %s" % (_fromD, _toD))
            snps = self.get_snapshots(fromDate = _fromD, toDate = _toD)
            if snps is not None:
                self.logger.debug("Found %s snapshots in timespan (%s..%s)" % (len(snps), _fromD, _toD))
                if len(snps) > 1: # we need 3 snapshots to delete 1!
                    snps_for_purge = snps[1:]
                    for snp in snps_for_purge:
                        self.logger.debug("Snapshot '%s' -> will be removed!" % (snp))
                        try:
                            self.removeSnapshot(snp)
                        except RemoveSnapshotHasChildsError, exc:
                            self.logger.info("%s Continue with next one." % exc)
                            continue

        self.logger.info("Logarithm Purging !")
        # Logarithmic purge
        #Keep progressivelly less backups into the past:
        #Keep all backups from yesterday
        #Keep one backup per day from last week.
        #Keep one backup per week from last month.
        #Keep one backup per month from last year.
        #Keep one backup per year further into past.
        #Erase all other backups.
        daytime = 24 * 3600
        _today = t = int(time.time())
        _2daysbefore = t - 2 * daytime
        _1weekbefore = t - 9 * daytime
        _1monthbefore = t - 30 * daytime
        _1yearbefore = t - 365 * daytime
        currentday = _2daysbefore

        # the appropriate interval is given as parameter e.g. a single day
        # within the last week or a single week within the last month
        # Within these timespans the defined number of backups must remain

        # check for last week 
        self.logger.info("Logarithm Purging [Last week]!")
        for n in range(1, (_2daysbefore - _1weekbefore) / daytime) :
            purgeinterval(_2daysbefore - n * daytime, _2daysbefore - (n - 1) * daytime)

        # check for last month
        self.logger.info("Logarithm Purging [Last month]!")
        for n in range(1, (_1weekbefore - _1monthbefore) / (7 * daytime)) :
            purgeinterval(_1weekbefore - n * 7 * daytime, _1weekbefore - (n - 1) * 7 * daytime)

        # check for last year
        self.logger.info("Logarithm Purging [Last Year]!")
#            for n in range(1,(_1monthbefore - _1yearbefore) / (30*daytime)) :
        for n in range(1, (currentday - _1yearbefore) / (30 * daytime)) :
            from_time_int = _1monthbefore - n * 30 * daytime
            purgeinterval(from_time_int, _1monthbefore - (n - 1) * 30 * daytime)

        from_time = datetime.date.fromtimestamp(from_time_int)

        # now we need to remove any older snapshots by simple cutoff
        max_age = (datetime.date.today() - from_time).days
        self._do_cutoff_purge(max_age)

    def _do_cutoff_purge(self, purge, no_purge_snp = ""):
        """Simple cut-off purging is processed: all snapshots older than
        a certain value are removed. During removal of snapshots the
        snapshot state (full, inc) is considered.
        """
        try:
            purge = int(purge)
        except ValueError:
            purge = 0
        if purge > 0:
            self.logger.info("Simple purge - remove freestanding snapshots older "\
                             "than %s days." % purge)

            while True:
                _was_removed = False
                snapshots = _get_snapshots_older_than(self.get_snapshots(),
                                                      purge, logger = self.logger)
                for snp in snapshots:
                    if snp.getName() == no_purge_snp:
                        self.logger.debug("`%s` skipped.")
                        continue

                    self.logger.debug("Checking '%s' for childs." % (snp))
                    childs = self._retrieve_childsnps(snapshot = snp)
                    if len(childs) == 0:
                        self.logger.debug("Snapshot '%s' has no childs "\
                                        "-> is being removed." % (snp))
                        self._remove_standalone_snapshot(snapshot = snp)
                        _was_removed = True
                        break
                if _was_removed is not True:
                    break
            self.get_snapshots(forceReload = True)

def _get_snapshots_older_than(snapshots, max_age, logger = None):
    _res = []
    for snp in snapshots:
        if logger:
            logger.debug("Checking age of snapshot '%s'." % snp)
        date = snp.getDate()
        age = (datetime.date.today() - datetime.date(date['year'],
                                                    date['month'],
                                                    date['day'])).days
        if age > max_age:
            _res.append(snp)
            if logger:
                logger.debug("Adding '%s' to list of removable snapshots."\
                              % (snp))
    return _res


def debug_print_snarfile(filename):
    """Print function only for debugging.
    
    :param filename: full path of snar to be printed out
    :type filename: string
    
    """
    _fop = fam.get_file_operations_facade_instance()
    if _fop.path_exists(filename):
        _snar = SnapshotFile(filename, writeFlag = False)
        print "\nSUMMARY of SNAR '%s':" % filename
        for _record in _snar.parseFormat2():
            print "%s" % _record
    else:
        print "\nSUMMARY of SNAR '%s': file not found!" % filename


def debug_snarfile_to_list(filename):
    """Helper function for debugging: the snar-file given by parameter
    'filename' is converted into a list and this list is returned by
    the function.

    :param filename: full path of snar to be converted
    :type filename: string
    :return: list containing snar file entries
    
    """
    _res = []
    _fop = fam.get_file_operations_facade_instance()
    if _fop.path_exists(filename):
        _snar = SnapshotFile(filename, writeFlag = False)
        for _record in _snar.parseFormat2():
            _res.append(_record)
    return _res
