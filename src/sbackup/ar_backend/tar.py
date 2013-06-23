#   Simple Backup - provides access to TAR functionality
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
:mod:`tar` --- provides access to TAR functionality
===================================================

.. module:: tar
   :synopsis: provides access to TAR functionality
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

from gettext import gettext as _
import time
import os
import subprocess
import tempfile
import shutil
import re

from datetime import datetime


from sbackup.core.ConfigManager import ConfigurationFileHandler

from sbackup.fs_backend import fam

from sbackup.util.log import LogFactory
from sbackup.util.structs import SBdict
from sbackup.util import exceptions
from sbackup.util.exceptions import SBException
from sbackup.util import constants
from sbackup.util import system
from sbackup import util
from sbackup.util import local_file_utils
from sbackup.util import structs
from sbackup.util import log


GZIP_COMPRESSION_SPEED = "-1"


_FOP = fam.get_file_operations_facade_instance()


def getArchiveType(archive):
    """Determines the type of an archive by its file extension.
     
    @param archive: Full path to file to check  
    @return: tar, gzip, bzip2 or None
    @rtype: String
    """
    _res = None
    if archive.endswith(".bz2"):
        _res = "bzip2"
    elif archive.endswith(".gz") or archive.endswith(".tgz"):
        _res = "gzip"
    elif archive.endswith(".tar"):
        _res = "tar"
    return _res

def extract(sourcear, eff_local_sourcear, restore_file, dest , bckupsuffix = None, splitsize = None):
    """Extract from source archive the file "file" to dest.
    
    @param sourcear: path of archive
    @param file:
    @param dest:
    @param bckupsuffix: If set a backup suffix option is set to backup existing files
    @param splitsize: If set the split options are added supposing the size of the archives is this variable
    @type splitsize: Integer in 1024 Bytes
    """
    _logger = log.LogFactory().getLogger()
    _logger.debug("input param `sourcear`: %s" % sourcear)
    _logger.debug("input param `eff_local_sourcear`: %s" % eff_local_sourcear)
    restore_file = restore_file.lstrip(_FOP.pathsep)    # strip leading separator (as TAR did before)
    # tar option  -p, --same-permissions, --preserve-permissions:
    # ignore umask when extracting files (the default for root)

    options = ["-xp", "--ignore-failed-read", "--backup=existing", "--totals"]

    archType = getArchiveType(sourcear)
    _logger.debug("Archive type: %s" % archType)
    if archType == "tar" :
        pass
    elif archType == "gzip" :
        options.insert(1, "--gzip")
    elif archType == "bzip2" :
        options.insert(1, "--bzip2")
    else :
        raise SBException (_("Invalid archive type."))

    if system.is_superuser():
        options.append("--same-owner")
    if dest :
        options.append("--directory=" + dest)
    else :
        options.append("--directory=" + _FOP.pathsep)
    if bckupsuffix :
        options.append("--suffix=" + bckupsuffix)

    if splitsize > 0:
        options.extend(["-L %s" % splitsize , "-F %s" % util.get_resource_file("multipleTarScript")])
        if eff_local_sourcear is None:
            raise exceptions.FileAccessException(_("Effective path for `%s` is not available") % sourcear)

    _launcher = TarBackendLauncherSingleton()
    if eff_local_sourcear is None:
        _launcher.set_stdin_file(sourcear)
    else:
        options.append("--file=%s" % eff_local_sourcear)

    options.append(restore_file)

    _launcher.launch_sync(options, env = {})
    retVal = _launcher.get_returncode()
    outstr = _launcher.get_stdout()
    errStr = _launcher.get_stderr()

    __finish_tar(retVal, outstr, errStr)


# extract2 is currently (series 0.2) only used in SnapshotManager.makeTmpTAR
def extract2(sourcear, fileslist, dest, bckupsuffix = None, additionalOpts = None):
    """Extract the files listed in the 'fileslist' file to dest. This method 
    has been created to optimize the time spent by giving to tar a complete 
    list of file to extract.
    
    Use this if ever you have to extract more than 1 dir .
    
    @param sourcear:
    @param fileslist: a path to the file containing the list
    @param dest: destination
    @param bckupsuffix: 
    @param additionalOpts: a list of options to add
    """
    # tar option  -p, --same-permissions, --preserve-permissions:
    # ignore umask when extracting files (the default for root)
    options = ["-xp", "--ignore-failed-read", '--backup=existing']

    archType = getArchiveType(sourcear)
    if archType == "tar" :
        pass
    elif archType == "gzip" :
        options.insert(1, "--gzip")
    elif archType == "bzip2" :
        options.insert(1, "--bzip2")
    else :
        raise SBException (_("Invalid archive type."))

    if system.is_superuser():
        options.append("--same-owner")

    if dest:
        options.append("--directory=" + dest)
    else:
        options.append("--directory=" + _FOP.pathsep)

    if bckupsuffix:
        options.append("--suffix=" + bckupsuffix)

    if additionalOpts and type(additionalOpts) == list:
        options.extend(additionalOpts)

    options.extend(['--file=' + sourcear, '--null',
                    '--files-from=' + _FOP.normpath(fileslist)])

    outStr, errStr, retval = util.launch("tar", options)
    if retval != 0 :
        LogFactory.getLogger().debug("output was : " + outStr)
        raise SBException("Error when extracting : " + errStr)
    if outStr.strip() == "":
        outStr = "(nothing)"
    LogFactory.getLogger().debug("output was: " + outStr)


