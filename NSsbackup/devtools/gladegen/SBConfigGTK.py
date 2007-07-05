#!/usr/bin/env python
    
#----------------------------------------------------------------------
# SBConfigGTK.py
# Ouattara Aziz
# 06/16/2007
#----------------------------------------------------------------------

import re
import subprocess
import sys
import os
import time
import locale
import sbackup.managers.FileAccessManager as FAM
from sbackup.util.log import getLogger
from sbackup.util.exceptions import SBException
from sbackup.managers.ConfigManager import ConfigManager
from GladeWindow import *
from gettext import gettext as _

#----------------------------------------------------------------------

class SBconfigGTK(GladeWindow):
	
	configman = None
    #----------------------------------------------------------------------

	def __init__(self):
		''' '''
		self.init()

    #----------------------------------------------------------------------

	def init(self):

		filename = '/usr/local/share/sbackup/simple-backup-config.glade'

		widget_list = [
			'dialog-vbox4',
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
			'backup_properties_dialog',
			'vbox17',
			'save',
			'save_as',
			'exit',
			'about',
			'vbox1',
			'notebook',
			'vbox2',
			'main_radio',
			'hbox1',
			'main_radio2',
			'hbox2',
			'main_radio3',
			'hbox3',
			'vbox3',
			'scrolledwindow1',
			'includetv',
			'inc_addfile',
			'hbox4',
			'inc_adddir',
			'hbox5',
			'inc_del',
			'scrolledwindow7',
			'remote_includetv',
			'remote_inc_add',
			'remote_inc_del',
			'test_remote',
			'hbox23',
			'notebook2',
			'vbox4',
			'scrolledwindow2',
			'ex_pathstv',
			'ex_addfile',
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
			'dest_remote',
			'dest_remotetest',
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
			'dialog-vbox3',
			'vbox10',
			'hbox27',
			'pluginscombobox',
			'hbox24',
			'remote_inc_entry',
			'fusecheckbutton',
			'hbox26',
			'remote_inc_okbutton',
			'button2',
			]

		handlers = [
			'on_ftype_toggled',
			'on_ftype_st_box_changed',
			'on_ftype_custom_ex_changed',
			'gtk_main_quit',
			'on_save_activate',
			'on_save_as_activate',
			'on_about_activate',
			'on_reload_clicked',
			'on_save_clicked',
			'on_backup_clicked',
			'on_main_radio_toggled',
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
			'on_ex_maxsize_value_changed',
			'on_dest1_toggled',
			'on_dest_localpath_selection_changed',
			'on_dest_remote_changed',
			'on_dest_remotetest_clicked',
			'on_time_freq_changed',
			'on_anacronRadio_toggled',
			'on_ccronline_changed',
			'on_purgecheckbox_toggled',
			'on_purgeradiobutton_toggled',
			'on_purgedays_changed',
			'on_loglevelcombobox_changed',
			'on_logfilechooser_selection_changed',
			'on_smtpport_changed',
			'on_smtpserver_changed',
			'on_smtpto_changed',
			'on_smtpfrom_changed',
			'on_testMailButton_clicked',
			'on_smtplogincheckbox_toggled',
			'on_smtppassword_changed',
			'on_smtplogin_changed',
			'on_TLScheckbutton_toggled',
			'on_TLSradiobutton_toggled',
			'on_crtfilechooser_selection_changed',
			'on_keyfilechooser_selection_changed',
			'on_pluginscombobox_changed',
			'on_fusecheckbutton_clicked',
			'gtk_widget_hide',
			]

		top_window = 'backup_properties_dialog'
		GladeWindow.__init__(self, filename, top_window, widget_list, handlers)
	#----------------------------------------------------------------------
		
	def prefillWindow(self):
		"""
		Prefill the GTK window with config infos
		"""
		# General tab
		croninfos = self.configman.getSchedule()
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
			self.on_main_radio_toggled()
			
		#Include and exclude tabs
		self.include.clear()
		self.ex_paths.clear()
		if self.configman.has_section("dirconfig") :
			for i,v in self.configman.items( "dirconfig" ) :
				if v=="1":
					self.include.append( [i] )
				else:
					self.ex_paths.append( [i] )
		
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
			self.on_dest1_toggled()
		
		# log
		if self.configman.has_option("log", "level") :
			self.widgets["loglevelcombobox"].set_active(self.loglevels[self.configman.get("log", "level")][1])
		else :
			self.widgets["loglevelcombobox"].set_active(self.loglevels['Info'])
		
		if self.configman.has_option("log", "file") :
			self.widgets["logfilechooser"].set_current_folder(os.path.dirname(self.configman.get("log", "file")) )
		else : 
			if os.getuid() == 0 :
				self.widgets["logfilechooser"].set_current_folder(os.sep.join("","var","log") )
			else :
				self.widgets["logfilechooser"].set_current_folder(os.sep.join(os.getenv("HOME"),".sbackup") )
				
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
				self.widgets['smtplogininfo'].set_sensitive(False)
				self.widgets['TLSinfos'].set_sensitive(False)
				unfillreportentries()
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
			self.widgets['smtplogininfo'].set_sensitive(False)
			self.widgets['TLSinfos'].set_sensitive(False)
			unfillreportentries()
			
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
		print("TODO: on_save_as_activate")
		pass

	def on_exit_activate(self, *args):
		gtk.main_quit()

	def on_about_activate(self, *args):
		about = gtk.AboutDialog()
		about.set_name(_("Simple Backup Suite"))
		about.set_version("0.10.3")
		about.set_comments(_("This is a user friendly backup solution for common desktop needs. The project was was sponsored by Google during Google Summer of Code 2005 and mentored by Ubuntu."))
		about.set_transient_for(self.widgets["backup_properties_dialog"])
		about.set_copyright("Aigars Mahinovs <aigarius@debian.org>")
		about.set_translator_credits(_("translator-credits"))
		about.set_authors(["Oumar Aziz Ouattara <wattazoum@gmail.com>" ,
						"Aigars Mahinovs <aigarius@debian.org>",
				   		"Jonh Wendell <wendell@bani.com.br>"])
		about.set_website("http://sourceforge.net/projects/sbackup/")
		about.set_logo(gtk.gdk.pixbuf_new_from_file("/usr/share/pixmaps/sbackup-conf.png"))
		about.run()
		about.destroy()

	def on_reload_clicked(self, *args):
		if os.geteuid() == 0 :
			if FAM.exist("/etc/sbackup.conf") :
				self.configman = ConfigManager("/etc/sbackup.conf")
			else :
				self.configman = ConfigManager()
		else :
			if FAM.exists(os.getenv("HOME")+os.sep.join(["",".sbackup","sbackup.conf"])) :
				self.configman = ConfigManager(os.getenv("HOME")+os.sep.join(["",".sbackup","sbackup.conf"]))
			else :
				self.configman = ConfigManager()
		self.prefillWindow()		
		getLogger().debug("Config reloaded")

	def on_save_clicked(self, *args):
		getLogger().debug("Saving Config")
		self.configman.saveConf()

	def on_backup_clicked(self, *args):
		print("TODO: on_backup_clicked")
		retval = subprocess.call(["python","../sbackupd.py"])
		pid = os.spawnl( os.P_NOWAIT, "python ../sbackupd.py" )
		dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=_("A backup run is initiated in the background. The process id is: ")+str(pid)+".")
		dialog.run()
		dialog.destroy()
		pass

	def on_main_radio_toggled(self, *args):
		if self.widgets["main_radio"].get_active():
			# set all values to defaults
		
			self.configman = ConfigManager()
			
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
			getLogger().debug("self.widgets['time_freq'].set_active( 0 )")
			self.widgets["time_freq"].set_active( 0 )
			self.widgets["croninfos"].set_sensitive( False )
			self.widgets["ccronline"].set_sensitive( False )

	#----------------------------------------------------------------------
	
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
		elif response == gtk.RESPONSE_CANCEL:
		    pass
		dialog.destroy()

	def on_inc_del_clicked(self, *args):
		(store, iter) = self.includetv.get_selection().get_selected()
		if store and iter:
			value = store.get_value( iter, 0 )
			self.configman.remove_option( "dirconfig", value )
			store.remove( iter )

	def on_remote_inc_add_clicked(self,*args):
		print ("TODO: on_remote_inc_add_clicked")
		question = self.widgets['remote_inc_dialog']
		response = question.run()
		question.hide()
		if response == gtk.RESPONSE_OK:
			entry = self.widgets["remote_inc_entry"].get_text()
			getLogger().debug("Entry : '%s'"% entry)
			self.remoteinc.append( [entry] )
			self.configman.set( "dirconfig", "remote", {entry:1} )
			getLogger().debug("Entry in dirconf:'%s' " % self.configman.get("dirconfig", "remote"))
		elif response == gtk.RESPONSE_CANCEL:
			pass
		else : 
			getLogger().debug("Response : '%s'" % str(response))
		
	
	def on_remote_inc_del_clicked(self,*args):
		print ("TODO: on_remote_inc_del_clicked")
	
	def on_test_remote_clicked(self,*args):
		print ("TODO: on_test_remote_clicked ")

	def on_ex_addfile_clicked(self, *args):
		print("TODO: on_ex_addfile1_clicked")
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
		elif response == gtk.RESPONSE_CANCEL:
		    pass
		dialog.destroy()

	def on_ex_adddir_clicked(self, *args):
		print("TODO: on_ex_adddir1_clicked")
		dialog = gtk.FileChooserDialog(_("Exclude folder ..."), None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		
		response = dialog.run()
		if response == gtk.RESPONSE_OK and not self.already_ex(self.configman.items( "dirconfig" ),dialog.get_filename()+"/"):
			self.ex_paths.append( [dialog.get_filename()+"/"] )
			self.configman.set( "dirconfig", dialog.get_filename()+"/", "0" )
		elif response == gtk.RESPONSE_CANCEL:
			pass
		dialog.destroy()

	def on_ex_delpath_clicked(self, *args):
		print("TODO: on_ex_delpath1_clicked")
		(store, iter) = self.ex_pathstv.get_selection().get_selected()
		if store and iter:
			value = store.get_value( iter, 0 )
			self.configman.remove_option( "dirconfig", value )
			store.remove( iter )

	#----------------------------------------------------------------------

	def on_dest1_toggled(self, *args):
		print("TODO: on_dest1_toggled")
		if self.widgets["dest1"].get_active():
			self.widgets["hbox9"].set_sensitive( False )
			self.widgets["hbox10"].set_sensitive( False )
			self.widgets["dest_unusable"].hide()
			if os.getuid() == 0 :
				self.configman.set( "general", "target", "/var/backup/")
			else :
				self.configman.set( "general", "target", os.sep.join([os.getenv("HOME"),"backup"]))
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
		getLogger().debug("Cronline is " +self.configman.get("schedule", "cron"))
		
	
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
					getLogger().debug("Removing ('schedule','%s') from config file " % option)
					self.configman.remove_option("schedule", option)
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
			if self.widgets["preciselyRadio"].get_active() :
				if self.widgets["time_freq"].get_active()==1:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( False )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					self.widgets["ccronline"].set_sensitive( False )
					print ("TODO: Add in the configfile now")
				elif self.widgets["time_freq"].get_active()==2:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					self.widgets["ccronline"].set_sensitive( False )
					print ("TODO: Add in the configfile now")
				elif self.widgets["time_freq"].get_active()==3:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow6"].set_sensitive( True )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["ccronline"].set_sensitive( False )
					print ("TODO: Add in the configfile now")
				elif self.widgets["time_freq"].get_active()==4:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					self.widgets["scrolledwindow5"].set_sensitive( True )
					self.widgets["ccronline"].set_sensitive( False )
					print ("TODO: Add in the configfile now")
					# TODO : put current cronline into the ccronline widget here
			# We are in anacron mode (everything is disable)
			else :
				self.widgets["croninfos"].set_sensitive( False )
				self.widgets["ccronline"].set_sensitive( False )
				if self.widgets["time_freq"].get_active()==1:			
					self.configman.setSchedule(0, "hourly")
					getLogger().debug("AnaCronline is " +self.configman.get("schedule", "anacron"))
				elif self.widgets["time_freq"].get_active()==2:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					self.widgets["ccronline"].set_sensitive( False )
					self.configman.setSchedule(0, "daily")
					getLogger().debug("AnaCronline is " +self.configman.get("schedule", "anacron"))
				elif self.widgets["time_freq"].get_active()==3:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow6"].set_sensitive( True )
					self.widgets["scrolledwindow5"].set_sensitive( False )
					self.widgets["ccronline"].set_sensitive( False )
					self.configman.setSchedule(0, "weekly")
					getLogger().debug("AnaCronline is " +self.configman.get("schedule", "anacron"))
				elif self.widgets["time_freq"].get_active()==4:
					self.widgets["time_min"].set_sensitive( True )
					self.widgets["time_hour"].set_sensitive( True )
					self.widgets["scrolledwindow6"].set_sensitive( False )
					self.widgets["scrolledwindow5"].set_sensitive( True )
					self.widgets["ccronline"].set_sensitive( False )
					self.configman.setSchedule(0, "monthly")
					getLogger().debug("AnaCronline is " +self.configman.get("schedule", "anacron"))

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
		if self.widgets["purgecheckbox"].get_active():
		    self.widgets["purgedays"].set_sensitive( True )
		    try: i = int(self.widgets["purgedays"].get_text())
		    except: i = -1
		    if not ( i>0 and i<10000 ):	i=30
		    self.widgets["purgedays"].set_text(str(i))
		    self.configman.set( "general", "purge", str(i) )
		else:
		    self.widgets["purgedays"].set_sensitive( False )
		    self.configman.set( "general", "purge", "log" )

	#----------------------------------------------------------------------

	def on_purgeradiobutton_toggled(self, *args):
		if self.widgets["purgecheckbox"].get_active():
		    self.widgets["purgedays"].set_sensitive( True )
		    try: i = int(self.widgets["purgedays"].get_text())
		    except: i = -1
		    if not ( i>0 and i<10000 ):	i=30
		    self.widgets["purgedays"].set_text(str(i))
		    self.configman.set( "general", "purge", str(i) )
		else:
		    self.widgets["purgedays"].set_sensitive( False )
		    self.configman.set( "general", "purge", "log" )

	def on_purgedays_changed( self, *args ):
		try: i = int(self.widgets["purgedays"].get_text())
		except: i = -1
		if not ( i>0 and i<10000 ):	i=30
		print i
		self.configman.set( "general", "purge", str(i) )
		
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
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format="Test Succeeded !")
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
		else :
			self.widgets['smtplogininfo'].set_sensitive(True)
			if self.widgets['smtplogin'].get_text() :
				self.configman.set("report", "smtpuser",self.widgets['smtplogin'].get_text())
				getLogger().debug("login : " + self.configman.get("report", "smtpuser"))
			if self.widgets['smtppassword'].get_text() :
				self.configman.set("report", "smtpuser", self.widgets['smtppassword'].get_text())
				getLogger().debug("Password : " + self.configman.get("report", "smtppassword"))
				
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
		else :
			self.configman.set("report", "smtptls","1")
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

			if ftype in self.known_ftypes:
				self.ex_ftype.append( [self.known_ftypes[ftype], ftype] )
			else:
				self.ex_ftype.append( [_("Custom"), ftype] )

			r = self.configman.get( "exclude", "regex" )
			r = r + r",\." + ftype.strip()
			self.configman.set( "exclude", "regex", r )
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
			store.remove( iter )		

	#----------------------------------------------------------------------

	def on_ex_addregex_clicked(self, *args):
		dialog = self.widgets["regexdialog"]
		response = dialog.run()
		dialog.hide()
		if response == gtk.RESPONSE_OK:
			regex = self.widgets["regex_box"].get_text()
			
			self.ex_regex.append( [regex] )
			r = self.configman.get( "exclude", "regex" )
			r = r + r"," + regex.strip()
			self.configman.set( "exclude", "regex", r )
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
			store.remove( iter )

	#----------------------------------------------------------------------

	def on_ex_maxsize_value_changed(self, *args):
		if not self.widgets["ex_max"].get_active():
			self.widgets["ex_maxsize"].set_sensitive( False )
			self.configman.set( "exclude", "maxsize", "-1" )
		else:
			self.widgets["ex_maxsize"].set_sensitive( True )
			self.configman.set( "exclude", "maxsize", str(int(self.widgets["ex_maxsize"].get_value())*1024*1024) )
	
	#----------------------------------------------------------------------
	
	def on_dest_localpath_selection_changed(self, *args):
		t = self.widgets["dest_localpath"].get_filename()
		if (os.path.isdir( t ) and os.access( t, os.R_OK | os.W_OK | os.X_OK ) ):
			self.configman.set( "general", "target", t )
			self.widgets["dest_unusable"].hide()
		else:
			self.widgets["dest_unusable"].show()

	#----------------------------------------------------------------------

	def on_dest_remote_changed(self, *args):
		self.widgets["dest_remote_light1"].set_from_stock( gtk.STOCK_DIALOG_WARNING , gtk.ICON_SIZE_BUTTON)
		gtk.tooltips_data_get(self.widgets["eventbox"])[0].set_tip(self.widgets["eventbox"], "Please test writability of the target directory by pressing \"Test\" button on the right.")
		self.configman.set( "general", "target", self.widgets['dest_remote'].get_text() )

	#----------------------------------------------------------------------
	
	def on_dest_remotetest_clicked(self, *args):
		from sbackup.managers.FuseFAM import FuseFAM
		_fusefam = FuseFAM()
		try :
			if (_fusefam.testFusePlugins(self.widgets['dest_remote'].get_text())) :
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format="Test Succeeded !")
				dialog.run()
				dialog.destroy()
				
				self.widgets["dest_unusable"].hide()
				self.widgets["dest_remote_light1"].set_from_stock( gtk.STOCK_YES , gtk.ICON_SIZE_BUTTON )
				gtk.tooltips_data_get(self.widgets["eventbox"])[0].set_tip(self.widgets["eventbox"], "Target directory is writable.")
				
		except Exception, e: 
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
				dialog.run()
				dialog.destroy()
				
				self.widgets["dest_remote_light1"].set_from_stock( gtk.STOCK_DIALOG_ERROR , gtk.ICON_SIZE_BUTTON )
				gtk.tooltips_data_get(self.widgets["eventbox"])[0].set_tip(self.widgets["eventbox"], "Please change target directory and test writability of the target directory by pressing \"Test\" button on the right.")
				self.widgets["dest_unusable"].show()
	
	#----------------------------------------------------------------------

	def on_logfilechooser_selection_changed(self, *args):
		self.configman.set("log", "file", self.widgets['logfilechooser'].get_filename()+os.sep+"sbackup.log")
		getLogger().debug("Log file : " + self.configman.get("log", "file"))

	#----------------------------------------------------------------------

	def on_loglevelcombobox_changed(self, *args):
		if self.widgets['loglevelcombobox'].get_active_text() == "Info" :
			self.configman.set("log", "level", "20")
			getLogger().debug("Log level : " + self.configman.get("log", "level"))
		elif self.widgets['loglevelcombobox'].get_active_text() == "Debug" :
			self.configman.set("log", "level", "10")
			getLogger().debug("Log level : " + self.configman.get("log", "level"))
		elif self.widgets['loglevelcombobox'].get_active_text() == "Error" :
			self.configman.set("log", "level", "50")
			getLogger().debug("Log level : " + self.configman.get("log", "level"))
		elif self.widgets['loglevelcombobox'].get_active_text() == "Warning" :
			self.configman.set("log", "level", "30")
			getLogger().debug("Log level : " + self.configman.get("log", "level"))

	#----------------------------------------------------------------------

	def on_smtpfrom_changed(self, *args):
		if self.widgets['smtpfrom'].get_text() != "":
			self.configman.set("report", "from", self.widgets['smtpfrom'].get_text())
		else :
			self.configman.remove_option("report", "from")

	#----------------------------------------------------------------------

	def on_smtpto_changed(self, *args):
		if self.widgets['smtpto'].get_text() != "":
			self.configman.set("report", "to", self.widgets['smtpto'].get_text())
		else :
			self.configman.remove_option("report", "to")
	#----------------------------------------------------------------------

	def on_smtpserver_changed(self, *args):
		if self.widgets['smtpserver'].get_text() != "":
			self.configman.set("report", "smtpserver", self.widgets['smtpserver'].get_text())
		else :
			self.configman.remove_option("report", "smtpserver")
		
	#----------------------------------------------------------------------

	def on_smtpport_changed(self, *args):
		if self.widgets['smtpport'].get_text() != "":
			self.configman.set("report", "smtpport", self.widgets['smtpport'].get_text())
		else :
			self.configman.remove_option("report", "smtpport")
		
	#----------------------------------------------------------------------

	def on_smtplogin_changed(self, *args):
		if self.widgets['smtplogin'].get_text() != "":
			self.configman.set("report", "smtpuser", self.widgets['smtplogin'].get_text())
		else :
			self.configman.remove_option("report", "smtpuser")
		
	#----------------------------------------------------------------------

	def on_smtppassword_changed(self, *args):
		if self.widgets['smtppassword'].get_text() != "":
			self.configman.set("report", "smtppassword", self.widgets['smtppassword'].get_text())
		else :
			self.configman.remove_option("report", "smtppassword")
	#----------------------------------------------------------------------

	def on_crtfilechooser_selection_changed(self, *args):
		self.configman.set("report", "smtpcert", self.widgets['crtfilechooser'].get_filename())
		getLogger().debug("Certificate : " + self.configman.get("report", "smtpcert"))

	#----------------------------------------------------------------------

	def on_keyfilechooser_selection_changed(self, *args):
		self.configman.set("report", "smtpkey", self.widgets['keyfilechooser'].get_filename())
		getLogger().debug("Key : " + self.configman.get("report", "smtpkey"))

	#----------------------------------------------------------------------

	def gtk_main_quit( self, *args):
		gtk.main_quit()
	#----------------------------------------------------------------------

	def on_ftype_custom_ex_changed(self, *args):
		print("TODO: on_ftype_custom_ex_changed")
		pass

	#----------------------------------------------------------------------

	def on_pluginscombobox_changed(self, *args):
		print("TODO: on_pluginscombobox_changed")
		pass

	#----------------------------------------------------------------------

	def on_fusecheckbutton_clicked(self, *args):
		print("TODO: on_fusecheckbutton_clicked")
		pass

	#----------------------------------------------------------------------

	def gtk_widget_hide(self, *args):
		print("TODO: gtk_widget_hide")
		pass



#----------------------------------------------------------------------

def main(argv):

	w = SBconfigGTK()
	w.show()
	gtk.main()

#----------------------------------------------------------------------

if __name__ == '__main__':
	main(sys.argv)
