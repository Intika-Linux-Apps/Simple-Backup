#!/usr/bin/env python
    
#----------------------------------------------------------------------
# SBRestoreGTK.py
# Ouattara Aziz
# 07/07/2007
#----------------------------------------------------------------------

import gettext
from gettext import gettext as _
import sys, traceback, time
from thread import *
from GladeWindow import *
import nssbackup.util as Util
from nssbackup.managers.FuseFAM import FuseFAM
from nssbackup.managers.ConfigManager import ConfigManager, getUserConfDir, getUserDatasDir
from nssbackup.managers.SnapshotManager import SnapshotManager
from nssbackup.managers.RestoreManager import RestoreManager
from nssbackup.util.log import getLogger
import nssbackup.util.Snapshot
from nssbackup.util.Snapshot import Snapshot

#----------------------------------------------------------------------

class SBRestoreGTK(GladeWindow):
	
	currentSnp = None
	currentsbdict = None
	restoreman = RestoreManager()

	#----------------------------------------------------------------------

	def __init__(self):
		''' '''
		self.init()
		
		# get the config file
		if os.getuid() == 0 : # we are root
			if os.path.exists("/etc/nssbackup.conf") :
				self.config = ConfigManager("/etc/nssbackup.conf")
			else :
				self.config = ConfigManager()
					
		else :  # we are others
			if os.path.exists(getUserConfDir()+ "nssbackup.conf") :
				self.config = ConfigManager(getUserConfDir()+ "nssbackup.conf")
			else :
				self.config = ConfigManager()
		
		# set fusefam
		self.fusefam = FuseFAM(self.config)
		self.fusefam.initialize()
		
		# set the default label
		self.widgets['defaultfolderlabel'].set_text(self.config.get("general", "target"))
		
		#tree strores
		self.snplisttreestore = gtk.TreeStore( str )
		self.widgets['snplisttreeview'].set_model( self.snplisttreestore )
		acolumn = gtk.TreeViewColumn(_("Snapshots"), gtk.CellRendererText(), text=0 )
		self.widgets['snplisttreeview'].append_column( acolumn )
		
		self.flisttreestore = gtk.TreeStore( str )
		# self.flisttreemodelsort = gtk.TreeModelSort(self.flisttreestore)
		# self.flisttreemodelsort.set_sort_column_id(1, gtk.SORT_ASCENDING)
		# self.widgets['filelisttreeview'].set_model( self.flisttreemodelsort )
		self.widgets['filelisttreeview'].set_model( self.flisttreestore )
		acolumn1 = gtk.TreeViewColumn(_("Path"), gtk.CellRendererText(), text=0 )
		self.widgets['filelisttreeview'].append_column( acolumn1 )
		
		self.on_defaultradiob_toggled()
		
		# select the current day
		today = time.localtime()
		self.widgets["calendar"].select_month(today[1]-1,today[0])
		self.widgets["calendar"].select_day(today[2])
		self.on_calendar_day_selected()
	
	#----------------------------------------------------------------------

	def init(self):

		filename = Util.getResource('nssbackup-restore.glade')

		widget_list = [
			'restorewindow',
			'defaultfolderlabel',
			'defaultradiob',
			'customradiob',
			'custominfos',
			'customentry',
			'customchooser',
			'customapply',
			'calendar',
			'snplist',
			'scrolledwindow1',
			'snplisttreeview',
			'snpdetails',
			'scrolledwindow2',
			'filelisttreeview',
			'buttonspool',
			'restore',
			'restoreas',
			'revert',
			'revertas',
			]

		handlers = [
			'gtk_main_quit',
			'on_defaultradiob_toggled',
			'on_customchooser_clicked',
			'on_customapply_clicked',
			'on_calendar_month_changed',
			'on_calendar_day_selected',
			'on_snplisttreeview_cursor_changed',
			'on_filelisttreeview_row_expanded',
			'on_filelisttreeview_cursor_changed',
			'on_filelisttreeview_unselect_all',
			'on_restore_clicked',
			'on_restoreas_clicked',
			'on_revert_clicked',
			'on_revertas_clicked',
			]

		top_window = 'restorewindow'
		GladeWindow.__init__(self, filename, top_window, widget_list, handlers)
		self.widgets[top_window].set_icon_from_file(Util.getResource("nssbackup-restore.png"))
	#----------------------------------------------------------------------

	def on_defaultradiob_toggled(self, *args):
		if self.widgets['defaultradiob'].get_active() :
			self.widgets['custominfos'].set_sensitive( False )
			self.change_target(self.config.get("general", "target"))
		elif self.widgets['customradiob'].get_active() :
			self.widgets['custominfos'].set_sensitive( True )

	#----------------------------------------------------------------------

	def on_customchooser_clicked(self, *args):
		dialog = gtk.FileChooserDialog(_("Choose a source folder"), None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_local_only(False)
		if dialog.run() == gtk.RESPONSE_OK:
			self.widgets["customentry"].set_text(dialog.get_current_folder())
		dialog.destroy()

	#----------------------------------------------------------------------

	def on_customapply_clicked(self, *args):
		"""
		Reload all backup info from a custom location
		"""
		ltarget = self.widgets["customentry"].get_text()
		self.change_target(ltarget)

	#----------------------------------------------------------------------

	def on_calendar_month_changed(self, *args):
		self.fill_calendar()

	#----------------------------------------------------------------------

	def on_calendar_day_selected(self, *args):
		self.load_snapshotslist(self.widgets['calendar'].get_date())

	#----------------------------------------------------------------------
	
	def on_snplisttreeview_cursor_changed(self,*args):
		self.flisttreestore.clear()
		self.load_filestree()

	#----------------------------------------------------------------------

	def on_filelisttreeview_row_expanded(self, tv, iter, path, user_data=None):
		"""
		When a row in the file tree view is expanded, we populate
		it with children (unless they are there already).
		"""
		if self.flisttreestore.iter_nth_child( iter, 1 ):
			return
		self.show_dir( self.path_to_dir(path), iter )
	
	def path_to_dir( self, path ):
		"""
		Recievs path in the treestore (as tuple) and returns a directory
		path as string.
		"""
		g = list(path)
		p = ""
		while g != []:
			i = self.flisttreestore.get_iter( tuple(g) )
			p = "/" + self.flisttreestore.get_value( i, 0 ) + p
			g = g[:-1]
		return p
	
	def show_dir(self, path, rootiter):
		"""
		Worker function - adds all files/directories from the filez list
		to the treestore at the rootiter.
		"""
		# hack to get the dir filled with some "loading"
		dummy = self.flisttreestore.iter_children(rootiter)
		
		son = self.currentsbdict.getSon(os.path.normpath(path))
		if son :
			for d in dict.iterkeys(self.currentsbdict.getSon(os.path.normpath(path))):
				iter = self.flisttreestore.append( rootiter, [d] )
				if self.currentsbdict.getSon(os.sep.join([os.path.normpath(path),d])) :
					self.flisttreestore.append( iter, [_("Loading ...")] )
		if dummy :
			self.flisttreestore.remove( dummy )
	
	#----------------------------------------------------------------------

	def on_filelisttreeview_cursor_changed(self, *args):
		self.widgets['buttonspool'].set_sensitive(True)


	#----------------------------------------------------------------------

	def on_filelisttreeview_unselect_all(self, *args):
		self.widgets['buttonspool'].set_sensitive(False)

	#----------------------------------------------------------------------

	def on_restore_clicked(self, *args):
		tstore, iter = self.widgets['filelisttreeview'].get_selection().get_selected()
		src = self.path_to_dir( tstore.get_path( iter ) )
		dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Do you really want to restore backuped copy of '%s' ?" % src)
		
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			# TODO: put a progress bar here
			progressbar = None
			try :
				progressbar = gtk.ProgressBar()
				progressbar.pulse()
				progressbar.show()
				self.restoreman.restore(self.currentSnp, src)
				progressbar.destroy()
			except Exception, e :
				getLogger().error(str(e))
				getLogger().error(traceback.format_exc())
				if progressbar : progressbar.destroy()
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
				dialog.run()
				dialog.destroy()
		

	#----------------------------------------------------------------------

	def on_restoreas_clicked(self, *args):
		tstore, iter = self.widgets['filelisttreeview'].get_selection().get_selected()
		src = self.path_to_dir( tstore.get_path( iter ) )
		
		dialog = gtk.FileChooserDialog(title=_("Select restore location") ,action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		dialog.set_filename( src )
		result = dialog.run()
		dirname = dialog.get_filename()
		dialog.destroy()
		
		if result == gtk.RESPONSE_OK:
			dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Do you really want to restore backuped copy of '%s' to '%s' ?" % (src, dirname))
			
			response = dialog.run()
			dialog.destroy()
			if response == gtk.RESPONSE_YES:
				# TODO: put a progress bar here
				progressbar = None
				try :
					progressbar = gtk.ProgressBar()
					progressbar.pulse()
					progressbar.show()
					self.restoreman.restoreAs(self.currentSnp, src, dirname)
					progressbar.destroy()
				except Exception, e :
					getLogger().error(str(e))
					getLogger().error(traceback.format_exc())
					if progressbar : progressbar.destroy()
					dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
					dialog.run()
					dialog.destroy()


	#----------------------------------------------------------------------

	def on_revert_clicked(self, *args):
		tstore, iter = self.widgets['filelisttreeview'].get_selection().get_selected()
		src = self.path_to_dir( tstore.get_path( iter ) )
		dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Do you really want to revert '%s' ?" % src)
		
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			# TODO: put a progress bar here
			progressbar = None
			try :
				progressbar = gtk.ProgressBar()
				progressbar.pulse()
				progressbar.show()
				self.restoreman.revert(self.currentSnp, src)
				progressbar.destroy()
			except Exception, e :
				getLogger().error(str(e))
				getLogger().error(traceback.format_exc())
				if progressbar : progressbar.destroy()
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
				dialog.run()
				dialog.destroy()

	#----------------------------------------------------------------------

	def on_revertas_clicked(self, *args):
		tstore, iter = self.widgets['filelisttreeview'].get_selection().get_selected()
		src = self.path_to_dir( tstore.get_path( iter ) )
		
		dialog = gtk.FileChooserDialog(title=_("Select revert location") ,action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		dialog.set_filename( src )
		result = dialog.run()
		dirname = dialog.get_filename()
		dialog.destroy()
		
		if result == gtk.RESPONSE_OK:
			dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Do you really want to revert '%s' to '%s' ?" % (src, dirname))
			
			response = dialog.run()
			dialog.destroy()
			if response == gtk.RESPONSE_YES:
				# TODO: put a progress bar here
				progressbar = None
				try :
					progressbar = gtk.ProgressBar()
					progressbar.pulse()
					progressbar.show()
					self.restoreman.revertAs(self.currentSnp, src,dirname)
					progressbar.destroy()
				except Exception, e :
					getLogger().error(str(e))
					getLogger().error(traceback.format_exc())
					if progressbar : progressbar.destroy()
					dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
					dialog.run()
					dialog.destroy()
	
	#----------------------------------------------------------------------
	
	def gtk_main_quit( self, *args):
		self.fusefam.terminate()
		gtk.main_quit()

#--------------------------------------------------------------------------

	def load_filestree(self):
		global currentsbdict
		self.flisttreestore.clear()
		self.widgets['buttonspool'].set_sensitive(False)
		tstore, iter = self.widgets['snplisttreeview'].get_selection().get_selected()
		self.currentSnp = self.snpman.getSnapshot(str(tstore.get_value(iter,0)))
		self.currentsbdict = self.currentSnp.getFilesList()
		
		if len(self.currentsbdict) > 0 and self.currentsbdict.getSon(os.sep) :
			self.widgets['snpdetails'].set_sensitive(True)
			for k in dict.iterkeys(self.currentsbdict.getSon(os.sep)) :
				iter = self.flisttreestore.append(None, [k])
				self.show_dir(os.sep+k, iter)
		else :
			self.flisttreestore.append(None, [_("This snapshot seems empty.")])
			self.widgets['snpdetails'].set_sensitive(False)
		

	def load_snapshotslist(self, date):
		"""
		load the snapshot list for that date
		@param date: a tupe (year, month, day) using the Calendar.get_date convention ie month is 0-11
		"""
		day = "-".join([str(date[0]),"%02d" % (int(date[1])+1),"%02d" % date[2]])
		getLogger().debug("Selected day : " + day)
		snplist = self.snpman.getSnapshots(byDate=day)
		
		self.snplisttreestore.clear()
		self.flisttreestore.clear()
		self.widgets['buttonspool'].set_sensitive(False)
		self.widgets['snpdetails'].set_sensitive(True)
		
		if snplist == []:
			self.snplisttreestore.append( None, [_("No backups found for this day !")])
			self.widgets['snplist'].set_sensitive(False)
		else:
			self.widgets['snplist'].set_sensitive(True)
			for snapshot in snplist:
				self.snplisttreestore.append(None, [snapshot.getName()])
	
	def fill_calendar(self):
		"""
		Fill the calendar with the snapshots of the month
		"""
		self.widgets['calendar'].clear_marks()
		
		date = self.widgets["calendar"].get_date()
		fromDate = "-".join([str(date[0]),"%02d" % (int(date[1])+1),"01"])
		toDate = "-".join([str(date[0]),"%02d" % (int(date[1])+1),"31"])
		snplist = self.snpman.getSnapshots(fromDate, toDate)
		
		for snapshot in snplist :
			self.widgets["calendar"].mark_day( int(snapshot.getDate()["day"]) )
		
		self.snplisttreestore.clear()
		self.flisttreestore.clear()
		self.widgets['buttonspool'].set_sensitive(False)
		self.widgets['snpdetails'].set_sensitive(True)

	def change_target(self, newtarget):
		"""
		"""
		global snpman, target
		try :
			self.target =  self.fusefam.mount(newtarget)
			self.snpman = SnapshotManager(self.target)
			self.fill_calendar()
		except Exception, e :
			getLogger().error(str(e))
			getLogger().error(traceback.format_exc())
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
			dialog.run()
			dialog.destroy()
	
#----------------------------------------------------------------------

def main(argv):

	w = SBRestoreGTK()
	w.show()
	gtk.main()

#----------------------------------------------------------------------

if __name__ == '__main__':
	application = 'nssbackup'
	gettext.install(application)
	main(sys.argv)
