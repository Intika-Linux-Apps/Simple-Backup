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
from nssbackup.util.tar import SnapshotFile
from nssbackup.util.tar import ProcSnapshotFile
import nssbackup.util.tar as TAR
import shutil
import tempfile
import os
import re
import datetime
import time
import FileAccessManager as FAM
from gettext import gettext as _
import nssbackup.util as Util
from nssbackup.util.structs import SBdict
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.exceptions import *
from nssbackup.util.log import LogFactory
##
#@author: Oumar Aziz Ouattara <wattazoum@gmail.com>
#@version: 1.0
##
class SnapshotManager :

	## This is the current diectory use by this SnapshotManager
	#
	__targetDir = None
	
	statusMessage = None
	substatusMessage = None
	statusNumber = None
	
	REBASEDIR = "rebaseTmpDir"
	
	def __init__(self,targetDir):
		global __targetDir
		self.logger = LogFactory.getLogger()
		
		## 
		# The list of the snapshots is stored the first time it's used so that we don't have to reget it
		self.__snapshots = None
		
		if not targetDir or not FAM.exists(targetDir) :
			raise SBException(_("Invalid value of the target directory : ") + targetDir)
		self.__targetDir = targetDir
	
	def getStatus(self):
		"""
		@return: [statusNumber,statusMessage,substatusMessage]
		"""
		return [self.statusNumber,self.statusMessage,self.substatusMessage]
	
	def getSnapshot(self,name):
		"""
		Return the snapshot using his name.
		@param name: 
		"""
		for snp in self.getSnapshots() :
			if snp.getName() == name :
				return snp
		raise SBException(_("Snapshot '%s' not found ") % name)
	
	def getSnapshots(self, fromDate=None, toDate=None, byDate=None,forceReload=False):
		"""
		Return a list with all the found snapshots (according to the options set).
		This list is sorted from the latest snapshot to the earliest . 
		0 => last snapshot 
		len(list) => older one
		@param fromDate : eg. 2007-02-17
		@param toDate :  2007-02-17
		@param byDate : 2007-02-17
		@param forceReload: True or false
		@return: 
		"""
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
			if self.__snapshots and not forceReload: return self.__snapshots
			else :
				listing = FAM.listdir(self.__targetDir)
				for dir in listing :
					try :
						snapshots.append( Snapshot( self.__targetDir+"/"+str(dir) ) )
					except NotValidSnapshotException, e :
						self.logger.warning(e.message)
				snapshots.sort(key=Snapshot.getName,reverse=True)
				self.__snapshots = snapshots
			
		if self.logger.isEnabledFor(10) :
			self.logger.debug("[Snapshots Listing]") 
			for snp in snapshots :
				self.logger.debug(str(snp)) 
			
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
		
		Rebase principle:
		snp1 -> snp2 -> snp3
		
		rebase snp3 on snp1 :
		(snp3 has the newer version of the file it contains)
			remove snp3 "ver" file ( means the snapshot is being processed )
			for each file in snp2 :
				if included in snp3 -> pass
				if not : push the file in snp3
			when finished, checks and merge the includes.list and excludes.list
			change the base file content to the new base
			write the "ver" file
		If an error is encountered -> cancel Rebase ( we shouldn't loose the snapshot !)

		@raise SBException: if torebase is a full backup or newbase is ealier
		"""
		#if the snapshot to rebase is full, no need to do the operation. 
		if torebase.isfull() : 
			raise RebaseFullSnpForbidden(_("No need to rebase a full snapshot '%s'") % torebase.getName()) 
		# if the new base is earlier, t
		if newbase and torebase.getName() <= newbase.getName() :
			raise RebaseSnpException(_("Cannot rebase a snapshot on an earlier one : '%(snapshotToRebase)s' <= '%(NewBaseSnapshot)s' ")% {'snapshotToRebase':torebase.getName(), 'NewBaseSnapshot': newbase.getName()}) 
		if not torebase.getBase():
			raise RebaseSnpException(_("'%(snapshotToRebase)s'  doesn't have 'base' file , it might have been broken ")% {'snapshotToRebase':torebase.getName()})
		
		currentTorebase = torebase
		
		while currentTorebase.getBase():
			self.statusMessage = _("Rebasing '%s' on '%s'") % (currentTorebase,currentTorebase.getBase)
			self.__rebaseOnLastSnp(currentTorebase)
			if newbase and currentTorebase.getBaseSnapshot().getName() <= newbase.getName():
				break
		
	
	def convertToFullSnp(self,snapshot):
		"""
		rebase a snapshot till the full one and then make it ful.
		@param snapshot: the snapshot to make full
		@type snapshot: Snapshot
		"""
		self.rebaseSnapshot(snapshot)
	
	def __pullSnpContent(self,snapshot, topullSnp):
		"""
		Move the 'topullSnp' snapshot content to the 'snapshot' snapshot
		@param snapshot: the snapshot to push in
		@type snapshot: Snapshot
		@param topullSnp: The snapshot to pull
		@type topullSnp: Snapshot
		"""
		# Utilities functions everything should be done in temporary files #
		
		def makeTmpTAR():
			# write temp flist using the snar file  to backup
			self.logger.info("Writing the temporary Files list to make the transfer")
			flistd = open(tmpdir+os.sep+"flist.tmp",'w')
			snarfile = ProcSnapshotFile(SnapshotFile(tmpdir+os.sep+"snar.part.tmp"))
			for f in snarfile.iterfiles():
				flistd.write(f.lstrip(os.sep)+'\0')
			flistd.close()
			
			self.logger.info("Make a temporary tar file by tranfering the files from base")
			tmptardir = tmpdir+os.sep+"tempTARdir"
			os.mkdir(tmptardir)
			
			TAR.extract2(topullSnp.getArchive(), tmpdir+os.sep+"flist.tmp", tmptardir,additionalOpts=["--no-recursion"])
			
			# uncompress the tar file so that we can append files to it
			archive = snapshot.getArchive()
			if not TAR.getArchiveType(archive):
				raise SBException("Invalid archive file '%s'" % archive)
			else :
				arvtype = TAR.getArchiveType(archive)
				if arvtype == "gzip" :
					Util.launch("gunzip", [archive])
					archive = archive[:-3]
				elif arvtype == "bzip2" :
					Util.launch("bunzip2", [archive])
					archive = archive[:-4]
				# else : the archive is already uncompressed
			
			# get file list to append
			fl = os.listdir(tmptardir+os.sep)
					
			TAR.appendToTarFile(archive, fl,workingdir=tmptardir+os.sep )
			
			# recompress
			if arvtype == "gzip" :
				Util.launch("gzip", [archive])
			elif arvtype == "bzip2" :
				Util.launch("bzip2", [archive])
			
			shutil.rmtree(tmptardir)
		
		def mergeSnarFile():
			"""
			Merge the snar.full.tmp file with the current snapshot snarfile in a snar.final.tmp file.
			for each path in the current snar if included inthe snar.full.tmp , drop it, oherwise add the whole record.
			""" 
			self.logger.info("Merging Snar files")
			
			fd = open(tmpdir+os.sep+"snar.final.tmp",'w')
			fd.write(header)
			fd.close()
			
			tmpfinalSnarinfo = ProcSnapshotFile(SnapshotFile(tmpdir+os.sep+"snar.final.tmp",True))
			
			snarfileinfos = ProcSnapshotFile(SnapshotFile(tmpdir+os.sep+"snar.full.tmp"))
			for record in cur_snpfinfo.iterRecords():
				if not snarfileinfos.hasPath(record[SnapshotFile.REC_DIRNAME]):
					tmpfinalSnarinfo.addRecord(record)
			
			for record in snarfileinfos.iterRecords():
				tmpfinalSnarinfo.addRecord(record)
			
		
		def mergeIncludesList():
			srcfd = open(topullSnp.getIncludeFListFile())
			destfd = open(tmpdir+os.sep+"includes.list.tmp",'w')
			for line in srcfd.readlines():
				destfd.write(line)
			srcfd.close()
			
			srcfd = open(snapshot.getIncludeFListFile())
			for line in srcfd.readlines():
				destfd.write(line)
			srcfd.close()
			
			destfd.close()
			
				
		def mergeExcludesList():
			srcfd = open(topullSnp.getExcludeFListFile())
			destfd = open(tmpdir+os.sep+"excludes.list.tmp",'w')
			for line in srcfd.readlines():
				destfd.write(line)
			srcfd.close()
			
			srcfd = open(snapshot.getExcludeFListFile())
			for line in srcfd.readlines():
				destfd.write(line)
			srcfd.close()
			
			destfd.close()
			
		
		def movetoFinaldest():
			self.logger.info("Move all temporary files to their final destivation")
			# SNAR file
			if os.path.exists(snapshot.getSnarFile()) :
				os.remove(snapshot.getSnarFile())
			os.rename(tmpdir+os.sep+"snar.final.tmp",snapshot.getSnarFile())
			
			# Includes.list
			if os.path.exists(snapshot.getIncludeFListFile()) :
				os.remove(snapshot.getIncludeFListFile())
			os.rename(tmpdir+os.sep+"includes.list.tmp",snapshot.getIncludeFListFile())
			
			# Excludes.list
			if os.path.exists(snapshot.getIncludeFListFile()) :
				os.remove(snapshot.getExcludeFListFile())
			os.rename(tmpdir+os.sep+"excludes.list.tmp",snapshot.getExcludeFListFile())
		
		# ------------------
		# process
		try :
			self.statusNumber = 0.00
			tmpdir = snapshot.getPath()+os.sep+self.REBASEDIR
			os.mkdir(tmpdir)
			
			self.logger.info("Writing the temporary SNARFILEs to make the transfer")
			
			# get snar header from current snapshots
			snard = open(snapshot.getSnarFile())
			header = snard.readline()
			if len(header) > 0 :
				# the SNAR file isn't empty
				n=0
				while n < 2:
					c = snard.read(1)
					if len(c) != 1:
						snard.close()
						raise SBException(_("The snarfile header is incomplete !"))
					if c == '\0' : n += 1
					header+=c
				snard.close()
			else :
				# the SNAR file is empty
				self.logger.debug("SNAR file empty, create the header manually")
				snard.close()
				date = snapshot.getDate()
				datet = datetime.datetime(date['year'],date['month'],date['day'],date['hour'],date['minute'],date['second'])
				
			self.logger.debug("Current SNAR Header : " + header)
			
			snarpartinfo = ProcSnapshotFile(SnapshotFile(tmpdir+os.sep+"snar.part.tmp",True))
			snarfullinfo = ProcSnapshotFile(SnapshotFile(tmpdir+os.sep+"snar.full.tmp",True))
			
			if header: 
				fd = open(tmpdir+os.sep+"snar.part.tmp",'w')
				fd.write(header)
				fd.close()
				fd = open(tmpdir+os.sep+"snar.full.tmp",'w')
				fd.write(header)
				fd.close()
			else :
				snarpartinfo.setHeader(datet)
				snarfullinfo.setHeader(datet)
				header = snarfullinfo.getHeader()
			
			base_snpfinfo = topullSnp.getSnapshotFileInfos()
			cur_snpfinfo = snapshot.getSnapshotFileInfos()
			for record in base_snpfinfo.iterRecords():
				
				if not cur_snpfinfo.hasPath(record[SnapshotFile.REC_DIRNAME]):
					# ADD to temp snar
					snarfullinfo.addRecord(record)
					snarpartinfo.addRecord(record)
				else :
					toaddContent = []
					# go in the content to check for the existance 
					curcontent = cur_snpfinfo.getContent(record[SnapshotFile.REC_DIRNAME])
					curcontentFiles = []
					for d in curcontent :
						curcontentFiles.append(d.getFilename())
					
					for dumpdir in record[SnapshotFile.REC_CONTENT]:
						if dumpdir.getFilename() not in curcontentFiles :
							toaddContent.append(dumpdir)
							# to prepare the full temp snar file, complet the curcontent
							curcontent.append(dumpdir)
					
					# if toadd content is empty then , the whole content is already included in the directory
					# no need to add it
					if toaddContent:
						toaddRecord = record[:-1]
						toaddRecord.append(toaddContent)
						# write to the SnarFile
						snarpartinfo.addRecord(toaddRecord)
					# 	add the complete record to the full temp snar file
					toaddFullRecord = record[:-1]
					toaddFullRecord.append(curcontent)
					snarfullinfo.addRecord(toaddFullRecord)
					
			# Currently the snar.full.tmp contains both base complete records and the common completed 
			# records between base and current 
			self.statusNumber = 0.20
			mergeSnarFile()
			
			self.statusNumber = 0.35
			mergeIncludesList()
			
			self.statusNumber = 0.45
			mergeExcludesList()
			
			self.statusNumber = 0.55
			makeTmpTAR()
			
			self.statusNumber = 0.75
			movetoFinaldest()
			
			# clean Temporary files 
			self.statusNumber = 0.85
			shutil.rmtree(tmpdir)
			
			self.statusNumber = 0.95
			snapshot.commitverfile()
			self.statusNumber = 1.00
			
			self.statusNumber = None
			self.statusMessage = None
			self.substatusMessage = None
		except Exception, e :
			_msg = _("Got an exception when Pulling '%s' : ") + str(e)
			self.logger.error( _msg % ( snapshot.getName()) ) 
			self.__cancelPull(snapshot)
			raise e
		
	
	def __rebaseOnLastSnp(self,snapshot):
		"""
		One step rebase
		"""
		
		if not snapshot.getBase() :
			raise SBException(_("Snapshot '%s' is a full . Can't rebase on older snapshot") ) % snapshot.getName()
		basesnp = snapshot.getBaseSnapshot()
		newbase = basesnp.getBase()
		
		self.__pullSnpContent(snapshot, basesnp)
		
		# set the new base
		if newbase :
			snapshot.setBase(newbase)
			snapshot.commitbasefile()
		else :
			self.__makeSnpFull(snapshot)
		
		
	def __makeSnpFull(self,snapshot):
		"""
		Make an inc  snapshot to a full one
		@param snapshot: The snapshot to transform
		@type snapshot: Snapshot
		@return: the new full snapshot
		@rtype: Snapshot
		"""
		if snapshot.isfull():
			self.logger.info(_("Snapshot '%s' is already Full, nothing to do (not changing it to full")) % snapshot.getName()
			return snapshot
		path = snapshot.getPath()
		os.rename(path+os.sep+'base', path+os.sep+'base.old')
		os.rename(path, path[:-3]+'ful')
		return Snapshot(path[:-3]+'ful')
		
	def __cancelPull(self,snapshot):
		"""
		To be able to handle well the cancellation of a pull of a snapshot from another, we will need to not modify the snapshot till the last moment.
		This means, the infos we want to add in the SNAR file should be created as a temporary SNAR file
		Same goes for the TAR file. So that to cancel, we will just have to remove those temporary files and restore the 'ver' file.
		"""
		self.logger.info(_("Cancelling pull of snapshot '%s'") % snapshot.getName() )
		path = snapshot.getPath()+os.sep+self.REBASEDIR
		shutil.rmtree(path)
		
		if os.path.exists(snapshot.getPath()+os.sep+"files.tar"):
			format = snapshot.getFormat()
			if format == "gzip":
				Util.launch("gzip",[snapshot.getPath()+os.sep+"files.tar"])
			elif format == "bzip2":
				Util.launch("bzip2",[snapshot.getPath()+os.sep+"files.tar"])
		snapshot.commitverfile()
	
	
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
				if snapshot.isfull():
					raise SBException(_("It's impossible and not recommended to delete a full snapshot !"))
				else:
					self.logger.debug("Rebasing '%s' to '%s' " % (snp.getName(), snapshot.getBaseSnapshot().getName()) )
					self.rebaseSnapshot(snp, snapshot.getBaseSnapshot())
		self.logger.debug("Removing '%s'" % snapshot.getName())
		FAM.delete(snapshot.getPath())
		
		
	def compareSnapshots(self, snap1, snap2):
		"""
		Compare 2 snapshots and return and SBdict with the differences between their 
		files. The format is {"file" : ("propsnap1|propsnap2",sonsbdict)}.
		"""
	

	def getSnpHistory(self,snapshot):
		"""
		gets the list of preceding snapshots till the last full one
		@param snapshot : the given snapshot
		@return: a list of Snapshots starting from the most recent one to the full one
		@note: you'll need to reverse this list to make a revert 
		"""
		if not snapshot :
			raise SBException("Please provide a snapshot to process")
		
		result = []
		# add the first snapshot
		result.append(snapshot)
		current = snapshot
		while (current.getBaseSnapshot()) :
			current = current.getBaseSnapshot()
			result.append(current)
		
		# Just for DEBUG
		if self.logger.isEnabledFor(10) :
			# get the history 
			history = "\n[%s history]"% snapshot.getName()
			for snp in result :
				history += "\n- %s" % snp.getName()
			self.logger.debug(history)
		
		return result
			
	def purge(self, purge="30"):
		"""
		Purge a directory
		@param mode : for the moment, only "log" and "simple" are supported 
		"""
		
		def purgeinterval(_from,_to):
			f,t = datetime.date.fromtimestamp(_from),datetime.date.fromtimestamp(_to)
			_fromD = '%04d-%02d-%02d' % (f.year,f.month,f.day)
			_toD = '%04d-%02d-%02d' % (t.year,t.month,t.day)
			self.logger.debug("Purging from %s to %s" % (_fromD,_toD))
			snps = self.getSnapshots(fromDate=_fromD, toDate=_toD)
			if not snps is None and len(snps) != 0 :
				try :
					self.rebaseSnapshot(snps[0],snps[-1])
				except RebaseFullSnpForbidden, e:
					self.logger.warning(_("Got till a Full backup before the end of the rebase ! Stopping here !"))  
				if len(snps[1:-1]) > 0:
					# remove the snapshot
					for s in snps[1:-1]:
						if not s.isfull():
							FAM.delete(s.getPath())
						
			
		snapshots = []
		# Remove broken backup snapshots after first intact snapshot
		listing = FAM.listdir(self.__targetDir)
		for dir in listing :
			try :
				snapshots.append(Snapshot( self.__targetDir+os.sep+str(dir) ))
			except NotValidSnapshotException, e :
				if isinstance(e, NotValidSnapshotNameException) :
					self.logger.warning(_("Got a non valid snapshot '%(name)s' due to name convention : %(error_cause)s ") % {'name': str(dir),'error_cause' :e.message})
				else : 
					self.logger.info(_("Got a non valid snapshot '%(name)s' , removing : %(error_cause)s ") % {'name': str(dir),'error_cause' :e.message})
					FAM.delete(self.__targetDir+os.sep+str(dir))
		
		# now purge according to date
		if purge == "log":
			self.logger.info("Logarithm Purging !")
			# Logarithmic purge
			#Keep progressivelly less backups into the past:
			#Keep all backups from yesterday
			#Keep one backup per day from last week.
			#Keep one backup per week from last month.
			#Keep one backup per month from last year.
			#Keep one backup per year further into past.
			#Erase all other backups.
			daytime = 24*3600
			_today = t = int(time.time())
			_2daysbefore = t - 2*daytime
			_1weekbefore = t - 9*daytime
			_1monthbefore = t - 30*daytime
			_1yearbefore = t - 365*daytime
			currentday = _2daysbefore
			
			# check for last week 
			self.logger.info("Logarithm Purging [Last week]!")
			for n in range(1,(_2daysbefore - _1weekbefore) / daytime) : 
				purgeinterval(_2daysbefore - n*daytime,_2daysbefore - (n-1)*daytime)
			
			# check for last month
			self.logger.info("Logarithm Purging [Last month]!")
			for n in range(1,(_1weekbefore - _1monthbefore) / (7*daytime)) : 
				purgeinterval(_1weekbefore- n*7*daytime,_1weekbefore - (n-1)*7*daytime)
			
			# check for last year
			self.logger.info("Logarithm Purging [Last Year]!")
			for n in range(1,(_1monthbefore - _1yearbefore) / (30*daytime)) : 
				purgeinterval(_1monthbefore- n*30*daytime,_1monthbefore - (n-1)*30*daytime)
						
		else:
			# Purge isn't logarithmic
			try: purge = int(purge)
			except: purge = 0
			if purge:
				# Simple purge - remove all backups older then 'purge' days
				for snp in snapshots:
					date = snp.getDate()
					if (datetime.date.today() - datetime.date(date['year'],date['month'],date['day']) ).days > purge:
								self.logger.warning(_("Deleting '%(snp)s' for purge !") % {'snp' : snp })
								self.removeSnapshot(snp)
		
