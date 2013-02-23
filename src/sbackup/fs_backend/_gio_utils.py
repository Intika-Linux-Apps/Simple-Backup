#   Simple Backup - file access management using GIO/GVFS
#
#   Copyright (c)2010,2013: Jean-Peer Lorenz <peer.loz@gmx.net>
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
:mod:`sbackup.util.gio_utils` -- file access management using GIO/GVFS
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


from sbackup.util import local_file_utils
from sbackup.util import exceptions
from sbackup.util import interfaces
from sbackup.util import constants
from sbackup.util import pathparse
from sbackup.util import structs
from sbackup.util import system
from sbackup.util import log

errorcodes = {
    gio.ERROR_ALREADY_MOUNTED : exceptions.ErrorDescription(gio.ERROR_ALREADY_MOUNTED,
                                                            "ERROR_ALREADY_MOUNTED",
                                                            "File is already mounted."),
    gio.ERROR_BUSY : exceptions.ErrorDescription(gio.ERROR_BUSY, "ERROR_BUSY", "File is busy."),
    gio.ERROR_CANCELLED : exceptions.ErrorDescription(gio.ERROR_CANCELLED, "ERROR_CANCELLED",
                                                      "Operation was cancelled. See gio.Cancellable."),
    gio.ERROR_CANT_CREATE_BACKUP : exceptions.ErrorDescription(gio.ERROR_CANT_CREATE_BACKUP,
                                                               "ERROR_CANT_CREATE_BACKUP",
                                                               "Backup couldn't be created."),
    gio.ERROR_CLOSED : exceptions.ErrorDescription(gio.ERROR_CLOSED, "ERROR_CLOSED", "File was closed."),
    gio.ERROR_EXISTS : exceptions.ErrorDescription(gio.ERROR_EXISTS, "ERROR_EXISTS",
                                                   "File already exists error."),
    gio.ERROR_FAILED : exceptions.ErrorDescription(gio.ERROR_FAILED, "ERROR_FAILED",
                                                   "Generic error condition for when any operation fails."),
    gio.ERROR_FAILED_HANDLED : exceptions.ErrorDescription(gio.ERROR_FAILED_HANDLED, "ERROR_FAILED_HANDLED",
            "Operation failed and a helper program has already interacted with the user. Do not display any error dialog."),
    gio.ERROR_FILENAME_TOO_LONG : exceptions.ErrorDescription(gio.ERROR_FILENAME_TOO_LONG,
                                                              "ERROR_FILENAME_TOO_LONG",
                                                              "Filename is too many characters."),
    gio.ERROR_HOST_NOT_FOUND : exceptions.ErrorDescription(gio.ERROR_HOST_NOT_FOUND, "ERROR_HOST_NOT_FOUND",
                                                           "Host couldn't be found (remote operations)."),
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

MSG_UNKNOWN_ERROR_CODE = _("Unknown error code:")


MAX_NUMBER_ASK_PASSWORD = 4


REMOTE_SERVICE_SFTP = 101
REMOTE_SERVICE_FTP = 102
#REMOTE_SERVICE_SECURE_WEBDAV = 103
REMOTE_SERVICE_SSH = 104
REMOTE_SERVICE_NFS = 105
REMOTE_SERVICE_SMB = 106


REMOTE_SERVICES_AVAIL = { REMOTE_SERVICE_SFTP : _("SFTP"),
                          REMOTE_SERVICE_SSH : _("SSH"),
                          REMOTE_SERVICE_FTP : _("FTP"),
                          REMOTE_SERVICE_NFS : _("NFS"),
                          REMOTE_SERVICE_SMB : _("SMB")
#                          REMOTE_SERVICE_SECURE_WEBDAV : _("Secure WebDAV (HTTPS)")
                        }
REMOTE_SERVICE_TO_URI_SCHEME = { REMOTE_SERVICE_FTP : pathparse.URI_SCHEME_FTP,
                                 REMOTE_SERVICE_SFTP : pathparse.URI_SCHEME_SFTP,
                                 REMOTE_SERVICE_SSH : pathparse.URI_SCHEME_SSH,
                                 REMOTE_SERVICE_NFS : pathparse.URI_SCHEME_NFS,
                                 REMOTE_SERVICE_SMB : pathparse.URI_SCHEME_SMB
#                                 REMOTE_SERVICE_SECURE_WEBDAV : URI_SCHEME_DAVS
                               }
URI_SCHEME_TO_REMOTE_SERVICE = { REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_FTP] : REMOTE_SERVICE_FTP,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_SFTP] : REMOTE_SERVICE_SFTP,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_SSH] : REMOTE_SERVICE_SSH,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_NFS] : REMOTE_SERVICE_NFS,
                                 REMOTE_SERVICE_TO_URI_SCHEME[REMOTE_SERVICE_SMB] : REMOTE_SERVICE_SMB
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
#        self.__logger.debug("set_additional_callbacks - mount: %s - umount: %s" % (str(mount), str(umount)))
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
        """
        :todo: Consolidate with `pathparse.is_local`
        """
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
            # don't set password if none is given (LP #701403)
            if self.__uri.password is not None:
                mount_op.set_password(self.__uri.password)
            mount_op.reply(gio.MOUNT_OPERATION_HANDLED)
        else:
            self._error = exceptions.RemoteMountFailedError("Max. number of password inputs reached. Aborted.")
            mount_op.reply(gio.MOUNT_OPERATION_ABORTED)

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

    def mount(self):
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

    def _do_mount(self, gfileobj):
        op = gio.MountOperation()
        self.__ask_password_cnt = 0
        op.connect('ask-password', self._ask_password_cb)
        try:
            gfileobj.mount_enclosing_volume(op, self._mount_done_cb)
            if self.__mainloop is not None:
                self.__mainloop.run()
        except gio.Error, error:
            self.__logger.error(get_gio_errmsg(error, "Error in `_do_mount`"))
            raise exceptions.RemoteMountFailedError(str(error))
        except glib.GError, error:
            self.__logger.error(str(error))
            raise exceptions.RemoteMountFailedError(str(error))

    def _do_umount(self, gfileobj):
        _mount = self._get_mount(gfileobj)
        error = None
        if _mount is None:
            self.__logger.debug("No mount found.")

            self._unset_mount_flag()
            self._error = error
            if self.__umount_finish_callback is not None:
                self.__logger.debug("Calling additional callback")
                self.__umount_finish_callback(error)

        else:
            try:
                _mount.unmount(self._umount_done_cb, gio.MOUNT_UNMOUNT_FORCE, None, gfileobj)
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

    def _mount_done_cb(self, obj, res):
        error = None
        try:
            obj.mount_enclosing_volume_finish(res)
            self._set_mount_flag(obj = obj, required = True)
        except gio.Error, error:
            self._set_mount_flag(obj = obj, required = False)
            if error.code == gio.ERROR_ALREADY_MOUNTED:
                self.__logger.info(_("Path is already mounted."))
                error = None
            elif error.code == gio.ERROR_FAILED_HANDLED:
                self.__logger.error(get_gio_errmsg(error, "Mount failed"))
                if self._error is not None:
                    self.__logger.error(str(self._error))
                    error = self._error
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

    def _umount_done_cb(self, obj, res, gfile):
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

    pathsep = system.PATHSEP

    def __init__(self):
        interfaces.IOperations.__init__(self)

    @classmethod
    def path_exists(cls, path):
        # `gfile.query_exists()' is not used since it returns True even
        # if path is not accessible!
        #XXX: rename into 'is_readable'?
        _gfileobj = gio.File(path)
        try:
            _ginfo = _gfileobj.query_info(attributes = gio.FILE_ATTRIBUTE_ACCESS_CAN_READ)
            _can_read = _ginfo.get_attribute_boolean(gio.FILE_ATTRIBUTE_ACCESS_CAN_READ)
        except gio.Error, error:
            _can_read = False
            if error.code == gio.ERROR_NOT_FOUND:
                pass
            else:
                _logger = log.LogFactory.getLogger()
                _logger.debug(get_gio_errmsg(error, "Unable to get attribute for path"))
        return _can_read

    @classmethod
    def openfile_for_write(cls, path):
        _gfileobj = gio.File(path)
