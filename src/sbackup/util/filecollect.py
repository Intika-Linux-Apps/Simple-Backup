#   Simple Backup - collection of files and files metadata
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


from gettext import gettext as _
import os
import re
import types

from sbackup import util

from sbackup.util import local_file_utils
from sbackup.util import exceptions
from sbackup.util import log


#TODO: make this module independent from archive backend 


class FileCollectorStats(object):
    """Provides statistical information about files collected by `FileCollector` objects.
    These information encompass:
    * size of files being backuped
    * number of files being backuped.
    """

    def __init__(self, followlinks = False):
        self.__followlinks = False
        self.set_followlinks(followlinks)
        # uncompressed size of snapshot (cummulative)
        self.__size_in_bytes = 0L

        self.__ndirs = 0L
        self.__nfiles = 0L
        self.__nsymlinks = 0L

        # for incremental counting (in case of full snapshot only `__nfile_incl` is used)
        self.__nfiles_incl = 0L
        self.__nfiles_skip = 0L
        self.__nfiles_new = 0L

        self.__nexcl_forced = 0L
        self.__nexcl_config = 0L

    def set_followlinks(self, followlinks):
        if not isinstance(followlinks, types.BooleanType):
            raise TypeError("Expected parameter of boolean type. "\
                            "Got %s instead." % type(followlinks))
        self.__followlinks = followlinks

    def get_size_payload(self):
        """Returns the cumulated size of files being backuped in bytes.
        Additional overhead due to storage etc. is not considered.
        """
        return self.__size_in_bytes

    def get_size_overhead(self, size_per_item):
        """Returns the cumulated size of overhead produced by files being backuped.
        The overhead is calculated based on the number of files and their overhead
        per file given as parameter.
        """
        if not isinstance(size_per_item, types.IntType):
            raise TypeError("Expected parameter of integer type. "\
                            "Got %s instead." % type(size_per_item))
        _overhead = (self.__ndirs + self.__nfiles_incl) * size_per_item
        if not self.__followlinks:
            _overhead += self.__nsymlinks * size_per_item
        return _overhead

    def get_count_files_total(self):
        """Returns the number of files.
        """
        return self.__nfiles

    def get_count_files_incl(self):
        """Returns the number of files.
        """
        return self.__nfiles_incl

    def get_count_files_skip(self):
        """Returns the number of files.
        """
        return self.__nfiles_skip

    def get_count_files_new(self):
        """Returns the number of new included files.
        """
        return self.__nfiles_new

    def get_count_dirs(self):
        """Returns the number of files.
        """
        return self.__ndirs

    def get_count_symlinks(self):
        """Returns the number of files.
        """
        return self.__nsymlinks

    def get_count_items_excl_forced(self):
        """Returns the number of files.
        """
        return self.__nexcl_forced

    def get_count_items_excl_config(self):
        """Returns the number of files.
        """
        return self.__nexcl_config

    def clear(self):
        """Clears collected data.
        """
        self.__size_in_bytes = 0L
        self.__ndirs = 0L
        self.__nfiles = 0L
        self.__nsymlinks = 0L
        self.__nfiles_incl = 0L
        self.__nfiles_skip = 0L
        self.__nexcl_forced = 0L
        self.__nexcl_config = 0L
        self.__nfiles_new = 0L

    def add_size(self, value):
        """The given value is added to the cumulated file size.
        """
        self.__size_in_bytes += value

    def count_file(self):
        """The file counter is increased by 1.
        """
        self.__nfiles += 1

    def count_incl_file(self):
        self.__nfiles_incl += 1

    def count_new_file(self):
        self.__nfiles_new += 1

    def count_skip_file(self):
        self.__nfiles_skip += 1

    def count_dir(self):
        """The file counter is increased by 1.
        """
        self.__ndirs += 1

    def count_symlink(self):
        self.__nsymlinks += 1

    def count_excl_forced(self):
        self.__nexcl_forced += 1

    def count_excl_config(self):
        self.__nexcl_config += 1


