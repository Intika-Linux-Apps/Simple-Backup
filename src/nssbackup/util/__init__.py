#    NSsbackup - Miscellaneous utilities
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
:mod:`nssbackup.util` -- Miscellaneous utilities
================================================

.. module:: util
   :synopsis: Provide functions for disk operations.
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""

#TODO: Clean up this module!

from gettext import gettext as _
import os
import subprocess
import tempfile
import inspect
import shutil
import types
import re
import signal

import nssbackup
from nssbackup.util import local_file_utils
from nssbackup.util import exceptions
from nssbackup.util import constants
from nssbackup.util import structs
from nssbackup.util import log


def __get_resource(resource_name, is_file = False):
    """Looks for certain resources installed by nssbackup.
    The installation script writes into the 'resources' file where
    the files/resources are being stored.
    This function will look for them and return the appropriate path.
    
    @param resourceName: the ressource name, as complete as possible
    @param isFile: flag whether the resource looked up is a file
    
    @note: The resources file is required to be located in the
            root directory of the nssbackup package. 
    """
#    print "Debug: Looking for '%s' (isFile=%s)" % (resourceName, isFile)
    tmp = inspect.getabsfile(nssbackup)
    resfile = file(os.path.join(os.path.dirname(tmp), constants.RSRC_FILE), "r")
    resfilelines = resfile.readlines()
    resfile.close()

    for _dir in resfilelines:
        _dir = _dir.strip()
#        print "Debug: Searching in directory '%s'" % _dir
        if os.path.exists(_dir) and os.path.isdir(_dir):
            # only directories stored in resource file are considered 
            if _dir.endswith(resource_name):
                if not is_file:
#                    print "Debug: Directory found in '%s'" % _dir
                    return _dir

            _flist = os.listdir(_dir)
#            print "Debug: directory listing is :" + str(_flist)
            for _item in _flist:
                _path = os.path.join(_dir, resource_name)
                if os.path.exists(_path) and _path.endswith(resource_name):
                    if os.path.isdir(_path):
                        if not is_file:
#                            print "Debug: Directory found in '%s'" % _path
                            return _path
                    else:
                        if is_file:
#                            print "Debug: File found in '%s'" % _path
                            return _path

    raise exceptions.SBException(\
                "'%s' hasn't been found in the ressource list" % resource_name)


def get_resource_file(resource_name):
    return __get_resource(resource_name, is_file = True)


def get_resource_dir(resource_name):
    return __get_resource(resource_name, is_file = False)


def get_locale_dir():
    return get_resource_dir(constants.LOCALE_DIR)


def get_locale_domain():
    return constants.LOCALE_DOMAIN


def get_version_number():
    """Returns the version number that is stored in according 'metainfo' file.
    
    @todo: Implement similar naming as CPython does (version, version_info).
    """
    ver_line = "VERSION=n.a."

    tmp = inspect.getabsfile(nssbackup)
    resfile = file(os.sep.join([os.path.dirname(tmp), "metainfo"]), "r")
    resfilelines = resfile.readlines()
    resfile.close()

    for _line in resfilelines:
        _line = _line.strip()
        if _line.startswith("VERSION="):
            ver_line = _line

    versfull_t = ver_line.split("=")
    versfull = versfull_t[1]

    version_t = versfull.split("~")
    vers = version_t[0]
    # version-postfix is currently ignored
    return vers


def launch(cmd, opts, env = None):
    """
    launch a command and gets stdout and stderr
    outStr = a String containing the output from stdout" 
    errStr = a String containing the error from stderr
    retVal = the return code (= 0 means that everything were fine )
    @param cmd: The command to launch
    @return: (outStr, errStr, retVal)
    
    @todo: Implement a Singleton TAR launcher!
    """
    _logger = log.LogFactory.getLogger()

    # Create output log file
    outptr, outFile = tempfile.mkstemp(prefix = "output_")

    # Create error log file
    errptr, errFile = tempfile.mkstemp(prefix = "error_")

    # Call the subprocess using convenience method
    opts.insert(0, cmd)
    _logger.debug("Lauching : " + str(opts))

    retval = subprocess.call(opts, stdin = None, stdout = outptr,
                             stderr = errptr, env = env)

    # Close log handles
    os.close(errptr)
    os.close(outptr)

    outStr = local_file_utils.readfile(outFile)
    errStr = local_file_utils.readfile(errFile)

    local_file_utils.delete(outFile)
    local_file_utils.delete(errFile)

    return (outStr, errStr, retval)