#FIXME: etag should be set to None though it doesn't work then!
        _ostr = _gfileobj.replace(etag = '', make_backup = False)
        return _ostr

    @classmethod
    def openfile_for_read(cls, path):
        _gfile = gio.File(path)
        _istr = _gfile.read()
        return _istr

    @classmethod
    def openfile_for_append(cls, path):
        _gfileobj = gio.File(path)
        _ostr = _gfileobj.append_to()
        return _ostr

    @classmethod
    def copyfile(cls, src, dest):
        """Copies given file and metadata (similar to `shutil.copy2`).
        Overwrites `dest` if it already exists
        """
        _src = gio.File(src)
        _dest = gio.File(dest)

        # the source must be a file and exist
        if not cls.path_exists(src):
            raise IOError("Given copy source `%s` does not exist" % _src.get_parse_name())
        if cls.__isfile(_src):
            _src, _dest = cls._prepare_copy(_src, _dest)
            _src.copy(_dest, flags = gio.FILE_COPY_OVERWRITE)
            try:
                _src.copy_attributes(_dest, flags = gio.FILE_COPY_ALL_METADATA)
            except gio.Error:
                raise exceptions.CopyFileAttributesError(\
                            "Unable to copy file attributes (permissions etc.) of file `%s`."\
                            % _src.get_parse_name())
        else:
            _logger = log.LogFactory.getLogger()
            _logger.warning("Given copy source `%s` is not a file. Skipped." % _src.get_parse_name())

    @classmethod
    def _prepare_copy(cls, src_gfile, dst_gfile):
        """Helper function that prepares the given paths for copying
        using 'nssb_copy'.
        
        Source must be a file or symbolic link to a file!
        
        @todo: Implement test case for symbolic links!
        """
        _src_uri = src_gfile.get_uri()
        _dst_uri = dst_gfile.get_uri()

        _src_file = cls.__basename(src_gfile)

        if cls.__isdir(dst_gfile):
            _dstu = cls.joinpath(_dst_uri, _src_file)
            _dst = gio.File(_dstu)
        elif _dst_uri.endswith(cls.pathsep):
            _dstu = cls.joinpath(_dst_uri, _src_file)
            _dst = gio.File(_dstu)
        else:
            _dst = dst_gfile

        _dstdir = cls.get_dirname(_dst.get_uri())
        if cls.path_exists(_dstdir) is False:
            raise IOError("Given copy destination '%s' does not exist" % _dstdir)

        retval = (src_gfile, _dst)

        return retval

    @classmethod
    def _copy_metadata(cls, src, dest):
        _src = gio.File(src)
        _dest = gio.File(dest)
        _src.copy_attributes(_dest, flags = gio.FILE_COPY_ALL_METADATA)

    @classmethod
    def delete(cls, uri):
        """Deletes given file or directory (recursive).
        """
        if (cls.is_dir(uri) is True) and (cls.is_link(uri) is False):
            cls._rmtree_recurse(uri)
        else:
            cls._rm_file(uri)

    @classmethod
    def _rm_file(cls, path):
        # setting of permissions only in case of failures does not work:
        # if directory is read-only we cannot remove files inside even if these are
        # read/write
        try:
            _gfile = gio.File(path)
            _gfile.delete()
        except gio.Error, error:
            raise IOError(str(error))

    @classmethod
    def _rmtree_recurse(cls, path):
        _listing = cls.listdir_fullpath(path)
        for _ent in _listing:
            if (cls.is_dir(_ent) is True) and (cls.is_link(_ent) is False):
                cls._rmtree_recurse(_ent)
            else:
                cls._rm_file(_ent)
        cls._rm_file(path)

    @classmethod
    def _add_write_permission(cls, path, recursive = True):
        """Sets write permissions for user, group, and others for
        given directory or file (recursive). 
        """
        _gfileobj = gio.File(path)
        try:
            _ginfo = _gfileobj.query_info(attributes = gio.FILE_ATTRIBUTE_UNIX_MODE)
            _fmode = _ginfo.get_attribute_uint32(gio.FILE_ATTRIBUTE_UNIX_MODE)
            _new_mode = _fmode | system.UNIX_PERM_ALL_WRITE
            _ginfo.set_attribute_uint32(gio.FILE_ATTRIBUTE_UNIX_MODE, _new_mode)
            _gfileobj.set_attributes_from_info(_ginfo) # setting attributes directly seems broken
        except gio.Error, error:
            _msg = get_gio_errmsg(error, "Unable to set permissions")
            _logger = log.LogFactory.getLogger()
            _logger.warning(_msg)
            return

        if cls.is_dir(path) and recursive is True:
            for _entryp in cls.listdir_fullpath(path):
                if (cls.is_dir(_entryp) is True)  and (cls.is_link(_entryp) is False):
                    cls._add_write_permission(_entryp)
                else:
                    cls._add_write_permission(_entryp, recursive = False)

    @classmethod
    def chmod_no_rwx_grp_oth(cls, path):
        """Sets write permissions for user only for
        given directory or file (*not* recursive). 
        """
        _gfileobj = gio.File(path)
        try:
            _ginfo = _gfileobj.query_info(attributes = gio.FILE_ATTRIBUTE_UNIX_MODE)
            _fmode = _ginfo.get_attribute_uint32(gio.FILE_ATTRIBUTE_UNIX_MODE)
            _new_mode = _fmode & system.UNIX_PERM_GRPOTH_NORWX
            _ginfo.set_attribute_uint32(gio.FILE_ATTRIBUTE_UNIX_MODE, _new_mode)
            _gfileobj.set_attributes_from_info(_ginfo) # setting attributes directly seems broken
        except gio.Error, error:
            _msg = get_gio_errmsg(error, "Unable to set permissions")
            _logger = log.LogFactory.getLogger()
            _logger.warning(_msg)
            return

    @classmethod
    def force_delete(cls, path):
        cls._add_write_permission(path, recursive = True)
        cls.delete(path)

    @classmethod
    def force_move(cls, src, dst):
        _gsrc = gio.File(src)
        _gdst = gio.File(dst)
        try:
            _gsrc.move(_gdst, flags = gio.FILE_COPY_OVERWRITE)
        except gio.Error:
            if cls.is_dir(src):
                cls._copytree(src, dst)
                cls.force_delete(src)
            else:
                cls.copyfile(src, dst)
                cls.force_delete(src)

    @classmethod
    def _copytree(cls, src, dst):
        """mod of `shutil.copytree`. This doesn't fail if the
        directory exists, it copies inside.
    
        :param src: source path for copy operation
        :param dst: destination
        :param symlinks: copy symlinks?
        :type src: string
        :type dst: string
    
        """
        names = cls.listdir(src)
        if not cls.path_exists(dst):
            cls.makedirs(dst)
