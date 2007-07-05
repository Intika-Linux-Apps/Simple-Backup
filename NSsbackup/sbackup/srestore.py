#!/usr/bin/python
#
# Simple Backup suit
#
# Running this command will restore a file or directory from backup.
# This is also a backend for simple-restore-gnome GUI.
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

import sys, re, os, os.path, shutil, datetime, tempfile, filecmp

try:
    import gnomevfs
except ImportError:
    import gnome.vfs as gnomevfs

import locale
import gettext
from gettext import gettext as _

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
				self.childlist = [x[1:] for x in gnomevfs.read_entire_file( backup+"/flist" ).split( "\n" ) if x == "/"+spath or x[1:len(spath)+2]==spath+"/"]
		except:
			print "E: Error opening backup snapshot metadata"
			return False

		if len(self.childlist) == 0:
			print _("E: File not found in the backup snapshot")
			return False

		if os.path.exists(dpath):
			if os.path.isdir(dpath):
				tdir = tempfile.mkdtemp( dir=dpath )
				self.extract( backup, spath, tdir )
				for file in self.childlist:
					print file
					if len(self.childlist)==1:
					    bname = sname
					    src = os.path.join( tdir, spath )
					else:
					    bname = file[len(spath)+1:]
					    src = os.path.join( tdir, spath, bname )
					dst = os.path.join( dpath, bname )
					if os.path.isdir(src):
						if not os.path.exists(dst):
							os.makedirs(dst)
						srcstat = os.stat( src )
						os.chown( dst, srcstat.st_uid, srcstat.st_gid )
						os.chmod( dst, srcstat.st_mode )
					else:
						if os.path.exists(dst) and not filecmp.cmp(src, dst):
							shutil.move( dst, dst+".before_restore_"+now )
						if not os.path.exists(dst):
							shutil.move( src, dst )
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

if __name__ == "__main__":

	# i18n init
	locale.setlocale(locale.LC_ALL, '')
	gettext.textdomain("sbackup")
	gettext.install("sbackup", unicode=True) 

	r = SRestore()
	if not len(sys.argv) in [3,4]:
		print _("Simple Backup suit command line restore utility\n")
		print _(" Usage: simple-restore backup-url file-or-dir-to-restore [target-file-or-dir]")
		print _(" Note: backup-url must include the snapshot subdirectory name, for example:")
		print "  /var/backup/2005-08-09_14.59.38.441112.myhost.ful/"
		print _(" Use simple-restore-gnome for more ease of use.\n")
		sys.exit(1)
	
	if len(sys.argv) == 3:
		ret = r.restore( sys.argv[1], sys.argv[2] )
	else:
		ret = r.restore( sys.argv[1], sys.argv[2], sys.argv[3] )

	if not ret:
		print _("Restore FAILED! Please check you parameters.")
