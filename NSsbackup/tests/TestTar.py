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

from nssbackup.util.tar import SnapshotFile
from nssbackup.util.log import getLogger
import unittest

class TestSnapshotManager(unittest.TestCase) :
	"""
	"""
	
	def setUp(self):
		getLogger(level=10)
		self.snarSNPfile = SnapshotFile("test-datas/files.snar")
		
	def testGetFormatVersion(self):
		self.assertEqual(self.snarSNPfile.getFormatVersion(),2)
	
	def testParseFormat2(self):
		for f in self.snarSNPfile.parseFormat2():
			print f[-2]+ "\t"
			for d in f[-1] :
				print str(d)
	
	