#        errors = []
        for name in names:
            srcname = cls.joinpath(src, name)
            dstname = cls.joinpath(dst, name)
#            try:
            if cls.is_dir(srcname) and not cls.is_link(srcname):
                cls._copytree(srcname, dstname)
            else:
                cls.copyfile(srcname, dstname)
#            except gio.Error, why:
#                errors.append((srcname, dstname, str(why)))
#            # catch the Error from the recursive copytree so that we can
#            # continue with other files
#            except shutil.Error, err:
#                errors.extend(err.args[0])
#        try:
#            shutil.copystat(src, dst)
#        except OSError, why:
#            errors.extend((src, dst, str(why)))
#        if len(errors) > 0:
#            raise shutil.Error, errors
        cls._copy_metadata(src, dst)


    @classmethod
    def is_link(cls, path):
        _res = False
        _gfileobj = gio.File(path)
#        _ftype = _gfileobj.query_file_type() #flags = gio.FILE_QUERY_INFO_NONE, cancellable = None)
        _ftype = cls._query_file_type(_gfileobj)
        if _ftype == gio.FILE_TYPE_SYMBOLIC_LINK:
            _res = True
        return _res

    @classmethod
    def __isdir(cls, gfile):
        """Private helper method that takes `gio.File` rather pathname.
        """
        _res = False
        _ftype = cls._query_file_type(gfile)
        if _ftype == gio.FILE_TYPE_DIRECTORY:
            _res = True
        return _res

    @classmethod
    def __isfile(cls, gfile):
        """Private helper method that takes `gio.File` rather pathname.
        """
        _res = False
        _ftype = cls._query_file_type(gfile)
        if _ftype == gio.FILE_TYPE_REGULAR:
            _res = True
        return _res

    @classmethod
    def _query_file_type(cls, gfile):
        try:
            _info = gfile.query_info(attributes = "standard::type", flags = gio.FILE_QUERY_INFO_NONE,
                                       cancellable = None)
            _ftype = _info.get_file_type()
        except gio.Error, error:
            if error.code == gio.ERROR_NOT_FOUND:
                _ftype = None
            else:
                raise
        return _ftype

    @classmethod
    def test_dir_access(cls, path):
        _gfileobj = gio.File(path)
        try:
            _gfileobj.enumerate_children('standard::name')
        except gio.Error, error:
            raise exceptions.FileAccessException(get_gio_errmsg(error,
                                        "Unable to list directory content"))

    @classmethod
    def is_dir(cls, path):
        _gfileobj = gio.File(path)
        _res = cls.__isdir(_gfileobj)
        return _res

    @classmethod
    def listdir(cls, path) :
        """List a directory. Returns basenames of entries.
        """
        listing = []
        _gfileobj = gio.File(path)
        try:
            _infos = _gfileobj.enumerate_children('standard::name')
        except gio.Error, error:
            if error.code == gio.ERROR_NOT_DIRECTORY:
                _msg = get_gio_errmsg(error, "Unable to list directory content")
                _logger = log.LogFactory.getLogger()
                _logger.warning(_msg)
                _ftype = cls._query_file_type(_gfileobj)
                if _ftype == gio.FILE_TYPE_DIRECTORY:
                    _msg = "Directory"
                elif _ftype == gio.FILE_TYPE_MOUNTABLE:
                    _msg = "Mountable"
                elif _ftype == gio.FILE_TYPE_REGULAR:
                    _msg = "Regular file"
                elif _ftype == gio.FILE_TYPE_SHORTCUT:
                    _msg = "Shortcut"
                elif _ftype == gio.FILE_TYPE_SPECIAL:
                    _msg = "Special file"
                elif _ftype == gio.FILE_TYPE_SYMBOLIC_LINK:
                    _msg = "Symbolic link"
                elif _ftype == gio.FILE_TYPE_UNKNOWN:
                    _msg = "unknown"
                else:
                    _msg = "unknown (no match)"
                _logger.warning("Filetype of `listdir` parameter is: %s" % _msg)
            else:
                raise
        else:
            for _info in _infos:
                listing.append(_info.get_name())
        return listing

    @classmethod
    def listdir_fullpath(cls, path) :
        """List a directory. Returns full paths to entries.
        """
        _lst = cls.listdir(path)
        _res = []
        for _ent in _lst:
            _res.append(cls.joinpath(path, _ent))
        return _res

    @classmethod
    def makedir(cls, path):
        _gfileobj = gio.File(path)
        _gfileobj.make_directory()

    @classmethod
    def makedirs(cls, path):
        _gfileobj = gio.File(path)
        _gfileobj.make_directory_with_parents(gio.Cancellable())

    @classmethod
    def normpath(cls, *args):
        """
        :todo: Implement GIO method!
        """
        return local_file_utils.normpath(*args)

    @classmethod
    def joinpath(cls, *args):
        return pathparse.joinpath(*args)

    @classmethod
    def get_eff_path(cls, path):
        _logger = log.LogFactory.getLogger()
        _logger.debug("get effective path for URI: `%s`" % path)
        _gfile = gio.File(path)
        _eff_path = _gfile.get_path()
        _logger.debug("Effective path: `%s`" % _eff_path)
        return _eff_path

    @classmethod
    def get_dirname(cls, path):
