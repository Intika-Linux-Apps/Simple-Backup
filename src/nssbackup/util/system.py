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

import glib


from nssbackup.util import readline_nullsep


COMMAND_GREP = "grep"
COMMAND_PS = "ps"


# default values for environment variable if not set
# see: http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
ENVVAR_XDG_DATA_DIRS = "XDG_DATA_DIRS"
DEFAULT_XDG_DATA_DIRS = "/usr/local/share/:/usr/share/"


CLEAN_ENVIRONMENT = {
# default Gnome environment 
    "_" : "",
    "COLORTERM" : "",
    "DBUS_SESSION_BUS_ADDRESS" : "",
    "DEFAULTS_PATH" : "",
    "DESKTOP_SESSION" : "",
    "DISPLAY" : "",
    "GDM_KEYBOARD_LAYOUT" : "",
    "GDMSESSION" : "",
    "GDM_LANG" : "",
    "GNOME_KEYRING_PID" : "",
    "GNOME_KEYRING_CONTROL" : "",
    "GPG_AGENT_INFO" : "",
    "GTK_MODULES" : "",
    "HISTCONTROL" : "",
    "HOME" : "",
    "LANG" : "",
    "LC_ALL" : "",
    "LD_LIBRARY_PATH" : "",
    "LESSCLOSE" : "",
    "LESSOPEN" : "",
    "LOGNAME" : "",
    "MANDATORY_PATH" : "",
    "MANPATH" : "",
    "OLDPWD" : "",
    "PATH" : "",
    "PWD" : "",
    "PYTHONPATH" : "",
    "SESSION_MANAGER" : "",
    "SHELL" : "",
    "SHLVL" : "",
    "SPEECHD_PORT" : "",
    "SSH_AUTH_SOCK" : "",
    "TERM" : "",
    "USER" : "",
    "USERNAME" : "",
    "WINDOWID" : "",
    "XAUTHORITY" : "",
    "XDG_CONFIG_DIRS" : "",
    "XDG_DATA_DIRS" : "",
    "XDG_SESSION_COOKIE" : "",
# additional KDE environment variables
    "KDE_FULL_SESSION" : "",
    "GS_LIB" : "",
    "DM_CONTROL" : "",
    "SSH_AGENT_PID" : "",
    "XDM_MANAGED" : "",
    "KDE_SESSION_VERSION" : "",
    "LD_BIND_NOW" : "",
    "GTK2_RC_FILES" : "",
    "WINDOWPATH" : "",
    "XCURSOR_THEME" : "",
    "KDE_SESSION_UID" : "",
    "QT_PLUGIN_PATH" : ""
    }


def get_user_home_dir():
    return os.path.expanduser('~')


def get_user_config_dir():
#    _confdir = os.getenv("XDG_CONFIG_DIR", os.path.normpath(os.path.join(os.getenv("HOME"), ".config")))
    _confdir = glib.get_user_config_dir()
    return _confdir


def get_user_data_dir():
#    _datadir = os.getenv("XDG_DATA_HOME", os.path.normpath(os.path.join(os.getenv("HOME"), ".local", "share")))
    _datadir = glib.get_user_data_dir()
    return _datadir


def get_pid():
    _pid = os.getpid()
    return _pid


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
#    starting_gid = os.getgid()
#    starting_uid_name = pwd.getpwuid(starting_uid)[0]
#    print 'switch_user: started as %s/%s' % \
#    (pwd.getpwuid(starting_uid).pw_name,
#    grp.getgrgid(starting_gid).gr_name)
#    print "UID: %s  EUID: %s  GID: %s" % (os.getuid(), os.geteuid(), os.getgid())

    if os.getuid() != 0:
        # We're not root so, like, whatever dude
#        print "switch_user: already running as '%s'" % starting_uid_name
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
#    print 'drop_privileges: Old umask: %s, new umask: %s' % \
    (oct(old_umask), oct(new_umask))

    final_uid = os.getuid()
    final_gid = os.getgid()
    print 'drop privileges: running as %s/%s' % \
    (pwd.getpwuid(final_uid).pw_name,
    grp.getgrgid(final_gid).gr_name)


def drop_privileges():
    switch_user(uid_name = 'nobody')


def set_grp(groupname):
    # [Bug 112540] : Let the admin group have read access to the backup dirs
    if os.geteuid() == 0:
        try :
            os.setgid(grp.getgrnam(groupname).gr_gid)
        except (KeyError, OSError), error:
            print "Failed to set GID to `admin`: %s" % error


def very_nice():
    os.nice(20)


def get_environment():
    _env = os.environ
    return _env