def appendToTarFile(desttar, fileslist, workingdir, additionalOpts):
    """
    @param desttar: The tar file to wich append
    @param fileslist The files to append, can be a list of files too
    @type fileslist: list
    @param workingdir: the dir to move in before appending the dir ( usefun for relative paths)
    @param additionalOpts: a list of additional option to append (will be append before changing the working dir)
    """
    options = ["--append", "--ignore-failed-read"]

    archType = getArchiveType(desttar)
    if archType == "tar" :
        pass
    elif archType == "gzip" :
        options.insert(1, "--gzip")
    elif archType == "bzip2" :
        options.insert(1, "--bzip2")
    else :
        raise SBException (_("Invalid archive type."))

    if additionalOpts and type(additionalOpts) == list :
        options.extend(additionalOpts)

    options.extend(['--file=' + desttar, '--null'])

    if workingdir:
        options.append("--directory=" + workingdir)

    options.append('--files-from=' + _FOP.normpath(fileslist))

    outStr, errStr, retval = util.launch("tar", options)
    if retval != 0 :
        LogFactory.getLogger().debug("output was : " + outStr)
        raise SBException("Error when extracting : " + errStr)
    if outStr.strip() == "":
        outStr = "(nothing)"
    LogFactory.getLogger().debug("output was: " + outStr)


def __prepare_common_opts(snapshot, targethandler, publish_progress, use_io_pipe):
    """Prepares common TAR options used when full or incremental
    backups are being made.  
    
    :param snapshot: The snapshot to fill in
    :return: a list of options to be use to launch tar
    
    :todo: Check whether it's necessary to escape white spaces in path names!
    
    """
    # don't escape spaces i.e. do not replace them with '\ '; this will fail
    # take care where to insert additional options (e.g. --gzip)

    tdir = snapshot.getPath()
    _snpname = snapshot.getName()
    options = ["-cS", "--directory=%s" % _FOP.pathsep,
               "--ignore-failed-read",
               "--no-check-device",
               "--blocking-factor", str(constants.TAR_BLOCKING_FACTOR),
               "--totals"
              ]

    # includes and excludes
    tmp_incl = _FOP.normpath(ConfigurationFileHandler().get_user_tempdir(),
                                 _FOP.get_basename(snapshot.getIncludeFListFile()))
    tmp_excl = _FOP.normpath(ConfigurationFileHandler().get_user_tempdir(),
                                 _FOP.get_basename(snapshot.getExcludeFListFile()))

    LogFactory.getLogger().debug("Temporary includes file: `%s`" % tmp_incl)
    LogFactory.getLogger().debug("Temporary excludes file: `%s`" % tmp_excl)

    if not _FOP.path_exists(tmp_incl):
        raise SBException("Temporary includes.list does not exist")
    if not _FOP.path_exists(tmp_excl):
        raise SBException("Temporary excludes.list does not exist")

    options.append('--files-from=%s' % tmp_incl)
    options.append('--exclude-from=%s' % tmp_excl)

    if snapshot.isFollowLinks() :
        options.append("--dereference")

    archivename = "files.tar"
    if snapshot.getFormat() == "gzip":
        options.insert(0, "--gzip")
        archivename += ".gz"
    elif snapshot.getFormat() == "bzip2":
        options.insert(0, "--bzip2")
        archivename += ".bz2"
    elif snapshot.getFormat() == "none":
        pass
    else:
        LogFactory.getLogger().debug("Setting compression to default 'none'")

    _ar_path = _FOP.normpath(tdir, archivename)
    if use_io_pipe:
        pass
    # write to socket file object?
    else:
        _larpath = targethandler.get_eff_fullpath(_snpname, archivename)
        if _larpath is None:
            raise exceptions.FileAccessException(_("Unable to get effective path for `%s`") % _ar_path)
        options.append('--file=%s' % _larpath)

    # progress signal
#TODO: improve calculation of number of checkpoints based on estimated transfer rate.
    if publish_progress is True:
        one_mb = 1000000
        one_gb = 1000 * one_mb
        _snpsize = snapshot.get_space_required()
        if _snpsize < (50 * one_mb):
            _ncheckp = 10
        elif _snpsize < (500 * one_mb):
            _ncheckp = 50
        elif _snpsize < (5 * one_gb):
            _ncheckp = 250
        else:
            _ncheckp = 500

        _checkpsize = _snpsize / _ncheckp
        _checkp = int(_checkpsize / constants.TAR_RECORDSIZE)
        if _checkp > 0:
            # LP: #875634
            # Sometimes the calculation of the space required goes badly wrong
            # and we could end-up with _checkp=1 for 30GB to save, making tar
            # VERY slow. Fix: set minimum value to 100
            _checkp = max(100, _checkp)
            options.append("--checkpoint=%s" % _checkp)
            _progessf = util.get_resource_file(resource_name = "sbackup-progress")
            options.append('--checkpoint-action=exec=%s' % _progessf)

    if LogFactory.getLogger().isEnabledFor(5):
        options.append("--verbose")

    return (options, _ar_path, tmp_incl, tmp_excl)


def __add_split_opts(snapshot, options, size):
    """
    Compiles and add the split management options to the TAR line.
    Valid for read and create actions
    @param snapshot: The snapshot to process
    @type snapshot: Snapshot
    @param options: the option in which to append
    @type options: list
    @param size: the size of each part (in KiB)
    @type size: int
    @raise SBException: if the snapshot format is other than none
    """
    if snapshot.getFormat() != "none" :
        raise SBException(_("For the moment split functionality is not compatible with compress option."))
    options.extend(["-L %s" % str(size), "-F %s" % util.get_resource_file("multipleTarScript")])
    return options


def __copy_temp_snarfile_into_snapshot(tmp_snarfile, snarfile):
    try:
        _FOP.copyfile(tmp_snarfile, snarfile)
    except exceptions.CopyFileAttributesError:
        LogFactory.getLogger().warning(_("Unable to change permissions for file '%s'.")\
                                    % snarfile)


def __remove_tempfiles(tmp_files):
    for _tmpf in tmp_files:
        try:
            _FOP.delete(_tmpf)
        except (OSError, IOError), error:
            LogFactory.getLogger().warning(_("Unable to remove temporary file `%(file)s`: %(error)s")\
                                            % { 'file' : _tmpf, 'error': error })


