#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
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


import os,re,shutil
from gettext import gettext as _
from nssbackup.util.log import getLogger
import nssbackup.util as Util
from nssbackup.util.structs import SBdict
from nssbackup.util.exceptions import SBException
from datetime import datetime
import time

def getArchiveType(archive):
	"""
	return the type of an archive 
	@param archive: 
	@return: tar, gzip, bzip2 or None
	"""
	command = "file"
	opts = ["--mime","-b",archive]
	out, err, retVal = Util.launch(command, opts)
	if "x-bzip2" in out :
		return "bzip2"
	elif "x-gzip" in out :
		return "gzip"
	elif "x-tar" in out :
		return "tar"
	else :
		return None
	
	
def extract(sourcetgz, file, dest , bckupsuffix = None, splitsize=None):
	"""
	Extract from source tar.gz the file "file" to dest.
	@param source:
	@param file:
	@param dest:
	@param bckupsuffix: If set a backup suffix option is set to backup existing files
	@param splitsize: If set the split options are added supposing the size of the archives is this variable
	@type splitsize: Integer in KB
	"""
	# strip leading sep
	file = file.lstrip(os.sep)
	
	options = ["-xp", "--ignore-failed-read", '--backup=existing']
	
	archType = getArchiveType(sourcetgz)
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
	
	options.extend(['--file='+sourcetgz,file])
	
	getLogger().debug("Launching TAR with options : %s" % options)
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)
	
def extract2(sourcetgz, fileslist, dest, bckupsuffix = None,additionalOps=None ):
	"""
	Extract the files listed in the 'fileslist' file to dest. This method 
	has been created to optimize the time spent by giving to tar a complete 
	list of file to extract. Use this if ever you have to extract more than 1 dir .
	@param sourcetgz:
	@param fileslist: a path to the file containing the list
	@param dest: destination
	@param bckupsuffix: 
	@param additionalOpts: a list of aption to add
	"""
	options = ["-xp", "--ignore-failed-read", '--backup=existing']
	
	archType = getArchiveType(sourcetgz)
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
	
	if additionalOps and type(additionalOps) == list :
		options.extend(additionalOps)
		
	options.extend(['--file='+sourcetgz,'--null','--files-from='+os.path.normpath(fileslist)])
	
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)

def appendToTarFile(desttar, fileOrDir, workingdir=None,additionalOps=None ):
	"""
	@param desttar: The tar file to wich append
	@param fileOrDir: The file or directory to append
	@param workingDir: the dir to move in before appending the dir ( usefun for relative paths)
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
		
	if additionalOps and type(additionalOps) == list :
		options.extend(additionalOps)
		
	options.extend(['--file='+desttar,'--null'])
	
	if workingdir:
		options.append("-C "+workingdir)
	
	options.append(fileOrDir)
	
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)

def appendToTarFile2(desttar, fileslist, additionalOps=None ):
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
		
	if additionalOps and type(additionalOps) == list :
		options.extend(additionalOps)
		
	options.extend(['--file='+desttar,'--null','--files-from='+os.path.normpath(fileslist)])
	
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)


def __prepareTarCommonOpts(snapshot):
	"""
	Prepare the options to fill tar in .
	@param snapshot: The snapshot to fill in
	@return: a list of options to be use to launch tar
	"""
	tdir = snapshot.getPath().replace(" ", "\ ")
	options = list()
	
	options.extend(["-cS","--directory="+ os.sep , "--ignore-failed-read","--files-from="+snapshot.getIncludeFListFile().replace(" ", "\ ")+".tmp"])
	options.append ("--exclude-from="+snapshot.getExcludeFListFile().replace(" ", "\ "))
	
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
		getLogger().debug("Defaulting to gzip ! ")
		options.insert(1,"--gzip")
		archivename+=".gz"
	
	options.append("--file="+tdir+os.sep +archivename)
	
	getLogger().debug(options)
	
	getLogger().debug("Common TAR options : " + str(options))
	
	return options 
	
def __addSplitOpts(snapshot, options, size):
	"""
	Compiles and add the split management options to the TAR line.
	Valid for read and create actions
	@param snapshot: The snapshot to process
	@type snapshot: Snapshot
	@param options: the option in which to append
	@type options: list
	@param size: the size of each part (in KB)
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
	getLogger().info(_("Launching TAR to make Inc backup "))
	
	options = __prepareTarCommonOpts(snapshot)
	
	splitSize = snapshot.getSplitedSize()
	if splitSize :
		options = __addSplitOpts(snapshot, options, splitSize)
	
	# For an INC backup the base SNAR file should exists
	if not os.path.exists(snapshot.getBaseSnapshot().getSnarFile()) :
		getLogger().error(_("Unable to find the SNAR file to make an Incremental backup"))
		getLogger().error(_("Falling back to full backup"))
		makeTarFullBackup(snapshot)
	else:
		shutil.copy(snapshot.getBaseSnapshot().getSnarFile(), snapshot.getSnarFile())
		options.append("--listed-incremental="+snapshot.getSnarFile())
		
		outStr, errStr, retVal = Util.launch("tar", options)
		getLogger().debug("TAR Output : " + outStr)
		if retVal != 0 :
			# list-incremental is not compatible with ignore failed read
			getLogger().error(_("Couldn't make a proper backup, finishing backup though :") + errStr )
		

