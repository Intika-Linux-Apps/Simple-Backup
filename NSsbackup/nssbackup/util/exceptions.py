
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