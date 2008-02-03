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
from gettext import gettext as _
from tempfile import mkstemp
import nssbackup.managers.FileAccessManager as FAM
from nssbackup.util.exceptions import FuseFAMException

class sftpFuseFAM (pluginFAM)  :
	"""
	The fuseFAM plugin for sftp
	@requires: curlftpfs
	"""
	
	def matchScheme(self,remoteSource):
		if re.compile("^(sftp://[^/]+?/)(.*)").search(remoteSource) :
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
		mountbase = mountbase.rstrip("/")
		#make the mount point
		mountpoint = os.sep.join([mountbase,self.__defineMountDirName(source)])
		if not os.path.exists(mountpoint) :
			os.mkdir(mountpoint)
		server,pathinside = re.compile("^(sftp://[^/]+?/)(.*)").search(source).groups()
		if not pathinside : pathinside=""
		
		#If the path is already mounted No need to retry
		if self.checkifmounted(source, mountbase) :
			return (server,mountpoint,pathinside)
		
		# Create output log file
		outptr,outFile = mkstemp(prefix="sftpFuseFAMmount_output_")
		# Create error log file
		errptr, errFile = mkstemp(prefix="sftpFuseFAMmount_error_")
		# Call the subprocess using convenience method
		retval = subprocess.call(["curlftpfs",server ,mountpoint], 0, None, None, outptr, errptr)
		# Close log handles
		os.close(errptr)
		os.close(outptr)
		outStr, errStr = FAM.readfile(outFile), FAM.readfile(errFile)	
		FAM.delete(outFile)
		FAM.delete(errFile)
		if retval != 0 :
			raise FuseFAMException(_("Couldn't mount '%(server)s' into '%(mountpoint)s' : %(error)s") %  {'server' : server , 'mountpoint': mountpoint, 'error':errStr})
		
		return (server,mountpoint,pathinside)
	
	def getdoc(self):
		doc = _("SFTP schema is like : sftp://user:pass@server/anything") 
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
		# this will match the RE and give us a group like ('ftp://', 'test:pass@', 'wattazoum-vm.ft.nn', 'ddd/kjlh/klhkl/vvvv')
		exp = re.compile("^(sftp://)([^:]+?:[^@]+?@|[^:]+?@)?([^/^:^@]+?)/(.*)")
		match = exp.search(remote)
		if not match : 
			raise FuseFAMException(_("Error matching the schema 'sftp://user:pass@server/anything' with '%s' (The '/' after server is mandatory)") % remote)
		else :
			if match.group(2) :
				exp1 = re.compile("^([^:]+?)(:[^@]+?)?@")
				user = exp1.search(match.group(2)).group(1)
				dirname = "sftp_"+user+"@"+match.group(3)
				return dirname
			else :
				dirname = "sftp_"+match.group(3)
				return dirname
