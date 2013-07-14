#   Simple Backup - Configuration GUI (GTK+)
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

from gettext import gettext as _

import re
import os
import sys
import types

import gobject
import glib
import gtk

from sbackup.util import log
from sbackup.util import system
from sbackup.util.log import LogFactory
from sbackup.util.exceptions import SBException

from sbackup.core import ConfigManager
from sbackup.core.ConfigManager import ConfigurationFileHandler
from sbackup.core.ConfigManager import ConfigManagerStaticData

import sbackup.util as Util

from sbackup.ui.GladeGnomeApp import GladeGnomeApp
from sbackup.ui import misc
from sbackup.ui import gtk_rsrc

from sbackup.fs_backend import fam

from sbackup.util import exceptions
from sbackup.util import pathparse
from sbackup.util import constants
from sbackup.util import local_file_utils


sys.excepthook = misc.except_hook
system.launch_dbus_if_required()


class SBconfigGTK(GladeGnomeApp):
    """
    
    @todo: Unify displaying of error messages/dialog boxes!
    @todo: Strictly separate UI from core. Don't set defaults from the UI (business logic in handler).
    @todo: Use functions from ConfigManager to set the paths in
            a consistent manner.         
    @todo: Configuration handling must be reviewed. Direct manipulation
            of the configuration from widget's signal handler is *really*
            errorprone and hard to debug (e.g. clearing a text input field
            from the source code/application side before filling it with new
            content currently yields in the removal of the according
            config option and the config is unintentionally changed). 
    """
    # why class variables?
    configman = None
    conffile = None
    orig_configman = None
    plugin_manager = None

    def __init__(self):
        """Default constructor.
        """
        # it is distinguished between the 'current' conffile and
        # the 'default file' configuring the default profile
        self.default_conffile = None
        self.__configFileHandler = ConfigurationFileHandler()
        _path_conffile = self.__configFileHandler.get_default_conffile_fullpath()
        if os.path.exists(_path_conffile):
            self.default_conffile = _path_conffile
            self.conffile = self.default_conffile
            self.configman = ConfigManager.ConfigManager(self.default_conffile)

            # hack to get rid of schedule settings in non-admin profiles
            # we just remove existing schedules from the config files
            # and don't allow new settings by disabling the schedule page
            if os.geteuid() != 0:
                self.configman.remove_schedule()
                self.configman.saveConf()
            # end of hack

            self.orig_configman = ConfigManager.ConfigManager(self.default_conffile)
        else:
            self.configman = ConfigManager.ConfigManager()
            self.orig_configman = None
            gobject.idle_add(_notify_new_default_profile_created)

        self.logger = LogFactory.getLogger()
        self.__destination_uri_obj = None
        self.__destination_hdl = None
        self.__destination_failure = False

        GladeGnomeApp.__init__(self,
                               app_name = "SBackup",
                               app_version = "0.2",
                               filename = Util.get_resource_file(gtk_rsrc.CONFIGGUI_GLADEFILE),
                               top_window = gtk_rsrc.CONFIGGUI_TOPWINDOW,
                               widget_list = gtk_rsrc.get_configgui_widgets(),
                               handlers = gtk_rsrc.get_configgui_handlers())

        gtk.window_set_default_icon_from_file(Util.get_resource_file(constants.CONFIG_ICON_FILENAME))

        # hide the schedule tab if not root
        if not system.is_superuser():
            self.__enable_schedule_page(enable = False)
            self.widgets['label_schedule_page'].set_tooltip_text(\
            _('Scheduled backups are available for Administrator users only.'))

        # Initiate all data structures
        # Paths to be included or excluded
        self.include = gtk.ListStore(str)
        self.includetv = self.widgets["includetv"]
        self.includetv.set_model(self.include)
        cell = gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', self.cell_edited_callback, (self.include, "dirconfig", 1))
        column = gtk.TreeViewColumn(_('Name'), cell, text = 0)
        self.includetv.append_column(column)

        self.ex_paths = gtk.ListStore(str)
        self.ex_pathstv = self.widgets["ex_pathstv"]
        self.ex_pathstv.set_model(self.ex_paths)
        cell1 = gtk.CellRendererText()
        cell1.set_property('editable', True)
        cell1.connect('edited', self.cell_edited_callback, (self.ex_paths, "dirconfig", 0))
        column1 = gtk.TreeViewColumn(_('Name'), cell1, text = 0)
        self.ex_pathstv.append_column(column1)

        # Excluded file types and general regular expressions
        self.ex_ftype = gtk.ListStore(str, str)
        self.ex_ftypetv = self.widgets["ex_ftypetv"]
        self.ex_ftypetv.set_model(self.ex_ftype)
        cell3 = gtk.CellRendererText()
        column3 = gtk.TreeViewColumn(_('File Type'), cell3, text = 0)
        cell2 = gtk.CellRendererText()
        column2 = gtk.TreeViewColumn('Ext.', cell2, text = 1)
        self.ex_ftypetv.append_column(column3)
        self.ex_ftypetv.append_column(column2)

        self.ex_regex = gtk.ListStore(str)
        self.ex_regextv = self.widgets["ex_regextv"]
        self.ex_regextv.set_model(self.ex_regex)
        cell4 = gtk.CellRendererText()
        cell4.set_property('editable', True)
        cell4.connect('edited', self.cell_regex_edited_callback)
        column4 = gtk.TreeViewColumn('Name', cell4, text = 0)
        self.ex_regextv.append_column(column4)

        # Profile Manager
        # [ enable , profilename, cfPath ]
        self.profiles = gtk.ListStore(bool, str, str)
        # add the default profile and disable any modification to it
        self.profiles.append([True,
            ConfigManagerStaticData.get_default_profilename(),
            self.__configFileHandler.get_default_conffile_fullpath()])
        for i, v in self.configman.getProfiles().iteritems() :
            self.profiles.append([v[1], i, v[0]])
        self.profilestv = self.widgets['profilesListTreeView']
        self.profilestv.set_model(self.profiles)

        cell8, cell9 = gtk.CellRendererToggle(), gtk.CellRendererText()
        cell8.set_active(True)
        cell8.connect("toggled", self.on_prfEnableCB_toggled)

        enableCBColumn = gtk.TreeViewColumn(_("Enable"), cell8, active = 0)
        prfNameColumn = gtk.TreeViewColumn(_("Profile Name"), cell9, text = 1)

        self.profilestv.append_column(enableCBColumn)
        self.profilestv.append_column(prfNameColumn)

        # The split size coices        
        self.splitSizeLS = misc.set_model(widget = self.widgets['splitsizeCB'],
                                          values = ConfigManagerStaticData.get_splitsize_dict())

        self.__model_remote_services = misc.set_model(widget = self.widgets['cmb_set_remote_service'],
                                                      values = fam.get_remote_services_avail())

        self._fill_widgets_from_config(probe_fs = True)
        
        self.xml.signal_autoconnect(self.cb_dict)
        

    def isConfigChanged(self, force_the_change = False):
        """Checks whether the current configuration has changed compared to
        the configuration which was originally loaded resp. stored on last
        save action. The result (irrespective whether it was forced or not)
        is returned by the method.
        
        @param force_the_change: Flag that that forces the check to be True
                                (i.e. the method acts as there were changes
                                regardless of the real test result)
        
        @return: True if the config has changed, False otherwise
        @rtype: Boolean                        
        """
        changed = not self.configman.isConfigEquals(self.orig_configman)
        if force_the_change == True:
            changed = True
        self.widgets['save'].set_sensitive(changed)
        self.widgets['saveButton'].set_sensitive(changed)
        return changed

    def ask_save_config(self):
        """Checks whether the configuration has changed and displays
        a dialog window if so. The user then can decide to save, not to save
        the configuration or to cancel the process.
        
        @return: False if the user pressed 'yes' or 'no'; True in any other case
        @rtype: Boolean
        """
        cancelled = False
        changed = self.isConfigChanged()
        if changed:
            question = self.widgets['askSaveDialog']
            question.set_title("")
            response = question.run()
            question.hide()
            if response == gtk.RESPONSE_YES:
                self.on_save_clicked()
            elif response == gtk.RESPONSE_NO:
                pass
            else:
                cancelled = True
        return cancelled

    def __fill_dir_widgets_from_config(self):
        """Fills the directory include and exclude tabs according to
        the values found in the current configuration.
        """
        _section = "dirconfig"
        self.include.clear()
        self.ex_paths.clear()
        dirconfig = self.configman.get_dirconfig_local()
        if dirconfig is not None:
            for _item, _value in dirconfig:
                if _value == 1:
                    self.include.append([_item])
                elif _value == 0:
                    self.ex_paths.append([_item])

    def __fill_regex_widgets_from_config(self):
        # regexp excludes
        _known_ftypes_dict = ConfigManagerStaticData.get_known_ftypes_dict()
        _invalid_regex_found = False
        _invalid_regex = ""
        self.ex_ftype.clear()
        self.ex_regex.clear()
        if self.configman.has_option("exclude", "regex") :
            r = self.configman.get("exclude", "regex")
            if not Util.is_empty_regexp(r):
                _list = str(r).split(",")
                for i in _list:
