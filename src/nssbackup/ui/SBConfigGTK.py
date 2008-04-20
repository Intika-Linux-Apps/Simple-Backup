
#----------------------------------------------------------------------
# SBConfigGTK.py
# Ouattara Aziz
# 06/16/2007
#----------------------------------------------------------------------

import re
import subprocess
import os
import time
import locale
import nssbackup.managers.FileAccessManager as FAM
from nssbackup import Infos
from nssbackup.plugins import PluginManager, pluginFAM
from nssbackup.managers.FuseFAM import FuseFAM
from nssbackup.util.log import LogFactory
from nssbackup.util.exceptions import SBException
from nssbackup.managers.ConfigManager import ConfigManager, getUserConfDir, getUserDatasDir
from nssbackup.ui.GladeGnomeApp import *
from gettext import gettext as _
import nssbackup.util as Util

#----------------------------------------------------------------------

class SBconfigGTK(GladeGnomeApp):
	
	configman = None
	conffile = None
	orig_configman = None
	plugin_manager = None
	
	#----------------------------------------------------------------------

	def __init__(self):
		''' '''
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
				self.configman = ConfigManager(getUserConfDir()+"nssbackup.conf")
			else :
				self.configman = ConfigManager()
		
		self.orig_configman = ConfigManager(self.default_conffile)
		
		self.logger = LogFactory.getLogger()
		
		self.loglevels = {'20' : ("Info",1) ,'10' : ("Debug", 0), '30' : ("Warning", 2), '50' : ("Error", 3)}
		self.timefreqs = {"never":0, "hourly": 1,"daily": 2,"weekly": 3,"monthly": 4,"custom":5}
		self.cformat = {'none':0, 'gzip':1, 'bzip2':2}
		self.splitSize = {0:_('Unlimited'),100:_('100 MB'),250:_('250 MB'), 650 : _('650 MB'),2000 :_('2 GB (FAT16)'),4000 : _('4 GB (FAT32)'), -1: _('Custom')}
		
		self.init()
		
		self.widgets['nssbackupConfApp'].set_icon_from_file(Util.getResource("nssbackup-conf.png"))
		
		# hide the schedule tab if not root
		if os.geteuid() != 0 :
			self.widgets['notebook'].remove_page(4)	
		
		# ---
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
		
		# Day of month table
		self.time_dom = gtk.ListStore( str )
		self.time_domtv = self.widgets["time_domtv"]
		self.time_domtv.set_model( self.time_dom )
		cell6 = gtk.CellRendererText()
		column6 = gtk.TreeViewColumn(_('Name'), cell6, text=0)
		self.time_domtv.append_column(column6)

		for i in range(1, 32):
			self.time_dom.append( [str(i)] )

		# Day of week table
		self.time_dow = gtk.ListStore( str )
		self.time_dowtv = self.widgets["time_dowtv"]
		self.time_dowtv.set_model( self.time_dow )
		cell7 = gtk.CellRendererText()
		column7 = gtk.TreeViewColumn(_('Name'), cell7, text=0)
		self.time_dowtv.append_column(column7)

		self.known_ftypes = { "mp3": _("MP3 Music"), "avi": _("AVI Video"), "mpeg": _("MPEG Video"), "mpg": _("MPEG Video"), "mkv": _("Matrjoshka Video"), "ogg": _("OGG Multimedia container"), "iso": _("CD Images")}
		
		for i in range(0,7):
			self.time_dow.append([ time.strftime( "%A", (2000,1,1,1,1,1,i,1,1)) ])
			
		# Profile Manager
		# [ enable , profilename, cfPath ]
		self.profiles = gtk.ListStore( bool, str, str )
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
			
		# ---
			
		self.prefillWindow()

	#----------------------------------------------------------------------

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
			'vbox2',
			'main_radio',
			'hbox1',
			'main_radio2',
			'hbox2',
			'main_radio3',
			'cformat',
			'splitsizeCB',
			'splitsizeSB',
			'splitsizevbox',
			'hbox3',
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
			'vbox9',
			'hbox12',
			'time_freq',
			'anacronRadio',
			'preciselyRadio',
			'croninfos',
			'time_hour',
			'time_min',
			'scrolledwindow6',
			'time_dowtv',
			'scrolledwindow5',
			'time_domtv',
			'hbox13',
			'ccronline',
			'hbox14',
			'time_maxinc',
			'hbox15',
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
			'on_about_activate',
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
			'on_time_freq_changed',
			'on_time_hour_changed',
			'on_time_min_changed',
			'on_anacronRadio_toggled',
			'on_ccronline_changed',
			'on_time_domtv_cursor_changed',
			'on_time_dowtv_cursor_changed',
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
			]

		top_window = 'nssbackupConfApp'
		GladeGnomeApp.__init__(self, "NSsbackup", "0.2", filename, top_window, widget_list, handlers)

	#----------------------------------------------------------------------
	
			
	def isConfigChanged(self):
		"""
		"""
		changed = not self.configman.isConfigEquals(self.orig_configman)
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
		"""
		
		# General tab
		croninfos = self.configman.getSchedule()
		if not recommened_setting :	
			if  croninfos :
				self.widgets['main_radio2'].set_active(True)
				if croninfos[0] == 1 :
					self.widgets['time_freq'].set_active(5)
					self.on_time_freq_changed()
					self.widgets['ccronline'].set_text(croninfos[1])
				elif croninfos[0] == 0 :
					if croninfos[1] in self.timefreqs.keys():
						self.widgets['time_freq'].set_active(self.timefreqs[croninfos[1]])
					else :
						self.widgets['time_freq'].set_active(self.timefreqs["never"])
					self.on_time_freq_changed()
			else :
				self.widgets['main_radio3'].set_active(True)
				#self.on_main_radio_toggled()
		if self.configman.has_option("general", "format") :
			cformatOpt = self.configman.get("general", "format") 
			if cformatOpt in ["none","gzip","bzip2"]:
				self.logger.debug("Setting compression format to %s " % self.cformat[cformatOpt])
				self.widgets["cformat"].set_active(self.cformat[cformatOpt])
			else:
				self.logger.debug("Setting compression format to %s " % self.cformat['gzip'])
				self.widgets["cformat"].set_active(self.cformat['gzip'])
			
				
		#Include and exclude tabs
		self.include.clear()
		self.ex_paths.clear()
		if self.configman.has_section("dirconfig") :
			for i,v in self.configman.items( "dirconfig" ) :
				if v=="1":
					self.include.append( [i] )
				elif v =="0":
					self.ex_paths.append( [i] )
		#remote inc
		self.remoteinc.clear()
		if self.configman.has_option("dirconfig", "remote") :
			for i,v in self.configman.get("dirconfig", "remote").iteritems():
				if str(v) == "1":
					self.remoteinc.append( [i] )
				elif v =="0":
					print ("TODO: add a remote ex widget")
					
		# regexp
		self.ex_ftype.clear()
		self.ex_regex.clear()
		if self.configman.has_option("exclude", "regex") :
			list = str(self.configman.get( "exclude", "regex" )).split(",")
			for i in list:
				if re.match( r"\\\.\w+", i ):
					if i[2:] in self.known_ftypes:
						self.ex_ftype.append( [self.known_ftypes[i[2:]], i[2:]] )
					else:
						self.ex_ftype.append( [_("Custom"), i[2:]] )
				else:
					self.ex_regex.append( [i] )
		
		# Set maximum size limits
		if self.configman.has_option("exclude", "maxsize") :
			self.widgets["ex_maxsize"].set_value( self.configman.getint("exclude", "maxsize")/(1024*1024) )
			if self.configman.getint("exclude", "maxsize") < 0:
				self.widgets["ex_maxsize"].set_sensitive( False )
				self.widgets["ex_max"].set_active( False )
			else:
				self.widgets["ex_maxsize"].set_sensitive( True )
				self.widgets["ex_max"].set_active( True )
		
		# Maximum of inc
		if self.configman.has_option("general", "maxincrement") :
			self.widgets["time_maxinc"].set_value( int(self.configman.get("general", "maxincrement")))
	
		# Target 
		if self.configman.has_option("general", "target" ) :
			ctarget = self.configman.get("general", "target" )
			if ctarget.startswith(os.sep) :
				if (os.getuid() == 0 and ctarget == "/var/backup") or (os.getuid() != 0 and ctarget == getUserDatasDir()+"backups"):
					self.widgets["dest1"].set_active( True )
					self.widgets["hbox9"].set_sensitive( False )
					self.widgets["hbox10"].set_sensitive( False )
				else :
					if not os.path.exists(ctarget ): 
						os.makedirs(ctarget)
					self.widgets["dest2"].set_active( True )			
					self.widgets["hbox9"].set_sensitive( True )
					self.widgets["dest_localpath"].set_current_folder( ctarget )
					self.widgets["hbox10"].set_sensitive( False )
			else :
				self.widgets["dest3"].set_active( True )			
				self.widgets["hbox9"].set_sensitive( False )
				self.widgets["hbox10"].set_sensitive( True )
				self.widgets["dest_remote"].set_text( ctarget )
		else :
			self.widgets["dest1"].set_active( True )
			self.widgets["hbox9"].set_sensitive( False )
			self.widgets["hbox10"].set_sensitive( False )
			#self.on_dest1_toggled()
		
		# log
		if self.configman.has_option("log", "level") :
			self.widgets["loglevelcombobox"].set_active(self.loglevels[self.configman.get("log", "level")][1])
		else :
			self.widgets["loglevelcombobox"].set_active(self.loglevels['20'][1])
		
		if self.configman.has_option("log", "file") :
			self.widgets["logfilechooser"].set_current_folder(os.path.dirname(self.configman.get("log", "file")) )
		else : 
			if os.getuid() == 0 :
				self.widgets["logfilechooser"].set_current_folder(os.sep.join(["","var","log"]) )
			else :
				self.widgets["logfilechooser"].set_current_folder(getUserConfDir())
				
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
			if not self.configman.options("report") :
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
	#----------------------------------------------------------------------
	
	#   configlist is like self.conf.items( "dirconfig" ) 
	#	return True if the dir is already included
	#			False if not
	#
	def already_inc (self, configlist, toInclude):
		for i,v in configlist :
			if v=="1" and i == toInclude :
				# the chosen item match an included one 
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Already included item !"))
				dialog.run()
				dialog.destroy()
				return True
		# No match found
		return False
	
	#   configlist is like self.conf.items( "dirconfig" ) 
	#	return True if the dir is already excluded
	#			False if not
	#
	def already_ex (self, configlist, toExclude):
		for i,v in configlist :
			if v=="0" and i == toExclude :
				# the chosen item match an included one 
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Already excluded item !"))
				dialog.run()
				dialog.destroy()
				return True
		# No match found
		return False
	
	#----------------------------------------------------------------------
	
	def cell_remoteinc_edited_callback(self, cell, path, new_text, data):
		# Check if new path is empty
		if (new_text == None) or (new_text == ""):
			dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Empty filename or path. Please enter a valid filename or path."))
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
		if (new_text == None) or (new_text == ""):
			dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Empty expression. Please enter a valid regular expression."))
			dialog.run()
			dialog.destroy()
			return
		
		# Remove old expression and add the new one
		value = self.ex_regex[path][0]
		r = self.configman.get( "exclude", "regex" )
		r = re.sub( r","+re.escape(value) , "", r )
		r = r + r"," + new_text.strip()
		self.configman.set( "exclude", "regex", r )
		self.ex_regex[path][0] = new_text
		self.isConfigChanged()
		

	def cell_edited_callback(self, cell, path, new_text, data):
		# Check if new path is empty
		if (new_text == None) or (new_text == ""):
			dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Empty filename or path. Please enter a valid filename or path."))
			dialog.run()
			dialog.destroy()
			return
		# Check if new path exists and asks the user if path does not exists
		if not os.path.exists(new_text):
			dialog = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_YES_NO, message_format=_("It seems the path you entered does not exists. Do you want to add this wrong path?"))
			response = dialog.run()
			dialog.destroy()
			if response == gtk.RESPONSE_NO:
				return
				
		model, section, value = data
		self.configman.remove_option(section, model[path][0])
		model[path][0] = new_text
		self.configman.set(section, new_text, value)
		self.isConfigChanged()
		
	#----------------------------------------------------------------------

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
		dialog = gtk.FileChooserDialog(_("Save to file ..."), None, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
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

	def on_about_activate(self, *args):
		about = gtk.AboutDialog()
		about.set_name(Infos.NAME)
		# TODO: Always keep this updated
		about.set_version(Infos.VERSION)
		about.set_comments(Infos.DESCRIPTION)
		about.set_transient_for(self.widgets["nssbackupConfApp"])
		about.set_copyright("Oumar Aziz Ouattara <wattazoum@gmail.com>")
		about.set_translator_credits(_("translator-credits"))
		about.set_authors(["Oumar Aziz Ouattara <wattazoum@gmail.com>", "Mathias HOUNGBO <mathias.houngbo@gmail.com>"])
		about.set_website(Infos.WEBSITE)
		about.set_logo(gtk.gdk.pixbuf_new_from_file(Util.getResource("nssbackup-conf.png")))
		about.run()
		about.destroy()

	def on_reload_clicked(self, *args):
		self.configman = ConfigManager(self.conffile)
		self.orig_configman = ConfigManager(self.conffile)
		self.prefillWindow()
		self.isConfigChanged()
		self.logger.debug("Config '%s' loaded" % self.conffile)

	def on_save_clicked(self, *args):
		self.logger.debug("Saving Config")
		self.configman.saveConf()
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
		if self.widgets["main_radio"].get_active():
			# set all values to defaults
		
			self.configman = ConfigManager()
			self.prefillWindow(True)
			self.widgets["time_freq"].set_active( 2 )
			# choose between anacron or cron here (old behaviour has been kept for the moment.
			self.widgets["preciselyRadio"].set_active( True )
			self.widgets["anacronRadio"].set_active( False )
			
			self.widgets["croninfos"].set_sensitive( True )
			self.widgets["time_min"].set_sensitive( True )
			self.widgets["time_hour"].set_sensitive( True )
			self.widgets["time_min"].set_value( 0 )
			self.widgets["time_hour"].set_value( 0 )
			self.widgets["scrolledwindow5"].set_sensitive( False )
			self.widgets["scrolledwindow6"].set_sensitive( False )
			self.widgets["ccronline"].set_sensitive( False )

			self.widgets["purgecheckbox"].set_active( True )
			self.widgets["purgeradiobutton"].set_active( 1 )
			self.widgets["purgedays"].set_sensitive( False )

			# disable all tabs
			self.widgets["vbox3"].set_sensitive( False )
			self.widgets["notebook2"].set_sensitive( False )
			self.widgets["vbox8"].set_sensitive( False )
			self.widgets["vbox9"].set_sensitive( False )
			self.widgets["reportvbox"].set_sensitive( True )

		elif self.widgets["main_radio2"].get_active():
			# enable all tabs
			self.widgets["vbox3"].set_sensitive( True )
			self.widgets["notebook2"].set_sensitive( True )
			self.widgets["vbox8"].set_sensitive( True )
			self.widgets["vbox9"].set_sensitive( True )
			self.widgets["reportvbox"].set_sensitive( True )
			
		elif self.widgets["main_radio3"].get_active():
			# enable all tabs
			self.widgets["vbox3"].set_sensitive( True )
			self.widgets["notebook2"].set_sensitive( True )
			self.widgets["vbox8"].set_sensitive( True )
			self.widgets["vbox9"].set_sensitive( True )
			self.widgets["reportvbox"].set_sensitive( True )
			# disable Time tab
			self.logger.debug("self.widgets['time_freq'].set_active( 0 )")
			self.widgets["time_freq"].set_active( 0 )
			self.widgets["croninfos"].set_sensitive( False )
			self.widgets["ccronline"].set_sensitive( False )

	#----------------------------------------------------------------------
	
	def on_cformat_changed(self, *args):
		"""
		handle that sets the compression format
		"""
		selected = self.widgets["cformat"].get_active_text()
		if selected in self.cformat.keys() :
			self.configman.set("general", "format", selected )
		else :
			self.configman.remove_option("general", "format")
		if selected == "none" :
			# activate split functionality config
			self.widgets['splitsizevbox'].set_sensitive(True)
		else :
			self.widgets["splitsizeCB"].set_active(1)
			self.widgets['splitsizevbox'].set_sensitive(False)
			if self.configman.has_option("general", "splitsize"):
				self.configman.remove_option("general", "splitsize")
			self.on_splitsizeCB_changed()
		self.isConfigChanged()
	
	#----------------------------------------------------------------------
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
		dialog = gtk.FileChooserDialog(_("Include file ..."), None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
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
		dialog = gtk.FileChooserDialog(_("Include folder ..."), None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
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
	
	#----------------------------------------------------------------------

	def on_pluginscombobox_changed(self, *args):
		plist = self.plugin_manager.getPlugins()
		pname = self.widgets['pluginscombobox'].get_active_text()
		plugin = plist[pname]()
		# update the help label
		try :
			self.widgets['fusehelplabel'].set_text(plugin.getdoc())
		except SBException, e :
			self.widgets['fusehelplabel'].set_text(str(e))

	#----------------------------------------------------------------------

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

	#----------------------------------------------------------------------
	
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

	#----------------------------------------------------------------------

	def on_dest1_toggled(self, *args):
		if self.widgets["dest1"].get_active():
			self.widgets["hbox9"].set_sensitive( False )
			self.widgets["hbox10"].set_sensitive( False )
			self.widgets["dest_unusable"].hide()
			if os.getuid() == 0 :
				self.configman.set( "general", "target", "/var/backup/")
				self.isConfigChanged()
			else :
				self.configman.set( "general", "target", getUserDatasDir()+"backups")
				self.isConfigChanged()
		elif self.widgets["dest2"].get_active():
			self.widgets["hbox9"].set_sensitive( True )
			self.widgets["hbox10"].set_sensitive( False )
			self.on_dest_localpath_selection_changed()
		else:
			self.widgets["hbox9"].set_sensitive( False )
			self.widgets["hbox10"].set_sensitive( True )
			self.on_dest_remote_changed()

	def on_ccronline_changed(self, *args):
		self.configman.setSchedule(1, self.widgets['ccronline'].get_text())
		self.isConfigChanged()
		self.logger.debug("Cronline is " +self.configman.get("schedule", "cron"))
		
	
	def on_time_freq_changed(self, *args):
		if self.widgets["time_freq"].get_active()==0:
			# Never is chosen
			self.widgets["croninfos"].set_sensitive( False )
			self.widgets["ccronline"].set_sensitive( False )
			self.widgets["anacronRadio"].set_sensitive( False )
			self.widgets["preciselyRadio"].set_sensitive( False )
			self.widgets["main_radio3"].set_active(True)
			if self.configman.getSchedule() :
				for option in self.configman.options("schedule") :
					self.logger.debug("Removing ('schedule','%s') from config file " % option)
					self.configman.remove_option("schedule", option)
					self.isConfigChanged()
		elif self.widgets["time_freq"].get_active()==5:
			# In custom mode we can't use anacron
			self.widgets["main_radio3"].set_active(False)
			self.widgets["main_radio2"].set_active(True)
			self.widgets["preciselyRadio"].set_active( True )
			self.widgets["anacronRadio"].set_active( False )
			self.widgets["anacronRadio"].set_sensitive( False )
			self.widgets["preciselyRadio"].set_sensitive( False )
			self.widgets["croninfos"].set_sensitive( False )
			self.widgets["ccronline"].set_sensitive( True )
			# set config
			self.on_ccronline_changed()
		else :
			if not self.widgets["main_radio"].get_active() :
				self.widgets["main_radio3"].set_active(False)
				self.widgets["main_radio2"].set_active(True)
			self.widgets["anacronRadio"].set_sensitive( True )
			self.widgets["preciselyRadio"].set_sensitive( True )
			self.widgets["croninfos"].set_sensitive( True )
			self.widgets["ccronline"].set_sensitive( False )
			if self.widgets["preciselyRadio"].get_active() :
				if self.widgets["time_freq"].get_active()==1:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( False )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					# Add in the configfile now
					cmin = str(int(self.widgets["time_min"].get_value()))
					cronline = " ".join([cmin,"*","*","*","*"])
					self.configman.setSchedule(1, cronline)
					self.isConfigChanged()
					
				elif self.widgets["time_freq"].get_active()==2:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					# Add in the configfile now
					cmin = str(int(self.widgets["time_min"].get_value()))
					chour = str(int(self.widgets["time_hour"].get_value()))
					cronline = " ".join([cmin,chour,"*","*","*"])
					self.configman.setSchedule(1, cronline)
					self.isConfigChanged()
					
				elif self.widgets["time_freq"].get_active()==3:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow6"].set_sensitive( True )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					# Add in the configfile now
					cmin = str(int(self.widgets["time_min"].get_value()))
					chour = str(int(self.widgets["time_hour"].get_value()))
					cdow  = self.widgets["time_dowtv"].get_selection().get_selected_rows()[1]
					try:  cdow = str(int(cdow[0][0])+1)
					except: cdow = "1"
					cronline = " ".join([cmin,chour,cdow,"*","*"])
					self.configman.setSchedule(1, cronline)
					self.isConfigChanged()
					
				elif self.widgets["time_freq"].get_active()==4:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					self.widgets["scrolledwindow5"].set_sensitive( True )
					# Add in the configfile now
					cmin = str(int(self.widgets["time_min"].get_value()))
					chour = str(int(self.widgets["time_hour"].get_value()))
					cdom  = self.widgets["time_domtv"].get_selection().get_selected_rows()[1]
					try:  cdom = str(int(cdom[0][0])+1)
					except: cdom = "1"
					cronline = " ".join([cmin,chour,"*",cdom,"*"])
					self.configman.setSchedule(1, cronline)
					self.isConfigChanged()
				# put current cronline into the ccronline widget here
				self.widgets["ccronline"].set_text(cronline)
			else :
				# We are in anacron mode (everything is disable)
				self.widgets["croninfos"].set_sensitive( False )
				self.widgets["ccronline"].set_sensitive( False )
				if self.widgets["time_freq"].get_active()==1:			
					self.configman.setSchedule(0, "hourly")
					self.isConfigChanged()
					self.logger.debug("AnaCronline is " +self.configman.get("schedule", "anacron"))
				elif self.widgets["time_freq"].get_active()==2:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					self.widgets["ccronline"].set_sensitive( False )
					self.configman.setSchedule(0, "daily")
					self.isConfigChanged()
					self.logger.debug("AnaCronline is " +self.configman.get("schedule", "anacron"))
				elif self.widgets["time_freq"].get_active()==3:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow6"].set_sensitive( True )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["ccronline"].set_sensitive( False )
					self.configman.setSchedule(0, "weekly")
					self.isConfigChanged()
					self.logger.debug("AnaCronline is " +self.configman.get("schedule", "anacron"))
				elif self.widgets["time_freq"].get_active()==4:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					self.widgets["scrolledwindow5"].set_sensitive( True )
					self.widgets["ccronline"].set_sensitive( False )
					self.configman.setSchedule(0, "monthly")
					self.isConfigChanged()
					self.logger.debug("AnaCronline is " +self.configman.get("schedule", "anacron"))

	#----------------------------------------------------------------------
	
	def on_time_domtv_cursor_changed(self, *args):
		# Add in the configfile now
		cmin = str(int(self.widgets["time_min"].get_value()))
		chour = str(int(self.widgets["time_hour"].get_value()))
		cdom  = self.widgets["time_domtv"].get_selection().get_selected_rows()[1]
		try:  cdom = str(int(cdom[0][0])+1)
		except: cdom = "1"
		cronline = " ".join([cmin,chour,"*",cdom,"*"])
		self.configman.setSchedule(1, cronline)
		self.isConfigChanged()
		# put current cronline into the ccronline widget here
		self.widgets["ccronline"].set_text(cronline)
		
		
	def on_time_dowtv_cursor_changed(self, *args):
		# Add in the configfile now
		cmin = str(int(self.widgets["time_min"].get_value()))
		chour = str(int(self.widgets["time_hour"].get_value()))
		cdow  = self.widgets["time_dowtv"].get_selection().get_selected_rows()[1]
		try:  cdow = str(int(cdow[0][0])+1)
		except: cdow = "1"
		cronline = " ".join([cmin,chour,cdow,"*","*"])
		self.configman.setSchedule(1, cronline)
		self.isConfigChanged()
		# put current cronline into the ccronline widget here
		self.widgets["ccronline"].set_text(cronline)

	def on_time_hour_changed(self, *args):
		# Add in the configfile now
		cmin = str(int(self.widgets["time_min"].get_value()))
		chour = str(int(self.widgets["time_hour"].get_value()))
		# if every day is selected, 
		if self.widgets["time_freq"].get_active()==2:	
			cronline = " ".join([cmin,chour,"*","*","*"])
		else:
			if self.widgets["time_freq"].get_active()==3:
				cdow  = self.widgets["time_dowtv"].get_selection().get_selected_rows()[1]
				try:  cdow = str(int(cdow[0][0])+1)
				except: cdow = "1"
				cronline = " ".join([cmin,chour,cdow,"*","*"])
			elif self.widgets["time_freq"].get_active()==4:
				cdom  = self.widgets["time_domtv"].get_selection().get_selected_rows()[1]
				try:  cdom = str(int(cdom[0][0])+1)
				except: cdom = "1"
				cronline = " ".join([cmin,chour,"*",cdom,"*"])
		self.configman.setSchedule(1, cronline)
		self.isConfigChanged()
		# put current cronline into the ccronline widget here
		self.widgets["ccronline"].set_text(cronline)
		
	def on_time_min_changed(self, *args):
		# Add in the configfile now
		cmin = str(int(self.widgets["time_min"].get_value()))
		# if every day is selected, 
		if self.widgets["time_freq"].get_active()==1:	
			cronline = " ".join([cmin,"*","*","*","*"])
		else:
			chour = str(int(self.widgets["time_hour"].get_value()))
			if self.widgets["time_freq"].get_active()==2:	
				cronline = " ".join([cmin,chour,"*","*","*"])
			elif self.widgets["time_freq"].get_active()==3:
				cdow  = self.widgets["time_dowtv"].get_selection().get_selected_rows()[1]
				try:  cdow = str(int(cdow[0][0])+1)
				except: cdow = "1"
				cronline = " ".join([cmin,chour,cdow,"*","*"])
			elif self.widgets["time_freq"].get_active()==4:
				cdom  = self.widgets["time_domtv"].get_selection().get_selected_rows()[1]
				try:  cdom = str(int(cdom[0][0])+1)
				except: cdom = "1"
				cronline = " ".join([cmin,chour,"*",cdom,"*"])
		self.configman.setSchedule(1, cronline)
		self.isConfigChanged()
		# put current cronline into the ccronline widget here
		self.widgets["ccronline"].set_text(cronline)
		
	def on_time_maxinc_changed(self,*args):
		# add maxinc to the config
		self.configman.set("general", "maxincrement", int(self.widgets["time_maxinc"].get_value())) 
		self.isConfigChanged()
	
	#----------------------------------------------------------------------

	def on_anacronRadio_toggled(self, *args):
		if self.widgets["anacronRadio"].get_active() :
			self.widgets["croninfos"].set_sensitive( False )
			self.widgets["ccronline"].set_sensitive( False )
			self.widgets["anacronRadio"].set_sensitive( True )
			self.widgets["preciselyRadio"].set_sensitive( True )
		elif self.widgets["preciselyRadio"].get_active() :
			self.widgets["croninfos"].set_sensitive( True )
			self.on_time_freq_changed()

	#----------------------------------------------------------------------

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
			
	#----------------------------------------------------------------------

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
		
	#----------------------------------------------------------------------

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

	#----------------------------------------------------------------------

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
				
	#----------------------------------------------------------------------

	def on_TLScheckbutton_toggled(self, *args):
		if not self.widgets['TLScheckbutton'].get_active():
			self.widgets['TLSinfos'].set_sensitive(False)
			if self.configman.has_option("report", "smpttls") :
				self.configman.remove_option("report", "smpttls")
			if self.configman.has_option("report", "smptcert") :
				self.configman.remove_option("report", "smptcert")
			if self.configman.has_option("report", "smptkey") :
				self.configman.remove_option("report", "smptkey")
			if self.configman.has_option("report", "smtptls") :
				self.configman.remove_option("report", "smtptls")
			self.isConfigChanged()
		else :
			self.configman.set("report", "smtptls","1")
			self.isConfigChanged()
			self.widgets['TLSinfos'].set_sensitive(True)
			self.on_TLSradiobutton_toggled()
			

	#----------------------------------------------------------------------

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


#----------------------------------------------------------------------

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

	#----------------------------------------------------------------------

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

	#----------------------------------------------------------------------

	def on_ex_addregex_clicked(self, *args):
		dialog = self.widgets["regexdialog"]
		response = dialog.run()
		dialog.hide()
		if response == gtk.RESPONSE_OK:
			regex = self.widgets["regex_box"].get_text()
			
			if self.configman.has_option("exclude", "regex") :
				r = self.configman.get( "exclude", "regex" )
			else:
				r=""
			r = r + r"," + regex.strip()
			self.configman.set( "exclude", "regex", r )
			
			self.ex_regex.append( [regex] )
			self.isConfigChanged()
		elif response == gtk.RESPONSE_CANCEL:
			pass
	
	#----------------------------------------------------------------------

	def on_ex_delregex_clicked(self, *args):
		(store, iter) = self.ex_regextv.get_selection().get_selected()
		if store and iter:
			value = store.get_value( iter, 0 )
			r = self.configman.get( "exclude", "regex" )
			r = re.sub( r","+re.escape(value) , "", r )
			self.configman.set( "exclude", "regex", r )
			self.isConfigChanged()
			store.remove( iter )

	#----------------------------------------------------------------------

	def on_includetv_key_press_event(self, widget, event, *args):
		if event.keyval == gtk.keysyms.Delete :
			self.on_inc_del_clicked()
	
	#----------------------------------------------------------------------
	
	def on_remote_includetv_key_press_event(self, widget, event, *args):
		if event.keyval == gtk.keysyms.Delete :
			self.on_remote_inc_del_clicked()
	
	#----------------------------------------------------------------------
	
	def on_ex_pathstv_key_press_event(self, widget, event, *args):
		if event.keyval == gtk.keysyms.Delete :
			self.on_ex_delpath_clicked()
	
	#----------------------------------------------------------------------

	def on_ex_ftypetv_key_press_event(self, widget, event, *args):
		if event.keyval == gtk.keysyms.Delete :
			self.on_ex_delftype_clicked()
	
	#----------------------------------------------------------------------
	
	def on_ex_regextv_key_press_event(self, widget, event, *args):
		if event.keyval == gtk.keysyms.Delete :
			self.on_ex_delregex_clicked()

	#----------------------------------------------------------------------

	def on_ex_max_toggled(self, *args):
		if self.widgets["ex_max"].get_active():
			self.widgets["ex_maxsize"].set_sensitive( True )
			self.on_ex_maxsize_changed()
		elif not self.widgets["ex_max"].get_active():
			self.widgets["ex_maxsize"].set_sensitive( False )
			self.configman.remove_option("exclude", "maxsize")
			self.isConfigChanged()

	def on_ex_maxsize_changed(self, *args):
		self.configman.set( "exclude", "maxsize", str(int(self.widgets["ex_maxsize"].get_value())*1024*1024) )
		self.isConfigChanged()
	
	#----------------------------------------------------------------------
	
	def on_dest_localpath_selection_changed(self, *args):
		t = self.widgets["dest_localpath"].get_filename()
		if (os.path.isdir( t ) and os.access( t, os.R_OK | os.W_OK | os.X_OK ) ):
			self.configman.set( "general", "target", t )
			self.isConfigChanged()
			self.widgets["dest_unusable"].hide()
		else:
			self.widgets["dest_unusable"].show()

	#----------------------------------------------------------------------

	def on_dest_remote_changed(self, *args):
		self.widgets["dest_remote_light1"].set_from_stock( gtk.STOCK_DIALOG_WARNING , gtk.ICON_SIZE_BUTTON)
		gtk.tooltips_data_get(self.widgets["eventbox"])[0].set_tip(self.widgets["eventbox"], _("Please test writability of the target directory by pressing \"Test\" button on the right."))
		self.configman.set( "general", "target", self.widgets['dest_remote'].get_text() )
		self.isConfigChanged()

	#----------------------------------------------------------------------
	
	def on_dest_remotetest_clicked(self, *args):
		_fusefam = FuseFAM()
		try :
			if (_fusefam.testFusePlugins(self.widgets['dest_remote'].get_text())) :
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
	
	#----------------------------------------------------------------------

	def on_logfilechooser_selection_changed(self, *args):
		self.configman.set("log", "file", self.widgets['logfilechooser'].get_filename()+os.sep+"nssbackup.log")
		self.isConfigChanged()
		self.logger.debug("Log file : " + self.configman.get("log", "file"))

	#----------------------------------------------------------------------

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
			self.configman.set("log", "level", "50")
			self.isConfigChanged()
			self.logger.debug("Log level : " + self.configman.get("log", "level"))
		elif self.widgets['loglevelcombobox'].get_active_text() == "Warning" :
			self.configman.set("log", "level", "30")
			self.isConfigChanged()
			self.logger.debug("Log level : " + self.configman.get("log", "level"))

	#----------------------------------------------------------------------

	def on_smtpfrom_changed(self, *args):
		if self.widgets['smtpfrom'].get_text() != "":
			self.configman.set("report", "from", self.widgets['smtpfrom'].get_text())
			self.isConfigChanged()
		else :
			self.configman.remove_option("report", "from")
			self.isConfigChanged()

	#----------------------------------------------------------------------

	def on_smtpto_changed(self, *args):
		if self.widgets['smtpto'].get_text() != "":
			self.configman.set("report", "to", self.widgets['smtpto'].get_text())
			self.isConfigChanged()
		else :
			self.configman.remove_option("report", "to")
			self.isConfigChanged()
	#----------------------------------------------------------------------

	def on_smtpserver_changed(self, *args):
		if self.widgets['smtpserver'].get_text() != "":
			self.configman.set("report", "smtpserver", self.widgets['smtpserver'].get_text())
			self.isConfigChanged()
		else :
			self.configman.remove_option("report", "smtpserver")
			self.isConfigChanged()
		
	#----------------------------------------------------------------------

	def on_smtpport_changed(self, *args):
		if self.widgets['smtpport'].get_text() != "":
			self.configman.set("report", "smtpport", self.widgets['smtpport'].get_text())
			self.isConfigChanged()
		else :
			self.configman.remove_option("report", "smtpport")
			self.isConfigChanged()
		
	#----------------------------------------------------------------------

	def on_smtplogin_changed(self, *args):
		if self.widgets['smtplogin'].get_text() != "":
			self.configman.set("report", "smtpuser", self.widgets['smtplogin'].get_text())
			self.isConfigChanged()
		else :
			self.configman.remove_option("report", "smtpuser")
			self.isConfigChanged()
		
	#----------------------------------------------------------------------

	def on_smtppassword_changed(self, *args):
		if self.widgets['smtppassword'].get_text() != "":
			self.configman.set("report", "smtppassword", self.widgets['smtppassword'].get_text())
			self.isConfigChanged()
		else :
			self.configman.remove_option("report", "smtppassword")
			self.isConfigChanged()
	#----------------------------------------------------------------------

	def on_crtfilechooser_selection_changed(self, *args):
		self.configman.set("report", "smtpcert", self.widgets['crtfilechooser'].get_filename())
		self.isConfigChanged()
		self.logger.debug("Certificate : " + str(self.configman.get("report", "smtpcert")))

	#----------------------------------------------------------------------

	def on_keyfilechooser_selection_changed(self, *args):
		self.configman.set("report", "smtpkey", self.widgets['keyfilechooser'].get_filename())
		self.isConfigChanged()
		self.logger.debug("Key : " + str(self.configman.get("report", "smtpkey")))

	#----------------------------------------------------------------------

	def gtk_main_quit( self, *args):
		self.askSaveConfig()
		gtk.main_quit()

	#----------------------------------------------------------------------

	def on_ftype_custom_ex_changed(self, *args):
		print("TODO: on_ftype_custom_ex_changed")
		pass

	#----------------------------------------------------------------------

	def on_prfManager_activate(self, *args):
		"""
		Launch Profile manager dialog
		"""
		self.askSaveConfig()
		
		dialog = self.widgets["ProfileManagerDialog"]
		dialog.run()
		dialog.hide()


	#----------------------------------------------------------------------

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
		
		
		
	#----------------------------------------------------------------------

	def on_removeProfileButton_clicked(self, *args):
		
		tm, iter = self.profilestv.get_selection().get_selected()
		
		if not iter :
			dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("Please select a Profile !"))
			dialog.run()
			dialog.destroy()
			return 
		
		prfName, prfConf = tm.get_value(iter,1), tm.get_value(iter,2)
		
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

	#----------------------------------------------------------------------

	def on_editProfileButton_clicked(self, *args):
		
		tm, iter = self.profilestv.get_selection().get_selected()
		prfName, prfConf = tm.get_value(iter,1), tm.get_value(iter,2)
		self.logger.debug("Load Profile '%s' configuration" % prfName)
		
		self.conffile = prfConf
		self.on_reload_clicked()
		self.widgets["ProfileManagerDialog"].hide()

	#----------------------------------------------------------------------

	def on_closeProfileManagerButton_clicked(self, *args):
		"""
		Load the default configuration file
		"""
		self.logger.debug("Load the default configuration file '%s'" % self.default_conffile)
		self.conffile = self.default_conffile
		self.on_reload_clicked()
		
	#-----------------------------------------------------------------------
	
	def on_prfEnableCB_toggled(self,*args):
		
		tm, iter = self.profilestv.get_selection().get_selected()
		enable, prfName, prfConf =tm.get_value(iter,0), tm.get_value(iter,1), tm.get_value(iter,2)
		
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
		


#----------------------------------------------------------------------

def main(argv):

	w = SBconfigGTK()
	w.show()
	gtk.main()
	
