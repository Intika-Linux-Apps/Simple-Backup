#
# sbackup - legacy support for restore operation
#
#   Copyright (c)2013: Jean-Peer Lorenz <peer.loz@gmx.net>
#   Copyright (c)2005-2008: Aigars Mahinovs <aigarius@debian.org>
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


import shutil
import datetime
import tempfile
import filecmp

import sys
import os.path
import re
import threading
import time
import traceback

import sbackup.util as Util

# Attempt to load GTK bindings
try:
    import pygtk
    pygtk.require("2.0")
    import gtk
    import gtk.glade
except ImportError:
    print "Failed to load Python GTK/Gnome bindings. Please check your Gnome installation."
    sys.exit(1)
try:
    import gnomevfs
except ImportError:
    import gnome.vfs as gnomevfs
    
from sbackup.ui import misc
sys.excepthook = misc.except_hook_threaded


_LEGACY_RESTOREGUI_GLADE = Util.get_resource_file('sbackup-legacy-restore.glade')


class SRestore:
    def __init__(self):
        pass

    def restore( self, backup, spath, dpath = None ):
        """
        Restore one file or directory from the backup tdir with name
        spath to dpath (or to its old location).
        All existing files must be moved to a "*.before_restore_$time" files.
        """
        
        if not dpath:
            dpath = spath

        # Gather spath and dpath information
        if spath[0] == "/": spath = spath[1:]
        (sparent, sname) = os.path.split( spath )
        if not sname:
            spath = sparent
            (sparent, sname) = os.path.split( sparent )
        dpath = os.path.normpath( dpath )
        (dparent, dname) = os.path.split( dpath )
        if not dname:
            dpath = dparent
            (dparent, dname) = os.path.split( dpath )
        
        now = datetime.datetime.now().isoformat("_").replace( ":", "." )
        ver = str(gnomevfs.read_entire_file( backup+"/ver" ))
        
        try: 
            if ver[:3] == "1.4":
                self.childlist = [x[1:] for x in gnomevfs.read_entire_file( backup+"/flist" ).split( "\000" ) if x == "/"+spath or x[1:len(spath)+2]==spath+"/"]
            else:
                print "Only snapshot version 1.4 is supported"
                return False
        except:
            print "E: Error opening backup snapshot metadata"
            return False

        if len(self.childlist) == 0:
            print "E: File not found in the backup snapshot"
            return False

        if os.path.exists(dpath):
            if os.path.isdir(dpath):
                tdir = tempfile.mkdtemp( dir=dpath )
                self.extract( backup, spath, tdir )
                for _file in self.childlist:
                    if len(self.childlist)==1:
                        bname = sname
                        src = os.path.join( tdir, spath )
                    else:
                        bname = _file[len(spath)+1:]
                        src = os.path.join( tdir, spath, bname )
                    dst = os.path.join( dpath, bname )
                    if os.path.isdir(src):
                        if not os.path.exists(dst):
                            os.makedirs(dst)
                        srcstat = os.stat( src )
                        os.chown( dst, srcstat.st_uid, srcstat.st_gid )
                        os.chmod( dst, srcstat.st_mode )
                    elif os.path.isfile(src) or os.path.islink(src):
                        if os.path.exists(dst) and not filecmp.cmp(src, dst):
                            shutil.move( dst, dst+".before_restore_"+now )
                        if not os.path.exists(dst):
                            shutil.move( src, dst )
                    else:
                        print "W: Path '%s' is neither directory nor file! Skipped." % src
                shutil.rmtree( tdir )
            else:
                tdir = tempfile.mkdtemp( dir=dparent )
                self.extract( backup, spath, tdir )
                shutil.move( dpath, dpath+".before_restore_"+now )
                shutil.move( os.path.join(tdir,spath), dpath )
                shutil.rmtree( tdir )
                
        else:
            tdir = tempfile.mkdtemp( dir=dparent )
            self.extract( backup, spath, tdir )
            shutil.move( os.path.join(tdir,spath), dpath )
            shutil.rmtree( tdir )

        return True

    def islocal( self, uri ):
        local = True
        try:
            if not gnomevfs.URI( uri ).is_local:
                local = False
        except:
            pass
        return local

    def extract( self, backup, spath, tdir ):
        tarline = "tar -xzp --occurrence=1 --ignore-failed-read -C '"+tdir+"' "
        if self.islocal( backup ):
            tarline += " -f '"+backup+"/files.tgz' '"+spath+"' >/dev/null 2>&1"
            os.system( tarline )
        else:
            tarline += "'"+spath+"' 2>/dev/null"
            tsrc = gnomevfs.open( backup+"/files.tgz", 1)
            tdst = os.popen( tarline, "w" )
            try: shutil.copyfileobj( tsrc, tdst, 100*1024 )
            except gnomevfs.EOFError: pass
            tdst.close()
            tsrc.close()


