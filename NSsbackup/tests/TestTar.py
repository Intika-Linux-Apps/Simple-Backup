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

from nssbackup.util.tar import SnapshotFile, MemSnapshotFile,ProcSnapshotFile
from nssbackup.util.log import getLogger
import unittest,os
from nssbackup.util.exceptions import *

class TestSnapshotManager(unittest.TestCase) :
	"""
	"""
	
	def setUp(self):
		getLogger(level=20)
		self.snarSNPfile = SnapshotFile("test-datas"+os.sep+"files.snar")
		self.snarSNPfile2 = SnapshotFile("test-datas"+os.sep+"files-2.snar")
		
	def testGetFormatVersion(self):
		" Get the SNAR file version"
		self.assertEqual(self.snarSNPfile.getFormatVersion(),2)
	
	def testParseFormat2(self):
		" Parse the SNAR file "
		for f in self.snarSNPfile.parseFormat2():
			print f[-2]+ "\t"
			for d in f[-1] :
				print str(d)
	
	def testMemSnasphotFile(self):
		" Create and read a MemSnapshotFile "
		msnpf = MemSnapshotFile(self.snarSNPfile)
		for i in msnpf.getContent("/home/wattazoum/Images/camescope/2007-04-08--09.09.05") :
			print str(i)
		print msnpf
		
	def testProcSnapshotFile(self):
		" Create and read a ProcSnapshotFile "
		psnpf = ProcSnapshotFile(self.snarSNPfile)
		for i in psnpf.getContent("/home/wattazoum/Images/camescope/2007-04-08--09.09.05") :
			print str(i)
		print psnpf
		
		psnpf = ProcSnapshotFile(self.snarSNPfile2)
		self.assertRaises(SBException,psnpf.getContent, "/home/wattazoum/Images/camescope/2007-04-08--09.09.05")
		for i in psnpf.getContent("/home/wattazoum/Images") :
			print str(i)
		print psnpf
		
	def testGetFirstItems(self):
		" Get the list of first items into a snarfile"
		psnpf = ProcSnapshotFile(self.snarSNPfile)
		print psnpf.getFirstItems()
		self.assertEqual(len(psnpf.getFirstItems()),1)
		self.assertEquals(psnpf.getFirstItems(),['/home/wattazoum/Images/camescope'])
		
		psnpf = ProcSnapshotFile(self.snarSNPfile2)
		print psnpf.getFirstItems()
		self.assertEqual(len(psnpf.getFirstItems()),4)
		
		msnpf = MemSnapshotFile(self.snarSNPfile2)
		print msnpf
		print msnpf.getFirstItems()
		self.assertEqual(len(psnpf.getFirstItems()),4)
		