#        _gfileobj = gio.File(path)
#        return _gfileobj.get_parent()
        return local_file_utils.get_dirname(path)

    @classmethod
    def __basename(cls, gfile):
        return gfile.get_basename()

    @classmethod
    def get_basename(cls, path):
        _gfileobj = gio.File(path)
        return _gfileobj.get_basename()

    @classmethod
    def pickleload(cls, path):
        """
        Load a python object from the given pickle file
        @param file: the path of the pickle file
        """
        _str = cls.openfile_for_read(path)
        _pobj = pickle.load(_str)
        _str.close()
        return _pobj

    @classmethod
    def pickledump(cls, datas, path):
        _ostr = cls.openfile_for_write(path)
        pickle.dump(datas , _ostr)
        _ostr.close()

    @classmethod
    def rename(cls, src, dst):
        _gfileobj = gio.File(src)
        _info = _gfileobj.query_info('standard::name')
        _dst = cls.get_basename(dst)
        _gfileobj.set_display_name(_dst)

    @classmethod
    def readfile(self, path):
        """Returns content of file en bloc.
        :return: string
        """
        _gfileobj = gio.File(path)
        _cont_t = _gfileobj.load_contents()   # returns (content, length, etag)
        _cont = _cont_t[0]
        return _cont

    @classmethod
    def writetofile(cls, path, content):
        _ostr = cls.openfile_for_write(path)
        _ostr.write(content)
        _ostr.close()

    @classmethod
    def close_stream(cls, file_desc):
        try:
            file_desc.close()
        except gio.Error, error:
            if error.code == gio.ERROR_CLOSED:
                raise exceptions.FileAlreadyClosedException(_("Error while closing stream: %s") % error)
            else:
                raise exceptions.FileAccessException(get_gio_errmsg(error, _("Error while closing stream")))

