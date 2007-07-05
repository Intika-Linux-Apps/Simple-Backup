#!/usr/bin/python
#
# Simple Backup Solution - GUI restore tool
#
# Running this command will restore a file or directory from backup.
#
# Author: Aigars Mahinovs <aigarius@debian.org>
#
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


import sys
import os
import commands
import re
import cPickle
import locale
import gettext
import sbackup.managers.FileAccessManager as FAM
from sbackup.managers.ConfigManager import ConfigManager
from sbackup.managers.RestoreManager import RestoreManager
from sbackup.managers.FuseFAM import FuseFAM
from sbackup.managers.SnapshotManager import SnapshotManager
from gettext import gettext as _

# Attempt to load GTK bindings
try:
	import pygtk
	pygtk.require("2.0")
	import gtk
	import gtk.glade
	import gobject
except ImportError:
	print "Failed to load Python GTK/Gnome bindings. Please check your Gnome installation."
	sys.exit(1)
try:
    import gnomevfs
except ImportError:
    import gnome.vfs as gnomevfs



def error_dialog(message, parent = None):
	"""
	Displays an error message.
	"""
	
	dialog = gtk.MessageDialog(parent = parent, type = gtk.MESSAGE_ERROR, buttons = gtk.BUTTONS_OK, flags = gtk.DIALOG_MODAL)
	dialog.set_markup(message)

	result = dialog.run()
	dialog.destroy()