def makeTarFullBackup(snapshot):
	"""
	Launch a TAR full backup
	@param snapshot: the snapshot in which to make the backup
	@raise SBException: if there was a problem with tar
	"""
	getLogger().info(_("Launching TAR to make a Full backup "))
	
	options = __prepareTarCommonOpts(snapshot)
	
	splitSize = snapshot.getSplitedSize()
	if splitSize :
		options = __addSplitOpts(snapshot, options, splitSize)
	
	# For a full backup the SNAR file shouldn't exists
	if os.path.exists(snapshot.getSnarFile()) :
		os.remove(snapshot.getSnarFile())
	
	options.append("--listed-incremental="+snapshot.getSnarFile())
	
	outStr, errStr, retVal = Util.launch("tar", options)
	getLogger().debug("TAR Output : " + outStr)
	if retVal != 0 :
		# list-incremental is not compatible with ignore failed read
		getLogger().error(_("Couldn't make a proper backup, finishing backup though : ") + errStr )
	
# ---

class Dumpdir():
	"""
	Dumpdir is a sequence of entries of the following form:
		C filename \0
	where C is one of the control codes described below, filename is the name of the file C operates upon, and '\0' represents a nul character (ASCII 0). The white space characters were added for readability, real dumpdirs do not contain them.
	Each dumpdir ends with a single nul character. 
	
	@see: http://www.gnu.org/software/tar/manual/html_chapter/tar_13.html#SEC171
	"""
	
	INCLUDED = 'Y'
	UNCHANGED = 'N'
	DIRECTORY = 'D'
	
	__HRCtrls = {'Y':_('Included'),'N':_('Unchanged'),'D':_('Directory')} #: The dictionary mapping control with their meanings
	
	control = None
	filename = None
	
	def __init__(self, line):
		"""
		Constructor that takes a line to create a Dumpdir.
		we will parse this line and fill the Dumpdir in
		@param line: the line (in dumpdir point of view ) to parse
		@raise Exception: when the line doesn't have the requeried format
		"""
		if not line :
			self = None
			return
		
		if (not isinstance(line,str)) :
			raise Exception(_("Line must be a string"))
		
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
			raise Exception(_("Dumpdir inconsistancy : 'filename' is empty"))
		
	def getControl(self):
		"""
		Get the control character from the DumpDir
		@return: control
		@raise Exception: if the control is null 
		"""
		if self.control :
			return self.control
		else :
			raise Exception(_("Dumpdir inconsistancy : 'control' is empty"))
	
	def getHumanReadableControl(self):
		"""
		Get the control character as a Human readable string from the DumpDir
		"""
		return self.__HRCtrls[self.getControl()]
	
	def __str__(self):
		return self.filename + " " +self.getHumanReadableControl() 
	
	@classmethod
	def getHRCtrls(Dumpdir):
		"""
		@return: The Human Readable control dictionary
		@rtype: dict
		"""
		return Dumpdir.__HRCtrls
	
# ---

