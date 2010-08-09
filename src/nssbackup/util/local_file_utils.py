#    Simple Backup - unified file handling
#
#   Copyright (c)2009-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#   Copyright (c)2007-2009: Ouattara Oumar Aziz <wattazoum@gmail.com>
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
:mod:`local_file_utils` --- unified file handling (local)
====================================================================

.. module:: local_file_utils
   :synopsis: common functions for unified file handling within local filesystems
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>

"""


import os.path
import shutil
import pickle
import stat
import types

import gzip
import uuid


from nssbackup.util import pathparse
from nssbackup.util import exceptions
from nssbackup.util import constants
from nssbackup.util import system
from nssbackup.util import log



#TODO: make these functions module functions? See article: Python is not Java

PATHSEP = system.PATHSEP

path_exists = os.path.exists
is_dir = os.path.isdir
listdir = os.listdir
makedir = os.mkdir #, 0750)
makedirs = os.makedirs #, 0750)
chmod = os.chmod
get_dirname = os.path.dirname
get_basename = os.path.basename
is_mount = os.path.ismount

# TDOD: Evaluate alternate implementations:
#def path_exists(path):
# os.path.exists(path)
# os.access(uri, os.F_OK)

#def copyfile(src, dest):
#    """Copies given file and metadata
#    """
#    if os.path.isdir(src):
#        raise ValueError("Given copy source is a directory, not a file")
##TODO: What happens if `dest` already exists?
#    if os.path.isfile(src):
#        shutil.copy2(src, dest)

def copyfile(src, dst):
    """Copies given file and metadata including file permissions.
    If this fails a custom exception is raised. 
    
    @param src: an existing file that should be copied
    @param dst: copy destination - an existing directory or full path to new file
                
    @return: None
    
    @raise CopyFileAttributesError: if the permissions could not be copied
    """
    prep_src, prep_dst = _prepare_copy(src, dst)
    shutil.copyfile(prep_src, prep_dst)
    try:
        shutil.copystat(prep_src, prep_dst)
    except OSError:
        raise exceptions.CopyFileAttributesError(\
                        "Unable to copy file attributes (permissions etc.) of file '%s'." % prep_dst)

def _prepare_copy(src, dst):
    """Helper function that prepares the given paths for copying
    using 'nssb_copy'.
    
    Source must be a file or symbolic link to a file!
    
    @todo: Implement test case for symbolic links!
    """
    # firstly the types are checked
    if not isinstance(src, types.StringTypes):
        raise TypeError("Given parameter must be a string. "\
                        "Got %s instead" % (type(src)))
    if not isinstance(dst, types.StringTypes):
        raise TypeError("Given parameter must be a string. "\
                        "Got %s instead" % (type(dst)))

    # only absolute paths are supported
    if not os.path.isabs(src):
        raise ValueError("Given copy source '%s' must be absolute" % src)
    if not os.path.isabs(dst):
        raise ValueError("Given copy destination '%s' must be absolute" % dst)

    # the source must be a file and exist
    if not os.path.exists(src):
        raise IOError("Given copy source '%s' does not exist" % src)
    if not os.path.isfile(src):
        raise IOError("Given copy source '%s' is not a file" % src)

    _src_file = os.path.basename(src)
    _src_dir = os.path.dirname(src)

    if os.path.isdir(dst):
        _dst_file = _src_file
        _dst_dir = dst
    elif dst.endswith(os.path.sep):
        _dst_file = _src_file
        _dst_dir = dst
    else:
        _dst_file = os.path.basename(dst)
        _dst_dir = os.path.dirname(dst)

    if not os.path.isdir(_dst_dir):
        raise IOError("Given copy destination '%s' does not exist" % _dst_dir)

    _dst_path = joinpath(_dst_dir, _dst_file)
    retval = (src, _dst_path)

    return retval

def listdir_fullpath(path) :
    """List a directory. Returns full paths to entries.
    """
    _lst = listdir(path)
    _res = []
    for _ent in _lst:
        _res.append(joinpath(path, _ent))
    return _res


def path_writeable(path):
    _res = os.access(path, os.W_OK)
    return _res

def normpath(*args):
    """Normalizes the given paths (i.e. concatenates them and removes trailing
    separators).
    
    @todo: Consistent handling of `normpath` (Quote: os.path.normpath - It should be understood
    that this may change the meaning of the path if it contains symbolic links!)
    
    :note: Be careful when using `normpath`. Consider `joinpath` instead.
    """
    _path = os.path.join(*args)
    _path = pathparse.remove_trailing_sep(_path)
#    _path = os.path.normpath(_path)
    return _path

def joinpath(*args):
    return pathparse.joinpath(*args)

def is_link(path):
    spath = pathparse.remove_trailing_sep(path)
    res = os.path.islink(spath)
    return res