# Bugfix LP #258542 
                    if re.match(r"\\\.\w+\$", i):
                        _ftype = i[2:len(i) - 1]
                        if _ftype in _known_ftypes_dict:
                            self.ex_ftype.append([_known_ftypes_dict[_ftype], _ftype])

                        else:
                            self.ex_ftype.append([_("Custom"), _ftype])
                    else:
                        if (not Util.is_empty_regexp(i)) and Util.is_valid_regexp(i):
                            self.ex_regex.append([i])
                        else:
                            r = Util.remove_conf_entry(r, i)
                            self.logger.warning(_("Invalid or empty regular expression ('%s') found in configuration. Removed.") % i)
                            _invalid_regex_found = True
                            _invalid_regex = "%s, %s" % (_invalid_regex, i)

        if _invalid_regex_found:
            self.configman.set("exclude", "regex", r)
            self.isConfigChanged()
            _msg = _("Invalid or empty regular expressions found\nin configuration file:\n'%s'\n\nThese expressions are not used and were\nremoved from the configuration.")\
                % (_invalid_regex.lstrip(","))
            gobject.idle_add(misc.show_errdialog, _msg,
                             self.__get_application_widget())

    def __fill_max_filesize_widgets_from_config(self):
        """Sets the UI elements for 'maximum size limit' to the value
        specified in configuration.
        """
        if self.configman.has_option("exclude", "maxsize"):
            _maxsize = self.configman.getint("exclude", "maxsize")
            self.widgets["ex_maxsize"].set_value(_maxsize / (1024 * 1024))
            if _maxsize > 0:
                self.widgets["ex_maxsize"].set_sensitive(True)
                self.widgets["ex_max"].set_active(True)
            else:
                self.widgets["ex_maxsize"].set_sensitive(False)
                self.widgets["ex_max"].set_active(False)
        else:
            self.widgets["ex_maxsize"].set_sensitive(False)
            self.widgets["ex_max"].set_active(False)

    def __fill_followlinks_widgets_from_config(self):
        """Sets the UI elements for 'followlinks' to the value
        specified in configuration.
        """
        section = "general"
        option = "followlinks"
        followlinks = False
        if self.configman.has_option(section, option):
            config_fl = self.configman.get(section, option)
            if config_fl is True or config_fl == 1 or config_fl == "1":
                followlinks = True
        self.widgets["followlinks"].set_active(followlinks)

    def __fill_compression_widgets_from_config(self):
        """Sets the UI elements for 'compression format' to the value
        specified in configuration.
        """
        cformats = ConfigManagerStaticData.get_compr_formats()
        cformatOpt = self.configman.get_compress_format()
        if cformatOpt not in cformats:
            cformatOpt = 'none'
        cformatIndex = cformats.index(cformatOpt)
        self.widgets["cformat"].set_active(cformatIndex)

    def __fill_purge_widgets_from_config(self):
        """Sets the UI elements for 'purge' to the value
        specified in configuration.
        """
        if self.configman.has_option("general", "purge"):
            self.logger.debug("Setting purge")
            if self.configman.get("general", "purge") == "log":
                self.widgets['logpurgeradiobutton'].set_active(True)
                self.widgets["purgecheckbox"].set_active(True)
            else:
                try :
                    purge = int(self.configman.get("general", "purge"))
                except Exception, e:
                    self.logger.error("Purge value '%s' is invalid: '%s'" \
                                % (self.configman.get("general", "purge"), e))
                    purge = 30
                self.widgets['purgedays'].set_text(str(purge))
                self.widgets['purgeradiobutton'].set_active(True)
                self.widgets["purgedays"].set_sensitive(True)
                self.on_purgedays_changed()
                self.widgets['purgecheckbox'].set_active(True)
        else:
            self.widgets["purgecheckbox"].set_active(False)
        self.on_purgecheckbox_toggled()

    def __fill_max_inc_widgets_from_config(self):
        """Sets the UI elements for 'Maximum of inc' to the value
        specified in configuration.
        """
        if self.configman.has_option("general", "maxincrement"):
            self.widgets["time_maxinc"].set_value(\
                            int(self.configman.get("general", "maxincrement")))

    def __fill_log_widgets_from_config(self):
        """Sets the UI elements for 'log' to the value
        specified in configuration.
        """
        _default_config = ConfigManager.get_default_config_obj()

        if not self.configman.has_section("log"):
            self.configman.add_section("log")

        if not self.configman.has_option("log", "level"):
            self.configman.set("log", "level", _default_config.get_loglevel())

        if not self.configman.has_option("log", "file"):
            self.configman.set_logdir(_default_config.get_logdir())
            self.configman.set_logfile_templ_to_config()

        loglevel = str(self.configman.get("log", "level"))  # LP #1159705
        valid_levels = ConfigManagerStaticData.get_valid_loglevels()
        selection = valid_levels[loglevel][1]
        self.widgets["loglevelcombobox"].set_active(selection)
        self.widgets["logfilechooser"].set_current_folder(self.configman.get_logdir())

    def __fill_report_widgets_from_config(self):
        """Sets the UI elements for 'report' to the value
        specified in configuration.

        @todo: Handling of non-existing settings must be removed and unified.
        """
        _from = ""
        _to = ""
        _server = ""
        _port = ""
        _user = ""
        _passw = ""
        _cert = None
        _key = None

        if self.configman.has_section("report"):
            if self.configman.has_option("report", "from"):
                _from = self.configman.get("report", "from")

            if self.configman.has_option("report", "to"):
                _to = self.configman.get("report", "to")

            if self.configman.has_option("report", "smtpserver"):
                _server = self.configman.get("report", "smtpserver")

            if self.configman.has_option("report", "smtpport"):
                _port = self.configman.get("report", "smtpport")

            if self.configman.has_option("report", "smtpuser") or \
               self.configman.has_option("report", "smtppassword"):
                self.widgets["smtplogincheckbox"].set_active(True)
                self.widgets['smtplogininfo'].set_sensitive(True)

                if self.configman.has_option("report", "smtpuser"):
                    _user = self.configman.get("report", "smtpuser")

                if self.configman.has_option("report", "smtppassword"):
                    _passw = self.configman.get("report", "smtppassword")
            else:
                self.widgets["smtplogincheckbox"].set_active(False)
                self.widgets['smtplogininfo'].set_sensitive(False)

            if self.configman.has_option("report", "smtptls"):
                self.widgets["TLScheckbutton"].set_active(True)
                self.widgets['TLSinfos'].set_sensitive(True)
            else:
                self.widgets["TLScheckbutton"].set_active(False)

            if self.configman.has_option("report", "smtpcert") or \
               self.configman.has_option("report", "smtpkey"):
                self.widgets["SSLradiobutton"].set_active(True)
                self.__enable_ssl_options(enable = True)

                if self.configman.has_option("report", "smtpcert"):
                    _cert = self.configman.get("report", "smtpcert")
                    self.widgets['crtfilechooser'].set_filename(_cert)

                if self.configman.has_option("report", "smtpkey"):
                    _key = self.configman.get("report", "smtpkey")
                    self.widgets['keyfilechooser'].set_filename(_key)
            else :
                self.widgets["TLSradiobutton"].set_active(True)
                self.__enable_ssl_options(enable = False)

        self.widgets["smtpfrom"].set_text(_from)
        self.widgets["smtpto"].set_text(_to)
        self.widgets["smtpserver"].set_text(_server)
        self.widgets["smtpport"].set_text(_port)
        self.widgets["smtplogin"].set_text(_user)
        self.widgets["smtppassword"].set_text(_passw)

    def __fill_schedule_widgets(self, from_func):
        """Sets the UI elements for 'schedule' to the value
        specified in configuration (only from configuration or from file
        and file system).
        
        @param from_func: function object reference which is called in order
                            to retrieve the current cron state
                            
        @note: Purpose of the given function object is to use this method
                with `ConfigManager.get_schedule` as well as
                `ConfigManager.get_schedule_and_probe`.
                
        @todo: Implement signature checking. 
        """
        if not isinstance(from_func, types.MethodType):
            raise TypeError("Given parameter 'from_func' must be of type "\
                            "Method. Got %s instead." % (type(from_func)))

        if system.is_superuser() and self.configman.is_default_profile():
            self.__enable_schedule_page(enable = True)

            croninfos = from_func()    # = (isCron, val)

            # any schedule information was found
            if  croninfos is not None:
                # scheduled using Cron i.e. a custom setting
                if croninfos[0] == 1:
                    self.__set_schedule_option('custom')
                    self.__set_value_txtfld_custom_cronline(croninfos[1])

                # scheduled using Anacron
                elif croninfos[0] == 0:
                    self.__set_schedule_option('simple')
                    self.__set_value_cmbbx_simple_schedule_freq(croninfos[1])

            # no scheduled backups
            else:
                self.__set_schedule_option('no')
        else:
            self.__enable_schedule_page(enable = False)

    def __fill_splitsize_widgets_from_config(self):
        if self.configman.has_option("general", "splitsize") :
            model = self.widgets["splitsizeCB"].get_model()
            custom = True
            for i in range(0, len(model)) :
                if model[i][1] == int(self.configman.get("general",
                                                        "splitsize")) / 1024:
                    self.widgets["splitsizeCB"].set_active(i)
                    self.__enable_splitsize_custom_option(enable = False)
                    custom = False
            if custom:
                # NOTE: if we don't do this is this order, the handler
                #        on splitsizeCB will overide splitsizeSB value
                self.widgets["splitsizeSB"].set_value(\
                        int(self.configman.get("general", "splitsize")) / 1024)
                self.widgets["splitsizeCB"].set_active(0)

    def __dest_from_config_helper(self):
        """Creates and returns a TargetHandlerInstance with set
        destination path as stored/set in ConfigurationManager.
        """
        if self.__destination_uri_obj is None:
            self.__destination_uri_obj = pathparse.UriParser()
            
        self.__destination_uri_obj.set_and_parse_uri(uri = self.configman.get_destination_path())
        _dest = fam.get_fam_target_handler_facade_instance()
        _dest.set_destination(self.__destination_uri_obj.uri)
        return _dest

    def __fill_destination_widgets(self):
        """Helper method which fills the UI widgets related to
        the backup target (i.e. destination).
        """
        _dest = self.__dest_from_config_helper()
        ctarget = _dest.query_dest_display_name()
        self.logger.debug("Current destination: %s" % ctarget)

        if _dest.is_local():
            self.__set_target_label("local", ctarget)
            if not _dest.dest_path_exists():
                _sec = _("A common mistake is a not mounted external disk.")
                _msg = _("Backup destination folder `%s` does not exist.\n\nPlease make "\
                  "sure the missing directory exists and check your settings on the "\
                  "destination settings page.") % ctarget
                _hdl = _("Unable to open backup destination")
                gobject.idle_add(misc.show_errdialog, _msg,
                                  self.__get_application_widget(),
                                  _hdl, _sec)
        else:
            self.__set_target_label("remote", ctarget)

    def _fill_widgets_from_config(self, probe_fs):
        """Prefill the GTK window with config infos.
        
        @param probe_fs: Flag whether to probe the filesystem for schedule info
        
        @todo: Opening of directories (e.g. target) must be unified over all
               modules that use such functionality!
        """
        if not isinstance(probe_fs, types.BooleanType):
            raise TypeError("Given parameter must be of boolean type. "\
                            "Got %s instead." % (type(probe_fs)))
        try:
            # General
            self.__fill_max_inc_widgets_from_config()
            self.__fill_compression_widgets_from_config()
            self.__fill_splitsize_widgets_from_config()

            # dirconfig and excludes
            self.__fill_dir_widgets_from_config()
            self.__fill_regex_widgets_from_config()

            # other exclude reasons
            self.__fill_max_filesize_widgets_from_config()
            self.__fill_followlinks_widgets_from_config()

            # target (= destination)
            self.__fill_destination_widgets()

            # schedule - with probing the filesystem or without
            if probe_fs:
                sched_func = self.configman.get_schedule_and_probe
            else:
                sched_func = self.configman.get_schedule
            self.__fill_schedule_widgets(from_func = sched_func)

            # Purging
            self.__fill_purge_widgets_from_config()

            # Log and report
            self.__fill_log_widgets_from_config()
            self.__fill_report_widgets_from_config()

            self.__fill_statusbar_from_config()
        except exceptions.NonValidOptionException, error:
            gobject.idle_add(self.__config_invalid_cb, error, probe_fs)
        else:
