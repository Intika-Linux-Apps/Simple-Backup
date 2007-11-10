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
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum at gmail dot com>

from gettext import gettext as _
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.log import getLogger
from nssbackup.util.exceptions import SBException
from nssbackup.managers.SnapshotManager import SnapshotManager
import nssbackup.util as Util
import nssbackup.util.tar as Tar
import tempfile, datetime,os, shutil

class RestoreManager :
	"""
	"""
	
	def __init__(self):
		"""
		"""
		
	def restore(self,snapshot, _file):
		"""
		Restore one file or directory from the backup tdir with name
		file to its old location.
		All existing files must be moved to a "*.before_restore_$time" files.
		@param snapshot: 
		@param file : 
		"""
		self.restoreAs(snapshot, _file, None)
		
	def restoreAs(self,snapshot,_file, target, backupFlag=True,failOnNotFound=True) :
		"""
		Restore one file or directory from the backup tdir with name
		file to target (or to its old location if None if given to target).
		All existing files must be moved to a "*.before_restore_$time" files.
		@param snapshot:
		@param file :  
		@param target: 
		@param backupFlag: Set to false to make no backup when restoring (default = True)
		@param failOnNotFound: set to False if we don't want to fail if a file is not found (default is True)
		"""
		if not snapshot :
			raise SBException("Please provide a Snapshot")
		if not _file :
			raise SBException("Please provide a File/directory")
		
		_file = os.sep+_file.lstrip(os.sep)
		
		# restore
		if not snapshot.getSnapshotFileInfos().hasPath(_file):
			if failOnNotFound :
				raise SBException(_("File '%s' not found in the backup snapshot files list") % _file)
			else : 
				getLogger().warning(_("File '%s' not found in the backup snapshot [%s] files list, We'll not fail though !") % (_file,snapshot.getName()) )
				return
		
		suffix = None
		if backupFlag :
			now = datetime.datetime.now().isoformat("_").replace( ":", "." )
			suffix = ".before_restore_"+now
		
		if target and os.path.exists(target):
			# The target is given and exists
			if os.path.isdir(target):
				# the target is a dir 	
				#create a temp file , extract inside then move the content
				tmpdir = tempfile.mkdtemp(dir=target,prefix='nssbackup-restore_')
				
				Tar.extract( snapshot.getArchive(), _file, tmpdir, bckupsuffix=suffix, splitsize=snapshot.getSplitedSize() )
				if os.path.exists(target+os.sep+ os.path.basename(_file))  and backupFlag :
					Util.nssb_move(target+os.sep+ os.path.basename(_file), target+os.sep+ os.path.basename(_file)+suffix)
				Util.nssb_move(tmpdir+_file, target+os.sep+ os.path.basename(_file))
				shutil.rmtree(tmpdir)
				
			else:
				#the target is a file
				parent = os.path.dirname(target)
				Tar.extract( snapshot.getArchive(), _file, parent, bckupsuffix=suffix,splitsize=snapshot.getSplitedSize() )
		else:
			# target is set to None or target not exists
			if target and not os.path.exists(target) :
				#target != None but target doesn't exists
				os.makedirs(target)
				Tar.extract( snapshot.getArchive(), _file, target,splitsize=snapshot.getSplitedSize() )
			else :
				# Target = None , extract at the place it belongs
				if os.path.exists(_file) :
					# file exist:
					Tar.extract(snapshot.getArchive(), _file, target, bckupsuffix=suffix,splitsize=snapshot.getSplitedSize())
				else :
					# file doesn't exist nothing to move, just extract
					Tar.extract(snapshot.getArchive(), _file, target,splitsize=snapshot.getSplitedSize() )
		
		
	def revert(self, snapshot, dir):
		"""
		Revert a directory to its snapshot date state.
		@param snapshot : The snapshot from which to revert 
		@param dir : the dir to revert, use os.sep for the whole snapshot
		"""
		self.revertAs(snapshot, dir, None)
		
	
	def __cleanBackupedFiles(self, dir , suffix):
		"""
		clean the backuped copies in the directory (dir) that ends with suffix
		@param dir: directory to clean up
		@param suffix: the suffix of backuped files
		"""
		
	
	def revertAs(self,snapshot, dir, targetdir):
		"""
		Revert a directory to its snapshot date state into a directory.
		We will restore the directory starting from the base snapshot to the selected one and clean the restore directory each time.
		@param snapshot : The snapshot from which to revert 
		@param dir : the dir to revert, use os.sep for the whole snapshot
		@param targetdir: The dir in which to restore files 
		"""
		if not snapshot :
			raise SBException("Please provide a Snapshot")
		if not dir :
			raise SBException("Please provide a File/directory")
		
		#dir = os.sep+dir.lstrip(os.sep)
		snpman = SnapshotManager(os.path.dirname(snapshot.getPath()))
		history = snpman.getSnpHistory(snapshot)
		history.reverse()
		
		for snp in history :
			getLogger().debug("Restoring '%s' from snapshot '%s' " % (dir, snp.getName()) )
			self.restoreAs(snp, dir, targetdir, False,False)


