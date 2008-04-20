
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
#	Aigars Mahinovs <aigarius@debian.org>
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>

# IMPORTS #
import FileAccessManager as FAM
import nssbackup.util as Util
from SnapshotManager import SnapshotManager
from nssbackup.util.log import LogFactory
from nssbackup.util.exceptions import SBException
from nssbackup.util.Snapshot import Snapshot
from gettext import gettext as _
import cPickle as pickle
from nssbackup.util.tar import Dumpdir
from nssbackup.util.structs import SBdict
import datetime, time
import os
from stat import *

# ------------------ #

class UpgradeManager() :
	"""
	The UpgradeManager class
	"""
	
	
	__possibleVersion = ["1.0","1.1","1.2","1.3","1.4","1.5"]

	statusMessage = None
	substatusMessage = None
	statusNumber = None

	def __init__(self):
		"""
		"""
		self.logger = LogFactory.getLogger()
		
	def getStatus(self):
		"""
		@return: [statusNumber,statusMessage,substatusMessage]
		"""
		return [self.statusNumber,self.statusMessage,self.substatusMessage]

	def upgradeSnapshot(self, snapshot,version="1.5"):
		"""
		Upgrade a snapshot to a version. Default is the higher version available
		@param snapshot: the snapshot to upgrade
		@param version : default is 1.5
		"""
		
		if version not in self.__possibleVersion :
			raise SBException("Version should be in '%s' , got '%s' " % (str(self.__possibleVersion),str(version) ) )
		else :
			if snapshot.getVersion() >= version  :
				self.logger.debug("Nothing to do : version of snapshot is already higher than given version (%s >= %s )" %(snapshot.getVersion() ,version))
				return
			else :
				self.logger.info("Upgrading snapshot '%s' to version '%s'" % (str(snapshot),str(version)) )
				while snapshot.getVersion() < version :
					if snapshot.getVersion() < "1.2" :
						if ":" in snapshot.getName():
							newname = snapshot.getName().replace( ":", "." )
							self.logger.info("Renaming directory: '"+snapshot.getName()+"' to '"+newname+"'" )
							FAM.rename(snapshot.getPath(), newname )
							snapshot = Snapshot( os.path.dirname(snapshot.getPath()) + os.sep + newname)
						self.__upgrade_v12(snapshot)
					elif snapshot.getVersion() < "1.3" :
						self.__upgrade_v13(snapshot)
					elif snapshot.getVersion() < "1.4" :
						self.__upgrade_v14(snapshot)
					elif snapshot.getVersion() < "1.5" :
						self.__upgrade_v15(snapshot)
				self.statusMessage = None
				self.substatusMessage = None
				self.statusNumber = None
	
	##
	#The downgrade feature will be certainly used for exporting snapshots, 
	#so that it would be possible to use it with a previous version of nssbackup
	# @param snapshot : the snapshot to downgrade : 
	# @param version : The version to which one the snapshot will be downgraded
	def downgradeSnapshot(self,snapshot,version="1.5"):
		self.logger.info("Downgrading snapshot '%s' to version '%s'" % (str(snapshot),str(version)) )
		if version not in self.__possibleVersion :
			raise SBException("Version should be in '%s' , got '%s' " % (str(self.__possibleVersion),str(version) ) )
		else :
			if snapshot.getVersion() <= version  :
				self.logger.info("Nothing to do : version of snapshot is already higher than given version (%s <= %s )" %(snapshot.getVersion() ,version))
			while snapshot.getVersion() > version :
					if snapshot.getVersion() > "1.4" :
						self.__downgrade_v14(snapshot)
					elif snapshot.getVersion() > "1.3" :
						self.__downgrade_v13(snapshot)
					elif snapshot.getVersion() > "1.2" :
						self.__downgrade_v12(snapshot)
					else : 
						raise SBException("Downgrade to version '%s' isn't supported " % str(version))
			
	
	##
	#Upgrade all valid snapshot in a certain directory 
	#@param target: The directory containing the snapshots		
	def upgradeAll( self, target ):
		self.logger.info("Upgrading All valid snapshot in '%s'" % target)
		snapman = SnapshotManager(target)
		snapshots= snapman.getSnapshots()
		for s in snapshots :
			if s.getVersion() < "1.5" :
				self.upgradeSnapshot(s)
	
	
	def __upgrade_v12( self, snapshot ):
		self.statusMessage = _("Upgrading from v1.0 to v1.2: %s")  % str(snapshot)
		self.logger.info(self.statusMessage)
		i = FAM.openfile(snapshot.getPath()+os.sep +"tree")
		bfiles = pickle.load( i )
		n = FAM.openfile( snapshot.getPath()+os.sep +"flist", True )
		p = FAM.openfile( snapshot.getPath()+os.sep +"fprops", True )
		for item in bfiles:
			n.write( str(item[0])+"\n" )
			p.write( str(item[1])+str(item[2])+str(item[3])+str(item[4])+str(item[5])+"\n" )
		p.close()
		n.close()
		i.close()
		FAM.writetofile( snapshot.getPath()+os.sep +"ver", "1.2\n" )
		snapshot.setVersion("1.2")
		self.statusNumber = 0.40
		
			
	def __upgrade_v13( self, snapshot ):
		self.statusMessage = _("Upgrading to v1.3: %s")  % str(snapshot) 
		self.logger.info(self.statusMessage)
		flist = FAM.readfile( snapshot.getPath()+os.sep +"flist" ).split( "\n" )
		fprops = FAM.readfile( snapshot.getPath()+os.sep +"fprops" ).split( "\n" )
		if len(flist)==len(fprops) :
			if len(flist) > 1:
				l = FAM.openfile(snapshot.getPath()+os.sep +"flist.v13", True)
				p = FAM.openfile(snapshot.getPath()+os.sep +"fprops.v13", True)
				for a,b in zip(flist,fprops):
					l.write( a+"\000" )
					p.write( b+"\000" )
				l.close()
				p.close()
				FAM.rename(snapshot.getPath()+os.sep +"flist", "flist.old")
				FAM.rename(snapshot.getPath()+os.sep +"flist.v13", "flist")
				FAM.rename(snapshot.getPath()+os.sep +"fprops", "fprops.old")
				FAM.rename(snapshot.getPath()+os.sep +"fprops.v13", "fprops")
				FAM.writetofile( snapshot.getPath()+os.sep +"ver", "1.3\n" )
				snapshot.setVersion("1.3")
		else:
			FAM.delete(snapshot.getPath()+os.sep +"ver")
			raise SBException ("Damaged backup metainfo - disabling %s" % snapshot.getPath() )
		self.statusNumber = 0.60

	def __upgrade_v14( self, snapshot ):
		self.statusMessage = _("Upgrading to v1.4: %s") % str(snapshot)
		self.logger.info(self.statusMessage )
		FAM.delete( snapshot.getPath() + os.sep +"ver" )
		
		if not FAM.exists( snapshot.getPath()+os.sep +"flist" ) or not FAM.exists( snapshot.getPath()+os.sep +"fprops" ) or not FAM.exists( snapshot.getPath()+os.sep +"files.tgz" ) or not FAM.exists( snapshot.getPath()+os.sep +"excludes" ):
			raise SBException ("Non complete Snapshot ! One of the essential files doesn't exist" )
		FAM.writetofile( snapshot.getPath()+os.sep +"ver", "1.4\n" )
		snapshot.setVersion("1.4")
		self.statusNumber = 0.80
		
	def __upgrade_v15( self, snapshot ):
		self.statusMessage = _("Upgrading to v1.5: %s") % str(snapshot) 
		self.statusNumber = 0.80
		self.logger.info(self.statusMessage)
		FAM.delete( snapshot.getPath() + os.sep +"ver" )
		
		if not FAM.exists( snapshot.getPath()+os.sep +"flist" ) or not FAM.exists( snapshot.getPath()+os.sep +"fprops" ) or not FAM.exists( snapshot.getPath()+os.sep +"files.tgz" ) or not FAM.exists( snapshot.getPath()+os.sep +"excludes" ):
			raise SBException ("Non complete Snapshot ! One of the essential files doesn't exist" )
		
		self.logger.info("renaming file.tgz to file.tar.gz")
		os.rename(snapshot.getPath()+os.sep +"files.tgz", snapshot.getPath()+os.sep +"files.tar.gz") 
		self.statusNumber = 0.82
		#TODO:
		self.logger.info("Creating includes.list")
		flist = snapshot.getPath()+os.sep +"flist" 
		fprops = snapshot.getPath()+os.sep +"fprops" 
		
		f1 = open(flist,'r')
		f2 = open(fprops,'r')
		
		isEmpty = True
		
		for f,p in Util.readlineNULSep(f1,f2):
			if f :
				if p is not None and p != str(None) :
					if isEmpty:
						isEmpty = False
					snapshot.addToIncludeFlist(f)
		# commit include.list
		fi = open(snapshot.getIncludeFListFile(),"w")
		for f in snapshot.getIncludeFlist().getEffectiveFileList() :
			fi.write(str(f) +"\n")
		fi.close()
		
		self.statusNumber = 0.85
		self.logger.info("Creating empty excludes.list")
		f1 = open(snapshot.getExcludeFListFile(),'w')
		f1.close()
		
		self.statusNumber = 0.87
		self.logger.info("creating 'format' file .")
		formatInfos = snapshot.getFormat()+"\n"
		formatInfos += str(snapshot.getSplitedSize())
		FAM.writetofile(snapshot.getPath()+os.sep +"format", formatInfos)
		
		self.statusNumber = 0.90
		self.logger.info("Creating the SNAR file ")
		if os.path.exists(snapshot.getSnarFile()) :
			self.logger.warning(_("The SNAR file alredy exist for snapshot '%s', I'll not overide it") % str(snapshot))
		else :
			snarfileinfo = snapshot.getSnapshotFileInfos(writeFlag=True)
			if not isEmpty :
				date = snapshot.getDate()
				datet = datetime.datetime(date['year'],date['month'],date['day'],date['hour'],date['minute'],date['second'])
				snarfileinfo.setHeader(datet)
							
				#header created, let's now add the directories from includes.list
				last_parentdir=None
				for f in snapshot.getIncludeFlist().getEffectiveFileList() :
					if f :
						
						parentdir = os.path.dirname(f)
						if parentdir == last_parentdir :
							self.logger.debug("[LastParentDir] already processed '%s'" % parentdir)
							continue
						last_parentdir = parentdir
						
						
						_time = str(int(time.mktime(datet.timetuple())))
						result = ["0", _time, _time]
						
						if snarfileinfo.hasPath(parentdir) :
							self.logger.debug("[SNARFileInfo] already processed '%s'" % parentdir)
							continue
						
						self.logger.debug("processing '%s'" % parentdir)
						
						if os.path.exists(parentdir) :
							result.append(str(os.stat(parentdir)[ST_DEV]))
							result.append(str(os.stat(parentdir)[ST_INO]))
						else :
							result.extend(['0','0'])
						
						result.append(parentdir)
						
						fname = os.path.basename(f)
						dumpdirs = list()
						
						#get the parent dir content
						cSBdict = snapshot.getIncludeFlist().getSon(parentdir)
						for k,v in dict.iteritems(cSBdict):
							# determine if it's a dir or a file
							if os.path.exists(parentdir+os.sep+k) :
								if os.path.isdir(parentdir+os.sep+k) :
									control = Dumpdir.DIRECTORY
								else :
									control = Dumpdir.INCLUDED
							else :
								if v and type(v) is list and len(v) == 2 and type(v[1]) == SBdict :
									# this is a dirrectory
									control = Dumpdir.DIRECTORY
								else :
									control = Dumpdir.INCLUDED
							
							dumpdirs.append(Dumpdir(control+k))
						
						result.append(dumpdirs)
					
						snarfileinfo.addRecord(result)

		self.statusNumber = 0.97
		self.logger.info("creating 'ver' file .")
		FAM.writetofile( snapshot.getPath()+os.sep +"ver", "1.5\n" )
		snapshot.setVersion("1.5")
		if os.path.exists(snapshot.getPath()+os.sep +"ver") :
			self.logger.debug("'ver' file created.")
		self.statusNumber = 1.00
		

	#---------------------------------------------------------------------------------

	def __downgrade_v12 (self,snapshot ):
		self.logger.info("Downgrading to v1.2: %s" % str(snapshot) )
		flist = FAM.readfile( snapshot.getPath()+os.sep +"flist" ).split( "\000" )
		fprops = FAM.readfile( snapshot.getPath()+os.sep +"fprops" ).split( "\000" )
		
		if len(flist)==len(fprops) :
			if len(flist) > 1:
				l = FAM.openfile(snapshot.getPath()+os.sep +"flist.v12", True)
				p = FAM.openfile(snapshot.getPath()+os.sep +"fprops.v12", True)
				for a,b in zip(flist,fprops):
					l.write( a+"\n" )
					p.write( b+"\n" )
				l.close()
				p.close()
				FAM.rename(snapshot.getPath()+os.sep +"flist", "flist.old")
				FAM.rename(snapshot.getPath()+os.sep +"flist.v12", "flist")
				FAM.rename(snapshot.getPath()+os.sep +"fprops", "fprops.old")
				FAM.rename(snapshot.getPath()+os.sep +"fprops.v12", "fprops")
				FAM.writetofile( snapshot.getPath()+os.sep +"ver", "1.3\n" )
		else:
			FAM.delete(snapshot.getPath()+os.sep +"ver")
			raise SBException ("Damaged backup metainfo - disabling %s" % snapshot.getPath() )
		FAM.delete( snapshot.getPath() + os.sep +"ver" )
		FAM.writetofile( snapshot.getPath()+os.sep +"ver", "1.2\n" )
		snapshot.setVersion("1.2")
	
	def __downgrade_v13( self, snapshot ):
		self.logger.info("Downgrading to v1.3: %s" % str(snapshot) )
		FAM.delete( snapshot.getPath() + os.sep +"ver" )
		FAM.writetofile( snapshot.getPath()+os.sep +"ver", "1.3\n" )
		snapshot.setVersion("1.3")

	def __downgrade_v14( self, snapshot ):
		if snapshot.getFormat() != "gzip" :
			raise SBException (_("Cannot downgrade other format than 'gzip' to 1.4"))
		
		self.logger.info("Downgrading to v1.4: %s" % str(snapshot) )
		FAM.delete( snapshot.getPath() + os.sep +"ver" )
		
		self.logger.debug("renaming file.tar.gz to file.tgz")
		os.rename(snapshot.getPath()+os.sep +"files.tar.gz", snapshot.getPath()+os.sep +"files.tgz") 
		
		self.logger.debug("removing 'format' file .")
		FAM.writetofile(snapshot.getPath()+os.sep +"format", snapshot.getFormat())
		
		FAM.writetofile( snapshot.getPath()+os.sep +"ver", "1.4\n" )
		snapshot.setVersion("1.4")