class SnapshotFile():
	"""
	
	@see: http://www.gnu.org/software/tar/manual/html_chapter/tar_13.html#SEC170
	"""
	header = None
	snpfile = None
	version = None
	versionRE = re.compile("GNU tar-(.+?)-([0-9]+?)")
	
	__SEP = '\000'
	__entrySEP = 2*__SEP
	
	# Infos on indices in a record 
	REC_NFS = 0
	REC_MTIME_SEC =1
	REC_MTIME_NANO=2
	REC_DEV_NO=3
	REC_INO=4
	REC_DIRNAME=5
	REC_CONTENT=6
	
	
	def __init__(self, filename,writeFlag=False):
		"""
		Constructor 
		@param filename: the snapshot file absolute file path to get the infos (SNAR file)
		"""
		if os.path.exists(filename) :
			self.snpfile = os.path.abspath(filename)
		else :
			if writeFlag :
				self.snpfile = os.path.abspath(filename)
				fd = open(self.snpfile,'a+')
				fd.close()
			else :
				raise Exception (_("'%s' doesn't exist ") % filename)

	def getFormatVersion(self):
		"""
		Get the format version
		@return: the version 
		@rtype: int 
		"""
		global header, version
		
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
		
		for line in fd.readlines() :
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
		"""
		Iterator method that gives each line entry
		@warning: only compatible tar version 2 of Tar format
		@return: [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a list of Dumpdirs
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
			return (nfs,mtime_sec,mtime_nano,dev_no,i_no,name,formatDumpDirs(contents))
			
			
		fd = open(self.snpfile)
		# skip header which is the first line and 2 entries separated with NULL in this case
		fd.readline()
		
		n = 0
		
		while n < 2 :
			c = fd.read(1)
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

	# ---
	
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
		
	def addRecord(self,record):
		"""
		Write a record in the snar file. A record is a tuple with 6 entries + a content that is a dict
		@param record: A tuple that contains the record to add. [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a dict of {file:'control'}
		"""
		woContent,contents = record[:-1],record[-1]
		# compute contents
		strContent = self.createContent(contents)
		toAdd = self.__SEP.join(woContent)+self.__SEP+strContent
		
		fd = open(self.snpfile,'a+')
		fd.write(toAdd + self.__entrySEP)
		fd.close()
		
		
	def createContent(self,contentDict):
		"""
		create a content out of a dict of {file:'control'}
		@param contentDict: the content dictionary
		@type contentDict: dict
		@return: a string containing the computed content
		@rtype: string
		"""
		if type(contentDict) != dict :
			raise SBException("contentDict must be a dictionary")
		
		result = ""
		
		for f,c in contentDict.iteritems():
			result += c+f+self.__SEP
		
		return result
		
		
# ----

class MemSnapshotFile(SBdict):
	"""
	This is a representation in memory of a simplified SNAR file. The used structure is an SBDict.
	The "prop" value is the content of the directory. wich is a list of L{Dumpdir}
	"""
	
	__snapshotFile = None
	
	def __init__(self,snapshotFile):
		"""
		load the snapshotFile in memory
		@param snapshotFile: a SnapshotFile to convert in MemSnapshotFile
		@type snapshotFile: nssbackup.util.tar.SnapshotFile
		"""
		if not isinstance(snapshotFile, SnapshotFile) :
			raise Exception("A SnapshotFile is required")
		
		self.__snapshotFile = snapshotFile
		
		for f in snapshotFile.parseFormat2():
			self[f[-2]] = f[-1]
		
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
		
		
class ProcSnapshotFile :
	"""
	This is a Snapshotfile that will basically every time parse the snarfile for information
	"""
	
	__snapshotFile = None
	
	def __init__(self,snapshotFile):
		"""
		load the snapshotFile to get a reference on it
		@param snapshotFile: a SnapshotFile to convert in MemSnapshotFile
		@type snapshotFile: nssbackup.util.tar.SnapshotFile
		"""
		if not isinstance(snapshotFile, SnapshotFile) :
			raise Exception(_("A SnapshotFile is required"))
		
		self.__snapshotFile = snapshotFile
		
	def hasPath(self,path):
		"""
		Checks if a path is included in the SNAR file
		@param path: The path to check
		@return: True if the file is included, False otherwise
		@rtype: boolean
		"""
		for f in self.__snapshotFile.parseFormat2():
			if f[-2].rstrip(os.sep) == path.rstrip(os.sep) :
				return True
		return False
	
	def hasFile(self,_file):
		"""
		Checks if a file is included in the SNAR file. a file is in a directory thus in the content.
		@param _file: The file to check. a complete path must be given
		@return: True if the file is included, False otherwise
		@rtype: boolean
		"""
		dir,inFile = _file.rsplit(os.sep,1)
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
		"""
		Iter snar file records (wrapper on the parseFormat2 method of SnaspshotFile
		"""
		for record in self.__snapshotFile.parseFormat2():
			yield record
	
	
	def addRecord(self,record):
		"""
		Write a record in the snar file. A record is a tuple with 6 entries + a content that is a dict
		@param record: A tuple that contains the record to add. [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is a dict of {file:'control'}
		"""
		self.__snapshotFile.addRecord(record)
	
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
		@raise SBException: if the path isn't found in the snapshot file
		"""
		for f in self.__snapshotFile.parseFormat2():
			if f[-2].rstrip(os.sep) == dirpath.rstrip(os.sep) :
				return f[-1]
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
	
