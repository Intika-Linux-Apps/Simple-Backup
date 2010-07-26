#    Simple Backup - file access management using GIO/GVFS
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
"""
:mod:`nssbackup.util.gio_utils` -- file access management using GIO/GVFS
========================================================================

.. module:: gio_utils
   :synopsis: public entry point to file access management using GIO/GVFS
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""


from gettext import gettext as _
import types
import time
import uuid
import pickle

import glib
import gio


from nssbackup.util import log
from nssbackup.util import constants
from nssbackup.util import exceptions
from nssbackup.util import local_file_utils
from nssbackup.util import interfaces
from nssbackup.util import pathparse
from nssbackup.util import structs


errorcodes = {
    gio.ERROR_ALREADY_MOUNTED : exceptions.ErrorDescription(gio.ERROR_ALREADY_MOUNTED,
                                                            "ERROR_ALREADY_MOUNTED",
                                                            "File is already mounted."),
    gio.ERROR_BUSY : exceptions.ErrorDescription(gio.ERROR_BUSY, "ERROR_BUSY", "File is busy."),
    gio.ERROR_CANCELLED : exceptions.ErrorDescription(gio.ERROR_CANCELLED, "ERROR_CANCELLED", "Operation was cancelled. See gio.Cancellable."),
    gio.ERROR_CANT_CREATE_BACKUP : exceptions.ErrorDescription(gio.ERROR_CANT_CREATE_BACKUP, "ERROR_CANT_CREATE_BACKUP", "Backup couldn't be created."),
    gio.ERROR_CLOSED : exceptions.ErrorDescription(gio.ERROR_CLOSED, "ERROR_CLOSED", "File was closed."),
    gio.ERROR_EXISTS : exceptions.ErrorDescription(gio.ERROR_EXISTS, "ERROR_EXISTS", "File already exists error."),
    gio.ERROR_FAILED : exceptions.ErrorDescription(gio.ERROR_FAILED, "ERROR_FAILED", "Generic error condition for when any operation fails."),
    gio.ERROR_FAILED_HANDLED : exceptions.ErrorDescription(gio.ERROR_FAILED_HANDLED, "ERROR_FAILED_HANDLED", "Operation failed and a helper program has already interacted with the user. Do not display any error dialog."),
    gio.ERROR_FILENAME_TOO_LONG : exceptions.ErrorDescription(gio.ERROR_FILENAME_TOO_LONG, "ERROR_FILENAME_TOO_LONG", "Filename is too many characters."),
    gio.ERROR_HOST_NOT_FOUND : exceptions.ErrorDescription(gio.ERROR_HOST_NOT_FOUND, "ERROR_HOST_NOT_FOUND", "Host couldn't be found (remote operations)."),
    gio.ERROR_INVALID_ARGUMENT : exceptions.ErrorDescription(gio.ERROR_INVALID_ARGUMENT, "ERROR_INVALID_ARGUMENT", "Invalid argument."),
    gio.ERROR_INVALID_FILENAME : exceptions.ErrorDescription(gio.ERROR_INVALID_FILENAME, "ERROR_INVALID_FILENAME", "Filename is invalid or contains invalid characters."),
    gio.ERROR_IS_DIRECTORY : exceptions.ErrorDescription(gio.ERROR_IS_DIRECTORY, "ERROR_IS_DIRECTORY", "File is a directory error."),
    gio.ERROR_NOT_DIRECTORY : exceptions.ErrorDescription(gio.ERROR_NOT_DIRECTORY, "ERROR_NOT_DIRECTORY", "File is not a directory."),
    gio.ERROR_NOT_EMPTY : exceptions.ErrorDescription(gio.ERROR_NOT_EMPTY, "ERROR_NOT_EMPTY", "File is a directory that isn't empty."),
    gio.ERROR_NOT_FOUND : exceptions.ErrorDescription(gio.ERROR_NOT_FOUND, "ERROR_NOT_FOUND", "File not found error."),
    gio.ERROR_NOT_MOUNTABLE_FILE : exceptions.ErrorDescription(gio.ERROR_NOT_MOUNTABLE_FILE, "ERROR_NOT_MOUNTABLE_FILE", "File cannot be mounted."),
    gio.ERROR_NOT_MOUNTED : exceptions.ErrorDescription(gio.ERROR_NOT_MOUNTED, "ERROR_NOT_MOUNTED", "File isn't mounted."),
    gio.ERROR_NOT_REGULAR_FILE : exceptions.ErrorDescription(gio.ERROR_NOT_REGULAR_FILE, "ERROR_NOT_REGULAR_FILE", "File is not a regular file."),
    gio.ERROR_NOT_SUPPORTED : exceptions.ErrorDescription(gio.ERROR_NOT_SUPPORTED, "ERROR_NOT_SUPPORTED", "Operation not supported for the current backend."),
    gio.ERROR_NOT_SYMBOLIC_LINK : exceptions.ErrorDescription(gio.ERROR_NOT_SYMBOLIC_LINK, "ERROR_NOT_SYMBOLIC_LINK", "File is not a symbolic link."),
    gio.ERROR_NO_SPACE : exceptions.ErrorDescription(gio.ERROR_NO_SPACE, "ERROR_NO_SPACE", "No space left on drive."),
    gio.ERROR_PENDING : exceptions.ErrorDescription(gio.ERROR_PENDING, "ERROR_PENDING", "Operations are still pending."),
    gio.ERROR_PERMISSION_DENIED : exceptions.ErrorDescription(gio.ERROR_PERMISSION_DENIED, "ERROR_PERMISSION_DENIED", "Permission denied."),
    gio.ERROR_READ_ONLY : exceptions.ErrorDescription(gio.ERROR_READ_ONLY, "ERROR_READ_ONLY", "File is read only."),
    gio.ERROR_TIMED_OUT : exceptions.ErrorDescription(gio.ERROR_TIMED_OUT, "ERROR_TIMED_OUT", "Operation timed out."),
    gio.ERROR_TOO_MANY_LINKS : exceptions.ErrorDescription(gio.ERROR_TOO_MANY_LINKS, "ERROR_TOO_MANY_LINKS", "File contains too many symbolic links."),
    gio.ERROR_TOO_MANY_OPEN_FILES : exceptions.ErrorDescription(gio.ERROR_TOO_MANY_OPEN_FILES, "ERROR_TOO_MANY_OPEN_FILES", "The current process has too many files open and can't open any more. Duplicate descriptors do count toward this limit. Since 2.20"),
    gio.ERROR_WOULD_BLOCK : exceptions.ErrorDescription(gio.ERROR_WOULD_BLOCK, "ERROR_WOULD_BLOCK", "Operation would block."),
    gio.ERROR_WOULD_MERGE : exceptions.ErrorDescription(gio.ERROR_WOULD_MERGE, "ERROR_WOULD_MERGE", "Operation would merge files."),
    gio.ERROR_WOULD_RECURSE : exceptions.ErrorDescription(gio.ERROR_WOULD_RECURSE, "ERROR_WOULD_RECURSE", "Operation would be recursive."),
    gio.ERROR_WRONG_ETAG : exceptions.ErrorDescription(gio.ERROR_WRONG_ETAG, "ERROR_WRONG_ETAG", "File's Entity Tag was incorrect.")
}


MAX_NUMBER_ASK_PASSWORD = 4


REMOTE_SERVICE_SFTP = 101
REMOTE_SERVICE_FTP = 102
#REMOTE_SERVICE_SECURE_WEBDAV = 103
REMOTE_SERVICE_SSH = 104
REMOTE_SERVICE_NFS = 105


REMOTE_SERVICES_AVAIL = { REMOTE_SERVICE_SFTP : _("SFTP"),
                          REMOTE_SERVICE_SSH : _("SSH"),
                          REMOTE_SERVICE_FTP : _("FTP"),
                          REMOTE_SERVICE_NFS : _("NFS")
#                          REMOTE_SERVICE_SECURE_WEBDAV : _("Secure WebDAV (HTTPS)")
                        }
REMOTE_SERVICE_TO_URI_SCHEME = { REMOTE_SERVICE_FTP : pathparse.URI_SCHEME_FTP,
                                 REMOTE_SERVICE_SFTP : pathparse.URI_SCHEME_SFTP,
                                 REMOTE_SERVICE_SSH : pathparse.URI_SCHEME_SSH,
                                 REMOTE_SERVICE_NFS : pathparse.URI_SCHEME_NFS
#                                 REMOTE_SERVICE_SECURE_WEBDAV : URI_SCHEME_DAVS
                               }
URI_SCHEME_TO_REMOTE_SERVICE = { REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_FTP] : REMOTE_SERVICE_FTP,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_SFTP] : REMOTE_SERVICE_SFTP,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_SSH] : REMOTE_SERVICE_SSH,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_NFS] : REMOTE_SERVICE_NFS
#                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_SECURE_WEBDAV] : REMOTE_SERVICE_SECURE_WEBDAV
                               }



class PathInfo(object):
    def __init__(self, path, eff_path, mounted):
        self.path = path
        self.eff_path = eff_path
        self.mounted = mounted

    def __str__(self):
        _res = [ "Path: `%s`" % self.path,
                 "Eff. path: `%s`" % self.eff_path,
                 "Mounted: %s" % self.mounted
               ]
        _res_str = "\n".join(_res)
        return _res_str


#TODO: implement interface?
class GioMountHandler(object):
    """Handles mounting process for a single URI.
    """

    def __init__(self):
        """
        Constructor
        @param configManager: 
        """
        self.__logger = log.LogFactory.getLogger()

        self.__uri = None
        self.__ask_password_cnt = 0

        self.__path_mount_info = None
        self.__mainloop = None
        self.__mount_finish_callback = None
        self.__umount_finish_callback = None

        self._error = None  # latest error during mount/umount

    def use_own_mainloop(self, use = True):
        if use is True:
            if self.__mainloop is None:
                self.__mainloop = glib.MainLoop()
        else:
            self.__mainloop = None

    def set_callbacks(self, mount, umount):
        self.__logger.debug("set_additional_callbacks - mount: %s - umount: %s" % (str(mount), str(umount)))
        self.__mount_finish_callback = mount
        self.__umount_finish_callback = umount

    def set_uri(self, uri):
        if not isinstance(uri, pathparse.UriParser):
            raise TypeError("Expected URI of type UriParser. Got %s instead." % type(uri))
        self.__uri = uri

    def _get_mount(self, gfileobj):
        _mount = None
        try:
            _mount = gfileobj.find_enclosing_mount(None)
        except gio.Error, error:
            _mount = None
            if error.code == gio.ERROR_NOT_MOUNTED:
                self.__logger.info(_("Unable to get mount: path is not mounted"))
            elif error.code == gio.ERROR_NOT_FOUND:
                self.__logger.info(_("Unable to get mount: path not found when mounting (is probably local)"))
            else:
                self.__logger.info(_("Unable to get mount: %s") % error)
        except glib.GError, error:
            _mount = None
            self.__logger.info(_("Unable to get mount: %s") % error)

        return _mount

    def _is_local(self, gfileobj):
        _uri_scheme = gfileobj.get_uri_scheme()
        if _uri_scheme == "file":
            _res = True
        else:
            _res = False

        if _res is True:
            self.__logger.debug("Given path is local")
        else:
            self.__logger.debug("Given path is not local")

        return _res

    def _ask_password_cb(self, mount_op, message, default_user, default_domain, flags):
        self.__ask_password_cnt += 1
        self.__logger.debug("ask password (no: %s)" % self.__ask_password_cnt)
        if self.__ask_password_cnt < MAX_NUMBER_ASK_PASSWORD:
            if self.__uri is None:
                raise ValueError("No URI set")
            self.__logger.debug("Setting username: %s password: %s" % (self.__uri.username,
                                                                    "*"*len(self.__uri.password)))
            mount_op.set_username(self.__uri.username)
#            mount_op.set_domain() # required for samba
            mount_op.set_password(self.__uri.password)
            mount_op.reply(gio.MOUNT_OPERATION_HANDLED)
        else:
            raise exceptions.RemoteMountFailedError("Max. number of password inputs reached. Aborted.")

    def _set_mount_flag(self, obj, required):
        if self.__uri is None:
            raise ValueError("No URI set")
        path = self.__uri.query_mount_uri()
        self.__path_mount_info = PathInfo(path, obj.get_path(), required)
        self.__logger.debug("Path_mount_info: %s" % str(self.__path_mount_info))

    def _unset_mount_flag(self):
        if self.__uri is None:
            raise ValueError("No URI set")
        if self.__path_mount_info is None:
            self.__logger.warning(_("Unable to un-set mount flag: path is not stored"))
        else:
            self.__path_mount_info = None

    def get_eff_path(self):
        """Returns None in case of not mounted URIs.
        """
        if self.__uri is None:
            raise ValueError("No URI set")
        path = self.__uri.query_mount_uri()
        self.__logger.debug("URI: %s" % path)
        _gfile = gio.File(path)
        _eff_path = _gfile.get_path()
        self.__logger.debug("Effective path: `%s`" % _eff_path)
        return _eff_path

    def mount(self):
#        print "Begin of GioMountHandler.mount"
        if self.__uri is None:
            raise ValueError("No URI set")
        path = self.__uri.query_mount_uri()
        self.__logger.debug("Mount path: %s" % path)
        _gfileobj = gio.File(path)

        _local = self._is_local(_gfileobj)
        if _local:
            self.__logger.debug("Mounting local path is not required - calling additional callback")
#Note: call additional callbacks anyway              
            if self.__mount_finish_callback is not None:
                self.__mount_finish_callback(error = None)
        else:
            self._do_mount(_gfileobj)

#        print "End of GioMountHandler.mount"

    def umount(self, overwrite_require = False):
        if self.__uri is None:
            raise ValueError("No URI set")
        path = self.__uri.query_mount_uri()
        self.__logger.debug("Umount path: %s" % path)
        _gfileobj = gio.File(path)

        _local = self._is_local(_gfileobj)
        if _local:
            self.__logger.debug("Unmounting local path is not required - calling additional callback")
            if self.__umount_finish_callback is not None:
                self.__umount_finish_callback(error = None)
        else:
            try:
                _mounted = self.__path_mount_info.mounted
            except KeyError:
                _mounted = True

            if overwrite_require is True:
                _mounted = True

            if _mounted is True:
                self.__logger.debug("Umount is required")
                self._do_umount(_gfileobj)
            else:
                self.__logger.debug("Umount is not required - calling additional callback")
                if self.__umount_finish_callback is not None:
                    self.__umount_finish_callback(error = None)

#        print "End of GioMountHandler.umount"

    def _do_mount(self, gfileobj):
#        self.__logger.debug("begin of hdl._do_mount")
        op = gio.MountOperation()
        self.__ask_password_cnt = 0
        op.connect('ask-password', self._ask_password_cb)
        try:
#            print "Now calling: mount_enclosing_volume"
            gfileobj.mount_enclosing_volume(op, self._mount_done_cb)
#            print "mount_enclosing_volume was called"
            if self.__mainloop is not None:
#                print "run loop"
                self.__mainloop.run()
        except gio.Error, error:
            self.__logger.error(get_gio_errmsg(error, "Error in `_do_mount`"))
            raise exceptions.RemoteMountFailedError(str(error))
        except glib.GError, error:
            self.__logger.error(str(error))
            raise exceptions.RemoteMountFailedError(str(error))
#        print "End of hdl._do_mount"

    def _do_umount(self, gfileobj):
        _mount = self._get_mount(gfileobj)
        error = None
#        self.__logger.debug("hdl._do_umount - mount obj: %s" % str(_mount))
        if _mount is None:
            self.__logger.debug("No mount found.")

            self._unset_mount_flag()
            self._error = error
            if self.__umount_finish_callback is not None:
                self.__logger.debug("Calling additional callback")
                self.__umount_finish_callback(error)

        else:
            try:
                _mount.unmount(self._umount_done_cb, gio.MOUNT_UNMOUNT_NONE, None, gfileobj)
    #            gobject.timeout_add(15000, self._umount_done_cb, _mount, None, gfileobj)
    # remaining issues:
    # * how to cancel a timeout if mount was successful?
    # * how to return False (quit timer) when calling callback function?
    # * does it work without an already runnning mainloop
                if self.__mainloop is not None:
                    self.__logger.debug("run loop")
                    self.__mainloop.run()
            except gio.Error, error:
                self.__logger.error(get_gio_errmsg(error, "Error in `umount`"))
                raise exceptions.RemoteUmountFailedError(str(error))
            except glib.GError, error:
                self.__logger.error(str(error))
                raise exceptions.RemoteUmountFailedError(str(error))
#        print "End of hdl._do_umount"

    def _mount_done_cb(self, obj, res):
        self.__logger.debug("Begin of hdl._mount_done_cb")
        error = None
        try:
            obj.mount_enclosing_volume_finish(res)
            self._set_mount_flag(obj = obj, required = True)
        except gio.Error, error:
            self._set_mount_flag(obj = obj, required = False)
            if error.code == gio.ERROR_ALREADY_MOUNTED:
                self.__logger.info(_("Path is already mounted."))
                error = None
            else:
                self.__logger.error(get_gio_errmsg(error, "Error in `_do_mount`"))
        except glib.GError, error:
            self._set_mount_flag(obj = obj, required = False)
            self.__logger.error(str(error))
        finally:
            if self.__mainloop is not None:
                self.__logger.debug("quit loop")
                self.__mainloop.quit()

        self._error = error
        if self.__mount_finish_callback is not None:
            self.__logger.debug("Calling additional callback")
            self.__mount_finish_callback(error)
#        print "End of hdl._mount_done_cb"

    def _umount_done_cb(self, obj, res, gfile):
#        self.__logger.debug("umount done")
        error = None
        try:
            obj.unmount_finish(res)
        except gio.Error, error:
            if error.code == gio.ERROR_NOT_MOUNTED:
                self.__logger.info(_("Path is not mounted."))
                error = None
            else:
                self.__logger.error(get_gio_errmsg(error, "Error in `_umount_done_cb`"))
        except glib.GError, error:
            self.__logger.error(str(error))
        finally:
            if self.__mainloop is not None:
                self.__logger.debug("quit loop")
                self.__mainloop.quit()

        if error is None:
            self._unset_mount_flag()

        self._error = error
        if self.__umount_finish_callback is not None:
            self.__logger.debug("Calling additional callback")
            self.__umount_finish_callback(error)

#        print "End of hdl._umount_done_cb"

    def test_path(self):
        if self.__uri is None:
            raise ValueError("No URI set")

        _mpath = self.__uri.query_mount_uri()

        try:
            _gmpath = gio.File(_mpath)
            _effpath = _gmpath.get_path()
        except (gio.Error, glib.GError), error:
            raise exceptions.RemoteMountTestFailedError(str(error))

        dname = "%s-%s-%s.tmp" % ("sbackup-dir", time.time(), uuid.uuid4())
        tfilen = "%s-%s-%s.tmp" % ("sbackup", time.time(), uuid.uuid4())

        _test_path(_mpath, dname, tfilen)
        local_file_utils.test_path(_effpath, dname, tfilen, test_read = False)

    def query_fs_info(self):
        if self.__uri is None:
            raise ValueError("No URI set")
        _mpath = self.__uri.query_mount_uri()

        _size = constants.SIZE_FILESYSTEM_UNKNOWN
        _free = constants.FREE_SPACE_UNKNOWN

        _gfo = gio.File(_mpath)
        try:
            _gfoinfo = _gfo.query_filesystem_info("filesystem::*")
        except gio.Error, error:
            self.__logger.warning(get_gio_errmsg(error, "Error in `query_fs_info`"))
        else:
            _size = _gfoinfo.get_attribute_uint64(gio.FILE_ATTRIBUTE_FILESYSTEM_SIZE)
            _free = _gfoinfo.get_attribute_uint64(gio.FILE_ATTRIBUTE_FILESYSTEM_FREE)
        self.__logger.debug("FS info - size: %s free: %s" % (_size, _free))
        return (_size, _free)


class GioOperations(interfaces.IOperations):
    """Collects simple operations    
    """
    __metaclass__ = structs.Singleton

    def __init__(self):
        interfaces.IOperations.__init__(self)
        self.pathsep = local_file_utils.pathsep

    @classmethod
    def path_exists(cls, path):
        _gfileobj = gio.File(path)
        _res = _gfileobj.query_exists()
        return bool(_res)

    def openfile(self, uri, write = False):
        return local_file_utils.openfile(uri, write)

    def path_writeable(self, path):
        return local_file_utils.path_writeable(path)

    def chmod(self, path, mode):
        local_file_utils.chmod(path, mode)

    def copy(self, src, dst):
#TODO: replace by gio operation
        local_file_utils.copy(src, dst)

    def copyfile(self, src, dest):
        local_file_utils.copyfile(src, dest)

    def copy_no_permissions(self, src, dst):
        local_file_utils.copy_no_permissions(src, dst)

    def createfile(self, filepath):
        local_file_utils.createfile(filepath)

    def delete(self, uri):
        """Deletes given file or directory (recursive).
        """
        local_file_utils.delete(uri)

    def force_delete(self, path):
        local_file_utils.force_delete(path)

    def force_move(self, src, dst):
        local_file_utils.force_move(src, dst)

    def is_link(self, path):
        return local_file_utils.is_link(path)

    def get_link(self, path):
        return local_file_utils.get_link(path)

    def get_link_abs(self, path):
        return local_file_utils.get_link_abs(path)

    def is_dir(self, path):
        return local_file_utils.is_dir(path)

    def rename_errors_ignored(self, src, dst):
        local_file_utils.rename_errors_ignored(src, dst)

    def listdir(self, path) :
        """List a directory. Returns basenames of entries.
        """
        listing = local_file_utils.listdir(path)
        return listing

    def listdir_fullpath(self, path) :
        """List a directory. Returns full paths to entries.
        """
        _res = local_file_utils.listdir_fullpath(path)
        return _res

    def makedir(self, path):
        local_file_utils.makedir(path)

    def makedirs(self, path):
        local_file_utils.makedirs(path)

    @classmethod
    def normpath(cls, *args):
        return local_file_utils.normpath(*args)

    def get_dirname(self, path):
        return local_file_utils.get_dirname(path)

    def get_basename(self, path):
        return local_file_utils.get_basename(path)

    def pickleload(self, path):
        """
        Load a python object from the given pickle file
        @param file: the path of the pickle file
        """
        f = self.openfile(path)
        result = pickle.load(f)
        f.close()
        return result

    def pickledump(self, datas, path):
        local_file_utils.pickledump(datas, path)

    def rename(self, src, dst):
        local_file_utils.rename(src, dst)

    def readfile(self, path):
        return local_file_utils.readfile(path)

    def writetofile(self, path, content):
        local_file_utils.writetofile(path, content)



def get_gio_errmsg(error, title):
    _error_descr = errorcodes[error.code]
    _msg = "%s: %s [%s - %s]" % (title, error, _error_descr.name, _error_descr.message)
    return _msg


def _test_path(path, testdir_name, testfile_name):
    __logger = log.LogFactory().getLogger()
    _mpath = path

    testdir = GioOperations.normpath(_mpath, testdir_name)
    testfile = GioOperations.normpath(testdir, testfile_name)

    try:
        # test specified path
        __logger.info(_("test specified path for existence using GIO"))
        _gmpath = gio.File(_mpath)
        _exists = _gmpath.query_exists()
        if bool(_exists) is False:
            raise exceptions.RemoteMountTestFailedError("Specified remote path does not exists.")

        # test directory
        __logger.debug("Test testdir: %s" % testdir)
        _gtdir = gio.File(testdir)
        _exists = _gtdir.query_exists()
        if bool(_exists) is True:
            raise exceptions.RemoteMountTestFailedError("Unable to create directory for testing purpose: Directory already exists.")

        __logger.info(_("Create testdir"))
        _res = _gtdir.make_directory()
        if bool(_res) is False:
            raise exceptions.RemoteMountTestFailedError("Unable to create directory for testing purpose.")

        __logger.info(_("Test testfile for existence"))
        _gtfile = gio.File(testfile)
        _exists = _gtfile.query_exists()
        if bool(_exists) is True:
            raise exceptions.RemoteMountTestFailedError("Unable to create file for testing purpose: File already exists.")

        _buffer = "Some arbitrary content: %s" % uuid.uuid4()
        __logger.info(_("Create file"))
        _ostr = _gtfile.create()
        __logger.debug("Write buffer: `%s` to file" % _buffer)
        _ostr.write(_buffer)
        _ostr.close()

        # and re-read
        __logger.info(_("Re-read test file"))
        _gtfile = gio.File(testfile)
        _exists = _gtfile.query_exists()
        if bool(_exists) is False:
            raise exceptions.RemoteMountTestFailedError("Unable to open file for testing purpose: File does not exists.")
        _cont = _gtfile.load_contents()
        assert len(_cont) == 3
        __logger.debug(_cont[0])
        if _cont[0] != _buffer:
            raise exceptions.RemoteMountTestFailedError("Unable to read content from test file: content differs.")

        # clean-up
        __logger.info(_("Remove file"))
        _gtfile.delete()
        __logger.info(_("Remove dir"))
        _gtdir.delete()

    except (gio.Error, glib.GError), error:
        raise exceptions.RemoteMountTestFailedError(str(error))


def get_scheme_from_service(service):
    if not isinstance(service, types.IntType):
        raise TypeError
    if service not in REMOTE_SERVICES_AVAIL:
        raise ValueError("Given remote service not supported")
    if service not in REMOTE_SERVICE_TO_URI_SCHEME:
        raise ValueError("Given remote service not supported")

    _scheme = REMOTE_SERVICE_TO_URI_SCHEME[service]
    return _scheme


def get_service_from_scheme(scheme):
    try:
        _service = URI_SCHEME_TO_REMOTE_SERVICE[scheme]
    except KeyError:
        _service = None
    return _service
