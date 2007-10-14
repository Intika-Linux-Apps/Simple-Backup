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

import logging
import logging.handlers
import sys
import traceback
import os.path
import nssbackup.managers.FileAccessManager as FAM

logger = None
logfiles = []
#create formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s(%(lineno)d) - %(message)s")


def getLogger( logfile=None, level=20 ) :
	"""
	Initialization
	@param logfile : default=False
	@param level: The level of the logger (default = logging.INFO(20) )
	"""
	global logger

	if logger :
		if logfile :
			if logfile in logfiles : 
				return logger
			else :
				# create the logfile
				if not FAM.exists(logfile) :
					FAM.writetofile(logfile, "NSSBackup Logger\r\n==============\r\n")
				else :
					# clean the logfile
					FAM.delete(logfile)
					FAM.writetofile(logfile, "NSSBackup Logger\r\n==============\r\n")
				ch1 = logging.FileHandler(logfile)
				ch1.setLevel(level)
				ch1.setFormatter(formatter)
				logger.addHandler(ch1)
				logfiles.append(logfile)
		else :
			return logger
	else :
		#create logger
		logger = logging.getLogger("NSSbackup")
		logger.setLevel(level)
		#create console handler and set level to debug
		ch = logging.StreamHandler()
		ch.setLevel(level)
		#add formatter to ch
		ch.setFormatter(formatter)
		#add ch to logger
		logger.addHandler(ch)
		
		if logfile :
			# create the logfile
			if not os.path.exists(logfile) :
				FAM.writetofile(logfile, "NSSBackup Logger\r\n==============\r\n")
			else :
				# clean the logfile
				FAM.delete(logfile)
				FAM.writetofile(logfile, "NSSBackup Logger\r\n==============\r\n")
			ch1 = logging.FileHandler(logfile)
			ch1.setLevel(level)
			ch1.setFormatter(formatter)
			logger.addHandler(ch1)
			logfiles.append(logfile)
		
		return logger