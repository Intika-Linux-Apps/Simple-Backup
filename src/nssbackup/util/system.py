#    Simple Backup - Operation System related utilities
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


import os
import pwd
import grp
import subprocess
import types

from nssbackup.util import readline_nullsep


CLEAN_ENVIRONMENT = {
    "SHELL" : "",
    "MANDATORY_PATH" : "",
    "MANPATH" : "",
    "PYTHONPATH" : "",
    "DBUS_SESSION_BUS_ADDRESS" : "",
    "DEFAULTS_PATH" : "",
    "DESKTOP_SESSION" : "",
    "GTK_MODULES" : "",
    "LESSOPEN" : "",
    "USER" : "",
    "XAUTHORITY" : "",
    "SESSION_MANAGER" : "",
    "SHLVL" : "",
    "DISPLAY" : "",
    "WINDOWID" : "",
    "GPG_AGENT_INFO" : "",
    "GDM_KEYBOARD_LAYOUT" : "",
    "GDMSESSION" : "",
    "_" : "",
    "XDG_CONFIG_DIRS" : "",
    "XDG_DATA_DIRS" : "",
    "COLORTERM" : "",
    "HOME" : "",
    "LD_LIBRARY_PATH" : "",
    "LANG" : "",
    "USERNAME" : "",
    "LESSCLOSE" : "",
    "GNOME_KEYRING_PID" : "",
    "LOGNAME" : "",
    "PATH" : "",
    "GNOME_KEYRING_CONTROL" : "",
    "HISTCONTROL" : "",
    "TERM" : "",
    "XDG_SESSION_COOKIE" : "",
    "SSH_AUTH_SOCK" : "",
    "LC_ALL" : "",
    "OLDPWD" : "",
    "GDM_LANG" : "",
    "SPEECHD_PORT" : "",
    "PWD" : ""
    }


def get_user_from_env():
    """Returns the USER defined in current environment. If no USER is
    set, None is returned.
    """
    _user = os.environ.get("USER", None)
    return _user


def get_user_from_uid():
    _user = pwd.getpwuid(os.getuid()).pw_name
    return _user


def is_superuser():
    _res = False
    if os.geteuid() == 0:
        _res = True
    return _res


def switch_user(uid_name):
    """
    """
    starting_uid = os.getuid()
    starting_gid = os.getgid()
    starting_uid_name = pwd.getpwuid(starting_uid)[0]

    print 'switch_user: started as %s/%s' % \
    (pwd.getpwuid(starting_uid).pw_name,
    grp.getgrgid(starting_gid).gr_name)
#    print "UID: %s  EUID: %s  GID: %s" % (os.getuid(), os.geteuid(), os.getgid())

    if os.getuid() != 0:
        # We're not root so, like, whatever dude
        print "switch_user: already running as '%s'" % starting_uid_name
        return

    # If we started as root, drop privs and become the specified user/group
    if starting_uid == 0:
        # Get the uid/gid from the name
        running_uid = pwd.getpwnam(uid_name).pw_uid
        running_gid = pwd.getpwnam(uid_name).pw_gid

    # Try setting the new uid/gid
    try:
        os.setgid(running_gid)
    except OSError, e:
        print 'Could not set effective group id: %s' % e

    try:
        os.setgroups([running_gid])
    except OSError, e:
        print 'Could not set associated groups: %s' % e

    try:
        os.setuid(running_uid)
    except OSError, e:
        print 'Could not set effective user id: %s' % e

    # Ensure a very convervative umask
    new_umask = 077
    old_umask = os.umask(new_umask)
    print 'drop_privileges: Old umask: %s, new umask: %s' % \
    (oct(old_umask), oct(new_umask))

    final_uid = os.getuid()
    final_gid = os.getgid()
    print 'drop_privileges: running as %s/%s' % \
    (pwd.getpwuid(final_uid).pw_name,
    grp.getgrgid(final_gid).gr_name)


def drop_privileges():
    switch_user(uid_name = 'nobody')


def get_environment():
    _env = os.environ
    return _env


def get_process_environment(pid):
    _envlst = None
    _envfile = "/proc/%s/environ" % pid
    try:
        fobj = open(_envfile, "rb")
        _envlst = [_var for _var in readline_nullsep(fobj)]
        fobj.close()
    except IOError, error:
        print "Unable to open Gnome session environment:\n%s" % str(error)
        _envlst = None

    _env = None
    if _envlst is not None:
        _env = {}
        for _var in _envlst:
            if _var != "":
                _vars = _var.split("=", 1)
                if len(_vars) != 2:
                    print "Unable to read environment variable '%s'. Skipped." % _var
                else:
                    _env[_vars[0]] = _vars[1]
    return _env


def get_clean_environment():
    _clean_env = {}
    _env = get_environment()
    for _var in CLEAN_ENVIRONMENT:
        _val = _env.get(_var, "")
        if _val != "":
            _clean_env[_var] = _val
    return _clean_env


def get_gnome_session_environment():
    _mod_env = None
    _session_pid = grep_pid(processname = "gnome-session")
    if _session_pid is None:
        print "No Gnome session found."
    else:
        print "Gnome session PID: %s" % _session_pid
        _mod_env = get_clean_environment()
        _session_env = get_process_environment(pid = _session_pid)
        if _session_env is None:
            _mod_env = None
        else:
            _mod_env.update(_session_env)
    return _mod_env


def debug_print_environment():
    _env = os.environ
    print "\nCurrent environment:"
    print "-----------------------------------------------------------------------------"
    for _var in _env:
        print "%s: %s" % (_var, _env[_var])
    print "-----------------------------------------------------------------------------"


def exec_command(args):
    if not isinstance(args, types.ListType):
        raise TypeError("List of arguments expected.")
    _output = subprocess.Popen(args, stdout = subprocess.PIPE).communicate()[0]
    _output = _output.strip()
    return _output


def grep_pid(processname):
    _pid = None
    output = exec_command(args = ["pgrep", processname])
    try:
        _pid = int(output)
    except ValueError:
        print "Unable to get PID of process '%s'." % processname
        _pid = None
    return _pid


def pid_exists(pid):
    """
    @type pid: String
    """
    _exists = False
    output = exec_command(args = ["ps", "--no-headers", "--pid", pid])
    if output != "":
        _exists = True
    return _exists