class SRestoreGTK:
    """
    Main GUI application class.
    """
    
    default_target = "/var/backup"
    target = default_target
    versions = []
    
    
    def __init__(self):
        """
        Initializes the application.
        """

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

        self.widgets = gtk.glade.XML(_LEGACY_RESTOREGUI_GLADE)
        
        self.widgets.signal_autoconnect(self.signals)
        
        # Get handle to window
        self.window = self.widgets.get_widget("restore")

        self.widgets.get_widget("labelDefaultSource").set_text(self.default_target)    

        # Load the backup tree from the default location
        self.init_tree()
        self.sel = self.flist_widget.get_selection()
        self.sel.set_mode( gtk.SELECTION_SINGLE )
        self.load_tree(self.default_target)
        
        gtk.gdk.threads_init()
        # Start the main loop
        gtk.main()
    
    def init_tree(self):
        """
        Initalizes the tree structure
        """
        
        self.flist_widget = self.widgets.get_widget("treeview1")
        self.treestore = gtk.TreeStore( str )
        
        self.flist_widget.set_model( self.treestore )
        
        acolumn = gtk.TreeViewColumn( "Path", gtk.CellRendererText(), text=0 )
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
        self.treestore.clear()
        
        # Checking if the target directory is local or remote
        local = True
        try:
            if gnomevfs.URI( target ).is_local:
                target = gnomevfs.get_local_path_from_uri( target )
            else:
                local = False
        except:
            pass

        self.local = local
        self.target = target
        
        # Checking if it is a readable directory
        if local:
            if not (os.path.exists( target ) and os.path.isdir( target ) and os.access( target, os.R_OK | os.X_OK ) ):    
                self.treestore.append( None, ["Error: backups directory does not exist!"])
                self.target = False
        else:
            if not (gnomevfs.exists( target ) and gnomevfs.get_file_info(target).type == 2):
                self.treestore.append( None, ["Error: backups directory does not exist!"])
                self.target = False
        
        # Get list of backup directories
        r = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})[\:\.](\d{2})[\:\.](\d{2})\.\d+\..*?\.(.+)$")
        
        listing = []
    
        if local and self.target:
            listing = os.listdir( target )
            listing = filter( r.search, listing )
        elif self.target:
            try:     
                d = gnomevfs.open_directory( target )
                listing = []
                for f in d:
                    if f.type == 2 and f.name != "." and f.name != ".." and r.search( f.name ):
                        listing.append( f.name )
            except: pass

        # Check if these directories are complete and remove from the list those that are not
        for adir in listing[:]:
            if not gnomevfs.exists(self.target+"/"+adir+"/ver") :
                listing.remove( adir )
                continue
            else :
                if str(gnomevfs.read_entire_file( self.target+"/"+adir+"/ver"))[:3] != "1.4":
                    listing.remove( adir )
                    continue

        listing.sort()
        listing.reverse()

        self.vtree = {}

        if listing == []:
            self.treestore.append( None, ["Error: no backups found in the target directory"])
            self.target = False
        else:
            for base in listing:
                if str(gnomevfs.read_entire_file(target+"/"+base+"/ver"))[:3] == "1.4":
                    self.vtree[base] = str(gnomevfs.read_entire_file(target+"/"+base+"/flist")).split("\000")
                else:
                    self.vtree[base] = str(gnomevfs.read_entire_file(target+"/"+base+"/flist")).split("\n")
        
        self.blist.clear()
        
        for base in listing:
            self.blist.append( [base] )
        
        self.good = False
        self.on_selection_change()
        if self.target:
            self.treestore.append( None, ["Select any of the available backups to see list of files that can be restored."])        
        
    def on_customFolderButton_clicked(self, *args):
        dialog = gtk.FileChooserDialog("Choose a source folder", None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
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
        
    def on_expand_row( self, tv, aiter, path, user_data=None):
        """
        When a row in the file tree view is expanded, we populate
        it with children (unless they are there already).
        """
        if self.treestore.iter_nth_child( aiter, 1 ):
            return
        self.show_dir( self.path_to_dir(path), aiter )

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
            aiter = self.treestore.append( rootiter, [d] )
            self.treestore.append( aiter, ["Loading ..."] )
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
        
        self.load_tree(self.widgets.get_widget("entry1").get_text())

    def on_selection_change(self, *args):
        """
        Enable/disable restore buttons as selection changes
        """
        (model, aiter) = self.sel.get_selected()
        if aiter and self.good:
            self.widgets.get_widget("button2").set_sensitive(True)
            self.widgets.get_widget("button3").set_sensitive(True)
        else:
            self.widgets.get_widget("button2").set_sensitive(False)
            self.widgets.get_widget("button3").set_sensitive(False)
    
    def _restore_init( self, *args):
        """
        Internal function to prepare for restorin a file
        """
        (store, aiter) = self.widgets.get_widget("treeview1").get_selection().get_selected()
        self.src = self.path_to_dir( store.get_path( aiter ) )
        return aiter
    
    def _do_restore( self, src, dst):
        """ Internal function to ask for confirmation and call the real restore library func"""
        dialog = gtk.MessageDialog(parent=None, flags=0,
                        type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO,
                        message_format="Do you really want to restore backuped copy of '%s' to '%s' ?" % (src, dst))
        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_YES:
            while gtk.events_pending():
                gtk.main_iteration(False)
            dialog = self.widgets.get_widget("restore_progress_dialog")
            dialog.show()

            progressBar = self.widgets.get_widget("progressbar")
            progressThread = ProgressThread(dialog, progressBar)
            progressThread.setDaemon(True)
            progressThread.start()
            tdir = self.target+"/"+self.get_active_text(self.widgets.get_widget("combobox1"))
            self.restoreThread = RestoreThread(tdir, src, dst, progressThread)
            self.restoreThread.setDaemon(True)
            self.restoreThread.start()

    def restore( self, *args):
        """ Restore selected path to its original location"""
        self._restore_init()
        self._do_restore( self.src, self.src )

    def restore_as( self, *args):
        """ Restore selected path to a specific location"""
        aiter = self._restore_init()
        if self.treestore.iter_children( aiter ):
            # is a directory
            dialog = gtk.FileChooserDialog(title="Select restore location",
                                action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            dialog.set_filename( self.src )
            result = dialog.run()
            filename = dialog.get_filename()
            dialog.destroy()

            if result == gtk.RESPONSE_OK:
                self._do_restore( self.src, filename )
        else:
            dialog = gtk.FileChooserDialog(title="Select restore location",
                                action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            dialog.set_filename( self.src )
            dialog.set_current_name( self.src )
            result = dialog.run()
            filename = dialog.get_filename()
            dialog.destroy()

            if result == gtk.RESPONSE_OK:
                self._do_restore( self.src, filename )


class RestoreThread(threading.Thread):

    def __init__(self, tdir, src, dst, progressThread):
        threading.Thread.__init__(self)
        self.tdir = tdir
        self.src = src
        self.dst = dst
        self.alive = True
        self.progressThread = progressThread

    def run(self):
        try:
            r = SRestore()
            r.restore( self.tdir, self.src, self.dst )
            del r
        except:
            _exc = traceback.format_exc()
            misc.show_errdialog_threaded(message_str = "An uncaught error "\
                        "occurred. Close this message window and restart the "\
                        "application.\n\nPlease report this error on "\
                        "https://bugs.launchpad.net/sbackup.",
                        parent = None,
                        headline_str = "Sorry, this should not have happened",
                        secmsg_str = _exc)
        self.alive = False
        self.progressThread.cancel = True


class ProgressThread(threading.Thread):

    def __init__(self, dialog, progressBar):
        threading.Thread.__init__(self)
        self.dialog = dialog
        self.progressBar = progressBar
        self.cancel = False

    def run(self):
        while not self.cancel:
            self.progressBar.pulse()
            time.sleep(0.5)

        self.dialog.destroy()
