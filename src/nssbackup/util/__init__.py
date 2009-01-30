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

import nssbackup.managers.FileAccessManager as FAM
import os
import subprocess, nssbackup
from nssbackup.util.log import LogFactory
from nssbackup.util.exceptions import SBException
from nssbackup.util.exceptions import ChmodNotSupportedError
import tempfile
import inspect, shutil
import shutil
import types
import re


def nssb_copytree(src, dst, symlinks=False):
	"""
	mod of shutil.copytree 
	This doesn't fail if the directory exists, it copies inside
	"""
	names = os.listdir(src)
	if not os.path.exists(dst) :
		os.makedirs(dst)
	errors = []
	for name in names:
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)
		try:
			if symlinks and os.path.islink(srcname):
				linkto = os.readlink(srcname)
				os.symlink(linkto, dstname)
			elif os.path.isdir(srcname):
				nssb_copytree(srcname, dstname, symlinks)
			else:
				shutil.copy2(srcname, dstname)
			# XXX What about devices, sockets etc.?
		except (IOError, os.error), why:
			errors.append((srcname, dstname, str(why)))
		# catch the Error from the recursive copytree so that we can
		# continue with other files
		except shutil.Error, err:
			errors.extend(err.args[0])
	try:
		shutil.copystat(src, dst)
	except OSError, why:
		errors.extend((src, dst, str(why)))
	if errors:
		raise shutil.Error, errors

def nssb_move(src, dst):
	"""
	mod of shutil.move that uses nssb_copytree
	"""
	
	try:
		os.rename(src, dst)
	except OSError:
		if os.path.isdir(src):
			if shutil.destinsrc(src, dst):
				raise shutil.Error, "Cannot move a directory '%s' into itself '%s'." % (src, dst)
			nssb_copytree(src, dst, symlinks=True)
			shutil.rmtree(src)
		else:
			shutil.copy2(src,dst)
			os.unlink(src)
			
def nssb_copy(src, dst):
	"""Customized copy routine that copies the fileobject and afterwards
	tries to copy the file permissions. If this fails a custom exception
	is raised. The date and archive bit of the file is not copied. 
	
	@param src: an existing file that should be copied
	@param dst: copy destination - an existing directory or full path to new
				file (the directory must exist too)
				
	@return: None
	
	@raise ChmodNotSupportedError: if the permissions could not be copied
	"""
	prep_src, prep_dst = _prepare_nssb_copy(src, dst)
	shutil.copyfile(prep_src, prep_dst)
	try:
		shutil.copymode(prep_src, prep_dst)
	except OSError:
		raise ChmodNotSupportedError("Unable to change permissions of file '%s'." % prep_dst)
		
def _prepare_nssb_copy(src, dst):
	"""Helper function that prepares the given paths for copying
	using 'nssb_copy'.
	
	Source must be a file or symbolic link to a file!
	
	@todo: Implement test case for symbolic links!
	"""
	# firstly the types are checked
	if not isinstance( src, types.StringTypes):
		raise TypeError("Given parameter must be a string. "\
					    "Got %s instead." % (type(src)))
	if not isinstance( dst, types.StringTypes):
		raise TypeError("Given parameter must be a string. "\
					    "Got %s instead." % (type(dst)))
		
	# only absolute paths are supported
	if not os.path.isabs(src):
		raise ValueError("Given copy source '%s' must be absolute." % src)
	if not os.path.isabs(dst):
		raise ValueError("Given copy destination '%s' must be absolute." % dst)

	# the source must be a file and exist
	if not os.path.isfile(src):	
		raise IOError("Given copy source '%s' does not exist." % src)

	_src_file = os.path.basename(src)
	_src_dir = os.path.dirname(src)

	if os.path.isdir(dst):
		_dst_file = _src_file
		_dst_dir = dst
	elif dst.endswith(os.path.sep):
		_dst_file = _src_file
		_dst_dir = dst		
	else:
		_dst_file = os.path.basename(dst)
		_dst_dir = os.path.dirname(dst)
	
	if not os.path.isdir(_dst_dir):
		raise IOError("Given copy destination '%s' does not exist." % _dst_dir)

	_dst_path = os.path.join( _dst_dir, _dst_file )
	retval = (src, _dst_path)

	return retval
	

def getResource(resourceName):
	"""
	This will look for a ressource installed by nssbackup.
	The installation script write in the ressources file were it stores the file
	then getRessource will look for them.
	@param ressourceName: the ressource name, as complete as possible.
	@param the ressource: absolute path. 
	"""
	tmp = inspect.getabsfile(nssbackup)
	resfile = open(os.sep.join([os.path.dirname(tmp),"ressources"]))
	for _dir in resfile.readlines() :
		_dir = _dir.strip()
		#LogFactory.getLogger().debug("Searching in directory '%s'" % dir)
		if os.path.exists(_dir) and os.path.isdir(_dir):
			if _dir.endswith(resourceName):
				return _dir 
			list = os.listdir(_dir)
			#LogFactory.getLogger().debug("File list is :" + str(list))
			for f in list :
				if f == resourceName :
					return os.path.normpath(os.sep.join([_dir,resourceName]))
	devvalue = os.path.dirname(tmp)+"/../../datas/"
	if os.path.exists(devvalue + resourceName) :
		return os.path.normpath(devvalue + resourceName)
	raise SBException("'%s' hasn't been found in the ressource list"% resourceName)
					