def get_gio_errmsg(error, title):
    _msg = "%s: %s" % (title, error)
    try:
        _error_descr = errorcodes[error.code]
        _msg = "%s [%s - %s]" % (_msg, _error_descr.name, _error_descr.message)
    except KeyError:
        _msg = "%s [%s %s]" % (_msg, MSG_UNKNOWN_ERROR_CODE, error.code)
    return _msg


def _test_path(path, testdir_name, testfile_name):
    __logger = log.LogFactory().getLogger()
    _mpath = path

    testdir = GioOperations.joinpath(_mpath, testdir_name)
    testfile = GioOperations.joinpath(testdir, testfile_name)

    __logger.info("Perform tests at specified location")
    try:
        # test specified path
        __logger.debug(_("test specified path for existence using GIO"))
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

        __logger.debug(_("Create testdir"))
        _res = _gtdir.make_directory()
        if bool(_res) is False:
            raise exceptions.RemoteMountTestFailedError("Unable to create directory for testing purpose.")

        __logger.debug(_("Test testfile for existence"))
        _gtfile = gio.File(testfile)
        _exists = _gtfile.query_exists()
        if bool(_exists) is True:
            raise exceptions.RemoteMountTestFailedError("Unable to create file for testing purpose: File already exists.")

        _buffer = "Some arbitrary content: %s" % uuid.uuid4()
        __logger.debug(_("Create file"))
        _ostr = _gtfile.create()
        __logger.debug("Write buffer: `%s` to file" % _buffer)
        _ostr.write(_buffer)
        _ostr.close()

        # and re-read
        __logger.debug(_("Re-read test file"))
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
        __logger.debug(_("Remove file"))
        _gtfile.delete()
        __logger.debug(_("Remove dir"))
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
