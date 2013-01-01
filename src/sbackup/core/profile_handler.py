#   Simple Backup - process a certain profile (a distinct configuration)
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
:mod:`BackupProfileHandler` --- backup handler class
====================================================================

.. module:: BackupProfileHandler
   :synopsis: Defines a backup handler class
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>

"""


from gettext import gettext as _
import os
import datetime
import socket
import time


from sbackup.fs_backend import fam
from sbackup.core.SnapshotManager import SnapshotManager
from sbackup.core.UpgradeManager import UpgradeManager
from sbackup.core import snapshot

from sbackup import util
from sbackup.util import filecollect
from sbackup.util import exceptions
from sbackup.util import constants
from sbackup.util import log


class BackupProfileHandler(object):
    """Class that handles/manages the backup process of a single profile.
    
    """

    def __init__(self, configmanager, backupstate, dbus_connection = None,
                 use_indicator = False, full_snapshot = False):
        """The `BackupProfileHandler` Constructor.

        :param configmanager : The current configuration manager
        :param backupstate: object that stores the current state of the process
        
        :note: Make sure to call for the appropriate logger before\
               instantiating this class!
               
        """
        self.logger = log.LogFactory.getLogger()
#TODO: Simplify/refactor these attributes.
        self.__dbus_conn = dbus_connection
        self.__use_indicator = use_indicator
        self.__full_snp = full_snapshot

        self.config = configmanager
        self.__state = backupstate
        self.__state.clear_backup_properties()

        self.__profilename = self.config.getProfileName()
        self.__state.set_profilename(self.__profilename)

        self.__um = UpgradeManager()
        self.__snpman = None

        self.__snapshot = None

        self.__fam_target_hdl = fam.get_fam_target_handler_facade_instance()

        self.logger.debug("Instance of BackupProfileHandler created.")

    def do_hook(self, hookname):
        """Runs scripts optionally defined in section 'hooks' of
        configuration file. Currently defined are
        * pre-backup - before preparation of backup starts
        * post-backup - after completion and finishing of backup
        
        """
        #LP #173490
        import commands
        hooks = None
        if self.config.has_option('hooks', hookname):
            hooks = str(self.config.get('hooks', hookname)).split(",")
    
        if hooks is not None:
            self.logger.info(_("Running of hooks: %s") % hookname)
            for hook in hooks:
                result = commands.getstatusoutput(hook)
                if( 0 != result[0]):
                    raise exceptions.HookedScriptError(\
                      "Hook %s returned error: '%s' (exit code=%s)" % (hookname,
                                                                    result[1],
                                                                    result[0]))

    def prepare(self):
        self.logger.info(_("Preparation of backup process"))
        _uri = self.config.get_destination_path()
        try:
            self.__fam_target_hdl.set_destination(_uri)
            self.__fam_target_hdl.set_configuration_ref(self.config)
            self.__fam_target_hdl.set_use_mainloop(use = True)
            self.__fam_target_hdl.initialize()
        except exceptions.FileAccessException:
            self.__fam_target_hdl.terminate()
            raise

        self.__check_target()

    def process(self):
        """Runs the whole backup process:
        
        1. check pre-conditions
        2. test for upgrades (but don't perform)
        3. purge snapshots (if configured)
        4. open new snapshot containing common metadata (full or incr.
            depending on existing one, base, settings etc.)
        5. fill new snapshot (with packages list, include lists, exclude lists,
            size prediction)
        6. commit new snapshot to disk (creates the actual tar archive and
            writes everything into the snapshot directory).
        """
        assert self.__fam_target_hdl.is_initialized()

        self.__snpman = SnapshotManager(self.__fam_target_hdl.query_mount_uri())

        # Upgrade Target
        # But we should not upgrade without user's agreement!
        # Solution 1: add an option: AutoAupgrade = True/False
        #          2: start with a new and full dump and inform the user that
        #              there are snapshots in older versions 
        needupgrade = False
        try:
            needupgrade = self.__um.need_upgrade(self.__fam_target_hdl.query_mount_uri())
        except exceptions.SBException, exc:
            self.logger.warning(str(exc))

        if needupgrade:
            self.__state.set_state('needupgrade')
            _msg = _("There are snapshots stored in outdated snapshot formats. Please upgrade them using 'Simple Backup-Restoration' if you want to use them.")
            self.logger.warning(_msg)

        # get basic informations about new snapshot
        self.__state.set_state('prepare')
        (snppath, base) = self.__retrieve_basic_infos(force_full_snp = self.__full_snp)

        # Create a new snapshot
        self.__snapshot = snapshot.Snapshot(snppath)
        self.logger.info(_("Snapshot '%(name)s' is being made.")
                         % {'name' :str(self.__snapshot)})

        # Set the base file
        if base is not None:
            if self.__snapshot.isfull():
                self.logger.debug("Base is not being set for this full snapshot.")
            else:
                self.logger.info(_("Setting Base to '%(value)s'.") % {'value' : str(base)})
                self.__snapshot.setBase(base.getName())

        # Backup list of installed packages
        _packagecmd = "dpkg --get-selections"
        if self.config.has_option("general", "packagecmd"):
            _packagecmd = self.config.get("general", "packagecmd")
        if _packagecmd:
            try:
                self.logger.info(_("Setting packages File."))
                s = os.popen(_packagecmd)
                pkg = s.read()
                s.close()
                self.__snapshot.setPackages(pkg)
            except Exception, _exc:
                self.logger.warning(_("Problem when setting the packages list: ") + str(_exc))

        # set Excludes
# TODO: improve handling of Regex containing ',' (delimiter); currently this will crash
        self.logger.info(_("Setting Excludes File."))
        if self.config.has_option("exclude", "regex"):
            gexclude = str(self.config.get("exclude", "regex")).split(",")
        else :
            gexclude = ""
        self.__snapshot.setExcludes(gexclude)

        _compr = self.config.get_compress_format()
        self.logger.info(_("Setting compression format to `%s`") % _compr)
        self.__snapshot.setFormat(_compr)

        if self.config.has_option("general", "splitsize"):
            _chunks = int(self.config.get("general", "splitsize"))
            self.__snapshot.setSplitedSize(_chunks)
            if _chunks:
                self.logger.info(_("Setting size of archive chunks to %s")\
                            % util.get_humanreadable_size_str(size_in_bytes = (_chunks * 1024),
                                                              binary_prefixes = True))

        # set followlinks
        self.__snapshot.setFollowLinks(self.config.get_followlinks())
        if self.__snapshot.isFollowLinks():
            self.logger.info(_("Option 'Follow symbolic links' is enabled."))
        else:
            self.logger.info(_("Option 'Follow symbolic links' is disabled."))

        self.__collect_files()

        _publish_progress = True
        if self.__dbus_conn is None:
            _publish_progress = False
        _supports_publish = self.__fam_target_hdl.get_supports_publish()

        self.logger.info(_("Snapshot is being committed"))
        self.__state.set_state('start')
#        self.__state.set_state('commit')
        self.__snapshot.commit(self.__fam_target_hdl, _publish_progress, _supports_publish)

#TODO: add state purging
        # purge
        purge = None
        if self.config.has_option("general", "purge"):
            purge = self.config.get("general", "purge")
        if purge is not None:
            try:
                self.__snpman.purge(purge, self.__snapshot.getName()) # do not purge created snapshot
            except exceptions.SBException, sberror:
                self.logger.error(_("Error while purging old snapshots: %s") % sberror)

        self.logger.info(_("Backup process finished."))
        self.__state.set_state('finish')

    def __collect_files(self):
        """Fill snapshot's include and exclude lists and retrieve some information
        about the snapshot (uncompressed size, file count).
        """
        self.logger.info(_("Inspect file system and collect file infos"))
        _collector = self.__create_collector_obj()
        _collector.collect_files()
        _stats = _collector.get_stats()
        _snpsize = _stats.get_size_payload() + _stats.get_size_overhead(size_per_item = constants.TAR_BLOCKSIZE)

        self.__state.set_space_required(_snpsize)
        self.__snapshot.set_space_required(_snpsize)
        _sizefs, _freespace = self.__fam_target_hdl.query_dest_fs_info()

        _snpsize_hr = util.get_humanreadable_size_str(size_in_bytes = _snpsize, binary_prefixes = True)
        self.logger.info(_("Summary of backup"))
        self.logger.info(_("Number of directories: %s.") % _stats.get_count_dirs())
        self.logger.info(_("Total number of files: %s.") % _stats.get_count_files_total())
        self.logger.info(_("Number of symlinks: %s.") % _stats.get_count_symlinks())
        self.logger.info(_("Number of files included in snapshot: %s.") % _stats.get_count_files_incl())
        self.logger.info(_("Number of new files (also included): %s.") % _stats.get_count_files_new())
        self.logger.info(_("Number of files skipped in incremental snapshot: %s.") % _stats.get_count_files_skip())
        self.logger.info(_("Number of items forced to be excluded: %s.") % _stats.get_count_items_excl_forced())
        self.logger.info(_("Number of items to be excluded by config: %s.") % _stats.get_count_items_excl_config())
        self.logger.info(_("Maximum free size required is '%s'.") % _snpsize_hr)

        if _freespace == constants.FREE_SPACE_UNKNOWN:
            self.logger.warning("Unable to query available space on target: Operation not supported")
        else:
            _freespace_hr = util.get_humanreadable_size_str(size_in_bytes = _freespace, binary_prefixes = True)
            self.logger.info(_("Available disk size is '%s'.") % _freespace_hr)
            if _freespace <= _snpsize:
                raise exceptions.SBException(_("Not enough free space in the target directory for the planned backup (free: %(freespace)s, required: %(neededspace)s).")\
                                               % { 'freespace' : _freespace_hr, 'neededspace' : _snpsize_hr})

    def __create_collector_obj(self):
        """Factory method that returns instance of `FileCollector`.
        """
        _eff_local_dest_path = self.__fam_target_hdl.get_eff_path()
        _configfac = filecollect.FileCollectorConfigFacade(self.config, _eff_local_dest_path)
        _collect = filecollect.FileCollector(self.__snapshot, _configfac)
        if not self.__snapshot.isfull():
            _base = self.__snapshot.getBaseSnapshot()
            _basesnar = _base.getSnapshotFileInfos().get_snapfile_obj()
            _collect.set_parent_snapshot(_basesnar)
        return _collect

    def __copylogfile(self):
# TODO: we should flush the log file before copy!
        _op = fam.get_file_operations_facade_instance()

        if not self.__fam_target_hdl.is_initialized():
            self.logger.warning(_("Unable to copy log. File access is not initialized."))
        else:
            if self.__snapshot is not None:
                logf_src = self.config.get_current_logfile()
                if logf_src is None:
                    self.logger.warning(_("No log file specified."))
                else:
                    logf_name = _op.get_basename(logf_src)
                    logf_target = _op.joinpath(self.__snapshot.getPath(),
                                                logf_name)

                    if _op.path_exists(logf_src):
                        try:
                            _op.copyfile(logf_src, logf_target)
                        except exceptions.CopyFileAttributesError:
                            self.logger.warning(_("Unable to change permissions for file '%s'.")\
                                            % logf_target)
                        except (OSError, IOError), error:
                            self.logger.warning(_("Unable to copy log file: %s") % error)
                    else :
                        self.logger.warning(_("Unable to find logfile to copy into snapshot."))
            else:
                self.logger.warning(_("No snapshot to copy logfile."))

    def cancel(self):
        if self.__snapshot is not None:
            self.__snpman.remove_snapshot_forced(self.__snapshot)

        self.__fam_target_hdl.terminate()
        self.logger.info(_("Processing of profile was canceled on user request\n"))
        _excode = constants.EXCODE_SUCCESS
        return _excode

    def finish(self, error = None):
        """End SBackup session :
        
        - copy the log file into the snapshot dir
        
        Might be called multiple times.
        
        :note: When this method is called no exceptions were raised during the backup.
        """
        self.__copylogfile()
        self.__fam_target_hdl.terminate()

        if error is None:
            self.logger.info(_("Processing of profile successfully finished (no errors)\n"))
            _excode = constants.EXCODE_SUCCESS
        else:
            err_str = str(error)
            if err_str == "":
                err_str = str(type(error))
            self.logger.info(_("Processing of profile failed with error: %s\n") % err_str)
            _excode = constants.EXCODE_BACKUP_ERROR

        return _excode

    def __check_target(self):
        assert self.__fam_target_hdl.is_initialized(), "File access manager not initialized"

# TODO: Improve handling of original and modified target paths. Support display names for state (improved user interaction)
        _target_display_name = self.__fam_target_hdl.query_dest_display_name()
        self.__state.set_target(_target_display_name)
        self.logger.info(_("Backup destination: %s") % _target_display_name)

        # Check if the target dir exists, but Do not create any directories. 
        if not self.__fam_target_hdl.dest_path_exists():
            self.logger.warning(_("Unable to find destination directory."))
            self.__state.set_state('target-not-found')

            if self.__use_indicator and self.__dbus_conn is not None:
                _time = 0
                _retry = constants.RETRY_UNKNOWN

                while (_time <= constants.TIMEOUT_RETRY_TARGET_CHECK_SECONDS):
                    time.sleep(constants.INTERVAL_RETRY_TARGET_CHECK_SECONDS)
                    _time = _time + constants.INTERVAL_RETRY_TARGET_CHECK_SECONDS
#TODO: put the get_retry_target.. into State?
                    _retry = self.__dbus_conn.get_retry_target_check()
                    if _retry == constants.RETRY_FALSE:
                        raise exceptions.BackupCanceledError

                    elif _retry == constants.RETRY_TRUE:
                        if self.__fam_target_hdl.dest_path_exists():
                            pass
                        else:
                            self.logger.warning(_("Unable to find destination directory even after retry."))
                            raise exceptions.SBException(_("Target directory '%(target)s' does not exist.")\
                                            % {"target" : _target_display_name})
                        break
                    else:
                        pass

            else:
                raise exceptions.SBException(_("Target directory '%(target)s' does not exist.")\
                                % {"target" : _target_display_name})

        try:
            self.__fam_target_hdl.test_destination()
        except exceptions.FileAccessException, error:
            self.logger.error(_("Unable to access destination: %s") % (error))
            raise error

    def __retrieve_basic_infos(self, force_full_snp = False):
        """Retrieves basic informations about the snapshot that is going
        to be created. This informations include:
        1. the path of the new snapshot
        2. the base of the new snapshot
        
        :param listing: a list of snapshots
        
        :return: the determined `snppath` and `base`
        :rtype: a tuple
        
        """
        _fop = fam.get_file_operations_facade_instance()
        # Get the list of snapshots that matches the latest snapshot format
        listing = self.__snpman.get_snapshots()
        agelimit = int(self.config.get("general", "maxincrement"))
        increment = False

        base = None
        if (len(listing) == 0) or (force_full_snp is True):
            increment = False
        else:
            # we got some snaphots 
            # we search for the last full 
            base = listing[0]
            if listing[0].isfull() :  # Last backup was full backup
                self.logger.debug("Last (%s) was a full backup" % listing[0].getName())
                d = listing[0].getDate()
                age = (datetime.date.today() - datetime.date(d["year"], d["month"], d["day"])).days
                if  age < agelimit :
                    # Less than maxincrement days passed since that -> make an increment
                    self.logger.info("Last full backup is %i days old < %s -> make inc backup" % (age, agelimit))
                    increment = True
                else:
                    self.logger.info("Last full backup is %i days old > %s -> make full backup" % (age, agelimit))
                    increment = False      # Too old -> make full backup
            else: # Last backup was an increment - lets search for the last full one
                self.logger.debug(" Last snapshot (%s) was incremental. Lookup of latest full snapshot." % listing[0].getName())
                for i in listing :
                    if i.isfull():
                        d = i.getDate()
                        age = (datetime.date.today() - datetime.date(d["year"], d["month"], d["day"])).days
                        if  age < agelimit :
                            # Last full backup is fresh -> make an increment
                            self.logger.info("Last full backup is fresh (%d days old )-> make an increment" % age)
                            increment = True
                        else: # Last full backup is old -> make a full backup
                            self.logger.info("Last full backup is old -> make a full backup")
                            increment = False
                        break
                else:
                    self.logger.info("No full backup found -> lets make a full backup to be safe")
                    increment = False

        # Determine and create backup target directory
        hostname = socket.gethostname()
        snpname = "%s.%s" % (datetime.datetime.now().isoformat("_").replace(":", "."),
                             hostname)
        if increment is True:
            snpname = "%s.inc" % snpname
        else:
            snpname = "%s.ful" % snpname

        tdir = self.__fam_target_hdl.get_snapshot_path(snpname)
        self.logger.debug("Snapshot path: %s" % tdir)

        return (tdir, base)