def mk_archive(snapshot, targethandler, publish_progress, supports_publish):
    if snapshot.isfull():
        _mk_tar_full(snapshot, targethandler, publish_progress, supports_publish)
    else:
        _mk_tar_incr(snapshot, targethandler, publish_progress, supports_publish)

def _mk_tar_incr(snapshot, targethandler, publish_progress, supports_publish):
    """
    Launch a TAR incremental backup
    @param snapshot: the snapshot in which to make the backup
    @raise SBException: if there was a problem with tar
    """
    LogFactory.getLogger().info(_("Launching TAR to make incremental backup."))

    # LP #638072: no wildcards in excludes list
    _env = { "GZIP" : GZIP_COMPRESSION_SPEED,
             "TAR_OPTIONS" : "--no-wildcards --anchored --no-wildcards-match-slash" }
    _use_io_pipe = targethandler.get_use_iopipe()
    _splitsize = snapshot.getSplitedSize()
    if _splitsize > 0:
        _use_io_pipe = False
        publish_progress = publish_progress and supports_publish
        _env["SBACKUP_VOLUME_SIZE"] = str(_splitsize * constants.TAR_VOLUME_SIZE_UNIT_IN_BYTES)

    options, ar_path, tmp_incl, tmp_excl = __prepare_common_opts(snapshot, targethandler,
                                                                 publish_progress, _use_io_pipe)

    if _splitsize > 0:
        options = __add_split_opts(snapshot, options, _splitsize)

    base_snarfile = snapshot.getBaseSnapshot().getSnarFile()
    snarfile = snapshot.getSnarFile()
    tmp_snarfile = _FOP.normpath(ConfigurationFileHandler().get_user_tempdir(),
                                 _FOP.get_basename(snarfile))

    LogFactory.getLogger().debug("Snapshot's base snarfile: %s" % base_snarfile)
    LogFactory.getLogger().debug("Snapshot's snarfile: %s" % snarfile)
    LogFactory.getLogger().debug("Temporary snarfile: %s" % tmp_snarfile)

    # For an INC backup the base SNAR file should exists
    if not _FOP.path_exists(base_snarfile) :
        LogFactory.getLogger().error(_("Unable to find the SNAR file to make an incremental backup."))
        LogFactory.getLogger().error(_("Falling back to full backup."))
        _mk_tar_full(snapshot, targethandler, publish_progress, _use_io_pipe)
    else:
        try:
            _FOP.copyfile(base_snarfile, tmp_snarfile)
        except exceptions.CopyFileAttributesError:
            LogFactory.getLogger().warning(_("Unable to change permissions for file '%s'.")\
                                    % tmp_snarfile)

        # check (and set) the permission bits; necessary if the file's origin
        # does not support user rights (e.g. some FTP servers, file systems...)
#FIXME: use generalized File operations here!
        if not local_file_utils.path_writeable(tmp_snarfile):
            local_file_utils.chmod(tmp_snarfile, 0644)
        # create the snarfile within a local directory; necessary if the
        # backup target does not support 'open' within the TAR process and
        # would fail
        options.append("--listed-incremental=" + tmp_snarfile)

        # launch TAR with empty environment
        _launcher = TarBackendLauncherSingleton()
        if _use_io_pipe:
            _launcher.set_stdout_file(ar_path)
        try:
            _launcher.launch_sync(options, env = _env)
            retVal = _launcher.get_returncode()
            outstr = _launcher.get_stdout()
            errStr = _launcher.get_stderr()
            __finish_tar(retVal, outstr, errStr)
            __copy_temp_snarfile_into_snapshot(tmp_snarfile, snarfile)

        finally:
            __remove_tempfiles([tmp_snarfile, tmp_incl, tmp_excl])


def _mk_tar_full(snapshot, targethandler, publish_progress, supports_publish):
    """Convenience function that launches TAR to create a full backup.

    @param snapshot: the snapshot in which to make the backup

    @raise SBException: if there was a problem with tar
    """
    LogFactory.getLogger().info(_("Launching TAR to make a full backup."))

    # LP #638072: no wildcards in excludes list
    _env = { "GZIP" : GZIP_COMPRESSION_SPEED,
             "TAR_OPTIONS" : "--no-wildcards --anchored --no-wildcards-match-slash" }
    _use_io_pipe = targethandler.get_use_iopipe()
    _splitsize = snapshot.getSplitedSize()
    if _splitsize > 0:
        _use_io_pipe = False
        publish_progress = publish_progress and supports_publish
        _env["SBACKUP_VOLUME_SIZE"] = str(_splitsize * constants.TAR_VOLUME_SIZE_UNIT_IN_BYTES)

    options, ar_path, tmp_incl, tmp_excl = __prepare_common_opts(snapshot, targethandler,
                                                                 publish_progress, _use_io_pipe)

    if _splitsize > 0:
        options = __add_split_opts(snapshot, options, _splitsize)

    snarfile = snapshot.getSnarFile()
    tmp_snarfile = _FOP.normpath(ConfigurationFileHandler().get_user_tempdir(),
                                 _FOP.get_basename(snarfile))

    LogFactory.getLogger().debug("Snapshot's snarfile: %s" % snarfile)
    LogFactory.getLogger().debug("Temporary snarfile: %s" % tmp_snarfile)

    # For a full backup the SNAR file shouldn't exists
    if _FOP.path_exists(snarfile) :
        _FOP.delete(snarfile)
    if _FOP.path_exists(tmp_snarfile) :
        _FOP.delete(tmp_snarfile)

    options.append("--listed-incremental=%s" % tmp_snarfile)

    # launch TAR with empty environment
    _launcher = TarBackendLauncherSingleton()
    if _use_io_pipe:
        _launcher.set_stdout_file(ar_path)
    try:
        _launcher.launch_sync(options, env = _env)
        retVal = _launcher.get_returncode()
        outstr = _launcher.get_stdout()
        errStr = _launcher.get_stderr()
        __finish_tar(retVal, outstr, errStr)
        __copy_temp_snarfile_into_snapshot(tmp_snarfile, snarfile)
    finally:
        __remove_tempfiles([tmp_snarfile, tmp_incl, tmp_excl])


