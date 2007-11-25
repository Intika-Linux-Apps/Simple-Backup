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
from nssbackup.util.log import getLogger
from nssbackup.util.exceptions import SBException
from tempfile import *
import inspect, shutil
from shutil import *


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
				copy2(srcname, dstname)
			# XXX What about devices, sockets etc.?
		except (IOError, os.error), why:
			errors.append((srcname, dstname, str(why)))
		# catch the Error from the recursive copytree so that we can
		# continue with other files
		except Error, err:
			errors.extend(err.args[0])
	try:
		copystat(src, dst)
	except OSError, why:
		errors.extend((src, dst, str(why)))
	if errors:
		raise Error, errors

def nssb_move(src, dst):
	"""
	mod of shutil.move that uses nssb_copytree
	"""
	
	try:
		os.rename(src, dst)
	except OSError:
		if os.path.isdir(src):
			if shutil.destinsrc(src, dst):
				raise Error, "Cannot move a directory '%s' into itself '%s'." % (src, dst)
			nssb_copytree(src, dst, symlinks=True)
			rmtree(src)
		else:
			copy2(src,dst)
			os.unlink(src)

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
	for dir in resfile.readlines() :
		dir = dir.strip()
		#getLogger().debug("Searching in directory '%s'" % dir)
		if os.path.exists(dir) and os.path.isdir(dir):
			list = os.listdir(dir)
			#getLogger().debug("File list is :" + str(list))
			for f in list :
				if f == resourceName :
					return os.path.normpath(os.sep.join([dir,resourceName]))
	devvalue = os.path.dirname(tmp)+"/../datas/"
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
	# Create output log file
	outptr,outFile = mkstemp(prefix="output_")

	# Create error log file
	errptr, errFile = mkstemp(prefix="error_")

	# Call the subprocess using convenience method
	opts.insert(0,cmd)
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
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)
	
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
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)


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
		
	
import pygtk
pygtk.require('2.0')
import gtk, gobject

# Update the value of the progress bar so that we get
# some movement
def progress_timeout(pbobj):
	
	pbobj.pbar.pulse()
	
	# As this is a timeout function, return TRUE so that it
	# continues to get called
	return True
	