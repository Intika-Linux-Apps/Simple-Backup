#!/usr/bin/env python
    
#----------------------------------------------------------------------
# SBRestoreGTK.py
# Ouattara Aziz
# 07/07/2007
#----------------------------------------------------------------------

import sys

from GladeWindow import *
import nssbackup.util as Util
from nssbackup.managers.FuseFAM import FuseFAM
from nssbackup.managers.ConfigManager import ConfigManager
from nssbackup.managers.SnapshotManager import SnapshotManager
from nssbackup.util.log import getLogger

#----------------------------------------------------------------------

class SBRestoreGTK(GladeWindow):

	fusefam = None
	target = None
	config = None
	snpman = None
	snplisttreestore = None
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
			if os.path.exists(os.getenv("HOME")+"/.nssbackup/nssbackup.conf") :
				self.config = ConfigManager(os.getenv("HOME")+"/.nssbackup/nssbackup.conf")
			else :
				self.config = ConfigManager()
		
				
		# set the default label
		self.widgets['defaultfolderlabel'].set_text(self.config.get("general", "target"))
		
		#tree strores
		self.snplisttreestore = gtk.TreeStore( str )
		self.widgets['snplisttreeview'].set_model( self.snplisttreestore )
		acolumn = gtk.TreeViewColumn("Snapshot", gtk.CellRendererText(), text=0 )
		self.widgets['snplisttreeview'].append_column( acolumn )
		
		self.flisttreestore = gtk.TreeStore( str )
		self.widgets['filelisttreeview'].set_model( self.flisttreestore )
		acolumn1 = gtk.TreeViewColumn("Path", gtk.CellRendererText(), text=0 )
		self.widgets['filelisttreeview'].append_column( acolumn1 )

		# set fusefam
		self.fusefam = FuseFAM(self.config)
		
		# set the target
		self.change_target(self.config.get("general", "target"))
	
	#----------------------------------------------------------------------

	def init(self):

		filename = Util.getResource('simple-restore-gnome.glade')

		widget_list = [
			'restorewindow',
			'vbox1',
			'table1',
			'defaultfolderlabel',
			'defaultradiob',
			'customradiob',
			'custominfos',
			'customentry',
			'customchooser',
			'customapply',
			'hbox1',
			'calendar',
			'vbox2',
			'scrolledwindow1',
			'snplisttreeview',
			'vbox3',
			'scrolledwindow2',
			'filelisttreeview',
			'vbox4',
			'restore',
			'hbox4',
			'restoreas',
			'hbox5',
			'revert',
			'hbox6',
			'revertas',
			'hbox7',
			]

		handlers = [
			'gtk_main_quit',
			'on_defaultradiob_toggled',
			'on_customchooser_clicked',
			'on_customapply_clicked',
			'on_calendar_month_changed',
			'on_calendar_day_selected',
			'on_filelisttreeview_select_cursor_row',
			'on_filelisttreeview_move_cursor',
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
	#----------------------------------------------------------------------

	def on_defaultradiob_toggled(self, *args):
		print("TODO: on_defaultradiob_group_changed")
		if self.widgets['defaultradiob'].get_active() :
			self.widgets['custominfos'].set_sensitive( False )
			self.change_target(self.config.get("general", "target"))
		elif self.widgets['customradiob'].get_active() :
			self.widgets['custominfos'].set_sensitive( True )
		pass

	#----------------------------------------------------------------------

	def on_customchooser_clicked(self, *args):
		dialog = gtk.FileChooserDialog("Choose a source folder", None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
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

	def on_filelisttreeview_select_cursor_row(self, *args):
		print("TODO: on_filelisttreeview_select_cursor_row")
		pass

	#----------------------------------------------------------------------

	def on_filelisttreeview_move_cursor(self, *args):
		print("TODO: on_filelisttreeview_move_cursor")
		pass

	#----------------------------------------------------------------------

	def on_filelisttreeview_row_expanded(self, *args):
		print("TODO: on_filelisttreeview_row_expanded")
		pass

	#----------------------------------------------------------------------

	def on_filelisttreeview_cursor_changed(self, *args):
		print("TODO: on_filelisttreeview_cursor_changed")
		pass

	#----------------------------------------------------------------------

	def on_filelisttreeview_unselect_all(self, *args):
		print("TODO: on_filelisttreeview_unselect_all")
		pass

	#----------------------------------------------------------------------

	def on_restore_clicked(self, *args):
		print("TODO: on_restore_clicked")
		pass

	#----------------------------------------------------------------------

	def on_restoreas_clicked(self, *args):
		print("TODO: on_restoreas_clicked")
		pass

	#----------------------------------------------------------------------

	def on_revert_clicked(self, *args):
		print("TODO: on_revert_clicked")
		pass

	#----------------------------------------------------------------------

	def on_revertas_clicked(self, *args):
		print("TODO: on_revertas_clicked")
		pass
	
	#----------------------------------------------------------------------
	
	def gtk_main_quit( self, *args):
		self.fusefam.terminate()
		gtk.main_quit()

#--------------------------------------------------------------------------

	def load_filestree(self):
		print("TODO: load_filestree")
		pass

	def load_snapshotslist(self, date):
		"""
		load the snapshot list for that date
		@param date: a tupe (year, month, day) using the Calendar.get_date convention ie month is 0-11
		"""
		day = "-".join([str(date[0]),"%02d" % (int(date[1])+1),"%02d" % date[2]])
		getLogger().debug("Selected day : " + day)
		snplist = self.snpman.getSnapshots(byDate=day)
		self.snplisttreestore.clear()
		if snplist == []:
			self.snplisttreestore.append( None, ["No backups found for this day !"])
		else:
			for snapshot in snplist:
				self.snplisttreestore.append(None, [snapshot.getName()])
	
	def fill_calendar(self):
		"""
		Fill the calendar with the snapshots of the month
		"""
		print("TODO: fill calendar")
		self.widgets['calendar'].clear_marks()
		
		date = self.widgets["calendar"].get_date()
		fromDate = "-".join([str(date[0]),"%02d" % (int(date[1])+1),"01"])
		toDate = "-".join([str(date[0]),"%02d" % (int(date[1])+1),"31"])
		snplist = self.snpman.getSnapshots(fromDate, toDate)
		
		for snapshot in snplist :
			self.widgets["calendar"].mark_day( int(snapshot.getDate()["day"]) )
		
		pass

	def change_target(self, newtarget):
		"""
		"""
		global snpman, target
		print ("TODO: change_target")
		try :
			self.target =  self.fusefam.mount(newtarget)
			self.snpman = SnapshotManager(self.target)
			self.fill_calendar()
		except Exception, e :
			getLogger().error(str(e))
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
			dialog.run()
			dialog.destroy()
		pass
		

#----------------------------------------------------------------------

def main(argv):

	w = SBRestoreGTK()
	w.show()
	gtk.main()

#----------------------------------------------------------------------

if __name__ == '__main__':
	main(sys.argv)