def __finish_tar(exitcode, output_str, error_str):
    """
    @todo: Catch failing child process (e.g. gzip) in proper way.
    """
    if output_str is None:
        output_str = ""
    if error_str is None:
        error_str = ""

    _logger = LogFactory.getLogger()
    _logger.debug("Exit code: %s" % exitcode)
    _logger.debug("Standard out: %s" % output_str)
    _logger.debug("Error out: %s" % error_str)

    _res_err = []
    if error_str != "":
        err_lst = error_str.split("\n")
        for err_item in err_lst:
            if err_item == "/bin/tar: Removing leading `/' from member names":
                _logger.info(_("Leading '/' from member names were removed."))
            elif err_item == "/bin/tar: Removing leading `/' from hard link targets":
                _logger.info(_("Leading '/' from hard link targets were removed."))
            else:
                err_item = err_item.lstrip("/bin/tar: ")
                err_item = err_item.strip()
                if err_item != "":
                    _res_err.append(err_item)

    if exitcode == 0:
        if len(_res_err) == 1:
            _logger.info(_("TAR returned a message: %s") % _res_err[0])
        elif len(_res_err) > 1:
            _logger.info(_("TAR returned messages:\n%s") % "\n".join(_res_err))
        else:
            pass
        _logger.info(_("TAR has been finished successfully."))

    elif exitcode == 1:
        if len(_res_err) == 1:
            _logger.info(_("TAR returned a warning: %s") % _res_err[0])
        elif len(_res_err) > 1:
            _logger.info(_("TAR returned warnings:\n%s") % "\n".join(_res_err))
        else:
            pass
        _logger.info(_("TAR returned warnings but has been finished successfully."))

    else:
        # list-incremental is not compatible with ignore failed read ???
        _errmsg = _("Unable to finish successfully. TAR terminated with errors.")
        _logger.error("%s\n%s(exit code: %s)" % (_errmsg, error_str, exitcode))
        raise SBException(_errmsg)


def get_dumpdir_from_list(lst_dumpdirs, filename):
    """Searchs within the given list of dumpdirs for the given filename
    and the dumpdir if found.
    
    @raise SBExcetion: if filename couldn't be found in list  
    """
#    print ">>> get_dumpdir_from_list"
#    print "  Looking for: %s" % filename
#    print "  List of dumpdirs:"
#    for _ddir in lst_dumpdirs:
#        print "    %s" % _ddir
    _res = None

    if not isinstance(lst_dumpdirs, list):
        raise TypeError("Given list of dumpdirs must be of type list. Got %s "\
                        "instead." % type(lst_dumpdirs))
    for _ddir in lst_dumpdirs:
        if not isinstance(_ddir, Dumpdir):
            raise TypeError("Element in list of dumpdirs must be of type "\
                            "Dumpdir. Got %s instead." % type(_ddir))

        if _ddir.getFilename() == filename:
            _res = _ddir
            break

    if _res is None:
        raise SBException("File '%s' was not found in given list of Dumpdirs."
                                                                    % filename)
    return _res


class TarBackendLauncherSingleton(object):
    __metaclass__ = structs.Singleton

    _cmd = "/bin/tar"

    def __init__(self):
        self._proc = None
        self._argv = []

        # files used for input/output piping
        self._stdout_f = None
        self._stdin_f = None

        # results
        self._stdout = None
        self._stderr = None
        self._returncode = None

    def set_stdin_file(self, path):
        if self._stdout_f is not None:
            raise AssertionError("Redirecting stdin and stdout is not supported")
        self._stdin_f = path

    def set_stdout_file(self, path):
        if self._stdin_f is not None:
            raise AssertionError("Redirecting stdin and stdout is not supported")
        self._stdout_f = path

    def get_pid(self):
        _pid = None
        if self._proc is not None:
            _pid = self._proc.pid
        return _pid

    def launch_sync(self, opts, env = None):
        # note: get logger instance on demand as BackendLauncher is a Singleton
        _logger = log.LogFactory.getLogger()
        if self._proc is not None:
            raise AssertionError("Another process is already running")

        self._clear_returns()
        self._argv = opts
        self._argv.insert(0, self._cmd)
        errptr, errfile = tempfile.mkstemp(prefix = "error_")

        _stdout_param = None
        _stdin_param = None

        try:
            _logger.debug("Lauching: %s" % (" ".join(self._argv)))

            if self._stdout_f is None:
                outptr, outfile = tempfile.mkstemp(prefix = "output_")
                _stdout_param = outptr
            else:
                assert self._stdin_f is None
                _logger.debug("Output archive: %s" % self._stdout_f)
                _stdout_param = subprocess.PIPE
                _ardst = _FOP.openfile_for_write(self._stdout_f)

            if self._stdin_f is not None:
                assert self._stdout_f is None
                _logger.debug("Input archive: %s" % self._stdin_f)
                _stdin_param = subprocess.PIPE
                _arsrc = _FOP.openfile_for_read(self._stdin_f)

            self._proc = subprocess.Popen(self._argv, stdin = _stdin_param, stdout = _stdout_param,
                                          stderr = errptr, env = env)
            _logger.debug("Subprocess created")
            if self._stdout_f is not None:
                _arsrc = self._proc.stdout
            if self._stdin_f is not None:
                _ardst = self._proc.stdin

            if (self._stdin_f is not None) or (self._stdout_f is not None):
                shutil.copyfileobj(_arsrc, _ardst)
                _arsrc.close()
                _ardst.close()
                self._proc.wait()
            else:
                self._proc.communicate(input = None)

        except (exceptions.BackupCanceledError, exceptions.SigTerminatedError), error:
            self.terminate()

            if (self._stdin_f is not None) or (self._stdout_f is not None):
                _arsrc.close()
                _ardst.close()
            # todo: remove code duplication
            self._returncode = self._proc.returncode
            os.close(errptr)    # Close log handle
            self._stderr = local_file_utils.readfile(errfile)
            if self._stdout_f is None:
                os.close(outptr)
                self._stdout = local_file_utils.readfile(outfile)
            local_file_utils.delete(errfile)

            self._clear_proc()
            raise error

        self._returncode = self._proc.returncode
        os.close(errptr)    # Close log handle
        self._stderr = local_file_utils.readfile(errfile)
        if self._stdout_f is None:
            os.close(outptr)
            self._stdout = local_file_utils.readfile(outfile)
        local_file_utils.delete(errfile)

        self._clear_proc()

    def _clear_returns(self):
        self._stdout = None
        self._stderr = None
        self._returncode = None

    def _clear_proc(self):
        self._proc = None
        self._stdin_f = None
        self._stdout_f = None
        self._argv = []

    def is_running(self):
        """
        :todo: Add more tests whether the process is running or not!
        """
        _res = False
        if self._proc is not None:
            # more tests here
            _res = True
        return _res

    def get_stdout(self):
        return self._stdout

    def get_stderr(self):
        return self._stderr

    def get_returncode(self):
        return self._returncode

    def terminate(self):
        if self.is_running():
            try:
                self._proc.terminate()
            except OSError, error:
                log.LogFactory.getLogger().warning(_("Unable to terminate backend process: %s") % error)


