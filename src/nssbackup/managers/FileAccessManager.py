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

"""Module contains common functions for unified file handling.

@todo: Should get renamed and moved to package 'utils'.
"""

import os
import shutil
import pickle
import stat


def rename(src, dst):
	os.rename(src, dst)
		

def __add_write_permission(path, recursive = True):
	"""Sets write permissions for user, group, and others for
	given directory or file (recursive). 
	"""
	fstats = os.stat(path)
	fmode = fstats.st_mode
	fmode = fmode | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
	os.chmod(path, fmode)

	if os.path.isdir(path) and recursive is True:
		for _entry in os.listdir(path):
			_entrypath = os.path.join(path, _entry)		
			if os.path.isdir(_entrypath):
				__add_write_permission(_entrypath)		
			else:
				__add_write_permission(path, recursive=False)


def delete(uri):
	"""Deletes given file or directory (recursive).
	"""
	if os.path.isdir(uri):
		shutil.rmtree(uri, ignore_errors=False)	#, onerror=_onerror)
		return True
	else:
		os.unlink(uri)
		return True


def force_delete(path):
	"""Forces removal of given file or directory (recursive).
	"""
	__add_write_permission(path, recursive=True)
	delete(path)


def copyfile(src, dest ):
	"copy the source file to the dest one"
	if not os.path.isdir(src):
		shutil.copy2(src, dest)


def exists(  uri ):
	" checks if the given uri exists "
	return os.access( uri, os.F_OK )


def openfile(  uri, write=False ):
	" opens a file for reading or writing. Default is reading "
	if write:
		return open( uri, "w" )
	else:
		return open( uri, "r" )

			
def listdir( target) :
	"""List a directory.
	@param target: The dir to list de content 
	@return: a list ['file1','file2','file3' ...]
	"""
	listing = os.listdir( target )
	return listing


def makedir( target) :
	" make a directory "
	os.makedirs( target, 0750 )

		
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

		
def readfile( uri ) :
	" Read a file from a given URI and return a string with the read content "
	f = open( uri, "r" )
	value = f.read()
	f.close()
	return str( value )


def writetofile( File, StringToWrite ) :
	"""
	Write a String to a file. You don't have to open and close the file.
	- File = path to the file
	- StringToWrite = String to write into the file.
	"""
	fobj = openfile(File, write=True)
	fobj.write( StringToWrite )
	fobj.close()


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