#            self.__set_default_focus()
            self.isConfigChanged()

    def __config_invalid_cb(self, error, probe_fs):
        dialog = gtk.MessageDialog(type = gtk.MESSAGE_ERROR,
                                   flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                   buttons = gtk.BUTTONS_CLOSE,
                                   message_format = _("%s\n\n"\
                                                      "A backup profile using default values was created. "\
                                                      "Save the new configuration in order to use it or "\
                                                      "check your existing configuration file manually.\n\n"\
                                                      "Important note: Saving will overwrite your "\
                                                      "existing invalid configuration.") % str(error))
        dialog.run()
        dialog.destroy()
        self.configman = ConfigManager.ConfigManager()
        self.orig_configman = None
        gobject.idle_add(self._fill_widgets_from_config, probe_fs)

#    def __set_default_focus(self):
#        self.widgets['label_general_page'].grab_focus()

    def __fill_statusbar_from_config(self):
        """Sets the profile name and the user mode.
        """
        stattxt = _("Current profile: %s") % self.configman.getProfileName()
        stattxt = misc.get_statusbar_msg_mode(stattxt)
        self.widgets['statusBar'].push(stattxt)

    def __enable_splitsize_custom_option(self, enable = True):
        """Enables resp. disables widgets for setting a custom archive
        splitsize.
        """
        self.widgets["splitsizeSB"].set_sensitive(enable)
        self.widgets["label_splitsize_custom"].set_sensitive(enable)

    def __enable_target_option(self, option):
        """The widgets within the 'Destination' page are
        enabled/disabled/set according to the given option.
        Unusable widgets are automatically disabled.
        """
        def __enable_local_target(enable = True):
            """The widgets within the 'Destination' page are
            enabled/disabled/set according to the given local target directory.
            """
            self.widgets["dest_local"].set_sensitive(enable)
            self.widgets["btn_browse_local"].set_sensitive(enable)

        def __enable_remote_target(enable = True):
            """The widgets within the 'Destination' page are
            enabled/disabled/set according to the given remote target.
            """
            self.widgets["dest_remote_light"].set_sensitive(enable)
            self.widgets["dest_remote"].set_sensitive(enable)
            self.widgets["btn_set_remote"].set_sensitive(enable)

        if option == "local":
            __enable_local_target(enable = True)
            __enable_remote_target(enable = False)
        elif option == "remote":
            __enable_local_target(enable = False)
            __enable_remote_target(enable = True)
        else:
            raise ValueError("Unknown target option given.")

    def __set_target_label(self, option, value):
        """Selects resp. sets the given choice for backup target.
        Valid options are 'local' and 'remote'.
        """
        self.__enable_target_option(option)
        twidget = None
        if option == "local":
            twidget = self.widgets["dest2"]
            label = self.widgets["dest_local"]
        elif option == "remote":
            twidget = self.widgets["dest3"]
            label = self.widgets["dest_remote"]
        else:
            raise ValueError("Unknown target option given.")
        label.set_text(value)
        twidget.set_active(True)
        twidget.grab_focus()

    def already_inc (self, configlist, toInclude):
        """configlist is like self.conf.items( "dirconfig" )
         
        @return: True if the dir is already included, False if not
        """
        for i, v in configlist :
            if v == "1" and i == toInclude :
                # the chosen item match an included one 
                dialog = gtk.MessageDialog(flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons = gtk.BUTTONS_CLOSE, message_format = _("Already included item !"))
                dialog.run()
                dialog.destroy()
                return True
        # No match found
        return False

    def already_ex (self, configlist, toExclude):
        """configlist is like self.conf.items( "dirconfig" )
        
        @return: True if the dir is already excluded, False if not
        """
        for i, v in configlist :
            if v == "0" and i == toExclude :
                # the chosen item match an included one 
                dialog = gtk.MessageDialog(flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons = gtk.BUTTONS_CLOSE, message_format = _("Already excluded item !"))
                dialog.run()
                dialog.destroy()
                return True
        # No match found
        return False

    def cell_regex_edited_callback(self, cell, path, new_text):
        # Check if new path is empty
        if Util.is_empty_regexp(new_text):
            misc.show_errdialog(parent = self.__get_application_widget(),
                                message_str = \
                _("Empty expression. Please enter a valid regular expression."))
        else:
            if Util.is_valid_regexp(new_text):
                # Remove old expression and add the new one
                value = self.ex_regex[path][0]
                r = self.configman.get("exclude", "regex")
                r = Util.remove_conf_entry(r, value)
                r = r + r"," + new_text.strip()
                r = r.strip(",")
                self.configman.set("exclude", "regex", r)
                self.ex_regex[path][0] = new_text
                self.isConfigChanged()
            else:
                misc.show_errdialog(parent = self.__get_application_widget(),
                                    message_str = \
                                _("Provided regular expression is not valid."))

    def cell_edited_callback(self, cell, path, new_text, data):
        # Check if new path is empty
        if (new_text == None) or (new_text == ""):
            dialog = gtk.MessageDialog(type = gtk.MESSAGE_ERROR,
                        flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons = gtk.BUTTONS_CLOSE,
                        message_format = _("Empty filename or path. Please enter a valid filename or path."))
            dialog.run()
            dialog.destroy()
            return
        # Check if new path exists and asks the user if path does not exists
        if not os.path.exists(new_text):
            dialog = gtk.MessageDialog(type = gtk.MESSAGE_QUESTION,
                        flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons = gtk.BUTTONS_YES_NO,
                        message_format = _("It seems the path you entered does not exists. Do you want to add this incorrect path?"))
            response = dialog.run()
            dialog.destroy()
            if response == gtk.RESPONSE_NO:
                return

        model, section, value = data
        self.configman.remove_option(section, model[path][0])
        model[path][0] = new_text
        self.configman.set(section, new_text, value)
        self.isConfigChanged()

    def on_ftype_toggled(self, *args): #IGNORE:W0613
        if self.widgets["ftype_st"].get_active():
            self.widgets["ftype_box"].set_sensitive(True)
            self.widgets["ftype_custom_ex"].set_sensitive(False)
        elif self.widgets["ftype_custom"].get_active():
            self.widgets["ftype_box"].set_sensitive(False)
            self.widgets["ftype_custom_ex"].set_sensitive(True)

    def on_ftype_st_box_changed(self, *args): #IGNORE:W0613
