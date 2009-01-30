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

from nssbackup.managers.SnapshotManager import SnapshotManager
from nssbackup.util.log import LogFactory
from nssbackup.util.Snapshot import Snapshot
import unittest

import os

class TestSnapshotManager(unittest.TestCase) :
	
	def setUp(self):
		LogFactory.getLogger(level=10)
		self.snpman = SnapshotManager(os.path.abspath("test-datas/backupdir"))
	
	def testGetSnapshots(self):
		"""
		"""
		
	def testExportSnapshot(self):
		"""
		"""
		
		
	def testRebaseSnapshot(self):
		"""
		"""
		snp1 = Snapshot(os.path.abspath("test-datas/backupdir/2007-12-28_16.49.54.838045.matou-laptop.inc"))
		snp2 = Snapshot(os.path.abspath("test-datas/backupdir/2007-12-28_16.47.05.716709.matou-laptop.ful"))
		self.snpman.rebaseSnapshot(snp1,snp2)
		
	
	def testRemoveSnapshot(self):
		"""
		"""
		
	def testCompareSnapshots(self):
		"""
		"""
	
#	def testGetRevertState(self):
#		"""
#		"""
#		snapshots = self.snpman.getSnapshots()
#		revertstate = self.snpman.getRevertState(snapshots[0], os.sep)
#		self.assertEqual(len(revertstate),3)
#		for k, v in revertstate.iteritems() :
#			print(k+" = "+str(v)) 
#		self.assertFalse(revertstate[os.path.abspath('./test-datas/backupdir/2007-05-17_13.45.45.609201.wattazoum-vm.ful')].has_key("/home/wattazoum/Desktop/sbackup-test/d17/"))
#		revertstate = self.snpman.getRevertState(snapshots[1], "/home/wattazoum/Desktop/sbackup-test/")
#		self.assertEqual(len(revertstate),2)
#		self.assertFalse(revertstate[os.path.abspath('./test-datas/backupdir/2007-05-17_13.45.45.609201.wattazoum-vm.ful')].has_key("/home/wattazoum/Desktop/sbackup-test/d17/"))
#		self.assertTrue(revertstate[os.path.abspath('./test-datas/backupdir/2007-05-17_19.45.08.812921.wattazoum-vm.inc')].has_key("/home/wattazoum/Desktop/sbackup-test/d17/"))
#		
	def testPurge(self):
		"""
		"""
		
