#	This program is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; either version 2 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program; if not, write to the Free Software
#	Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# Authors :
#	Ouattara Oumar Aziz ( alias wattazoum ) <wattazoum@gmail.com>


import unittest
import os
from nssbackup.managers.FuseFAM import FuseFAM
from nssbackup.managers.ConfigManager import ConfigManager

class TestFuseFAM(unittest.TestCase):
	"""
	"""
	fam = None
	
	def setUp(self):
		""
		self.fam = FuseFAM(ConfigManager(os.sep.join([os.path.abspath("test-datas"),"sbackup.conf.fusefam"])))
		
	
	def testInitialize(self):
		" Initialize "
		self.fam.initialize()
		
suite = unittest.TestLoader().loadTestsFromTestCase(TestFuseFAM)
unittest.TextTestRunner(verbosity=2).run(suite)