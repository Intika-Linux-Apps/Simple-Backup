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
#	Jean-Peer Lorenz <peer.loz@gmx.net>

import os
import os.path
import sys
import traceback
import time

import gtk
import gobject

from gettext import gettext as _

from GladeWindow import GladeWindow
from GladeWindow import ProgressbarMixin

import nssbackup.util as Util
from nssbackup.managers.FuseFAM import FuseFAM
from nssbackup.managers.ConfigManager import ConfigManager, getUserConfDir
from nssbackup.managers.SnapshotManager import SnapshotManager
from nssbackup.managers.RestoreManager import RestoreManager
from nssbackup.managers.UpgradeManager import UpgradeManager
from nssbackup.util.log import LogFactory
import nssbackup.util.tar as TAR
from nssbackup import Infos
from nssbackup.util import exceptions
from nssbackup.util import tasks

# initialize threading before running a main loop
gtk.gdk.threads_init()


class SBRestoreGTK(GladeWindow, ProgressbarMixin):
	
	currentSnp = None
	currentsbdict = None
	currSnpFilesInfos = None
	restoreman = None
		
	__msg_statusbar = { "restore"	 : _("Restore..."),
						"restore_as" : _("Restore as..."),
						"revert"	 : _("Revert..."),
						"revert_as"	 : _("Revert as...")
					  }

	def __init__(self, parent = None):
		''' '''
		self.init(parent = parent)
		
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
		
		self.logger = LogFactory.getLogger()

		self.restoreman = RestoreManager()
		
		# set fusefam
		self.fusefam = FuseFAM(self.config)
		try:
			self.fusefam.initialize()
		except exceptions.FuseFAMException, exc:
			_sec_msg = _("The program is going to be terminated. Please make "\
						 "sure the missing directory exists (e.g. by mounting "\
						 "an external disk) or change the specified target "\
						 "in NSsbackup configuration tool and restart this "\
						 "application.")
			self._show_errmessage( message_str = str(exc),
					boxtitle = _("NSsbackup error"),
					headline_str = _("An error occured during initialization:"),
					secmsg_str = _sec_msg)
			self.fusefam.terminate()
			sys.exit(-1)

			
		# set the default label
		self.widgets['defaultfolderlabel'].set_text(self.config.get("general",
																    "target"))
		
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
		
		self.historylisttreestore= gtk.TreeStore( str )
		self.widgets['historytv'].set_model(self.historylisttreestore)
		acolumn3 = gtk.TreeViewColumn(_("Snapshots"), gtk.CellRendererText(), text=0 )
		self.widgets['historytv'].append_column( acolumn3 )
		
		self.on_defaultradiob_toggled()
		
		# select the current day
		today = time.localtime()
		self.widgets["calendar"].select_month(today[1]-1,today[0])
		self.widgets["calendar"].select_day(today[2])
		self.on_calendar_day_selected()
		
		self.widgets['snpdetails'].set_sensitive(False)

		# setup the progressbar
		ProgressbarMixin.__init__(self, self.widgets['progressbar'])
		self._init_pulse()
		
		self.__context_id = None
		self.__init_statusbar()
		
		self.__restore_dialog = RestoreDialog( parent = self )


	def init(self, parent = None):
		_gladefile = Util.getResource('nssbackup-restore.glade')

		_wdgt_lst = [
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
			'snphistoryFrame',
			'historytv',
			'statusbar',
			'progressbar'
			]

		_hdls = [
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
			'on_rebaseButton_toggled',
			'on_deleteButton_clicked',
			'on_exportmanExpander_activate',
			]

		_top_win_name = 'restorewindow'
		GladeWindow.__init__( self, gladefile = _gladefile,
							  widget_list = _wdgt_lst,
							  handlers = _hdls, root = _top_win_name,
							  parent = parent, pull_down_dict=None )
		self.set_top_window( self.widgets[_top_win_name] )
		self.top_window.set_icon_from_file(Util.getResource("nssbackup-restore.png"))

	def __init_statusbar(self):
		"""Initializes the statusbar, i.e. gets the context (here
		'nssbackup restore') and displays 'Ready'.
		"""
 		if self.__context_id is not None:
 			raise AssertionError("Statusbar cannot be intialized multiple times!")		
		self.__context_id = self.widgets['statusbar'].get_context_id("nssbackup restore")
		self.__send_statusbar_msg(message=_("Ready"))

 	def __send_statusbar_msg(self, message):
 		"""Puts the given message on the statusbar's message stack and
 		returns the id.
 		
 		@param message: The message that should be displayed
 		@type message:  String
 		
 		@return: the id of the message
 		@rtype:  Integer
		
		@raise AssertionError: if the statusbar is not initialized
 		"""
 		if self.__context_id is None:
 			raise AssertionError("Please initialize statusbar first!")
 		message_id = self.widgets['statusbar'].push(self.__context_id, message)
		return message_id

 	def __clean_statusbar_msg(self, message_id = None):
 		"""Removes a message from the statusbar's message stack. If a
 		message id is given this particular message is removed from the stack.
 		If no id is given the last message is removed from stack. Whenever
 		it is possible one should use the message id to remove a certain
 		message to prevent unwanted removal of 'other' messages.
 		
 		@param message_id: the id of the message to remove
 		@type message_id:  Integer
 		 
 		@return: None

		@raise AssertionError: if the statusbar is not initialized
 		"""
 		if self.__context_id is None:
 			raise AssertionError("Please initialize statusbar first!")
 		if message_id is None:
 			self.widgets['statusbar'].pop(self.__context_id)
 		else:
 			self.widgets['statusbar'].remove(self.__context_id, message_id)

	
	def status_callback(self, getstatus):
		"""
		@todo: FIX ME - this does not work that way!
		"""
		return False