class FileCollectorParentSnapshotFacade(object):
    """Class that provides simplified access to attributes of the parent
    snapshot (the base). The class is designed for use with `FileCollector`.
    """

    def __init__(self):
        self.__logger = log.LogFactory.getLogger()
        # snapshot file (snar) of current snapshot's parent (base snapshot)
        # only set if the current one is incremental
        self.__base_snar = None
        self.__base_backup_time = None
        self.__base_snardict = None

    def set_base_snar(self, basesnar):
        """Sets the snapshot file (snar) of the base (parent) snapshot.
        
        @note: This implies that the current snapshot is incremental.
        
        """
#        if not isinstance(basesnar, tar.SnapshotFile):
#            raise TypeError("Expected parameter of type 'SnapshotFile'. "\
#                            "Got %s instead." % type(basesnar))
        self.__base_snar = basesnar
        self.__set_base_backup_time(basesnar.get_time_of_backup())
        self.__set_base_snardict(basesnar.get_dict_format2())

    def __set_base_backup_time(self, backup_time):
        """Sets the time the parent backup was created. The time is
        measured in seconds since beginning of the epoch (unix style).
        """
        if not isinstance(backup_time, types.FloatType):
            raise TypeError("Expected parameter of floar type. "\
                            "Got %s instead." % type(backup_time))
        self.__logger.debug("Backup time of parent snapshot: %s" % backup_time)
        self.__base_backup_time = backup_time

    def __set_base_snardict(self, snardict):
        """Sets the dictonary containing the parent snapshot file (snar file).
        """
        if not isinstance(snardict, types.DictionaryType):
            raise TypeError("Expected parameter of dictionary type. "\
                            "Got %s instead." % type(snardict))
        self.__base_snardict = snardict

    def get_base_snardict(self):
        """Returns the dictonary containing the parent snapshot file (snar file).
        """
        return self.__base_snardict

    def get_base_backup_time(self):
        """Returns the time the parent backup was created.
        """
        return self.__base_backup_time


class FileCollector(object):
    """Responsible for the process of collecting files that are being backuped.
    The collecting process comprises of:
    
    * check the files are readable/accessable
    * apply exclusion rules (Regex) defined by user to the list of files
    * calculate the required space for the backup
    * prepare include and exclude file lists used by the backup process.
    """

    def __init__(self, snp, configuration):
        self.__logger = log.LogFactory.getLogger()

        # current snapshot (the new one)
        self.__snapshot = None
        # flag whether the current snapshot is full or incremental
        self.__isfull = True

        self.__parent = FileCollectorParentSnapshotFacade()
        self.__collect_stats = FileCollectorStats()
        self.__configuration = None

        # stats of last processed file
        self.__stat_func = None
        self.__fstats = None
        self.__fislink = None
        self.__fisdir = None
        # list of Regular Expressions defining exclusion rules
        self.__excl_regex = []
# TODO: put list of compiled regex into `Snapshot` (i.e. compile them when setting the excludes). 

        self.set_snapshot(snp)
        self.set_configuration(configuration)

    def set_snapshot(self, snp):
        """Sets the given snapshot as the currently processed snapshot.
        """
#        if not isinstance(snp, snapshot.Snapshot):
#            raise TypeError("Expected parameter of type 'Snapshot'. "\
#                            "Got %s instead." % type(snp))
        self.__snapshot = snp
        self.__set_isfull(isfull = snp.isfull())
        self.__collect_stats.set_followlinks(followlinks = snp.isFollowLinks())

    def set_configuration(self, configuration):
        """Sets the given object of type `FileCollectorConfigFacade`.
        """
        if not isinstance(configuration, FileCollectorConfigFacade):
            raise TypeError("Expected parameter of type 'FileCollectorConfigFacade'. "\
                            "Got %s instead." % type(configuration))
        self.__configuration = configuration

    def set_parent_snapshot(self, parent):
        """Sets the snapshot file (snar) of the base (parent) snapshot.
        
        @note: This implies that the current snapshot is incremental.
        
        """