class Dumpdir(object):
    """This is actually a single dumdir entry.
    
    Here is the definition from TAR manual:
    Dumpdir is a sequence of entries of the following form: C filename \0
    where C is one of the control codes described below, filename is the name
    of the file C operates upon, and '\0' represents a nul character (ASCII 0).
    
    The white space characters were added for readability, real dumpdirs do not
    contain them. Each dumpdir ends with a single nul character.
    
    Dumpdirs stored in snapshot files contain only records of types 'Y', 'N'
    and 'D'. 

    
    @note: Is the nul character stored???
    
    @see: http://www.gnu.org/software/tar/manual/html_chapter/Tar-Internals.html#SEC173
    
    @todo: It should be distiguished between 'unchanged', 'excluded' and
           'removed'!
    @todo: Rename this class into 'DumpdirEntry'!
    @todo: Add a 'DumpdirClass' that collects entries and creates output content!
    """

    INCLUDED = 'Y'
    UNCHANGED = 'N'
    DIRECTORY = 'D'

    # The dictionary mapping control with their meanings
    __HRCtrls = {'Y':_('Included'), 'N':_('Not changed'), 'D':_('Directory')}

    def __init__(self, line):
        """
        Constructor that takes a line to create a Dumpdir.
        we will parse this line and fill the Dumpdir in
        @param line: the line (in dumpdir point of view ) to parse
        @raise Exception: when the line doesn't have the requeried format
        
        @todo: make the instance variables private!
        """
        self.control = None
        self.filename = None
        self.__set_entry(line)

    def __str__(self):
        return "%s %s" % (self.filename, self.getHumanReadableControl())

    def __repr__(self):
        return self.__str__()

    def __set_entry(self, line):
        """Private helper method that sets the given dumdir entry. It checks
        for type and length of given parameter.
        
        @todo: Add checks for validity of control etc.!
        """
        if (not isinstance(line, str)):
            raise TypeError(_("Line must be a string"))
        line = line.strip("\0")
        if len(line) < 2:
            raise ValueError("Line must contain 2 characters at minimum.")
        self.control = line[0]
        self.filename = line[1:]

    def getFilename(self):
        """
        get the filename embedded in the Dumpdir
        @return: finename
        @raise Exception: if the filename is null 
        """
        if self.filename :
            return self.filename
        else :
            raise SBException(_("Dumpdir inconsistancy : 'filename' is empty"))

    def getControl(self):
        """
        Get the control character from the DumpDir
        @return: control
        @raise Exception: if the control is null
        
        @todo: Checking against None is useless here!
        """
        if self.control:
            return self.control
        else :
            raise SBException(_("Dumpdir inconsistancy : 'control' is empty"))

    def getHumanReadableControl(self):
        """
        Get the control character as a Human readable string from the DumpDir
        """
        return self.__HRCtrls[self.getControl()]

    @classmethod
    def getHRCtrls(cls):
        """
        @return: The Human Readable control dictionary
        @rtype: dict
        
        """
        return cls.__HRCtrls


class SnapshotFile(object):
    """A snapshot file (or directory file) is created during incremental
    backups with TAR. It contains the status of the file system at the time
    of the dump and is used to determine which files were modified since the
    last backup. GNU tar version 1.20 supports three snapshot file formats.
    They are called 'format 0', 'format 1' and 'format 2'.
    
    Dumpdirs stored in snapshot files contain only records of types 'Y', 'N'
    and 'D'. 
    
    For displaying the content of an incremental backup manually use:
    tar --bzip --list --incremental --verbose --verbose --file files.tar.bz2

    @see: http://www.gnu.org/software/tar/manual/html_chapter/Tar-Internals.html#SEC177
    
    @attention: Only snapshot files in `format 2` are supported.
    
    @todo: Rename into 'DirectoryFile' or 'SnapshotDirectoryFile' since it only
           collects directories!
           
    @todo: Add class describing a SnapshotFile record!
    """
    versionRE = re.compile("GNU tar-(.+?)-([0-9]+?)")

    __SEP = '\000'
    __entrySEP = 2 * __SEP

    # Infos on indices in a record 
    REC_NFS = 0
    REC_MTIME_SEC = 1
    REC_MTIME_NANO = 2
    REC_DEV_NO = 3
    REC_INO = 4
    REC_DIRNAME = 5
    REC_CONTENT = 6


    def __init__(self, filename, writeFlag = False):
        """Constructor
         
        @param filename: the snapshot file (absolute? do we use relative paths?) file path to get the infos (SNAR file)
        @param writeFlag: if set, the file will be created in case it doesn't exist
        """
        self.header = None
        self.snpfile = None
        self.version = None

        if _FOP.path_exists(filename):
            self.snpfile = filename
        else :
            if writeFlag :
                self.snpfile = filename
                fd = _FOP.openfile_for_append(self.snpfile)
                fd.close()
            else :
                raise SBException(_("File '%s' does not exist.") % filename)

    def __str__(self):
        _str = [ "Snapshot file",
                 " Header: %s" % self.getHeader(),
#                 " Version: %s" % self.getFormatVersion(),
                 " file name: %s" % self.snpfile,
                 " Content:"
               ]
        for _item in self.parseFormat2():
            _str.append("  %s" % _item)

        return "\n".join(_str)

    def get_filename(self):
        return self.snpfile

