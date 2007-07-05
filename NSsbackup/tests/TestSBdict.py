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


import unittest
import os
from sbackup.util.structs import SBdict


class TestSBdict(unittest.TestCase):
	"""
	"""
	sbd = None
	
	def setUp(self):
		""
		self.sbd = SBdict()
		self.sbd["home"] =  ["0",None]
		self.sbd["/home/user"] =  "1"
		self.sbd["/home/usr1"] =  ["1",None]
		self.sbd["/home/usr1/usr2"] =  ["2",None]
		self.sbd["/home/usr1/usr2/test"] =  ["3",None]
		self.sbd["/home/usr1/usr2/test/dir"] =  ["4",None]
		self.sbd["/home/usr1/usr2/test/direrec"] =  ["4",None]
		self.sbd["/home/usr1/usr2/test/dir/test/de/plus"] =  ["7",None]
	
	def testIteritems(self):
		" IterItems () "
		for k,v in self.sbd.iteritems() :
			print k , v	
		
	def testIterkeys(self):
		" Iterkeys () "
		for k in self.sbd.iterkeys() :
			print k
	
	def testItervalues(self):
		""
		for v in self.sbd.itervalues() :
			print v
		
	def testGetSon(self):
		""
		
	def testDictCommonUsage(self):
		""

suite = unittest.TestLoader().loadTestsFromTestCase(TestSBdict)
unittest.TextTestRunner(verbosity=2).run(suite)