def readlineNULSep(fd, fd1):
    """
    Iterator that read a NUL separeted file as lines 
    @param fd: File descriptor
    @return: the gotten line
    @rtype: String
    """
    _continue = 0

    while _continue < 2 :
        c = fd.read(1)
        currentline = ''

        while c :
            if c == '\0'  :
                # we got a line
                break
            currentline += c
            c = fd.read(1)
        else :
            # c is None
            # This else correspond to the while statement
            _continue += 1

        c1 = fd1.read(1)
        currentline1 = ''

        while c1 :
            if c1 == '\0'  :
                # we got a line
                break
            c1 = fd1.read(1)
            currentline1 += c1
        else :
            # c1 is None
            # This else correspond to the while statement
            _continue += 1

        if _continue == 1 :
            raise exceptions.SBException(\
                                "The length of flist and Fprops are not equals")
        yield (currentline, currentline1)


def is_valid_regexp(aregex):
    """Checks if the given string is a valid regular expression.
    @type aregex: String
    
    @todo: Is an empty expression valid or not? Can we combine both checks?
    """
    if not isinstance(aregex, types.StringTypes):
        raise TypeError("is_valid_regexp: Given parameter must be a string. "\
                        "Got %s instead." % (type(aregex)))
    _res = True
    try:
        dummy = re.compile(aregex)
    except re.error:
        _res = False
    return _res


def is_empty_regexp(aregex):
    """Checks if the given parameter is empty, i.e. is None or a string
    containing only whitespaces.
    
    @type aregex: String 
    """
    if not isinstance(aregex, (types.StringTypes, types.NoneType)):
        raise TypeError("is_empty_regexp: Given parameter must be a string "\
                        "or None. Got %s instead." % (type(aregex)))
    _res = False
    if aregex is None:
        _res = True
    else:
        _stripped_aregex = aregex.strip()
        if _stripped_aregex == "":
            _res = True
    return _res


def add_conf_entry(confline, entry, separator = ","):
    """Appends the given entry to the given configuration line. Entries in
    configurations are separated by specified token.
    
    @param confline:  the string the entry is appended to
    @param entry:      the string that is added
    @param separator: the token that separates the entries
    
    @type confline:      String
    @type entry:      String
    @type separator:  String
    
    @return: the configuration line with the added entry
    @rtype:  String
    
    @raise TypeError: If one of the given parameters is not of string type
    
    @todo: Review behaviour if the entry contains characters equal to the \
            separator.
    """
    __conf_entry_func_type_check(confline, entry, separator)
    _strip_confline = confline.strip(separator)
    if not has_conf_entry(confline, entry, separator):
        _strip_entry = entry
        _line = r"%s%s%s" % (_strip_confline, separator, _strip_entry)
        _line = _line.strip(separator)
    else:
        _line = _strip_confline
    return _line


def remove_conf_entry(confline, entry, separator = ","):
    """Removes the given entry from the given string. Entries in configurations
    are separated by the specified token. Leading and trailing separators are
    taken into account.
    
    @param confline:  the string from which the entry should be removed
    @param entry:      the string that is removed
    @param separator: the token that separates the entries
    
    @type confline:      String
    @type entry:      String
    @type separator:  String
    
    @return: the configuration line without the removed entry
    @rtype:  String
    
    @raise TypeError: If one of the given parameters is not of string type
    """
    __conf_entry_func_type_check(confline, entry, separator)
    _line = r"%s%s%s" % (separator, confline, separator)
    _mentry = r"%s%s%s" % (separator, re.escape(entry), separator)
    _line = re.sub(_mentry , separator, _line)
    _line = _line.strip(separator)
    return _line


def has_conf_entry(confline, entry, separator = ","):
    """Checks whether the given `confline` contains the given
    entry.
    """
    __conf_entry_func_type_check(confline, entry, separator)
    has_entry = False
    conf_t = confline.split(separator)
    for conf_e in conf_t:
        if conf_e == entry:
            has_entry = True
            break
    return has_entry


def __conf_entry_func_type_check(confline, entry, separator):
    """Private helper function that does common type checking
    in the `conf_entry_*` functions.
    """
    if not isinstance(confline, types.StringTypes):
        raise TypeError("Given parameter must be a string. "\
                        "Got %s instead." % (type(confline)))
    if not isinstance(entry, types.StringTypes):
        raise TypeError("Given parameter must be a string. "\
                        "Got %s instead." % (type(entry)))
    if not isinstance(separator, types.StringTypes):
        raise TypeError("Given parameter must be a string. "\
                        "Got %s instead." % (type(separator)))
    return None


def _remove_dups(sequence):
    """Removes duplicate entries from the given list.
    This is not the most efficient implementation, however it
    provides safe behavior.
    """
    if not isinstance(sequence, types.ListType):
        raise TypeError("Expected parameter of type 'list'. Got '%s' instead."\
                        % type(sequence))

    _dest = []
    for val in sequence:
        if val not in _dest:
            _dest.append(val)
    return _dest