# (actually) not used: marked for removal
#    def getFormatVersion(self):
#        """
#        Get the format version
#        @return: the version 
#        @rtype: int 
#        """
#        if self.version :
#            return self.version
#
#        self.header = self.__getHeaderInfos()
#        m = self.versionRE.match(self.header)
#        if m :
#            # we are version 1 or 2
#            # check for version 2 first
#            self.version = m.group(2)
#        else :
#            # we are version 0
#            self.version = 0
#
#        return int(self.version)
#
#    def __getHeaderInfos(self):
#        """
#        Get the first line of the snapshot file
#        @return: the first line content
#        """
#        fd = open(self.snpfile)
#        header = fd.readline()
#        fd.close()
#        return header.strip()

# not used: marked for removal
#    def parseFormat0(self):
#        """
#        Iterator method that gives each line entry
#        @warning: only compatible tar version 0 of Tar format
#        @return: [nfs,dev,inode,name]
#        """
#        fd = open(self.snpfile)
#        # skip header which is the first line in this case
#        fd.readline()
#
#        for line in fd.readlines():
#            line = line.rstrip()
#
#            nfs = line[0] # can be a + or a single white space
#
#            dev, inode, name = line[1:].split(' ', 2)
#            yield [nfs, dev, inode, name]
#
#        fd.close()

# not used: marked for removal
#    def parseFormat1(self):
#        """
#        Iterator method that gives each line entry
#        @warning: only compatible tar version 1 of Tar format
#        @return: [nfs,mtime_sec,mtime_nsec,dev,inode,name]
#        """
#        fd = open(self.snpfile)
#        # skip header which is the 2 first lines in this case
#        fd.readline()
#        fd.readline()
#
#        for line in fd.readlines() :
#            line = line.rstrip()
#
#            nfs = line[0] # can be a + or a single white space
#
#            mtime_sec, mtime_nsec, dev, inode, name = line[1:].split(' ', 4)
#            yield [nfs, mtime_sec, mtime_nsec, dev, inode, name]
#
#        fd.close()

    def parseFormat2(self):
        """Iterator method that gives each line entry in SNAR-file.
        A line contains informations about a directory and its content.
        
        @warning: only compatible tar version 2 of Tar format
        
        @return: [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a list of Dumpdirs
        
        @todo: Iterator methods should have names like 'parseFormat2Iterator' or
               'parseFormat2Iter'!
        """

        def formatDumpDirs(content):
            """
            Subroutine to format a content into dump dirs
            """
            result = []
            if content :
                for d in content.rstrip('\0').split('\0'):
                    if d :
                        result.append(Dumpdir(d))
            return result

        def format(line):
            """
            subroutine to format a line including NUL char to have and array
            """
            nfs, mtime_sec, mtime_nano, dev_no, i_no, name, contents = line.lstrip("\0").split("\0", 6)
            return [nfs, mtime_sec, mtime_nano, dev_no, i_no, name, formatDumpDirs(contents)]


        fd = _FOP.openfile_for_read(self.snpfile)
        # skip header which is the first line and 2 entries separated with NULL in this case
#TODO: Handle empty files properly
        n = 0
        while n < 2 :
            c = fd.read(1)
            if len(c) != 1:
                raise SBException(_("The snarfile header is incomplete."))
            if c == '\0':
                n += 1

        currentline = ""
        c = fd.read(1)
        last_c = ''

        while c:
            currentline += c
            if c == '\0' and last_c == '\0' :
                # we got a line
                yield format(currentline)

                currentline = ''
                last_c = ''
            else :
                last_c = c
            c = fd.read(1)
        fd.close

    def getHeader(self):
        """
        Get the full header
        @return: the header (a string) or None if the file was empty
        @raise SBException: if the header is incomplete
        """
        fd = _FOP.openfile_for_read(self.snpfile)