def set_default_environment():
    """Sets required environment variables to their specified default
    values if not defined. This can happen e.g. some root shells where
    no environment variable for the freedesktop.org base directories
    are defined.
    
    """
    var = ENVVAR_XDG_DATA_DIRS
    defval = DEFAULT_XDG_DATA_DIRS
    val = os.environ.get(var)
    if val is None:
        os.environ[var] = defval


def get_process_environment(pid):
    _envlst = None
    _envfile = "/proc/%s/environ" % pid
    try:
        fobj = open(_envfile, "rb")
        _envlst = [_var for _var in readline_nullsep(fobj)]
        fobj.close()
    except (OSError, IOError), error:
        print "Unable to open Gnome session environment: %s." % error
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


def set_display_from_session():
    key = 'DISPLAY'
    _display = os.environ.get(key)
    print "Display: `%s`" % _display
    if _display is None:
        _session = get_session_name()
        _env = get_session_environment(_session)
        if _env is not None:
            _ndisplay = _env.get(key)
            print "Updating %s to: %s" % (key, _ndisplay)
            if _ndisplay is not None:
                os.environ[key] = _ndisplay


def get_session_name():
    _session = ""
    if grep_pid("gnome-session") is not None:
        _session = "gnome"
    elif grep_pid("ksmserver") is not None:
        _session = "kde"
#TODO: Cover other DEs (LXDE, KDE...) here and above!
    return _session


def get_session_environment(session):
    mod_env = None
    if session == "gnome":
        print "Gnome session running"
        mod_env = _get_gnome_session_environment()

    elif session == "kde":
        print "KDE session running"
        mod_env = _get_kde_session_environment()

    else:
        mod_env = None
        print "Neither Gnome nor KDE session providing D-Bus is running"
    return mod_env


def _get_gnome_session_environment():
    _mod_env = _get_session_env(session = "gnome-session")
    return _mod_env


def _get_kde_session_environment():
    _mod_env = _get_session_env(session = "ksmserver")
    return _mod_env


def _get_session_env(session):
    _mod_env = None
    _session_pid = grep_pid(processname = session)
    if _session_pid is None:
        print "Session `%s` not found" % session
    else:
        print "Session `%s` PID: %s" % (session, _session_pid)
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


def exec_command_async(args, env = None):
    if not isinstance(args, types.ListType):
        raise TypeError("List of arguments expected.")
    pid = subprocess.Popen(args, env = env).pid
    return pid


def exec_command_stdout(args, env = None):
    """
    :note: Standard output is hold in memory. Don't use this if you expect much output.
    """
    if not isinstance(args, types.ListType):
        raise TypeError("List of arguments expected.")
    _output = subprocess.Popen(args, stdout = subprocess.PIPE, env = env).communicate()[0]
    _output = _output.strip()
    return _output


def exec_command_returncode(args, env = None):
    """
    """
    if not isinstance(args, types.ListType):
        raise TypeError("List of arguments expected.")
    _ret = subprocess.call(args, env = env)
    return _ret


def grep_pid(processname):
    _pid = None
    output = exec_command_stdout(args = ["pgrep", processname])
    try:
        _pid = int(output)
    except ValueError:
        print "Unable to get PID of process '%s'." % processname
        _pid = None
    return _pid


def pid_exists(pid, processname = None):
    """
    @type pid: String
    """
    if not isinstance(pid, types.StringTypes):
        raise TypeError("PID expected as string.")
    if processname is not None:
        if not isinstance(processname, types.StringTypes):
            raise TypeError("Process name expected as string.")

    _exists = False
    output = exec_command_stdout(args = [COMMAND_PS, "--no-headers", "-lF", "--pid", pid])
    if output != "":
        if processname is None:
            _exists = True
        else:
            if processname in output:
                _exists = True
    return _exists


def proc_exists(processname, env = None):
    if not isinstance(processname, types.StringTypes):
        raise TypeError("Process name expected as string.")
    if COMMAND_GREP in processname:
        raise ValueError("Name of checked process must not contain `%s`" % COMMAND_GREP)

    _exists = False
    cmd_ps = subprocess.Popen([COMMAND_PS, "ax", "--no-headers", "-lF"],
                              stdout = subprocess.PIPE, env = env)
    cmd_v_grep = subprocess.Popen([COMMAND_GREP, "-v", COMMAND_GREP],
                                  stdin = cmd_ps.stdout, stdout = subprocess.PIPE, env = env)
    cmd_grep = subprocess.Popen([COMMAND_GREP, processname],
                                stdin = cmd_v_grep.stdout, stdout = subprocess.PIPE, env = env)
    _output = cmd_grep.communicate()[0]
    _output = _output.strip()
    if _output != "":
        _exists = True
    return _exists
