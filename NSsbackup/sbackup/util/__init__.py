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

import sbackup.managers.FileAccessManager as FAM
import os
import subprocess
from sbackup.util.log import getLogger
from sbackup.util.exceptions import SBException
from tempfile import *

def launch(cmd, opts):
	"""
	launch a command and gets stdout and stderr
	outStr = a String containing the output from stdout" 
	errStr = a String containing the error from stderr
	retVal = the return code (= 0 means that everything were fine )
	@param cmd: The command to launch
	@return: (outStr, errStr, retVal)
	"""
	# Create output log file
	outptr,outFile = mkstemp(prefix="output_")

	# Create error log file
	errptr, errFile = mkstemp(prefix="error_")

	# Call the subprocess using convenience method
	opts.insert(0,cmd)
	retval = subprocess.call(opts, 0, None, None, outptr, errptr)

	# Close log handles
	os.close(errptr)
	os.close(outptr)
	
	outStr, errStr = FAM.readfile(outFile),FAM.readfile(errFile)
	
	FAM.delete(outFile)
	FAM.delete(errFile)
	
	return (outStr, errStr, retval)

def extract(sourcetgz, file, dest , bckupsuffix = None):
	"""
	Extract from source tar.gz the file "file" to dest.
	@param source:
	@param file:
	@param dest:
	"""
	# strip leading sep
	file = file.lstrip(os.sep)
	
	options = ["-xzp", "--occurrence=1", "--ignore-failed-read", '--backup=existing']
	if dest :
		options.append( "--directory="+dest )
	else : 
		options.append( "--directory="+os.sep )
	if bckupsuffix :
		options.append("--suffix="+bckupsuffix)
	options.extend(['--file='+sourcetgz,file])
	
	outStr, errStr, retval = launch("tar", options)
	if retval != 0 :
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)
	
def extract2(sourcetgz, fileslist, dest, bckupsuffix = None ):
	"""
	Extract the files listed in the 'fileslist' file to dest. This method 
	has been created to optimize the time spent by giving to tar a complete 
	list of file to extract. Use this if ever you have to extract more than 1 dir .
	@param sourcetgz:
	@param fileslist: a path to the file containing the list
	@param dest: destination
	"""
	options = ["-xzp", "--occurrence=1", "--ignore-failed-read", '--backup=existing']
	if dest :
		options.append( "--directory="+dest )
	else : 
		options.append( "--directory="+os.sep )
	if bckupsuffix :
		options.append("--suffix="+bckupsuffix)
	
	options.extend(['--file='+sourcetgz,'--null','--files-from='+os.path.normpath(fileslist)])
	
	outStr, errStr, retval = launch("tar", options)
	if retval != 0 :
		getLogger().debug("output was : " + outStr)
		raise SBException("Error when extracting : " + errStr )
	getLogger().debug("output was : " + outStr)
	