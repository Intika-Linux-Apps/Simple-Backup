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

import nssbackup.managers.FileAccessManager as FAM
import os
import subprocess, nssbackup
from nssbackup.util.log import getLogger
from nssbackup.util.exceptions import SBException
from tempfile import *
import inspect

def getResource(resourceName):
	"""
	This will look for a ressource installed by nssbackup.
	The installation script write in the ressources file were it stores the file
	then getRessource will look for them.
	@param ressourceName: the ressource name, as complete as possible.
	@param the ressource: absolute path. 
	"""
	tmp = inspect.getabsfile(nssbackup)
	resfile = open(os.sep.join([os.path.dirname(tmp),"ressources"]))
	for dir in resfile.readlines() :
		dir = dir.strip()
		#getLogger().debug("Searching in directory '%s'" % dir)
		if os.path.exists(dir) and os.path.isdir(dir):
			list = os.listdir(dir)
			#getLogger().debug("File list is :" + str(list))
			for f in list :
				if f == resourceName :
					return os.path.normpath(os.sep.join([dir,resourceName]))
	devvalue = os.path.dirname(tmp)+"/../datas/"
	if os.path.exists(devvalue + resourceName) :
		return os.path.normpath(devvalue + resourceName)
	raise SBException("'%s' hasn't been found in the ressource list"% resourceName)
					

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
	if os.getuid() == 0 :
		options.append("--same-owner")
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
	options = ["-xzp", "--ignore-failed-read", '--backup=existing']
	if os.getuid() == 0 :
		options.append("--same-owner")
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
	
import pygtk
pygtk.require('2.0')
import gtk, gobject

# Update the value of the progress bar so that we get
# some movement
def progress_timeout(pbobj):
    
    pbobj.pbar.pulse()

    # As this is a timeout function, return TRUE so that it
    # continues to get called
    return True

class ProgressBar:
    
    # Clean up allocated memory and remove the timer
    def destroy_progress(self, widget, data=None):
        #gobject.source_remove(self.timer)
        self.timer = 0
        self.window.destroy()

    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_resizable(True)

        self.window.connect("destroy", self.destroy_progress)
        self.window.set_title("ProgressBar")
        self.window.set_border_width(0)

        vbox = gtk.VBox(False, 5)
        vbox.set_border_width(10)
        self.window.add(vbox)
        vbox.show()
        # Create a centering alignment object
        align = gtk.Alignment(0.5, 0.5, 0, 0)
        vbox.pack_start(align, False, False, 5)
        align.show()
        # Create the ProgressBar
        self.pbar = gtk.ProgressBar()

        align.add(self.pbar)
        self.pbar.show()

        # Add a timer callback to update the value of the progress bar
        self.timer = gobject.timeout_add (100, progress_timeout, self)

        self.window.show()