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
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>
#   Jean-Peer Lorenz <peer.loz@gmx.net>

import re
import subprocess
import os

import gobject
import gtk

from gettext import gettext as _

# project imports
from nssbackup import Infos
from nssbackup.plugins import PluginManager
from nssbackup.managers.FuseFAM import FuseFAM
from nssbackup.managers.ConfigManager import ConfigManager, getUserConfDir
from nssbackup.managers.ConfigManager import getUserDatasDir, ConfigStaticData
from nssbackup.util.log import LogFactory
from nssbackup.util.exceptions import SBException
import nssbackup.util as Util
from nssbackup.ui.GladeGnomeApp import GladeGnomeApp
from nssbackup.ui import misc


class SBconfigGTK(GladeGnomeApp):
	"""
	
	@todo: Unify displaying of error messages/dialog boxes!
	@todo: Strictly separate UI from core. Don't set defaults from the UI.
	"""
	
	configman = None
	conffile = None
	orig_configman = None
	plugin_manager = None
	
	def __init__(self):
		''' '''
		# it is distinguished between the 'current' conffile and
		# the 'default file' configuring the default profile
		self.default_conffile = None
		
		if os.geteuid() == 0 :
			if os.path.exists("/etc/nssbackup.conf") :
				self.default_conffile = "/etc/nssbackup.conf"
				self.configman = ConfigManager("/etc/nssbackup.conf")
			else :
				self.configman = ConfigManager()
		else :
			if os.path.exists(getUserConfDir()+"nssbackup.conf") :
				self.default_conffile = getUserConfDir()+"nssbackup.conf"
				self.conffile = getUserConfDir()+"nssbackup.conf"
				self.configman = ConfigManager(self.default_conffile)
			else :
				self.configman = ConfigManager()
		
		self.orig_configman = ConfigManager(self.default_conffile)
		
		self.logger = LogFactory.getLogger()
		
		self.loglevels = {'20' : ("Info",1) ,'10' : ("Debug", 0), '30' : ("Warning", 2), '40' : ("Error", 3)}
		self.__simple_schedule_freqs = 	{	"hourly"	: 0,
											"daily"		: 1,
											"weekly"	: 2,
											"monthly"	: 3
										}
		self.cformat = ['none', 'gzip', 'bzip2']
		self.splitSize =	{	0		: _('Unlimited'),
								100		: _('100 MiB'),
								250		: _('250 MiB'),
								650 	: _('650 MiB'),
								2000 	: _('2 GiB (FAT16)'),
								4000	: _('4 GiB (FAT32)'),
								-1		: _('Custom')
							}
		
		self.init()
		
		self.widgets['nssbackupConfApp'].set_icon_from_file(Util.getResource("nssbackup-conf.png"))
		
		# hide the schedule tab if not root
		if os.geteuid() != 0:
			self.__enable_schedule_page(enable=False)
		
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

		if os.getuid() == 0 :
			self.widgets['dest1'].set_label(_("Use default backup directory (/var/backup)"))
		else :
			self.widgets['dest1'].set_label(_("Use default backup directory (%s)") % (getUserDatasDir()+"backups") )
		
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
		
		self.known_ftypes = { "mp3": _("MP3 Music"), "avi": _("AVI Video"), "mpeg": _("MPEG Video"), "mpg": _("MPEG Video"), "mkv": _("Matrjoshka Video"), "ogg": _("OGG Multimedia container"), "iso": _("CD Images")}
					
		# Profile Manager
		# [ enable , profilename, cfPath ]
		self.profiles = gtk.ListStore( bool, str, str )
		# add the default profile and disable any modification to it
		self.profiles.append([True, ConfigStaticData.get_default_profilename(), getUserConfDir() + ConfigStaticData.get_default_conffile()]) 
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
		for k in self.splitSize.keys() :
			values.append(k)
		values.sort()
		
		for k in values :
			self.splitSizeLS.append([self.splitSize[k],k])
		self.widgets['splitsizeCB'].set_model(self.splitSizeLS)
		cell = gtk.CellRendererText()
		self.widgets['splitsizeCB'].pack_start(cell, True)
		self.widgets['splitsizeCB'].add_attribute(cell, 'text', 0) 
			
		self.prefillWindow()

	def init(self):
		
		filename = Util.getResource('nssbackup-config.glade')
		
		widget_list = [
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
			'nssbackupConfApp',
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
			'vbox_general_page',
			'rdbtn_recommended_settings',
			'rdbtn_custom_settings',
			'cformat',
			'splitsizeCB',
			'splitsizeSB',
			'splitsizevbox',
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
			'hbox9',
			'dest_localpath',
			'dest3',
			'hbox10',
			'eventbox',
			'dest_remote',
			'dest_remotetest',
			'dest_remote_light1',
			'hbox11',
			'dest_unusable',
#
#			schedule page
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
			'hbox17',
			'logpurgeradiobutton',
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
			'hbox22',
			'TLSradiobutton',
			'SSLradiobutton',
			'SSLinfos',
			'crtfilechooser',
			'keyfilechooser',
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
			]

		handlers = [
			'gtk_main_quit',
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
			'on_main_radio_toggled',
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
#			scheduling
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
			]

		top_window = 'nssbackupConfApp'
		GladeGnomeApp.__init__(self, "NSsbackup", "0.2", filename, top_window, widget_list, handlers)

	def isConfigChanged(self, force_the_change = False):
		"""Checks whether the current configuration has changed compared to
		the configuration which was originally loaded resp. stored on last
		save action.
		
		@param force_the_change: Flag that that forces the check to be True
								(i.e. the method acts as there were changes
								regardless of the real test result)
								
		"""
		changed = not self.configman.isConfigEquals(self.orig_configman)
		if force_the_change == True:
			changed = True
		self.widgets['save'].set_sensitive(changed)
		self.widgets['save_as'].set_sensitive(changed)
		self.widgets['saveButton'].set_sensitive(changed)
	
	def askSaveConfig(self):
		"""
		"""
		changed = not self.configman.isConfigEquals(self.orig_configman)
		if changed :
			question = self.widgets['askSaveDialog']
			response = question.run()
			question.hide()
			if response == gtk.RESPONSE_YES:
				self.on_save_clicked()

	def prefillWindow(self, recommened_setting=False):
		"""
		Prefill the GTK window with config infos
		
		@todo: Opening of directories (e.g. target) must be unified over all
			   modules that use such functionality!
		"""
		def __prefill_destination_widgets():
			"""Local helper function which fills the UI widgets related to
			the backup target (i.e. destination).
			"""
			# Target 
			if self.configman.has_option("general", "target" ) :
				ctarget = self.configman.get("general", "target" )
				if ctarget.startswith(os.sep) :
					if self.__is_target_set_to_default(ctarget):
						self.__set_destination_widgets_to_default()
					else :
						if not os.path.exists(ctarget ):
							self.__set_target_to_default()
							self.__set_destination_widgets_to_default()
							
							_sec_msg = _("Please make "\
					 "sure the missing directory exists (e.g. by mounting "\
					 "an external disk) or change the specified target "\
					 "to an existing one.")
							_message_str = "Backup target does not exist.\n\n"\
					 "Attention: The target will be set to the default "\
					 "value. Check this on the destination settings page "\
					 "before saving the configuration."
							_boxtitle = _("NSsbackup configuration error")
							_headline_str = \
							_("Unable to open backup target")

							gobject.idle_add( self._show_errdialog,
											  _message_str, _boxtitle,
											  _headline_str, _sec_msg )
							return
							
						self.__set_destination_widgets_to_local(ctarget)
				else :
					self.__set_destination_widgets_to_remote(ctarget)
			else :
				self.__set_destination_widgets_to_default()
							
		# Schedule page
		if not recommened_setting:
			if os.geteuid() == 0 and self.configman.is_default_profile():
				self.__enable_schedule_page(enable=True)
				
				croninfos = self.configman.getSchedule()	# = (isCron, val)
				
				# any schedule information was found
				if  croninfos is not None:
					self.widgets['rdbtn_custom_settings'].set_active(True)
