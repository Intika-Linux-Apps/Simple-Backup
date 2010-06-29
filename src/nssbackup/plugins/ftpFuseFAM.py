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
#	Jean-Peer Lorenz <peer.loz@gmx.net>

from nssbackup.plugins import pluginFAM
import subprocess
import re
import os
from gettext import gettext as _
from tempfile import mkstemp
from nssbackup.util import file_handling as FAM
from nssbackup.util.exceptions import FuseFAMException

ftpUrlRegex = "^ftp://" + "(([^:]+):([^@]+)@)?" + "([^/^:^@]+?)" + "(:([0-9]+))?" + "/(.*)"

class ftpFuseFAM (pluginFAM)  :
	"""The fuseFAM plugin for ftp
	
	@requires: curlftpfs
	@todo: Dependency on 'curlftpfs' must be taken into account for packaging!
	"""

	def matchScheme(self, remoteSource):
		"""This method checks for the scheme (the protocol) of the given
		remote source, i.e. it should not check the validity of the URL.
		This behavior is necessary since otherwise no plugin is found
		to handle a FTP address if this address is not valid. The user
		would be confused. The validity of a given FTP address must be
		checked separate.
		
		@todo: The plugins ssh, sftp do not behave if the suggested way! Fix them!
		"""
		_res = False
		_search_res = re.compile(ftpUrlRegex).search(remoteSource)
		if _search_res is not None:
			_res = True
		return _res

	def mount(self, source, mountbase):
		"""Mount the source into the mountbase dir . This method should
		create a mount point to mount the source. The name of the mount
		point should be very expressive so that we avoid collision with
		other mount points
		
		@param source: The remote path
		@param mountbase: The mount points base dir
		@return: The mount point complete path
		"""
		#make the mount point
		spliturl = SplittedURL(source)
		mountpoint = self.__get_mount_dir(mountbase, spliturl)

# TODO: Should we check if it is already mounted first?
		if not os.path.exists(mountpoint) :
# TODO: only the directories specified in URL should be created!
			os.makedirs(mountpoint)

		#If the path is already mounted No need to retry
		if not self.checkifmounted(source, mountbase) :
			# Create output log file
			outptr, outFile = mkstemp(prefix = "ftpFuseFAMmount_output_")
			# Create error log file
			errptr, errFile = mkstemp(prefix = "ftpFuseFAMmount_error_")

			# the option 'allow_root' is necessary to grant access
			# if the script is invoked as superuser
			curl_cmd = ["curlftpfs", "-o", "direct_io"]

			if spliturl.user and spliturl.password:
				curl_cmd.append("-o")
				opts = "user=%s:%s" % (spliturl.user, spliturl.password)
				curl_cmd.append(opts)
			if os.getuid() == 0:
				curl_cmd.append("-o")
				curl_cmd.append("allow_root")

			server = spliturl.server
			if spliturl.port:
				server += ":" + spliturl.port

			curl_cmd.append(server)

			curl_cmd.append(mountpoint)

			# Call the subprocess using convenience method
			try:
				retval = subprocess.call(curl_cmd, 0, None, None, outptr, errptr)
			except OSError, _exc:
				raise FuseFAMException(_("Couldn't found external application 'curlftpfs' needed for handling of ftp sites: %s") % _exc)

			# Close log handles
			os.close(errptr)
			os.close(outptr)
			outStr, errStr = FAM.readfile(outFile), FAM.readfile(errFile)
			FAM.delete(outFile)
			FAM.delete(errFile)
			if retval != 0 :
				raise FuseFAMException(_("Couldn't mount '%(server)s' into '%(mountpoint)s' : %(error)s") % {'server' : spliturl.server ,
													'mountpoint': mountpoint,
													'error':errStr})
		else:
			pass	# it is already mounted, do nothing

		remote_site = "ftp://" + spliturl.server
		if spliturl.port:
			remote_site += ":" + spliturl.port
		return (remote_site, mountpoint, spliturl.pathinside)

	def getdoc(self):
		"""Returns a short documentation of this plugin.
		"""
		doc = _("FTP schema is: ftp://user:pass@server/anything")
		return doc

	def checkifmounted(self, source, mountbase):
		"""Checks if the given source is already mounted in given directory.
		
		@return: True if mounted, False if not
		"""
		spliturl = SplittedURL(source)
		mountpoint = self.__get_mount_dir(mountbase, spliturl)
		return os.path.ismount(mountpoint)

	def __defineMountDirName(self, spliturl):
		"""
		Helper method that builds the name of the mount directory.
		"""
		dirname = "ftp_"
		if spliturl.user :
			dirname += spliturl.user + "@"
		dirname += spliturl.server
		if spliturl.port:
			dirname += "_%s" % spliturl.port
		return dirname

	def __get_mount_dir(self, mountbase, spliturl):
		"""Helper method that builds the full path to the mountpoint.
		"""
		mountpoint = os.path.join(mountbase, self.__defineMountDirName(spliturl))
		return mountpoint

class SplittedURL:
	"""This will match the RE and give us a group like
		('ftp://', 'test:pass@', 'wattazoum-vm.ft.nn', 'ddd/kjlh/klhkl/vvvv')
		
		@param remote: the remote site address
		@type remote: String
		
		@return: the address split into protocol, user, password, server
				 and path on server
		@rtype:  Tuple of Strings		 
		"""

	def __init__(self, url):

		exp = re.compile(ftpUrlRegex)
		match = exp.search(url)
		if match is None:
			raise FuseFAMException(_("Error matching the schema 'ftp://user:pass@server/anything' with '%s' (The '/' after server is mandatory)") % url)

		self.user = match.group(2)
		self.password = match.group(3)
		self.server = match.group(4)
		self.port = match.group(6)
		self.pathinside = match.group(7)
