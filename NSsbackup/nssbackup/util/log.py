# -*- coding: utf-8 -*-
# Elisa - Home multimedia server
# Copyright (C) 2006,2007 Fluendo Embedded S.L. (www.fluendo.com).
# All rights reserved.
#
# This file is available under one of two license agreements.
#
# This file is licensed under the GPL version 2.
# See "LICENSE.GPL" in the root of this distribution including a special
# exception to use Elisa with Fluendo's plugins.
#
# The GPL part of Elisa is also available under a commercial licensing
# agreement from Fluendo.
# See "LICENSE.Elisa" in the root directory of this distribution package
# for details on that license.


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
					FAM.writetofile(logfile, "SBackup Logger\r\n===========\r\n")
				else :
					# clean the logfile
					FAM.delete(logfile)
					FAM.writetofile(logfile, "SBackup Logger\r\n===========\r\n")
				ch1 = logging.FileHandler(logfile)
				ch1.setLevel(level)
				ch1.setFormatter(formatter)
				logger.addHandler(ch1)
				logfiles.append(logfile)
		else :
			return logger
	else :
		#create logger
		logger = logging.getLogger("Sbackup")
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
				FAM.writetofile(logfile, "SBackup Logger\r\n===========\r\n")
			else :
				# clean the logfile
				FAM.delete(logfile)
				FAM.writetofile(logfile, "SBackup Logger\r\n===========\r\n")
			ch1 = logging.FileHandler(logfile)
			ch1.setLevel(level)
			ch1.setFormatter(formatter)
			logger.addHandler(ch1)
			logfiles.append(logfile)
		
		return logger