#TODO: Handle empty files properly
        header = ""
        n = 0
        while n < 2 :
            c = fd.read(1)
            if len(c) != 1:
                raise SBException(_("The snarfile header is incomplete."))
            if c == '\0':
                n += 1
            header += c
        try:
            _FOP.close_stream(fd)
        except exceptions.FileAlreadyClosedError, error:
            log.LogFactory.getLogger().warn(_("File was already closed (ignored): %s") % error)

        return header

    def setHeader(self, timeofBackup):
        """
        Sets the header of the snar File. 
        GNU tar-1.19-2  -> in the first line
        second line is timeofBackupInSec\000timeofBackupInNano
        @param timeofBackup: The time to set in the snar file
        @type timeofBackup: datetime
        """
        if type(timeofBackup) != datetime :
            raise SBException("timeofBackup must be a datetime")
        fd = open(self.snpfile, 'w')

        fd.write("GNU tar-1.19-2\n")
        t = int(time.mktime(timeofBackup.timetuple()))
        fd.write(2 * (str(t) + self.__SEP))
        fd.close()

    def addRecord(self, record):
        """
        Write a record in the snar file. A record is a tuple with 6 entries + a content that is a dict
        @param record: A tuple that contains the record to add. [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a dict of {file:'control'}
        """
        if len(record) != 7:
            raise ValueError("Record must contain of 7 elments. Got %s instead." % str(len(record)))

        woContent, contents = record[:-1], record[-1]
        strContent = self.createContent(contents)   # compute contents
        toAdd = "%s%s%s" % (self.__SEP.join(woContent), self.__SEP, strContent)

        fd = _FOP.openfile_for_append(self.snpfile)
        fd.write("%s%s" % (toAdd, self.__entrySEP))
        fd.close()


    def createContent(self, contentList):
        """Creates a content item from a list of given Dumpdirs.
        
        @param contentList: the list of Dumpdirs
        @type contentList: list
        @return: a string containing the computed content
        @rtype: string
        """
        if type(contentList) != list :
            raise SBException("Contentlist must be a list : %r" % repr(contentList))

        result = ""

        for dumpdir in contentList:
            if not isinstance(dumpdir, Dumpdir):
                raise TypeError("Contentlist must contain elements of type "\
                                "'Dumdir'. Got %s instead." % type(dumpdir))
#            result += dumpdir.getControl() + dumpdir.getFilename() + self.__SEP
            result = "%s%s%s%s" % (result, dumpdir.getControl(), dumpdir.getFilename(), self.__SEP)

        return result

    def get_time_of_backup(self):
        """Returns the time of the snapshot (as stored in the snapshot file)
        in seconds since beginning of the epoch.
        
        @rtype: Float
        """
        _header = self.getHeader()
        _header_t = _header.split("\n")
        assert len(_header_t) == 2
        _time_t = _header_t[1].split(self.__SEP)
        assert len(_time_t) > 1
        _time = float("%s.%s" % (_time_t[0], _time_t[1]))
        return _time

    def get_dict_format2(self):
        """Returns the content of the snapshot file as dictionary.
        This provides a much faster way of accessing the content than
        parsing the file on demand. The required RAM is moderate,
        a 10GiB partition filled with files results in 6MiB dictonary.
        
        @warning: only compatible tar version 2 of Tar format
        @note: Uses the same algorithm as method `parseFormat2` and is ~15% faster
                than the high-level variant below.
        """
        _snardict = {}

        fd = _FOP.openfile_for_read(self.snpfile)
#TODO: Handle empty files properly
        header = ""
        n = 0
        while n < 2 :
            c = fd.read(1)
            if len(c) != 1:
                raise SBException(_("The snarfile header is incomplete."))
            if c == '\0':
                n += 1
            header += c
        # skip header which is the first line and 2 entries separated with NULL in this case
#FIXME: remove code duplication here and in `getHeader`

        currentline = ""
        last_c = ''
        c = fd.read(1)
        while c:
            currentline += c
            if c == '\0' and last_c == '\0' :
                # we got a line
                nfs, mtime_sec, mtime_nano, dev_no, i_no, _dirname, \
                    _content = currentline.lstrip("\0").split("\0", 6)
                _snardict[_dirname] = Dumpdir.DIRECTORY
                _content_t = _content.rstrip('\0').split('\0')
                for _entry in _content_t:
                    _entry = _entry.strip("\0")
                    if _entry:
                        _epath = _FOP.joinpath(_dirname, _entry[1:])
                        _snardict[_epath] = _entry[0]

                currentline = ''
                last_c = ''
            else :
                last_c = c
            c = fd.read(1)

        fd.close
        return _snardict

#    def get_dict_format2(self):
#        """        
#        @warning: only compatible tar version 2 of Tar format
#
#        more high-level programmed
#        """
##        _dirdict = {}
#        _snardict = {}
#
#        for _record in self.parseFormat2():
##            print _record
#            _dirname = _record[self.REC_DIRNAME]
#            _content = _record[self.REC_CONTENT]
##            if _dirname in _dirdict:
##                raise ValueError("Directory is already contained.")
##            _dirdict[_dirname] = _content
#            
#            _snardict[_dirname] = Dumpdir.DIRECTORY
#            
#            for _entry in _content:
##                print "Type: %s name: '%s' control: '%s'" %(type(_entry),
##                                                        _entry.getFilename(),
##                                                        _entry.getControl())
#                _epath = fam.joinpath(_dirname, _entry.getFilename())
#                _snardict[_epath] = _entry.getControl()
#            
#
##        print "Dir dictionary:\n%s" % _dirdict              
##        print "Snar dictionary:\n%s" % _snardict  
#        return _snardict


class SnapshotFileWrapper(object):
    """Something like an Interface class.
    
    @todo: Review/Implement
    """
    def __init__(self):
        pass

    def get_snapfile_path(self):
        raise NotImplementedError


class MemSnapshotFile(SnapshotFileWrapper, SBdict):
    """
    This is a representation in memory of a simplified SNAR file. The used structure is an SBDict.
    The "prop" value is the content of the directory. wich is a list of L{Dumpdir}
    
    @note: In the series 0.2 implementation this variant is not used.
    """

    def __init__(self, snapshotFile):
        """
        load the snapshotFile in memory
        @param snapshotFile: a SnapshotFile to convert in MemSnapshotFile
        @type snapshotFile: sbackup.util.tar.SnapshotFile
        """
        if not isinstance(snapshotFile, SnapshotFile) :
            raise Exception("A SnapshotFile is required")

        SnapshotFileWrapper.__init__(self)
