#	NSsbackup - unified file handling
#
#   Copyright (c)2007-2009: Ouattara Oumar Aziz <wattazoum@gmail.com>
#   Copyright (c)2009-2010: Jean-Peer Lorenz <peer.loz@gmx.net>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
"""
:mod:`FileAccessManager` --- unified file handling
====================================================================

.. module:: FileAccessManager
   :synopsis: common functions for unified file handling
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

@todo: Should get renamed and moved to package 'utils'.

"""

import os.path
import shutil
import pickle
import stat
import types
import datetime


def __remove_trailing_sep(path):
	spath = path.rstrip(os.sep)
	return spath


def is_link(path):
	spath = __remove_trailing_sep(path)
	res = os.path.islink(spath)
	return res


def get_link(path):
	"""Returns the target of given link `path`. Relative links remain
	unchanged (i.e. are not made absolute). 
	"""
	if not is_link(path):
		raise ValueError("Given path is not a symbolic link.")
	_res = os.readlink(path)
	return _res


def get_link_abs(path):
	"""Returns the absolute target of given link `path`. Relative links are
	modified (i.e. are made absolute). 
	"""
	_ln_target = get_link(path)
	if os.path.isabs(_ln_target):
		_res = _ln_target
	else:
		_res = os.path.join(os.path.dirname(path), _ln_target)
	_res = os.path.abspath(_res)
	return _res


def is_dir(path):
	res = os.path.isdir(path)
	return res


def normpath(*args):
	"""Normalizes the given paths (i.e. concatenates them and removes trailing
	separators).
	
	@todo: Consistent handling of `normpath` (Quote: os.path.normpath - It should be understood
	that this may change the meaning of the path if it contains symbolic links!)
	"""
	_path = os.path.join(*args)
	_path = __remove_trailing_sep(_path)
#	_path = os.path.normpath(_path)
	return _path
	

def rename(src, dst):
	os.rename(src, dst)
	
	
def rename_rotating(src, dst, max_num):
	"""Renames the given file `src` to `dst`. The destination (i.e. the new
	file name) is renamed in rotated manner prior the actual renaming
	process.
	"""
	if not isinstance(src, types.StringTypes):
		raise TypeError("Expected string as source. Got %s instead." % type(src))
	if not isinstance(dst, types.StringTypes):
		raise TypeError("Expected string as destination. Got %s instead." % type(dst))
	if not isinstance(max_num, types.IntType):
		raise TypeError("Expected integer as max. number. Got %s instead." % type(max_num))
	if max_num < 1:
		raise ValueError("Max. number must be greater than 0.")
	
	# at first: rotating rename of destination
	for _num in range(max_num, 0, -1):
		_rot_src = append_str_to_filename(dst, str((_num - 1)))
		_rot_target = append_str_to_filename(dst, str(_num)) 
		if _num == 1:
			_rot_src = dst
		if exists(_rot_src):
			rename(_rot_src, _rot_target)
	# then rename the source file
	rename(src, dst)
			
		
def append_time_to_filename(filename, filetype=""):
	if not isinstance(filename, types.StringTypes):
		raise TypeError("Expected string. Got %s instead." % type(filename))
	if not isinstance(filetype, types.StringTypes):
		raise TypeError("Expected string as file type. Got %s instead." % type(filetype))
	if filetype != "" and not filetype.startswith("."):
		raise ValueError("Given file type must start with dot (.xyz).")

	_time = datetime.datetime.now().isoformat("_").replace( ":", "." )
	_res = append_str_to_filename(filename, _time, filetype)
	return _res


def append_str_to_filename(filename, str_to_append, filetype=""):
	"""If a file type (i.e. file extension) is specified, the string
	to append is put in front of the file type extension.
	
	Example: string to append = 123
			 filename = basename.log
			 result without specifying a filetype = basename.log.123 
			 result with specifying filetype '.log' = basename.123.log 
			 
	"""
	if not isinstance(filename, types.StringTypes):
		raise TypeError("Expected string as filename. Got %s instead." % type(filename))
	if not isinstance(str_to_append, types.StringTypes):
		raise TypeError("Expected string to append. Got %s instead." % type(str_to_append))
	if not isinstance(filetype, types.StringTypes):
		raise TypeError("Expected string as file type. Got %s instead." % type(filetype))
	if filetype != "" and not filetype.startswith("."):
		raise ValueError("Given file type must start with dot (.xyz).")
	
	_filen = filename
	_ext = ""
	if filetype != "":
		if filename.endswith(filetype):
			_filen = filename.rstrip(filetype)
	_res = "%s.%s%s" % (_filen, str_to_append, filetype)
	return _res


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
			if os.path.isdir(_entrypath)  and not os.path.islink(_entrypath):
				__add_write_permission(_entrypath)		
			else:
				__add_write_permission(path, recursive=False)


def delete(uri):
	"""Deletes given file or directory (recursive).
	"""
	if os.path.isdir(uri) and not os.path.islink(uri):
		shutil.rmtree(uri, ignore_errors=False)	#, onerror=_onerror)
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
	"""checks if the given uri exists.
	@todo: Add check `os.path.exists()`.
	"""
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