#		n,m, subm = getstatus()
#		if (n,m,subm) == (None,None,None):
#			return False
#		if n : 	self.widgets['statusBar'].set_fraction(n)
#		if m : self.widgets['statusBarLabel'].set_text(m)
#		if subm : self.widgets['statusBar'].set_text(subm)

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
		try :
			self.target =  self.fusefam.mount(newtarget)
			self.snpman = SnapshotManager(self.target)
			self.widgets["restoreExpander"].set_expanded(False)
			self.fill_calendar()
		except Exception, e :
			self.logger.error(str(e))
			self.logger.error(traceback.format_exc())
			dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
			dialog.run()
			dialog.destroy()

	def on_defaultradiob_toggled(self, *args):
		if self.widgets['defaultradiob'].get_active() :
			self.widgets['custominfos'].set_sensitive( False )
			self.change_target(self.config.get("general", "target"))
		elif self.widgets['customradiob'].get_active() :
			self.widgets['custominfos'].set_sensitive( True )

	def on_customchooser_clicked(self, *args):
		dialog = gtk.FileChooserDialog(_("Choose a source folder"), None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_local_only(False)
		if dialog.run() == gtk.RESPONSE_OK:
			self.widgets["customentry"].set_text(dialog.get_current_folder())
		dialog.destroy()

	def on_customapply_clicked(self, *args):
		"""
		Reload all backup info from a custom location
		"""
		ltarget = self.widgets["customentry"].get_text()
		self.change_target(ltarget)

	def on_calendar_month_changed(self, *args):
		self.fill_calendar()

	def on_calendar_day_selected(self, *args):
		self.currentSnp = None
		self.widgets["restoreExpander"].set_expanded(False)
		self.widgets['snpmanExpander'].set_expanded(False)
		self.load_snapshotslist(self.widgets['calendar'].get_date())

	def on_snplisttreeview_cursor_changed(self,*args):
		self.flisttreestore.clear()
		self.widgets["restoreExpander"].set_expanded(False)
		self.widgets['snpmanExpander'].set_expanded(False)
		tstore, iter = self.widgets['snplisttreeview'].get_selection().get_selected()
		self.currentSnp = self.snpman.getSnapshot(str(tstore.get_value(iter,0)))

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
	
	def on_filelisttreeview_cursor_changed(self, *args):
		self.widgets['buttonspool'].set_sensitive(True)

	def on_filelisttreeview_unselect_all(self, *args):
		self.widgets['buttonspool'].set_sensitive(False)

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

	def __load_filestree(self):
		"""Method that loads the files list from a snapshot. It uses threads
		and shows a progressbar.
		
		@return: None 
		"""
		self.flisttreestore.clear()
		self.widgets['buttonspool'].set_sensitive(False)
		self.currSnpFilesInfos = self.currentSnp.getSnapshotFileInfos()
		if self.currSnpFilesInfos :
			# load the items in background
			self.__get_snpfileinfo_items_bg()
	
	def __show_filestree(self, *args):
		"""Shows the tree of files within the GUI. We need to use the
		magic *args parameter due to the use of this method as callback
		function. Exceptions that were raised within the thread are handled
		here.
		
		@param args: parameters of this method; used as follows:
					 [0] - the id of the prior set statusbar message
					 [1] - the result of the threaded retrieval of items

		@return: None
		
		@raise ValueError: If number of parameters mismatch
		"""
		if len(args) != 2:
			raise ValueError("Method expects excatly 2 arguments! "\
							 "Got %s instead." % len(args))
		
		_statbar_msgid	= args[0]	# the first parameter given to the callback
		_items			= args[1]	# result of the worker task (auto added)
		
		# if a statusbar message was set, clean it now
		if _statbar_msgid:
			self.__clean_statusbar_msg(_statbar_msgid)
			
		self._stop_pulse()
		
		# check if an exception was returned
		if isinstance(_items, Exception):
			self.logger.error(str(_items))
			self.logger.error(traceback.format_exc())
			self._show_errmessage( message_str = str(_items),
					boxtitle = _("NSsbackup restore error"),
					headline_str = _("An error occured "\
									 "while reading snapshot:"))
			_items = None

		if not _items :		# first items is empty
			self.flisttreestore.append(None,
									[_("This snapshot seems empty."),None])
			self.widgets['snpdetails'].set_sensitive(False)
		else :
			self.widgets['snpdetails'].set_sensitive(True)
			for k in _items :
				# add k and append the content if not empty
				iter = self.flisttreestore.append(None,
							[k,TAR.Dumpdir.getHRCtrls()[TAR.Dumpdir.DIRECTORY]])
				self.appendContent(k, iter)
					
	def __get_snpfileinfo_items_bg(self):
		"""This method shows a message in the statusbar and retrieves the
		snapshot informations in background (threaded).
		After finishing the retrieval the method '__show_filestree' is called.
		
		@return: None
		"""
		_statbar_msgid = self.__send_statusbar_msg(\
												_("Reading backup snapshot..."))
		self._start_pulse()
		_task = tasks.WorkerThread( self.currSnpFilesInfos.getFirstItems )
		_task.set_finish_callback( gobject.idle_add, self.__show_filestree,
								   _statbar_msgid )		
		_task.start()

	def load_snapshotslist(self, date):
		"""
		load the snapshot list for that date
		@param date: a tupe (year, month, day) using the Calendar.get_date convention ie month is 0-11
		"""
		day = "-".join([str(date[0]),"%02d" % (int(date[1])+1),"%02d" % date[2]])
		self.logger.debug("Selected day : " + day)
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

	def on_restoreExpander_activate(self,*args):
		if not self.widgets["restoreExpander"].get_expanded():
			tstore, iter = self.widgets['snplisttreeview'].get_selection().get_selected()
			if iter:
				self.currentSnp = self.snpman.getSnapshot(str(tstore.get_value(iter,0)))
				if self.currentSnp.getVersion() != Infos.SNPCURVERSION:
					message = _("The snapshot version is not supported (Just %(supportedversion)s is supported). Version '%(currentversion)s' found. You should upgrade it. ") % {'supportedversion': Infos.SNPCURVERSION, 'currentversion':self.currentSnp.getVersion() }
					self.logger.warning(message) 
					dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=message)
					dialog.run()
					dialog.destroy()
					self.widgets["snpdetails"].set_sensitive(False)
				else:
					self.__load_filestree()
			else:
				self.widgets["snpdetails"].set_sensitive(False)

	def on_restore_clicked(self, *args):
		tstore, iter = self.widgets['filelisttreeview'].get_selection().get_selected()
		src = self.path_to_dir( tstore.get_path( iter ) )
		dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Do you really want to restore backuped copy of '%s' ?" % src)
		
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			self.__restore_bg( mode = "restore",
						restore_callable = self.restoreman.restore,
						source = src, dirname = None )				
		
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
				self.__restore_bg( mode = "restore_as", 
							restore_callable = self.restoreman.restoreAs,
							source = src, dirname = dirname )

	def on_revert_clicked(self, *args):
		tstore, iter = self.widgets['filelisttreeview'].get_selection().get_selected()
		src = self.path_to_dir( tstore.get_path( iter ) )
		dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="Do you really want to revert '%s' ?" % src)
		
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			self.__restore_bg( mode = "revert",
						restore_callable = self.restoreman.revert,
						source = src, dirname = None )

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
				self.__restore_bg( mode = "revert_as",
							restore_callable = self.restoreman.revertAs,
							source = src, dirname = dirname )

	def __restore_bg(self, mode, restore_callable, source, dirname = None ):
		"""Helper method that creates a thread for the restoration process
		in background and shows an appropriate dialog box. The distinction
		between reverting and restoring is done by using a 'mode' variable.
		
		@param mode: operation mode of the restoration
		@param restore_callable: the object that actually performs the
								 restoration
		@param source:  what should be restored (filename/directory)
		@param dirname: where should it restored; if not set the original
						location is used
						
		@type mode:				String
		@type restore_callable: callable object
		@type source: 			String
		@type dirname: 			String (if used)
		
		@return: None
		"""
		snapshot 		= self.currentSnp
		statbar_msgid 	= self.__send_statusbar_msg(self.__msg_statusbar[mode])
		
		self.__restore_dialog.set_mode( mode )
		self.__restore_dialog.set_info(source, dirname)
		self.__restore_dialog.begin_restore()

		_task = tasks.WorkerThread( restore_callable )
		_task.set_finish_callback( gobject.idle_add, self.__restore_finished,
								   statbar_msgid )

		if dirname is None:
			_task.start( snapshot, source )
		else:
			_task.start( snapshot, source, dirname )

	def __restore_finished(self, *args):
		"""Callback method that is called after finishing of a restoration
		process. We need to use the magic *args parameter due to the use
		of this method as callback function. Exceptions that were raised
		within the thread are handled here.
		
		@param args: parameters of this method; used as follows:
					 [0] - the id of the prior set statusbar message
					 [1] - the result of the threaded restoration

		@return: None
		
		@raise ValueError: If number of parameters mismatch
		"""
		if len(args) != 2:
			raise ValueError("Method expects excatly 2 arguments! "\
							 "Got %s instead." % len(args))

		# this is the paramter given to the callback
		_statbar_msgid	= args[0]
		# this is the result of the thread
		_result 		= args[1]
		
		self.__clean_statusbar_msg(_statbar_msgid)

		if not isinstance(_result, Exception):
			self.__restore_dialog.finish_sucess()
		else:
			self.__restore_dialog.finish_failure( _result )
		
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
		
	def on_upgradeButton_clicked(self, *args):
		um = UpgradeManager()
		self.timer = gobject.timeout_add (100, self.status_callback, um.getStatus)
		um.upgradeSnapshot(self.currentSnp)
		self.load_snapshotslist(self.widgets['calendar'].get_date())
		self.widgets['snpmanExpander'].set_expanded(False)
		self.on_snpmanExpander_activate()
		self.widgets['snpmanExpander'].set_expanded(True)

	def on_rebaseButton_toggled(self, *args):
		if self.widgets['rebaseButton'].get_active():
			self.widgets['snphistoryFrame'].show()
			histlist = self.snpman.getSnpHistory(self.currentSnp)
			for snapshot in histlist:
				self.historylisttreestore.append(None, [snapshot.getName()])
		else :
			# get the selected base and rebase on it.
			tstore, iter = self.widgets['historytv'].get_selection().get_selected()
			if iter :
				snp = self.snpman.getSnapshot(str(tstore.get_value(iter,0)))
				try:
					message = _("Do you really want to rebase '%s' on '%s' ?") % (self.currentSnp, snp)
					dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=message)
					response = dialog.run()
					dialog.destroy()
					if response == gtk.RESPONSE_YES:
						self.timer = gobject.timeout_add (100, self.status_callback, self.snpman.getStatus)
						self.snpman.rebaseSnapshot(self.currentSnp, snp)
				except Exception, e: 
					self.logger.error(str(e))
					self.logger.error(traceback.format_exc())
					dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
					dialog.run()
					dialog.destroy()
			self.widgets['snphistoryFrame'].hide()
			self.historylisttreestore.clear()

	def on_deleteButton_clicked(self, *args):
		message = _("Are you sure that you want to definitely remove snapshot '%s' ?") % self.currentSnp
		dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=message)
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			try :
				self.snpman.removeSnapshot(self.currentSnp)
			except Exception, e: 
				self.logger.error(str(e))
				self.logger.error(traceback.format_exc())
				dialog = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_CLOSE, message_format=str(e))
				dialog.run()
				dialog.destroy()
			self.snpman.getSnapshots(forceReload=True)
			self.on_calendar_day_selected()
		
	def on_exportmanExpander_activate(self, *args):
		print("TODO: on_exportmanExpander_activate")
		pass
	
	def gtk_main_quit( self, *args):
		self.fusefam.terminate()
		gtk.main_quit()