#        SBdict.__init__(self, mapping)

        self.__snapshotFile = snapshotFile

        for f in snapshotFile.parseFormat2():
            self[f[-2]] = f[-1]

    def get_snapfile_path(self):
        return self.__snapshotFile.get_filename()

    def hasPath(self, path):
        """
        Checks if a path is include in the SNAR file
        @param path: The path to check
        @return: True if the file is included, False otherwise
        @rtype: boolean
        """
        return self.has_key(path)

    def addRecord(self, record):
        """
        Write a record in the snar file. A record is a tuple with 6 entries + a content that is a dict
        @param record: A tuple that contains the record to add. [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a dict of {file:'control'}
        """
        self.__snapshotFile.addRecord(record)
        self[record[-2]] = record[-1]

    def getHeader(self):
        self.__snapshotFile.getHeader()

    def setHeader(self, timeofBackup):
        """
        Sets the header of the snar File. 
        GNU tar-1.19-2  -> in the first line
        second line is timeofBackupInSec\000timeofBackupInNano
        @param timeofBackup: The time to set in the snar file
        @type timeofBackup: datetime
        """
        self.__snapshotFile.setHeader(timeofBackup)

    def getContent(self, dirpath):
        """
        convenance method to get the content of a directory.
        @param dirpath: The directory absolute path to get
        @type dirpath: str
        @return: The content of the dir
        @rtype: list
        """
        return self[dirpath]

    def getFirstItems(self):
        """
        Get the first items in this SnapshotFile (the lower level dirs in the file)
        @return: A list of paths
        @rtype: list 
        """
        result = list()
        for f in self.iterFirstItems():
            result.append(f)
        return result


class ProcSnapshotFile(SnapshotFileWrapper):
    """This is a Snapshotfile that will basically every time parse the
    snarfile for information.
    """

    def __init__(self, snapshotFile):
        """
        load the snapshotFile to get a reference on it
        @param snapshotFile: a SnapshotFile to convert in MemSnapshotFile
        @type snapshotFile: sbackup.util.tar.SnapshotFile
        """
        if not isinstance(snapshotFile, SnapshotFile) :
            raise TypeError(_("A SnapshotFile is required"))

        SnapshotFileWrapper.__init__(self)

        self.__snapshotFile = snapshotFile

    def __str__(self):
        _str = "Snar file: '%s'" % self.__snapshotFile
        return _str

    def get_snapfile_path(self):
        return self.__snapshotFile.get_filename()

    def get_snapfile_obj(self):
        """Returns the wrapped instance of the snapshot file.
        
        @return: snapshot file object
        @rtype: SnapshotFile
        """
        return self.__snapshotFile

    def hasPath(self, path):
        """
        Checks if a path is included in the SNAR file
        @param path: The path to check
        @return: True if the file is included, False otherwise
        @rtype: boolean
        """
        for f in self.__snapshotFile.parseFormat2():
            if f[SnapshotFile.REC_DIRNAME].rstrip(_FOP.pathsep) == path.rstrip(_FOP.pathsep):
                return True
        return False

    def hasFile(self, _file):
        """
        Checks if a file is included in the SNAR file. a file is in a directory thus in the content.
        @param _file: The file to check. a complete path must be given
        @return: True if the file is included, False otherwise
        @rtype: boolean
        """
        dir, inFile = _file.rsplit(_FOP.pathsep, 1)
        if not self.hasPath(dir):
            return False
        for f in self.getContent(dir):
            if f.getFilename() == inFile and f.getControl() != Dumpdir.UNCHANGED:
                return True
        return False

    def iterfiles(self):
        """
        iterator that returns every file in the snapshot
        """
        for l in self.__snapshotFile.parseFormat2():
            dir = l[-2]
            if l[-1] :
                for dumpdir in l[-1] :
                    yield dir + _FOP.pathsep + dumpdir.getFilename()

    def iterRecords(self):
        """Iterator over snar file records (wrapper on the
        'parseFormat2' method of SnaspshotFile
        """
        for record in self.__snapshotFile.parseFormat2():
            yield record


    def addRecord(self, record):
        """
        Write a record in the snar file. A record is a tuple with 6 entries + a content that is a dict
        @param record: A tuple that contains the record to add. [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a dict of {file:'control'}
        """
        self.__snapshotFile.addRecord(record)

    def getHeader(self):
        return self.__snapshotFile.getHeader()

    def setHeader(self, timeofBackup):
        """
        Sets the header of the snar File. 
        GNU tar-1.19-2  -> in the first line
        second line is timeofBackupInSec\000timeofBackupInNano
        @param timeofBackup: The time to set in the snar file
        @type timeofBackup: datetime
        """
        self.__snapshotFile.setHeader(timeofBackup)

    def getContent(self, dirpath):
        """convenance method to get the content of a directory.
        
        @param dirpath: The directory absolute path to get
        @type dirpath: str
        
        @return: The content of the dir
        @rtype: list
        
        @raise SBException: if the path isn't found in the snapshot file
        """
        for f in self.__snapshotFile.parseFormat2():
            if f[SnapshotFile.REC_DIRNAME].rstrip(_FOP.pathsep) == dirpath.rstrip(_FOP.pathsep):
                return f[SnapshotFile.REC_CONTENT]
        raise SBException(_("Directory does not exist: %s.") % dirpath)

    def getFirstItems(self):
        """
        Get the first items in this SnapshotFile (the lower level dirs in the file)
        @return: A list of paths
        @rtype: list 
        """

        def cleanDupl():
            if result:
                result.sort()
                last = result[-1]
                for i in range(len(result) - 2, -1, -1):
                    if last == result[i]:
                        del result[i]
                    else:
                        last = result[i]

        result = list()

        for f in self.__snapshotFile.parseFormat2():
            found = False

            for i in range(0, len(result)) :
                if result[i] == f[-2] or f[-2].startswith(result[i]) :
                    if found :
                        # then we are trying to overide
                        continue
                    else :
                        found = True
                        break
                elif result[i].startswith(f[-2]):
                    # replace with f[-2]
                    result[i] = f[-2]
                    found = True
                    # don't break cause it's possible that some others entries need to be overiden

            if not found :
                result.append(f[-2])
            else :
                cleanDupl()

        return result
