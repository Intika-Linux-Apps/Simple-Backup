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

from gettext import gettext as _
from nssbackup.util.Snapshot import Snapshot
from nssbackup.util.log import getLogger
from nssbackup.util.exceptions import SBException
from nssbackup.managers.SnapshotManager import SnapshotManager
import nssbackup.util as Util
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
		
	def restoreAs(self,snapshot,_file, target) :
		"""
		Restore one file or directory from the backup tdir with name
		file to target (or to its old location if None if given to target).
		All existing files must be moved to a "*.before_restore_$time" files.
		@param snapshot:
		@param file :  
		@param target: 
		"""
		if not snapshot :
			raise SBException("Please provide a Snapshot")
		if not _file :
			raise SBException("Please provide a File/directory")
		
		_file = os.sep+_file.lstrip(os.sep)
		
		# restore
		if not snapshot.getFilesList().has_key(_file) :
			raise SBException(_("File '%s' not found in the backup snapshot files list") % _file)
		
		now = datetime.datetime.now().isoformat("_").replace( ":", "." )
		suffix = ".before_restore_"+now
		
		if target and os.path.exists(target):
			# The target is given and exists
			if os.path.isdir(target):
				# the target is a dir 	
				#create a temp file , extract inside then move the content
				tmpdir = tempfile.mkdtemp(dir=target,prefix='nssbackup-restore_')
				Util.extract( os.sep.join([snapshot.getPath(),"files.tgz"]), _file, tmpdir, bckupsuffix=suffix )
				if os.path.exists(target+os.sep+ os.path.basename(_file)) :
					shutil.move(target+os.sep+ os.path.basename(_file), target+os.sep+ os.path.basename(_file)+suffix)
				shutil.move(tmpdir+_file, target+os.sep+ os.path.basename(_file))
				shutil.rmtree(tmpdir)
			else:
				#the target is a file
				parent = os.path.dirname(target)
				Util.extract( os.sep.join([snapshot.getPath(),"files.tgz"]), _file, parent, bckupsuffix=suffix )
		else:
			# target is set to None or target not exists
			if target and not os.path.exists(target) :
				#target != None but target doesn't exists
				os.makedirs(target)
				Util.extract( os.sep.join([snapshot.getPath(),"files.tgz"]), _file, target )
			else :
				# Target = None , extract at the place it belongs
				if os.path.exists(_file) :
					# file exist:
					Util.extract(os.sep.join([snapshot.getPath(),"files.tgz"]), _file, target, bckupsuffix=suffix)
				else :
					# file doesn't exist nothing to move, just extract
					Util.extract( os.sep.join([snapshot.getPath(),"files.tgz"]), _file, target )
		
		
	def revert(self, snapshot, dir):
		"""
		Revert a directory to its snapshot date state.
		@param snapshot : The snapshot from which to revert 
		@param dir : the dir to revert, use os.sep for the whole snapshot
		"""
		self.revertAs(snapshot, dir, None)
		
	
	def revertAs(self,snapshot, dir, targetdir):
		"""
		Revert a directory to its snapshot date state into a directory.
		@param snapshot : The snapshot from which to revert 
		@param dir : the dir to revert, use os.sep for the whole snapshot
		@param targetdir: The dir in which to restore files 
		"""
		snpman = SnapshotManager(os.path.dirname(snapshot.getPath()))
		revertState = snpman.getRevertState(snapshot, dir)
		# revertState is a dictionnay with snapshot names as keys and contents as values
		# we'll not recurse into a dir in revertState, tar wil do this job
		tempfiles = []
		for snppath, sbdict in revertState.iteritems() :
			# set the temp file list
			tmpfd, tmpname = tempfile.mkstemp(prefix="rvtlist_", dir=snppath)
			for path in sbdict.iterkeys():
				# we found an endpoint
				if not sbdict.getSon(path) :
					getLogger().debug("Adding %s to the extract list" % path.lstrip(os.sep))
					os.write(tmpfd,path.lstrip(os.sep)+"\000")
			os.close(tmpfd)
			# extract now from archive
			now = datetime.datetime.now().isoformat("_").replace( ":", "." )
			suffix = ".before_restore_"+now
			Util.extract2(os.sep.join([snppath,"files.tgz"]), tmpname, targetdir, bckupsuffix=suffix)