#        if not isinstance(parent, tar.SnapshotFile):
#            raise TypeError("Expected parameter of type 'SnapshotFile'. "\
#                            "Got %s instead." % type(parent))
        self.__set_isfull(isfull = False)
        self.__parent.set_base_snar(parent)

    def get_stats(self):
        """Returns the collector stats object.
        """
        return self.__collect_stats

    def __prepare_collecting(self):
        """The actual process of collecting is prepared (i.e. stats are cleared etc.).
        
        @note: Depending on setting `Follow links` are functions for testing file existance and
               retrieval of file stats selected here.
        """
        if self.__snapshot.isFollowLinks():
            self.__stat_func = os.stat
        else:
            self.__stat_func = os.lstat
        self.__collect_stats.clear()

    def __set_isfull(self, isfull):
        """Sets attribute `__isfull` to the given boolean value.
        
        Attribute `__isfull` is introduced because of performance concerns
        since the snapshot derives this information from its name on every
        request again.  
        """
        if not isinstance(isfull, types.BooleanType):
            raise TypeError("Expected parameter of boolean type. "\
                            "Got %s instead." % type(isfull))
        self.__isfull = isfull
        # test of post-condition: isfull must be equal to the value in the snapshot
        if self.__isfull != self.__snapshot.isfull():
            raise AssertionError("Values of attribute 'isfull' are "\
                                 "inconsistent. Found value in snapshot: %s."\
                                 % self.__snapshot.isfull())

    def __is_not_accessable(self, path):
        """Tests whether the given `path` can be accessed (i.e. exists and is readable).
        """
        # get the stats, If not possible, the file has to be exclude, return True
        try:
            self.__fstats = self.__stat_func(path)
            self.__fisdir = local_file_utils.is_dir(path)
            self.__fislink = local_file_utils.is_link(path)
        except Exception, _exc:    #IGNORE:W0703
            self.__logger.warning(_("File '%(file)s' is not accessable with error '%(error)s'.")\
                                    % {'file' : path, 'error' : str(_exc)})
            self.__fstats = None
            self.__fisdir = None
            self.__fislink = None
            return True

        # refuse a file if we don't have read access
        # The open() statement may hang indefinitely (LP Bug 184713)
        # taken from: http://docs.python.org/library/signal.html#example
        _res = False
        try:
            util.set_timeout_alarm(timeout = 5)
            fdscr = os.open(path, os.R_OK)
            os.close(fdscr)
        except exceptions.TimeoutError, _exc:
            self.__logger.warning(_("File '%(file)s' cannot be opened for read access. Operation timed out.")\
                                    % {'file' : path})
            _res = True
        except Exception, _exc:    #IGNORE:W0703
            self.__logger.warning(_("File '%(file)s' cannot be opened for read access with error '%(error)s'.")\
                                    % {'file': path, 'error' : str(_exc)})
            _res = True

        util.set_timeout_alarm(timeout = 0)
            # when file does not exist, the `open` fails and variable `fdscr` is not defined here
#            try:
#                os.close(fdscr)
#            except OSError:
#                pass    
        return _res

    def __is_circular_symlink(self, path):
        if self.__fislink:
            if self.__snapshot.isFollowLinks():
                ln_target = local_file_utils.get_link_abs(path)
                if path.startswith(ln_target):
                    self.__logger.info(_("Symbolic link '%(path)s' -> '%(ln_target)s' is a circular symlink.")\
                                % {'path' : path, 'ln_target' : ln_target})
                    return True
        #test passed
        return False

    def _is_excluded_by_name(self, path):
        """Decides whether or not a path has to be excluded by
        its name using the lists of defined
        * snapshot destination
        * regular expressions
        * blacklisted names.
                
        @return: True if the file has to be excluded, false if not
        """
        if path == self.__configuration.get_target_dir():
            self.__logger.info(_("File '%(file)s' is backup's target directory.") % {'file' : path})
            return True
        
        # if the file is in exclude list, return true
        if self.__snapshot.is_path_in_excl_filelist(path):
            self.__logger.info(_("Path '%(file)s' defined in excludes list.") % {'file' : path})
            return True

        # if the file matches an exclude regexp, return true