class SRestoreGTK:
	"""
	Main application class.
	"""
	
	default_target = "/var/backup"
	target = default_target
	versions = []
	snapman = None
	fusefam = None
	
	def __init__(self):
		"""
		Initializes the application.
		"""
		global fusefam
		
		# Load default config
		self.load_config()
		
		self.fusefam = FuseFAM(self.conf)
		
		# Setup glade and signals
		gtk.glade.textdomain("sbackup")
		self.signals = {"gtk_main_quit": gtk.main_quit,
				"on_customsrc_toggled": self.enable_custom,
				"on_treeview1_row_expanded": self.on_expand_row,
				"on_backup_changed": self.on_backup_changed,
				"on_apply_clicked": self.on_custom_apply,
				"on_move_cursor":self.on_selection_change,
				"on_restore":self.restore,
				"on_restore_as":self.restore_as,
				"on_customFolderButton_clicked": self.on_customFolderButton_clicked
				}

		self.widgets = gtk.glade.XML("/usr/share/sbackup/simple-restore.glade")
		self.widgets.signal_autoconnect(self.signals)

		# Get handle to window
		self.window = self.widgets.get_widget("restore")

		self.widgets.get_widget("labelDefaultSource").set_text(self.default_target)	

		# Load the backup tree from the default location
		self.init_tree()
		self.sel = self.flist_widget.get_selection()
		self.sel.set_mode( gtk.SELECTION_SINGLE )
		self.load_tree(self.default_target)
		

		# Start the main loop
		gtk.main()
	
	def load_config(self):
		"""
		Load the default system configuration file and determine
		the default backup location
		"""
		global target, default_target
		if os.geteuid() == 0 :
			if FAM.exist("/etc/sbackup.conf") :
				self.conf = ConfigManager("/etc/sbackup.conf")
			else :
				self.conf = ConfigManager()
		else :
			if FAM.exists(os.getenv("HOME")+os.sep.join(["",".sbackup","sbackup.conf"])) :
				self.conf = ConfigManager(os.getenv("HOME")+os.sep.join(["",".sbackup","sbackup.conf"]))
			else :
				self.conf = ConfigManager()

		if self.conf.has_option( "general", "target" ):
			self.default_target = self.conf.get( "general", "target" )
			self.target = self.default_target 
		else :
			if os.geteuid() == 0 :
				self.default_target = "/var/backup"
				self.target = self.default_target 
			else:
				self.default_target = os.getenv("HOME")+os.sep+"backup"
				self.target = self.default_target 
			

	def init_tree(self):
		"""
		Initalizes the tree structure
		"""
		
		self.flist_widget = self.widgets.get_widget("treeview1")
		self.treestore = gtk.TreeStore( str )
		
		self.flist_widget.set_model( self.treestore )
		
		acolumn = gtk.TreeViewColumn( _("Path"), gtk.CellRendererText(), text=0 )
		self.flist_widget.append_column( acolumn )

		blist_widget = self.widgets.get_widget( "combobox1" )
		self.blist = gtk.ListStore(str)
		blist_widget.set_model( self.blist )
		cell = gtk.CellRendererText()
		blist_widget.pack_start( cell, True )
		blist_widget.add_attribute( cell, "text", 0)

		
	def load_tree(self, target):
		"""
		Loads the tree information from the target backup directory
		"""
		global snapman
		self.treestore.clear()
		
		# Get list of backup directories
		
		self.snapman = SnapshotManager(self.target)
		
		listing = self.snapman.getSnapshots()
		
		self.vtree = {}

		if listing == []:
			self.treestore.append( None, [_("Error: no backups found in the target directory")])
			self.target = False
		else:
			for snapshot in listing:
				self.vtree[snapshot.getName()] = snapshot.getFilesList().iterkeys()
		
		self.blist.clear()
		
		for base in listing:
			self.blist.append( [base.getName()] )
		
		self.good = False
		self.on_selection_change()
		if self.target:
			self.treestore.append( None, [_("Select any of the available backups to see list of files that can be restored.")])
		#self.widgets.get_widget("entry1").set_text( target )
		
		
	def on_customFolderButton_clicked(self, *args):
		dialog = gtk.FileChooserDialog(_("Choose a source folder"), None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_local_only(False)
		if dialog.run() == gtk.RESPONSE_OK:
			self.widgets.get_widget("entry1").set_text(dialog.get_uri())
		dialog.destroy()

	def enable_custom(self, *args):
		"""
		Enables/Disables input box for the custom backup dir
		Reloads default dir on disabling
		"""
		if self.widgets.get_widget("radiobutton2").get_active():
			self.widgets.get_widget("entry1").set_sensitive(True)
			self.widgets.get_widget("customFolderButton").set_sensitive(True)
			self.widgets.get_widget("button7").set_sensitive(True)
			self.widgets.get_widget("labelDefaultSource").set_sensitive(False)
		else:
			self.widgets.get_widget("entry1").set_sensitive(False)
			self.widgets.get_widget("customFolderButton").set_sensitive(False)
			self.widgets.get_widget("button7").set_sensitive(False)
			self.widgets.get_widget("labelDefaultSource").set_sensitive(True)
			self.load_tree(self.default_target)

	def on_backup_changed( self, combox ):
		"""
		Reset the file tree view.
		"""
		self.treestore.clear()
		self.treestore.append( None, ["dummy"])
		self.show_dir( "", None )
		

	def on_expand_row( self, tv, iter, path, user_data=None):
		"""
		When a row in the file tree view is expanded, we populate
		it with children (unless they are there already).
		"""
		if self.treestore.iter_nth_child( iter, 1 ):
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
			i = self.treestore.get_iter( tuple(g) )
			p = "/" + self.treestore.get_value( i, 0 ) + p
			g = g[:-1]
		return p
	
	def show_dir(self, path, rootiter):
		"""
		Worker function - adds all files/directories from the filez list
		to the treestore at the rootiter.
		"""
		dummy = self.treestore.iter_children(rootiter)
		
		self.good = True

		base = self.get_active_text(self.widgets.get_widget("combobox1"))
		list2 = []
		list3 = []
		
		escapedFullPath = re.escape(path)+"/([^/]+/?)"
		for item in self.vtree[base]:
			m = re.match( escapedFullPath, item )
			if m and not list2.count(m.group(1)) and not list3.count(m.group(1)[:-1]):
				if m.group(1)[-1] == "/":
					if list2.count(m.group(1)[:-1]):
						list2.remove(m.group(1)[:-1])
					list3.append(m.group(1)[:-1])
				else:
					list2.append( m.group(1) )
		for d in list3:
			iter = self.treestore.append( rootiter, [d] )
			self.treestore.append( iter, [_("Loading ...")] )
		for f in list2:
			self.treestore.append( rootiter, [f] )
		
		self.treestore.remove( dummy )
		
		
	def get_active_text(self, combobox):
		model = combobox.get_model()
		active = combobox.get_active()
		if active < 0:
			return None
		return model[active][0]
	
	def on_custom_apply(self, *args):
		"""
		Reload all backup info from a custom location
		"""
		global fusefam, target
		# mount with FuseFAM
		ltarget = self.widgets.get_widget("entry1").get_text()
		newtarget = self.fusefam.mount(ltarget)
		self.target = newtarget
		self.load_tree(self.target)

	def on_selection_change(self, *args):
		"""
		Enable/disable restore buttons as selection changes
		"""
		(model, iter) = self.sel.get_selected()
		if iter and self.good:
			self.widgets.get_widget("button2").set_sensitive(True)
			self.widgets.get_widget("button3").set_sensitive(True)
		else:
			self.widgets.get_widget("button2").set_sensitive(False)
			self.widgets.get_widget("button3").set_sensitive(False)


	def show_help(self, *args):
		"""
		Displays the help window.
		Called when the 'Help' button is clicked.
		"""

		# TODO: Implement
		error_dialog(_("Sorry, help is not implemented yet."), self.window)
	
	def _restore_init( self, *args):
		"""
		Internal function to prepare for restorin a file
		"""
		(store, iter) = self.widgets.get_widget("treeview1").get_selection().get_selected()
		self.src = self.path_to_dir( store.get_path( iter ) )
		return iter
	
	def _do_restore( self, src, dst):
		""" Internal function to ask for confirmation and call the real restore library func"""
		dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=_("Do you really want to restore backuped copy of '%s' to '%s' ?") % (src, dst))
		
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_NONE, message_format=_("Restoring ..."))
			dialog.show()
			index = self.snapman.getSnapshots().index(self.get_active_text(self.widgets.get_widget("combobox1")))
			r = RestoreManager()
			r.restore( self.snapman.getSnapshots()[index], src, dst )
			del r
			dialog.destroy()

	def restore( self, *args):
		""" Restore selected path to its original location"""
		self._restore_init()
		self._do_restore( self.src, self.src )

	def restore_as( self, *args):
		""" Restore selected path to a specific location"""
		iter = self._restore_init()
		if self.treestore.iter_children( iter ):
			# is a directory
			dialog = gtk.FileChooserDialog(title=_("Select restore location") ,action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
			dialog.set_filename( self.src )
			result = dialog.run()
			filename = dialog.get_filename()
			dialog.destroy()

			if result == gtk.RESPONSE_OK:
				self._do_restore( self.src, filename )
		else:
			dialog = gtk.FileChooserDialog(title=_("Select restore location") ,action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
			dialog.set_filename( self.src )
			dialog.set_current_name( self.src )
			result = dialog.run()
			filename = dialog.get_filename()
			dialog.destroy()
			
			if result == gtk.RESPONSE_OK:
				self._do_restore( self.src, filename )


if __name__ == '__main__':
	
	# i18n init
	locale.setlocale(locale.LC_ALL, '')
	gettext.textdomain("sbackup")
	gettext.install("sbackup", unicode=True) 

	# Load GUI
	SRestoreGTK()