def get_link(path):
    """Returns the target of given link `path`. Relative links remain
    unchanged (i.e. are not made absolute). 
    """
    if not is_link(path):
        raise ValueError("Given path is not a symbolic link.")
    _res = os.readlink(path)
    return _res

def get_link_abs(path):
    """Returns the absolute target of given link `path`. Relative links are
    modified (i.e. are made absolute). 
    """
    _ln_target = get_link(path)
    if os.path.isabs(_ln_target):
        _res = _ln_target
    else:
        _res = os.path.join(os.path.dirname(path), _ln_target)
    _res = os.path.abspath(_res)
    return _res

def delete(uri):
    """Deletes given file or directory (recursive).
    """
    if os.path.isdir(uri) and not os.path.islink(uri):
        shutil.rmtree(uri, ignore_errors = False)    #, onerror=_onerror)
    else:
        os.unlink(uri)

def force_delete(path):
    """Forces removal of given file or directory (recursive).
    """
    _add_write_permission(path, recursive = True)
    delete(path)

def force_move(src, dst):
    """Modified version of `shutil.move` that uses `nssb_copytree`
    and even removes read-only files/directories.
    :note: it does not work (and won't never) if the `src` is located within a read-only
            directory. We'd need to manipulate the parent dir in that case.
    """
    try:
        os.rename(src, dst)
    except OSError:
        if os.path.isdir(src):
            if shutil.destinsrc(src, dst):
                raise shutil.Error("Cannot move a directory '%s' into itself "\
                                   "'%s'." % (src, dst))
#            _copytree(src, dst, symlinks = True)
#FIXME: copy symlinks (not the target)
            _copytree(src, dst, symlinks = False)
            force_delete(src)
        else:
            shutil.copy2(src, dst)
            force_delete(src)

def _copytree(src, dst, symlinks = False):
    """mod of `shutil.copytree`. This doesn't fail if the
    directory exists, it copies inside.

    :param src: source path for copy operation
    :param dst: destination
    :param symlinks: copy symlinks?
    :type src: string
    :type dst: string

    """
    names = os.listdir(src)
    if not os.path.exists(dst) :
        os.makedirs(dst)
    errors = []
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                _copytree(srcname, dstname, symlinks)
            else:
                shutil.copy2(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, OSError), why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error, err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except OSError, why:
        errors.extend((src, dst, str(why)))
    if len(errors) > 0:
        raise shutil.Error, errors

def createfile(filepath):
    """
    Create an empty file
    @param filepath : The file path
    
    :todo: Review and improve!
    """
    filepath = filepath.rstrip(os.sep)
    spl = filepath.split(os.sep)
    if len(spl) == 1 :
        writetofile(filepath, "")
    else:
        _dir = filepath[:-len(spl[len(spl) - 1])]
        if path_exists(_dir):
            writetofile(filepath, "")
        else:
            makedir(_dir)
            writetofile(filepath, "")

def readfile(path):
    """Read a file from a given URI and returns a string with the read content.
    
    @rtype: String
    """
    fobj = open(path, "r")
    value = fobj.read()
    fobj.close()
    return value

def writetofile(path, content) :
    """
    Write a String to a file. You don't have to open and close the file.
    - File = path to the file
    - StringToWrite = String to write into the file.
    """
    fobj = open(path, "w")
    fobj.write(content)
    fobj.close()

def openfile(uri, write = False):
    " opens a file for reading or writing. Default is reading "
    if write:
        return open(uri, "w")
    else:
        return open(uri, "r")

def openfile_for_append(path):
    return open(path, "a+")

def pickleload(path):
    """
    Load a python object from the given pickle file
    @param file: the path of the pickle file
    """
    f = openfile(path)
    result = pickle.load(f)
    f.close()
    return result

def pickledump(datas, path):
    """
    Dump the given datas into the file given 
    @param datas: any type of python datas/object
    @param file : a file path to the file in wich the dump will be made
    """
    f = openfile(path, True)
    pickle.dump(datas , f)
    f.close()

def _add_write_permission(path, recursive = True):
    """Sets write permissions for user, group, and others for
    given directory or file (recursive). 
    """
    fstats = os.stat(path)
    fmode = fstats.st_mode
    fmode = fmode | system.UNIX_PERM_ALL_WRITE
    os.chmod(path, fmode)

    if os.path.isdir(path) and recursive is True:
        for _entry in os.listdir(path):
            _entrypath = os.path.join(path, _entry)
            if os.path.isdir(_entrypath)  and not os.path.islink(_entrypath):
                _add_write_permission(_entrypath)
            else:
                _add_write_permission(_entrypath, recursive = False)

def rename(src, dst):
    # avoids (misused) move operations using `rename`
    _dstf = joinpath(get_dirname(src), get_basename(dst))
    os.rename(src, _dstf)

def rename_errors_ignored(src, dst):
    try:
        rename(src, dst)
    except OSError:
        pass