# TODO: Regex are applied to the full path. Add a choice to apply Regex only to files, directories etc.
        for _regex in self.__excl_regex:
            _regex_res = _regex.search(path)
            if _regex_res is not None:
                self.__logger.info(_("File '%(file)s' matches regular expression '%(regex)s'.")\
                                    % {'file' : path, 'regex' : str(_regex.pattern)})
                return True
        #all tests passed
        return False

    def _is_excluded_by_size(self, path):
        """Decides whether or not a file is to be excluded by the configuration.
        It is not decided for the incremental exclusion.

        Currently, following configuration options are tested:
        * file size
                
        @return: True if the file has to be excluded, false if not
        """
        #if the file is too big
        if self.__configuration.is_maxsize_enable():
            if self.__fstats.st_size > self.__configuration.get_maxsize_limit():
                self.__logger.info(_("File '%(file)s' exceeds maximum file size ( %(filesize)s > %(maxsize)s).")\
                                    % {'file' : path, 'filesize' : str(self.__fstats.st_size),
                                       'maxsize' : str(self.__configuration.get_maxsize_limit())})
                return True
        #all tests passed
        return False

    def _is_excluded_by_force(self, path):
        """Private interface method which checks for forced exclusion of given `path` by
        calling the according test methods in turn. If this method returns True, the
        path *must* be excluded irrespectively it is explicitely included etc.

        @return: True if the file has to be excluded, false if not
        """
        if self.__is_not_accessable(path) is True:
            return True
        elif self.__is_circular_symlink(path) is True:
            return True
        return False

    def _check_for_excludes(self, path): #, force_exclusion=False):
        """Checks given `path` for exclusion and adds it to the `ExcludeFlist` if
        required. Sub-directories are only entered in the case the `path` is not
        excluded.
        
        @param path: The path being checked for exclusion
        
        @note: Links are always backuped; TAR follows links (i.e. dereferences them = stores the actual
               content) only if option `followlinks` is set. A link targeting a directory yields
               'islink=True' and 'isdir=True'. 
        """
        _excluded = False
        _stop_checking = False

        if self._is_excluded_by_name(path):
            if not self.__snapshot.is_subpath_in_incl_filelist(path):
                # add to exclude list, if not explicitly included; since paths can be nested,
                # it is checked for sub-paths instead of full paths
                self.__snapshot.addToExcludeFlist(path)
                self.__collect_stats.count_excl_config()
                _excluded = True
            
        elif self._is_excluded_by_force(path):
            # force exclusion e.g. path is defined in includes list but does not exist/is not accessable
            self.__snapshot.addToExcludeFlist(path)
            self.__collect_stats.count_excl_forced()
            _excluded = True

        elif self._is_excluded_by_size(path):
            if not self.__snapshot.is_subpath_in_incl_filelist(path):
                # add to exclude list, if not explicitly included; since paths can be nested,
                # it is checked for sub-paths instead of full paths
                self.__snapshot.addToExcludeFlist(path)
                self.__collect_stats.count_excl_config()
                _excluded = True

        if not _excluded:
            # path was not excluded, so do further tests (stats, enter dir...)            
            if self.__fislink:
                self.__logger.debug("Symbolic link found: '%(path)s' -> '%(ln_target)s'."\
                                % {'path' : path, 'ln_target' : local_file_utils.get_link(path)})
                self.__collect_stats.count_symlink()
                if not self.__snapshot.isFollowLinks():
                    # if `followlinks` is *disabled*, just count the link and finish
                    _stop_checking = True

            if self.__fisdir:
                if _stop_checking:    # i.e. `followlinks` is not enabled
                    self.__collect_stats.count_file()
                    self.__cumulate_size(path)
                else:
                    # if it's a directory, enter inside
                    try:
                        for _dir_item in local_file_utils.listdir(path) :
                            _dir_item = local_file_utils.joinpath(path, _dir_item)
                            self._check_for_excludes(path = _dir_item)
                        self.__collect_stats.count_dir()    # the directory `path`
                    except OSError, _exc:
                        self.__logger.warning(_("Error while checking directory '%(dir)s': %(error)s.")\
                                              % {'dir' : path, 'error' : str(_exc)})
                        self.__snapshot.addToExcludeFlist(path)    # problems with `path` -> exclude it
                        self.__collect_stats.count_excl_forced()
            else:
                # it's a file (may also a link target in case of enabled `followlinks` option)
                self.__collect_stats.count_file()
                self.__cumulate_size(path)

    def __cumulate_size(self, path):
        """
        
        Files not contained in SNAR file are backuped in any case!
        (e.g. a directory was added to the includes)
        """
