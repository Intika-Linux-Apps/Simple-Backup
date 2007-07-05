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
import os
from sbackup.util.log import getLogger

class localFuseFAM (pluginFAM):
	"""
	The localFuseFAM plugin do nothing when the mount method is called
	@author: Oumar Aziz Ouattara <wattazoum@gmail.com>
	@version: 1.0
	"""

	def matchScheme(self,remoteSource):
		"""
		Try to match the scheme of the remoteSource.
		@param remoteSource: The remote path
		@return: True if the scheme matches the one for this 
		@rtype: boolean
		"""
		return remoteSource.startswith(os.sep)
	
	def mount(self,source, mountbase):
		"""
		Fake mounter to be used by the fuseFAM
		@param source: The remote path
		@param mountbase: The mount points base dir
		@return: The mount point complete path
		@rtype: str
		"""
		getLogger().debug("Nothing to do for '%s'" % source)
		return (os.sep,"",source.lstrip(os.sep))