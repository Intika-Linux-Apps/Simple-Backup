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
import sys
import traceback
import os.path
import nssbackup.managers.FileAccessManager as FAM

class LogFactory :
	"""
	"""
	logger = None
	
	#create formatter
	formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s(%(lineno)d) - %(message)s")
	
	def getLogger(name=None, logfile=None, level=20 ) :
		"""
		Initialization
		@param name: The name of the logger
		@param logfile : default=False
		@param level: The level of the logger (default = logging.INFO(20) )
		"""
			
		if LogFactory.logger :
			if name:
				if LogFactory.logger.name == name :
					return LogFactory.logger
				else :
					return LogFactory.__createLogger(name,logfile,level)
			else :
				return LogFactory.logger
		else :
			return LogFactory.__createLogger(name,logfile,level)

	getLogger = staticmethod(getLogger)
	
	def __createLogger(name=None, logfile=None, level=20):
	
		if not name :
			name = "NSsbackup"
		
		#create logger
		LogFactory.logger = logging.getLogger(name)
		LogFactory.logger.setLevel(level)
		#create console handler and set level to debug
		ch = logging.StreamHandler()
		ch.setLevel(level)
		#add formatter to ch
		ch.setFormatter(LogFactory.formatter)
		#add ch to logger
		LogFactory.logger.addHandler(ch)
		
		if logfile :
			# create the logfile
			if not os.path.exists(logfile) :
				FAM.writetofile(logfile, "NSSBackup '%s' Logger\r\n==============\r\n" % name)
			else :
				# clean the logfile
				os.remove(logfile)
				FAM.writetofile(logfile, "NSSBackup '%s' Logger\r\n==============\r\n" % name)
			ch1 = logging.FileHandler(logfile)
			ch1.setLevel(level)
			ch1.setFormatter(LogFactory.formatter)
			LogFactory.logger.addHandler(ch1)
		
		return LogFactory.logger

	__createLogger = staticmethod(__createLogger)