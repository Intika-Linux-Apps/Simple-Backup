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

# Imports
import nssbackup.managers.FileAccessManager as FAM
import re
import os
import subprocess
from tempfile import *
import cPickle as pickle
from exceptions import * 
from log import getLogger
from structs import SBdict
import nssbackup.util as Util

class Snapshot : 
	"The snapshot class represents one snapshot in the backup directory"
	# Attributes
	__name = False
	__base = False
	__excludes = False
	__filesList = None
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
		
	def getFilesList(self) :
		"Returns a SBdict with key='the file name' and value='the file properties'"
		global __filesList
		if self.getVersion() and self.getVersion() != "1.4" : raise SBException(_("Please upgrade the snapshot (version '%s' found)") % self.getVersion())
		if self.__filesList != None : return self.__filesList
		else :
			flist = self.__snapshotpath +os.sep +"flist"
			fprops = self.__snapshotpath +os.sep +"fprops"
			if not FAM.exists(flist) and not FAM.exists(fprops) : 
				return False
			elif not FAM.exists(flist) :
				raise NotValidSnapshotException(_("flist hasn't been found for snapshot '%s'") % self.getName())
			elif not FAM.exists(fprops) :
				raise NotValidSnapshotException(_("fprops hasn't been found for snapshot '%s'") % self.getName())
			else :
				f1 = FAM.readfile(flist)
				f2 = FAM.readfile(fprops)
				self.__filesList = SBdict(zip(f1.split( "\000" ),f2.split( "\000" )) )
				return self.__filesList
	
	def getPath(self) :
		"return the complete path of the snapshot"
		if not self.__snapshotpath : 
			raise SBException(_("Snapshot is inconsistant : __snapshotpath is not set "))
		else :
			return self.__snapshotpath
	
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
		@return: Snapshot
		"""
		global __baseSnapshot
		if self.__baseSnapshot : return self.__baseSnapshot
		else :
			path = os.path.dirname(self.getPath())
			self.__baseSnapshot = Snapshot( os.path.normpath(os.sep.join([path, self.getBase()])) )
			return self.__baseSnapshot
	
	
	def getFileProps(self, item) :
		"Returns for a certain item in the backup its properties"
		return self.getFilesList()[str(item)]
	
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
					major = int(ver[0])
					minor = int(ver[2])
				except Exception, e:
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
	
	def isfull(self):
		"""
		@return: True if the snapshot is full and false if inc
		"""
		return self.getName().endswith(".ful")
	
	def commit (self) :
		"Commit the snapshot infos ( write to the disk )"
		self.__commitbasefile()
		self.__commitexcludefile()
		self.__commitpackagefile()
		self.__commitflistfiles()
		self.__makebackup()
		self.__commitverfile()
	
	# Setters
	
	def setFilesList(self, fileslist=None) :
		"""
		Set a SBdictionary with key='the file name' and value='the file properties'
		@param fileslist: is the new filesList SBdict (default is an empty SBdict)
		ATTENTION : The snapshot fileList will be overwritten
		"""
		global __filesList
		if not fileslist :
			self.__filesList = SBdict()
			getLogger().debug(_("set filelist to empty SBdict : ")+ str(self.__filesList)) 
		else :
			self.__filesList = fileslist
	
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
	
	def addFile(self, item, props) :
		"""
		Add an item to be backup into the snapshot.
		 Usage :  addFile(item, props) where
		 - item is the item to be add (file, dir, or link)
		 - props is this item properties
		"""
		global __filesList
		if not self.getFilesList() :
			self.setFilesList()
		self.__filesList[item] = props
	
	def setVersion(self, ver="1.4") :
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
		if not FAM.exists( self.getPath()+os.sep +"flist" ) or not FAM.exists( self.getPath()+os.sep +"fprops" ) or not FAM.exists( self.getPath()+os.sep +"files.tgz" ) or not FAM.exists( self.getPath()+os.sep +"ver" ):
			raise NotValidSnapshotException (_("One of the mandatory files doesn't exist in [%s]") % self.getName())
		
	def __isValidName(self, name ) :
		" Check if the snapshot name is valid "
		return str(re.match(self.__validname_re , name )) != "None"

	def __commitverfile(self) :
		" Commit ver file on the disk "
		if not self.getVersion() :
			self.setVersion()
		FAM.writetofile(self.getPath()+os.sep +"ver", self.getVersion())
		
	def __commitbasefile(self):
		" Commit base file on the disk "
		if self.getBase() :
			if self.getName()[-3:] != "ful" :
				FAM.writetofile(self.getPath()+os.sep +"base", self.getBase())
		else : # base file was not found or base wasn't set. It MUST be a full backup
			if self.getName()[-3:] != "ful" :
				raise SBException(_("Base name must be set for inc backup !"))
		
	def __commitexcludefile(self):
		"""
		Commit exclude file on the disk.
		@raise SBException: if excludes hasn't been set 
		"""
		if not self.getExcludes() :
			raise SBException(_(" 'excludes' must be set !"))
		else :
			FAM.pickledump( self.__excludes, self.getPath()+os.sep +"excludes" )
		
	def __commitflistfiles(self):
		" Commit flist and fprops on the disk "
		if not self.getFilesList() :
			FAM.writetofile(self.getPath()+os.sep +"flist", "")
			FAM.writetofile(self.getPath()+os.sep +"fprops", "")
		else :
			fl, fp = "", ""
			for (fli, fpi ) in self.__filesList.iteritems() :
				if fli :
					fl += str(fli)+"\000"
					fp += str(fpi)+"\000"
			FAM.writetofile(self.getPath()+os.sep +"flist", fl)
			FAM.writetofile(self.getPath()+os.sep +"fprops", fp)
		
	
	def __commitpackagefile(self):
		" Commit packages file on the disk"
		if not self.getPackages() :
			FAM.writetofile(self.getPath()+os.sep +"packages", "")
		else :
			FAM.writetofile(self.getPath()+os.sep +"packages", self.getPackages())
		
	def __makebackup(self):
		" Make the backup on the disk "
		
		getLogger().info(_("Launching TAR to backup "))
		tdir = self.getPath().replace(" ", "\ ")
		options = list()
		options.extend(["-czS","--directory="+ os.sep , "--no-recursion", "--ignore-failed-read","--null","--files-from="+tdir+os.sep +"flist"])
		getLogger().debug(options)
		if FAM.islocal(self.getPath()) :
			options.extend(["--force-local", "--file="+tdir+os.sep +"files.tgz"])
			getLogger().debug("Tarline : " + "tar" + str(options))
			outStr, errStr, retVal = Util.launch("tar", options)
			getLogger().debug(outStr)
			if retVal != 0 :
				raise SBException(_("Couldn't make a proper backup : ") + errStr )
		else :
			getLogger().debug("Tarline : " + "tar" + options )
			turi = gnomevfs.URI( self.getPath()+os.sep +"files.tgz" )
			tardst = gnomevfs.create( turi, 2 )
			tarsrc = os.popen( "tar" + options )
			shutil.copyfileobj( tarsrc, tardst, 100*1024 )
			tarsrc.close()
			tardst.close()
			