def _list_union_no_dups_safe(source_a, source_b):
    """Merges the given lists into a single list not containing any
    duplicate entries using the default way.
    """
    if not isinstance(source_a, types.ListType):
        raise TypeError("Expected parameter of type 'list'. Got '%s' instead."\
                        % type(source_a))
    if not isinstance(source_b, types.ListType):
        raise TypeError("Expected parameter of type 'list'. Got '%s' instead."\
                        % type(source_b))

    _dest = _remove_dups(source_b)
    for val_a in source_a:
        if val_a not in _dest:
            _dest.append(val_a)
    return _dest


def list_union(source_a, source_b):
    """Merges the given lists into a single list not containing any
    duplicate entries in a very efficient way.
    """
    # this functions uses sets in order to merge the lists
    # doing so it is really fast compared to list operations
    # however, this only works if the lists do not contain
    # unhashable entries (such as other lists etc.)
    # in this case the default algorithm is used
    if not isinstance(source_a, types.ListType):
        raise TypeError("Expected parameter of type 'list'. Got '%s' instead."\
                        % type(source_a))
    if not isinstance(source_b, types.ListType):
        raise TypeError("Expected parameter of type 'list'. Got '%s' instead."\
                        % type(source_b))

    _logger = log.LogFactory.getLogger()
    fallback = False
    try:
        _set_a = set(source_a)
        _set_b = set(source_b)
    except TypeError:
        _logger.info("Lists contain unhashable types. Falling back on default.")
        fallback = True

    if fallback:
        _dest = _list_union_no_dups_safe(source_a, source_b)
    else:
        _set_dest = _set_a.union(_set_b)
        _dest = list(_set_dest)

    return _dest


def get_humanreadable_size(size_in_bytes, binary_prefixes = False):
    """Converts given number into more readable values.
     
    @todo: Implement sophisicated class for this!
    @note: Have also a look at function `get_humanreadable_size_str`.
    """
    if isinstance(size_in_bytes, types.StringTypes):
        size_in_bytes = long(size_in_bytes)

    factor = 1000
    if binary_prefixes is True:
        factor = 1024

    _mbytes = size_in_bytes / (factor * factor)
    _kbytes = (size_in_bytes % (factor * factor)) / factor
    _bytes = (size_in_bytes % (factor * factor)) % factor

    return (_mbytes, _kbytes, _bytes)


def get_humanreadable_size_str(size_in_bytes, binary_prefixes = False):
    """Converts given number into readable string.
     
    @todo: Implement sophisicated class for this!
    """
    _mb, _kb, _byt = get_humanreadable_size(size_in_bytes = size_in_bytes, binary_prefixes = binary_prefixes)
    if binary_prefixes is True:
        if _byt == 0:
            _res = _("%(mb)d MiB %(kb)d KiB") % {'mb' : _mb,
                                                 'kb' : _kb}
        else:
            _res = _("%(mb)d MiB %(kb)d KiB %(bytes)d") % {'mb' : _mb,
                                                           'kb' : _kb,
                                                           'bytes' : _byt}
    else:
        if _byt == 0:
            _res = _("%(mb)d MB %(kb)d kB") % {'mb' : _mb,
                                               'kb' : _kb}
        else:
            _res = _("%(mb)d MB %(kb)d kB %(bytes)d") % {'mb' : _mb,
                                                         'kb' : _kb,
                                                         'bytes' : _byt}
    return _res


def enable_timeout_alarm():
    """Helper method that enables timeout alarm handling.
    
    @todo: separate class? should we store the previous signal handler and restore it later? 
    """
    # Set the signal handler
    signal.signal(signal.SIGALRM, sigalarm_handler)


def set_timeout_alarm(timeout):
    """Sets the timeout to the given value.
    """
    signal.alarm(timeout)


def sigalarm_handler(signum, stack_frame): #IGNORE:W0613
    """Signal handler that is connected to the SIGALRM signal.
    
    @raise TimeoutError: A `TimeoutError` exception is raised.
    """
    raise exceptions.TimeoutError("Unable to open device.")


def enable_termsignal():
    signal.signal(signal.SIGTERM, sigterm_handler)


def sigterm_handler(signum, stack_frame): #IGNORE:W0613
    raise exceptions.SigTerminatedError("Application was terminated by signal %s." % signum)


def enable_backup_cancel_signal():
    signal.signal(constants.BACKUP_CANCEL_SIG, sigcancel_handler)


def sigcancel_handler(signum, stack_frame): #IGNORE:W0613
    """
    see `man 7 signal`
    """
    raise exceptions.BackupCanceledError
