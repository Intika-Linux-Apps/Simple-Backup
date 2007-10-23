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
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>

import re, os, os.path, shutil, filecmp
import cPickle as pickle
try:
    import gnomevfs
except ImportError:
    import gnome.vfs as gnomevfs


def delete(  uri ):
	" Deletes a file or a dir (recursively) "
	if islocal( uri ):
		if isdir( uri ):
			shutil.rmtree( uri, False )
			return True
		else : 
			os.unlink(uri)
			return True
	else:
		if not isdir( uri ):
		    gnomevfs.unlink( uri )
		else:
		    d = gnomevfs.open_directory( uri )
		    for f in d:
			if f.name=="." or f.name=="..":
			    continue
			if f.type==2:
			    delete( uri+"/"+f.name )
			else:
			    gnomevfs.unlink( uri+"/"+f.name )
		    d.close()
		    gnomevfs.remove_directory( uri )

def isdir(  uri ):
	"checks if the given uri is a dir"
	if uri.startswith(os.sep) :
		return os.path.isdir(uri)
	else :
		return ( gnomevfs.get_file_info( uri ).type == 2 )

def rename(  uri, name ) :
	"""
	 Rename the given uri file name to the new file name. 
	 ex: rename("/my/dir/filename", "newfilename") => "/my/dir/newfilename"
	"""
	p = gnomevfs.get_file_info( uri )
	p.name = name
	gnomevfs.set_file_info( uri, p, 1 )

def chmod(  uri, mode ):
	" Applies a chmod to the given file "
	p = gnomevfs.get_file_info( uri )
	p.permissions = mode
	gnomevfs.set_file_info( uri, p, 2 )

def copyfile(src, dest ):
	"copy the source file to the dest one"
	if islocal(src) and not isdir(src):
		if islocal(dest) :
			shutil.copy2(src, dest)
		else :
			s1 = open( src, "r" )
			if exists(dest) and isdir(dest) :
				splited = src.split("/")
				turi = gnomevfs.URI( dest +"/"+ splited[len(splited)-1] )
			else :
				turi = gnomevfs.URI( dest )
			d1 = gnomevfs.create( turi, 2 )
			shutil.copyfileobj( s1, d1 )
			s1.close()
			d1.close()		
	else : 
		print(" No support for copying from remote file/dir ")
		return

def permissions(  uri ):
	" Gets the permissions on the given file "
	return gnomevfs.get_file_info( uri ).permissions

def exists(  uri ):
	" checks if the given uri exists "
	if islocal(uri):
		return os.access( uri, os.F_OK )
	else:
		return gnomevfs.exists( uri )

def islocal(  uri ):
	" checks if the file is local or remote "
	return gnomevfs.URI( uri ).is_local

def openfile(  uri, write=False ):
	" opens a file for reading or writing. Default is reading "
	if islocal( uri ):
		if write:
			return open( uri, "w" )
		else:
			return open( uri, "r" )
	else:
		if write:
			if exists( uri ):
				return gnomevfs.open( uri, 2 )
			else:
				return gnomevfs.create( uri, 2 )
		else:
			return gnomevfs.open( uri, 1 )
			
def perm_secure(  tdir ):
	" Secures permissions "
	chmod( tdir, 0750 )
	chmod( tdir+"/ver", 0640 )
	chmod( tdir+"/tree", 0640 )
	chmod( tdir+"/flist", 0640 )
	chmod( tdir+"/fprops", 0640 )
	chmod( tdir+"/files.tgz", 0640 )
	chmod( tdir+"/packages", 0640 )
	chmod( tdir+"/excludes", 0640 )
	chmod( tdir+"/base", 0640 )

def listdir( target) :
	""" 
	List a directory.
	@param target: The dir to list de content 
	@return: a list ['file1','file2','file3' ...]
	"""
	if islocal( target ):
	    listing = os.listdir( target )
	else:
	    d = gnomevfs.open_directory( target )
	    listing = []
	    for f in d:
	        if f.name != "." and f.name != "..":
	            listing.append( f.name )
	return listing

def makedir( target) :
	" make a directory "
	if islocal(target):
		os.makedirs( target, 0750 )
	else:
		gnomevfs.make_directory( target, 0750 )
		
def createfile(filepath):
	"""
	Create an empty file
	@param filepath : The file path
	"""
	filepath = filepath.rstrip("/")
	spl = filepath.split("/")
	if len(spl) == 1 :
		writetofile(filepath, "")
	else :
		dir = filepath[:-len(spl[len(spl)-1])]
		if exists(dir) :
			writetofile(filepath, "")
		else :
			makedir(dir)
			writetofile(filepath, "")
		
def readfile( uri) :
	" Read a file from a given URI and return a string with the read content "
	if islocal( uri ) :
		f = open( uri, "r" )
		value = f.read()
		f.close()
		return str( value )
	else :
		return str( gnomevfs.read_entire_file( uri ) )

def writetofile( File, StringToWrite ) :
	"""
	Write a String to a file. You don't have to open and close the file.
	- File = path to the file
	- StringToWrite = String to write into the file.
	"""
	f = openfile(File, True)
	f.write( StringToWrite )
	f.close()

def pickledump( datas, file ):
	"""
	Dump the given datas into the file given 
	@param datas: any type of python datas/object
	@param file : a file path to the file in wich the dump will be made
	"""
	f = openfile(file, True)
	pickle.dump( datas , f )
	f.close()

def pickleload( file):
	"""
	Load a python object from the given pickle file
	@param file: the path of the pickle file
	"""
	f = openfile(file)
	result = pickle.load(f)
	f.close()
	return result