# TODO: This is obviously a bug: how to treat settings with no scheduling? \
#		As 'recommended setting' is definitely wrong.
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

		# General tab
		if self.configman.has_option("general", "format") :
			cformatOpt = self.configman.get("general", "format") 
			if cformatOpt not in self.cformat:
				cformatOpt = 'gzip'
			
			cformatIndex = self.cformat.index(cformatOpt)
			self.logger.debug("Setting compression format to %s " % cformatIndex)
			self.widgets["cformat"].set_active(cformatIndex)
							
		#Include and exclude tabs
		self.include.clear()
		self.ex_paths.clear()
		if self.configman.has_section("dirconfig") :
			for i,v in self.configman.items( "dirconfig" ) :
				if v=="1":
					self.include.append( [i] )
				elif v =="0":
					self.ex_paths.append( [i] )
					
		#remote includes
		self.remoteinc.clear()
		if self.configman.has_option("dirconfig", "remote") :
			for i,v in self.configman.get("dirconfig", "remote").iteritems():
				if str(v) == "1":
					self.remoteinc.append( [i] )
				elif v =="0":
					print ("TODO: add a remote ex widget")
					
		# regexp excludes
		_invalid_regex_found = False
		_invalid_regex = ""
		self.ex_ftype.clear()
		self.ex_regex.clear()
		if self.configman.has_option("exclude", "regex") :
			r = self.configman.get( "exclude", "regex" )
			if not Util.is_empty_regexp(r):
				list = str(r).split(",")
				for i in list:
					if re.match( r"\\\.\w+", i ):
						if i[2:] in self.known_ftypes:
							self.ex_ftype.append( [self.known_ftypes[i[2:]], i[2:]] )
						else:
							self.ex_ftype.append( [_("Custom"), i[2:]] )
					else:
						if (not Util.is_empty_regexp( i )) and Util.is_valid_regexp( i ):
							self.ex_regex.append( [i] )
						else:
							r = Util.remove_conf_entry(r, i); print "r: %s" % r
							self.logger.warning(_("Invalid regular "\
										"expression ('%s') found in "\
										"configuration. Removed.") % i )
							_invalid_regex_found = True
							_invalid_regex = "%s, %s" % (_invalid_regex, i)

		if _invalid_regex_found:
			self.configman.set( "exclude", "regex", r )
			self.isConfigChanged()
			_msg = _("Invalid regular expressions found\n"\
					 "in configuration file:\n"\
					 "'%s'\n\nThese expressions are not used and were\n"\
					 "removed from the "\
					 "configuration.") % (_invalid_regex.lstrip(","))
			gobject.idle_add(self._show_errdialog, _msg)
		
		# Set maximum size limits
		if self.configman.has_option("exclude", "maxsize") :
			self.widgets["ex_maxsize"].set_value( self.configman.getint("exclude", "maxsize")/(1024*1024) )
			if self.configman.getint("exclude", "maxsize") < 0:
				self.widgets["ex_maxsize"].set_sensitive( False )
				self.widgets["ex_max"].set_active( False )
			else:
				self.widgets["ex_maxsize"].set_sensitive( True )
				self.widgets["ex_max"].set_active( True )
		
		# backup links
		if self.configman.has_option("general", "followlinks") :
			self.widgets["followlinks"].set_active(True)
		else :
			self.widgets["followlinks"].set_active(False)
		
		# Maximum of inc
		if self.configman.has_option("general", "maxincrement") :
			self.widgets["time_maxinc"].set_value( int(self.configman.get("general", "maxincrement")))
	
		__prefill_destination_widgets()
		
		# log
		if self.configman.has_option("log", "level") :
			self.widgets["loglevelcombobox"].set_active(self.loglevels[self.configman.get("log", "level")][1])
		else :
			self.widgets["loglevelcombobox"].set_active(self.loglevels['20'][1])

		self.widgets["logfilechooser"].set_current_folder(self.configman.get_logdir())
				
		# report
		def unfillreportentries():
			self.widgets["smtpto"].set_text("")
			self.widgets["smtpfrom"].set_text("")
			self.widgets["smtpserver"].set_text("")
			self.widgets["smtpport"].set_text("")
			self.widgets["smtplogin"].set_text("")
			self.widgets["smtppassword"].set_text("")
			self.widgets["smtplogincheckbox"].set_active(False)
			self.widgets["TLScheckbutton"].set_active(False)
		
		if self.configman.has_section("report") :
			opts = self.configman.options("report")
			if not opts or len(opts)==0:
				unfillreportentries()
				# LP Bug #153605
				self.widgets['smtpfrom'].set_text(Infos.SMTPFROM)
				self.widgets['smtplogininfo'].set_sensitive(False)
				self.widgets['TLSinfos'].set_sensitive(False)
			else :
				if self.configman.has_option("report", "from") :
					self.widgets["smtpfrom"].set_text(self.configman.get("report", "from"))
				if self.configman.has_option("report", "to") :
					self.widgets["smtpto"].set_text(self.configman.get("report", "to"))
				if self.configman.has_option("report", "smtpserver") :
					self.widgets["smtpserver"].set_text(self.configman.get("report", "smtpserver"))
				if self.configman.has_option("report", "smtpport") :
					self.widgets["smtpport"].set_text(self.configman.get("report", "smtpport"))
				if self.configman.has_option("report", "smtpuser") or self.configman.has_option("report", "smtppassword") :
					self.widgets["smtplogincheckbox"].set_active(True)
					self.widgets['smtplogininfo'].set_sensitive(True)
					if self.configman.has_option("report", "smtpuser") :
						self.widgets["smtplogin"].set_text(self.configman.get("report", "smtpuser"))
					if self.configman.has_option("report", "smtppassword") :
						self.widgets["smtppassword"].set_text(self.configman.get("report", "smtppassword"))
				if self.configman.has_option("report", "smtptls"):
					self.widgets["TLScheckbutton"].set_active(True)
					self.widgets['TLSinfos'].set_sensitive(True)
				else:
					self.widgets["TLScheckbutton"].set_active(False)
				if self.configman.has_option("report", "smtpcert") or self.configman.has_option("report", "smtpkey") :
					self.widgets["SSLradiobutton"].set_active(True)
					self.widgets['SSLinfos'].set_sensitive(True)
					if self.configman.has_option("report", "smtpcert") :
						self.widgets['crtfilechooser'].set_filename(self.configman.get("report", "smtpcert"))
					if self.configman.has_option("report", "smtpkey") :
						self.widgets['crtfilechooser'].set_filename(self.configman.get("report", "smtpkey"))
				else :
					self.widgets["TLSradiobutton"].set_active(True)
					self.widgets['SSLinfos'].set_sensitive(False)
					self.widgets['crtfilechooser'].set_filename("")
					self.widgets['keyfilechooser'].set_filename("")
		else :
			unfillreportentries()
			# LP Bug #153605
			self.widgets['smtpfrom'].set_text(Infos.SMTPFROM)
			self.widgets['smtplogininfo'].set_sensitive(False)
			self.widgets['TLSinfos'].set_sensitive(False)
			
		# Purge setting 
		if self.configman.has_option("general", "purge") :
			self.logger.debug("setting purge")
			if self.configman.get("general", "purge") == "log" :
				self.widgets['logpurgeradiobutton'].set_active(True)
			else:
				try : 
					purge = int(self.configman.get("general", "purge"))
				except Exception,e:
					self.logger.error("Purge value '%s' is invalide : " + e %self.configman.get("general", "purge"))	
					purge = 30
				self.widgets['purgedays'].set_text(str(purge))
				self.widgets['purgeradiobutton'].set_active(True)
				self.widgets["purgedays"].set_sensitive( True )
				self.on_purgedays_changed()
			self.widgets['purgecheckbox'].set_active(True)
		
		if self.configman.has_option("general", "splitsize") :
			model = self.widgets["splitsizeCB"].get_model()
			custom = True
			for i in range(0,len(model)) :
				if model[i][1] == int(self.configman.get("general", "splitsize")) / 1024 :
					self.widgets["splitsizeCB"].set_active(i)
					self.widgets["splitsizeSB"].set_sensitive(False)
					custom =False
			if custom :
				# NOTE: if we don't do this is this order, the handler on splitsizeCB will overide splitsizeSB value
				self.widgets["splitsizeSB"].set_value(int(self.configman.get("general", "splitsize")) / 1024 )
				self.widgets["splitsizeCB"].set_active(0)
		
		# set the profile name
		self.widgets['statusBar'].push(_("Editing profile : %s ") % self.configman.getProfileName())
		
		self.isConfigChanged()
	
	def __set_destination_widgets_to_default(self):
		"""The widgets within the 'Destination' page are enabled/disabled/set
		according to default setting.
		""" 
		self.widgets["dest1"].set_active( True )
		self.widgets["hbox9"].set_sensitive( False )
		self.widgets["hbox10"].set_sensitive( False )
		
	def __set_destination_widgets_to_local(self, atarget):
		"""The widgets within the 'Destination' page are enabled/disabled/set
		according to the given local target directory.
		""" 
		self.widgets["dest2"].set_active( True )			
		self.widgets["hbox9"].set_sensitive( True )
		self.widgets["dest_localpath"].set_current_folder( atarget )
		self.widgets["hbox10"].set_sensitive( False )

	def __set_destination_widgets_to_remote(self, atarget):
		"""The widgets within the 'Destination' page are enabled/disabled/set
		according to the given remote target.
		""" 
		self.widgets["dest3"].set_active( True )			
		self.widgets["hbox9"].set_sensitive( False )
		self.widgets["hbox10"].set_sensitive( True )
		self.widgets["dest_remote"].set_text( atarget )
	
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
			self._show_errdialog(message_str = _("Empty expression. Please enter a valid regular expression."))
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
				self._show_errdialog(message_str = _("Provided regular expression is not valid."))		

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
						message_format=_("It seems the path you entered does not exists. Do you want to add this wrong path?"))
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
		dialog = gtk.FileChooserDialog(_("Save to file ..."),
									None,
									gtk.FILE_CHOOSER_ACTION_SAVE,
									(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
									 gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		response = dialog.run()
		if response == gtk.RESPONSE_OK :
			self.configman.saveConf(dialog.get_filename())
			self.isConfigChanged()
		elif response == gtk.RESPONSE_CANCEL:
			pass
		dialog.destroy()

	def on_exit_activate(self, *args):
		gtk.main_quit()

	def on_menu_help_activate(self, button):
		misc.open_uri("ghelp:nssbackup")

	def on_menu_about_activate(self, *args):
		about = gtk.AboutDialog()
		about.set_name(Infos.NAME)
		# TODO: Always keep this updated
		about.set_version(Infos.VERSION)
		about.set_comments(Infos.DESCRIPTION)
		about.set_transient_for(self.widgets["nssbackupConfApp"])
		about.set_copyright("Oumar Aziz Ouattara <wattazoum@gmail.com>")
		about.set_translator_credits(_("translator-credits"))
		about.set_authors(Infos.AUTHORS)
		about.set_website(Infos.WEBSITE)
		about.set_logo(gtk.gdk.pixbuf_new_from_file(Util.getResource("nssbackup-conf.png")))
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
		self.prefillWindow()
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
		self.askSaveConfig()
		try :
			pid = subprocess.Popen(["nssbackupd"]).pid
			
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("A backup run is initiated in the background. The process id is: ")+str(pid)+".")
			dialog.run()
			dialog.destroy()
		except Exception, e:
			dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
			dialog.run()
			dialog.destroy()
			raise e

	def on_main_radio_toggled(self, *args):
		"""Signal handler which is called when the radio buttons on the main
		page are toggled.
		"""
		if self.widgets["rdbtn_recommended_settings"].get_active():
			# set all values to defaults
		
			self.configman = ConfigManager()
			self.prefillWindow(True)
			
#			self.widgets["time_freq"].set_active( 2 )
			# choose between anacron or cron here (old behaviour has been kept for the moment.
			# TODO: Needs review!
#			self.widgets["preciselyRadio"].set_active( True )
#			self.widgets["anacronRadio"].set_active( False )

#			self.widgets["croninfos"].set_sensitive( True )
#			self.widgets["time_min"].set_sensitive( True )
#			self.widgets["time_hour"].set_sensitive( True )
#			self.widgets["time_min"].set_value( 0 )
#			self.widgets["time_hour"].set_value( 0 )
#			self.widgets["scrolledwindow5"].set_sensitive( False )
#			self.widgets["scrolledwindow6"].set_sensitive( False )
#			self.widgets["ccronline"].set_sensitive( False )

			self.widgets["purgecheckbox"].set_active( True )
			self.widgets["purgeradiobutton"].set_active( 1 )
			self.widgets["purgedays"].set_sensitive( False )

			# disable all tabs
			self.widgets["vbox3"].set_sensitive( False )
			self.widgets["notebook2"].set_sensitive( False )
			self.widgets["vbox8"].set_sensitive( False )
			self.widgets["vbox_schedule_page"].set_sensitive(False)
			self.widgets["reportvbox"].set_sensitive( True )

		elif self.widgets["rdbtn_custom_settings"].get_active():
			# enable all tabs
			self.widgets["vbox3"].set_sensitive( True )
			self.widgets["notebook2"].set_sensitive( True )
			self.widgets["vbox8"].set_sensitive( True )
			self.widgets["vbox_schedule_page"].set_sensitive(True)
			self.widgets["reportvbox"].set_sensitive( True )

	def on_cformat_changed(self, *args):
		"""
		handle that sets the compression format
		"""
		selected = self.widgets["cformat"].get_active()
		if 0 <= selected < len(self.cformat) :
			self.configman.set("general", "format", self.cformat[selected] )
		else :
			self.configman.remove_option("general", "format")
			
		if selected == self.cformat.index("none") :
			# activate split functionality config
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
			self.widgets['splitsizeSB'].set_sensitive(False)
			self.configman.set("general", "splitsize", value*1024)
		else :
			# activate Spin box
			self.widgets['splitsizeSB'].set_sensitive(True)
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
		dialog = gtk.FileChooserDialog(_("Include file ..."),
									None,
									gtk.FILE_CHOOSER_ACTION_OPEN,
									(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
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

	def on_inc_adddir_clicked(self, *args):
		dialog = gtk.FileChooserDialog(_("Include folder ..."),
									None,
									gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
									(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
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
		(store, iter) = self.includetv.get_selection().get_selected()
		if store and iter:
			value = store.get_value( iter, 0 )
			self.configman.remove_option( "dirconfig", value )
			self.isConfigChanged()
			store.remove( iter )

	def on_remote_inc_add_clicked(self,*args):
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
											message_format="Test on '%s' didn't succeed !"% row[0])
					dialog.run()
					dialog.destroy()
				else :
					n = n +1
			except Exception, e: 
					dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
					dialog.run()
					dialog.destroy()
		if n == len(self.remoteinc) :
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format="Test Succeeded !")
			dialog.run()
			dialog.destroy()
		else :
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, 
											message_format=_("'%d' test(s) didn't succeed !") % (len(self.remoteinc)- n))
			dialog.run()
			dialog.destroy()

	def on_ex_addfile_clicked(self, *args):
		dialog = gtk.FileChooserDialog(_("Include file ..."), None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
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
		dialog = gtk.FileChooserDialog(_("Exclude folder ..."), None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
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
		(store, iter) = self.ex_pathstv.get_selection().get_selected()
		if store and iter:
			value = store.get_value( iter, 0 )
			self.configman.remove_option( "dirconfig", value )
			self.isConfigChanged()
			store.remove( iter )

	def __is_target_set_to_default(self, atarget):
		"""Checks if the given target directory is equal to the
		default settings:
		'/var/backup' for root, 'homedir+/backups' for non-admins.
		@rtype: Boolean
		
		@todo: Use functions from ConfigManager to proceed the check in
				a consistent manner.
		"""
		_reslt = False
		if (os.getuid() == 0 and atarget == "/var/backup") or\
		   (os.getuid() != 0 and atarget == getUserDatasDir()+"backups"):
			_reslt = True
		return _reslt

	def __set_target_to_default(self):
		"""The target option within the configuration is set to the default:
		'/var/backup' for root, 'homedir+/backups' for non-admins.
		
		@todo: The result of 'os.getuid' should be retrieved during the
			   initialization process and stored in a member attribute, so
			   we don't need to use operation system call over and over!

		@todo: Use functions from ConfigManager to set the paths in
				a consistent manner.
		"""
		if os.getuid() == 0 :
			self.configman.set( "general", "target", "/var/backup")
			self.isConfigChanged()
		else :
			self.configman.set( "general", "target", getUserDatasDir()+"backups")
			self.isConfigChanged()

	def on_dest1_toggled(self, *args):
		if self.widgets["dest1"].get_active():
			self.widgets["hbox9"].set_sensitive( False )
			self.widgets["hbox10"].set_sensitive( False )
			self.widgets["dest_unusable"].hide()
			self.__set_target_to_default()
		elif self.widgets["dest2"].get_active():
			self.widgets["hbox9"].set_sensitive( True )
			self.widgets["hbox10"].set_sensitive( False )
			self.on_dest_localpath_selection_changed()
		else:
			self.widgets["hbox9"].set_sensitive( False )
			self.widgets["hbox10"].set_sensitive( True )
			self.on_dest_remote_changed()

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
		
#	def __set_schedule_defaults(self):
#		_default_schedule = "simple"
#		_simple_default_freq = "daily"
#		_custom_default_cronline = "0 0 * * *"
#		
#		self.__set_schedule_option(_default_schedule)
#		self.__set_value_cmbbx_simple_schedule_freq(_simple_default_freq)
#		self.__set_value_txtfld_custom_cronline(_custom_default_cronline)
		
	def __set_default_cmbbx_simple_schedule_freq(self):
		_simple_default_freq = "daily"		
		self.__set_value_cmbbx_simple_schedule_freq(_simple_default_freq)

	def __set_value_txtfld_custom_cronline(self, cronline):
		self.widgets['txtfld_custom_cronline'].set_text(cronline)
#TODO: Review - is it required?
#		self.on_txtfld_custom_cronline_changed()

	def __set_value_cmbbx_simple_schedule_freq(self, frequency):
		if frequency in self.__simple_schedule_freqs.keys():
			self.widgets['cmbbx_simple_schedule_freq'].set_active(\
										self.__simple_schedule_freqs[frequency])
		else:
			raise ValueError("Unknown anacron setting found!")
#TODO: Review - is it required?
#		self.on_cmbbx_simple_schedule_freq_changed()

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
		
		@todo: Use __simple_schedule_freqs keys!
		"""
		_selection = self.widgets["cmbbx_simple_schedule_freq"].get_active()
		
		if _selection not in self.__simple_schedule_freqs.values():
			self.__set_default_cmbbx_simple_schedule_freq()

		for _freq_key in self.__simple_schedule_freqs.keys():
			if _selection == self.__simple_schedule_freqs[_freq_key]:
				self.configman.setSchedule(0, _freq_key)
			
		self.isConfigChanged()
		self.logger.debug("AnaCronline is: %s" % self.configman.get("schedule",
																	"anacron"))

	def on_txtfld_custom_cronline_changed(self, *args):
		_cronline = self.widgets['txtfld_custom_cronline'].get_text()
		print "WE MUST CHECK THE INPUT HERE!"
#TODO: WE MUST CHECK THE INPUT HERE!
		self.configman.setSchedule(1, _cronline)
		self.isConfigChanged()
		self.logger.debug("Cronline set to '%s'" % self.configman.get("schedule", "cron"))

	def on_time_maxinc_changed(self,*args):
		# add maxinc to the config
		self.configman.set("general", "maxincrement", int(self.widgets["time_maxinc"].get_value())) 
		self.isConfigChanged()
	
	def on_purgecheckbox_toggled(self, *args):
		if self.widgets["purgecheckbox"].get_active() :
			self.widgets['hbox16'].set_sensitive(True)
			self.widgets['hbox17'].set_sensitive(True)
			self.on_purgeradiobutton_toggled()
		else :
			self.widgets['hbox16'].set_sensitive(False)
			self.widgets['hbox17'].set_sensitive(False)
			self.configman.remove_option( "general", "purge")
			self.isConfigChanged()

	def on_purgeradiobutton_toggled(self, *args):
		if self.widgets["purgeradiobutton"].get_active():
			self.widgets["purgedays"].set_sensitive( True )
			try: i = int(self.widgets["purgedays"].get_text())
			except: i = -1
			if not ( i>0 and i<10000 ):	i=30
			self.widgets["purgedays"].set_text(str(i))
			self.configman.set( "general", "purge", str(i) )
			self.isConfigChanged()
		elif self.widgets["logpurgeradiobutton"].get_active():
			self.widgets["purgedays"].set_sensitive( False )
			self.configman.set( "general", "purge", "log" )
			self.isConfigChanged()

	def on_purgedays_changed( self, *args ):
		try: i = int(self.widgets["purgedays"].get_text())
		except: i = -1
		if not ( i>0 and i<10000 ):	i=30
		self.configman.set( "general", "purge", str(i) )
		self.isConfigChanged()
		
	def on_testMailButton_clicked(self, *args):
		result = False
		try :
			result = self.configman.testMail()
		except SBException, e:
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
			dialog.run()
			dialog.destroy()
		
		if result :
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Test Succeeded !"))
			dialog.run()
			dialog.destroy()

	def on_smtplogincheckbox_toggled(self, *args):
		if not self.widgets['smtplogincheckbox'].get_active():
			self.widgets['smtplogininfo'].set_sensitive(False)
			if self.configman.has_option("report", "smtpuser") :
				self.configman.remove_option("report", "smtpuser")
			if self.configman.has_option("report", "smtppassword") :
				self.configman.remove_option("report", "smtppassword")
			self.isConfigChanged()
		else :
			self.widgets['smtplogininfo'].set_sensitive(True)
			if self.widgets['smtplogin'].get_text() :
				self.configman.set("report", "smtpuser",self.widgets['smtplogin'].get_text())
				self.isConfigChanged()
				self.logger.debug("login : " + self.configman.get("report", "smtpuser"))
			if self.widgets['smtppassword'].get_text() :
				self.configman.set("report", "smtpuser", self.widgets['smtppassword'].get_text())
				self.isConfigChanged()
				self.logger.debug("Password : " + self.configman.get("report", "smtppassword"))
				
	def on_TLScheckbutton_toggled(self, *args):
		if not self.widgets['TLScheckbutton'].get_active():
			self.widgets['TLSinfos'].set_sensitive(False)
			if self.configman.has_option("report", "smtptls") :
				self.configman.remove_option("report", "smtptls")
			if self.configman.has_option("report", "smtpcert") :
				self.configman.remove_option("report", "smtpcert")
			if self.configman.has_option("report", "smtpkey") :
				self.configman.remove_option("report", "smtpkey")
			self.isConfigChanged()
		else :
			self.configman.set("report", "smtptls","1")
			self.isConfigChanged()
			self.widgets['TLSinfos'].set_sensitive(True)
			self.on_TLSradiobutton_toggled()
			
	def on_TLSradiobutton_toggled(self, *args):
		if self.widgets['TLSradiobutton'].get_active():
			self.widgets['SSLinfos'].set_sensitive(False)
			if self.configman.has_option("report", "smptcert") :
				self.configman.remove_option("report", "smptcert")
			if self.configman.has_option("report", "smptkey") :
				self.configman.remove_option("report", "smptkey")
			self.isConfigChanged()
		elif self.widgets['SSLradiobutton'].get_active():
			self.widgets['SSLinfos'].set_sensitive(True)
			if self.widgets['crtfilechooser'].get_filename() :
				self.on_crtfilechooser_selection_changed()
			if self.widgets['keyfilechooser'].get_filename() :
				self.on_keyfilechooser_selection_changed()

	def on_ex_addftype_clicked(self, *args):
		dialog = self.widgets["ftypedialog"]
		response = dialog.run()
		dialog.hide()
		if response == gtk.RESPONSE_OK:
			if self.widgets["ftype_st"].get_active():
				ftype = self.widgets["ftype_box"].get_model()[self.widgets["ftype_box"].get_active()][0]
			else:
				ftype = self.widgets["ftype_custom_ex"].get_text()

			if self.configman.has_option("exclude", "regex") :
				r = self.configman.get( "exclude", "regex" )
			else:
				r=""
			r = r + r",\." + ftype.strip()
			self.configman.set( "exclude", "regex", r )
			
			if ftype in self.known_ftypes:
				self.ex_ftype.append( [self.known_ftypes[ftype], ftype] )
			else:
				self.ex_ftype.append( [_("Custom"), ftype] )

			self.isConfigChanged()
		elif response == gtk.RESPONSE_CANCEL:
			pass		                

	def on_ex_delftype_clicked(self, *args):
		(store, iter) = self.ex_ftypetv.get_selection().get_selected()
		if store and iter:
			value = store.get_value( iter, 1 )
			r = self.configman.get( "exclude", "regex" )
			r = ","+r+","
			r = re.sub( r",\\."+re.escape(value)+"," , ",", r )
			r = r.lstrip( "," ).rstrip( "," )
			self.configman.set( "exclude", "regex", r )
			self.isConfigChanged()
			store.remove( iter )		

	def on_ex_addregex_clicked(self, *args):
		dialog = self.widgets["regexdialog"]
		response = dialog.run()
		dialog.hide()
		if response == gtk.RESPONSE_OK:
			regex = self.widgets["regex_box"].get_text()
			if Util.is_empty_regexp(regex):
				self._show_errdialog(message_str = _("Empty expression. Please enter a valid regular expression."))
			else:
				if Util.is_valid_regexp(regex):			
					if self.configman.has_option("exclude", "regex") :
						r = self.configman.get( "exclude", "regex" )
					else:
						r=""
					r = r + r"," + regex.strip()
					r = r.strip(",")
					self.configman.set( "exclude", "regex", r )					
					self.ex_regex.append( [regex] )
					self.isConfigChanged()
				else:
					self._show_errdialog(message_str = _("Provided regular expression is not valid."))

		elif response == gtk.RESPONSE_CANCEL:
			pass
	
	def on_ex_delregex_clicked(self, *args):
		(store, iter) = self.ex_regextv.get_selection().get_selected()
		if store and iter:
			value = store.get_value( iter, 0 )
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
		if self.widgets["ex_max"].get_active():
			self.widgets["ex_maxsize"].set_sensitive( True )
			self.on_ex_maxsize_changed()
		elif not self.widgets["ex_max"].get_active():
			self.widgets["ex_maxsize"].set_sensitive( False )
			self.configman.remove_option("exclude", "maxsize")
			self.isConfigChanged()

	def on_followlinks_toggled(self, *args):
		if self.widgets['followlinks'].get_active():
			self.configman.set("general", "followlinks", 1)
		else :
			self.configman.remove_option("general", "followlinks")
		self.isConfigChanged()

	def on_ex_maxsize_changed(self, *args):
		self.configman.set( "exclude", "maxsize", str(int(self.widgets["ex_maxsize"].get_value())*1024*1024) )
		self.isConfigChanged()
	
	def on_dest_localpath_selection_changed(self, *args):
		t = self.widgets["dest_localpath"].get_filename()
		if (os.path.isdir( t ) and os.access( t, os.R_OK | os.W_OK | os.X_OK ) ):
			self.configman.set( "general", "target", t )
			self.isConfigChanged()
			self.widgets["dest_unusable"].hide()
		else:
			self.widgets["dest_unusable"].show()

	def on_dest_remote_changed(self, *args):
		self.widgets["dest_remote_light1"].set_from_stock( gtk.STOCK_DIALOG_WARNING , gtk.ICON_SIZE_BUTTON)
		gtk.tooltips_data_get(self.widgets["eventbox"])[0].set_tip(self.widgets["eventbox"], _("Please test writability of the target directory by pressing \"Test\" button on the right."))
		self.configman.set( "general", "target", self.widgets['dest_remote'].get_text() )
		self.isConfigChanged()

	def on_dest_remotetest_clicked(self, *args):
		_fusefam = FuseFAM()
		try :
			_remote_dest = self.widgets['dest_remote'].get_text()
			if (_fusefam.testFusePlugins( _remote_dest )) :
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Test Succeeded !"))
				dialog.run()
				dialog.destroy()
				
				self.widgets["dest_unusable"].hide()
				self.widgets["dest_remote_light1"].set_from_stock( gtk.STOCK_YES , gtk.ICON_SIZE_BUTTON )
				gtk.tooltips_data_get(self.widgets["eventbox"])[0].set_tip(self.widgets["eventbox"], _("Target directory is writable."))				
		except Exception, e: 
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
				dialog.run()
				dialog.destroy()
				
				self.widgets["dest_remote_light1"].set_from_stock( gtk.STOCK_DIALOG_ERROR , gtk.ICON_SIZE_BUTTON )
				gtk.tooltips_data_get(self.widgets["eventbox"])[0].set_tip(self.widgets["eventbox"], _("Please change target directory and test writability of the target directory by pressing \"Test\" button on the right."))
				self.widgets["dest_unusable"].show()
	
	def on_logfilechooser_selection_changed(self, *args):
		self.configman.set_logdir(self.widgets['logfilechooser'].get_filename())
		self.configman.set_logfile()
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

	def gtk_main_quit( self, *args):
		self.askSaveConfig()
		gtk.main_quit()

	def on_ftype_custom_ex_changed(self, *args):
		print("TODO: on_ftype_custom_ex_changed")
		pass

	def on_prfManager_activate(self, *args):
		"""
		Launch Profile manager dialog
		"""
		self.askSaveConfig()
		
		dialog = self.widgets["ProfileManagerDialog"]
		dialog.run()
		dialog.hide()

	def on_addProfileButton_clicked(self, *args):
		
		prfDir = getUserConfDir()+"nssbackup.d/"
		if not os.path.exists(prfDir):
			os.makedirs(prfDir)
		
		dialog = self.widgets['askNewPrfNameDialog']
		response = dialog.run()
		dialog.hide()
		
		if response == gtk.RESPONSE_OK :

			enable = self.widgets['enableNewPrfCB'].get_active()
			prfName = self.widgets['newPrfNameEntry'].get_text()
			prfConf = getUserConfDir()+"nssbackup.d/nssbackup-"+prfName.strip()+".conf"
			
			if not prfName or prfName is '' :
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
										 buttons=gtk.BUTTONS_CLOSE, message_format="Profile Name must not be empty ! " )
				dialog.run()
				dialog.destroy()
			
			elif os.path.exists(prfConf) :
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
										 buttons=gtk.BUTTONS_CLOSE, message_format="%s already exists . Please use 'Edit' instead of 'Add' !" % prfName )
				dialog.run()
				dialog.destroy()
			else :
					
				self.logger.debug("Got new profile name '%s : enable=%r' " % (prfName,enable) )
			
				if not enable : 
					prfConf += "-disable"
				
				confman = ConfigManager()
				confman.saveConf(prfConf)
				
				self.profiles.append([enable, prfName, prfConf])
		
		elif response == gtk.RESPONSE_CANCEL :
			pass
		
	def on_removeProfileButton_clicked(self, *args):
		
		tm, iter = self.profilestv.get_selection().get_selected()
		
		if not iter :
			dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Please select a Profile !"))
			dialog.run()
			dialog.destroy()
			return 
		
		prfName, prfConf = tm.get_value(iter,1), tm.get_value(iter,2)
		if prfName == ConfigStaticData.get_default_profilename():
			self._forbid_default_profile_removal(_("remove"))
		else :
			warning = _("You are trying to remove a profile. You will not be able to restore it .\n If you are not sure of what you are doing, please use the 'enable|disable' functionality.\n <b>Are you sure to want to delete the '%(name)s' profile ?</b> " % {'name': prfName})
			
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
		
		if prfName == ConfigStaticData.get_default_profilename():
			self._forbid_default_profile_removal(_("disable"))
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

	def _show_errdialog(self, message_str, boxtitle = "",
							   headline_str = "", secmsg_str = ""):
		"""Creates und displays a modal dialog box. Main purpose is
		displaying of error messages.
		
		@param message_format: error message to show
		@type message_format: String
		
		@todo: Should we use the button OK or CLOSE?
		"""
		dialog = gtk.MessageDialog(
					flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
					type = gtk.MESSAGE_ERROR,
					buttons=gtk.BUTTONS_CLOSE)
		if boxtitle.strip() != "":
			dialog.set_title( boxtitle )
			
		_hdl = headline_str.strip(" \n\t")
		if _hdl != "":
			_hdl = "<b>%s</b>\n\n" % _hdl
		_msg = "%s%s" % ( _hdl, message_str )
		dialog.set_markup(_msg)

		# an optional secondary message is added
		_sec = secmsg_str.strip(" \n\t")
		if _sec != "":
			_sec = "<small>%s</small>" % ( _sec )
			dialog.format_secondary_markup(_sec)
			
		# the message box is showed
		dialog.run()
		dialog.destroy()

	def _forbid_default_profile_removal(self, action):
		"""Shows an info box which states that we are not able to do the
		given action on the default profile.
		
		"""
		info = _("You can't %s the Default Profile. Please use it if you "\
				 "need only one profile." % action)
		
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
