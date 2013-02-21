#   Simple Backup - snapshot handling
#
#   Copyright (c)2008-2010,2013: Jean-Peer Lorenz <peer.loz@gmx.net>
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

from sbackup.pkginfo import Infos
from sbackup.fs_backend import fam

from sbackup.ar_backend import tar
from sbackup.ar_backend.tar import SnapshotFile
from sbackup.ar_backend.tar import Dumpdir
from sbackup.ar_backend.tar import SnapshotFileWrapper
from sbackup.ar_backend.tar import ProcSnapshotFile
from sbackup.ar_backend.tar import get_dumpdir_from_list

import sbackup.util as Util
from sbackup.util import constants
from sbackup.core.snapshot import Snapshot
from sbackup.util.log import LogFactory
from sbackup.util.exceptions import SBException
from sbackup.util.exceptions import NotValidSnapshotException
from sbackup.util.exceptions import NotValidSnapshotNameException
from sbackup.util.exceptions import RemoveSnapshotHasChildsError
from sbackup.util.exceptions import NotSupportedError
from sbackup.util.exceptions import FileAccessException


_EXT_CORRUPT_SNP = ".corrupt"


class SnapshotManager(object):
    """Class responsible for handling and managing of several snapshots.
     
    :todo: Remove instance variables 'status' and implement an observer\
           pattern or progress function hooks! 
    
    :note: Rebasing of snapshots is disabled due to severe performance issues.
    """

    def __init__(self, destination):
        """Default constructor. Takes the path to the target backup
        directory as parameter.
        """
        if not isinstance(destination, types.StringTypes):
            raise TypeError("Destination path of type string expected. Got %s instead"\
                            % type(destination))

        self.logger = LogFactory.getLogger()

        self._fop = fam.get_file_operations_facade_instance()
        # This is the current directory used by this SnapshotManager
        self.__dest_path = destination

        # The list of the snapshots is stored the first time it's used,
        # so we don't have to re-get it later
        self.__snapshots = None

        # helper variables for displaying status messages
        self.statusMessage = None
        self.substatusMessage = None
        self.statusNumber = None

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

    def get_snapshots_allformats_by_timespan_ro(self, from_date, to_date, force_reload = False):
        """Read-only variant that returns a list with *all* found snapshots, according to the
        given parameters. All versions of snapshots were returned.
        No snapshot are being removed or renamed.
        """
        snapshots = []
        for snp in self.get_snapshots_allformats_ro(force_reload):
            if from_date <= snp.getName()[:10] <= to_date:
                snapshots.append(snp)
        snapshots.sort(key = Snapshot.getName, reverse = True)
        return snapshots

    def get_snapshots_allformats_by_date_ro(self, by_date, force_reload = False):
        snapshots = []
        for snp in self.get_snapshots_allformats_ro(force_reload):
            if snp.getName().startswith(by_date):
                snapshots.append(snp)
        snapshots.sort(key = Snapshot.getName, reverse = True)
        return snapshots

    def get_snapshots_allformats_ro(self, force_reload = False):
        if self.__snapshots and not force_reload:
            pass
        else:
            self._read_snps_from_disk_allformats(read_only = True)
        snapshots = self.__snapshots
        snapshots.sort(key = Snapshot.getName, reverse = True)
        return snapshots

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
                (e.g. method `reload` + `get...`
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
                self._read_snps_from_disk_allformats(read_only = False)
            snapshots = self.__snapshots

        return snapshots

    def _read_snps_from_disk_allformats(self, read_only = True):
        """Reads snapshots from the defined/set target directory and
        stores them in according class attribute.
        
        Unreadable snapshots are being renamed.
        """
        self.__snapshots = []
        listing = self._fop.listdir_fullpath(self.__dest_path)

        for _snppath in listing :
            _snpname = self._fop.get_basename(_snppath)
            try:
                self._fop.test_dir_access(_snppath)
            except FileAccessException, error:
                self.logger.info("Unable to access `%s'. Skipped." % _snppath)
                continue

            if _snpname.endswith(_EXT_CORRUPT_SNP):
                self.logger.info("Corrupt snapshot `%s` found. Skipped." % _snpname)
                continue
            try:
                self.__snapshots.append(Snapshot(_snppath))
            except NotValidSnapshotException, error :
                if isinstance(error, NotValidSnapshotNameException) :
                    self.logger.info(_("Invalid snapshot `%(name)s` found: Name of snapshot not valid.")\
                                        % { 'name': str(_snpname) })
                else: # rename only if name was valid but snapshot was invalid
                    self.logger.info(_("Invalid snapshot `%(name)s` found: %(error_cause)s.")\
                                        % { 'name': str(_snpname), 'error_cause' :error })
                    if not read_only:
                        self.logger.info("Invalid snapshot `%s` is being renamed." % _snpname)
                        if _snppath.endswith(".inc") or _snppath.endswith(".ful"):
                            _ren_snppath = "%s%s" % (_snppath[:-4], _EXT_CORRUPT_SNP)
                        else:
                            _ren_snppath = "%s%s" % (_snppath, _EXT_CORRUPT_SNP)
                        self._fop.rename(_snppath, _ren_snppath)

        self.__snapshots.sort(key = Snapshot.getName, reverse = True)

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

    def _retrieve_childsnps(self, snapshot):
        """Retrieves all snapshots that rely on the given parent
        `snapshot` and returns a list containing all child snapshots.
        
        """
        listing = self.get_snapshots(forceReload = False)
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
        self.logger.info("Removing '%s'" % snapshot.getName())
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
        
        :param snapshot: the snapshot to be removed
        :type snapshot: `Snapshot`
        
        :note; Currently removal of freestanding snapshots is supported only.
        """
        self._remove_standalone_snapshot(snapshot)

    def remove_snapshot_forced(self, snapshot):
        """Removes snapshot directory forcefully.
        """
        self.logger.debug("Removing '%s'" % snapshot.getName())
        self._fop.delete(snapshot.getPath())
        self.get_snapshots(forceReload = True)

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
            self._do_log_purge(no_purge_snp)
        else:
            self._do_cutoff_purge(purge, no_purge_snp)
        self.get_snapshots(forceReload = True)

    def _do_log_purge(self, no_purge_snp = ""):
        """Logarithmic purge
        Keep progressivelly less backups into the past:
        Keep all backups from yesterday
        Keep one backup per day from last week.
        Keep one backup per week from last month.
        Keep one backup per month from last year.
        Keep one backup per quarter from 2nd last year.
        Keep one backup per year further in past.        
        """

        self.logger.info("Logarithmic purging")
        # compute years since begin of epoch: we need to go back this far
        _years_epoch = int(time.time() / (constants.SECONDS_IN_DAY * constants.DAYS_IN_YEAR))

        purge_plan = [ { "title" : "Last week", "nperiod" : 7,
                         "interval" : 1 },
                       { "title" : "Last month", "nperiod" : 3,
                         "interval" : constants.DAYS_IN_WEEK },
                       { "title" : "Last year", "nperiod" : 11,
                         "interval" : constants.DAYS_IN_MONTH },
                       { "title" : "2nd last year", "nperiod" : 4,
                         "interval" : constants.DAYS_IN_QUARTER },
                       { "title" : "remaining years", "nperiod" : _years_epoch,
                         "interval" : constants.DAYS_IN_YEAR }
                     ]

        _max_age = 2    # start value
        for pent in purge_plan:
            self.logger.info("Logarithm Purging [%s]" % pent["title"])
            _max_age = self.__purge_period(start = (_max_age - 1), nperiod = pent["nperiod"],
                                           interval = pent["interval"], no_purge_snp = no_purge_snp)

    def __purge_period(self, start, nperiod, interval, no_purge_snp):
        """period is given as `start` age and interval length in days.
        The period is repeated `nperiod` times.
        Within these timespans the defined number of backups must remain.
        """
        _number_to_keep = 1
        for j in range(0, nperiod):
            _min_age = start + (j * interval)
            _max_age = _min_age + (interval + 1)
            self._do_purge_in_timespan(_min_age, _max_age, _number_to_keep, no_purge_snp)
        return _max_age

    def _do_purge_in_timespan(self, min_age, max_age, number_to_keep, no_purge_snp = ""):
        """Simple purging is processed: all snapshots in timespan (i.e. younger
        than `max_age` and older than `min_age` are removed. Only freestanding
        snapshots are removed.
        Given snapshot `no_purge_snp` is never removed.
        The removal is terminated if `number_to_keep` snapshots remain.
        """
        _min_age = int(round(min_age))
        _max_age = int(round(max_age))
        assert _max_age > _min_age, "Given parameter max. age should be greater than min. age"

        if _min_age > 0:
            self.logger.debug("Purge in timespan\nRemove freestanding snapshots younger "\
                              "than %(max_age)s and older than %(min_age)s days."\
                              % {"max_age" : _max_age, "min_age" : _min_age})

            while True:
                _was_removed = False
                snapshots = self.get_snapshots()    # sort order: idx 0 = most recent
                snapshots = _get_snapshots_younger_than(snapshots, _max_age)
                snapshots = _get_snapshots_older_than(snapshots, _min_age)

                # debugging output
                if self.logger.isEnabledFor(5):
                    self.logger.debug("Snapshots in timespan - re-sorted]")
                    for csnp in snapshots:
                        self.logger.debug(str(csnp))
                ###

                _nsnps = len(snapshots)
                _maxidx = _nsnps - number_to_keep    # biggest valid index
                if _nsnps <= number_to_keep:
                    break
                for _idx in range(_maxidx):
                    snp = snapshots[_idx]
                    if snp.getName() == no_purge_snp:
                        self.logger.debug("`%s` skipped.")
                        continue

                    self.logger.debug("Checking '%s' for childs." % (snp))
                    childs = self._retrieve_childsnps(snapshot = snp)
                    if len(childs) == 0:
                        self.logger.debug("Snapshot '%s' has no childs "\
                                        "-> is being removed." % (snp))
                        self.remove_snapshot_forced(snapshot = snp) # it's freestanding
                        _was_removed = True
                        break
                if _was_removed is False:
                    break

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
                snapshots = _get_snapshots_older_than(self.get_snapshots(), purge)
                for snp in snapshots:
                    if snp.getName() == no_purge_snp:
                        self.logger.debug("`%s` skipped.")
                        continue

                    self.logger.debug("Checking '%s' for childs." % (snp))
                    childs = self._retrieve_childsnps(snapshot = snp)
                    if len(childs) == 0:
                        self.logger.debug("Snapshot '%s' has no childs "\
                                        "-> is being removed." % (snp))
                        self.remove_snapshot_forced(snapshot = snp)
                        _was_removed = True
                        break
                if _was_removed is not True:
                    break


def _get_snapshots_younger_than(snapshots, age):
    _res = []
    for snp in snapshots:
        date = snp.getDate()
        snp_age = (datetime.date.today() - datetime.date(date['year'],
                                                         date['month'],
                                                         date['day'])).days
        if snp_age < age:
            _res.append(snp)
    return _res


def _get_snapshots_older_than(snapshots, age):
    _res = []
    for snp in snapshots:
        date = snp.getDate()
        snp_age = (datetime.date.today() - datetime.date(date['year'],
                                                    date['month'],
                                                    date['day'])).days
        if snp_age > age:
            _res.append(snp)
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