def launch(cmd, opts):
	"""
	launch a command and gets stdout and stderr
	outStr = a String containing the output from stdout" 
	errStr = a String containing the error from stderr
	retVal = the return code (= 0 means that everything were fine )
	@param cmd: The command to launch
	@return: (outStr, errStr, retVal)
	"""
	_logger = LogFactory.getLogger()
	# Create output log file
	outptr,outFile = tempfile.mkstemp(prefix="output_")

	# Create error log file
	errptr, errFile = tempfile.mkstemp(prefix="error_")

	# Call the subprocess using convenience method
	opts.insert(0,cmd)
	_logger.debug("Lauching : "+str(opts))
	retval = subprocess.call(opts, 0, None, None, outptr, errptr)

	# Close log handles
	os.close(errptr)
	os.close(outptr)
	
	outStr, errStr = FAM.readfile(outFile),FAM.readfile(errFile)
	
	FAM.delete(outFile)
	FAM.delete(errFile)
	
	return (outStr, errStr, retval)

def extract(sourcetgz, file, dest , bckupsuffix = None):
	"""
	Extract from source tar.gz the file "file" to dest.
	@param source:
	@param file:
	@param dest:
	"""
	# strip leading sep
	file = file.lstrip(os.sep)
	
	options = ["-xzp", "--occurrence=1", "--ignore-failed-read", '--backup=existing']
	if os.getuid() != 0 :
		options.append("--same-owner")
	if dest :
		options.append( "--directory="+dest )
	else : 
		options.append( "--directory="+os.sep )
	if bckupsuffix :
		options.append("--suffix="+bckupsuffix)
	options.extend(['--file='+sourcetgz,file])
	
	outStr, errStr, retval = launch("tar", options)
	if retval != 0 :
		LogFactory.getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	LogFactory.getLogger().debug("output was : " + outStr)
	
def extract2(sourcetgz, fileslist, dest, bckupsuffix = None ):
	"""
	Extract the files listed in the 'fileslist' file to dest. This method 
	has been created to optimize the time spent by giving to tar a complete 
	list of file to extract. Use this if ever you have to extract more than 1 dir .
	@param sourcetgz:
	@param fileslist: a path to the file containing the list
	@param dest: destination
	"""
	options = ["-xzp", "--ignore-failed-read", '--backup=existing']
	if os.getuid() != 0 :
		options.append("--same-owner")
	if dest :
		options.append( "--directory="+dest )
	else : 
		options.append( "--directory="+os.sep )
	if bckupsuffix :
		options.append("--suffix="+bckupsuffix)
	
	options.extend(['--file='+sourcetgz,'--null','--files-from='+os.path.normpath(fileslist)])
	
	outStr, errStr, retval = launch("tar", options)
	if retval != 0 :
		LogFactory.getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	LogFactory.getLogger().debug("output was : " + outStr)


def readlineNULSep(fd,fd1):
	"""
	Iterator that read a NUL separeted file as lines 
	@param fd: File descriptor
	@return: the gotten line
	@rtype: String
	"""
	_continue = 0
	
	while _continue < 2 :
		c = fd.read(1)
		currentline = ''
		
		while c :
			if c == '\0'  :
				# we got a line
				break
			currentline += c
			c = fd.read(1)
		else :
			# c is None
			# This else correspond to the while statement
			_continue += 1
		
		c1 = fd1.read(1)
		currentline1 = ''
		
		while c1 :
			if c1 == '\0'  :
				# we got a line
				break
			c1 = fd1.read(1)
			currentline1 += c1
		else :
			# c1 is None
			# This else correspond to the while statement
			_continue += 1
		
		if _continue == 1 :
			raise SBException("The length of flist and Fprops are not equals")
		yield (currentline,currentline1)


def is_valid_regexp( aregex ):
	"""Checks if the given string is a valid regular expression.
	@type aregex: String
	
	@todo: Is an empty expression valid or not? Can we combine both checks?
	"""
	if not isinstance( aregex, types.StringTypes):
		raise TypeError("is_valid_regexp: Given parameter must be a string. "\
					    "Got %s instead." % (type(aregex)))
	_res = True
	try:
		dummy = re.compile(aregex)
	except re.error:
		_res = False
	return _res


def is_empty_regexp( aregex ):
	"""Checks if the given parameter is empty, i.e. is None or a string
	containing only whitespaces.
	
	@type aregex: String 
	"""
	if not isinstance( aregex, (types.StringTypes, types.NoneType)):
		raise TypeError("is_empty_regexp: Given parameter must be a string "\
						"or None. Got %s instead." % (type(aregex)))
	_res = False
	if aregex is None:
		_res = True
	else:
		_stripped_aregex = aregex.strip()
		if _stripped_aregex == "":
			_res = True
	return _res


def remove_conf_entry(confline, entry, separator = ","):
	"""Removes the given entry from the given string. Entries in configurations
	were separated by specified token. Leading and trailing separators are
	taken into account.
	
	@param confline:  the string from which the entry should be removed
	@param entry:	  the string that is removed
	@param separator: the token that separates the entries
	
	@type confline:	  String
	@type entry:      String
	@type separator:  String
	
	@return: the configuration line without the removed entry
	@rtype:  String
	
	@raise TypeError: If one of the given parameters is not of string type
	"""
	if not isinstance( confline, types.StringTypes):
		raise TypeError("remove_conf_entry: Given parameter must be a string. "\
					    "Got %s instead." % (type(confline)))
	if not isinstance( entry, types.StringTypes):
		raise TypeError("remove_conf_entry: Given parameter must be a string. "\
					    "Got %s instead." % (type(entry)))
	if not isinstance( separator, types.StringTypes):
		raise TypeError("remove_conf_entry: Given parameter must be a string. "\
					    "Got %s instead." % (type(separator)))
	_line = "%s%s%s" % (separator, confline, separator)
	_mentry = r"%s%s%s" % (separator, re.escape( entry ), separator)
	_line = re.sub( _mentry , separator, _line )
	_line = _line.strip( separator )
	return _line
