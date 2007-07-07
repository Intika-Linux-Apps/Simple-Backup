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

from sbackup.plugins import pluginFAM

class smbFuseFAM(pluginFAM) :
	"""
	The fuseFAM plugin interface
	"""
	
	def matchScheme(self,remoteSource):
		return remoteSource.startswith("smb://")
	
	def mount(self,source, mountbase):
		"""
		Mount the source intor the mountbase dir . This method should create a mount point to mount the source. 
		The name of the mount point should be very expressive so that we avoid collision with other mount points
		@param source: The remote path
		@param mountbase: The mount points base dir
		@return: The mount point complete path
		"""
		raise Exception("Not implemented for that plugin")