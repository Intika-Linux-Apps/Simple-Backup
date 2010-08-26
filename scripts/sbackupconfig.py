#! /usr/bin/env python

#   Simple Backup - post-installation script for upgrading Simple Backup
#
#   Copyright (c)2009-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
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
:mod:`sbackupupgrade` --- post-installation script for upgrading Simple Backup
==============================================================================

.. module:: sbackupupgrade
   :synopsis: helper script for upgrading sbackup from older versions
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

This script provides necessary functionality when upgrading SBackup
to a new version. Purpose of this script is to be run from the Debian
`postinst` script after package update resp. manually after `make install`.

Since the package (at least core) is configured when this script runs,
we can import modules from sbackup here.
"""

import sys
import traceback
import os
import pwd
import ConfigParser
import re
import shutil

from sbackup.pkginfo import Infos
from sbackup.core import ConfigManager

from sbackup.util import system


# definition of error codes
NO_ERRORS = 0
NO_SUPERUSER = 1
GENERAL_ERROR = 9


class _Config(ConfigParser.ConfigParser):
    """A customized ConfigParser for reading and writing of SBackup
    configuration files.
    
    """
    def __init__(self, configfile):
        """Default constructor. Reads the given file into this
        parser.
        
        :param configfile: Full path to the current configuration file
        
        """
        ConfigParser.ConfigParser.__init__(self)
        self._configfile = configfile
        try:
            fobj = file(self._configfile, "r")
        except IOError:
            print "Unable to open `%s` for reading." % str(self._configfile)
        else:
            self.readfp(fobj, self._configfile)
            fobj.close()

    def optionxform(self, option):
        """
        Default behaviour of ConfigParser is to set the option keys to lowercase. 
        by overiding this method, we make it case sensitive. that's really important for dirconfig pathes 
        """
        return str(option)

    def commit_to_disk(self):
        """Writes the current configuration set to the disk. The
        configuration file given to the constructor is used.
        
        """
        try:
            fobj = file(self._configfile, "wb")
        except IOError:
            print "Unable to open `%s` for writing." % str(self._configfile)
        else:
            ConfigParser.ConfigParser.write(self, fobj)
            fobj.close()


class _Settings(object):
    """Class containing constants for upgrading the log option.
    
    These constants cover
    - `__logindefs`: path to file ``login.defs``
    - `__uidmin_name`: name of entry for minimal uid
    - `__uidmax_name`: name of entry for maximal uid
    
    The constants are accessable using the defined classmethods.         
    """
    __logindefs = "/etc/login.defs"
    __uidmin_name = "UID_MIN"
    __uidmax_name = "UID_MAX"

    def __init__(self):
        pass

    @classmethod
    def get_logindefs_path(cls):
        """Returns the path to the file `login.defs`.            
        """
        return cls.__logindefs

    @classmethod
    def get_uidmin_name(cls):
        """Returns the name of the entry for minimal uid.            
        """
        return cls.__uidmin_name

    @classmethod
    def get_uidmax_name(cls):
        """Returns the name of the entry for maximal uid.            
        """
        return cls.__uidmax_name


class _UpgradeAllConffiles(object):
    """This class encapsulates the upgrading of the log options due
    to changes in log file naming in release 0.2.0-RC3. In prior
    releases the log file was named `sbackup.log`. With release
    0.2.0-RC3 this has changed. From now the log file for the default
    profile is named `sbackup.log` and log files for any other
    profiles are named `sbackup-profilename.log`. This was
    neccessary due to problems with identical names of log files.    
    """

    def __init__(self):
        """Constructor of the log option upgrader.        
        """
        self._min_uid = 1000       # fallback values
        self._max_uid = 60000
        self._users = []
        self._configdirs = []

        reexp_templ = "^%s[ \t]+(\d+)$"
        self._reexp_min_uid = re.compile(reexp_templ
                                         % _Settings.get_uidmin_name(),
                                         re.IGNORECASE)
        self._reexp_max_uid = re.compile(reexp_templ
                                         % _Settings.get_uidmax_name(),
                                         re.IGNORECASE)

    def __repr__(self):
        _repr = ["min uid: %s" % self._min_uid,
                 "max uid: %s" % self._max_uid,
                 "users: %s" % self._users,
                 "config dirs: %s" % self._configdirs
               ]
        return "\n".join(_repr)

    def _read_logindefs(self):
        """Reads the lower and upper limit for user ids from
        the `login.defs` file.        
        """
        defspath = _Settings.get_logindefs_path()
        if os.path.isfile(defspath) and os.access(defspath, os.F_OK and os.R_OK):
            eof = False
            try:
                defsfile = file(defspath, "r")
                while not eof:
                    defsline = defsfile.readline()
                    if defsline == "":
                        eof = True
                    else:
                        defsline = defsline.strip()
                        match = self._reexp_min_uid.search(defsline)
                        if match is not None:
                            self._min_uid = int(match.group(1))

                        match = self._reexp_max_uid.search(defsline)
                        if match is not None:
                            self._max_uid = int(match.group(1))
            except IOError:
                print "Error while reading definitions from '%s'. "\
                      "Using defaults." % (defspath)
            else:
                defsfile.close()
        else:
            print "Unable to read definitions from '%s'. "\
                  "Using defaults." % (defspath)

    def _retrieve_users(self):
        """Retrieves all users from the password database that are
        apparently not system services (using the `uid_min` and
        `uid_max` for this). 
        
        """
        self._users = []
        allpw = pwd.getpwall()
        for cpw in allpw:
            try:
                uid = cpw.pw_uid
            except KeyError:
                continue
            if uid >= self._min_uid and uid <= self._max_uid:
                self._users.append(cpw)

    def _make_configdir_list(self):
        """Creates a list containing all basic configuration directories
        of the previously retrieved users. This includes in any case the
        default configuration directory `/etc`.
        
        :note: It is assumed that user configurations are stored in a\
               directory like `~/.config/sbackup`.
        
        :todo: Implement a better way for retrieval of user's confdirs e.g.\
               by reading the users environ!
               
        """
        self._configdirs = []
        # for the superuser
        self._configdirs.append(ConfigManager.\
                                 ConfigManagerStaticData.get_superuser_confdir())

        # for the other users
        for user in self._users:
            try:
                wdir = user.pw_dir
            except KeyError:
                continue
            wdir = os.path.join(wdir,
                    ConfigManager.ConfigManagerStaticData.get_user_confdir_template())
            self._configdirs.append(wdir)



class CopyConf_nssbackup_to_sbackup_011(_UpgradeAllConffiles):

    def __init__(self):
        _UpgradeAllConffiles.__init__(self)

    def _mk_dir(self, dst, src):
        if not os.path.exists(dst):
            print "`%s` is being created" % dst
            os.mkdir(dst)
            _stats = os.stat(src)
            os.chown(dst, _stats.st_uid, _stats.st_gid)
            os.chmod(dst, _stats.st_mode)

    def _copy_default_profile(self):
        for cdir in self._configdirs:
            cdir_nssb = cdir.replace("sbackup", "nssbackup")

            if os.path.isdir(cdir_nssb) and os.access(cdir_nssb, os.F_OK and os.R_OK):
                self._mk_dir(cdir, cdir_nssb)
                cfile_src = os.path.join(cdir_nssb, "nssbackup.conf")
                cfile_dst = os.path.join(cdir, ConfigManager.ConfigManagerStaticData.get_default_conffile())
                self._copy_configfile(cfile_src, cfile_dst)

    def _copy_other_profiles(self):
        """Modifies the configuration files for the other profiles.
        
        """
        for cdir in self._configdirs:
            pdir = os.path.join(cdir, ConfigManager.ConfigManagerStaticData.get_profiles_dir())

            cdir_nssb = cdir.replace("sbackup", "nssbackup")
            pdir_nssb = os.path.join(cdir_nssb, ConfigManager.ConfigManagerStaticData.get_profiles_dir_nssbackup())

            # get the profile directory for current configuration directory
            if os.path.isdir(pdir_nssb) and\
               os.access(pdir_nssb, os.F_OK and os.R_OK):
                # and get the profiles from the profiles directory
                self._mk_dir(pdir, pdir_nssb)
                profiles_nssb = ConfigManager.get_profiles_nssbackup(pdir_nssb)
                for cprof in profiles_nssb:
                    _src = profiles_nssb[cprof][0]
                    _pname = os.path.basename(_src)
                    _dst = os.path.join(pdir, "sbackup%s" % (_pname.lstrip("nssbackup")))
                    self._copy_configfile(_src, _dst)

    def _copy_configfile(self, src, dst):
        """This method modifies a single configuration file, i.e.
        
        * it reads the existing value from the file
        * retrieves the new value under consideration of the profile name
        * writes the new value to the configuration file.
        
        Files that are not readable/writable are skipped.
        
        """
        if os.path.isfile(src) and\
           os.access(src, os.F_OK and os.R_OK):
            print "checking nssbackup config for copy: %s" % src
            if os.path.exists(dst):
                print "   `%s` already exists. Nothing to do." % dst
            else:
                print "   copy nssbackup configuration"
                print "   from `%s`" % (src)
                print "   to   `%s`" % (dst)

                try:
                    shutil.copy2(src, dst)
                    _stats = os.stat(src)
                    os.chown(dst, _stats.st_uid, _stats.st_gid)
                    os.chmod(dst, _stats.st_mode)
                except (OSError, IOError), error:
                    print "failed (%s)" % error

    def do_upgrade(self):
        """Public method that actually processes the upgrade
        consisting of the following steps:
        
        1. Reading the login defaults for determination of non-system users
        2. Retrieve all users on the system
        3. Make a list of all configuration directories for these users
        4. modify the default profile configuration file
        5. modify the configuration files for any other profiles.
        
        An appropriate error code is returned.
        
        """
        self._read_logindefs()
        self._retrieve_users()
        self._make_configdir_list()

        # keep order of method calls due to directory creation
        self._copy_default_profile()
        self._copy_other_profiles()


class UpgradeConfAllProfiles(_UpgradeAllConffiles):
    """This class encapsulates the upgrading of the log options due
    to changes in log file naming in release 0.2.0-RC3. In prior
    releases the log file was named `sbackup.log`. With release
    0.2.0-RC3 this has changed. From now the log file for the default
    profile is named `sbackup.log` and log files for any other
    profiles are named `sbackup-profilename.log`. This was
    neccessary due to problems with identical names of log files.    
    """

    def __init__(self):
        """Constructor of the log option upgrader.        
        """
        _UpgradeAllConffiles.__init__(self)

    def _modify_default_profile(self):
        """Modifies the configuration file for the default profile.
        
        """
        for cdir in self._configdirs:
            cfile = os.path.join(cdir,
                        ConfigManager.ConfigManagerStaticData.get_default_conffile())
            self._modify_configfile(cfile)

    def _modify_other_profiles(self):
        """Modifies the configuration files for the other profiles.
        
        """
        for cdir in self._configdirs:
            pdir = os.path.join(cdir,
                            ConfigManager.ConfigManagerStaticData.get_profiles_dir())
            # get the profile directory for current configuration directory
            if os.path.isdir(pdir) and\
               os.access(pdir, os.F_OK and os.R_OK and os.W_OK):
                # and get the profiles from the profiles directory
                profiles = ConfigManager.get_profiles(pdir)
                for cprof in profiles:
                    cconf = profiles[cprof][0]
                    self._modify_configfile(cconf)

    def _modify_configfile(self, conffile):
        """This method modifies a single configuration file, i.e.
        
        * it reads the existing value from the file
        * retrieves the new value under consideration of the profile name
        * writes the new value to the configuration file.
        
        Files that are not readable/writable are skipped.
        
        """
        if os.path.isfile(conffile) and\
           os.access(conffile, os.F_OK and os.R_OK and os.W_OK):
            print "checking file: %s" % conffile
            config = _Config(conffile)
            _default_config = ConfigManager.get_default_config_obj()
            if config.has_section("log"):
                if config.has_option("log", "file"):
                    logfile = config.get("log", "file")
                    logdir = os.path.dirname(logfile)

                    new_logfn = ConfigManager.get_logfile_name_template(conffile)
                    new_log = os.path.join(logdir, new_logfn)

                    if logfile == new_log:
                        print "   nothing to do. skipped"
                    else:
                        print "   changing log file option"
                        print "   from `%s`" % (logfile)
                        print "   to   `%s`" % (new_log)
                        config.set("log", "file", str(new_log))
                else:
                    config.set("log", "file", os.path.join(_default_config.get_logdir(),
                                                           ConfigManager.get_logfile_name_template(conffile)))
                    print "   no log file specified. Default value set"

                if not config.has_option("log", "level"):
                    config.set("log", "level", _default_config.get_loglevel())
                    print "   no log level specified. Default value set"
            else:
                config.add_section("log")
                config.set("log", "file", os.path.join(_default_config.get_logdir(),
                                                       ConfigManager.get_logfile_name_template(conffile)))
                config.set("log", "level", _default_config.get_loglevel())
                print "   no section `log` found. Default values set"

            config.commit_to_disk()

            if config.has_section("general"):
                # remove old backuplinks options - it's now always done.
                if config.has_option("general", "backuplinks"):
                    print "   Removing backuplinks option (not needed anymore)"
                    config.remove_option("general", "backuplinks")
                    config.commit_to_disk()

    def do_upgrade(self):
        """Public method that actually processes the upgrade
        consisting of the following steps:
        
        1. Reading the login defaults for determination of non-system users
        2. Retrieve all users on the system
        3. Make a list of all configuration directories for these users
        4. modify the default profile configuration file
        5. modify the configuration files for any other profiles.
        
        An appropriate error code is returned.
        
        """
        try:
            self._read_logindefs()
            self._retrieve_users()
            self._make_configdir_list()

            self._modify_default_profile()
            self._modify_other_profiles()
        except Exception, error:
            print "Error while upgrading profiles: %s" % error
            traceback.print_exc()


class CronSetter(object):
    """Reads schedule info from superuser's
    default profile and write according cron entries.
    
    Purpose is to re-create cron entries after package upgrades
    (i.e. when configurations already exist).
    """

    def __init__(self):
        pass

    def do_upgrade(self):
        """Public method that performs the setting.
        Returns always `NO_ERRORS` as exit code.
        """
        if system.is_superuser():
            try:
                print "Reading schedule info from superuser's default profile"
                _conffilehdl = ConfigManager.ConfigurationFileHandler()
                _defconffile = _conffilehdl.get_default_conffile_fullpath()
                print "Configuration: `%s`" % _defconffile

                if os.path.exists(_defconffile):
                    _conf = ConfigManager.ConfigManager(_defconffile)
                    _conf.write_schedule()
            except Exception, error:
                print "Error while writing CRON settings: %s" % error
                traceback.print_exc()

        else:
            print "Operation requires root privileges"


class UpgradeSBackupConf_v010_011(object):
    """Reads schedule info from superuser's
    default profile and write according cron entries.
    
    Purpose is to re-create cron entries after package upgrades
    (i.e. when configurations already exist).
    """

    def __init__(self):
        self._conffile = None
        self._valid_opts = ConfigManager.ConfigManagerStaticData.get_our_options()

    def _query_default_conffile(self):
        print "Reading schedule info from superuser's default profile"
        _conffilehdl = ConfigManager.ConfigurationFileHandler()
        _defconffile = _conffilehdl.get_default_conffile_fullpath()
        print "Configuration: `%s`" % _defconffile
        self._conffile = _defconffile
        if not os.path.exists(self._conffile):
            self._conffile = None

    def _make_conffile_backup(self):
        _bakf = "%s.before_upgrade_to_v011.bak" % self._conffile
        if not os.path.exists(_bakf):
            shutil.copy2(self._conffile, _bakf)

    def _clean_opts(self):
        print "Validating config file: %s" % self._conffile
        _mod = False
        if (self._valid_opts is None):
            return
        _conf = _Config(self._conffile)
        for section in _conf.sections():
            for key in _conf.options(section):
                if (not self._valid_opts.has_key(section)):
                    _conf.remove_section(section)
                    _mod = True
                    print "Section [%(section)s] in '%(configfile)s' should not exist. Removed."\
                          % {'section': section, 'configfile' : self._conffile}

                if (self._valid_opts[section].has_key(key) or self._valid_opts[section].has_key('*')):
                    continue

                _conf.remove_option(section, key)
                _mod = True
                print "Option '%s' in section '%s' in file '%s' is not known. Removed."\
                      % (key, section, self._conffile)

        if _mod:
            _conf.commit_to_disk()

    def _update_compress_format(self):
        print "Updating config file: %s" % self._conffile
        _conf = _Config(self._conffile)
        if _conf.has_option("general", "format"):
            _compr = _conf.get("general", "format")
            if str(_compr) == "1":  # sbackup < 0.11 compatibility hack
                _compr = "gzip"
                _conf.set("general", "format", _compr)
                _conf.commit_to_disk()

    def _update_schedule(self):
        _conf = ConfigManager.ConfigManager(self._conffile)

        if not _conf.has_section("schedule") \
                or (not _conf.has_option("schedule", "cron") \
                and not _conf.has_option("schedule", "anacron")):
            _sched = _conf.get_schedule_and_probe()
            if _sched is not None:  # entry in cron.* found that is not stored in conf file
                print "Schedule found on FS: %s" % str(_sched)
                _ctype = _sched[0]
                _cexpr = _sched[1]
                assert _ctype in ConfigManager.SCHEDULE_TYPES, "Given schedule type `%s` is invalid" % _ctype
                assert (_cexpr is not None) and (_cexpr != "None"), \
                       "Given cron expression `%s` is invalid" % _cexpr

                _conf.setSchedule(_ctype, _cexpr)
                _conf.saveConf()

    def do_upgrade(self):
        """Public method that performs the setting.
        Returns always `NO_ERRORS` as exit code.
        """
        if system.is_superuser():
            try:
                self._query_default_conffile()
                if self._conffile is not None:
                    self._make_conffile_backup()
                    self._clean_opts()
                    self._update_compress_format()
                    self._update_schedule()
            except Exception, error:
                print "Error while upgrading configuration 0.10 to 0.11: %s" % error
                traceback.print_exc()

        else:
            print "Operation requires root privileges"


class UpgradeApplication(object):
    """The upgrade application class that instantiates several upgrade
    action classes and processes them. Due to this design one can simply
    add and execute further upgrade actions. 
    
    """
    def __init__(self):
        """Default constructor. Creates an `UpgradeLogOption` object.
        
        """
        self.__upgrader_v010 = UpgradeSBackupConf_v010_011()
        self.__upgrader_v011 = UpgradeConfAllProfiles()
        self.__cron_setter = CronSetter()
        self.__nssbackup_configs = CopyConf_nssbackup_to_sbackup_011()

    def main(self):
        """Main method that actually does the upgrade process. It returns
        an appropriate error code. 
        
        """
        print "-" * 60
        print "%s %s upgrade tool" % (Infos.NAME, Infos.VERSION)
        print "-" * 60

        if not system.is_superuser():
            print "Upgrade script must be run with root privileges!"
            retcode = NO_SUPERUSER
        else:
            retcode = NO_ERRORS
            self.__upgrader_v010.do_upgrade()

            self.__nssbackup_configs.do_upgrade()

            self.__upgrader_v011.do_upgrade()
            self.__cron_setter.do_upgrade()

        return retcode


if __name__ == "__main__":
    try:
        _UPGRADER = UpgradeApplication()
        RETC = _UPGRADER.main()
    except:
        print "errors occurred:"
        traceback.print_exc()
        RETC = GENERAL_ERROR

    if RETC == NO_ERRORS:
        print "successful finished."

    sys.exit(RETC)