def rename_rotating(src, dst, max_num, compressed = True):
    """Renames the given file `src` to `dst`. The destination (i.e. the new
    file name) is renamed in rotated manner prior the actual renaming
    process.
    If `compressed` is set to True, compressed files (*.gz) are considered.
    """
    if not isinstance(src, types.StringTypes):
        raise TypeError("Expected string as source. Got %s instead." % type(src))
    if not isinstance(dst, types.StringTypes):
        raise TypeError("Expected string as destination. Got %s instead." % type(dst))
    if not isinstance(max_num, types.IntType):
        raise TypeError("Expected integer as max. number. Got %s instead." % type(max_num))
    if max_num < 1:
        raise ValueError("Max. number must be greater than 0.")

    # at first: rotating rename of destination
    for _num in range(max_num, 0, -1):
        _rot_src = pathparse.append_str_to_filename(dst, str((_num - 1)))
        _rot_target = pathparse.append_str_to_filename(dst, str(_num))
        if compressed is True:
            _rot_src = "%s.gz" % _rot_src
            _rot_target = "%s.gz" % _rot_target
        if path_exists(_rot_src):
            rename(_rot_src, _rot_target)
    # then rename the source file
    rename(src, dst)


def compress_rotated_files(basename, max_num):
    """Compresses files with trailing number 0..max_num.
    """
    if not isinstance(basename, types.StringTypes):
        raise TypeError("Expected string as basename. Got %s instead." % type(basename))
    if not isinstance(max_num, types.IntType):
        raise TypeError("Expected integer as max. number. Got %s instead." % type(max_num))
    if max_num < 1:
        raise ValueError("Max. number must be greater than 0.")

    for _num in range(max_num, -1, -1):
        _src = pathparse.append_str_to_filename(basename, str(_num))
        if path_exists(_src):
            compress(_src)


def compress(src, keep_original = False):
    if not isinstance(src, types.StringTypes):
        raise TypeError("Expected string as source. Got %s instead." % type(src))

    out_file = "%s.gz" % src
    if path_exists(src) and os.path.isfile(src):
        f_in = open(src, 'rb')
        f_out = gzip.open(out_file, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        if not keep_original:
            delete(src)


def stat_device(path):
    _res = os.stat(path)[stat.ST_DEV]
    return _res

def stat_inode(path):
    _res = os.stat(path)[stat.ST_INO]
    return _res



def test_path(path, testdir_name, testfile_name, test_read = True):
    __logger = log.LogFactory().getLogger()

    testdir = os.path.join(path, testdir_name)
    testfile = os.path.join(testdir, testfile_name)

    __logger.info("Perform tests at specified location")
    try:
        __logger.debug("test access to specified path using native functions")
        _exists = path_exists(path)
        if bool(_exists) is False:
            raise exceptions.RemoteMountTestFailedError("Specified remote path is not accessable.")

        # test directory
        __logger.debug("Test testdir: %s" % testdir)
        _exists = path_exists(testdir)
        if bool(_exists) is True:
            raise exceptions.RemoteMountTestFailedError("Unable to create directory for testing purpose: Directory already exists.")

        __logger.debug("Create testdir")
        makedir(testdir)

        __logger.debug("Test testfile for existence")
        _exists = path_exists(testfile)
        if bool(_exists) is True:
            raise exceptions.RemoteMountTestFailedError("Unable to create file for testing purpose: File already exists.")

        _buffer = "Some arbitrary content: %s" % uuid.uuid4()
        __logger.debug("Write buffer: `%s` to file" % _buffer)
        writetofile(testfile, _buffer)

        if test_read is True:
            # and re-read
            __logger.debug("Re-read test file")
            _exists = path_exists(testfile)
            if bool(_exists) is False:
                raise exceptions.RemoteMountTestFailedError("Unable to open file for testing purpose: File does not exists.")
            _cont = readfile(testfile)
            if _cont != _buffer:
                raise exceptions.RemoteMountTestFailedError("Unable to read content from test file: content differs.")

        # clean-up
        __logger.debug("Remove file")
        delete(testfile)
        __logger.debug("Remove dir")
        delete(testdir)
    except (OSError, IOError), error:
        raise exceptions.RemoteMountTestFailedError(str(error))


def query_fs_info(path):
    _logger = log.LogFactory.getLogger()
    _size = constants.SIZE_FILESYSTEM_UNKNOWN
    _free = constants.FREE_SPACE_UNKNOWN

    try:
        _vstat = os.statvfs(path)
    except OSError, error:
        _logger.error("Error in `query_fs_info`: %s" % error)
    else:
        _size = _vstat.f_blocks * _vstat.f_bsize
        _free = _vstat.f_bavail * _vstat.f_bsize
    _logger.debug("FS info - size: %s free: %s" % (_size, _free))
    return (_size, _free)
