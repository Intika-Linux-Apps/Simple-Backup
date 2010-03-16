#	NSsbackup - provides access to TAR functionality
#
#   Copyright (c)2007-2008: Ouattara Oumar Aziz <wattazoum@gmail.com>
#   Copyright (c)2008-2009: Jean-Peer Lorenz <peer.loz@gmx.net>
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
:mod:`tar` --- provides access to TAR functionality
===================================================

.. module:: tar
   :synopsis: provides access to TAR functionality
.. moduleauthor:: Ouattara Oumar Aziz (alias wattazoum) <wattazoum@gmail.com>
.. moduleauthor:: Jean-Peer Lorenz <peer.loz@gmx.net>

"""


import os,re,shutil
from gettext import gettext as _
from nssbackup.util.log import LogFactory
import nssbackup.util as Util
from nssbackup.util.structs import SBdict
from nssbackup.util.exceptions import SBException
from nssbackup.util import exceptions
from datetime import datetime
import time
from nssbackup.managers import ConfigManager
from nssbackup.managers.ConfigManager import ConfigurationFileHandler


def getArchiveType(archive):
	"""Determines the type of an archive by its mime type.
	 
	@param archive: Full path to file to check  
	@return: tar, gzip, bzip2 or None
	@rtype: String
	"""
	_res = None
	command = "file"
	opts = ["--mime", "-b", archive]
	out, err, retVal = Util.launch(command, opts)
	if "x-bzip2" in out:
		_res = "bzip2"
	elif "x-gzip" in out:
		_res = "gzip"
	elif "x-tar" in out:
		_res = "tar"
	return _res
	
	
def extract(sourcear, file, dest , bckupsuffix = None, splitsize=None):
	"""Extract from source archive the file "file" to dest.
	
	@param sourcear: path of archive
	@param file:
	@param dest:
	@param bckupsuffix: If set a backup suffix option is set to backup existing files
	@param splitsize: If set the split options are added supposing the size of the archives is this variable
	@type splitsize: Integer in KB
	"""
	# strip leading sep
	file = file.lstrip(os.sep)
	
	options = ["-xp", "--ignore-failed-read", '--backup=existing']
	
	archType = getArchiveType(sourcear)
	if archType =="tar" :
		pass
	elif archType == "gzip" :
		options.insert(1,"--gzip")
	elif archType == "bzip2" :
		options.insert(1,"--bzip2")
	else :
		raise SBException (_("Invalid Archive type"))
		
	if os.getuid() == 0 :
		options.append("--same-owner")
	if dest :
		options.append( "--directory="+dest )
	else : 
		options.append( "--directory="+os.sep )
	if bckupsuffix :
		options.append("--suffix="+bckupsuffix)
	
	if splitsize :
		options.extend(["-L "+ str(splitsize) , "-F "+ Util.getResource("multipleTarScript")])
	
	options.extend(['--file='+sourcear,file])
	
	LogFactory.getLogger().debug("Launching TAR with options : %s" % options)
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		LogFactory.getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	LogFactory.getLogger().debug("output was : " + outStr)
	
def extract2(sourcear, fileslist, dest, bckupsuffix = None,additionalOpts=None ):
	"""
	Extract the files listed in the 'fileslist' file to dest. This method 
	has been created to optimize the time spent by giving to tar a complete 
	list of file to extract. Use this if ever you have to extract more than 1 dir .
	@param sourcear:
	@param fileslist: a path to the file containing the list
	@param dest: destination
	@param bckupsuffix: 
	@param additionalOpts: a list of aption to add
	"""
	# tar option  -p, --same-permissions, --preserve-permissions:
	# ignore umask when extracting files (the default for root)

	options = ["-xp", "--ignore-failed-read", '--backup=existing']
	
	archType = getArchiveType(sourcear)
	if archType =="tar" :
		pass
	elif archType == "gzip" :
		options.insert(1,"--gzip")
	elif archType == "bzip2" :
		options.insert(1,"--bzip2")
	else :
		raise SBException (_("Invalid Archive type"))
		
	if os.getuid() == 0 :
		options.append("--same-owner")
	if dest :
		options.append( "--directory="+dest )
	else : 
		options.append( "--directory="+os.sep )
	if bckupsuffix :
		options.append("--suffix="+bckupsuffix)
	
	if additionalOpts and type(additionalOpts) == list :
		options.extend(additionalOpts)
		
	options.extend(['--file='+sourcear,'--null','--files-from='+os.path.normpath(fileslist)])
	
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		LogFactory.getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	LogFactory.getLogger().debug("output was : " + outStr)

def appendToTarFile(desttar, fileOrDir, workingdir=None,additionalOpts=None ):
	"""
	@param desttar: The tar file to wich append
	@param fileOrDir: The file or directory to append, can be a list of files too
	@type fileOrDir: str or list
	@param workingDir: the dir to move in before appending the dir ( usefun for relative paths)
	@param additionalOpts: a list of additional option to append (will be append before changing the working dir)
	"""
	options = ["--append", "--ignore-failed-read"]
	
	archType = getArchiveType(desttar)
	if archType =="tar" :
		pass
	elif archType == "gzip" :
		options.insert(1,"--gzip")
	elif archType == "bzip2" :
		options.insert(1,"--bzip2")
	else :
		raise SBException (_("Invalid Archive type"))
		
	if additionalOpts and type(additionalOpts) == list :
		options.extend(additionalOpts)
		
	options.extend(['--file='+desttar,'--null'])
	
	if workingdir:
		options.append("--directory="+workingdir)
	
	if type(fileOrDir) is str:
		options.append(fileOrDir)
	elif type(fileOrDir) is list :
		options.extend(fileOrDir)
	
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		LogFactory.getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	LogFactory.getLogger().debug("output was : " + outStr)

def appendToTarFile2(desttar, fileslist, additionalOpts=None ):
	"""
	"""
	options = ["--append", "--ignore-failed-read"]
	
	archType = getArchiveType(desttar)
	if archType =="tar" :
		pass
	elif archType == "gzip" :
		options.insert(1,"--gzip")
	elif archType == "bzip2" :
		options.insert(1,"--bzip2")
	else :
		raise SBException (_("Invalid Archive type"))
		
	if additionalOpts and type(additionalOpts) == list :
		options.extend(additionalOpts)
		
	options.extend(['--file='+desttar,'--null','--files-from='+os.path.normpath(fileslist)])
	
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		LogFactory.getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	LogFactory.getLogger().debug("output was : " + outStr)

def __prepareTarCommonOpts(snapshot):
	"""Prepare the options to fill tar in.
	
	:param snapshot: The snapshot to fill in
	:return: a list of options to be use to launch tar
	
	:todo: Check whether it's necessary to escape white spaces in path names!
	
	"""
	# don't escape spaces i.e. do not replace them with '\ '; this will fail
	tdir = snapshot.getPath()
	options = list()
	
	options.extend(["-cS","--directory="+ os.sep,
				    "--ignore-failed-read",
				    "--files-from="+snapshot.getIncludeFListFile()+".tmp"])
	options.append ("--exclude-from="+snapshot.getExcludeFListFile()+".tmp")
	
	if snapshot.isFollowLinks() :
		options.append("--dereference")
	
	archivename = "files.tar"
	if snapshot.getFormat() == "gzip":
		options.insert(1,"--gzip")
		archivename+=".gz"
	elif snapshot.getFormat() == "bzip2":
		options.insert(1,"--bzip2")
		archivename+=".bz2"
	elif snapshot.getFormat() == "none":
		pass
	else :
		LogFactory.getLogger().debug("Defaulting to gzip ! ")
		options.insert(1,"--gzip")
		archivename+=".gz"
	
	options.append("--file="+os.sep.join([tdir,archivename]) )
	
	LogFactory.getLogger().debug(options)
	
	LogFactory.getLogger().debug("Common TAR options : " + str(options))
	
	return options 
	
def __addSplitOpts(snapshot, options, size):
	"""
	Compiles and add the split management options to the TAR line.
	Valid for read and create actions
	@param snapshot: The snapshot to process
	@type snapshot: Snapshot
	@param options: the option in which to append
	@type options: list
	@param size: the size of each part (in KiB)
	@type size: int
	@raise SBException: if the snapshot format is other than none
	"""
	if snapshot.getFormat() != "none" :
		raise SBException(_("For the moment split functionality is not compatible with compress option ! "))
	options.extend(["-L "+ str(size) , "-F "+ Util.getResource("multipleTarScript")])
	return options

def makeTarIncBackup(snapshot):
	"""
	Launch a TAR incremental backup
	@param snapshot: the snapshot in which to make the backup
	@raise SBException: if there was a problem with tar
	"""
	LogFactory.getLogger().info(_("Launching TAR to make Inc backup "))
	
	options = __prepareTarCommonOpts(snapshot)
	
	splitSize = snapshot.getSplitedSize()
	if splitSize :
		options = __addSplitOpts(snapshot, options, splitSize)

	base_snarfile = snapshot.getBaseSnapshot().getSnarFile()
	snarfile = snapshot.getSnarFile()
	tmp_snarfile = os.path.join( ConfigurationFileHandler().get_user_tempdir(),
								 os.path.basename(snarfile) )
	
	LogFactory.getLogger().debug("Snapshot's base snarfile: %s" % base_snarfile)	
	LogFactory.getLogger().debug("Snapshot's snarfile: %s" % snarfile)
	LogFactory.getLogger().debug("Temporary snarfile: %s" % tmp_snarfile)
	
	# For an INC backup the base SNAR file should exists
	if not os.path.exists( base_snarfile ) :
		LogFactory.getLogger().error(_("Unable to find the SNAR file to make an Incremental backup"))
		LogFactory.getLogger().error(_("Falling back to full backup"))
		makeTarFullBackup(snapshot)
	else:
		shutil.copy( base_snarfile, tmp_snarfile )		
		# check (and set) the permission bits; necessary if the file's origin
		# does not support user rights (e.g. some FTP servers, file systems...)
		if not os.access(tmp_snarfile, os.W_OK):
			os.chmod(tmp_snarfile, 0644)

		# create the snarfile within a local directory; necessary if the
		# backup target does not support 'open' within the TAR process and
		# would fail
		options.append("--listed-incremental="+tmp_snarfile)
		
		outStr, errStr, retVal = Util.launch("tar", options)
		LogFactory.getLogger().debug("TAR Output : " + outStr)
		
		# and move the temporary snarfile back into the backup directory
		try:
			Util.nssb_copy( tmp_snarfile, snarfile )
		except exceptions.ChmodNotSupportedError:
			LogFactory.getLogger().warning(_("Unable to change permissions for "\
									  "file '%s'.") % snarfile )
		os.remove( tmp_snarfile )
		if retVal == 1 :
			# list-incremental is not compatible with ignore failed read
			LogFactory.getLogger().warning(_("TAR sent a warning when making the backup : ") + errStr )
		elif retVal != 0 :
			# list-incremental is not compatible with ignore failed read
			LogFactory.getLogger().error(_("Couldn't make a proper backup : ") + errStr )
			raise SBException(_("Couldn't make a proper backup : ") + errStr )
		

def makeTarFullBackup(snapshot):
	"""
	Launch a TAR full backup
	@param snapshot: the snapshot in which to make the backup
	@raise SBException: if there was a problem with tar
	"""
	LogFactory.getLogger().info(_("Launching TAR to make a Full backup "))
	
	options = __prepareTarCommonOpts(snapshot)
	
	splitSize = snapshot.getSplitedSize()
	if splitSize :
		options = __addSplitOpts(snapshot, options, splitSize)
	
	snarfile = snapshot.getSnarFile()
	tmp_snarfile = os.path.join( ConfigurationFileHandler().get_user_tempdir(),
								 os.path.basename(snarfile) )
	
	LogFactory.getLogger().debug("Snapshot's snarfile: %s" % snarfile)
	LogFactory.getLogger().debug("Temporary snarfile: %s" % tmp_snarfile)

	# For a full backup the SNAR file shouldn't exists
	if os.path.exists( snarfile ) :
		os.remove( snarfile )		
	if os.path.exists( tmp_snarfile ) :
		os.remove( tmp_snarfile )
	
	options.append( "--listed-incremental="+tmp_snarfile )

	outStr, errStr, retVal = Util.launch("tar", options)
	LogFactory.getLogger().debug("TAR Output : " + outStr)

	# and move the temporary snarfile into the backup directory
	try:
		Util.nssb_copy( tmp_snarfile, snarfile )
	except exceptions.ChmodNotSupportedError:
		LogFactory.getLogger().warning(_("Unable to change permissions for "\
									  "file '%s'.") % snarfile )
	os.remove( tmp_snarfile )

	if retVal == 1 :
		# list-incremental is not compatible with ignore failed read
		LogFactory.getLogger().warning(_("TAR sent a warning when making the backup : ") + errStr )
	elif retVal != 0 :
		# list-incremental is not compatible with ignore failed read
		LogFactory.getLogger().error(_("Couldn't make a proper backup : ") + errStr )
		raise SBException(_("Couldn't make a proper backup : ") + errStr )

	
def get_dumpdir_from_list(lst_dumpdirs, filename):
	"""Searchs within the given list of dumpdirs for the given filename
	and the dumpdir if found.
	
	@raise SBExcetion: if filename couldn't be found in list  
	"""
	_res = None

	if not isinstance(lst_dumpdirs, list):
		raise TypeError("Given list of dumpdirs must be of type list! Got %s "\
					    "instead." % type(lst_dumpdirs))
	for _ddir in lst_dumpdirs:
		if not isinstance(_ddir, Dumpdir):
			raise TypeError("Element in list of dumpdirs must be of type "\
							"Dumpdir! Got %s instead." % type(_ddir))

		if _ddir.getFilename() == filename:
			_res = _ddir
			break
		
	if _res is None:
		raise SBException("File '%s' was not found in given list of Dumpdirs."
																	% filename)
	return _res


class Dumpdir(object):
	"""This is actually a single dumdir entry.
	
	Here is the definition from TAR manual:
	Dumpdir is a sequence of entries of the following form: C filename \0
	where C is one of the control codes described below, filename is the name
	of the file C operates upon, and '\0' represents a nul character (ASCII 0).
	
	The white space characters were added for readability, real dumpdirs do not
	contain them. Each dumpdir ends with a single nul character.
	
	Dumpdirs stored in snapshot files contain only records of types 'Y', 'N'
	and 'D'. 

	
	@note: Is the nul character stored???
	
	@see: http://www.gnu.org/software/tar/manual/html_chapter/Tar-Internals.html#SEC173
	
	@todo: It should be distiguished between 'unchanged', 'excluded' and
		   'removed'!
	@todo: Rename this class into 'DumpdirEntry'!
	@todo: Add a 'DumpdirClass' that collects entries and creates output content!
	"""
	
	INCLUDED = 'Y'
	UNCHANGED = 'N'
	DIRECTORY = 'D'
	
	# The dictionary mapping control with their meanings
	__HRCtrls = {'Y':_('Included'),'N':_('Not changed'),'D':_('Directory')}
		
	def __init__(self, line):
		"""
		Constructor that takes a line to create a Dumpdir.
		we will parse this line and fill the Dumpdir in
		@param line: the line (in dumpdir point of view ) to parse
		@raise Exception: when the line doesn't have the requeried format
		
		@todo: make the instance variables private!
		"""
		self.control = None
		self.filename = None
		self.__set_entry(line)
		
	def __str__(self):
		return "%s %s" % (self.filename, self.getHumanReadableControl())
	
	def __repr__(self):
		return self.__str__()
	
	def __set_entry(self, line):
		"""Private helper method that sets the given dumdir entry. It checks
		for type and length of given parameter.
		
		@todo: Add checks for validity of control etc.!
		"""
		if (not isinstance(line, str)):
			raise TypeError(_("Line must be a string"))
		line = line.strip("\0")
		if len(line) < 2:
			raise ValueError("Line must contain 2 characters at minimum!")
		self.control = line[0]
		self.filename = line[1:]

	def getFilename(self):
		"""
		get the filename embedded in the Dumpdir
		@return: finename
		@raise Exception: if the filename is null 
		"""
		if self.filename :
			return self.filename
		else :
			raise SBException(_("Dumpdir inconsistancy : 'filename' is empty"))
		
	def getControl(self):
		"""
		Get the control character from the DumpDir
		@return: control
		@raise Exception: if the control is null
		
		@todo: Checking against None is useless here!
		"""
		if self.control:
			return self.control
		else :
			raise SBException(_("Dumpdir inconsistancy : 'control' is empty"))
	
	def getHumanReadableControl(self):
		"""
		Get the control character as a Human readable string from the DumpDir
		"""
		return self.__HRCtrls[self.getControl()]
		
	@classmethod
	def getHRCtrls(cls):
		"""
		@return: The Human Readable control dictionary
		@rtype: dict
		
		"""
		return cls.__HRCtrls
	

class SnapshotFile(object):
	"""A snapshot file (or directory file) is created during incremental
	backups with TAR. It contains the status of the file system at the time
	of the dump and is used to determine which files were modified since the
	last backup. GNU tar version 1.20 supports three snapshot file formats.
	They are called 'format 0', 'format 1' and 'format 2'.
	
	Dumpdirs stored in snapshot files contain only records of types 'Y', 'N'
	and 'D'. 
	
	For displaying the content of an incremental backup manually use:
	tar --bzip --list --incremental --verbose --verbose --file files.tar.bz2

	@see: http://www.gnu.org/software/tar/manual/html_chapter/Tar-Internals.html#SEC172
	
	@todo: Rename into 'DirectoryFile' or 'SnapshotDirectoryFile' since it only
	       collects directories!
	       
	@todo: Add class describing a SnapshotFile record!
	"""
	versionRE = re.compile("GNU tar-(.+?)-([0-9]+?)")
	
	__SEP = '\000'
	__entrySEP = 2*__SEP
	
	# Infos on indices in a record 
	REC_NFS = 0
	REC_MTIME_SEC = 1
	REC_MTIME_NANO = 2
	REC_DEV_NO = 3
	REC_INO = 4
	REC_DIRNAME = 5
	REC_CONTENT = 6
	
	
	def __init__(self, filename, writeFlag=False):
		"""Constructor
		 
		@param filename: the snapshot file absolute file path to get the infos (SNAR file)
		@param writeFlag: if set, the file will be created in case it doesn't exist
		"""
		self.header = None
		self.snpfile = None
		self.version = None

		if os.path.exists(filename) :
			self.snpfile = os.path.abspath(filename)
		else :
			if writeFlag :
				self.snpfile = os.path.abspath(filename)
				fd = open(self.snpfile, 'a+')
				fd.close()
			else :
				raise SBException(_("'%s' doesn't exist ") % filename)

	def get_filename(self):
		return self.snpfile

	def getFormatVersion(self):
		"""
		Get the format version
		@return: the version 
		@rtype: int 
		"""
		if self.version :
			return self.version
		
		self.header = self.__getHeaderInfos()
		m = self.versionRE.match(self.header)
		if m :
			# we are version 1 or 2
			# check for version 2 first
			self.version = m.group(2)
		else :
			# we are version 0
			self.version = 0
		
		return int(self.version)
		
	def __getHeaderInfos(self):
		"""
		Get the first line of the snapshot file
		@return: the first line content
		"""
		fd = open(self.snpfile)
		header = fd.readline()
		fd.close()
		return header.strip()
	
	def parseFormat0(self):
		"""
		Iterator method that gives each line entry
		@warning: only compatible tar version 0 of Tar format
		@return: [nfs,dev,inode,name]
		"""
		fd = open(self.snpfile)
		# skip header which is the first line in this case
		fd.readline()
		
		for line in fd.readlines():
			line = line.rstrip()
			
			nfs = line[0] # can be a + or a single white space
			
			dev,inode,name = line[1:].split(' ',2)
			yield [nfs,dev,inode,name]
		
		fd.close()
		
	def parseFormat1(self):
		"""
		Iterator method that gives each line entry
		@warning: only compatible tar version 1 of Tar format
		@return: [nfs,mtime_sec,mtime_nsec,dev,inode,name]
		"""
		fd = open(self.snpfile)
		# skip header which is the 2 first lines in this case
		fd.readline()
		fd.readline()
		
		for line in fd.readlines() :
			line = line.rstrip()
			
			nfs = line[0] # can be a + or a single white space
			
			mtime_sec,mtime_nsec,dev,inode,name = line[1:].split(' ',4)
			yield [nfs,mtime_sec,mtime_nsec,dev,inode,name]
		
		fd.close()
		
	def parseFormat2(self):
		"""Iterator method that gives each line entry in SNAR-file.
		A line contains informations about a directory and its content.
		
		@warning: only compatible tar version 2 of Tar format
		
		@return: [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a list of Dumpdirs
		
		@todo: Iterator methods should have names like 'parseFormat2Iterator' or
		       'parseFormat2Iter'!
		"""
		
		def formatDumpDirs(content):
			"""
			Subroutine to format a content into dump dirs
			"""
			result = []
			if content :
				for d in content.rstrip('\0').split('\0'):
					if d :
						result.append(Dumpdir(d))
			return result
		
		def format(line):
			"""
			subroutine to format a line including NUL char to have and array
			"""
			nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents = line.lstrip("\0").split("\0",6)
			return [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,formatDumpDirs(contents)]
			
			
		fd = open(self.snpfile)
		# skip header which is the first line and 2 entries separated with NULL in this case
		l = fd.readline()
		if l !="":
			#Snarfile not empty
			n = 0
			while n < 2 :
				c = fd.read(1)
				if len(c) != 1:
					raise SBException(_("The snarfile header is incomplete !"))
				if c == '\0' : n += 1
			
			currentline=""
			
			c = fd.read(1)
			last_c = ''
			
			while c :
				currentline += c
				if c == '\0' and last_c == '\0' :
					# we got a line
					yield format(currentline)
					
					currentline = ''
					last_c = ''
				else :
					last_c = c
				c = fd.read(1)
			
			fd.close
	
	def getHeader(self):
		"""
		Get the full header
		@return: the header (a string) or None if the file was empty
		@raise SBException: if the header is incomplete
		"""
		fd = open(self.snpfile)
		header = fd.readline()
		if header !="":
			#Snarfile not empty
			n = 0
			while n < 2 :
				c = fd.read(1)
				if len(c) != 1:
					raise SBException(_("The snarfile header is incomplete !"))
				if c == '\0' : n += 1
				header += c
		else :
			header = None
				
		return header
	
	def setHeader(self,timeofBackup):
		"""
		Sets the header of the snar File. 
		GNU tar-1.19-2  -> in the first line
		second line is timeofBackupInSec\000timeofBackupInNano
		@param timeofBackup: The time to set in the snar file
		@type timeofBackup: datetime
		"""
		if type(timeofBackup) != datetime :
			raise SBException("timeofBackup must be a datetime")
		fd = open(self.snpfile,'w')
		
		fd.write("GNU tar-1.19-2\n")
		t = int(time.mktime(timeofBackup.timetuple()))
		fd.write(2*(str(t)+self.__SEP))
		fd.close()
		
	def addRecord(self, record):
		"""
		Write a record in the snar file. A record is a tuple with 6 entries + a content that is a dict
		@param record: A tuple that contains the record to add. [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a dict of {file:'control'}
		"""
		if len(record) != 7:
			raise ValueError("Record must contain of 7 elments. Got %s instead." % str(len(record)))
				
		woContent,contents = record[:-1],record[-1]
		# compute contents
		strContent = self.createContent(contents)
		toAdd = self.__SEP.join(woContent)+self.__SEP+strContent
		
		fd = open(self.snpfile,'a+')
		fd.write(toAdd + self.__entrySEP)
		fd.close()
		
		
	def createContent(self, contentList):
		"""Creates a content item from a list of given Dumpdirs.
		
		@param contentList: the list of Dumpdirs
		@type contentList: list
		@return: a string containing the computed content
		@rtype: string
		"""
		if type(contentList) != list :
			raise SBException("Contentlist must be a list : %r" % repr(contentList))
		
		result = ""
		
		for dumpdir in contentList:
			if not isinstance(dumpdir, Dumpdir):
				raise TypeError("Contentlist must contain elements of type "\
							    "'Dumdir'! Got %s instead." % type(dumpdir))
			result += dumpdir.getControl()+dumpdir.getFilename()+self.__SEP
		
		return result


class SnapshotFileWrapper(object):
	def __init__(self):
		pass
	
	def get_snapfile_path(self):
		raise NotImplementedError
	
	
class MemSnapshotFile(SnapshotFileWrapper, SBdict):
	"""
	This is a representation in memory of a simplified SNAR file. The used structure is an SBDict.
	The "prop" value is the content of the directory. wich is a list of L{Dumpdir}
	"""
		
	def __init__(self, snapshotFile):
		"""
		load the snapshotFile in memory
		@param snapshotFile: a SnapshotFile to convert in MemSnapshotFile
		@type snapshotFile: nssbackup.util.tar.SnapshotFile
		"""
		if not isinstance(snapshotFile, SnapshotFile) :
			raise Exception("A SnapshotFile is required")
		
		SnapshotFileWrapper.__init__(self)
#		SBdict.__init__(self, mapping)
		
		self.__snapshotFile = snapshotFile
		
		for f in snapshotFile.parseFormat2():
			self[f[-2]] = f[-1]
		
	def get_snapfile_path(self):
		return self.__snapshotFile.get_filename()

	def hasPath(self,path):
		"""
		Checks if a path is include in the SNAR file
		@param path: The path to check
		@return: True if the file is included, False otherwise
		@rtype: boolean
		"""
		return self.has_key(path)
	
	def addRecord(self,record):
		"""
		Write a record in the snar file. A record is a tuple with 6 entries + a content that is a dict
		@param record: A tuple that contains the record to add. [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a dict of {file:'control'}
		"""
		self.__snapshotFile.addRecord(record)
		self[record[-2]] = record[-1]
	
	def getHeader(self):
		self.__snapshotFile.getHeader()
		
	def setHeader(self,timeofBackup):
		"""
		Sets the header of the snar File. 
		GNU tar-1.19-2  -> in the first line
		second line is timeofBackupInSec\000timeofBackupInNano
		@param timeofBackup: The time to set in the snar file
		@type timeofBackup: datetime
		"""
		self.__snapshotFile.setHeader(timeofBackup)
	
	def getContent(self,dirpath):
		"""
		convenance method to get the content of a directory.
		@param dirpath: The directory absolute path to get
		@type dirpath: str
		@return: The content of the dir
		@rtype: list
		"""
		return self[dirpath]
	
	def getFirstItems(self):
		"""
		Get the first items in this SnapshotFile (the lower level dirs in the file)
		@return: A list of paths
		@rtype: list 
		"""
		result = list()
		for f in self.iterFirstItems():
			result.append(f)
		return result
		
		
class ProcSnapshotFile(SnapshotFileWrapper):
	"""This is a Snapshotfile that will basically every time parse the
	snarfile for information.
	"""
	
	def __init__(self, snapshotFile):
		"""
		load the snapshotFile to get a reference on it
		@param snapshotFile: a SnapshotFile to convert in MemSnapshotFile
		@type snapshotFile: nssbackup.util.tar.SnapshotFile
		"""
		if not isinstance(snapshotFile, SnapshotFile) :
			raise TypeError(_("A SnapshotFile is required"))
		
		SnapshotFileWrapper.__init__(self)
		
		self.__snapshotFile = snapshotFile
		
	def get_snapfile_path(self):
		return self.__snapshotFile.get_filename()

	def hasPath(self,path):
		"""
		Checks if a path is included in the SNAR file
		@param path: The path to check
		@return: True if the file is included, False otherwise
		@rtype: boolean
		"""
		for f in self.__snapshotFile.parseFormat2():
			if f[SnapshotFile.REC_DIRNAME].rstrip(os.sep) == path.rstrip(os.sep):
				return True
		return False
	
	def hasFile(self,_file):
		"""
		Checks if a file is included in the SNAR file. a file is in a directory thus in the content.
		@param _file: The file to check. a complete path must be given
		@return: True if the file is included, False otherwise
		@rtype: boolean
		"""
		dir, inFile = _file.rsplit(os.sep,1)
		if not self.hasPath(dir):
			return False
		for f in self.getContent(dir):
			if f.getFilename() == inFile and f.getControl() != Dumpdir.UNCHANGED:
				return True
		return False
	
	def iterfiles(self):
		"""
		iterator that returns every file in the snapshot
		"""
		for l in self.__snapshotFile.parseFormat2():
			dir = l[-2]
			if l[-1] :
				for dumpdir in l[-1] :
					yield dir+os.sep+dumpdir.getFilename()
	
	def iterRecords(self):
		"""Iterator over snar file records (wrapper on the
		'parseFormat2' method of SnaspshotFile
		"""
		for record in self.__snapshotFile.parseFormat2():
			yield record
	
	
	def addRecord(self,record):
		"""
		Write a record in the snar file. A record is a tuple with 6 entries + a content that is a dict
		@param record: A tuple that contains the record to add. [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a dict of {file:'control'}
		"""
		self.__snapshotFile.addRecord(record)
	
	def getHeader(self):
		return self.__snapshotFile.getHeader()
	
	def setHeader(self,timeofBackup):
		"""
		Sets the header of the snar File. 
		GNU tar-1.19-2  -> in the first line
		second line is timeofBackupInSec\000timeofBackupInNano
		@param timeofBackup: The time to set in the snar file
		@type timeofBackup: datetime
		"""
		self.__snapshotFile.setHeader(timeofBackup)
		
	def getContent(self, dirpath):
		"""convenance method to get the content of a directory.
		
		@param dirpath: The directory absolute path to get
		@type dirpath: str
		
		@return: The content of the dir
		@rtype: list
		
		@raise SBException: if the path isn't found in the snapshot file
		"""
		for f in self.__snapshotFile.parseFormat2():
#			if f[-2].rstrip(os.sep) == dirpath.rstrip(os.sep) :
			if f[SnapshotFile.REC_DIRNAME].rstrip(os.sep) == dirpath.rstrip(os.sep) :
				return f[SnapshotFile.REC_CONTENT]
		raise SBException(_("Non existing directory : %s") % dirpath)
			
	def getFirstItems(self):
		"""
		Get the first items in this SnapshotFile (the lower level dirs in the file)
		@return: A list of paths
		@rtype: list 
		"""
		
		def cleanDupl():
			if result:
				result.sort()
				last = result[-1]
				for i in range(len(result)-2, -1, -1):
					if last == result[i]:
						del result[i]
					else:
						last = result[i]
			
		result = list()
		
		for f in self.__snapshotFile.parseFormat2():
			found = False
			
			for i in range(0,len(result)) :
				if result[i] == f[-2] or f[-2].startswith(result[i]) : 
					if found :
						# then we are trying to overide
						continue
					else :
						found = True
						break
				elif result[i].startswith(f[-2]):
					# replace with f[-2]
					result[i] = f[-2]
					found = True
					# don't break cause it's possible that some others entries need to be overiden
			
			if not found :
				result.append(f[-2])
			else :
				cleanDupl()
		
		return result
	
