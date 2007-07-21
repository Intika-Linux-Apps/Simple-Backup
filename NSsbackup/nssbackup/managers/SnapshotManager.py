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

import os
import re
import datetime
import time
import FileAccessManager as FAM
from gettext import gettext as _
from nssbackup.util.structs import SBdict
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.exceptions import *
from nssbackup.util.log import getLogger
##
#@author: Oumar Aziz Ouattara <wattazoum@gmail.com>
#@version: 1.0
##
class SnapshotManager :

	## This is the current diectory use by this SnapshotManager
	#
	__targetDir = None
	
	## 
	# The list of the snapshots is stored the first time it's used so that we don't have to reget it
	__snapshots = None
	
	def __init__(self,targetDir):
		global __targetDir
		if not targetDir or not FAM.exists(targetDir) :
			raise SBException(_("Invalid value of the target directory : ") + targetDir)
		self.__targetDir = targetDir
	
	
	def getSnapshot(self,name):
		"""
		Return the snapshot using his name.
		@param name: 
		"""
		for snp in self.getSnapshots() :
			if snp.getName() == name :
				return snp
		raise SBException(_("Snapshot '%s' not found ") % name)
	
	def getSnapshots(self, fromDate=None, toDate=None, byDate=None):
		"""
		@param fromDate : eg. 2007-02-17
		@param toDate :  2007-02-17
		@param byDate : 2007-02-17
		@return: a list with all the found snapshots (according to the options set)
		"""
		global __snapshots
		snapshots = list()
		
		if fromDate and toDate :
			# get the snapshots from list
			for snp in self.getSnapshots() :
				if fromDate <= snp.getName()[:10] <= toDate :
					snapshots.append( snp )
			snapshots.sort(key=Snapshot.getName,reverse=True)
		elif byDate :
			# get the snapshots from list
			for snp in self.getSnapshots() :
				if snp.getName().startswith(byDate) :
					snapshots.append( snp )
			snapshots.sort(key=Snapshot.getName,reverse=True)
		else :
			if self.__snapshots : return self.__snapshots
			else :
				listing = FAM.listdir(self.__targetDir)
				for dir in listing :
					try :
						snapshots.append( Snapshot( self.__targetDir+"/"+str(dir) ) )
					except NotValidSnapshotException, e :
						getLogger().warning(e.message)
				snapshots.sort(key=Snapshot.getName,reverse=True)
				self.__snapshots = snapshots
			
		if getLogger().isEnabledFor(10) :
			getLogger().debug("[Snapshots Listing]") 
			for snp in snapshots :
				getLogger().debug(str(snp)) 
			getLogger().debug("")
			
		return snapshots
	
	def exportSnapshot(self,snapshot, target, rebase=False):
		"""
		There is two ways of exporting a snapshot. You can either copy the dir to the target 
		or rebase the snapshot before copying it. 
		TODO: Think about a plugins system that will be used to export on TAPE, on DVD and so on.
		@param snapshot :
		@param target :
		@param rebase :   
		"""
		
		
	def rebaseSnapshot(self,torebase, newbase=None):
		"""
		The rebase operation consists in changing the base of a snapshot. 
		Basicaly , That means for 3 snapshots A,B,C if we rebase C to A, 
		we can remove B with no problem, the information contained in C will be updated to 
		keep the changed occurred in B inside C.
		@raise SBException: if torebase is a full backup or newbase is ealier
		"""
		#if the snapshot to rebase is full, no need to do the operation. 
		if torebase.isfull() : 
			raise SBException(_("No need to rebase a full snapshot '%s'") % torebase.getName()) 
		# if the new base is earlier, t
		if newbase and torebase.getName() <= newbase.getName() :
			raise SBException(_("Cannot rebase a snapshot on an earlier one : '%(snapshotToRebase)s' <= '%(NewBaseSnapshot)s' ")% {'snapshotToRebase':torebase.getName(), 'NewBaseSnapshot': newbase.getName()}) 
		# to rebase, we get the revert state to update the snapshot
	
	
	def removeSnapshot(self,snapshot):
		"""
		The removal of a snapshot is more complicated than just remove the snapshot dir, 
		We need to rebase the next snapshot before removing the snapshot.
		@param snapshot: the snapshot to remove
		"""
		# rebase all child snapshots to the base of this snapshot
		listing = self.getSnapshots()
		for snp in listing :
			if snp.getBase() == snapshot.getName() :
				getLogger().debug("Rebasing '%s' to '%s' " % (snp.getName(), snapshot.getBaseSnapshot().getName()) )
				self.rebaseSnapshot(snp, snapshot.getBaseSnapshot())
		getLogger().debug("Removing '%s'" % snapshot.getName())
		FAM.delete(snapshot.getPath())	
		
	def compareSnapshots(self, snap1, snap2):
		"""
		Compare 2 snapshots and return and SBdict with the differences between their 
		files. The format is {"file" : ("propsnap1|propsnap2",sonsbdict)}.
		"""
	
	def isAlreadyStored(self,snapshot, _file, lastsnapshot=None):
		"""
		for a file , check if it's already stored in a last snapshot
		@param snapshot: The first snapshot in wih to look
		@param file: The file to look for
		@param lastsnapshot(=None): The lastsnapshot in wich to search (default is last Full one)
		@return: None if file not inside, (the file props if it was stored) 
		"""
		# keep all the snapshot infos
		#getLogger().debug("Searching for '%s' from '%s'" % (_file, snapshot.getName()))
		result = None
		
		if snapshot.isfull() :
			#getLogger().debug("Snapshot '%s' is full, no need to go further " % snapshot.getName())
			if snapshot.getFilesList().has_key(_file) :
				#getLogger().debug("found in '%s' " % snapshot.getName())
				result = snapshot.getFilesList()[_file][0]
			return result
		else :
			getLogger().debug("Snapshot '%s' is inc" % snapshot.getName())
			# snapshot is inc
			# till we reach full base add the non existing files
			endpointfound = False
			cursnp = snapshot
			while endpointfound is False and result is None :
				#getLogger().debug("Searching for '%s' from '%s'" % (_file, cursnp.getName()))
				if cursnp.isfull() or cursnp.getName() == lastsnapshot :
					#getLogger().debug("stop point found '%s'" % cursnp.getName())
					endpointfound = True
				if cursnp.getFilesList().has_key(_file) :
					#getLogger().debug("found in '%s' " % cursnp.getName())
					result = cursnp.getFilesList()[_file][0]
				else : 
					if not cursnp.isfull() :
						cursnp = cursnp.getBaseSnapshot()
			
			return result
	
	def getRevertState(self,snapshot, path, lastsnapshot=None):
		"""
		gets the revert state ie the state of the files at the snapshot time. 
		The algorithm is to keep the newer file existing between snapshot and the first ful snapshot that we encounter.
		@param snapshot: the snapshot from wich to get the state:
		@param path: the path to get the revert state.
		@param lastsnapshot : The snapshot on which one to stop  
		@return: a dict {snapshotPath : SBdict } where SBdict is filled with 
		the files and properties coming from snapshot 'snapshot' and that must be include in the revert state.
		"""
		if not snapshot.getFilesList().has_key(path) : 
			raise SBException(_("The file '%s' is not found in snapshot") % path)
		# keep all the snapshot infos
		contents = SBdict()
		contents[path] = snapshot.getFilesList()[path]
		getLogger().debug("keep all the snapshot '%s' infos" % snapshot.getName())
		result = {snapshot.getPath() : contents}
			
		if snapshot.isfull() :
			getLogger().debug("Snapshot '%s' is full, no need to go further " % snapshot.getName())
			return result
		else :
			getLogger().debug("Snapshot '%s' is inc" % snapshot.getName())
			# snapshot is inc
			# till we reach full base add the non existing files
			fullfound = False
			cursnp = snapshot
			while fullfound is False :
				cursnp = cursnp.getBaseSnapshot()
				if cursnp.isfull() or cursnp.getName() == lastsnapshot :
					getLogger().debug("stop point found '%s'" % cursnp.getName())
					fullfound = True
				if cursnp.getFilesList().has_key(path) and cursnp.getFilesList().getSon(path) :
					for subfile,props in cursnp.getFilesList().getSon(path).iteritems() :
						if not result.has_key(cursnp.getPath()) :
							result[cursnp.getPath()] = SBdict()
						#now sort result.
						keys = result.keys()
						keys.sort(reverse=True)
						
						file = os.path.normpath(os.sep.join([path.rstrip(os.sep),subfile.lstrip(os.sep)]))
						
						for k in keys :
							incl = result[k]
							# /!\ Don't add the cursnp in the include check process.
							if k != cursnp.getPath() and not incl.has_key(file):
								# It means that it's the newer version of that file ,
								#add the file 
								result[cursnp.getPath()][file] = props
				# processing finished for this snapshot
				getLogger().debug("processing finished for snapshot %s " % str(cursnp))
			return result
			
	def purge(self, purge="30"):
		"""
		Purge a directory
		@param mode : for the moment, only "log" and "simple" are supported 
		"""
		snapshots = []
		# Remove broken backup snapshots after first intact snapshot
		listing = FAM.listdir(self.__targetDir)
		for dir in listing :
			try :
				snapshots.append(Snapshot( self.__targetDir+os.sep+str(dir) ))
			except NotValidSnapshotException, e :
				getLogger().info(_("Got a non valid snapshot '%(name)s' , removing : %(error_cause)s ") % {'name': str(dir),'error_cause' :e.message})
				FAM.delete(self.__targetDir+os.sep+str(dir))
		
		# now purge according to date
		topurge = []
		if purge == "log":
			# Logarithmic purge
			# Determine which incremental backup snapshots to remove
			getLogger().warning("Logarithmic purge not implemented yet !")
			
		else:
			# Purge isn't logarithmic
			try: purge = int(purge)
			except: purge = 0
			if purge:
				# Simple purge - remove all backups older then 'purge' days
				for snp in snapshots:
					date = snp.getDate()
					if (datetime.date.today() - datetime.date(date['year'],date['month'],date['day']) ).days > purge:
						topurge.append(snp.getPath())
		
		for adir in topurge:
			getLogger().warning("Deleting '%(dir)s' for purge !" % {'dir' : adir })
			FAM.delete( adir )
		
