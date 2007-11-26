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
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum at gmail dot com>

# Imports
import nssbackup.managers.FileAccessManager as FAM
import re
import os
from gettext import gettext as _
from exceptions import NotValidSnapshotNameException,SBException, NotValidSnapshotException
from log import getLogger
from structs import SBdict
import nssbackup.util.tar as TAR
from nssbackup.util.tar import SnapshotFile, MemSnapshotFile, ProcSnapshotFile

class Snapshot : 
	"The snapshot class represents one snapshot in the backup directory"
	# Attributes
	__name = False
	__base = False
	__format = "gzip" # default value
	
	# TODO (in|ex)cludeFlist should be an SBdict
	__snarfile = None
	__includeFlist = SBdict()
	__includeFlistFile = None # Str
	__excludeFlist = SBdict()
	__excludeFlistFile = None # Str
	
	__splitedSize = 0
	__excludes = False
	
	__packages = False
	__version = False
	__snapshotpath = False
	
	__baseSnapshot = None
	
	__validname_re = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})[\:\.](\d{2})[\:\.](\d{2})\.\d+\..*?\.(.+)$")
	
	# Constructor
	def __init__ (self, path, fam=False) :
		"""
		The snapshot constructor.
		@param path : the path to the snapshot dir.
		@param fam : The File Access Manager to use. False will create a default one
		"""
		global __name, __snapshotpath
		
		self.__snapshotpath = os.path.normpath(str(path))
		
		self.__name = os.path.basename(self.__snapshotpath)
				
		# check if it's an existing snapshot
		if FAM.exists(self.__snapshotpath) :
			#snapshot exists
			self.__validateSnapshot(self.__snapshotpath, self.__name)
		else : # Snapshot for creation
			# validate the name
			if not self.__isValidName(self.__name) :
				raise NotValidSnapshotNameException (_("Name of Snapshot not valid : %s") % self.__name)
			FAM.makedir(self.__snapshotpath)
	
	def __str__(self):
		"Return the snapshot name"
		return self.getName()
	
	
	# Public Methods
	def getName(self) :
		" return the name of the snapshot (ie the dir name)"
		if not self.__name : 
			raise SBException(_("Snapshot is inconsistant : __name is not set "))
		else :
			return self.__name

	def getDate(self):
		"""
		You can get from the dictionary returned the following keys :
		year, month, day, hour, minute, second
		@return : a dictionary with the date time this snapshot has been taken.
		"""
		m = re.match(self.__validname_re , self.getName() )
		if not m : raise NotValidSnapshotNameException(_("Name of snapshot '%s' doesn't match requirement") % self.getName())
		date = {"year" : int(m.group(1)),"month":int(m.group(2)),"day":int(m.group(3)),
			"hour":int(m.group(4)),"minute":int(m.group(5)),"second":int(m.group(6))}
		return date
	# ---
	
	def getIncludeFlist(self):
		"""
		get the Include file list
		@rtype: list
		"""
		return self.__includeFlist
	
	def getExcludeFlist(self):
		"""
		get the Exclude file list
		@rtype: list
		"""
		return self.__excludeFlist
	
	def getExcludeFListFile(self):
		"""
		@return: the path to the exclude file list file
		"""
		global __excludeFlistFile
		
		if not self.__excludeFlistFile :
			self.__excludeFlistFile = self.getPath()+os.sep+"excludes.list"
			
		return self.__excludeFlistFile

	def getIncludeFListFile(self):
		"""
		@return: the path to the include file list file
		"""
		global __includeFlistFile
		
		if not self.__includeFlistFile :
			self.__includeFlistFile = self.getPath()+os.sep+"includes.list"
			
		return self.__includeFlistFile

	def getSnarFile(self):
		"""
		@return: the path to the TAR SNAR file
		"""
		global __snarfile
		
		if not self.__snarfile : 
			self.__snarfile = self.getPath()+os.sep+"files.snar"
		return self.__snarfile
	
	def getPath(self) :
		"return the complete path of the snapshot"
		if not self.__snapshotpath : 
			raise SBException(_("Snapshot is inconsistant : __snapshotpath is not set "))
		else :
			return self.__snapshotpath
	
	def getFormat(self):
		"""
		Returns the compression format of the snapshot (from the "format" file or default to "gzip")
		"""
		global __format
		if os.path.exists(os.sep.join([self.getPath(),"format"])):
			self.__format = FAM.readfile(os.sep.join([self.getPath(),"format"])).split('\n')[0]
		return self.__format
	
	def getBase(self) :
		"""
		return the name of the base snapshot of this snapshot if its an Inc backup
		return False if it's a full backup
		"""
		global __base
		if self.__base : return self.__base
		else :
			basefile = self.__snapshotpath +os.sep +"base"
			if not FAM.exists(basefile) : return False
			else :
				self.__base = FAM.readfile(basefile).strip()
				return self.__base
	
	def getBaseSnapshot(self):
		"""
		Return the base snapshot (as a Snapshot ) not only the name
		@return: the base Snapshot if it exists or None otherwise (we are a full snapshot) 
		"""
		global __baseSnapshot
		if self.__baseSnapshot : return self.__baseSnapshot
		else :
			# check if we are not a full snapshot 
			if self.getBase():
				path = os.path.dirname(self.getPath())
				self.__baseSnapshot = Snapshot( os.path.normpath(os.sep.join([path, self.getBase()])) )
			else :
				self.__baseSnapshot = None
			return self.__baseSnapshot
			
	
	def getArchive(self):
		"""
		Get the snapshot archive which depends on the Format
		@raise NonValidSnapshotException: if the archive equivalent to the described format doesn't exist
		@return: the path to the archive
		"""
		problem = False
		if self.getFormat() == "none" :
			if os.path.exists(self.getPath()+os.sep+"files.tar") :
				return self.getPath()+os.sep+"files.tar"
			else :
				problem = True
		elif self.getFormat() == "gzip" :
			if os.path.exists(self.getPath()+os.sep+"files.tar.gz") :
				return self.getPath()+os.sep+"files.tar.gz"
			elif self.getVersion() == "1.4":
				getLogger().warning("The tgz name is deprecated, please upgrade Snapshot to Version 1.5")
				if os.path.exists(self.getPath()+os.sep+"files.tgz") :
					return self.getPath()+os.sep+"files.tgz"
				else :
					problem = True
			else :
				problem = True
		elif self.getFormat() == "bzip2" :
			if os.path.exists(self.getPath()+os.sep+"files.tar.bz2") :
				return self.getPath()+os.sep+"files.tar.bz2"
			else :
				problem = True
		if problem : 
			raise NotValidSnapshotException(_("The snapshot compression format is supposed to be '%s' but the corresponding well named file wasn't found") % self.getFormat())
	
	def getVersion(self) :
		"Return the version of the snapshot comming from the 'ver' file"
		global __version
		
		if self.__version : return self.__version
		elif ":" in self.getName() : 
			self.__version = "1.0"
			return self.__version
		else :
			verfile = self.getPath() +os.sep +"ver"
			if not FAM.exists(verfile) : return False
			else :
				ver = FAM.readfile(verfile)
				try : 
					# major = 
					int(ver[0])
					# minor = 
					int(ver[2])
				except Exception:
					FAM.delete(self.getPath()+os.sep +"ver")
					raise SBException (_("%(file)s doesn't contain valid value ! Ignoring incomplete or non-backup directory. ") % {"file" : self.getPath()+ os.sep +"ver"})
				self.__version = ver[:3]
				return self.__version
	
	def getExcludes(self) :
		"Return the content of excludes"
		global __excludes
		if self.__excludes : return self.__excludes
		else :
			excludefile = self.getPath() +os.sep +"excludes"
			if not FAM.exists(excludefile) : return False
			else :
				self.__excludes = FAM.pickleload(excludefile)
				return self.__excludes
	
		
	def getPackages(self) :
		"Return the packages"
		global __packages
		if self.__packages : return self.__packages
		else :
			packagesfile = self.getPath() +os.sep +"packages"
			if not FAM.exists(packagesfile) : return False
			else :
				self.__packages = FAM.readfile(packagesfile)
				return self.__packages
	
	def getSnapshotFileInfos(self,useMem=False,writeFlag=False):
		"""
		@param useMem: use or not the memory to store infos about the SNAR file
		@type useMem: boolean
		@param writeFlag: Will be passed to the SnapshotFile to permit writing
		@type writeFlag: boolean
		@return: the corresponding SnapshotFile (Mem ou Proc), the only method usable afterward is getContent(path) 
		"""
		snpfile = SnapshotFile(self.getSnarFile(),writeFlag)
		
		snpfileInfo = None
		
		if useMem :
			snpfileInfo = MemSnapshotFile(snpfile)
		else :
			snpfileInfo = ProcSnapshotFile(snpfile)
		
		return snpfileInfo
	
		
	def getSplitedSize(self):
		"""
		@return: the size of each archive in the snapshot (0 means unlimited )
		"""
		if os.path.exists(os.sep.join([self.getPath(),"format"])):
			self.__splitedSize = int(FAM.readfile(os.sep.join([self.getPath(),"format"])).split('\n')[1])
		return self.__splitedSize
	
	def isfull(self):
		"""
		@return: True if the snapshot is full and false if inc
		"""
		return self.getName().endswith(".ful")

	
	def commit (self) :
		"Commit the snapshot infos ( write to the disk )"
		self.commitbasefile()
		self.commitFormatfile()
		self.commitexcludefile()
		self.commitpackagefile()
		self.commitflistFiles()
		self.__makebackup()
		self.__clean()
		self.commitverfile()
	
	
	#----------------------------
	
	def addToIncludeFlist (self, item) :
		"""
		Add an item to be backup into the snapshot.
		Usage :  addToIncludeFlist(item) where
		- item is the item to be add (file, dir, or link)
		"""
		global __includeFlist
		
		self.__includeFlist[item] = "1"
	
	def addToExcludeFlist (self, item) :
		"""
		Add an item to not be backup into the snapshot.
		Usage :  addToExcludeFlist(item) where
		- item is the item to be add (file, dir, or link)
		"""
		global __excludeFlist
		
		self.__excludeFlist[item] = "0"
	
	#---------------------------------
	
	# Setters
	
	def setFormat(self,cformat=None):
		"""
		Sets the backup compression format
		cformat : the format to set
		"""
		global __format
		supported = ["none","bzip2", "gzip"]
		if cformat and cformat in supported :
			getLogger().debug("Set the compression format to %s" % cformat)
			self.__format = cformat
	
	
	def setPath(self, path) :
		"Set the complete path of the snapshot. That path will be used to get the name of the snapshot"
		global __snapshotpath, __name
		self.__snapshotpath = path
		splited = str(self.__snapshotpath).split(os.sep)
		name = splited[len(splited) - 1]
		if not self.__isValidName(name) :
			raise SBException (_("Name of Snapshot not valid : %s") % self.__name)
		else : 
			self.__name = name
		
	
	def setBase(self, baseName) :
		"Set the name of the base snapshot of this snapshot"
		global __base
		if not self.__isValidName(baseName) :
			raise SBException (_("Name of base not valid : %s") % self.__name)
		self.__base = baseName		
	
	
	def setVersion(self, ver="1.5") :
		"Set the version of the snapshot"
		self.__version = ver
	
	def setExcludes(self, excludes) :
		"Set the content of excludes"
		self.__excludes = excludes
	
	def setPackages(self, packages="") :
		"""
		set the packages list for debian based distros
		@param packages: Must be the results of the 'dpkg --get-selections' command . default = '' 
		"""
		global __packages
		self.__packages = packages
	
	def setSplitedSize(self, size):
		"""
		@param size: The size in KB to set
		"""
		global __splitedSize
		if type(size) != int :
			raise SBException("The size parameter must be an integer")
		self.__splitedSize = size
	
	
	# Private
	def __validateSnapshot(self,path, name):
		"""
		Validate the snapshot
		@param path : the snapshot path
		@param name : the snapshot name 
		"""
		# validate the name
		if not self.__isValidName(self.__name) :
			raise NotValidSnapshotNameException (_("Name of Snapshot not valid : %s") % self.__name)
		if  not FAM.exists( self.getPath()+os.sep +"ver" ):
			raise NotValidSnapshotException (_("The mandatory 'ver' file doesn't exist in [%s]") % self.getName())
		
	def isValidName(self, name ) :
		" Check if the snapshot name is valid "
		return str(re.match(self.__validname_re , name )) != "None"

	def commitFormatfile(self):
		"""
		writes the format file
		"""
		formatInfos = self.getFormat()+"\n"
		formatInfos += str(self.getSplitedSize())
		
		FAM.writetofile(self.getPath()+os.sep+"format", formatInfos)

	def commitverfile(self) :
		" Commit ver file on the disk "
		if not self.getVersion() :
			self.setVersion()
		FAM.writetofile(self.getPath()+os.sep +"ver", self.getVersion())
		
	def commitbasefile(self):
		" Commit base file on the disk "
		if self.getBase() :
			if self.getName()[-3:] != "ful" :
				FAM.writetofile(self.getPath()+os.sep +"base", self.getBase())
		else : # base file was not found or base wasn't set. It MUST be a full backup
			if self.getName()[-3:] != "ful" :
				raise SBException(_("Base name must be set for inc backup !"))
		
	def commitexcludefile(self):
		"""
		Commit exclude file on the disk.
		@raise SBException: if excludes hasn't been set 
		"""
		FAM.pickledump( self.__excludes, self.getPath()+os.sep +"excludes" )
	
	
	def commitflistFiles(self):
		"""
		Commit the include.list and exclude.list to the disk
		"""
		if os.path.exists(self.getIncludeFListFile()) or os.path.exists(self.getIncludeFListFile()) :
			raise SBException("includes.list and excludes.list shouldn't exist at this stage")
		
		# commit include.list.tmp
		fi = open(self.getIncludeFListFile()+".tmp","w")
		for f in self.__includeFlist.getEffectiveFileListForTAR() :
			fi.write(str(f) +"\n")
		fi.close()
		
		# commit include.list
		fi = open(self.getIncludeFListFile(),"w")
		for f in self.__includeFlist.getEffectiveFileList() :
			fi.write(str(f) +"\n")
		fi.close()
		
		# commit exclude.list
		fe = open(self.getExcludeFListFile(),"w")
		for f in self.__excludeFlist.getEffectiveFileList() :
			fe.write(str(f) +"\n")
		fe.close()
		
		
	def commitpackagefile(self):
		" Commit packages file on the disk"
		if not self.getPackages() :
			FAM.writetofile(self.getPath()+os.sep +"packages", "")
		else :
			FAM.writetofile(self.getPath()+os.sep +"packages", self.getPackages())
		
	def __makebackup(self):
		" Make the backup on the disk "
		
		if self.isfull() :
			TAR.makeTarFullBackup(self)
		else :
			TAR.makeTarIncBackup(self)

	def __clean(self):
		"""
		Clean operational temporary files
		"""
		# 
		if os.path.exists(self.getIncludeFListFile()+".tmp") :
			os.remove(self.getIncludeFListFile()+".tmp")