#TODO: on_ftype_st_box_changed
#        print("TODO: on_ftype_st_box_changed")
        pass

    def on_save_activate(self, *args): #IGNORE:W0613
        self.on_save_clicked()

    def on_save_as_activate(self, *args): #IGNORE:W0613
        dialog = gtk.FileChooserDialog(title = _("Save configuration as..."),
                                parent = self.__get_application_widget(),
                                action = gtk.FILE_CHOOSER_ACTION_SAVE,
                                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        response = dialog.run()
        if response == gtk.RESPONSE_OK :
            self.configman.saveConf(dialog.get_filename())
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()

    def on_menu_help_activate(self, button):
        misc.open_uri("ghelp:sbackup")

    def on_menu_about_activate(self, *args): #IGNORE:W0613
        misc.show_about_dialog(set_transient_for = self.widgets["sbackupConfApp"])

    def on_reload_clicked(self, *args): #IGNORE:W0613
        self.configman = ConfigManager.ConfigManager(self.conffile)
        # hack to get rid of schedule settings in non-default profiles
        # we just remove existing schedules from the non-default config files
        # and don't allow new settings by disabling the schedule page
        if not self.configman.is_default_profile():
            self.configman.remove_schedule()
            self.configman.saveConf()
        # end of hack
        self.orig_configman = ConfigManager.ConfigManager(self.conffile)
        self._fill_widgets_from_config(probe_fs = True)
        self.isConfigChanged()
        self.logger.debug("Config '%s' loaded" % self.conffile)

    def on_save_clicked(self, *args): #IGNORE:W0613
        self.logger.debug("Saving Config")
        self.configman.saveConf()
        self.conffile = self.configman.conffile
        if not self.default_conffile:
            self.default_conffile = self.conffile
        self.orig_configman = ConfigManager.ConfigManager(self.configman.conffile)
        self.isConfigChanged()

    def on_backup_clicked(self, *args): #IGNORE:W0613
        cancelled = self.ask_save_config()
        if not cancelled:
            dialog = self.widgets["dialog_make_backup"]
            chkbtn_full_bak = self.widgets["checkbtn_make_backup_full"]
            btn_cancel = self.widgets['btn_cancel_make_backup']
            btn_cancel.grab_focus()

            response = dialog.run()
            _full_bak = chkbtn_full_bak.get_active()
            dialog.hide()

            if response == gtk.RESPONSE_APPLY:
                _path_to_app = Util.get_resource_file(constants.BACKUP_COMMAND)
                _cmd = [_path_to_app]

                if _full_bak is True:
                    _cmd.append("--full")

                _env = None
                if system.is_superuser():
                    _env = {}   # clear environment
                system.exec_command_async(args = _cmd, env = _env)
                misc.show_infodialog(message_str = _("A backup process is now executed in the background.\n\nYou can monitor the progress of the backup by means of the status indicator displayed in the notification area."),
                                     parent = self.top_window, headline_str = _("Backup process started"))
            elif response == gtk.RESPONSE_CANCEL or \
                 response == gtk.RESPONSE_DELETE_EVENT:
                pass
            else:
                self.logger.error(_("Unexpected dialog response: %s") % response)
                raise ValueError("Unexpected dialog response: %s" % response)

    def on_cformat_changed(self, *args): #IGNORE:W0613
        """
        handle that sets the compression format
        """
        selected = self.widgets["cformat"].get_active()
        cformats = ConfigManagerStaticData.get_compr_formats()
        if 0 <= selected < len(cformats):
            self.configman.set("general", "format", cformats[selected])
        else :
            self.configman.remove_option("general", "format")

        if selected == cformats.index("none"):
            # 'none' -> activate split functionality
            self.widgets['splitsizevbox'].set_sensitive(True)
        else :
            self.widgets["splitsizeCB"].set_active(1)
            self.widgets['splitsizevbox'].set_sensitive(False)
            if self.configman.has_option("general", "splitsize"):
                self.configman.remove_option("general", "splitsize")
            self.on_splitsizeCB_changed()
        self.isConfigChanged()

    def on_cmb_set_remote_service_changed(self, *args): #IGNORE:W0613
        pass
#        dialog = self.widgets['dialog_connect_remote']
#        cmbbx = self.widgets['cmb_set_remote_service']
#        model = cmbbx.get_model()
#        label, value = model[cmbbx.get_active()]
#        print "on_cmb_set_remote_service_changed - label: %s value: %s" % (label, value)
#        _user = self.widgets['entry_set_remote_user']
#        _user_lab = self.widgets['label_set_remote_user']
#        _pass = self.widgets['entry_set_remote_pass']
#        _pass_lab = self.widgets['label_set_remote_pass']
#
#        if value == REMOTE_SERVICE_FTP_PUBLIC:
#            _user.hide()
#            _user_lab.hide()
#            _pass.hide()
#            _pass_lab.hide()
#        else:
#            _user.show()
#            _user_lab.show()
#            _pass.show()
#            _pass_lab.show()
#        _width, _height = dialog.get_size()
#        dialog.resize(width = _width, height = 1)

    def on_splitsizeCB_changed(self, *args): #IGNORE:W0613
        """
        """
        model = self.widgets["splitsizeCB"].get_model()
        label, value = model[self.widgets["splitsizeCB"].get_active()]
        if value != -1 :
            self.__enable_splitsize_custom_option(enable = False)
            self.configman.set("general", "splitsize", value * 1024)
        else :
            # activate Spin box
            self.__enable_splitsize_custom_option(enable = True)
            val = self.widgets['splitsizeSB'].get_value_as_int()
            self.configman.set("general", "splitsize", val * 1024)
        self.isConfigChanged()

    def on_splitsizeSB_value_changed(self, *args): #IGNORE:W0613
        """
        """
        val = int(self.widgets['splitsizeSB'].get_value())
        self.configman.set("general", "splitsize", val * 1024)
        self.isConfigChanged()

    def on_inc_addfile_clicked(self, *args): #IGNORE:W0613
        self.__check_for_section("dirconfig")
        dialog = gtk.FileChooserDialog(title = _("Include file..."),
                                parent = self.__get_application_widget(),
                                action = gtk.FILE_CHOOSER_ACTION_OPEN,
                                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        filter = gtk.FileFilter()
        filter.set_name(_("All files"))
        filter.add_pattern("*")
        dialog.add_filter(filter)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            _file = _prepare_filename(dialog.get_filename())
            _enc_file = _escape_path(_file)
            if not self.already_inc(self.configman.items("dirconfig", raw = True), _enc_file):
                self.include.append([_file])
                self.configman.set("dirconfig", _enc_file, "1")
                self.isConfigChanged()
        dialog.destroy()

    def __check_for_section(self, section):
        if not self.configman.has_section(section):
            self.configman.add_section(section)

    def on_inc_adddir_clicked(self, *args): #IGNORE:W0613
        self.__check_for_section("dirconfig")
        dialog = gtk.FileChooserDialog(title = _("Include folder..."),
                                parent = self.__get_application_widget(),
                                action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            _dir = _prepare_dirname(dialog.get_filename())
            _enc_dir = _escape_path(_dir)
            if not self.already_inc(self.configman.items("dirconfig", raw = True), _enc_dir):
                self.include.append([_dir])
                self.configman.set("dirconfig", _enc_dir, "1")
                self.isConfigChanged()
        dialog.destroy()

    def on_inc_del_clicked(self, *args):
        self.__check_for_section("dirconfig")
        (store, iter) = self.includetv.get_selection().get_selected()
        if store and iter:
            enc_val = _escape_path(store.get_value(iter, 0))
            self.configman.remove_option("dirconfig", enc_val)
            self.isConfigChanged()
            store.remove(iter)

    def on_ex_addfile_clicked(self, *args):
        self.__check_for_section("dirconfig")
        dialog = gtk.FileChooserDialog(title = _("Exclude file..."),
                                parent = self.__get_application_widget(),
                                action = gtk.FILE_CHOOSER_ACTION_OPEN,
                                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        filter = gtk.FileFilter()
        filter.set_name(_("All files"))
        filter.add_pattern("*")
        dialog.add_filter(filter)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            _file = _prepare_filename(dialog.get_filename())
            _enc_file = _escape_path(_file)
            if not self.already_inc(self.configman.items("dirconfig", raw = True), _enc_file):
                self.ex_paths.append([_file])
                self.configman.set("dirconfig", _enc_file, "0")
                self.isConfigChanged()
        dialog.destroy()

    def on_ex_adddir_clicked(self, *args):
        self.__check_for_section("dirconfig")
        dialog = gtk.FileChooserDialog(title = _("Exclude folder..."),
                                parent = self.__get_application_widget(),
                                action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            _dir = _prepare_dirname(dialog.get_filename())
            _enc_dir = _escape_path(_dir)
            if not self.already_ex(self.configman.items("dirconfig", raw = True), _enc_dir):
                self.ex_paths.append([_dir])
                self.configman.set("dirconfig", _enc_dir, "0")
                self.isConfigChanged()
        dialog.destroy()

    def on_ex_delpath_clicked(self, *args):
        self.__check_for_section("dirconfig")
        (store, iter) = self.ex_pathstv.get_selection().get_selected()
        if store and iter:
            enc_val = _escape_path(store.get_value(iter, 0))
            self.configman.remove_option("dirconfig", enc_val)
            self.isConfigChanged()
            store.remove(iter)

    def on_dest_toggled(self, *args):
        if self.widgets["dest2"].get_active():
            self.__enable_target_option("local")

        elif self.widgets["dest3"].get_active():
            self.__enable_target_option("remote")

        # set changed path to destination
        if self.__destination_uri_obj is not None:
            _uri = self.__destination_uri_obj.uri
            self.configman.set("general", "target", _uri)
            self.isConfigChanged()

        else:
            raise ValueError("Unexpected widget was toggled.")

    def __enable_schedule_page(self, enable = True):
        """Enables resp. disables the complete schedule page including the
        tab label.
        
        @param enable: If True the page gets enabled, if False disabled.
        
        """
        self.widgets["label_schedule_page"].set_sensitive(enable)

        self.widgets["rdbtn_no_schedule"].set_sensitive(enable)
        self.widgets["rdbtn_simple_schedule"].set_sensitive(enable)
        self.widgets["rdbtn_custom_schedule"].set_sensitive(enable)

        self.widgets["label_simple_schedule_freq"].set_sensitive(enable)
        self.widgets["cmbbx_simple_schedule_freq"].set_sensitive(enable)

        self.widgets["label_custom_cronline"].set_sensitive(enable)
        self.widgets["txtfld_custom_cronline"].set_sensitive(enable)

        self.widgets["img_schedule_infotext"].set_sensitive(enable)
        self.widgets["label_schedule_infotext"].set_sensitive(enable)

    def __enable_schedule_option(self, option):
        """Enables resp. disables the according widgets for the given schedule
        option. Values are not set.
        """
        def __enable_no_scheduling(enable = True):
            """Enables resp. disables options related to 'No scheduling'.
            Values are not set.
            """
            pass

        def __enable_simple_scheduling(enable = True):
            """Enables resp. disables options related to 'Simple scheduling'.
            Values are not set.
            """
            self.widgets["label_simple_schedule_freq"].set_sensitive(enable)
            self.widgets["cmbbx_simple_schedule_freq"].set_sensitive(enable)

        def __enable_custom_scheduling(enable = True):
            """Enables resp. disables options related to 'Custom scheduling'.
            Values are not set.
            """
            self.widgets["label_custom_cronline"].set_sensitive(enable)
            self.widgets["txtfld_custom_cronline"].set_sensitive(enable)

        if option == "no":
            __enable_no_scheduling(enable = True)
            __enable_simple_scheduling(enable = False)
            __enable_custom_scheduling(enable = False)
        elif option == "simple":
            __enable_no_scheduling(enable = False)
            __enable_simple_scheduling(enable = True)
            __enable_custom_scheduling(enable = False)
        elif option == "custom":
            __enable_no_scheduling(enable = False)
            __enable_simple_scheduling(enable = False)
            __enable_custom_scheduling(enable = True)
        else:
            raise ValueError("Unknown schedule option given.")

    def __set_schedule_option(self, option):
        self.__enable_schedule_option(option)
        if option == "no":
            self.widgets["rdbtn_no_schedule"].set_active(is_active = True)
        elif option == "simple":
            self.widgets["rdbtn_simple_schedule"].set_active(is_active = True)
        elif option == "custom":
            self.widgets["rdbtn_custom_schedule"].set_active(is_active = True)
        else:
            raise ValueError("Unknown schedule option given.")

    def __set_value_txtfld_custom_cronline(self, cronline):
        self.widgets['txtfld_custom_cronline'].set_text(cronline)

    def __set_value_cmbbx_simple_schedule_freq(self, frequency):
        _valid_freqs = ConfigManagerStaticData.get_simple_schedule_frequencies()

        if frequency in _valid_freqs.keys():
            self.widgets['cmbbx_simple_schedule_freq'].set_active(\
                                                        _valid_freqs[frequency])
        else:
            raise ValueError("Unknown anacron setting found!")

    def on_rdbtn_schedule_toggled(self, *args):
        if self.widgets["rdbtn_no_schedule"].get_active():
            self.logger.debug("NO SCHEDULING selected.")
            self.__enable_schedule_option("no")
            _forcechange = self.configman.remove_schedule()
            self.isConfigChanged(_forcechange)

        elif self.widgets["rdbtn_simple_schedule"].get_active():
            self.logger.debug("SIMPLE SCHEDULING selected.")
            self.__enable_schedule_option("simple")
            self.on_cmbbx_simple_schedule_freq_changed()

        elif self.widgets["rdbtn_custom_schedule"].get_active():
            self.logger.debug("CUSTOM SCHEDULING selected.")
            self.__enable_schedule_option("custom")
            self.on_txtfld_custom_cronline_changed()

        else:
            raise ValueError("Unexpected radio button group member was changed.")

    def on_cmbbx_simple_schedule_freq_changed(self, *args):
        """Signal handler which is called whenever the schedule time frequency
        in the 'time_freq' combo box is changed.
        
        """
        _selection = self.widgets["cmbbx_simple_schedule_freq"].get_active()

        _valid_freqs = ConfigManagerStaticData.get_simple_schedule_frequencies()
        if _selection in _valid_freqs.values():
            for _freq_key in _valid_freqs.keys():
                if _selection == _valid_freqs[_freq_key]:
                    self.configman.setSchedule(0, _freq_key)
        self.isConfigChanged()
        self.logger.debug("Scheduling is: %s" % str(self.configman.get_schedule()))

    def on_txtfld_custom_cronline_changed(self, *args):
        _cronline = self.widgets['txtfld_custom_cronline'].get_text()
#        print "WE MUST CHECK THE INPUT!"
#TODO: WE MUST CHECK THE INPUT!
        self.configman.setSchedule(1, _cronline)
        self.isConfigChanged()
        self.logger.debug("Scheduling is: %s" % str(self.configman.get_schedule()))

    def on_time_maxinc_changed(self, *args):
        """Adds a changed value for 'maximum increment days' to the
        configuration.
        """
        self.configman.set("general", "maxincrement",
                            int(self.widgets["time_maxinc"].get_value()))
        self.isConfigChanged()

    def __enable_purge_options(self, enable = True):
        self.widgets['purgeradiobutton'].set_sensitive(enable)
        self.widgets['purgedays'].set_sensitive(enable)
        self.widgets['purgelabel'].set_sensitive(enable)
        self.widgets['logpurgeradiobutton'].set_sensitive(enable)
        self.widgets['purgelabel2'].set_sensitive(enable)

    def on_purgecheckbox_toggled(self, *args):
        """Signal handler that is called whenever the state of the 'Purging'
        checkbox is toggled.
        """
        purge = self.widgets["purgecheckbox"].get_active()
        if purge:
            self.__enable_purge_options(enable = True)
            self.on_purgeradiobutton_toggled()
        else:
            self.__enable_purge_options(enable = False)
            self.configman.remove_option("general", "purge")
            self.isConfigChanged()

    def on_purgeradiobutton_toggled(self, *args):
        if self.widgets["purgeradiobutton"].get_active():
            self.widgets["purgedays"].set_sensitive(True)
            try: i = int(self.widgets["purgedays"].get_text())
            except: i = -1
            if not (i > 0 and i < 10000):    i = 30
            self.widgets["purgedays"].set_text(str(i))
            self.configman.set("general", "purge", str(i))
            self.isConfigChanged()
        elif self.widgets["logpurgeradiobutton"].get_active():
            self.widgets["purgedays"].set_sensitive(False)
            self.configman.set("general", "purge", "log")
            self.isConfigChanged()

    def on_purgedays_changed(self, *args):
        try:
            i = int(self.widgets["purgedays"].get_text())
        except:
            i = 30
        if not (i > 0 and i < 10000):
            i = 30
        self.configman.set("general", "purge", str(i))
        self.isConfigChanged()

    def __enable_ssl_options(self, enable = True):
        self.widgets['label_certificate'].set_sensitive(enable)
        self.widgets['label_key'].set_sensitive(enable)
        self.widgets['keyfilechooser'].set_sensitive(enable)
        self.widgets['crtfilechooser'].set_sensitive(enable)

    def __get_application_widget(self):
        """Returns the top level application widget object.
        """
        app_obj = self.widgets['sbackupConfApp']
        return app_obj

    def on_testMailButton_clicked(self, *args):
        testmail_res = False
        if self.isConfigChanged(force_the_change = False) is True:
            misc.show_infodialog(parent = self.__get_application_widget(),
                    headline_str = _("Configuration has changed"),
                    message_str = _("There are unsaved modifications. Please save the configuration or revert these changes before testing the mail settings."))
        else:
            try :
                testmail_res = self.configman.testMail()
            except SBException, _exc:
                misc.show_warndialog(parent = self.__get_application_widget(),
                    headline_str = _("Test mail settings"),
                    message_str = _("The test failed with following output:"),
                    secmsg_str = "%s" % (_exc))

            if testmail_res is True:
                misc.show_infodialog(parent = self.__get_application_widget(),
                        headline_str = _("Test mail settings"),
                        message_str = _("The test was successful."))

    def on_smtplogincheckbox_toggled(self, *args):
        if self.widgets['smtplogincheckbox'].get_active():
            self.widgets['smtplogininfo'].set_sensitive(True)
            if self.widgets['smtplogin'].get_text():
                self.configman.set("report", "smtpuser",
                                    self.widgets['smtplogin'].get_text())
            if self.widgets['smtppassword'].get_text() :
                self.configman.set("report", "smtpuser",
                                    self.widgets['smtppassword'].get_text())
        else:
            self.widgets['smtplogininfo'].set_sensitive(False)
            if self.configman.has_option("report", "smtpuser") :
                self.configman.remove_option("report", "smtpuser")
            if self.configman.has_option("report", "smtppassword") :
                self.configman.remove_option("report", "smtppassword")
        self.isConfigChanged()

    def __enable_secure_email_options(self, enable = True):
        self.widgets['TLSinfos'].set_sensitive(enable)

    def on_TLScheckbutton_toggled(self, *args):
        """Signal handler that is called when the checkbutton for
        'secure email connection' is checked/unchecked.
        """
        if self.widgets['TLScheckbutton'].get_active():
            # secure connection is enabled
            self.__enable_secure_email_options(enable = True)
            self.configman.set("report", "smtptls", "1")
        else:
            # *NO* secure connection
            self.__enable_secure_email_options(enable = False)
            if self.configman.has_option("report", "smtptls") :
                self.configman.remove_option("report", "smtptls")
            if self.configman.has_option("report", "smtpcert") :
                self.configman.remove_option("report", "smtpcert")
            if self.configman.has_option("report", "smtpkey") :
                self.configman.remove_option("report", "smtpkey")
        self.isConfigChanged()

    def on_TLSradiobutton_toggled(self, *args):
        if self.widgets['TLSradiobutton'].get_active():
            # TLS (i.e. no cert/key required)
            self.__enable_ssl_options(enable = False)
            if self.configman.has_option("report", "smtpcert"):
                self.configman.remove_option("report", "smtpcert")
            if self.configman.has_option("report", "smtpkey"):
                self.configman.remove_option("report", "smtpkey")
        elif self.widgets['SSLradiobutton'].get_active():
            self.__enable_ssl_options(enable = True)
            if self.widgets['crtfilechooser'].get_filename() :
                self.on_crtfilechooser_selection_changed()
            if self.widgets['keyfilechooser'].get_filename() :
                self.on_keyfilechooser_selection_changed()
        else:
            raise ValueError("Unexpected signal received.")
        self.isConfigChanged()

    def on_ex_addftype_clicked(self, *args):
        """Signal handler that is called when the user presses the
        'Add filetype' exclude button.
        
        @note: A dot separating filename and extension is added automatically.
        """
        _known_ftypes_dict = ConfigManagerStaticData.get_known_ftypes_dict()
        dialog = self.widgets["ftypedialog"]
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:
            if self.widgets["ftype_st"].get_active():
                ftype = self.widgets["ftype_box"].get_model()\
                                    [self.widgets["ftype_box"].get_active()][0]
            else:
                ftype = self.widgets["ftype_custom_ex"].get_text()

            r = r""
            if self.configman.has_option("exclude", "regex"):
                r = self.configman.get("exclude", "regex")
# Bugfix LP #258542 
            ftype_regex = r"\.%s$" % ftype.strip()
            _sep = ","
            if _sep in ftype_regex:
                _msg = _("The given expression contains unsupported characters ('%s'). Currently it is not possible to use these characters in exclude expressions.") % _sep
                misc.show_warndialog(message_str = _msg,
                                    parent = self.__get_application_widget(),
                                    headline_str = _("Unsupported character"))
            else:
                if not Util.has_conf_entry(r, ftype_regex):
                    r = Util.add_conf_entry(r, ftype_regex)
                    self.configman.set("exclude", "regex", r)
                    if ftype in _known_ftypes_dict:
                        self.ex_ftype.append([_known_ftypes_dict[ftype], ftype])
                    else:
                        self.ex_ftype.append([_("Custom"), ftype])
        else:
            pass
        self.isConfigChanged()

    def on_ex_delftype_clicked(self, *args):
        """
        @todo: Check whether escaping of value (re.escape(value)) before \
                adding it is required?
        """
        (store, iter) = self.ex_ftypetv.get_selection().get_selected()
        if store and iter:
            value = store.get_value(iter, 1)
            r = self.configman.get("exclude", "regex")
# Bugfix LP #258542 
            ftype_regex = r"\.%s$" % value
            r = Util.remove_conf_entry(r, ftype_regex)
            self.configman.set("exclude", "regex", r)
            self.isConfigChanged()
            store.remove(iter)

    def on_ex_addregex_clicked(self, *args):
        """Signal handler which is called when button 'Add regex' for
        exclusion is clicked.
        """
        dialog = self.widgets["regexdialog"]
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:
            regex = self.widgets["regex_box"].get_text()
            _sep = ","
            if _sep in regex:
                _msg = _("The given expression contains unsupported characters ('%s'). Currently it is not possible to use these characters in exclude expressions.") % _sep
                misc.show_warndialog(message_str = _msg,
                                    parent = self.__get_application_widget(),
                                    headline_str = _("Unsupported character"))

            elif Util.is_empty_regexp(regex):
                misc.show_errdialog(parent = self.__get_application_widget(),
                            message_str = \
                _("Empty expression. Please enter a valid regular expression."))
            else:
                if Util.is_valid_regexp(regex):
                    r = r""
                    if self.configman.has_option("exclude", "regex"):
                        r = self.configman.get("exclude", "regex")

                    if not Util.has_conf_entry(r, regex):
                        r = Util.add_conf_entry(r, regex)
                        self.configman.set("exclude", "regex", r)
                        self.ex_regex.append([regex])
                else:
                    misc.show_errdialog(parent = self.__get_application_widget(),
                            message_str = \
                                _("Provided regular expression is not valid."))
        else:
            pass
        self.isConfigChanged()

    def on_ex_delregex_clicked(self, *args):
        (store, iter) = self.ex_regextv.get_selection().get_selected()
        if store and iter:
            value = store.get_value(iter, 0)
            r = self.configman.get("exclude", "regex")
            r = Util.remove_conf_entry(r, value)
            self.configman.set("exclude", "regex", r)
            self.isConfigChanged()
            store.remove(iter)

    def on_includetv_key_press_event(self, widget, event, *args): #IGNORE:W0613
        if event.keyval == gtk.keysyms.Delete :
            self.on_inc_del_clicked()

    def on_ex_pathstv_key_press_event(self, widget, event, *args): #IGNORE:W0613
        if event.keyval == gtk.keysyms.Delete :
            self.on_ex_delpath_clicked()

    def on_ex_ftypetv_key_press_event(self, widget, event, *args): #IGNORE:W0613
        if event.keyval == gtk.keysyms.Delete :
            self.on_ex_delftype_clicked()

    def on_ex_regextv_key_press_event(self, widget, event, *args): #IGNORE:W0613
        if event.keyval == gtk.keysyms.Delete :
            self.on_ex_delregex_clicked()

    def on_ex_max_toggled(self, *args): #IGNORE:W0613
        """Signal handler which is called whenever the checkbutton
        'Do not backup files bigger than' is checked resp. unchecked.
        """
        _exclude_max = self.widgets["ex_max"].get_active()

        if _exclude_max:
            self.widgets["ex_maxsize"].set_sensitive(True)
            self.on_ex_maxsize_changed()
        else:
            self.widgets["ex_maxsize"].set_sensitive(False)
            self.configman.remove_option("exclude", "maxsize")
            self.isConfigChanged()

    def on_ex_maxsize_changed(self, *args): #IGNORE:W0613
        """Signal handler which is called when the value for
        maximum file size is changed. The number (from the text field)
        is interpreted as Megabyte (MB).
        """
        msize = int(self.widgets["ex_maxsize"].get_value())
        self.configman.set("exclude", "maxsize", str(msize * 1024 * 1024))
        self.isConfigChanged()

    def on_followlinks_toggled(self, *args): #IGNORE:W0613
        if self.widgets['followlinks'].get_active():
            self.configman.set("general", "followlinks", 1)
        else :
            self.configman.remove_option("general", "followlinks")
        self.isConfigChanged()

    def on_btn_browse_local_clicked(self, *args): #IGNORE:W0613
        _dest = self.__dest_from_config_helper()
        ctarget = _dest.query_dest_display_name()
        
        self.logger.debug("Current destination: %s" % ctarget)
        self.widgets["dialog_browse_localdest"].set_current_folder(ctarget)
        gobject.idle_add(self.__browse_localdest)

    def __browse_localdest(self):
        dialog = self.widgets["dialog_browse_localdest"]
        dialog.set_transient_for(self.__get_application_widget())
        response = dialog.run()

        if response == gtk.RESPONSE_APPLY:
            dialog.hide()
            _target = dialog.get_filename()            
            if _target is None:  # LP #1174124 Catch invalid selections
                _target = ""
            
            if not (os.path.isdir(_target) and \
                    os.access(_target, os.R_OK | os.W_OK | os.X_OK)):
                _sec_msg = _("Please make sure the directory exists "\
                  "and check file permissions. Then try again.")
                _message_str = _("Selected backup destination folder"\
                  "`%s` does not exist or is not accessable.") % _target
                _headline_str = \
                _("Unable to access selected folder")
                gobject.idle_add(misc.show_errdialog,
                                  _message_str,
                                  self.__get_application_widget(),
                                  _headline_str, _sec_msg)
            else:
                self.widgets['dest_local'].set_text(_target)
                self.configman.set("general", "target", _target)
                _dest = self.__dest_from_config_helper()
                self.isConfigChanged()

        elif response in (gtk.RESPONSE_NONE, gtk.RESPONSE_CANCEL,
                          gtk.RESPONSE_DELETE_EVENT):
            dialog.hide()

        else:
            self.logger.error(_("Unexpected dialog response: %s") % response)
            gobject.idle_add(self.__browse_localdest)

    def on_checkbtn_show_password_toggled(self, *args): #IGNORE:W0613
        self.__set_entry_remote_pass_visibiliy()

    def __set_entry_remote_pass_visibiliy(self):
        _pass_e = self.widgets['entry_set_remote_pass']
        _pass_e.set_visibility(visible = self.widgets['checkbtn_show_password'].get_active())

    def on_btn_set_remote_clicked(self, *args): #IGNORE:W0613
        dest_obj = pathparse.UriParser()
        dest_obj.set_and_parse_uri(uri = self.configman.get_destination_path())
        if dest_obj is not None:
            self.__destination_uri_obj = dest_obj
        gobject.idle_add(self.__show_connect_remote_dialog)

    def __show_connect_remote_dialog(self):
        dialog = self.widgets["dialog_connect_remote"]
        btn_connect = self.widgets['btn_connect_remote']

        _server_e = self.widgets['entry_set_remote_server']
        _port_e = self.widgets['entry_set_remote_port']
        _dir_e = self.widgets['entry_set_remote_dir']
        _user_e = self.widgets['entry_set_remote_user']
        _pass_e = self.widgets['entry_set_remote_pass']
        _service_b = self.widgets['cmb_set_remote_service']

        dialog.set_transient_for(self.__get_application_widget())
        self.__set_entry_remote_pass_visibiliy()
        btn_connect.grab_focus()

        # default values
        _rservice = fam.get_default_remote_service()
        _server = ""
        _port = ""
        _dir = ""
        _user = ""
        _pass = ""

        # fill entries
#TODO: wrap use of UriParser into Fam facade        
        if self.__destination_uri_obj is not None:
            if not self.__destination_uri_obj.is_local():

                _rservice = fam.get_service_from_scheme(self.__destination_uri_obj.uri_scheme)

                if _rservice is None:
                    raise SBException("Unable to query remote service")

                _server = self.__destination_uri_obj.hostname
                _port = self.__destination_uri_obj.port
                _dir = self.__destination_uri_obj.path
                _user = self.__destination_uri_obj.username
                _pass = self.__destination_uri_obj.password


        _servmodel = _service_b.get_model()
        for _idx in range(len(_servmodel)):
            if _servmodel[_idx][misc.MODEL_COLUMN_INDEX_KEY] == _rservice:
                _sidx = _idx
                break

        _service_b.set_active(_sidx)
        _server_e.set_text(_server)
        _port_e.set_text(_port)
        _dir_e.set_text(_dir)
        _user_e.set_text(_user)
        _pass_e.set_text(_pass)

        dialog.set_sensitive(True)
        response = dialog.run()

        if response == gtk.RESPONSE_APPLY:
            self.logger.info(_("Connect to remote destination"))

            _sidx = _service_b.get_active()
            _rservice = _servmodel[_sidx][misc.MODEL_COLUMN_INDEX_KEY]

            _server = _server_e.get_text()
            _port = _port_e.get_text()
            _dir = _dir_e.get_text()
            _user = _user_e.get_text()
            _pass = _pass_e.get_text()

            self.logger.debug("User input in dialog 'connect to host'")
            self.logger.debug("  Service: %s" % _rservice)
            self.logger.debug("  Server: %s" % _server)
            self.logger.debug("  Port: %s" % _port)
            self.logger.debug("  Path: %s" % _dir)
            self.logger.debug("  User: %s" % _user)
            self.logger.debug("  Pass: %s\n" % ("*" * len(_pass)))

            dialog.set_sensitive(False)
            misc.set_watch_cursor(dialog)

            _scheme = fam.get_scheme_from_service(_rservice)
            _uri = pathparse.construct_remote_uri_from_tupel(_scheme, _server, _port, _dir, _user, _pass)
            self.__destination_uri_obj.set_and_parse_uri(_uri)

            self.__destination_hdl = fam.get_fam_target_handler_facade_instance()
            self.__destination_hdl.set_initialize_callback(self._mount_done_cb)
            self.__destination_hdl.set_destination(self.__destination_uri_obj.uri)
            self.__destination_failure = False

            gobject.idle_add(self.__destination_hdl.initialize)

        elif response == gtk.RESPONSE_CANCEL or \
             response == gtk.RESPONSE_DELETE_EVENT:
            dialog.hide()
            _icon = self.widgets["dest_remote_light"]
            _icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)

        else:
            self.logger.error(_("Unexpected dialog response: %s") % response)
            gobject.idle_add(self.__show_connect_remote_dialog)

    def _mount_done_cb(self, error):
        self.logger.debug("GUI._mount_done_cb: error: %s" % str(error))
        dialog = self.widgets["dialog_connect_remote"]

        if error is None:
            self.logger.info(_("Mount was sucessful (no errors)"))
            gobject.idle_add(self._do_remote_tests)
        else:
            misc.unset_cursor(dialog)

            _icon = self.widgets["dest_remote_light"]
            _icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)

            misc.show_warndialog(
                parent = self.__get_application_widget(),
                message_str = str(error),
                headline_str = _("Unable to mount host"))
            self.__destination_failure = True
            gobject.idle_add(self.__show_connect_remote_dialog)

    def _umount_done_cb(self, error):
        self.logger.debug("GUI._umount_done_cb: error: %s" % str(error))
        dialog = self.widgets["dialog_connect_remote"]

        if error is None:
            self.logger.info(_("Umount was sucessful (no errors)"))
        else:
            misc.unset_cursor(dialog)

            _icon = self.widgets["dest_remote_light"]
            _icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)

            misc.show_warndialog(
                parent = self.__get_application_widget(),
                message_str = str(error),
                headline_str = _("Unable to unmount host"))
            self.__destination_failure = True
        gobject.idle_add(self._umount_done)

    def _umount_done(self):
        self.logger.debug("umount done - failures: %s" % self.__destination_failure)
        dialog = self.widgets["dialog_connect_remote"]
        misc.unset_cursor(dialog)
        dialog.set_sensitive(True)
        if self.__destination_failure == False:
            self.__destination_hdl = None
            dialog.hide()

            _uri = self.__destination_uri_obj.uri
            _displname = self.__destination_uri_obj.query_display_name()
            self.configman.set("general", "target", _uri)
            self.widgets['dest_remote'].set_text(_displname)

            _icon = self.widgets["dest_remote_light"]
            _icon.set_from_stock(gtk.STOCK_OK, gtk.ICON_SIZE_MENU)

            self.isConfigChanged()
        else:
            _icon = self.widgets["dest_remote_light"]
            _icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)

            gobject.idle_add(self.__show_connect_remote_dialog)

    def _do_remote_tests(self):
        error = None
        self.logger.info(_("Perfom tests on remote host"))
        dialog = self.widgets["dialog_connect_remote"]
        try:
            self.__destination_hdl.test_destination()
        except exceptions.RemoteMountTestFailedError, error:
            misc.unset_cursor(dialog)

            _icon = self.widgets["dest_remote_light"]
            _icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)

            misc.show_warndialog(
                parent = self.__get_application_widget(),
                message_str = str(error),
                headline_str = _("Unable to access remote destination"))
            misc.set_watch_cursor(dialog)
            self.__destination_failure = True
        else:
            self.logger.info(_("All tests passed"))

        self.__destination_hdl.set_terminate_callback(self._umount_done_cb)
        gobject.idle_add(self.__destination_hdl.terminate)


    def on_logfilechooser_selection_changed(self, *args): #IGNORE:W0613
        self.configman.set_logdir(self.widgets['logfilechooser'].get_filename())
        self.configman.set_logfile_templ_to_config()
        self.isConfigChanged()
        self.logger.debug("Log file set: " + self.configman.get("log", "file"))

    def on_loglevelcombobox_changed(self, *args): #IGNORE:W0613
        if self.widgets['loglevelcombobox'].get_active_text() == "Info" :
            self.configman.set("log", "level", "20")
            self.isConfigChanged()
            self.logger.debug("Log level : " + self.configman.get("log", "level"))
        elif self.widgets['loglevelcombobox'].get_active_text() == "Debug" :
            self.configman.set("log", "level", "10")
            self.isConfigChanged()
            self.logger.debug("Log level : " + self.configman.get("log", "level"))
        elif self.widgets['loglevelcombobox'].get_active_text() == "Error" :
            self.configman.set("log", "level", "40")
            self.isConfigChanged()
            self.logger.debug("Log level : " + self.configman.get("log", "level"))
        elif self.widgets['loglevelcombobox'].get_active_text() == "Warning" :
            self.configman.set("log", "level", "30")
            self.isConfigChanged()
            self.logger.debug("Log level : " + self.configman.get("log", "level"))

    def on_smtpfrom_changed(self, *args): #IGNORE:W0613
        self.__check_for_section("report")
        if self.widgets['smtpfrom'].get_text() != "":
            self.configman.set("report", "from", self.widgets['smtpfrom'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "from")
            self.isConfigChanged()

    def on_smtpto_changed(self, *args): #IGNORE:W0613
        self.__check_for_section("report")
        if self.widgets['smtpto'].get_text() != "":
            self.configman.set("report", "to", self.widgets['smtpto'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "to")
            self.isConfigChanged()

    def on_smtpserver_changed(self, *args): #IGNORE:W0613
        self.__check_for_section("report")
        if self.widgets['smtpserver'].get_text() != "":
            self.configman.set("report", "smtpserver", self.widgets['smtpserver'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "smtpserver")
            self.isConfigChanged()

    def on_smtpport_changed(self, *args):
        self.__check_for_section("report")
        if self.widgets['smtpport'].get_text() != "":
            self.configman.set("report", "smtpport", self.widgets['smtpport'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "smtpport")
            self.isConfigChanged()

    def on_smtplogin_changed(self, *args):
        self.__check_for_section("report")
        if self.widgets['smtplogin'].get_text() != "":
            self.configman.set("report", "smtpuser", self.widgets['smtplogin'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "smtpuser")
            self.isConfigChanged()

    def on_smtppassword_changed(self, *args):
        self.__check_for_section("report")
        if self.widgets['smtppassword'].get_text() != "":
            self.configman.set("report", "smtppassword", self.widgets['smtppassword'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "smtppassword")
            self.isConfigChanged()

    def on_crtfilechooser_selection_changed(self, *args):
        self.__check_for_section("report")
        smtpcert = self.widgets['crtfilechooser'].get_filename()
        if smtpcert != None and os.path.isfile(smtpcert):
            self.configman.set("report", "smtpcert", self.widgets['crtfilechooser'].get_filename())
            self.isConfigChanged()
            self.logger.debug("Certificate : " + str(self.configman.get("report", "smtpcert")))

    def on_keyfilechooser_selection_changed(self, *args):
        self.__check_for_section("report")
        smtpkey = self.widgets['keyfilechooser'].get_filename()
        if smtpkey != None and os.path.isfile(smtpkey):
            self.configman.set("report", "smtpkey", smtpkey)
            self.isConfigChanged()
            self.logger.debug("Key : " + str(self.configman.get("report", "smtpkey")))

    def on_sbackupConfApp_delete_event(self, *args):
        """Signal handler that is called when the window decorator close
        button is clicked.
        """
        cancelled = self.ask_save_config()
        return cancelled

    def __terminate_app(self):
        self.configman = None
        self.orig_configman = None
        gtk.main_quit()

    def on_sbackupConfApp_destroy(self, *args):
        """Signal handler that is called when the window was destroyed.
        """
        self.__terminate_app()

    def on_exit_activate(self, *args):
        """Signal handler that is called when the 'Quit' menu item
        is selected.
        """
        cancelled = self.ask_save_config()
        if not cancelled:
            self.__terminate_app()

    def on_ftype_custom_ex_changed(self, *args):
#TODO: on_ftype_custom_ex_changed
#        print("TODO: on_ftype_custom_ex_changed")
        pass

    def on_prfManager_activate(self, *args):
        """Launch Profile manager dialog
        """
        cancelled = self.ask_save_config()
        if not cancelled:
            dialog = self.widgets["ProfileManagerDialog"]
            dialog.run()
            dialog.hide()

    def on_addProfileButton_clicked(self, *args):
        valid_input = False
        prf_set = False

        prfDir = local_file_utils.normpath(self.__configFileHandler.get_user_confdir(), "sbackup.d")
        if not os.path.exists(prfDir):
            os.makedirs(prfDir)

        dialog = self.widgets['askNewPrfNameDialog']
        dialog.set_title("")

        while not valid_input:
            response = dialog.run()
            dialog.hide()

            if response == gtk.RESPONSE_OK :
                enable = self.widgets['enableNewPrfCB'].get_active()
                prfName = self.widgets['newPrfNameEntry'].get_text()
                prfName = prfName.strip()
                prfConf = local_file_utils.normpath(prfDir, "sbackup-%s.conf" % prfName)
                prfConfDisabled = "%s-disable" % prfConf

                if not prfName or prfName is '':
                    misc.show_warndialog(
                        parent = self.widgets["ProfileManagerDialog"],
                        message_str = _("The given name of the new profile is empty. Please enter a valid profile name."),
                        headline_str = _("Profile name not valid"))
                    continue

                if os.path.exists(prfConf) or os.path.exists(prfConfDisabled):
                    misc.show_warndialog(
                        parent = self.widgets["ProfileManagerDialog"],
                        message_str = _("The given name of the new profile already exists. Please enter another name."),
                        headline_str = _("Profile name not valid"),
                        secmsg_str = _("Renaming of profiles is not supported."))
                    continue
                # if we reach this branch a valid profile name was choosen
                prf_set = True
            # if this branch is reached the input (OK, Cancel, Destroy) was
            # valid
            valid_input = True
        # end of while loop

        if prf_set:
            self.logger.debug("Got new profile name '%s : enable=%r' " % (prfName, enable))
            if not enable:
                prfConf = prfConfDisabled
            confman = ConfigManager.ConfigManager()
            confman.saveConf(prfConf)
            self.profiles.append([enable, prfName, prfConf])
#        else:
#            print "Adding of profile canceled."

    def on_removeProfileButton_clicked(self, *args):
        tm, iter = self.profilestv.get_selection().get_selected()

        if iter is None:
            _show_errmsg_no_profile_selected()
            return

        prfName, prfConf = tm.get_value(iter, 1), tm.get_value(iter, 2)
        if prfName == ConfigManagerStaticData.get_default_profilename():
            _forbid_default_profile_removal()
        else :
            warning = _("<b>Delete configuration profile?</b>\n\nYou are trying to remove a configuration profile. You will not be able to restore it. If you are not sure, use the 'enable|disable' functionality instead.\n\nDo you really want to delete the profile '%(name)s'?") % {'name': glib.markup_escape_text(prfName)}
            dialog = gtk.MessageDialog(type = gtk.MESSAGE_WARNING, flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons = gtk.BUTTONS_YES_NO)
            dialog.set_markup(warning)
            response = dialog.run()
            dialog.destroy()

            if response == gtk.RESPONSE_YES :
                self.logger.debug("Remove Profile '%s' configuration" % prfName)
                if os.path.exists(prfConf) :
                    os.remove(prfConf)
                self.profiles.remove(iter)

            elif response == gtk.RESPONSE_NO :
                pass

    def on_editProfileButton_clicked(self, *args):
        tm, iter = self.profilestv.get_selection().get_selected()
        if iter is None:
            _show_errmsg_no_profile_selected()
            return
        prfName, prfConf = tm.get_value(iter, 1), tm.get_value(iter, 2)
        self.logger.debug("Load Profile '%s' configuration" % prfName)

        self.conffile = prfConf
        self.on_reload_clicked()
        self.widgets["ProfileManagerDialog"].hide()

    def on_closeProfileManagerButton_clicked(self, *args):
        """
        Load the default configuration file
        """
        self.logger.debug("Load the default configuration file '%s'" % self.default_conffile)
        self.conffile = self.default_conffile
        self.on_reload_clicked()

    def on_prfEnableCB_toggled(self, *args):

        tm, iter = self.profilestv.get_selection().get_selected()
        if iter is None:
            _show_errmsg_no_profile_selected()
            return
        enable, prfName, prfConf = tm.get_value(iter, 0), tm.get_value(iter, 1), tm.get_value(iter, 2)

        if prfName == ConfigManagerStaticData.get_default_profilename():
            _forbid_default_profile_disable()
        else :
            dir, file = prfConf.rsplit(os.sep, 1)

            # rename the file 
            if enable :
                # then disable
                self.logger.debug("Disabling %s " % prfName)
                os.rename(prfConf, prfConf + "-disable")
                self.profiles.set_value(iter, 0, False)
                self.profiles.set_value(iter, 2, prfConf + "-disable")

            else :
                # enable it
                self.logger.debug("Enabling %s " % prfName)
                os.rename(prfConf, prfConf.rstrip("-disable"))
                self.profiles.set_value(iter, 0, True)
                self.profiles.set_value(iter, 2, prfConf.rstrip("-disable"))

    def on_menu_set_default_settings_activate(self, *args):
        """Signal handler which is activated when the user either selects
        the menu item 'Set default settings...' or clicks the according
        toolbar button. The method presents a message box where
        confirmation for the changes is required.
        """
        dialog = self.widgets["dialog_default_settings"]
        label = self.widgets["label_dialog_default_settings_content"]
        btn_cancel = self.widgets['btn_cancel_default_settings']

        txt = _("<big><b>Set default values for current profile?</b></big>\nThis will restore the default values for the profile currently edited: '%s'.\n\nThese predefined settings are recommended for most users. Check whether they are appropriate for your use before saving the changed configuration.") % glib.markup_escape_text(self.configman.getProfileName())

        label.set_line_wrap(True)
        label.set_markup(txt)
        misc.label_set_autowrap(label)
        btn_cancel.grab_focus()

        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_APPLY:
            self.logger.info(_("Default settings are being applied."))
            self._set_default_settings()
        elif response == gtk.RESPONSE_CANCEL or \
             response == gtk.RESPONSE_DELETE_EVENT:
            pass
        else:
            self.logger.error(_("Unexpected dialog response: %s") % response)
            raise ValueError("Unexpected dialog response: %s" % response)

    def _set_default_settings(self):
        """Sets default values (which might be considered as recommended
        values for some usecase) for the current profile.
        """
        # implementation note: the values are set in the configuration
        # manager and afterwards the according UI widgets are updated
        # with these new values.
        self.configman.set_values_to_default()
        # filesystem is not probed since we want to apply *new* values
        self._fill_widgets_from_config(probe_fs = False)


def _forbid_default_profile_removal():
    """Helper function that shows an info box which states that we are
    not able to do the given action on the default profile.    
    """
    info = _("<b>Unable to remove default profile</b>\n\nThe default profile cannot be removed. In the case you want to use just a single profile, please set up the default profile accordingly.")

    dialog = gtk.MessageDialog(type = gtk.MESSAGE_INFO,
                    flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons = gtk.BUTTONS_CLOSE)
    dialog.set_markup(info)
    dialog.run()
    dialog.destroy()


def _forbid_default_profile_disable():
    """Helper function that shows an info box which states that we are
    not able to do the given action on the default profile.    
    """
    info = _("<b>Unable to remove default profile</b>\n\nThe default profile cannot be disabled. In the case you want to use just a single profile, please set up the default profile accordingly.")

    dialog = gtk.MessageDialog(type = gtk.MESSAGE_INFO,
                    flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons = gtk.BUTTONS_CLOSE)
    dialog.set_markup(info)
    dialog.run()
    dialog.destroy()


def _notify_new_default_profile_created():
    """Helper function that shows an info box which states that
    a new default profile was created.    
    """
    info = _("<b>No backup profile found.</b>\n\nNo default profile was found. You are probably running Simple Backup for the first time. A backup profile using default values was created.\n\nPlease modify the settings according to your needs and save the configuration in order to use it.")

    dialog = gtk.MessageDialog(type = gtk.MESSAGE_INFO,
                    flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons = gtk.BUTTONS_CLOSE)
    dialog.set_markup(info)
    dialog.run()
    dialog.destroy()


def _show_errmsg_no_profile_selected():
    dialog = gtk.MessageDialog(type = gtk.MESSAGE_ERROR,
                               flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                               buttons = gtk.BUTTONS_CLOSE, message_format = _("Please select a profile."))
    dialog.run()
    dialog.destroy()


def _prepare_dirname(path):
    _res = "%s%s" % (path.rstrip(os.sep), os.sep)
    return _res


def _prepare_filename(path):
    _res = "%s" % (path.rstrip(os.sep))
    return _res


def _escape_path(path):
    _enc_res = path.replace("=", "\\x3d")
    return _enc_res


def main(argv):
    window = SBconfigGTK()
    window.show()
    gtk.main()
    log.shutdown_logging()
