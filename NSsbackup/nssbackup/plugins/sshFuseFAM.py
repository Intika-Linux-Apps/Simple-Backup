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

from nssbackup.plugins import pluginFAM
import subprocess
import re
import os
import pexpect
from tempfile import mkstemp
import nssbackup.managers.FileAccessManager as FAM
from nssbackup.util.exceptions import FuseFAMException, SBException

class sshFuseFAM (pluginFAM)  :
	"""
	The fuseFAM plugin for ssh
	@requires: sshfs, python-pexpect
	@author: Oumar Aziz Ouattara
	@version: 1.0
	"""
	
	def matchScheme(self,remoteSource):
		"""
		SSH schema is like : ssh://user:pass@example.com/home/user/backup/ 
		(user,pass, the first '/' ) are mandatory
		"""
		if re.compile("^(ssh://)([^:]+?:[^@]+?)@([^/^:^@]+?)/(.*)").search(remoteSource) :
			return True
		return False
	
	def mount(self,source, mountbase):
		"""
		Mount the source intor the mountbase dir . This method should create a mount point to mount the source. 
		The name of the mount point should be very expressive so that we avoid collision with other mount points
		@param source: The remote path
		@param mountbase: The mount points base dir
		@return: The mount point complete path
		"""
		mountbase = mountbase.rstrip(os.sep)
		
		exp = re.compile("^(ssh://)([^:]+?):([^@]+?)@([^/^:^@]+?)/(.*)")
		match = exp.search(source)
		if not match : 
			raise FuseFAMException("Error matching the schema 'ssh://user:pass@example.com/home/' with '%s' (The '/' after server is mandatory)" % source)
		else :
			remoteSource = match.group(1)+match.group(2)+":"+match.group(3)+"@"+match.group(4)+'/'
			user = match.group(2)
			password = match.group(3)
			mountpoint = mountbase+os.sep+"ssh_"+user+"@"+match.group(4)
			if match.group(5) :
				pathinside = match.group(5)
			else :
				pathinside = ""
		
		#If the path is already mounted No need to retry
		if self.checkifmounted(source, mountbase) :
			return (remoteSource,mountpoint,pathinside)
		
		cmd = "sshfs "+user+"@"+match.group(4)+":/"
		cmd = cmd + " " + mountpoint
		
		if not os.path.exists(mountpoint) :
			os.mkdir(mountpoint)
		
		sshfsp = pexpect.spawn(cmd)
		sshfsp.expect(".*[pP]assword:")
		sshfsp.sendline(password)
		sshfsp.next()
	#	if sshfsp.isalive() or sshfsp.exitstatus :
	#		raise SBException ("The sshfs command '%s' didn't perform normally " % cmd )
		return (remoteSource,mountpoint,pathinside)

	def getdoc(self):
		doc = "SSH schema is like : ssh://user:pass@example.com/home/user/backup/" 
		return doc

	def checkifmounted(self,source, mountbase):
		"""
		@return: True if mounted, False if not
		"""
		mountpoint = mountbase.rstrip(os.sep)+os.sep+self.__defineMountDirName(source)
		return os.path.ismount(mountpoint)
		
	def __defineMountDirName(self, remote):
		"""
		"""
		# this will match the RE and give us a group like ('ssh://', 'test', 'pass', 'wattazoum-vm.ft.nn', 'ddd/kjlh/klhkl/vvvv')
		exp = re.compile("^(ssh://)([^:]+?):([^@]+?)@([^/^:^@]+?)/(.*)")
		match = exp.search(remote)
		if not match : 
			raise FuseFAMException("Error matching the schema 'ssh://user:pass@example.com/home/' with '%s' (The '/' after server is mandatory)" % remote)
		else :
			user = match.group(2)
			dirname = "ssh_"+user+"@"+match.group(4)
			return dirname