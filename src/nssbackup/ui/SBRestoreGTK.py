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
# Authors :
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum at gmail dot com>

from gettext import gettext as _
import traceback, time
from thread import *
from GladeWindow import *
import nssbackup.util as Util
from nssbackup.managers.FuseFAM import FuseFAM
from nssbackup.managers.ConfigManager import ConfigManager, getUserConfDir, getUserDatasDir
from nssbackup.managers.SnapshotManager import SnapshotManager
from nssbackup.managers.RestoreManager import RestoreManager
from nssbackup.managers.UpgradeManager import UpgradeManager
from nssbackup.util.log import getLogger
import nssbackup.util.Snapshot
from nssbackup.util.Snapshot import Snapshot
import nssbackup.util.tar as TAR
from nssbackup import Infos

#----------------------------------------------------------------------

class SBRestoreGTK(GladeWindow):
	
	currentSnp = None
	currentsbdict = None
	currSnpFilesInfos = None
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
		self.snplisttreestore = gtk.TreeStore( str,str )
		self.widgets['snplisttreeview'].set_model( self.snplisttreestore )
		acolumn = gtk.TreeViewColumn(_("Snapshots"), gtk.CellRendererText(), text=0 )
		bcolumn = gtk.TreeViewColumn(_("Version"), gtk.CellRendererText(), text=1 )
		self.widgets['snplisttreeview'].append_column( acolumn )
		self.widgets['snplisttreeview'].append_column( bcolumn )
		
		self.flisttreestore = gtk.TreeStore( str,str )
		self.flisttreesort =  gtk.TreeModelSort(self.flisttreestore)
		self.flisttreesort.set_sort_column_id(0, gtk.SORT_ASCENDING)
		self.widgets['filelisttreeview'].set_model( self.flisttreesort )
		
		acolumn1 = gtk.TreeViewColumn(_("Path"), gtk.CellRendererText(), text=0 )
		self.widgets['filelisttreeview'].append_column( acolumn1 )
		self.widgets['filelisttreeview'].set_search_column(0)
		acolumn1.set_sort_column_id(0)
		
		acolumn2 = gtk.TreeViewColumn(_("State"), gtk.CellRendererText(), text=1 )
		self.widgets['filelisttreeview'].append_column( acolumn2 )
		
		self.on_defaultradiob_toggled()
		
		# select the current day
		today = time.localtime()
		self.widgets["calendar"].select_month(today[1]-1,today[0])
		self.widgets["calendar"].select_day(today[2])
		self.on_calendar_day_selected()
		
		self.widgets['snpdetails'].set_sensitive(False)
	
	#----------------------------------------------------------------------

	def init(self):

		filename = Util.getResource('nssbackup-restore.glade')

		widget_list = [
			'progressbarDialog',
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
			'restoreExpander',
			'snpmanExpander',
			'filelisttreeview',
			'buttonspool',
			'restore',
			'restoreas',
			'revert',
			'revertas',
			'upgradeBox',
			'upgradeButton',
			'RebaseBox',
			'rebaseLabel',
			'rebaseButton',
			'deleteBox',
			'deleteButton',
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
			'on_restoreExpander_activate',
			'on_snpmanExpander_activate',
			'on_upgradeButton_clicked',
			'on_rebaseButton_clicked',
			'on_deleteButton_clicked',
			'on_exportmanExpander_activate',
			]

		top_window = 'restorewindow'
		GladeWindow.__init__(self, filename, top_window, widget_list, handlers)
		self.widgets[top_window].set_icon_from_file(Util.getResource("nssbackup-restore.png"))
	#----------------------------------------------------------------------

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
			self.widgets["restoreExpander"].set_expanded(False)
			self.fill_calendar()
		except Exception, e :
			getLogger().error(str(e))
			getLogger().error(traceback.format_exc())
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
			dialog.run()
			dialog.destroy()

	# ---------------------------------------------------------------------
	
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
		self.widgets["restoreExpander"].set_expanded(False)
		self.widgets['snpmanExpander'].set_expanded(False)
		tstore, iter = self.widgets['snplisttreeview'].get_selection().get_selected()
		self.currentSnp = self.snpman.getSnapshot(str(tstore.get_value(iter,0)))

	#----------------------------------------------------------------------

	def on_filelisttreeview_row_expanded(self, tv, iter, path, user_data=None):
		"""
		When a row in the file tree view is expanded, we populate
		it with children (unless they are there already).
		"""
		if self.flisttreestore.iter_nth_child( self.flisttreesort.convert_iter_to_child_iter(None,iter), 1 ):
			return
		self.appendContent( self.path_to_dir(path), self.flisttreesort.convert_iter_to_child_iter(None,iter) )
	
	def path_to_dir( self, path ):
		"""
		Recievs path in the treestore (as tuple) and returns a directory
		path as string.
		"""
		g = list(path)
		p = ""
		while g != []:
			i = self.flisttreestore.get_iter( self.flisttreesort.convert_path_to_child_path(tuple(g)) )
			p = os.sep + (self.flisttreestore.get_value( i, 0 ) + p).lstrip(os.sep)
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

	def appendContent(self,path,rootiter):
		"""
		append the content in the tree store
		@param path: The path to add the content of.
		@param rootiter: the GTKIter that indexes the row
		"""
		dummy = self.flisttreestore.iter_children(rootiter)
		
		content = self.currSnpFilesInfos.getContent(path)
		# content is a list of Dumpdirs
		if not content :
			# content is empty, do nothing
			pass
		else :
			for f in content :
				iter = self.flisttreestore.append( rootiter, [f.getFilename(),f.getHumanReadableControl()] )
				if f.getControl() == TAR.Dumpdir.DIRECTORY :
					self.flisttreestore.append( iter, [_("Loading ..."),None] )
		if dummy :
			self.flisttreestore.remove( dummy )
		
	def load_filestree(self):
		"""
		Load the files list 
		"""
		global currentsbdict
		self.flisttreestore.clear()
		#self.widgets['progressbarDialog'].show()
		self.widgets['buttonspool'].set_sensitive(False)

		self.currSnpFilesInfos = self.currentSnp.getSnapshotFileInfos()
		
		if self.currSnpFilesInfos :
			# load the first items 
			f1_items = self.currSnpFilesInfos.getFirstItems()
			if not f1_items :
				# first items is empty
				self.flisttreestore.append(None, [_("This snapshot seems empty."),None])
				self.widgets['snpdetails'].set_sensitive(False)
			else :
				self.widgets['snpdetails'].set_sensitive(True)
				for k in f1_items :
					# add k and append the content if not empty
					iter = self.flisttreestore.append(None, [k,TAR.Dumpdir.getHRCtrls()[TAR.Dumpdir.DIRECTORY]])
					self.appendContent(k, iter)
			
		self.widgets['progressbarDialog'].hide()

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
			self.snplisttreestore.append( None, [_("No backups found for this day !"),None])
			self.widgets['snplist'].set_sensitive(False)
		else:
			self.widgets['snplist'].set_sensitive(True)
			for snapshot in snplist:
				self.snplisttreestore.append(None, [snapshot.getName(),snapshot.getVersion()])

	#----------------------------------------------------------------------

	def on_restoreExpander_activate(self,*args):
		if not self.widgets["restoreExpander"].get_expanded():
			tstore, iter = self.widgets['snplisttreeview'].get_selection().get_selected()
			if iter:
				self.currentSnp = self.snpman.getSnapshot(str(tstore.get_value(iter,0)))
				if self.currentSnp.getVersion() != Infos.SNPCURVERSION:
					message = _("The snapshot version is not supported (Just %(supportedversion)s is supported). Version '%(currentversion)s' found. You should upgrade it. ") % {'supportedversion': Infos.SNPCURVERSION, 'currentversion':self.currentSnp.getVersion() }
					getLogger().warning(message) 
					dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=message)
					dialog.run()
					dialog.destroy()
					self.widgets["snpdetails"].set_sensitive(False)
				else:
					self.load_filestree()
			else:
				self.widgets["snpdetails"].set_sensitive(False)

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
				self.widgets['progressbarDialog'].show()
				self.restoreman.restore(self.currentSnp, src)
				self.widgets['progressbarDialog'].hide()
			except Exception, e :
				getLogger().error(str(e))
				getLogger().error(traceback.format_exc())
				self.widgets['progressbarDialog'].hide()
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
				dialog.run()
				dialog.destroy()
		
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
				try :	
					self.restoreman.restoreAs(self.currentSnp, src, dirname)
				except Exception, e :
					getLogger().error(str(e))
					getLogger().error(traceback.format_exc())
					self.widgets['progressbarDialog'].hide()
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
				self.widgets['progressbarDialog'].show()
				self.restoreman.revert(self.currentSnp, src)
				self.widgets['progressbarDialog'].hide()
			except Exception, e :
				getLogger().error(str(e))
				getLogger().error(traceback.format_exc())
				self.widgets['progressbarDialog'].hide()
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
					self.widgets['progressbarDialog'].show()
					self.restoreman.revertAs(self.currentSnp, src,dirname)
					self.widgets['progressbarDialog'].hide()
				except Exception, e :
					getLogger().error(str(e))
					getLogger().error(traceback.format_exc())
					self.widgets['progressbarDialog'].hide()
					dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
					dialog.run()
					dialog.destroy()
	
	#----------------------------------------------------------------------

	def on_snpmanExpander_activate(self, *args):
		if not self.widgets['snpmanExpander'].get_expanded():
			if self.currentSnp:
				if self.currentSnp.getVersion() == Infos.SNPCURVERSION:
					self.widgets["upgradeBox"].hide()
					if self.currentSnp.isfull():
						self.widgets["RebaseBox"].hide()
					else:
						self.widgets["RebaseBox"].show()
					self.widgets["rebaseLabel"].set_markup(_("Actual base : <b>%s</b>") % self.currentSnp.getBase())
					self.widgets["deleteBox"].show()
				elif self.currentSnp.getVersion() < Infos.SNPCURVERSION :
					self.widgets["upgradeBox"].show()
					self.widgets["RebaseBox"].hide()
					self.widgets["deleteBox"].hide()
				else :
					self.widgets["upgradeBox"].hide()
					self.widgets["RebaseBox"].hide()
					self.widgets["deleteBox"].hide()
					message=_("The version of the snapshot is greater than the supported one!")
					dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=message)
					dialog.run()
					dialog.destroy()
			else:
				self.widgets["upgradeBox"].hide()
				self.widgets["RebaseBox"].hide()
				self.widgets["deleteBox"].hide()
		

	#----------------------------------------------------------------------

	def on_upgradeButton_clicked(self, *args):
		um = UpgradeManager()
		um.upgradeSnapshot(self.currentSnp)
		self.load_snapshotslist(self.widgets['calendar'].get_date())
		self.widgets['snpmanExpander'].set_expanded(False)
		self.on_snpmanExpander_activate()
		self.widgets['snpmanExpander'].set_expanded(True)

	#----------------------------------------------------------------------

	def on_rebaseButton_clicked(self, *args):
		print("TODO: on_rebaseButton_clicked")
		pass

	#----------------------------------------------------------------------

	def on_deleteButton_clicked(self, *args):
		print("TODO: on_deleteButton_clicked")
		pass

	#----------------------------------------------------------------------

	def on_exportmanExpander_activate(self, *args):
		print("TODO: on_exportmanExpander_activate")
		pass
	
	#----------------------------------------------------------------------
	
	def gtk_main_quit( self, *args):
		self.fusefam.terminate()
		gtk.main_quit()

	
#----------------------------------------------------------------------

def main(argv):

	w = SBRestoreGTK()
	w.show()
	gtk.main()