#        self.__logger.debug("%s" % path)
        _incl_file = False
        if self.__isfull:        # full snapshots do not have a base snar file
            _incl_file = True
        else:
            # we don't look at the access time since this was even modified during the last backup 
            ftime = max(self.__fstats.st_mtime,
                        self.__fstats.st_ctime)
            if path in self.__parent.get_base_snardict():
#                self.__logger.debug("%s: is in snapshot file." % path)
                if ftime > self.__parent.get_base_backup_time():
                    self.__logger.debug("Delta=%s - %s: %s > %s" % ((ftime - self.__parent.get_base_backup_time()),
                                                                     path, ftime,
                                                                     self.__parent.get_base_backup_time()))
                    _incl_file = True

            else:
                self.__logger.debug("%s: No yet included - included." % path)
                self.__collect_stats.count_new_file()
                _incl_file = True

        if _incl_file:
            self.__collect_stats.count_incl_file()
            self.__collect_stats.add_size(self.__fstats.st_size)
        else:
            self.__collect_stats.count_skip_file()

    def __compile_excl_regex(self):
        """Prepares (i.e. compiles) Regular Expressions used for excluding files from flist.
        """
        self.__logger.debug("Prepare Regular Expressions used for file exclusion.")
        _rexclude = []
        _snp_excl = self.__snapshot.getExcludes()
        if _snp_excl:
            for _regex in _snp_excl:
                if util.is_empty_regexp(_regex):
                    self.__logger.warning(_("Empty regular expression found. Skipped."))
                else:
                    if util.is_valid_regexp(_regex):
                        _regex_c = re.compile(_regex)
                        _rexclude.append(_regex_c)
                    else:
                        self.__logger.warning(_("Invalid regular expression ('%s') found. Skipped.") % _regex)
        self.__excl_regex = _rexclude

    def __prepare_explicit_flists(self):
        """Paths (i.e. directories and files) defined in the configuration are added
        to the corresponding include/exclude file lists. These lists represent the
        explicitely defined includes and excludes. Includes are stronger than excludes!
        
        The config GUI avoids the definition of a file as included and excluded at the same time.
        The `ConfigManager` returns the last defined entry in the case of multiple definitions
        in section `dirconfig`.        
        """
        _config = self.__configuration
        if _config is None:
            raise ValueError("No configuration object set.")

        # set the list to backup (includes) and to exclude
        self.__logger.debug("Preparation of include and exclude lists.")
        if _config.has_dirconfig_entries() is False:
            self.__logger.warning(_("No directories to backup defined."))
        else:
            for _dir, _incl in _config.get_dirconfig_local():
                if _incl == 1:
                    self.__snapshot.addToIncludeFlist(_dir)
                elif _incl == 0:
                    self.__snapshot.addToExcludeFlist(_dir)

        # add the default excluded ones
