import os,re,tarfile, csv
from nssbackup.util.log import getLogger
import nssbackup.util as Util
from nssbackup.util.exceptions import SBException

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
	
	
def extract(sourcetgz, file, dest , bckupsuffix = None):
	"""
	Extract from source tar.gz the file "file" to dest.
	@param source:
	@param file:
	@param dest:
	"""
	# strip leading sep
	file = file.lstrip(os.sep)
	
	options = ["-xp", "--occurrence=1", "--ignore-failed-read", '--backup=existing']
	
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
	options.extend(['--file='+sourcetgz,file])
	
	outStr, errStr, retval = Util.launch("tar", options)
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
	
	options.extend(['--file='+sourcetgz,'--null','--files-from='+os.path.normpath(fileslist)])
	
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)


class Dumpdir():
	"""
	Dumpdir is a sequence of entries of the following form:
 		C filename \0
	where C is one of the control codes described below, filename is the name of the file C operates upon, and '\0' represents a nul character (ASCII 0). The white space characters were added for readability, real dumpdirs do not contain them.
	Each dumpdir ends with a single nul character. 
	
	@see: http://www.gnu.org/software/tar/manual/html_chapter/tar_13.html#SEC171
	"""
	
	control = None
	filename = None
	nul = '\0'
	
	def __init__(self, line):
		"""
		Constructor that takes a line to create a Dumpdir.
		we will parse this line and fill the Dumpdir in
		@param line: the line (in dumpdir point of view ) to parse
		@raise Exception: when the line doesn't have the requeried format
		"""
		
		if (not isinstance(line,str)) :
			raise Exception("Line must be a string")
		
		if line[-1] is not self.nul:
			raise Exception("Incorrect format of line : Last character must be '\\0'(NUL) ")
		
		self.control = line[0]
		self.filename = line[1:-1]

	def getFilename(self):
		"""
		get the filename embedded in the Dumpdir
		@return: finename
		@raise Exception: if the filename is null 
		"""
		if self.filename :
			return self.filename
		else :
			raise Exception("Dumpdir inconsistancy : filename is empty")
		
	def getControl(self):
		"""
		Get the control charactere from the DumpDir
		@return: control
		@raise Exception: if the control is null 
		"""
		if self.control :
			return self.control
		else :
			raise Exception("Dumpdir inconsistancy : 'control' is empty")
		
class SnapshotFile():
	"""
	
	@see: http://www.gnu.org/software/tar/manual/html_chapter/tar_13.html#SEC170
	"""
	header = None
	snpfile = None
	version = None
	versionRE = re.compile("GNU tar-(.+?)-([0-9]+?)")

	def __init__(self, filename):
		"""
		Constructor 
		@param filename: the snapshot file absolute file path to get the infos
		"""
		if os.path.exists(filename) :
			self.snpfile = os.path.abspath(filename)
		else :
			raise Exception ("'%s' doesn't exist "% filename)

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
		
		return self.version
		
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
		@return: [nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents] where contents is Dumpdirs
		"""
		
		def format(line):
			"""
			subroutine to format a line including NUL char to have and array
			"""
			nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents = line.lstrip("\0").split("\0",6)
			return (nfs,mtime_sec,mtime_nano,dev_no,i_no,name,contents)
			
			
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
		
		fd.close()
	 	