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
import nssbackup.managers.FileAccessManager as FAM
from nssbackup.util.exceptions import FuseFAMException


class ftpFuseFAM (pluginFAM)  :
	"""The fuseFAM plugin for ftp
	
	@requires: curlftpfs
	@todo: Dependency on 'curlftpfs' must be taken into account for packaging!
	"""
	
	# regular expression that matches any FTP address
	__scheme_regex = "^(ftp://[^/]).*"
	
	def matchScheme(self,remoteSource):
		"""This method checks for the scheme (the protocol) of the given
		remote source, i.e. it should not check the validity of the URL.
		This behavior is necessary since otherwise no plugin is found
		to handle a FTP address if this address is not valid. The user
		would be confused. The validity of a given FTP address must be
		checked separate.
		
		@todo: The plugins ssh, sftp do not behave if the suggested way! Fix them!
		""" 
		_res = False
		_search_res = re.compile( self.__scheme_regex ).search(remoteSource)
		if _search_res is not None:
			_res = True
		return _res
	
	def mount(self,source, mountbase):
		"""Mount the source into the mountbase dir . This method should
		create a mount point to mount the source. The name of the mount
		point should be very expressive so that we avoid collision with
		other mount points
		
		@param source: The remote path
		@param mountbase: The mount points base dir
		@return: The mount point complete path
		"""
		#make the mount point
		mountpoint = self.__get_mount_dir(mountbase, source)
		
# TODO: Should we check if it is already mounted first?
		if not os.path.exists(mountpoint) :
# TODO: only the directories specified in URL should be created!
			os.makedirs(mountpoint)

		protocol, user, passwd, server, pathinside = self.__split_url(source)

		#If the path is already mounted No need to retry
		if not self.checkifmounted(source, mountbase) :			
			# Create output log file
			outptr, outFile = mkstemp(prefix="ftpFuseFAMmount_output_")
			# Create error log file
			errptr, errFile = mkstemp(prefix="ftpFuseFAMmount_error_")
	
			# the option 'allow_root' is necessary to grant access
			# if the script is invoked as superuser
			if os.getuid() == 0:
				curl_cmd = ["curlftpfs", "-o",
							"user=%s:%s,allow_root" % (user, passwd),
						    server, mountpoint]
			else:
				curl_cmd = ["curlftpfs", "-o", "user=%s:%s" % (user, passwd),
						    server, mountpoint]
	
			# Call the subprocess using convenience method
			try:
				retval = subprocess.call( curl_cmd, 0, None, None, outptr, errptr)
			except OSError, _exc:
				raise FuseFAMException(_("Couldn't found external application "\
					"'curlftpfs' needed for handling of ftp sites: %s") % _exc)
	
			# Close log handles
			os.close(errptr)
			os.close(outptr)
			outStr, errStr = FAM.readfile(outFile), FAM.readfile(errFile)	
			FAM.delete(outFile)
			FAM.delete(errFile)
			if retval != 0 :
				raise FuseFAMException(_("Couldn't mount '%(server)s' into "\
						"'%(mountpoint)s' : %(error)s") %  {'server' : server ,
													'mountpoint': mountpoint,
													'error':errStr})
		else:
			pass	# it is already mounted, do nothing
		
		remote_site = protocol+server
		return (remote_site, mountpoint, pathinside)
	
	def getdoc(self):
		"""Returns a short documentation of this plugin.
		"""
		doc = _("FTP schema is like : ftp://user:pass@server/anything") 
		return doc

	def checkifmounted(self,source, mountbase):
		"""Checks if the given source is already mounted in given directory.
		
		@return: True if mounted, False if not
		"""
		_res = None
		mountpoint = self.__get_mount_dir(mountbase, source)
		_res = os.path.ismount(mountpoint)
		return _res
	
	def __defineMountDirName(self, remote):
		"""Helper method that builds the name of the mount directory.
		"""
		protocol, user, passwd, server, pathinside = self.__split_url(remote)
		if user != "":
			dirname = "ftp_%s@%s" % (user, server)
		else :
			dirname = "ftp_%s" % (server)
		return dirname
	
	def __get_mount_dir(self, mountbase, source):
		"""Helper method that builds the full path to the mountpoint.
		"""
		mountpoint = os.path.join( mountbase, self.__defineMountDirName(source))
		return mountpoint
		
	def __split_url(self, remote):
		"""This will match the RE and give us a group like
		('ftp://', 'test:pass@', 'wattazoum-vm.ft.nn', 'ddd/kjlh/klhkl/vvvv')
		
		@param remote: the remote site address
		@type remote: String
		
		@return: the address split into protocol, user, password, server
				 and path on server
		@rtype:  Tuple of Strings		 
		
		@todo: Add support for port numbers!
		@todo: Put the split URL into its own class!
		"""
		protocol = ""
		user = ""
		passwd = ""
		server = ""
		pathinside = ""

		exp = re.compile("^(ftp://)([^:]+?:[^@]+?@|[^:]+?@)?([^/^:^@]+?)/(.*)")
		match = exp.search(remote)
		if match is None: 
			raise FuseFAMException(_("Error matching the schema "\
							"'ftp://user:pass@server/anything' with '%s' "\
							"(The '/' after server is mandatory)") % remote)

		protocol = match.group(1)
		server = match.group(3)
		
		user_passwd = match.group(2)
		if user_passwd is not None:
			exp_user_passwd = re.compile("^([^:]+):?(.+)?@")
			user_passwd_match = exp_user_passwd.search(user_passwd)

			user = user_passwd_match.group(1)
			passwd = user_passwd_match.group(2)
			if passwd is None:
				passwd = ""
		pathinside = match.group(4)
		if pathinside is None:
			pathinside = ""
		return (protocol, user, passwd, server, pathinside)