# TODO: why add an empty string?
# TODO: put the default excludes into `ConfigManager`.
# TODO: Remove this hack and replace it by proper shell pattern expansion (glob).
        _excludes = ["", "/dev/", "/proc/", "/sys/", "/tmp/"]
        if _config.get_target_dir() is not None:
            _excludes.append(_config.get_target_dir().rstrip(os.sep) + os.sep)
        for _excl in _excludes:
            self.__snapshot.disable_path_in_incl_filelist(_excl)

# TODO: Even better: Remove this inconsistency and don't use TAR's shell patterns. Prefer pure Regex exclusion.
        # LP #638072: no wildcards in excludes list;
        #             excluded directory yields in excluding contained files
#FIXME: trailing slashes are not retained when writing excludes file! Since exclude items
#       are literally compared this can exclude more dirs/files than intended!
        for _excl in _excludes:
            self.__snapshot.addToExcludeFlist(_excl)

        # sanity check of the lists
        self.__snapshot.check_and_clean_flists()

    def collect_files(self):
        """Collects information about files that are included resp. excluded in
        the backup.
        """
        self.__prepare_collecting()
        self.__compile_excl_regex()
        self.__prepare_explicit_flists()
        util.enable_timeout_alarm()

        # We have now every thing we need , the rexclude, excludelist, includelist and already stored 
        self.__logger.debug("Creation of the complete exclude list.")

        # walk recursively into paths defined as includes (therefore don't call nested paths)
        for _incl in self.__snapshot.get_eff_incl_filelst_not_nested():
            _incl = local_file_utils.normpath(_incl)
            self._check_for_excludes(_incl)


class FileCollectorConfigFacade(object):
    """Provides a simplified and unified read-only access to configuration options required
    for file collection. Purpose is to de-couple class `ConfigManager` and `FileCollector`
    since only very little configuration settings are required in order to collect the files.
    """
    def __init__(self, configuration, eff_local_targetdir):
        self.__configuration = None
        self.__eff_local_targetdir = eff_local_targetdir     # needed to exclude paths == target

        self.__maxsize_enabled = False
        self.__maxsize = 0

        self.__dirconfig = None
        self.__dirconfig_set = False

        self.set_configuration(configuration)

    def set_configuration(self, configuration):
        """Sets the given `configuration`. Corresponding attributes are
        set from this ConfigManager instance.
        """
#        if not isinstance(configuration, ConfigManager):
#            raise TypeError("Expected parameter of type 'ConfigManager'. "\
#                            "Got %s instead." % type(configuration))
        self.__configuration = configuration
        self.__set_maxsize_limit_from_config()
        self.__set_dirconfig_from_config()

    def __set_maxsize_limit_from_config(self):
        if self.__configuration is None:
            raise ValueError("No configuration set.")
        self.__maxsize_enabled = self.__configuration.has_maxsize_limit()
        self.__maxsize = self.__configuration.get_maxsize_limit()

    def __set_dirconfig_from_config(self):
        if self.__configuration is None:
            raise ValueError("No configuration set.")
        self.__dirconfig = self.__configuration.get_dirconfig_local()
        if self.__dirconfig is None:
            self.__dirconfig_set = False
        else:
            self.__dirconfig_set = True

    def is_maxsize_enable(self):
        return self.__maxsize_enabled

    def get_maxsize_limit(self):
        return self.__maxsize

    def get_target_dir(self):
        return self.__eff_local_targetdir

    def get_dirconfig_local(self):
        """Returns the directory configuration stored in a list of pairs (name, value).
        
        @rtype: List
        """
        return self.__dirconfig

    def has_dirconfig_entries(self):
        """Returns True if the `dirconfig` has any entries. Purpose is improvement of
        performance when checking for entries in the `dirconfig` and hiding implementation
        details about format/storage of the list.
        """
        return self.__dirconfig_set
