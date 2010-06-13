#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# Authors :
#    Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>
#   Jean-Peer Lorenz <peer.loz@gmx.net>

import re
import subprocess
import os
import types

import gobject
import gtk
import gtk.gdk

from gettext import gettext as _

# project imports
from nssbackup.pkginfo import Infos
from nssbackup.util import log
from nssbackup.plugins import PluginManager
from nssbackup.managers.FuseFAM import FuseFAM
#from nssbackup.managers.ConfigManager import get_default_conffile_fullpath
from nssbackup.managers.ConfigManager import ConfigManagerStaticData
from nssbackup.util.log import LogFactory
from nssbackup.util.exceptions import SBException
from nssbackup.managers.ConfigManager import ConfigManager, ConfigurationFileHandler
from nssbackup.ui.GladeGnomeApp import GladeGnomeApp
from gettext import gettext as _
import nssbackup.util as Util
from nssbackup.ui.GladeGnomeApp import GladeGnomeApp
from nssbackup.ui import misc


class SBconfigGTK(GladeGnomeApp):
    """
    
    @todo: Unify displaying of error messages/dialog boxes!
    @todo: Strictly separate UI from core. Don't set defaults from the UI.
    @todo: The result of 'os.getuid' should be retrieved during the
       initialization process and stored in a member attribute, so
       we don't need to use operation system call over and over!
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
            self.configman = ConfigManager(self.default_conffile)
            # hack to get rid of schedule settings in non-admin profiles
            # we just remove existing schedules from the config files
            # and don't allow new settings by disabling the schedule page
            if os.geteuid() != 0:
                self.configman.remove_schedule()
                self.configman.saveConf()
            # end of hack
            self.orig_configman = ConfigManager(self.default_conffile)
        else :
            self.configman = ConfigManager()        
            self.orig_configman = None
        
        self.logger = LogFactory.getLogger()
    
        self._init_ui()
        
        # hide the schedule tab if not root
        if os.geteuid() != 0:
            self.__enable_schedule_page(enable=False)
            self.widgets['label_schedule_page'].set_tooltip_text(\
            _('Scheduled backups are available for Administrator users only.'))

        # Initiate all data structures
        # Paths to be included or excluded
        self.include = gtk.ListStore( str )
        self.includetv = self.widgets["includetv"]
        self.includetv.set_model( self.include )
        cell = gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', self.cell_edited_callback, (self.include, "dirconfig", 1))
        column = gtk.TreeViewColumn(_('Name'), cell, text=0)
        self.includetv.append_column(column)

        self.ex_paths = gtk.ListStore( str )
        self.ex_pathstv = self.widgets["ex_pathstv"]
        self.ex_pathstv.set_model( self.ex_paths )
        cell1 = gtk.CellRendererText()
        cell1.set_property('editable', True)
        cell1.connect('edited', self.cell_edited_callback, (self.ex_paths, "dirconfig", 0))
        column1 = gtk.TreeViewColumn(_('Name'), cell1, text=0)
        self.ex_pathstv.append_column(column1)

        # Excluded file types and general regular expressions
        self.ex_ftype = gtk.ListStore( str, str )
        self.ex_ftypetv = self.widgets["ex_ftypetv"]
        self.ex_ftypetv.set_model( self.ex_ftype )
        cell3 = gtk.CellRendererText()
        column3 = gtk.TreeViewColumn(_('File Type'), cell3, text=0)
        cell2 = gtk.CellRendererText()
        column2 = gtk.TreeViewColumn('Ext.', cell2, text=1)
        self.ex_ftypetv.append_column(column3)
        self.ex_ftypetv.append_column(column2)

        # set label of default target
        _default_target = str(self.configman.get_target_default())
        self.widgets['label_default_target'].set_text(_default_target)
        
        self.ex_regex = gtk.ListStore( str )
        self.ex_regextv = self.widgets["ex_regextv"]
        self.ex_regextv.set_model( self.ex_regex )
        cell4 = gtk.CellRendererText()
        cell4.set_property('editable', True)
        cell4.connect('edited', self.cell_regex_edited_callback)
        column4 = gtk.TreeViewColumn('Name', cell4, text=0)
        self.ex_regextv.append_column(column4)
        
        self.remoteinc = gtk.ListStore( str )
        self.rem_includetv = self.widgets["remote_includetv"]
        self.rem_includetv.set_model( self.remoteinc )
        cell = gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', self.cell_remoteinc_edited_callback, (self.remoteinc, "dirconfig", 1))
        column = gtk.TreeViewColumn(_('Name'), cell, text=0)
        self.rem_includetv.append_column(column)
                            
        # Profile Manager
        # [ enable , profilename, cfPath ]
        self.profiles = gtk.ListStore( bool, str, str )
        # add the default profile and disable any modification to it
        self.profiles.append([True,
            ConfigManagerStaticData.get_default_profilename(),
            self.__configFileHandler.get_default_conffile_fullpath()])
        for i,v in self.configman.getProfiles().iteritems() :
            self.profiles.append( [v[1], i, v[0]] )
        self.profilestv = self.widgets['profilesListTreeView']
        self.profilestv.set_model(self.profiles )
        
        cell8,cell9 = gtk.CellRendererToggle(), gtk.CellRendererText()
        cell8.set_active(True)
        cell8.connect("toggled", self.on_prfEnableCB_toggled)
        
        enableCBColumn = gtk.TreeViewColumn(_("Enable"), cell8, active=0 ) 
        prfNameColumn = gtk.TreeViewColumn(_("Profile Name"), cell9, text=1 )
        
        self.profilestv.append_column(enableCBColumn)
        self.profilestv.append_column(prfNameColumn)
        
        # The split size coices
        self.splitSizeLS = gtk.ListStore( str, int )
        values = []
        splitsize_dict = ConfigManagerStaticData.get_splitsize_dict()
        for k in splitsize_dict.keys() :
            values.append(k)
        values.sort()
        
        for k in values :
            self.splitSizeLS.append([splitsize_dict[k],k])
        self.widgets['splitsizeCB'].set_model(self.splitSizeLS)
        cell = gtk.CellRendererText()
        self.widgets['splitsizeCB'].pack_start(cell, True)
        self.widgets['splitsizeCB'].add_attribute(cell, 'text', 0) 
            
        self._fill_widgets_from_config(probe_fs = True)

    def _init_ui(self):        
        filename = Util.get_resource_file('nssbackup-config.glade')        
        widget_list = [
            'nssbackupConfApp',
            'toolbar',
            'askSaveDialog',
            'remote_inc_dialog',
            'remote_inc_entry',
            'fusecheckbutton',
            'remote_inc_okbutton',
            'pluginscombobox',
            'fusehelplabel',
            'regexdialog',
            'ftypedialog',
            'dialog-vbox4',
            'remote_inc_entry',
            'vbox18',
            'ftype_st',
            'ftype_box',
            'hbox25',
            'ftype_custom',
            'ftype_custom_ex',
            'cancelbutton',
            'okbutton',
            'dialog-vbox5',
            'vbox19',
            'regex_box',
            'cancelbutton2',
            'okbutton2',
            'statusBar',
            'vbox17',
            'save',
            'save_as',
            'saveButton',
            'exit',
            'imagemenuitem6',
            'imagemenuitem7',
            'imagemenuitem8',
            'imagemenuitem9',
            'about',
            'vbox1',
            'notebook',
#
# general/main page
            'label_general_page',
            'vbox_general_page',
            'cformat',
            'splitsizeCB',
            'splitsizeSB',
            'splitsizevbox',
            'label_splitsize_custom',
#
            'vbox3',
            'scrolledwindow1',
            'includetv',
            'inc_addfile',
            'hbox4',
            'inc_adddir',
            'hbox5',
            'inc_del',
            'remote_includetv',
            'remote_inc_add',
            'remote_inc_del',
            'test_remote',
            'notebook2',
            'vbox4',
            'scrolledwindow2',
            'ex_pathstv',
            'ex_addfile1',
            'hbox6',
            'ex_adddir',
            'hbox7',
            'ex_delpath',
            'vbox5',
            'scrolledwindow3',
            'ex_ftypetv',
            'ex_addftype',
            'ex_delftype',
            'vbox6',
            'scrolledwindow4',
            'ex_regextv',
            'ex_addregex',
            'ex_delregex',
            'vbox7',
            'hbox8',
            'ex_max',
            'ex_maxsize',
            'vbox8',
            'dest1',
            'dest2',
            'label_default_target',
            'hbox9',
            'dest_localpath',
            'dest3',
            'hbox10',
            'dest_remote',
            'dest_remotetest',
            'dest_remote_light',
            'hbox11',
            'dest_unusable',
#
#            schedule page
            'label_schedule_page',
            'vbox_schedule_page',
            'table_schedule',
            'rdbtn_no_schedule',
            'rdbtn_simple_schedule',
            'rdbtn_custom_schedule',
            'label_simple_schedule_freq',
            'label_custom_cronline',
            'txtfld_custom_cronline',
            'cmbbx_simple_schedule_freq',
            'lnkbtn_help_schedule',
            'hbox_schedule_footer',
            'hbox_schedule_infotext',
            'img_schedule_infotext',
            'label_schedule_infotext',
#
            'time_maxinc',
            'purgevbox',
            'purgecheckbox',
            'hbox16',
            'purgeradiobutton',
            'purgedays',
            'purgelabel',
            'hbox17',
            'logpurgeradiobutton',
            'purgelabel2',
            'hbox18',
            'reportvbox',
            'hbox19',
            'table2',
            'loglevelcombobox',
            'logfilechooser',
            'hbox20',
            'vbox11',
            'vbox12',
            'table3',
            'smtpport',
            'smtpserver',
            'smtpto',
            'smtpfrom',
            'hbox21',
            'testMailButton',
            'vbox13',
            'vbox14',
            'smtplogincheckbox',
            'smtplogininfo',
            'smtppassword',
            'smtplogin',
            'vbox15',
            'TLScheckbutton',
            'TLSinfos',
            'TLSradiobutton',
            'SSLradiobutton',
            'crtfilechooser',
            'keyfilechooser',
            'label_certificate',
            'label_key',
#
            'pluginscombobox',
            'ProfileManagerDialog',
            'profilesListTreeView',
            'addProfileButton',
            'removeProfileButton',
            'editProfileButton',
            'closeProfileManagerButton',
            'askNewPrfNameDialog',
            'enableNewPrfCB',
            'newPrfNameEntry',
            'followlinks',
#
            'dialog_default_settings',
            'label_dialog_default_settings_content',
            'btn_set_default_settings',
            'btn_cancel_default_settings'
            ]

        handlers = [
            'on_ftype_toggled',
            'on_ftype_st_box_changed',
            'on_ftype_custom_ex_changed',
            'on_save_activate',
            'on_save_as_activate',
            'on_exit_activate',
            'on_prfManager_activate',
            'on_menu_about_activate',
            'on_menu_help_activate',
            'on_reload_clicked',
            'on_save_clicked',
            'on_backup_clicked',
            'on_cformat_changed',
            'on_splitsizeCB_changed',
            'on_splitsizeSB_value_changed',
            'on_inc_addfile_clicked',
            'on_inc_adddir_clicked',
            'on_inc_del_clicked',
            'on_remote_inc_add_clicked',
            'on_remote_inc_del_clicked',
            'on_test_remote_clicked',
            'on_ex_addfile_clicked',
            'on_ex_adddir_clicked',
            'on_ex_delpath_clicked',
            'on_ex_addftype_clicked',
            'on_ex_delftype_clicked',
            'on_ex_addregex_clicked',
            'on_ex_delregex_clicked',
            'on_ex_max_toggled',
            'on_ex_maxsize_changed',
            'on_dest1_toggled',
            'on_dest_localpath_selection_changed',
            'on_dest_remote_changed',
            'on_dest_remotetest_clicked',
#            
#            scheduling
            'on_cmbbx_simple_schedule_freq_changed',
            'on_rdbtn_schedule_toggled',
            'on_txtfld_custom_cronline_changed',
#
            'on_time_maxinc_changed',
            'on_purgecheckbox_toggled',
            'on_purgeradiobutton_toggled',
            'on_purgedays_changed',
            'on_logfilechooser_selection_changed',
            'on_loglevelcombobox_changed',
            'on_smtpfrom_changed',
            'on_smtpto_changed',
            'on_smtpserver_changed',
            'on_smtpport_changed',
            'on_testMailButton_clicked',
            'on_smtplogincheckbox_toggled',
            'on_smtplogin_changed',
            'on_smtppassword_changed',
            'on_TLScheckbutton_toggled',
            'on_TLSradiobutton_toggled',
            'on_crtfilechooser_selection_changed',
            'on_keyfilechooser_selection_changed',
            'on_pluginscombobox_changed',
            'on_fusecheckbutton_clicked',
            'on_addProfileButton_clicked',
            'on_removeProfileButton_clicked',
            'on_editProfileButton_clicked',
            'on_closeProfileManagerButton_clicked',
            'on_includetv_key_press_event',
            'on_remote_includetv_key_press_event',
            'on_ex_pathstv_key_press_event',
            'on_ex_ftypetv_key_press_event',
            'on_ex_regextv_key_press_event',
            'on_followlinks_toggled',
#
            'on_menu_set_default_settings_activate',
            
            'on_exit_activate',
            'on_nssbackupConfApp_delete_event',
            'on_nssbackupConfApp_destroy'
            ]

        top_window = 'nssbackupConfApp'
        GladeGnomeApp.__init__(self, "NSsbackup", "0.2", filename, top_window,
                                                        widget_list, handlers)
        self.widgets['nssbackupConfApp'].set_icon_from_file(Util.get_resource_file("nssbackup-conf.png"))


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
        if self.configman.has_section(_section) :
            for _item, _value in self.configman.items(_section):
                if _value == "1":
                    self.include.append([_item])
                elif _value == "0":
                    self.ex_paths.append([_item])

    def __fill_remotedir_widgets_from_config(self):
        """Fills the remote directory include tab according to
        the values found in the current configuration.
        """
        _section = "dirconfig"
        _option = "remote"
        self.remoteinc.clear()
        if self.configman.has_option(_section, _option) :
            for _itm, _val in self.configman.get(_section, _option).iteritems():
                if _val == "1":
                    self.remoteinc.append([_itm])
                elif _val == "0":
                    print ("TODO: add a remote ex widget")

    def __fill_regex_widgets_from_config(self):
        # regexp excludes
        _known_ftypes_dict = ConfigManagerStaticData.get_known_ftypes_dict()
        _invalid_regex_found = False
        _invalid_regex = ""
        self.ex_ftype.clear()
        self.ex_regex.clear()
        if self.configman.has_option("exclude", "regex") :
            r = self.configman.get( "exclude", "regex" )
            if not Util.is_empty_regexp(r):
                list = str(r).split(",")
                for i in list:
# Bugfix LP #258542 
                    if re.match(r"\\\.\w+\$", i):
                        _ftype = i[2:len(i)-1]
                        if _ftype in _known_ftypes_dict:
                            self.ex_ftype.append([_known_ftypes_dict[_ftype], _ftype])

                        else:
                            self.ex_ftype.append([_("Custom"), _ftype])
                    else:
                        if (not Util.is_empty_regexp(i)) and Util.is_valid_regexp(i):
                            self.ex_regex.append([i])
                        else:
                            r = Util.remove_conf_entry(r, i)
                            self.logger.warning(_("Invalid or empty regular expression ('%s') found in configuration. Removed.") % i )
                            _invalid_regex_found = True
                            _invalid_regex = "%s, %s" % (_invalid_regex, i)

        if _invalid_regex_found:
            self.configman.set( "exclude", "regex", r )
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
            self.widgets["ex_maxsize"].set_value(_maxsize/(1024*1024))
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
        if self.configman.has_option("general", "format") :
            cformatOpt = self.configman.get("general", "format") 
            if cformatOpt not in cformats:
                cformatOpt = 'gzip'            
            cformatIndex = cformats.index(cformatOpt)
            self.widgets["cformat"].set_active(cformatIndex)
            
    def __fill_purge_widgets_from_config(self):
        """Sets the UI elements for 'purge' to the value
        specified in configuration.
        """
        if self.configman.has_option("general", "purge") :
            self.logger.debug("Setting purge")
            if self.configman.get("general", "purge") == "log" :
                self.widgets['logpurgeradiobutton'].set_active(True)
            else:
                try : 
                    purge = int(self.configman.get("general", "purge"))
                except Exception,e:
                    self.logger.error("Purge value '%s' is invalid: '%s'" \
                                % (self.configman.get("general", "purge"), e))    
                    purge = 30
                self.widgets['purgedays'].set_text(str(purge))
                self.widgets['purgeradiobutton'].set_active(True)
                self.widgets["purgedays"].set_sensitive( True )
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
            self.widgets["time_maxinc"].set_value( \
                            int(self.configman.get("general", "maxincrement")))
            
    def __fill_log_widgets_from_config(self):
        """Sets the UI elements for 'log' to the value
        specified in configuration.
        """
        if not self.configman.has_option("log", "level"):
            raise ValueError("No option 'loglevel' found.")
        
        loglevel = self.configman.get("log", "level")
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

        if os.geteuid() == 0 and self.configman.is_default_profile():
            self.__enable_schedule_page(enable=True)
            
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
            self.__enable_schedule_page(enable=False)
            
    def __fill_splitsize_widgets_from_config(self):
        if self.configman.has_option("general", "splitsize") :
            model = self.widgets["splitsizeCB"].get_model()
            custom = True
            for i in range(0, len(model)) :
                if model[i][1] == int(self.configman.get("general",
                                                        "splitsize")) / 1024:
                    self.widgets["splitsizeCB"].set_active(i)
                    self.__enable_splitsize_custom_option(enable=False)
                    custom = False
            if custom:
                # NOTE: if we don't do this is this order, the handler
                #        on splitsizeCB will overide splitsizeSB value
                self.widgets["splitsizeSB"].set_value(\
                        int(self.configman.get("general", "splitsize")) / 1024)
                self.widgets["splitsizeCB"].set_active(0)

    def __fill_destination_widgets(self):
        """Local helper function which fills the UI widgets related to
        the backup target (i.e. destination).
        """
        if self.configman.has_option("general", "target" ) :
            ctarget = self.configman.get("general", "target" )
            if ctarget.startswith(os.sep) :
                if self.__is_target_set_to_default(ctarget):
                    self.__set_target_option("default")
                else:
                    if not os.path.exists(ctarget):
                        self.__set_config_target_to_default()
                        self.__set_target_option("default")
                        
                        _sec_msg = _("Please make sure the missing directory exists (e.g. by mounting an external disk) or change the specified target to an existing one.")
                        _message_str = _("Backup target does not exist.\n\nAttention: The target will be set to the default value. Check this on the destination settings page before saving the configuration.")
                        _headline_str = \
                        _("Unable to open backup target")

                        gobject.idle_add( misc.show_errdialog,
                                          _message_str,
                                          self.__get_application_widget(),
                                          _headline_str, _sec_msg )
                        return
                        
                    self.__set_target_option("local")
                    self.__set_target_value("local", ctarget)
            else :
                self.__set_target_option("remote")
                self.__set_target_value("remote", ctarget)
        else:
            self.__set_config_target_to_default()
            # target set to default if no config option exists
            self.__set_target_option("default")
        
    def _fill_widgets_from_config(self, probe_fs):
        """Prefill the GTK window with config infos.
        
        @param probe_fs: Flag whether to probe the filesystem for schedule info
        
        @todo: Opening of directories (e.g. target) must be unified over all
               modules that use such functionality!
        """
        if not isinstance(probe_fs, types.BooleanType):
            raise TypeError("Given parameter must be of boolean type. "\
                            "Got %s instead." % (type(probe_fs)))

        # General
        self.__fill_max_inc_widgets_from_config()        
        self.__fill_compression_widgets_from_config()
        self.__fill_splitsize_widgets_from_config()
        
        # dirconfig and excludes
        self.__fill_dir_widgets_from_config()
        self.__fill_remotedir_widgets_from_config()
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
        
#        self.__set_default_focus()
        self.isConfigChanged()

    def __fill_statusbar_from_config(self):
        """Sets the profile name and the user mode.
        """
        stattxt = _("Current profile: %s") % self.configman.getProfileName()
        if os.geteuid() == 0:
            stattxt = _("%s   (Administrator mode)") % stattxt
        self.widgets['statusBar'].push(stattxt)
        
#    def __set_default_focus(self):
#        self.widgets['label_general_page'].grab_focus()
        
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
        def __enable_default_target(enable = True):
            """The widgets within the 'Destination' page are
            enabled/disabled/set according to default setting.
            """
            pass
        
        def __enable_local_target(enable = True):
            """The widgets within the 'Destination' page are
            enabled/disabled/set according to the given local target directory.
            """
            self.widgets["dest_localpath"].set_sensitive(enable)            
            
        def __enable_remote_target(enable = True):
            """The widgets within the 'Destination' page are
            enabled/disabled/set according to the given remote target.
            """
            self.widgets["dest_remote_light"].set_sensitive(enable)
            self.widgets["dest_remote"].set_sensitive(enable)
            self.widgets["dest_remotetest"].set_sensitive(enable)

        if option == "default":
            __enable_default_target(enable=True)
            __enable_local_target(enable=False)
            __enable_remote_target(enable=False)
        elif option == "local":
            __enable_default_target(enable=False)
            __enable_local_target(enable=True)
            __enable_remote_target(enable=False)
        elif option == "remote":
            __enable_default_target(enable=False)
            __enable_local_target(enable=False)
            __enable_remote_target(enable=True)
        else:
            raise ValueError("Unknown target option given.")

    def __set_target_option(self, option):
        """Selects resp. sets the given choice for backup target. Possible
        values are 'default', 'local', and 'remote'.
        """
        self.__enable_target_option(option)
        twidget = None
        if option == "default":
            twidget = self.widgets["dest1"]
        elif option == "local":
            twidget = self.widgets["dest2"]
        elif option == "remote":
            twidget = self.widgets["dest3"]
        else:
            raise ValueError("Unknown target option given.")
        twidget.set_active(True)
        twidget.grab_focus()
        
    def __set_target_value(self, option, value):
        """Sets the destination widget according to the given option. Valid
        options are: 'default', 'local', and 'remote'. In the case of the
        default option, the given value is ignored (since the default
        is used). 
        """
        if option == "default":
            pass
        elif option == "local":
            self.widgets["dest_localpath"].set_current_folder(value)
        elif option == "remote":
            self.widgets["dest_remote"].set_text(value)
        else:
            raise ValueError("Unknown target option given.")
    
    def already_inc (self, configlist, toInclude):
        """configlist is like self.conf.items( "dirconfig" )
         
        @return: True if the dir is already included, False if not
        """
        for i,v in configlist :
            if v=="1" and i == toInclude :
                # the chosen item match an included one 
                dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Already included item !"))
                dialog.run()
                dialog.destroy()
                return True
        # No match found
        return False
    
    def already_ex (self, configlist, toExclude):
        """configlist is like self.conf.items( "dirconfig" )
        
        @return: True if the dir is already excluded, False if not
        """
        for i,v in configlist :
            if v=="0" and i == toExclude :
                # the chosen item match an included one 
                dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Already excluded item !"))
                dialog.run()
                dialog.destroy()
                return True
        # No match found
        return False
    
    def cell_remoteinc_edited_callback(self, cell, path, new_text, data):
        # Check if new path is empty
        if (new_text == None) or (new_text == ""):
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                        flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons=gtk.BUTTONS_CLOSE,
                        message_format=_("Empty filename or path. Please enter a valid filename or path."))
            dialog.run()
            dialog.destroy()
            return
                
        model, section, value = data
        self.configman.remove_option(section, model[path][0])
        model[path][0] = new_text
        self.configman.set(section, "remote", {new_text: value})
        self.isConfigChanged()
    
    def cell_regex_edited_callback(self, cell, path, new_text):
        # Check if new path is empty
        if Util.is_empty_regexp(new_text):
            misc.show_errdialog(message_str = \
                _("Empty expression. Please enter a valid regular expression."))
        else:
            if Util.is_valid_regexp(new_text):                
                # Remove old expression and add the new one
                value = self.ex_regex[path][0]
                r = self.configman.get( "exclude", "regex" )
                r = Util.remove_conf_entry(r, value)
                r = r + r"," + new_text.strip()
                r = r.strip(",")
                self.configman.set( "exclude", "regex", r )
                self.ex_regex[path][0] = new_text
                self.isConfigChanged()
            else:
                misc.show_errdialog(message_str = \
                                _("Provided regular expression is not valid."))        

    def cell_edited_callback(self, cell, path, new_text, data):
        # Check if new path is empty
        if (new_text == None) or (new_text == ""):
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                        flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons=gtk.BUTTONS_CLOSE,
                        message_format=_("Empty filename or path. Please enter a valid filename or path."))
            dialog.run()
            dialog.destroy()
            return
        # Check if new path exists and asks the user if path does not exists
        if not os.path.exists(new_text):
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,
                        flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons=gtk.BUTTONS_YES_NO,
                        message_format=_("It seems the path you entered does not exists. Do you want to add this incorrect path?"))
            response = dialog.run()
            dialog.destroy()
            if response == gtk.RESPONSE_NO:
                return
                
        model, section, value = data
        self.configman.remove_option(section, model[path][0])
        model[path][0] = new_text
        self.configman.set(section, new_text, value)
        self.isConfigChanged()
        
    def on_ftype_toggled(self, *args):
        if self.widgets["ftype_st"].get_active():
            self.widgets["ftype_box"].set_sensitive( True )
            self.widgets["ftype_custom_ex"].set_sensitive( False )
        elif self.widgets["ftype_custom"].get_active():
            self.widgets["ftype_box"].set_sensitive( False )
            self.widgets["ftype_custom_ex"].set_sensitive( True )

    def on_ftype_st_box_changed(self, *args):
        print("TODO: on_ftype_st_box_changed")
        pass

    def on_save_activate(self, *args):
        self.on_save_clicked()

    def on_save_as_activate(self, *args):
        dialog = gtk.FileChooserDialog(title=_("Save configuration as..."),
                                parent=self.__get_application_widget(),
                                action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        response = dialog.run()
        if response == gtk.RESPONSE_OK :
            self.configman.saveConf(dialog.get_filename())
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()

    def on_menu_help_activate(self, button):
        misc.open_uri("ghelp:nssbackup")

    def on_menu_about_activate(self, *args):
        about = gtk.AboutDialog()
        about.set_name(Infos.NAME)
        about.set_version(Infos.VERSION)
        about.set_comments(Infos.DESCRIPTION)
        about.set_transient_for(self.widgets["nssbackupConfApp"])
        about.set_copyright(Infos.COPYRIGHT)
        about.set_translator_credits(Infos.TRANSLATORS)
        about.set_authors(Infos.AUTHORS)
        about.set_website(Infos.WEBSITE)
        about.set_logo(gtk.gdk.pixbuf_new_from_file(Util.get_resource_file("nssbackup-conf.png")))
        about.run()
        about.destroy()

    def on_reload_clicked(self, *args):
        self.configman = ConfigManager(self.conffile)
        # hack to get rid of schedule settings in non-default profiles
        # we just remove existing schedules from the non-default config files
        # and don't allow new settings by disabling the schedule page
        if not self.configman.is_default_profile():
            self.configman.remove_schedule()
            self.configman.saveConf()
        # end of hack
        self.orig_configman = ConfigManager(self.conffile)
        self._fill_widgets_from_config(probe_fs = True)
        self.isConfigChanged()
        self.logger.debug("Config '%s' loaded" % self.conffile)

    def on_save_clicked(self, *args):
        self.logger.debug("Saving Config")
        self.configman.saveConf()
        self.conffile=self.configman.conffile
        if not self.default_conffile:
            self.default_conffile = self.conffile
        self.orig_configman = ConfigManager(self.configman.conffile)
        self.isConfigChanged()
        
    def on_backup_clicked(self, *args):
        cancelled = self.ask_save_config()
        if not cancelled:
            try :
                pid = subprocess.Popen(["nssbackupd"]).pid
                
                dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | \
                                    gtk.DIALOG_DESTROY_WITH_PARENT,
                                    buttons=gtk.BUTTONS_CLOSE,
                                    message_format=_("A backup run is initiated in the background.\nThe process id is: %s.") % str(pid))
                dialog.run()
                dialog.destroy()
            except Exception, e:
                dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
                dialog.run()
                dialog.destroy()
                raise e

    def on_cformat_changed(self, *args):
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
    
    def on_splitsizeCB_changed(self, *args):
        """
        """
        model = self.widgets["splitsizeCB"].get_model()
        label,value = model[self.widgets["splitsizeCB"].get_active()]
        if value != -1 :
            self.__enable_splitsize_custom_option(enable=False)
            self.configman.set("general", "splitsize", value*1024)
        else :
            # activate Spin box
            self.__enable_splitsize_custom_option(enable=True)
            val = self.widgets['splitsizeSB'].get_value_as_int()
            self.configman.set("general", "splitsize", val * 1024)
        self.isConfigChanged()
            
    def on_splitsizeSB_value_changed(self, *args):
        """
        """
        val = int(self.widgets['splitsizeSB'].get_value())
        self.configman.set("general", "splitsize", val* 1024)
        self.isConfigChanged()
    
    def on_inc_addfile_clicked(self, *args):
        self.__check_for_section("dirconfig")        
        dialog = gtk.FileChooserDialog(title=_("Include file..."),
                                parent=self.__get_application_widget(),
                                action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        filter = gtk.FileFilter()
        filter.set_name(_("All files"))
        filter.add_pattern("*")
        dialog.add_filter(filter)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK and not self.already_inc(self.configman.items( "dirconfig" ),dialog.get_filename()):
            self.include.append( [dialog.get_filename()] )
            self.configman.set( "dirconfig", dialog.get_filename(), "1" )
            self.isConfigChanged()
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()

    def __check_for_section(self, section):
        if not self.configman.has_section(section):
            self.configman.add_section(section)
            
    def on_inc_adddir_clicked(self, *args):
        self.__check_for_section("dirconfig")
        dialog = gtk.FileChooserDialog(title=_("Include folder..."),
                                parent=self.__get_application_widget(),
                                action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                          gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK and not self.already_inc(self.configman.items( "dirconfig" ),dialog.get_filename()+"/"):
            self.include.append( [dialog.get_filename()+"/"] )
            self.configman.set( "dirconfig", dialog.get_filename()+"/", "1" )
            self.isConfigChanged()
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()

    def on_inc_del_clicked(self, *args):
        self.__check_for_section("dirconfig")
        (store, iter) = self.includetv.get_selection().get_selected()
        if store and iter:
            value = store.get_value( iter, 0 )
            self.configman.remove_option( "dirconfig", value )
            self.isConfigChanged()
            store.remove( iter )

    def on_remote_inc_add_clicked(self,*args):
        self.__check_for_section("dirconfig")
        global plugin_manager
        question = self.widgets['remote_inc_dialog']
        #add the plugin list in the dialog
        if not self.plugin_manager :
            self.plugin_manager = PluginManager()
        plist = self.plugin_manager.getPlugins()
        p_comboList = gtk.ListStore( str )
        plistCB = self.widgets['pluginscombobox']
        plistCB.set_model(p_comboList)
        for pname in plist.iterkeys() :
            p_comboList.append([pname])
        
        cell = gtk.CellRendererText()
        plistCB.pack_start(cell)
        plistCB.add_attribute(cell,'text',0)
        plistCB.set_active(0)
        
        response = question.run()
        question.hide()
        if response == gtk.RESPONSE_OK:
            entry = self.widgets["remote_inc_entry"].get_text()
            self.logger.debug("Entry : '%s'"% entry)
            self.remoteinc.append( [entry] )
            self.configman.set( "dirconfig", "remote", {entry:1} )
            self.isConfigChanged()
            self.logger.debug("Entry in dirconf:'%s' " % self.configman.get("dirconfig", "remote"))
        elif response == gtk.RESPONSE_CANCEL:
            pass
        else : 
            self.logger.debug("Response : '%s'" % str(response))
    
    def on_pluginscombobox_changed(self, *args):
        plist = self.plugin_manager.getPlugins()
        pname = self.widgets['pluginscombobox'].get_active_text()
        plugin = plist[pname]()
        # update the help label
        try :
            self.widgets['fusehelplabel'].set_text(plugin.getdoc())
        except SBException, e :
            self.widgets['fusehelplabel'].set_text(str(e))

    def on_fusecheckbutton_clicked(self, *args):
        entry = self.widgets["remote_inc_entry"].get_text()
        plist = self.plugin_manager.getPlugins()
        pname = self.widgets['pluginscombobox'].get_active_text()
        plugin = plist[pname]()
        # update the help label
        try :
            if plugin.matchScheme(entry) :
                dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format="Test Succeeded !")
                dialog.run()
                dialog.destroy()
            else :
                dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format="Test failed, the entry doesn't match the schema")
                dialog.run()
                dialog.destroy()
        except Exception, e :
            dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
            dialog.run()
            dialog.destroy()

    def on_remote_inc_del_clicked(self,*args):
        self.__check_for_section("dirconfig")
        (store, iter) = self.rem_includetv.get_selection().get_selected()
        if store and iter:
            value = store.get_value( iter, 0 )
            self.configman.remove_option( "dirconfig", value )
            self.isConfigChanged()
            store.remove( iter )
            self.logger.debug("Entry in dirconf:'%s' " % self.configman.get("dirconfig", "remote"))
    
    def on_test_remote_clicked(self,*args):
        if not self.plugin_manager : 
            self.plugin_manager = PluginManager()
        n = 0
        _fusefam = FuseFAM()
        for row in self.remoteinc:            
            try :
                if not _fusefam.testFusePlugins(row[0]) :
                    dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, 
                                            message_format=_("Test on '%s' didn't succeed!") % row[0])
                    dialog.run()
                    dialog.destroy()
                else :
                    n = n +1
            except Exception, e: 
                    dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
                    dialog.run()
                    dialog.destroy()
        if n == len(self.remoteinc) :
            dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Test was successful."))
            dialog.run()
            dialog.destroy()
        else :
            dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, 
                                            message_format=_("'%d' test(s) didn't succeed !") % (len(self.remoteinc)- n))
            dialog.run()
            dialog.destroy()

    def on_ex_addfile_clicked(self, *args):
        self.__check_for_section("dirconfig")
        dialog = gtk.FileChooserDialog(title=_("Exclude file..."),
                                parent=self.__get_application_widget(),
                                action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        filter = gtk.FileFilter()
        filter.set_name(_("All files"))
        filter.add_pattern("*")
        dialog.add_filter(filter)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK and not self.already_inc(self.configman.items( "dirconfig" ),dialog.get_filename()):
            self.ex_paths.append( [dialog.get_filename()] )
            self.configman.set( "dirconfig", dialog.get_filename(), "0" )
            self.isConfigChanged()
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()

    def on_ex_adddir_clicked(self, *args):
        self.__check_for_section("dirconfig")
        dialog = gtk.FileChooserDialog(title=_("Exclude folder..."),
                                parent=self.__get_application_widget(),
                                action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK and not self.already_ex(self.configman.items( "dirconfig" ),dialog.get_filename()+"/"):
            self.ex_paths.append( [dialog.get_filename()+"/"] )
            self.configman.set( "dirconfig", dialog.get_filename()+"/", "0" )
            self.isConfigChanged()
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()

    def on_ex_delpath_clicked(self, *args):
        self.__check_for_section("dirconfig")
        (store, iter) = self.ex_pathstv.get_selection().get_selected()
        if store and iter:
            value = store.get_value( iter, 0 )
            self.configman.remove_option( "dirconfig", value )
            self.isConfigChanged()
            store.remove( iter )

    def __is_target_set_to_default(self, atarget):
        """Checks if the given target directory is equal to the
        default settings.

        @rtype: Boolean
        
        @todo: Use functions from ConfigManager to proceed the check in
                a consistent manner.
        """
        _reslt = False
        _def_target = self.configman.get_target_default()
        if (os.getuid() == 0 and atarget == _def_target) or\
           (os.getuid() != 0 and atarget == _def_target):
            _reslt = True
        return _reslt

    def __set_config_target_to_default(self):
        """The target option within the configuration is set to the defaults.
                        
        @todo: We must ensure the default paths really do exist.
        """
        self.configman.set_target_to_default()
        self.isConfigChanged()

    def on_dest1_toggled(self, *args):
        if self.widgets["dest1"].get_active():
            self.__enable_target_option("default")
            self.widgets["dest_unusable"].hide()
            self.__set_config_target_to_default()
            
        elif self.widgets["dest2"].get_active():
            self.__enable_target_option("local")
            self.on_dest_localpath_selection_changed()
            
        elif self.widgets["dest3"].get_active():
            self.__enable_target_option("remote")
            self.on_dest_remote_changed()
            
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
            __enable_no_scheduling(enable=True)
            __enable_simple_scheduling(enable=False)
            __enable_custom_scheduling(enable=False)
        elif option == "simple":
            __enable_no_scheduling(enable=False)
            __enable_simple_scheduling(enable=True)
            __enable_custom_scheduling(enable=False)
        elif option == "custom":
            __enable_no_scheduling(enable=False)
            __enable_simple_scheduling(enable=False)
            __enable_custom_scheduling(enable=True)
        else:
            raise ValueError("Unknown schedule option given.")
        
    def __set_schedule_option(self, option):
        self.__enable_schedule_option(option)
        if option == "no":
            self.widgets["rdbtn_no_schedule"].set_active(is_active=True)
        elif option == "simple":
            self.widgets["rdbtn_simple_schedule"].set_active(is_active=True)
        elif option == "custom":
            self.widgets["rdbtn_custom_schedule"].set_active(is_active=True)
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
        print "WE MUST CHECK THE INPUT!"
#TODO: WE MUST CHECK THE INPUT!
        self.configman.setSchedule(1, _cronline)
        self.isConfigChanged()
        self.logger.debug("Scheduling is: %s" % str(self.configman.get_schedule()))

    def on_time_maxinc_changed(self,*args):
        """Adds a changed value for 'maximum increment days' to the
        configuration.
        """
        self.configman.set("general", "maxincrement",
                            int(self.widgets["time_maxinc"].get_value())) 
        self.isConfigChanged()
    
    def __enable_purge_options(self, enable=True):
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
            self.configman.remove_option( "general", "purge")
            self.isConfigChanged()

    def on_purgeradiobutton_toggled(self, *args):
        if self.widgets["purgeradiobutton"].get_active():
            self.widgets["purgedays"].set_sensitive( True )
            try: i = int(self.widgets["purgedays"].get_text())
            except: i = -1
            if not ( i>0 and i<10000 ):    i=30
            self.widgets["purgedays"].set_text(str(i))
            self.configman.set( "general", "purge", str(i) )
            self.isConfigChanged()
        elif self.widgets["logpurgeradiobutton"].get_active():
            self.widgets["purgedays"].set_sensitive( False )
            self.configman.set( "general", "purge", "log" )
            self.isConfigChanged()

    def on_purgedays_changed( self, *args ):
        try:
            i = int(self.widgets["purgedays"].get_text())
        except:
            i = 30
        if not ( i>0 and i<10000 ):
            i=30
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
        app_obj = self.widgets['nssbackupConfApp']
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
            self.configman.set("report", "smtptls","1")
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
                misc.show_warndialog(message_str=_msg,
                                    parent=self.__get_application_widget(),
                                    headline_str=_("Unsupported character"))
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
#        print "store: '%s', iter: '%s'" % (store, iter)
        if store and iter:
            value = store.get_value(iter, 1)
            r = self.configman.get( "exclude", "regex" )
# Bugfix LP #258542 
            ftype_regex = r"\.%s$" % value
            r = Util.remove_conf_entry(r, ftype_regex)
            self.configman.set( "exclude", "regex", r )
            self.isConfigChanged()
            store.remove( iter )        

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
                misc.show_warndialog(message_str=_msg,
                                    parent=self.__get_application_widget(),
                                    headline_str=_("Unsupported character"))

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
                        self.ex_regex.append( [regex] )
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
            r = self.configman.get( "exclude", "regex" )
            r = Util.remove_conf_entry(r, value)
            self.configman.set( "exclude", "regex", r )
            self.isConfigChanged()
            store.remove( iter )

    def on_includetv_key_press_event(self, widget, event, *args):
        if event.keyval == gtk.keysyms.Delete :
            self.on_inc_del_clicked()
    
    def on_remote_includetv_key_press_event(self, widget, event, *args):
        if event.keyval == gtk.keysyms.Delete :
            self.on_remote_inc_del_clicked()
    
    def on_ex_pathstv_key_press_event(self, widget, event, *args):
        if event.keyval == gtk.keysyms.Delete :
            self.on_ex_delpath_clicked()
    
    def on_ex_ftypetv_key_press_event(self, widget, event, *args):
        if event.keyval == gtk.keysyms.Delete :
            self.on_ex_delftype_clicked()
    
    def on_ex_regextv_key_press_event(self, widget, event, *args):
        if event.keyval == gtk.keysyms.Delete :
            self.on_ex_delregex_clicked()

    def on_ex_max_toggled(self, *args):
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

    def on_ex_maxsize_changed(self, *args):
        """Signal handler which is called when the value for
        maximum file size is changed. The number (from the text field)
        is interpreted as Megabyte (MB).
        """
        msize = int(self.widgets["ex_maxsize"].get_value())
        self.configman.set("exclude", "maxsize",str(msize*1024*1024))
        self.isConfigChanged()

    def on_followlinks_toggled(self, *args):
        if self.widgets['followlinks'].get_active():
            self.configman.set("general", "followlinks", 1)
        else :
            self.configman.remove_option("general", "followlinks")
        self.isConfigChanged()
    
    def on_dest_localpath_selection_changed(self, *args):
        """
        @todo: Check of accessibility should not take place in the UI.
        """
        t = self.widgets["dest_localpath"].get_filename()
        if (os.path.isdir( t ) and os.access(t, os.R_OK | os.W_OK | os.X_OK)):
            self.configman.set( "general", "target", t )
            self.isConfigChanged()
            self.widgets["dest_unusable"].hide()
        else:
            self.widgets["dest_unusable"].show()

    def on_dest_remote_changed(self, *args):
        _icon = self.widgets["dest_remote_light"]
        _icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_MENU)
        _icon.set_tooltip_text(_("Please test writability of the target directory by pressing \"Test\" button on the right."))
        
        self.configman.set("general", "target",
                            self.widgets['dest_remote'].get_text())
        self.isConfigChanged()

    def on_dest_remotetest_clicked(self, *args):
        _fusefam = FuseFAM()
        _icon = self.widgets["dest_remote_light"]
        try :
            _remote_dest = self.widgets['dest_remote'].get_text()
            if (_fusefam.testFusePlugins( _remote_dest )) :
                dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Test Succeeded !"))
                dialog.run()
                dialog.destroy()
                
                self.widgets["dest_unusable"].hide()
                _icon.set_from_stock(gtk.STOCK_YES, gtk.ICON_SIZE_MENU)
                _icon.set_tooltip_text(_("Target directory is writable."))
                
        except Exception, e: 
                dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
                dialog.run()
                dialog.destroy()

                _icon.set_from_stock(gtk.STOCK_DIALOG_ERROR,
                                     gtk.ICON_SIZE_MENU)
                _icon.set_tooltip_text(_("Please change target directory and test writability of the target directory by pressing \"Test\" button on the right."))

                self.widgets["dest_unusable"].show()
    
    def on_logfilechooser_selection_changed(self, *args):
        self.configman.set_logdir(self.widgets['logfilechooser'].get_filename())
        self.configman.set_logfile_templ_to_config()
        self.isConfigChanged()
        self.logger.debug("Log file set: " + self.configman.get("log", "file"))

    def on_loglevelcombobox_changed(self, *args):
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

    def on_smtpfrom_changed(self, *args):
        self.__check_for_section("report")
        if self.widgets['smtpfrom'].get_text() != "":
            self.configman.set("report", "from", self.widgets['smtpfrom'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "from")
            self.isConfigChanged()

    def on_smtpto_changed(self, *args):
        if self.widgets['smtpto'].get_text() != "":
            self.configman.set("report", "to", self.widgets['smtpto'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "to")
            self.isConfigChanged()

    def on_smtpserver_changed(self, *args):
        if self.widgets['smtpserver'].get_text() != "":
            self.configman.set("report", "smtpserver", self.widgets['smtpserver'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "smtpserver")
            self.isConfigChanged()
        
    def on_smtpport_changed(self, *args):
        if self.widgets['smtpport'].get_text() != "":
            self.configman.set("report", "smtpport", self.widgets['smtpport'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "smtpport")
            self.isConfigChanged()
        
    def on_smtplogin_changed(self, *args):
        if self.widgets['smtplogin'].get_text() != "":
            self.configman.set("report", "smtpuser", self.widgets['smtplogin'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "smtpuser")
            self.isConfigChanged()
        
    def on_smtppassword_changed(self, *args):
        if self.widgets['smtppassword'].get_text() != "":
            self.configman.set("report", "smtppassword", self.widgets['smtppassword'].get_text())
            self.isConfigChanged()
        else :
            self.configman.remove_option("report", "smtppassword")
            self.isConfigChanged()

    def on_crtfilechooser_selection_changed(self, *args):
        smtpcert = self.widgets['crtfilechooser'].get_filename()
        if smtpcert !=None and os.path.isfile(smtpcert):
            self.configman.set("report", "smtpcert", self.widgets['crtfilechooser'].get_filename())
            self.isConfigChanged()
            self.logger.debug("Certificate : " + str(self.configman.get("report", "smtpcert")))

    def on_keyfilechooser_selection_changed(self, *args):
        smtpkey = self.widgets['keyfilechooser'].get_filename()
        if smtpkey !=None and os.path.isfile(smtpkey):
            self.configman.set("report", "smtpkey", smtpkey)
            self.isConfigChanged()
            self.logger.debug("Key : " + str(self.configman.get("report", "smtpkey")))

    def on_nssbackupConfApp_delete_event(self, *args):
        """Signal handler that is called when the window decorator close
        button is clicked.
        """
        cancelled = self.ask_save_config()        
        return cancelled

    def __terminate_app(self):
        self.configman = None
        self.orig_configman = None
        gtk.main_quit()
        
    def on_nssbackupConfApp_destroy(self, *args):
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
        print("TODO: on_ftype_custom_ex_changed")

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
        while not valid_input:
            prfDir = self.__configFileHandler.get_user_confdir()+"nssbackup.d/"
            if not os.path.exists(prfDir):
                os.makedirs(prfDir)
            
            dialog = self.widgets['askNewPrfNameDialog']
            dialog.set_title("")
            response = dialog.run()
            dialog.hide()
            
            if response == gtk.RESPONSE_OK :    
                enable = self.widgets['enableNewPrfCB'].get_active()
                prfName = self.widgets['newPrfNameEntry'].get_text()
                prfName = prfName.strip()
                prfConf = self.__configFileHandler.get_user_confdir()+"nssbackup.d/nssbackup-"+prfName+".conf"
                prfConfDisabled = "%s-disable" % prfConf
                            
                if not prfName or prfName is '':
                    misc.show_warndialog(
                        parent=self.widgets["ProfileManagerDialog"],
                        message_str=_("The given name of the new profile is empty. Please enter a valid profile name."),
                        headline_str=_("Profile name not valid"))
                    continue
                
                if os.path.exists(prfConf) or os.path.exists(prfConfDisabled):
                    misc.show_warndialog(
                        parent=self.widgets["ProfileManagerDialog"],
                        message_str=_("The given name of the new profile already exists. Please enter another name."),
                        headline_str=_("Profile name not valid"),
                        secmsg_str=_("Renaming of profiles is not supported."))
                    continue
                # if we reach this branch a valid profile name was choosen
                prf_set = True
            # if this branch is reached the input (OK, Cancel, Destroy) was
            # valid
            valid_input = True
        # end of while loop

        if prf_set:                        
            self.logger.debug("Got new profile name '%s : enable=%r' " % (prfName,enable) )
#            print "Got new profile name '%s : enable=%r' " % (prfName,enable)
            if not enable:
                prfConf = prfConfDisabled            
            confman = ConfigManager()
            confman.saveConf(prfConf)            
            self.profiles.append([enable, prfName, prfConf])
#        else:
#            print "Adding of profile canceled."
        
    def on_removeProfileButton_clicked(self, *args):
        
        tm, iter = self.profilestv.get_selection().get_selected()
        
        if not iter :
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Please select a Profile !"))
            dialog.run()
            dialog.destroy()
            return 
        
        prfName, prfConf = tm.get_value(iter,1), tm.get_value(iter,2)
        if prfName == ConfigManagerStaticData.get_default_profilename():
            _forbid_default_profile_removal(_("remove"))
        else :
            warning = _("You are trying to remove a profile. You will not be able to restore it .\n If you are not sure of what you are doing, please use the 'enable|disable' functionality.\n<b>Are you sure to want to delete the '%(name)s' profile?</b>") % {'name': prfName}
            
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_WARNING, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_YES_NO)
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
        if not iter :
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Please select a Profile !"))
            dialog.run()
            dialog.destroy()
            return 
        prfName, prfConf = tm.get_value(iter,1), tm.get_value(iter,2)
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
        if not iter :
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Please select a Profile !"))
            dialog.run()
            dialog.destroy()
            return 
        enable, prfName, prfConf =tm.get_value(iter,0), tm.get_value(iter,1), tm.get_value(iter,2)
        
        if prfName == ConfigManagerStaticData.get_default_profilename():
            _forbid_default_profile_removal(_("disable"))
        else :
            dir, file = prfConf.rsplit(os.sep,1)
            
            # rename the file 
            if enable :
                # then disable
                self.logger.debug("Disabling %s " % prfName )
                os.rename(prfConf, prfConf+"-disable")
                self.profiles.set_value(iter, 0, False)
                self.profiles.set_value(iter, 2, prfConf+"-disable")
                
            else :
                # enable it
                self.logger.debug("Enabling %s " % prfName )
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

        txt = _("<big><b>Set default values for current profile?</b></big>\nThis will restore the default values for the profile currently edited: '%s'.\n\nThese predefined settings are recommended for most users. Check whether they are appropriate for your use before saving the changed configuration.") % self.configman.getProfileName()

        label.set_line_wrap(True)
        label.set_markup(txt)
        misc.label_set_autowrap(label)        
        btn_cancel.grab_focus()
        
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_APPLY:
            self.logger.info("Default settings are being applied.")
            self._set_default_settings()            
        elif response == gtk.RESPONSE_CANCEL or \
             response == gtk.RESPONSE_DELETE_EVENT:
            pass
        else:
            self.logger.error("Unexpected dialog response: %s" % response)
            raise ValueError("Unexpected dialog response: %s" % response)
                
    def _set_default_settings(self):
        """Sets default values (which might be considered as recommended
        values for some usecase) for the current profile.
        """
        # implementation note: the values are set in the configuration
        #     manager and afterwards the according UI widgets are updated
        #    with these new values.
        self.configman.set_values_to_default()
        # filesystem is not probed, we want to set new values
        self._fill_widgets_from_config(probe_fs = False)

def _forbid_default_profile_removal(action):
    """Helper function that shows an info box which states that we are
    not able to do the given action on the default profile.    
    """
    info = _("You can't %s the Default Profile. Please use it if you need only one profile.") % action
    
    dialog = gtk.MessageDialog(type=gtk.MESSAGE_INFO,
                    flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    buttons=gtk.BUTTONS_CLOSE)
    dialog.set_markup(info)
    dialog.run()
    dialog.destroy()


def main(argv):
    window = SBconfigGTK()
    window.show()
    gtk.main()
    log.shutdown_logging()