class RestoreDialog(GladeWindow, ProgressbarMixin):
	"""This is the window that appears if the restoration process is invoked.
	"""
	
	__messages 		= { "restore"	 : { "dialog_titletxt" : _("NSsbackup restoration"),
										 "msg_headline"    : _("<b>Restoring of selected files</b>"),
										 "msg_progress"    : _("Restoring of <tt>'%s'</tt> is in progress."),
										 "msg_sucess"  	   : _("Restoring of <tt>'%s'</tt> was sucessful."),
										 "msg_failure"     : _("Restoring of <tt>'%s'</tt> was not sucessful.\n\nThe following error occured:\n") },
										 
						"restore_as" : { "dialog_titletxt" : _("NSsbackup restoration"),
										 "msg_headline"    : _("<b>Restoring of selected files</b>"),
										 "msg_progress"    : _("Restoring of <tt>'%s'</tt>\nto <tt>'%s'</tt> is in progress."),
										 "msg_sucess"      : _("Restoring of <tt>'%s'</tt>\nto <tt>'%s'</tt> was sucessful."),
										 "msg_failure"     : _("Restoring of <tt>'%s'</tt>\nto <tt>'%s'</tt> was not sucessful.\n\nThe following error occured:\n") },
										 
						"revert"	 : { "dialog_titletxt" : _("NSsbackup restoration"),
										 "msg_headline"    : _("<b>Reverting selected files</b>"),
										 "msg_progress"    : _("Reverting of <tt>'%s'</tt> is in progress.\n"),
										 "msg_sucess"  	   : _("Reverting of <tt>'%s'</tt> was sucessful."),
										 "msg_failure"     : _("Reverting of <tt>'%s'</tt> was not sucessful.\n\nThe following error occured:\n") },

						"revert_as"	 : { "dialog_titletxt" : _("NSsbackup restoration"),
										 "msg_headline"    : _("<b>Reverting selected files</b>"),
										 "msg_progress"    : _("Reverting of <tt>'%s'</tt>\nto <tt>'%s'</tt> is in progress."),
										 "msg_sucess"      : _("Reverting of <tt>'%s'</tt>\nto <tt>'%s'</tt> was sucessful."),
										 "msg_failure"     : _("Reverting of <tt>'%s'</tt>\nto <tt>'%s'</tt> was not sucessful.\n\nThe following error occured:\n") },
					  }

	def __init__(self, parent):
		"""Default constructor.
		"""
		self.init(parent)				
		ProgressbarMixin.__init__(self, self.widgets['restore_progressbar'])
		self.__mode = None
		self.__source = None
		self.__dirname = None

		self._init_pulse()
		
	def init(self, parent):
		_gladefile = Util.getResource('nssbackup-restore.glade')

		_wdgt_lst = [
			'restoreDialog',
			'txt_title',
			'txt_content',
			'button_cancel',
			'button_close',
			'restore_progressbar'
			]

		_hdls = [
			'_on_button_close_clicked'
			]

		_top_win_name = 'restoreDialog'
		GladeWindow.__init__( self, gladefile = _gladefile,
							  widget_list = _wdgt_lst,
							  handlers = _hdls, root = _top_win_name,
							  parent = parent, pull_down_dict = None )
		self.set_top_window( self.widgets[_top_win_name] )
		self.top_window.set_icon_from_file(\
									Util.getResource("nssbackup-restore.png"))
		
	def _on_button_close_clicked(self, *args):
		"""Event handler for clicking the close button.
		"""
		self.top_window.hide()
		
	def set_mode(self, mode):
		"""Sets the operation mode for this dialog.
		@param mode: the operation mode; valid values are:
					 'restore'
					 'restore_as'
					 'revert'
					 'revert_as'
		@type mode: String
		
		@return: None
		"""
		self.__mode = mode

	def set_info(self, source, dirname):
		"""The given informations about the source and the directory are
		set.
		"""
		self.__source = source
		self.__dirname = dirname
		
	def begin_restore(self):
		"""Signals the beginning of the restoration process using the prior
		set informations.
		
		@return: NoneS
		"""
		dirname = self.__dirname
		source = self.__source
		msgs = self.__messages[self.__mode]
		if dirname is None:
			begin_msg = msgs["msg_progress"] % (source)
		else:
			begin_msg = msgs["msg_progress"] % (source, dirname)

		self.widgets['button_close'].set_sensitive(False)
		self.widgets['txt_title'].set_markup(msgs["msg_headline"])
		self.widgets['txt_content'].set_markup(begin_msg)
		self.top_window.show()
		self._start_pulse()
		
	def finish_sucess(self):
		"""Signals the sucessful finish of the restoration process.
		
		@return: None
		"""
		dirname = self.__dirname
		source = self.__source
		msgs = self.__messages[self.__mode]
		if dirname is None:
			msg_sucess = msgs["msg_sucess"] % (source)
		else:
			msg_sucess = msgs["msg_sucess"] % (source, dirname)

		self._stop_pulse()
		self.widgets['restore_progressbar'].hide()
		self.widgets['txt_content'].set_markup(msg_sucess)
		self.widgets['button_close'].set_sensitive(True)
		
	def finish_failure(self, failure):
		"""Signals the finish of the restoration process if a failure
		happened.
		
		@param failure: the failure that happend
		@type failure:  any object that is reprintable using 'str()'
		
		@return: None
		"""
		dirname = self.__dirname
		source = self.__source
		msgs = self.__messages[self.__mode]
		if dirname is None:
			msg_failure = msgs["msg_failure"] % (source)
		else:
			msg_failure = msgs["msg_failure"] % (source, dirname)

		msg_failure += str(failure)
		
		self._stop_pulse()
		self.widgets['restore_progressbar'].hide()
		self.widgets['txt_content'].set_markup(msg_failure)
		self.widgets['button_close'].set_sensitive(True)


def main(argv):
	restore_win = SBRestoreGTK()
	restore_win.show()
	gtk.main()
