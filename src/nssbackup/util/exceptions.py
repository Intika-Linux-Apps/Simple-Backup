#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
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

class SBException(Exception) :
	"""
	This class will help us distinguish Exception that we must handle( Exception created by us) 
	from programing errors Exception.
	"""

class NotValidSnapshotException(SBException) :
	"""
	This Exception is thrown by Snapshot validation.
	"""
	
class NotValidSnapshotNameException(NotValidSnapshotException):
	"""
	Exception launched when the name of a snapshot is not valid
	"""
	
	
class NotValidSectionException(SBException) :
	"""
	This Exception is thrown by Config Section validation.
	"""

class NonValidOptionException(SBException):
	"""
	Thrown when a config option is not Valid
	"""

class CorruptedSBdictException(SBException):
	"""
	Thrown when a SBdict is corrupted
	"""
	
class FuseFAMException(SBException):
	"""
	Thrown when a Fuse mount fails
	"""
	
class RebaseSnpException(SBException):
	"""
	Thrown for rebase exception
	"""

class RebaseFullSnpForbidden(RebaseSnpException):
	"""
	Thrown when trying to rebase a full snapshot
	"""