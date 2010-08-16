#   Simple Backup - snapshot definition
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
:mod:`sbackup.util.snapshot` -- snapshot definition
=====================================================

.. module:: snapshot
   :synopsis: Defines snapshots
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>
.. moduleauthor:: Ouattara Oumar Aziz <wattazoum@gmail.com>

"""


from gettext import gettext as _
import re
import types


from sbackup.fs_backend import fam
from sbackup.ar_backend import tar

from sbackup.core.ConfigManager import ConfigurationFileHandler

from sbackup.util.exceptions import NotValidSnapshotNameException
from sbackup.util.exceptions import SBException
from sbackup.util.exceptions import NotValidSnapshotException

from sbackup.util import constants
from sbackup.util import structs
from sbackup.util import log


AVAIL_SNP_FORMATS = ["none", "bzip2", "gzip"]


class Snapshot(object):
    """The snapshot class represents one snapshot in the backup directory.
    
    """

    __validname_re = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})[\:\.](\d{2})[\:\.](\d{2})\.\d+\..*?\.(.+)$")


    def __init__ (self, path):
        """The snapshot constructor.
        
        :param path : the path to the snapshot dir.
        
        :todo: Any distinction between creation of a new snapshot and opening\
               an existing one from disk would be useful! The reason is that\
               instantiation a Snapshot with a not existing path creates a\
               snapshot directory in any case, currently! We need to handle the\
               case: opening an snapshot that is supposed to exist but in fact\
               doesn't!
               
        :todo: Separate commit of snapshot and the snapshot (name, path, ...) itself into
               classes with concise responsibilities.

        """
        self.logger = log.LogFactory.getLogger()
        self._fop = fam.get_file_operations_facade_instance()

        # Attributes
        self.__name = False
        self.__base = None
        self.__format = "none" # default value

        self.__followlinks = False

        self.__snarfile = None

        # explicitely defined include and exclude file lists; these lists are filled from the configuration
        self.__includeFlist = structs.SBdict()
        self.__includeFlistFile = None # Str
        self.__excludeFlist = structs.SBdict()
        self.__excludeFlistFile = None # Str

        self.__space_required = constants.SPACE_REQUIRED_UNKNOWN
        self.__splitedSize = 0
        self.__excludes = False

        self.__packages = False
        self.__version = False
        self.__snapshotpath = None

        self.__baseSnapshot = None

        # set some attributes
        self.setPath(path)    # sets path and validates name

        # check if it's an existing snapshot
        if self._fop.path_exists(self.__snapshotpath):
            self.__validateSnapshot(self.__snapshotpath, self.__name)
        else : # Snapshot for creation
            self._fop.makedir(self.__snapshotpath)

    def __str__(self):
        "Return the snapshot name"
        return self.getName()

    def set_space_required(self, space):
        if not isinstance(space, (types.IntType, types.LongType)):
            raise TypeError("Parameter of string type expected. Got %s instead." % str(type(space)))
        space = long(space)
        self.__space_required = space

    def get_space_required(self):
        return self.__space_required

    # Public Methods
    def getName(self) :
        " return the name of the snapshot (ie the dir name)"
        if not self.__name :
            raise SBException(_("Snapshot is inconsistent: __name is not set "))
        else :
            return self.__name

    def getDate(self):
        """
        You can get from the dictionary returned the following keys :
        year, month, day, hour, minute, second
        @return : a dictionary with the date time this snapshot has been taken.
        """
        m = re.match(self.__validname_re , self.getName())
        if not m : raise NotValidSnapshotNameException(_("Name of snapshot '%s' doesn't match requirement") % self.getName())
        date = {"year" : int(m.group(1)), "month":int(m.group(2)), "day":int(m.group(3)),
            "hour":int(m.group(4)), "minute":int(m.group(5)), "second":int(m.group(6))}
        return date

    def getIncludeFlist(self):
        """Returns the list of files included into this snapshot.

        @rtype: SBDict
        """
        return self.__includeFlist

    def get_effective_incl_filelist(self):
        """Returns the *effective* list of files included into this snapshot.

        @rtype: SBDict
        """
        return self.__includeFlist.getEffectiveFileList()

    def get_eff_incl_filelst_not_nested(self):
        """Returns the *effective* list of files included into this snapshot.

        @rtype: SBDict
        """
        return self.__includeFlist.get_eff_filelist_not_nested()

    def is_path_in_incl_filelist(self, path):
        """Checks whether the given `path` is contained in list of included files.
        Only full paths (no sub-paths) are considered.
        """
        return self.__includeFlist.hasFile(path)

    def is_subpath_in_incl_filelist(self, path):
        """Checks whether the given `path` is contained in list of included files.
        Full paths as well as sub-paths are considered.
        """
        return self.__includeFlist.contains_path(path)

    def is_path_in_excl_filelist(self, path):
        """Checks whether the given `path` is contained in list of excluded files.
        Only full paths (no sub-paths) are considered.
        """
        return self.__excludeFlist.hasFile(path)

    def disable_path_in_excl_filelist(self, path):
        """Searches for the given `path` in the list of excluded files and set
        the properties to None. Sub-paths are also considered.
        """
        if self.__excludeFlist.has_key(path):
            self.__excludeFlist[path][0] = None

    def disable_path_in_incl_filelist(self, path):
        """Searches for the given `path` in the list of included files and set
        the properties to None. Sub-paths are also considered.
        """
        if self.__includeFlist.has_key(path):
            self.__includeFlist[path][0] = None

    def getExcludeFlist(self):
        """
        get the Exclude file list
        @rtype: list
        """
        return self.__excludeFlist

    def getExcludeFListFile(self):
        """
        @return: the path to the exclude file list file
        """
        if not self.__excludeFlistFile :
            self.__excludeFlistFile = self._fop.joinpath(self.getPath(), "excludes.list")

        return self.__excludeFlistFile

    def getIncludeFListFile(self):
        """
        @return: the path to the include file list file
        """
        if not self.__includeFlistFile :
            self.__includeFlistFile = self._fop.joinpath(self.getPath(), "includes.list")

        return self.__includeFlistFile

    def getSnarFile(self):
        """
        @return: the path to the TAR SNAR file
        """
        if not self.__snarfile :
            self.__snarfile = self._fop.joinpath(self.getPath(), "files.snar")
        return self.__snarfile

    def getPath(self) :
        "return the complete path of the snapshot"
        if not self.__snapshotpath :
            raise SBException(_("Snapshot is inconsistent: __snapshotpath is not set "))
        else :
            return self.__snapshotpath

    def getFormat(self):
        """
        Returns the compression format of the snapshot (from the "format" file or default value)
        """
        _formatf = self._fop.joinpath(self.getPath(), "format")
        if self._fop.path_exists(_formatf):
            self.__format = self._fop.readfile(_formatf).split('\n')[0]
        return self.__format

    def getBase(self) :
        """Returns the name of the base snapshot of this snapshot. If this
        is a full dump, None is returned. Please note that, if a base name
        was successful read from the snapshot directory once, this name is
        returned on any further calls to this method. If you don't want this
        you need to reset `self.__base` to None before.
        
        """
        if not self.__base:
            basefile = self._fop.joinpath(self.__snapshotpath, "base")
            if not self._fop.path_exists(basefile):
                self.__base = None
            else:
                if self.isfull():
                    raise AssertionError("Assertion failed when retrieving "\
                            "snapshot's base: A full backup ('%s') should not "\
                            "have a base file." % self)
                self.__base = self._fop.readfile(basefile).strip()
        return self.__base

    def getBaseSnapshot(self):
        """
        Return the base snapshot (as a Snapshot ) not only the name
        @return: the base Snapshot if it exists or None otherwise (we are a full snapshot) 
        """
        if self.__baseSnapshot is None:
            if not self.isfull():
                if self.getBase():
                    _path = self._fop.get_dirname(self.getPath())
                    _basef = self._fop.joinpath(_path, self.getBase())
                    self.__baseSnapshot = Snapshot(_basef)
        return self.__baseSnapshot

    def getArchive(self):
        """
        Get the snapshot archive which depends on the Format
        @raise NonValidSnapshotException: if the archive equivalent to the described format doesn't exist
        @return: the path to the archive
        """
        problem = False

        if self.getFormat() == "none":
            _arn = self._fop.joinpath(self.getPath(), "files.tar")
            if self._fop.path_exists(_arn):
                return _arn
            else :
                problem = True

        elif self.getFormat() == "gzip":
            _arn = self._fop.joinpath(self.getPath(), "files.tar.gz")
            if self._fop.path_exists(_arn):
                return _arn

            elif self.getVersion() == "1.4":
                self.logger.warning("The tgz name is deprecated, please upgrade Snapshot to Version 1.5")
                _arn = self._fop.joinpath(self.getPath(), "files.tgz")
                if self._fop.path_exists(_arn):
                    return _arn
                else :
                    problem = True
            else :
                problem = True

        elif self.getFormat() == "bzip2":
            _arn = self._fop.joinpath(self.getPath(), "files.tar.bz2")
            if self._fop.path_exists(_arn) :
                return _arn
            else :
                problem = True

        else:
            problem = True

        if problem :
            raise NotValidSnapshotException(_("The snapshot compression format is supposed to be '%s' but the corresponding well named file wasn't found") % self.getFormat())

    def getVersion(self) :
        """Retrieves and returns the version of the snapshot.

        """
        if self.__version:
            return self.__version
        elif ":" in self.getName():
            self.__version = "1.0"
            return self.__version
        else:
            verfile = self._fop.joinpath(self.getPath(), "ver")
            if not self._fop.path_exists(verfile):
                return False
            else :
                ver = self._fop.readfile(verfile)
#                self.logger.debug("Version read from snapshot: `%s`" % ver)
                try :
                    # major = 
                    int(ver[0])
                    # minor = 
                    int(ver[2])
                except Exception:
                    raise SBException(_("%(file)s doesn't contain valid value. Ignoring incomplete or non - backup directory. ") % {"file" : verfile})
                self.__version = ver[:3]
                return self.__version

    def getExcludes(self) :
        "Return the content of excludes (the list of Regex excludes)"
        if self.__excludes : return self.__excludes
        else :
            excludefile = self._fop.joinpath(self.getPath(), "excludes")
            if not self._fop.path_exists(excludefile):
                return False
            else :
                self.__excludes = self._fop.pickleload(excludefile)
                return self.__excludes

    def getPackages(self) :
        "Return the packages"
        if self.__packages : return self.__packages
        else :
            packagesfile = self._fop.joinpath(self.getPath(), "packages")
            if not self._fop.path_exists(packagesfile):
                return False
            else :
                self.__packages = self._fop.readfile(packagesfile)
                return self.__packages

    def getSnapshotFileInfos(self, useMem = False, writeFlag = False):
        """Returns a wrapper for the SnapshotFile resp. DirectoryFile that
        contains information what files are stored in this snapshot.

        @param useMem: use or not the memory to store infos about the SNAR file
        @type useMem:  boolean
        @param writeFlag: Will be passed to the SnapshotFile to permit writing
        @type writeFlag:  boolean

        @return: the corresponding SnapshotFile (Mem or Proc)

        @note: The only method usable afterward is getContent(path)
        """
        snpfile = tar.SnapshotFile(self.getSnarFile(), writeFlag)
        snpfileinfo = None

        if useMem:
            snpfileinfo = tar.MemSnapshotFile(snpfile)
        else :
            snpfileinfo = tar.ProcSnapshotFile(snpfile)

        return snpfileinfo

    def getSplitedSize(self):
        """
        @return: the size of each archive in the snapshot (0 means unlimited)

        @todo: Implement CQS pattern !
        """
        _formatf = self._fop.joinpath(self.getPath(), "format")
        if self._fop.path_exists(_formatf):
            self.__splitedSize = int(self._fop.readfile(_formatf).split('\n')[1])
        return self.__splitedSize

    def isfull(self):
        """
        @return: True if the snapshot is full and false if inc
        """
        _name = str(self.getName())
        return _name.endswith(".ful")

    def isFollowLinks(self):
        return self.__followlinks

    def commit(self, publish_progress = False, supports_publish = True):
        """Commit snapshot data (i.e. write to disk)
        
        :param publish_progress: Flag whether to call checkpoint script
        :param use_io_pipe: Flag whether to use pipes instead of files defined as parameters for archive
                            writing (should be hidden in FAM)
        
        :todo: Hide implementation detail `use_io_pipe`. 
        """
        if not self.isfull():
            self.commitbasefile()
        self.commitFormatfile()
        self.commitexcludefile()
        self.commitpackagefile()
        self.commitflistFiles()
        self.__commit_archive(publish_progress, supports_publish)
        self.commitverfile()

    def addToIncludeFlist (self, item) :
        """
        Add an item to be backup into the snapshot.
        Usage :  addToIncludeFlist(item) where
        - item is the item to be add (file, dir, or link)

        The `include flist` is of type `SBDict`, the according `props` for a single entry
        is '1' for included items.
        """
        self.__includeFlist[item] = "1"

    def addToExcludeFlist (self, item) :
        """
        Add an item to not be backup into the snapshot.
        Usage :  addToExcludeFlist(item) where
        - item is the item to be add (file, dir, or link)

        The `exclude flist` is of type `SBDict`, the according `props` for a single entry
        is '0' for excluded items.
        """
        self.__excludeFlist[item] = "0"

    def check_and_clean_flists(self):
        """Checks include and exclude flists for entries contained in both lists.
        Entries stored in both lists are removed from the exclude list (include overrides
        exclude).

        In theory it is impossible but what's in the case of manually written configuration files?
        
        @todo: Implement this method.
        """
        pass

    # Setters    
    def setFormat(self, cformat = None):
        """
        Sets the backup compression format
        cformat : the format to set
        """
        if cformat in AVAIL_SNP_FORMATS :
            self.logger.debug("Set the compression format to %s" % cformat)
            self.__format = cformat

    def setPath(self, path) :
        "Set the complete path of the snapshot. That path will be used to get the name of the snapshot"
        self.__snapshotpath = self._fop.normpath(str(path))
        name = self._fop.get_basename(self.__snapshotpath)
        if not self.__isValidName(name) :
            raise NotValidSnapshotNameException(_("Name of Snapshot not valid : %s") % self.__name)
        else :
            self.__name = name

    def setBase(self, baseName) :
        """Sets `baseName` as the name of the base snapshot of this
        snapshot and clears the reference to base snapshot object.
        It is not possible to set the base for a full backup, this
        raises a `SBException`. The `baseName` is checked for validity.
        Note that the base of the snapshot is not committed to disk
        if it is set using this method. Call `commitbasefile` for this.
        
        """
        if self.isfull():
            self.__base = None
            self.__baseSnapshot = None
            raise SBException("Base cannot be set for full snapshot.")
        if not self.__isValidName(baseName) :
            raise SBException (_("Name of base not valid : %s") % self.__name)
        # set the name and clean the baseSnapshot
        self.__base = baseName
        self.__baseSnapshot = None

    def setVersion(self, ver = "1.5") :
        "Set the version of the snapshot"
        self.__version = ver

    def setExcludes(self, excludes) :
        "Set the content of excludes (the list of Regex excludes)"
        self.__excludes = excludes

    def setPackages(self, packages = "") :
        """
        set the packages list for debian based distros
        @param packages: Must be the results of the 'dpkg - -get - selections' command . default = '' 
        """
        self.__packages = packages

    def setSplitedSize(self, size):
        """
        @param size: The size in KiB to set
        
        """
        if type(size) != int:
            raise TypeError("The size parameter must be an integer")
        self.__splitedSize = size

    def setFollowLinks(self, activate):
        """
        @param activate: boolean to activate symlinks follow up 
        """
        if type(activate) != bool :
            raise TypeError("the activate parameter must be a boolean")
        self.__followlinks = activate

    # Private
    def __validateSnapshot(self, path, name):
        """
        Validate the snapshot
        @param path : the snapshot path
        @param name : the snapshot name 
        """
        # validate the name
        if not self.__isValidName(self.__name) :
            raise NotValidSnapshotNameException(_("Invalid name of snapshot: %s") % self.__name)

        _verf = self._fop.joinpath(self.getPath(), "ver")
        if  not self._fop.path_exists(_verf):
            raise NotValidSnapshotException(_("Unable to read mandatory file `ver`"))

    def __isValidName(self, name) :
        " Check if the snapshot name is valid "
        _res = False
        if re.match(self.__validname_re , name) is not None:
            if name.endswith(".ful") or name.endswith(".inc"):
                _res = True
        return _res

    def commitFormatfile(self):
        """
        writes the format file
        """
        formatInfos = self.getFormat() + "\n"
        formatInfos += str(self.getSplitedSize())

        _formatf = self._fop.joinpath(self.getPath(), "format")
        self._fop.writetofile(_formatf, formatInfos)

    def commitverfile(self) :
        """Commit ver file on the disk.
        """
        if not self.getVersion():
            self.setVersion()
        _ver = self.getVersion()
        _verf = self._fop.joinpath(self.getPath(), "ver")
        self._fop.writetofile(_verf, _ver)
        self.logger.debug("Commit `ver` file `%s` with info `%s`" % (_verf, _ver))

    def commitbasefile(self):
        """In case this snapshot is an incremental snapshot, base file is
        committed to the disk. If not, this method shouldn't be called.
        The absence of a base for an incremental backup raises a SBException.
        
        """
        if self.isfull():
            self.logger.debug("WARNING: Attempt of committing base file for "\
                              "full snapshot ' % s'." % self.getName())
        else:
            if self.getBase():
                _basef = self._fop.joinpath(self.getPath(), "base")
                self._fop.writetofile(_basef, self.getBase())
            else:
            # base file was not found or base wasn't set. It MUST be full backup
                raise SBException(_("Base name must be set for incremental backup."))

    def commitexcludefile(self):
        """
        Commit exclude file on the disk (the list of Regex excludes).
        @raise SBException: if excludes hasn't been set 
        """
        _exf = self._fop.joinpath(self.getPath(), "excludes")
        self._fop.pickledump(self.__excludes, _exf)

    def commitflistFiles(self):
        """
        Commit the include.list and exclude.list to the disk.
        @todo: simplify the written files! The *.tmp files are partly obsolete.
        """
        if self._fop.path_exists(self.getIncludeFListFile()):
            raise SBException("includes.list should not exist at this stage")
        if self._fop.path_exists(self.getExcludeFListFile()):
            raise SBException("excludes.list should not exist at this stage")

        self._fop.writetofile(self.getIncludeFListFile(),
                              "\n".join(self.__includeFlist.getEffectiveFileList()))
        self._fop.writetofile(self.getExcludeFListFile(),
                              "\n".join(self.__excludeFlist.getEffectiveFileList()))

        # commit temporary lists
#FIXME: unify creation and storage of tmp. files and names
        tmp_incl = self._fop.normpath(ConfigurationFileHandler().get_user_tempdir(),
                                     self._fop.get_basename(self.getIncludeFListFile()))
        tmp_excl = self._fop.normpath(ConfigurationFileHandler().get_user_tempdir(),
                                     self._fop.get_basename(self.getExcludeFListFile()))

        self._fop.writetofile(tmp_incl,
                              "\n".join(self.__includeFlist.get_eff_filelist_not_nested()))
        self._fop.writetofile(tmp_excl,
                              "\n".join(self.__excludeFlist.getEffectiveFileList()))

    def commitpackagefile(self):
        " Commit packages file on the disk"
        _packf = self._fop.joinpath(self.getPath(), "packages")
        if not self.getPackages() :
            self._fop.writetofile(_packf, "")
        else:
            self._fop.writetofile(_packf, self.getPackages())

    def read_excludeflist_from_file(self):
        fe = self._fop.openfile_for_read(self.getExcludeFListFile())
        _res = set(line.strip("\n") for line in fe)
        fe.close()
        return _res

    def __commit_archive(self, publish_progress, supports_publish):
        " Make the backup on the disk "
        tar.mk_archive(self, publish_progress, supports_publish)
