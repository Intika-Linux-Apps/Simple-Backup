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
			raise SBException("Invalid Value of targetDir")
		self.__targetDir = targetDir
	

	def getSnapshots(self, fromDate=None, toDate=None, byDate=None):
		"""
		@param fromDate : eg. 2007-02-17
		@param toDate :  2007-02-17
		@param byDate : 2007-02-17
		@return: a list with all the found snapshots (acording to the options set)
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
			raise SBException("No need to rebase full snapshot '%s'"% torebase.getName()) 
		# if the new base is earlier, t
		if newbase and torebase.getName() <= newbase.getName() :
			raise SBException("Cannot rebase a snapshot on an earlier one : '%s' <= '%s' "% (torebase.getName(), newbase.getName())) 
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
	
	def getRevertState(self,snapshot, path, lastsnapshot=None):
		"""
		gets the revert state ie the state of the files at the snapshot time. 
		The algorithm is to keep the newer file existing between snapshot and the first ful snapshot that we encounter.
		@param snapshot: the snapshot from wich to get the state:
		@param path: the path to get the revert state.
		@param lastsnapshot : The snapshot on which one to stop  
		@return: a dict {snapshotPath : SBdict } where SBdict is filled with 
		the files and properties coming from snapshot 'snapshotName' and that must be include in the revert state.
		"""
		if not snapshot.getFilesList().has_key(path) : 
			raise SBException("'%s' not found in snapshot"% path)
		# keep all the snapshot infos
		getLogger().debug("keep all the snapshot '%s' infos" % snapshot.getName())
		contents = SBdict()
		contents[path] = snapshot.getFilesList()[path]
		result = {snapshot.getPath() : contents}
		getLogger().debug(" %s " % result)
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
				if cursnp.getFilesList().getSon(path) :
					for subfile,props in cursnp.getFilesList().getSon(path).iteritems() :
						if not result.has_key(cursnp.getPath()) :
							result[cursnp.getPath()] = SBdict()
						#now sort result.
						keys = result.keys()
						keys.sort(reverse=True)
						
						file = os.path.normpath(os.sep.join([path,subfile]))
						
						for k in keys :
							incl = result[k]
							# /!\ Don't add the cursnp in the include check process.
							if k != cursnp.getPath() and not incl.has_key(file):
								# It means that it's the newer version of that file ,
								#add the file 
								result[cursnp.getPath()][file] = props
								#getLogger().debug(" %s " % result)
				# processing finished for this snapshot
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
				getLogger().info("got non valid snapshot '%s' , removing : %s " % (str(dir),e.message))
				FAM.delete(self.__targetDir+os.sep+str(dir))
		
		# now purge according to date
		topurge = []
		if purge == "log":
			print ("TODO: Check that !!!")
			# Logarithmic purge
			# Determine which incremental backup snapshots to remove
			seenfull = 0
			for e in listing:
			    if seenfull < 1 and e.endswith( ".ful" ):
				seenfull += 1
			    elif seenfull > 1 and e.endswith( ".inc" ):
				topurge.append( e )
			
			# Now for the fun part - expiring the full backup snapshots
			# Only consider the full backups
			
			fulls = [x for x in listing if x.endswith( ".ful" )]
			days = {}
			
			for adir in fulls:
			    m = r.search( adir )
			    dif = datetime.datetime.today() - datetime.datetime(int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4)),int(m.group(5)),int(m.group(6)))
			    if dif.days < 1:
				# Keep all from last 24 hours
				continue
			    if days.has_key( dif.days ):
				topurge.append( days[dif.days] )
				days[dif.days] = adir # Keep the earliest backup of each day
			    else:
				days[dif.days] = adir
		
			bdays = sorted(days.keys())
			
			for i in range( 1, 4 ):
			    week = [ x for x in bdays if x>(i*7) and x<=((i+1)*7) ]
			    week.sort()
			    week = week[:-1] # Keep earliest backup in a week
			    for aday in week:
				topurge.append( days[aday] )

			for i in range( 0, 12 ):
			    month = [ x for x in bdays if x>(28+i*30) and x<=(28+(i+1)*30) ]
			    month.sort()
			    month = month[:-1] # Keep earliest backup in a month
			    for aday in month:
				topurge.append( days[aday] )
			
			bdays = [x for x in bdays if x>(28+12*30)] # Now for the really old backups
			bdays.sort()
			
			years = {}
			for aday in bdays:
			    year = int(aday/(28+12*30))
			    if years.has_key( year ):
				topurge.append( days[aday] ) # Keep earliest backup of a year
				years[year] = aday
			    else:
				years[year] = aday
			
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
		    FAM.delete( adir )
		
