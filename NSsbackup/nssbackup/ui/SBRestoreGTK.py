#!/usr/bin/env python
    
#----------------------------------------------------------------------
# SBRestoreGTK.py
# Ouattara Aziz
# 07/07/2007
#----------------------------------------------------------------------

import sys

from GladeWindow import *

#----------------------------------------------------------------------

class SBRestoreGTK(GladeWindow):

	#----------------------------------------------------------------------

	def __init__(self):

		''' '''
		self.init()

	#----------------------------------------------------------------------

	def init(self):

		filename = '../../datas/simple-restore-gnome.glade'

		widget_list = [
			'restorewindow',
			'vbox1',
			'table1',
			'defaultradiob',
			'customradiob',
			'hbox2',
			'customentry',
			'customchooser',
			'customapply',
			'hbox1',
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
			'on_defaultradiob_group_changed',
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

	def on_defaultradiob_group_changed(self, *args):
		print("TODO: on_defaultradiob_group_changed")
		pass

	#----------------------------------------------------------------------

	def on_customchooser_clicked(self, *args):
		print("TODO: on_customchooser_clicked")
		pass

	#----------------------------------------------------------------------

	def on_customapply_clicked(self, *args):
		print("TODO: on_customapply_clicked")
		pass

	#----------------------------------------------------------------------

	def on_calendar_month_changed(self, *args):
		print("TODO: on_calendar_month_changed")
		pass

	#----------------------------------------------------------------------

	def on_calendar_day_selected(self, *args):
		print("TODO: on_calendar_day_selected")
		pass

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

def main(argv):

	w = SBRestoreGTK()
	w.show()
	gtk.main()

#----------------------------------------------------------------------

if __name__ == '__main__':
	main(sys.argv)
