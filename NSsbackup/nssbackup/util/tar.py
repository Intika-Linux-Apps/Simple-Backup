import os
from nssbackup.util.log import getLogger
import nssbackup.util as Util
from nssbackup.util.exceptions import SBException

def getArchiveType(archive):
	"""
	return the type of an archive 
	@param archive: 
	@return: tar, gzip, bzip2 or None
	"""
	command = "file"
	opts = ["--mime","-b",archive]
	out, err, retVal = Util.launch(command, opts)
	if "x-bzip2" in out :
		return "bzip2"
	elif "x-gzip" in out :
		return "gzip"
	elif "x-tar" in out :
		return "tar"
	else :
		return None
	
	
def extract(sourcetgz, file, dest , bckupsuffix = None):
	"""
	Extract from source tar.gz the file "file" to dest.
	@param source:
	@param file:
	@param dest:
	"""
	# strip leading sep
	file = file.lstrip(os.sep)
	
	options = ["-xp", "--occurrence=1", "--ignore-failed-read", '--backup=existing']
	
	archType = getArchiveType(sourcetgz)
	if archType =="tar" :
		pass
	elif archType == "gzip" :
		options.insert(1,"--gzip")
	elif archType == "bzip2" :
		options.insert(1,"--bzip2")
	else :
		raise SBException (_("Invalid Archive type"))
		
	if os.getuid() == 0 :
		options.append("--same-owner")
	if dest :
		options.append( "--directory="+dest )
	else : 
		options.append( "--directory="+os.sep )
	if bckupsuffix :
		options.append("--suffix="+bckupsuffix)
	options.extend(['--file='+sourcetgz,file])
	
	outStr, errStr, retval = Util.launch("tar", options)
	if retval != 0 :
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)
	
		
class Dumpdir():
	"""
	"""
	
